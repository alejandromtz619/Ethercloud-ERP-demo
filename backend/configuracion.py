"""
Configuración de la instancia: lo que cambia de un cliente a otro y se carga desde la pantalla
Configuración, sin tocar código ni recompilar (plan: PLAN_CONFIGURACION_POR_INSTANCIA.md).

Dónde vive cada dato:
- Infraestructura (variables de entorno que carga Ether al crear la instancia): base, JWT_SECRET,
  CLAVE_CIFRADO, MODULOS. No pasa por acá.
- Configuración del cliente: acá. Cada clave se declara en CLAVES (tipo, valor por defecto, si es
  secreta, qué variable de entorno la pisa, qué permiso la edita) y se guarda en ajustes_sistema
  como "config.<clave>".
- Datos de la empresa (razón social, RUC...): tabla empresas, como siempre.

Orden de lectura: variable de entorno (si existe, gana y la pantalla la muestra como "fijada en el
servidor") → valor guardado → valor por defecto.

Secretos (API keys): se cifran con Fernet usando CLAVE_CIFRADO (una por instancia, no se deriva de
JWT_SECRET: rotar el JWT dejaría ilegibles las claves). La API nunca los devuelve, sólo si están
cargados y sus últimos 4 caracteres.
"""
import base64
import hashlib
import os
import re
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Awaitable, Callable, Optional

from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session_maker, get_db
from models import AjusteSistema, CambioConfiguracion, Usuario

PREFIJO = "config."
SEGUNDOS_CACHE = 30  # con varios procesos, un cambio se ve en los demás en hasta 30 s
LARGO_MINIMO_CLAVE_CIFRADO = 32


class ConfiguracionInvalida(ValueError):
    """Un valor que no pasa la validación de su clave."""


# ---------------------------------------------------------------- validadores

def texto(minimo: int = 0, maximo: int = 255) -> Callable[[Any], str]:
    def _validar(valor) -> str:
        valor = str(valor or "").strip()
        if not minimo <= len(valor) <= maximo:
            raise ConfiguracionInvalida(f"debe tener entre {minimo} y {maximo} caracteres")
        return valor
    return _validar


def codigo_numerico(digitos: int, opcional: bool = False) -> Callable[[Any], str]:
    def _validar(valor) -> str:
        valor = str(valor or "").strip()
        if not valor and opcional:
            return ""
        if not re.fullmatch(rf"\d{{1,{digitos}}}", valor):
            raise ConfiguracionInvalida(f"debe ser un número de hasta {digitos} dígitos")
        return valor.zfill(digitos)
    return _validar


def decimal_entre(minimo: float, maximo: float) -> Callable[[Any], float]:
    def _validar(valor) -> float:
        try:
            numero = Decimal(str(valor).replace(",", "."))
        except (InvalidOperation, ValueError):
            raise ConfiguracionInvalida("debe ser un número")
        if not Decimal(str(minimo)) <= numero <= Decimal(str(maximo)):
            raise ConfiguracionInvalida(f"debe estar entre {minimo} y {maximo}")
        return float(numero)
    return _validar


# ---------------------------------------------------------------- claves

@dataclass(frozen=True)
class Clave:
    nombre: str
    seccion: str
    etiqueta: str
    tipo: str = "texto"                  # texto | decimal (para la pantalla)
    defecto: Any = None
    secreta: bool = False
    entorno: Optional[str] = None        # variable de entorno que la pisa
    permiso: str = "sistema.configurar"  # quién la edita (los administradores, siempre)
    validar: Callable[[Any], Any] = texto()
    ayuda: str = ""


# sección -> (título, módulo de MODULOS que la habilita; None = siempre)
SECCIONES = {
    "documentos": ("Documentos impresos", None),
    "facturacion_electronica": ("Facturación electrónica (SIFEN)", "fe"),
    "laboratorio": ("Laboratorio", None),
}

