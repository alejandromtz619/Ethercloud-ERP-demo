"""
API de integración v1 (/api/integracion/v1): lo que el CRM y el bot pueden pedirle al ERP.

Autenticación (Authorization: Bearer ...), una de dos:
- Token de servicio (ecs_...): de una empresa, con scopes fijos. Perfiles: "crm-interno" (todo) y
  "crm-bot" (sólo catálogo y pedidos). El techo lo pone el ERP: aunque el CRM se viera
  comprometido, el token del bot no puede leer clientes, ventas ni costos.
- Token de un usuario (el JWT del ERP): cuando una persona usa el CRM. Cada scope se traduce a
  permisos del ERP (PERMISOS_POR_SCOPE), así el ERP le aplica los permisos de esa persona.

Nunca expone costos, proveedores ni márgenes. Los datos siempre son de la empresa del token.
Contrato completo: documentacion/api_integracion_v1.md
"""
import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Categoria, Marca, Producto, StockActual, TokenServicio, Usuario

PREFIJO_TOKEN = "ecs_"

SCOPES = ("catalogo.publico", "pedidos.crear", "pedidos.leer", "clientes.leer", "clientes.escribir",
          "metricas.leer", "eventos.leer")
PERFILES = {
    "crm-interno": SCOPES,
    "crm-bot": ("catalogo.publico", "pedidos.crear", "pedidos.leer"),
}
# Con token de usuario: alguno de estos permisos del ERP habilita el scope (() = cualquier usuario)
PERMISOS_POR_SCOPE = {
    "catalogo.publico": (),
    "pedidos.crear": ("ventas.crear", "presupuestos.crear"),
    "pedidos.leer": ("ventas.crear", "ventas.ver", "ventas.ver_historial", "presupuestos.ver"),
    "clientes.leer": ("clientes.ver",),
    "clientes.escribir": ("clientes.crear", "clientes.editar"),
    "metricas.leer": ("bi.ver", "dashboard.ver"),
    "eventos.leer": ("sistema.configurar",),
}


def generar_token() -> tuple:
    """(token, hash). El token se muestra una sola vez; en la base queda el hash."""
    token = PREFIJO_TOKEN + secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    # Los tokens son aleatorios de 256 bits: SHA-256 alcanza (no hace falta un hash lento)
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass
class Credencial:
    empresa_id: int
    usuario: Optional[Usuario] = None       # token de usuario, o el usuario asociado al token de servicio
    token: Optional[TokenServicio] = None   # sólo con token de servicio
    permisos_ok: dict = field(default_factory=dict)  # scope -> bool, ya consultado en esta petición

    @property
    def es_servicio(self) -> bool:
        return self.token is not None


def _token_del_encabezado(request: Request) -> str:
    valor = request.headers.get("Authorization", "")
    if not valor.lower().startswith("bearer ") or not valor[7:].strip():
        raise HTTPException(status_code=401, detail="Token de autenticación requerido.")
    return valor[7:].strip()


