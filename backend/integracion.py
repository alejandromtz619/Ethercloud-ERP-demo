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
import re
import secrets
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, event, func, insert, inspect as sa_inspect, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import (
    PARAGUAY_TZ, Almacen, Categoria, Cliente, CreditoCliente, Entrega, EstadoEntrega, EstadoVenta, EventoIntegracion,
    Marca, MovimientoStock, PedidoIntegracion, Presupuesto, Producto, StockActual, TipoMovimientoStock, TokenServicio,
    Usuario, Venta, VentaItem,
)
from schemas import VentaCreate, VentaItemCreate

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


# ---------------------------------------------------------------------------------------------
# Eventos (outbox). Un listener de la sesión detecta los cambios al guardarlos y escribe el evento
# en la MISMA transacción: si el cambio se deshace, el evento también; ninguna ruta, actual o
# futura, se olvida de emitirlo.
# ---------------------------------------------------------------------------------------------
TIPOS_EVENTO = ("venta.confirmada", "venta.anulada", "cliente.creado", "cliente.actualizado",
                "presupuesto.creado", "entrega.estado", "stock.entrada")
# Los eventos se entregan con este retraso: dos transacciones pueden confirmarse en otro orden que el
# de sus ids, y sin margen el CRM se saltaría la más lenta. El CRM descarta repetidos por id.
RETRASO_EVENTOS_SEGUNDOS = 5
DIAS_DE_EVENTOS = 30


def _cambio(obj, atributo):
    """Valor nuevo si `atributo` cambió en este flush, si no None."""
    hist = sa_inspect(obj).attrs[atributo].history
    return hist.added[0] if hist.added else None


def _eventos_del_flush(session: Session) -> list:
    eventos = []
    conexion = session.connection()

    def empresa_y_cliente_de_venta(venta_id):
        return conexion.execute(select(Venta.empresa_id, Venta.cliente_id).where(Venta.id == venta_id)).first() or (None, None)

    for obj in list(session.new) + list(session.dirty):
        nuevo = obj in session.new
        if isinstance(obj, Venta):
            estado = _cambio(obj, "estado")
            if estado in (EstadoVenta.CONFIRMADA, EstadoVenta.ANULADA):
                eventos.append((obj.empresa_id, "venta." + estado.value.lower(),
                                obj.id, {"venta_id": obj.id, "cliente_id": obj.cliente_id,
                                         "total": float(obj.total or 0), "tipo_pago": obj.tipo_pago.value if obj.tipo_pago else None,
                                         "es_delivery": bool(obj.es_delivery)}))
        elif isinstance(obj, Cliente):
            if nuevo:
                eventos.append((obj.empresa_id, "cliente.creado", obj.id, {"cliente_id": obj.id}))
            elif session.is_modified(obj, include_collections=False):
                eventos.append((obj.empresa_id, "cliente.actualizado", obj.id,
                                {"cliente_id": obj.id, "activo": bool(obj.estado)}))
        elif isinstance(obj, Presupuesto) and nuevo:
            eventos.append((obj.empresa_id, "presupuesto.creado", obj.id,
                            {"presupuesto_id": obj.id, "cliente_id": obj.cliente_id}))
        elif isinstance(obj, Entrega) and (nuevo or _cambio(obj, "estado") is not None):
            estado = obj.estado.value if obj.estado else None
            empresa_id, cliente_id = empresa_y_cliente_de_venta(obj.venta_id)
            eventos.append((empresa_id, "entrega.estado", obj.id,
                            {"entrega_id": obj.id, "venta_id": obj.venta_id, "cliente_id": cliente_id, "estado": estado}))
        elif isinstance(obj, MovimientoStock) and nuevo and obj.tipo == TipoMovimientoStock.ENTRADA                 and obj.referencia_tipo != "ANULACION_VENTA":
            empresa_id = conexion.execute(select(Almacen.empresa_id).where(Almacen.id == obj.almacen_id)).scalar()
            eventos.append((empresa_id, "stock.entrada", obj.producto_id,
                            {"producto_id": obj.producto_id, "almacen_id": obj.almacen_id, "cantidad": obj.cantidad}))
    return eventos


@event.listens_for(Session, "after_flush")
def registrar_eventos(session, flush_context):
    """after_flush: los objetos nuevos ya tienen id y el historial de cambios sigue disponible."""
    eventos = [e for e in _eventos_del_flush(session) if e[0] is not None]
    if eventos:
        ahora = datetime.now(timezone.utc)
        session.connection().execute(insert(EventoIntegracion), [
            {"empresa_id": empresa_id, "tipo": tipo, "entidad_id": entidad_id, "datos": datos, "creado_en": ahora}
            for empresa_id, tipo, entidad_id, datos in eventos
        ])


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