CLAVES = {c.nombre: c for c in (
    Clave("documentos.ciudad_factura", "documentos", "Ciudad que se imprime en la factura", defecto="",
          validar=texto(0, 60), ayuda="Va junto a la fecha en la factura pre-impresa"),
    Clave("documentos.ajuste_x_mm", "documentos", "Corrimiento horizontal de la factura en papel (mm)", tipo="decimal",
          defecto=0.0, validar=decimal_entre(-30, 30), ayuda="Si lo impreso no cae en los casilleros: positivo mueve todo a la derecha"),
    Clave("documentos.ajuste_y_mm", "documentos", "Corrimiento vertical de la factura en papel (mm)", tipo="decimal",
          defecto=0.0, validar=decimal_entre(-30, 30), ayuda="Positivo mueve todo hacia abajo"),
    Clave("fe.api_key", "facturacion_electronica", "API key de SIFEN SIS", secreta=True, entorno="SIFENSIS_API_KEY",
          permiso="sistema.integraciones", validar=texto(10, 200),
          ayuda="Se crea en el portal de SIFEN SIS. El ambiente (SANDBOX, HOMOLOGACION o PRODUCCION) lo define la key"),
    Clave("fe.establecimiento", "facturacion_electronica", "Establecimiento", defecto="", entorno="SIFEN_ESTABLECIMIENTO",
          permiso="sistema.integraciones", validar=codigo_numerico(3, opcional=True),
          ayuda="Vacío = el primero configurado en SIFEN SIS"),
    Clave("fe.punto", "facturacion_electronica", "Punto de expedición", defecto="001", entorno="SIFEN_PUNTO",
          permiso="sistema.integraciones", validar=codigo_numerico(3),
          ayuda="Uno distinto por cada sistema que emita con el mismo RUC"),
    Clave("fe.plazo_credito", "facturacion_electronica", "Plazo de las ventas a crédito", defecto="30 días",
          entorno="SIFEN_PLAZO_CREDITO", validar=texto(2, 15), ayuda="Se informa en las facturas a crédito"),
    Clave("laboratorio.margen", "laboratorio", "Margen de ganancia del laboratorio", tipo="decimal", defecto=0.30,
          entorno="LAB_MARGEN_GANANCIA", validar=decimal_entre(0, 0.95),
          ayuda="Fracción del precio que es ganancia (0,30 = 30 %); el resto es costo"),
)}


# ---------------------------------------------------------------- cifrado

def _fernet() -> Optional[Fernet]:
    clave = os.environ.get("CLAVE_CIFRADO", "").strip()
    if len(clave) < LARGO_MINIMO_CLAVE_CIFRADO:
        return None
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(clave.encode("utf-8")).digest()))


def cifrado_disponible() -> bool:
    return _fernet() is not None


def _cifrar(valor: str) -> str:
    fernet = _fernet()
    if fernet is None:
        raise ConfiguracionInvalida(f"falta CLAVE_CIFRADO en el servidor (mínimo {LARGO_MINIMO_CLAVE_CIFRADO} caracteres) "
                                    "para guardar claves secretas")
    return fernet.encrypt(valor.encode("utf-8")).decode("ascii")


def _descifrar(token: str) -> Optional[str]:
    fernet = _fernet()
    if fernet is None:
        return None
    try:
        return fernet.decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:  # se cambió CLAVE_CIFRADO: hay que volver a cargar el secreto
        return None


def _enmascarar(valor: Optional[str]) -> Optional[str]:
    return None if valor is None else f"…{valor[-4:]}" if len(valor) > 4 else "…"


# ---------------------------------------------------------------- lectura

_cache: dict = {}
_cache_vence = 0.0


def invalidar_cache() -> None:
    global _cache_vence
    _cache_vence = 0.0


async def _guardados() -> dict:
    """Filas config.* de ajustes_sistema (crudas: los secretos, cifrados), con caché."""
    global _cache, _cache_vence
    if time.monotonic() >= _cache_vence:
        async with async_session_maker() as db:
            filas = (await db.execute(select(AjusteSistema).where(AjusteSistema.clave.like(PREFIJO + "%")))).scalars().all()
        _cache = {f.clave[len(PREFIJO):]: f.valor for f in filas}
        _cache_vence = time.monotonic() + SEGUNDOS_CACHE
    return _cache


def _de_entorno(clave: Clave) -> Optional[str]:
    if clave.entorno:
        valor = os.environ.get(clave.entorno, "").strip()
        if valor:
            return valor
    return None


async def obtener(nombre: str) -> Any:
    """Valor vigente de una clave (los secretos, descifrados): entorno → guardado → defecto."""
    clave = CLAVES[nombre]
    entorno = _de_entorno(clave)
    if entorno is not None:
        try:
            return clave.validar(entorno)
        except ConfiguracionInvalida:
            return entorno
    guardado = (await _guardados()).get(nombre)
    if guardado is not None:
        if clave.secreta:
            return _descifrar(guardado.get("cifrado", ""))
        return guardado.get("v")
    return clave.defecto