def crear_router(usuario_desde_jwt: Callable, tiene_algun_permiso: Callable) -> APIRouter:
    """Router de la API. Recibe de server.py cómo validar un JWT y cómo consultar permisos (así
    este módulo no importa server.py)."""

    async def autenticar(request: Request, db: AsyncSession) -> Credencial:
        cred = getattr(request.state, "credencial_integracion", None)
        if cred:
            return cred
        token = _token_del_encabezado(request)
        if token.startswith(PREFIJO_TOKEN):
            fila = (await db.execute(select(TokenServicio).where(
                TokenServicio.hash == hash_token(token), TokenServicio.activo == True))).scalar_one_or_none()
            if not fila:
                raise HTTPException(status_code=401, detail="Token de servicio inválido o revocado.")
            ahora = datetime.now(timezone.utc)
            # Último uso con resolución de un minuto: no escribir en cada petición
            if not fila.ultimo_uso or ahora - fila.ultimo_uso.replace(tzinfo=fila.ultimo_uso.tzinfo or timezone.utc) > timedelta(minutes=1):
                fila.ultimo_uso = ahora
                await db.commit()
            usuario = await db.get(Usuario, fila.usuario_id) if fila.usuario_id else None
            cred = Credencial(empresa_id=fila.empresa_id, usuario=usuario, token=fila)
        else:
            usuario = await usuario_desde_jwt(token, db)
            cred = Credencial(empresa_id=usuario.empresa_id, usuario=usuario)
        request.state.credencial_integracion = cred
        return cred

    def requiere_scope(scope: str):
        assert scope in SCOPES, scope

        async def _dep(request: Request, db: AsyncSession = Depends(get_db)) -> Credencial:
            cred = await autenticar(request, db)
            if cred.es_servicio:
                permitido = scope in (cred.token.scopes or [])
            elif scope not in cred.permisos_ok:
                permisos = PERMISOS_POR_SCOPE[scope]
                cred.permisos_ok[scope] = not permisos or await tiene_algun_permiso(db, cred.usuario.id, permisos)
                permitido = cred.permisos_ok[scope]
            else:
                permitido = cred.permisos_ok[scope]
            if not permitido:
                raise HTTPException(status_code=403, detail=f"El token no tiene el permiso {scope}.")
            return cred
        _dep.scope = scope  # lo lee la prueba que verifica que toda ruta declare un scope
        return _dep

    router = APIRouter(prefix="/api/integracion/v1", tags=["integracion"])

    # ---------- Identidad ----------
    @router.get("/yo")
    async def quien_soy(request: Request, db: AsyncSession = Depends(get_db)):
        """Con qué credencial se está llamando (para verificar la configuración del CRM)."""
        cred = await autenticar(request, db)
        return {
            "tipo": "servicio" if cred.es_servicio else "usuario",
            "empresa_id": cred.empresa_id,
            "nombre": cred.token.nombre if cred.es_servicio else f"{cred.usuario.nombre} {cred.usuario.apellido or ''}".strip(),
            "scopes": list(cred.token.scopes) if cred.es_servicio else None,
        }

    # ---------- Catálogo ----------
    async def _disponibilidad(db: AsyncSession, productos: list) -> dict:
        """D7: sin stock / disponible (sin número) / últimas unidades (cantidad exacta) cuando el
        stock está en el umbral de alerta o por debajo. Umbral: la menor alerta mínima de sus
        almacenes; si no tiene, el stock mínimo del producto. La calcula el ERP, no el bot."""
        ids = [p.id for p in productos]
        if not ids:
            return {}
        filas = (await db.execute(
            select(StockActual.producto_id, func.coalesce(func.sum(StockActual.cantidad), 0),
                   func.min(StockActual.alerta_minima))
            .where(StockActual.producto_id.in_(ids)).group_by(StockActual.producto_id)
        )).all()
        stock = {pid: (int(total), alerta) for pid, total, alerta in filas}
        out = {}
        for p in productos:
            total, alerta = stock.get(p.id, (0, None))
            umbral = alerta if alerta is not None else (p.stock_minimo or 0)
            if total <= 0:
                out[p.id] = {"estado": "sin_stock", "cantidad": None}
            elif total <= umbral:
                out[p.id] = {"estado": "ultimas_unidades", "cantidad": total}
            else:
                out[p.id] = {"estado": "disponible", "cantidad": None}
        return out

    def _producto_publico(p, categoria, marca, disponibilidad) -> dict:
        return {
            "id": p.id,
            "nombre": p.nombre,
            "descripcion": p.descripcion,
            "categoria": categoria,
            "marca": marca,
            "precio_venta": float(p.precio_venta),
            "disponibilidad": disponibilidad,
            "imagen_url": p.imagen_url,
        }

    def _consulta_catalogo(empresa_id: int):
        return (
            select(Producto, Categoria.nombre, Marca.nombre)
            .outerjoin(Categoria, Producto.categoria_id == Categoria.id)
            .outerjoin(Marca, Producto.marca_id == Marca.id)
            .where(Producto.empresa_id == empresa_id, Producto.activo == True)
        )

    @router.get("/catalogo/productos")
    async def catalogo_productos(
        q: Optional[str] = None,
        categoria_id: Optional[int] = None,
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        cred: Credencial = Depends(requiere_scope("catalogo.publico")),
        db: AsyncSession = Depends(get_db),
    ):
        """Productos activos con precio de venta y disponibilidad. Búsqueda por nombre, código o marca."""
        consulta = _consulta_catalogo(cred.empresa_id)
        if q and q.strip():
            patron = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            consulta = consulta.where(or_(Producto.nombre.ilike(patron, escape="\\"),
                                          Producto.codigo_barra.ilike(patron, escape="\\"),
                                          Marca.nombre.ilike(patron, escape="\\")))
        if categoria_id:
            consulta = consulta.where(Producto.categoria_id == categoria_id)
        total = await db.scalar(select(func.count()).select_from(consulta.subquery()))
        filas = (await db.execute(consulta.order_by(Producto.nombre, Producto.id).limit(limit).offset(offset))).all()
        disp = await _disponibilidad(db, [f[0] for f in filas])
        return {"items": [_producto_publico(p, c, m, disp[p.id]) for p, c, m in filas],
                "total": total, "limit": limit, "offset": offset}

    @router.get("/catalogo/productos/{producto_id}")
    async def catalogo_producto(
        producto_id: int,
        cred: Credencial = Depends(requiere_scope("catalogo.publico")),
        db: AsyncSession = Depends(get_db),
    ):
        fila = (await db.execute(_consulta_catalogo(cred.empresa_id).where(Producto.id == producto_id))).first()
        if not fila:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        p, c, m = fila
        return _producto_publico(p, c, m, (await _disponibilidad(db, [p]))[p.id])

    return router