def crear_router(usuario_desde_jwt: Callable, tiene_algun_permiso: Callable, armar_venta: Callable) -> APIRouter:
    """Router de la API. Recibe de server.py cómo validar un JWT, cómo consultar permisos y cómo
    armar una venta (así este módulo no importa server.py ni duplica esa lógica)."""

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

    # ---------- Clientes ----------
    def _cliente_publico(c: Cliente) -> dict:
        return {"id": c.id, "nombre": c.nombre, "apellido": c.apellido, "ruc": c.ruc, "cedula": c.cedula,
                "telefono": c.telefono, "email": c.email, "direccion": c.direccion, "activo": bool(c.estado)}

    async def _cliente_de_la_empresa(db: AsyncSession, cred: Credencial, cliente_id: int) -> Cliente:
        cliente = await db.get(Cliente, cliente_id)
        if not cliente or cliente.empresa_id != cred.empresa_id:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return cliente

    @router.get("/clientes")
    async def buscar_clientes(
        telefono: Optional[str] = None,
        documento: Optional[str] = None,
        desde_id: Optional[int] = Query(None, ge=0),
        limite: int = Query(200, ge=1, le=1000),
        cred: Credencial = Depends(requiere_scope("clientes.leer")),
        db: AsyncSession = Depends(get_db),
    ):
        """Clientes por teléfono (se comparan los últimos 9 dígitos: "0981 111-222" y "595981111222"
        son el mismo), por documento (RUC con o sin dígito verificador, o cédula), o todos de a
        páginas con desde_id (los de id mayor, en orden; para importarlos al CRM)."""
        consulta = select(Cliente).where(Cliente.empresa_id == cred.empresa_id)
        if desde_id is not None:
            filas = (await db.execute(consulta.where(Cliente.id > desde_id).order_by(Cliente.id).limit(limite))).scalars().all()
            return {"items": [_cliente_publico(c) for c in filas], "cursor": filas[-1].id if filas else desde_id}
        if not (telefono and telefono.strip()) and not (documento and documento.strip()):
            raise HTTPException(status_code=400, detail="Indique telefono, documento o desde_id")
        if telefono and telefono.strip():
            digitos = re.sub(r"\D", "", telefono)[-9:]
            if len(digitos) < 6:
                raise HTTPException(status_code=400, detail="Teléfono demasiado corto")
            # Prefiltro en la base (los dígitos en orden, con cualquier separador) y control exacto acá
            consulta = consulta.where(Cliente.telefono.like("%" + "%".join(digitos) + "%"))
            candidatos = (await db.execute(consulta.limit(200))).scalars().all()
            encontrados = [c for c in candidatos if re.sub(r"\D", "", c.telefono or "").endswith(digitos)]
        else:
            doc = documento.strip()
            consulta = consulta.where(or_(Cliente.ruc == doc, Cliente.ruc.like(doc.split("-")[0] + "-%"),
                                          Cliente.cedula == doc))
            encontrados = (await db.execute(consulta.limit(50))).scalars().all()
        return {"items": [_cliente_publico(c) for c in encontrados]}

    class ClienteNuevo(BaseModel):
        nombre: str = Field(min_length=1, max_length=255)
        apellido: Optional[str] = Field(None, max_length=255)
        telefono: Optional[str] = Field(None, max_length=50)
        ruc: Optional[str] = Field(None, max_length=50)
        cedula: Optional[str] = Field(None, max_length=50)
        email: Optional[str] = Field(None, max_length=255)
        direccion: Optional[str] = Field(None, max_length=500)

    @router.post("/clientes")
    async def crear_cliente(
        data: ClienteNuevo,
        cred: Credencial = Depends(requiere_scope("clientes.escribir")),
        db: AsyncSession = Depends(get_db),
    ):
        """Crea un cliente (contacto nuevo del CRM). Con un RUC o cédula que ya existe responde 409 y
        el id del existente, para vincularlo en lugar de duplicarlo."""
        for campo in ("ruc", "cedula"):
            valor = getattr(data, campo)
            if valor and valor.strip():
                existente = (await db.execute(select(Cliente.id).where(
                    Cliente.empresa_id == cred.empresa_id, getattr(Cliente, campo) == valor.strip()))).scalar()
                if existente:
                    raise HTTPException(status_code=409, detail={"mensaje": f"Ya existe un cliente con ese {campo}",
                                                                 "cliente_id": existente})
        cliente = Cliente(empresa_id=cred.empresa_id,
                          **{k: (v.strip() if isinstance(v, str) else v) or None for k, v in data.model_dump().items()})
        cliente.nombre = data.nombre.strip()
        db.add(cliente)
        await db.commit()
        await db.refresh(cliente)
        return _cliente_publico(cliente)

    @router.get("/clientes/{cliente_id}/resumen-360")
    async def resumen_cliente(
        cliente_id: int,
        cred: Credencial = Depends(requiere_scope("clientes.leer")),
        db: AsyncSession = Depends(get_db),
    ):
        """Perfil del cliente para el CRM: compras, productos que más compra, últimas ventas,
        presupuestos, entregas pendientes y crédito (el crédito, sólo con permiso para verlo)."""
        cliente = await _cliente_de_la_empresa(db, cred, cliente_id)
        confirmadas = (Venta.cliente_id == cliente_id, Venta.estado == EstadoVenta.CONFIRMADA)
        total, cantidad, ultima = (await db.execute(
            select(func.coalesce(func.sum(Venta.total), 0), func.count(Venta.id), func.max(Venta.creado_en))
            .where(*confirmadas))).one()
        top = (await db.execute(
            select(Producto.id, Producto.nombre, func.sum(VentaItem.cantidad).label("unidades"))
            .join(Venta, VentaItem.venta_id == Venta.id).join(Producto, VentaItem.producto_id == Producto.id)
            .where(*confirmadas).group_by(Producto.id, Producto.nombre)
            .order_by(func.sum(VentaItem.cantidad).desc(), Producto.id).limit(5))).all()
        recientes = (await db.execute(
            select(Venta).where(Venta.cliente_id == cliente_id).order_by(Venta.creado_en.desc(), Venta.id.desc()).limit(5)
        )).scalars().all()
        presupuestos = (await db.execute(
            select(Presupuesto).where(Presupuesto.cliente_id == cliente_id)
            .order_by(Presupuesto.creado_en.desc(), Presupuesto.id.desc()).limit(5))).scalars().all()
        entregas = await db.scalar(
            select(func.count(Entrega.id)).join(Venta, Entrega.venta_id == Venta.id)
            .where(Venta.cliente_id == cliente_id, Entrega.estado != EstadoEntrega.ENTREGADO,
                   Entrega.estado != EstadoEntrega.CANCELADO))

        resumen = {
            "cliente": _cliente_publico(cliente),
            "compras": {
                "total": float(total or 0), "cantidad": cantidad,
                "ticket_promedio": round(float(total or 0) / cantidad, 0) if cantidad else 0,
                "ultima_compra": ultima.isoformat() if ultima else None,
            },
            "productos_mas_comprados": [{"producto_id": i, "nombre": n, "unidades": int(u)} for i, n, u in top],
            "ventas_recientes": [{"venta_id": v.id, "fecha": v.creado_en.isoformat() if v.creado_en else None,
                                  "total": float(v.total or 0), "estado": v.estado.value if v.estado else None}
                                 for v in recientes],
            "presupuestos_recientes": [{"presupuesto_id": p.id, "fecha": p.creado_en.isoformat() if p.creado_en else None,
                                        "total": float(p.total or 0)} for p in presupuestos],
            "entregas_pendientes": entregas or 0,
        }
        puede_ver_credito = cred.es_servicio or await tiene_algun_permiso(db, cred.usuario.id, ("clientes.ver_creditos",))
        if puede_ver_credito:
            usado = await db.scalar(select(func.coalesce(func.sum(CreditoCliente.monto_pendiente), 0)).where(
                CreditoCliente.cliente_id == cliente_id, CreditoCliente.pagado == False))
            limite = float(cliente.limite_credito or 0)
            resumen["credito"] = {"limite": limite, "usado": float(usado or 0),
                                  "disponible": max(0.0, limite - float(usado or 0))}
        return resumen

    # ---------- Métricas ----------
    @router.get("/metricas/ventas")
    async def metricas_ventas(
        desde: date,
        hasta: date,
        por: str = Query("dia", pattern="^(dia|semana|mes)$"),
        cliente_id: Optional[int] = None,
        cred: Credencial = Depends(requiere_scope("metricas.leer")),
        db: AsyncSession = Depends(get_db),
    ):
        """Ventas confirmadas por día, semana (lunes) o mes, en hora de Paraguay. Con cliente_id, sólo
        las de ese cliente (atribución de campañas). Hasta 366 días por consulta."""
        if hasta < desde or (hasta - desde).days > 366:
            raise HTTPException(status_code=400, detail="Rango inválido (hasta 366 días)")
        inicio = datetime.combine(desde, datetime.min.time(), PARAGUAY_TZ)
        fin = datetime.combine(hasta + timedelta(days=1), datetime.min.time(), PARAGUAY_TZ)
        filtros = [Venta.empresa_id == cred.empresa_id, Venta.estado == EstadoVenta.CONFIRMADA,
                   Venta.creado_en >= inicio, Venta.creado_en < fin]
        if cliente_id:
            filtros.append(Venta.cliente_id == cliente_id)
        filas = (await db.execute(select(Venta.creado_en, Venta.total).where(*filtros))).all()

        def periodo(momento: datetime) -> str:
            d = (momento.astimezone(PARAGUAY_TZ) if momento.tzinfo else momento).date()
            if por == "semana":
                return (d - timedelta(days=d.weekday())).isoformat()
            return d.isoformat()[:7] if por == "mes" else d.isoformat()
        series = {}
        for creado_en, monto in filas:
            p = series.setdefault(periodo(creado_en), {"total": 0.0, "cantidad": 0})
            p["total"] += float(monto or 0)
            p["cantidad"] += 1
        return {"por": por, "desde": desde.isoformat(), "hasta": hasta.isoformat(), "series": [
            {"periodo": k, "total": round(v["total"], 2), "cantidad": v["cantidad"],
             "ticket_promedio": round(v["total"] / v["cantidad"], 0)} for k, v in sorted(series.items())]}

    # ---------- Pedidos ----------
    class ItemPedido(BaseModel):
        producto_id: int
        cantidad: int = Field(gt=0, le=10000)

    class PedidoNuevo(BaseModel):
        cliente_id: int
        items: list[ItemPedido] = Field(min_length=1, max_length=100)
        tipo_pago: Literal["EFECTIVO", "TARJETA", "TRANSFERENCIA"] = "EFECTIVO"  # crédito: sólo un vendedor
        es_delivery: bool = False

    async def _pedido_publico(db: AsyncSession, pedido: PedidoIntegracion) -> dict:
        venta = await db.get(Venta, pedido.venta_id)
        items = (await db.execute(
            select(VentaItem.producto_id, Producto.nombre, VentaItem.cantidad, VentaItem.precio_unitario, VentaItem.total)
            .outerjoin(Producto, VentaItem.producto_id == Producto.id).where(VentaItem.venta_id == venta.id)
            .order_by(VentaItem.id))).all()
        return {
            "pedido_id": pedido.id, "venta_id": venta.id, "cliente_id": venta.cliente_id,
            "estado": venta.estado.value,  # PENDIENTE hasta que lo confirma un vendedor
            "tipo_pago": venta.tipo_pago.value if venta.tipo_pago else None, "es_delivery": bool(venta.es_delivery),
            "items": [{"producto_id": pid, "nombre": n, "cantidad": c, "precio_unitario": float(pu), "total": float(t)}
                      for pid, n, c, pu, t in items],
            "descuento": float(venta.descuento or 0), "total": float(venta.total or 0),
            "creado_en": pedido.creado_en.isoformat() if pedido.creado_en else None,
        }

    @router.post("/pedidos")
    async def crear_pedido(
        data: PedidoNuevo,
        request: Request,
        cred: Credencial = Depends(requiere_scope("pedidos.crear")),
        db: AsyncSession = Depends(get_db),
    ):
        """Crea un pedido como venta PENDIENTE que confirma un vendedor (D8, modo por defecto). Los
        precios los pone el ERP (precio de venta actual y el descuento del cliente); el pedido no
        trae precios ni descuentos. Encabezado Idempotency-Key obligatorio: repetir la misma clave
        devuelve el mismo pedido; la misma clave con otro pedido, 409."""
        clave = (request.headers.get("Idempotency-Key") or "").strip()
        if not clave or len(clave) > 100:
            raise HTTPException(status_code=400, detail="Encabezado Idempotency-Key obligatorio (hasta 100 caracteres)")
        huella = hashlib.sha256(data.model_dump_json().encode("utf-8")).hexdigest()

        async def existente():
            return (await db.execute(select(PedidoIntegracion).where(
                PedidoIntegracion.empresa_id == cred.empresa_id,
                PedidoIntegracion.clave_idempotencia == clave))).scalar_one_or_none()

        previo = await existente()
        if previo:
            if previo.huella != huella:
                raise HTTPException(status_code=409, detail="Esa Idempotency-Key ya se usó con otro pedido")
            return await _pedido_publico(db, previo)

        usuario_id = cred.usuario.id if cred.usuario else None
        if not usuario_id:
            raise HTTPException(status_code=400, detail="El token no tiene un usuario asignado para registrar pedidos")
        await _cliente_de_la_empresa(db, cred, data.cliente_id)
        ids = [i.producto_id for i in data.items]
        productos = {p.id: p for p in (await db.execute(select(Producto).where(
            Producto.id.in_(ids), Producto.empresa_id == cred.empresa_id, Producto.activo == True))).scalars().all()}
        faltan = sorted(set(ids) - set(productos))
        if faltan:
            raise HTTPException(status_code=400, detail={"mensaje": "Productos inexistentes o inactivos", "producto_ids": faltan})

        venta = await armar_venta(db, VentaCreate(
            empresa_id=cred.empresa_id, usuario_id=usuario_id, cliente_id=data.cliente_id, tipo_pago=data.tipo_pago,
            es_delivery=data.es_delivery,
            items=[VentaItemCreate(producto_id=i.producto_id, cantidad=i.cantidad,
                                   precio_unitario=productos[i.producto_id].precio_venta) for i in data.items],
        ), True)
        pedido = PedidoIntegracion(empresa_id=cred.empresa_id, clave_idempotencia=clave, huella=huella, venta_id=venta.id,
                                   token_id=cred.token.id if cred.token else None,
                                   usuario_id=None if cred.es_servicio else usuario_id)
        db.add(pedido)
        try:
            await db.commit()  # venta y pedido juntos: o se guardan los dos o ninguno
        except IntegrityError:
            # Otra petición con la misma clave ganó la carrera: devolver la suya
            await db.rollback()
            previo = await existente()
            if not previo or previo.huella != huella:
                raise HTTPException(status_code=409, detail="Esa Idempotency-Key ya se usó con otro pedido")
            return await _pedido_publico(db, previo)
        await db.refresh(pedido)
        return await _pedido_publico(db, pedido)

    @router.get("/pedidos/{pedido_id}")
    async def ver_pedido(
        pedido_id: int,
        cred: Credencial = Depends(requiere_scope("pedidos.leer")),
        db: AsyncSession = Depends(get_db),
    ):
        """Estado de un pedido. Un token de servicio sin clientes.leer (el bot) sólo ve los suyos."""
        pedido = await db.get(PedidoIntegracion, pedido_id)
        if not pedido or pedido.empresa_id != cred.empresa_id:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        if cred.es_servicio and "clientes.leer" not in (cred.token.scopes or []) and pedido.token_id != cred.token.id:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        return await _pedido_publico(db, pedido)

    # ---------- Eventos ----------
    @router.get("/eventos")
    async def eventos(
        desde: int = Query(0, ge=0, description="Último id ya procesado (cursor)"),
        limite: int = Query(100, ge=1, le=1000),
        cred: Credencial = Depends(requiere_scope("eventos.leer")),
        db: AsyncSession = Depends(get_db),
    ):
        """Eventos con id mayor a `desde`, en orden. Para seguir, pasar como `desde` el `cursor`
        devuelto. Llegan con unos segundos de retraso; procesarlos de forma idempotente por id."""
        hasta = datetime.now(timezone.utc) - timedelta(seconds=RETRASO_EVENTOS_SEGUNDOS)
        filas = (await db.execute(
            select(EventoIntegracion)
            .where(EventoIntegracion.empresa_id == cred.empresa_id, EventoIntegracion.id > desde,
                   EventoIntegracion.creado_en <= hasta)
            .order_by(EventoIntegracion.id).limit(limite)
        )).scalars().all()
        return {
            "eventos": [{"id": e.id, "tipo": e.tipo, "entidad_id": e.entidad_id, "datos": e.datos,
                         "creado_en": e.creado_en.isoformat()} for e in filas],
            "cursor": filas[-1].id if filas else desde,
        }

    return router


async def depurar_eventos(engine) -> int:
    """Borra los eventos de más de DIAS_DE_EVENTOS días (al arrancar el backend)."""
    limite = datetime.now(timezone.utc) - timedelta(days=DIAS_DE_EVENTOS)
    async with engine.begin() as conn:
        r = await conn.execute(delete(EventoIntegracion).where(EventoIntegracion.creado_en < limite))
    return r.rowcount or 0