async def describir(nombre: str, usuario_puede: Callable[[str], bool]) -> dict:
    """Cómo se muestra una clave en la pantalla (nunca el valor de un secreto)."""
    clave = CLAVES[nombre]
    entorno = _de_entorno(clave)
    guardado = (await _guardados()).get(nombre)
    origen = "entorno" if entorno is not None else "guardado" if guardado is not None else "defecto"
    datos = {"clave": nombre, "etiqueta": clave.etiqueta, "tipo": clave.tipo, "ayuda": clave.ayuda,
             "secreta": clave.secreta, "origen": origen,
             "editable": origen != "entorno" and usuario_puede(clave.permiso)}
    if clave.secreta:
        valor = await obtener(nombre)
        datos["configurado"] = bool(valor)
        datos["termina_en"] = _enmascarar(valor) if valor else None
        datos["ilegible"] = origen == "guardado" and valor is None  # cambió CLAVE_CIFRADO
    else:
        datos["valor"] = await obtener(nombre)
        datos["defecto"] = clave.defecto
    return datos


# ---------------------------------------------------------------- escritura

async def guardar(db: AsyncSession, valores: dict, usuario_id: Optional[int]) -> list:
    """Valida y guarda {clave: valor}. None vuelve al valor por defecto (o borra el secreto).
    Deja un registro por cambio. Lanza ConfiguracionInvalida (con la clave en el mensaje) sin guardar
    nada si algún valor no sirve. Hace commit."""
    invalidar_cache()  # el valor anterior (para el registro) se lee de la base, no de la caché
    preparados = []
    for nombre, valor in valores.items():
        clave = CLAVES.get(nombre)
        if clave is None:
            raise ConfiguracionInvalida(f"{nombre}: clave desconocida")
        if _de_entorno(clave) is not None:
            raise ConfiguracionInvalida(f"{nombre}: está fijada en el servidor ({clave.entorno}) y no se puede cambiar acá")
        try:
            normalizado = None if valor is None else clave.validar(valor)
        except ConfiguracionInvalida as e:
            raise ConfiguracionInvalida(f"{clave.etiqueta}: {e}")
        preparados.append((clave, normalizado))

    cambios = []
    for clave, valor in preparados:
        fila = await db.get(AjusteSistema, PREFIJO + clave.nombre)
        anterior = await obtener(clave.nombre)
        if valor is None:
            if fila is None:
                continue  # ya estaba en el valor por defecto: no hay cambio que registrar
            await db.delete(fila)
            nuevo_visible = None if clave.secreta else clave.defecto
        else:
            almacenado = {"cifrado": _cifrar(valor)} if clave.secreta else {"v": valor}
            if fila is None:
                db.add(AjusteSistema(clave=PREFIJO + clave.nombre, valor=almacenado))
            else:
                fila.valor = almacenado
            nuevo_visible = valor
        if anterior == nuevo_visible:
            continue
        if clave.secreta:
            antes, despues = _enmascarar(anterior), _enmascarar(nuevo_visible) if nuevo_visible else "(quitada)"
        else:
            antes, despues = (None if anterior is None else str(anterior)), (None if nuevo_visible is None else str(nuevo_visible))
        db.add(CambioConfiguracion(clave=clave.nombre, valor_anterior=antes, valor_nuevo=despues, usuario_id=usuario_id))
        cambios.append(clave.nombre)
    await db.commit()
    invalidar_cache()
    return cambios


# ---------------------------------------------------------------- rutas

PERMISOS_LECTURA = ("sistema.configurar", "sistema.integraciones")
# Prueba de conexión por sección (la registra cada módulo, p. ej. facturación electrónica)
PROBADORES: dict[str, Callable[[Request], Awaitable[dict]]] = {}


class Cambios(BaseModel):
    valores: dict[str, Any]


def crear_router(usuario_desde_jwt: Callable, tiene_algun_permiso: Callable, modulos_activos: set) -> APIRouter:
    """modulos_activos: el conjunto MODULOS de la instancia (las secciones de un módulo no contratado no
    se muestran)."""
    router = APIRouter(prefix="/api/configuracion", tags=["configuración"])

    def visibles() -> dict:
        return {s: t for s, (t, modulo) in SECCIONES.items() if modulo is None or modulo in modulos_activos}

    async def autenticar(request: Request, db: AsyncSession = Depends(get_db)) -> tuple:
        encabezado = request.headers.get("Authorization", "")
        if not encabezado.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Sesión requerida")
        usuario = await usuario_desde_jwt(encabezado[7:].strip(), db)
        permisos = {p for p in PERMISOS_LECTURA if await tiene_algun_permiso(db, usuario.id, (p,))}
        if not permisos:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver la configuración")
        return usuario, permisos

    @router.get("/impresion")
    async def impresion(request: Request, db: AsyncSession = Depends(get_db)):
        """Lo que necesita la impresión de la factura en papel. Lo usa cualquier persona que imprime
        (cajeros), por eso no pide permisos de configuración, sólo sesión."""
        encabezado = request.headers.get("Authorization", "")
        if not encabezado.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Sesión requerida")
        await usuario_desde_jwt(encabezado[7:].strip(), db)
        return {"ciudad_factura": await obtener("documentos.ciudad_factura"),
                "ajuste_x_mm": await obtener("documentos.ajuste_x_mm"),
                "ajuste_y_mm": await obtener("documentos.ajuste_y_mm")}

    @router.get("")
    async def ver(sesion: tuple = Depends(autenticar)):
        """Todas las secciones con sus valores (sin secretos) y qué puede editar la persona."""
        _, permisos = sesion
        secciones = []
        for seccion, titulo in visibles().items():
            campos = [await describir(c.nombre, lambda p: p in permisos) for c in CLAVES.values() if c.seccion == seccion]
            secciones.append({"seccion": seccion, "titulo": titulo, "campos": campos,
                              "se_puede_probar": seccion in PROBADORES})
        return {"secciones": secciones, "cifrado_disponible": cifrado_disponible()}

    @router.put("/{seccion}")
    async def cambiar(seccion: str, datos: Cambios, sesion: tuple = Depends(autenticar), db: AsyncSession = Depends(get_db)):
        usuario, permisos = sesion
        if seccion not in visibles():
            raise HTTPException(status_code=404, detail="Sección desconocida")
        for nombre in datos.valores:
            clave = CLAVES.get(nombre)
            if clave is None or clave.seccion != seccion:
                raise HTTPException(status_code=422, detail=f"{nombre}: no es una clave de esta sección")
            if clave.permiso not in permisos:
                raise HTTPException(status_code=403, detail=f"{clave.etiqueta}: no tiene permiso para cambiarla")
        try:
            cambios = await guardar(db, datos.valores, usuario.id)
        except ConfiguracionInvalida as e:
            raise HTTPException(status_code=422, detail=str(e))
        return {"cambios": cambios,
                "campos": [await describir(c.nombre, lambda p: p in permisos) for c in CLAVES.values() if c.seccion == seccion]}

    @router.post("/{seccion}/probar")
    async def probar(seccion: str, request: Request, sesion: tuple = Depends(autenticar)):
        """Prueba la conexión con lo configurado en la sección (p. ej. la API key de SIFEN SIS)."""
        if seccion not in PROBADORES or seccion not in visibles():
            raise HTTPException(status_code=404, detail="Esta sección no tiene prueba de conexión")
        return await PROBADORES[seccion](request)

    @router.get("/cambios")
    async def historial(limit: int = Query(100, ge=1, le=500), sesion: tuple = Depends(autenticar),
                        db: AsyncSession = Depends(get_db)):
        """Quién cambió qué y cuándo (los secretos, enmascarados)."""
        filas = (await db.execute(select(CambioConfiguracion, Usuario.nombre, Usuario.apellido)
                                  .outerjoin(Usuario, Usuario.id == CambioConfiguracion.usuario_id)
                                  .order_by(CambioConfiguracion.id.desc()).limit(limit))).all()
        return [{"clave": c.clave, "etiqueta": CLAVES[c.clave].etiqueta if c.clave in CLAVES else c.clave,
                 "valor_anterior": c.valor_anterior, "valor_nuevo": c.valor_nuevo,
                 "usuario": " ".join(p for p in (nombre, apellido) if p) or None,
                 "creado_en": c.creado_en.isoformat() if c.creado_en else None} for c, nombre, apellido in filas]

    return router
