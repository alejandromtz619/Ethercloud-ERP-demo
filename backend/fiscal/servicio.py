"""
Ciclo de vida de los documentos electrónicos.

emitir:      valida con el proveedor (no consume número) → toma el número y guarda el documento
             POR_ENVIAR (commit) → lo envía. Si el envío se corta, el documento queda POR_ENVIAR con
             su número y su contenido exacto, y el seguimiento lo reenvía: el proveedor reconoce la
             numeración y devuelve el ya emitido, sin duplicarlo.
reemitir:    un documento INVALIDO o RECHAZADO se corrige y se manda de nuevo con el MISMO número.
seguir:      en segundo plano, reenvía los POR_ENVIAR y consulta los que van camino a SIFEN.
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Awaitable, Callable, Optional

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session_maker, engine
from fiscal import config, numerador
from fiscal.puerto import (
    ConflictoFiscal, CredencialFiscalInvalida, DocumentoInvalido, DocumentoNoEncontrado, EmisorFiscal, ErrorFiscal, ProveedorNoDisponible,
)
from models import PARAGUAY_TZ, AjusteSistema, DocumentoFiscal, Venta, now_paraguay

logger = logging.getLogger(__name__)

EN_CAMINO = ("GENERADO", "ENVIADO")
CORREGIBLES = ("INVALIDO", "RECHAZADO")
CANDADO_SEGUIMIENTO = 7_311_002_027
SEGUNDOS_CACHE_EMISOR = 600
CLAVE_EMISOR = "fiscal.emisor"  # últimos datos del emisor conocidos (ajustes_sistema)


def fecha_local() -> str:
    return datetime.now(PARAGUAY_TZ).strftime("%Y-%m-%dT%H:%M:%S")


def metadata(usuario=None) -> dict:
    """Quién emite, para la auditoría del proveedor."""
    nombre = " ".join(p for p in (getattr(usuario, "nombre", None), getattr(usuario, "apellido", None)) if p) or "Sistema"
    return {"deviceId": "ethercloud-erp", "deviceName": "ERP Ethercloud", "userId": str(getattr(usuario, "id", "sistema")),
            "userName": nombre, "app": "ethercloud-erp", "version": "1.0"}


class ServicioFiscal:
    def __init__(self, emisor: EmisorFiscal):
        self.emisor = emisor
        self._info: Optional[dict] = None
        self._info_vence = 0.0

    async def info(self, refrescar: bool = False) -> dict:
        """Datos del emisor en el proveedor (ambiente, establecimientos), guardados unos minutos. Si
        el proveedor no responde se usan los últimos conocidos (también guardados en la base): así se
        puede numerar y dejar el documento POR_ENVIAR aunque el proveedor esté caído."""
        if not refrescar and self._info is not None and time.monotonic() < self._info_vence:
            return self._info
        try:
            self._info = await self.emisor.emisor()
        except ProveedorNoDisponible:
            if self._info is None:
                async with async_session_maker() as db:
                    guardado = await db.get(AjusteSistema, CLAVE_EMISOR)
                if guardado is None:
                    raise
                self._info = guardado.valor
            if refrescar:
                raise
            return self._info
        self._info_vence = time.monotonic() + SEGUNDOS_CACHE_EMISOR
        async with async_session_maker() as db:
            fila = await db.get(AjusteSistema, CLAVE_EMISOR)
            if fila is None:
                db.add(AjusteSistema(clave=CLAVE_EMISOR, valor=self._info))
            elif fila.valor != self._info:
                fila.valor = self._info
            await db.commit()
        return self._info

    async def origen(self) -> tuple[str, str, str]:
        """(ambiente, establecimiento, punto) desde donde emite esta instancia."""
        info = await self.info()
        codigos = [e["codigo"] for e in info.get("establecimientos", [])]
        establecimiento = config.SIFEN_ESTABLECIMIENTO.zfill(3) if config.SIFEN_ESTABLECIMIENTO else (codigos or [""])[0]
        if establecimiento not in codigos:
            raise ErrorFiscal(f"El establecimiento {establecimiento or '(ninguno)'} no está configurado en SIFEN SIS "
                              f"(configurados: {', '.join(codigos) or 'ninguno'})")
        return info["ambiente"], establecimiento, config.SIFEN_PUNTO

    # ------------------------------------------------------------ emisión

    async def emitir(self, db: AsyncSession, *, empresa_id: int, tipo: int, contenido: dict, origen: str, total,
                     usuario=None, venta_id: Optional[int] = None, factura_grupal_id: Optional[int] = None,
                     documento_asociado_id: Optional[int] = None,
                     antes_de_numerar: Optional[Callable[[AsyncSession], Awaitable[None]]] = None) -> DocumentoFiscal:
        """Valida, numera, guarda y envía. DocumentoInvalido si el proveedor rechaza el contenido (no se
        consume ningún número). antes_de_numerar corre en la transacción de la numeración (p. ej. para
        bloquear la venta y verificar que nadie la facturó mientras tanto)."""
        ambiente, establecimiento, punto = await self.origen()
        data = {"tipoDocumento": tipo, "establecimiento": establecimiento, "punto": punto, "numero": 1,
                "fecha": fecha_local(), **contenido}
        try:
            await self.emisor.validar(data)
        except ProveedorNoDisponible as e:
            # Sin proveedor no se puede validar: se numera igual y el envío se reintenta solo
            logger.warning(f"Facturación: no se pudo validar antes de numerar ({e.mensaje})")
        if antes_de_numerar:
            await antes_de_numerar(db)
        data["numero"] = await numerador.siguiente_numero(db, empresa_id, ambiente, tipo, establecimiento, punto)
        doc = DocumentoFiscal(empresa_id=empresa_id, ambiente=ambiente, tipo_documento=tipo, establecimiento=establecimiento,
                              punto=punto, numero=data["numero"], origen=origen, venta_id=venta_id,
                              factura_grupal_id=factura_grupal_id, documento_asociado_id=documento_asociado_id,
                              estado="POR_ENVIAR", total=total, datos=data, usuario_id=getattr(usuario, "id", None))
        db.add(doc)
        await db.commit()  # el número queda guardado y se suelta el bloqueo de la secuencia
        return await self.enviar(db, doc, usuario)

    async def enviar(self, db: AsyncSession, doc: DocumentoFiscal, usuario=None, _renumerado: bool = False) -> DocumentoFiscal:
        doc.intentos = (doc.intentos or 0) + 1
        try:
            r = await self.emisor.emitir(doc.datos, metadata(usuario))
        except DocumentoInvalido as e:
            doc.estado, doc.mensaje, doc.respuesta = "INVALIDO", e.mensaje, e.respuesta
        except ConflictoFiscal as e:
            if _renumerado or doc.cdc:
                doc.mensaje, doc.respuesta = e.mensaje, e.respuesta
            else:
                # Ese número ya lo tiene otro documento en el proveedor (p. ej. se restauró un respaldo
                # del ERP): se adelanta la numeración y se usa el siguiente libre
                logger.warning(f"Facturación: número {doc.numero} ocupado en el proveedor, se renumera ({e.mensaje})")
                await self._renumerar(db, doc)
                return await self.enviar(db, doc, usuario, _renumerado=True)
        except (ProveedorNoDisponible, CredencialFiscalInvalida) as e:
            doc.mensaje = e.mensaje  # sigue POR_ENVIAR: el seguimiento lo reintenta
        else:
            doc.cdc, doc.estado, doc.respuesta = r.cdc, r.estado, r.respuesta
            doc.mensaje = "; ".join(r.advertencias) or None
            if r.estado == "APROBADO":
                doc.aprobado_en = now_paraguay()
            if doc.venta_id:
                await db.execute(update(Venta).where(Venta.id == doc.venta_id).values(facturada=True))
        await db.commit()
        return doc

    async def _renumerar(self, db: AsyncSession, doc: DocumentoFiscal) -> None:
        await numerador.sincronizar(db, doc.empresa_id, doc.ambiente, await self.emisor.numeracion())
        numero = await numerador.siguiente_numero(db, doc.empresa_id, doc.ambiente, doc.tipo_documento,
                                                  doc.establecimiento, doc.punto)
        doc.numero = numero
        doc.datos = {**doc.datos, "numero": numero}
        await db.commit()

    async def reemitir(self, db: AsyncSession, doc: DocumentoFiscal, contenido: dict, total, usuario=None) -> DocumentoFiscal:
        """Manda de nuevo un documento INVALIDO o RECHAZADO, corregido, con el mismo número."""
        if doc.estado not in CORREGIBLES:
            raise ConflictoFiscal(f"Sólo se reemite un documento inválido o rechazado (este está {doc.estado})")
        data = {"tipoDocumento": doc.tipo_documento, "establecimiento": doc.establecimiento, "punto": doc.punto,
                "numero": doc.numero, "fecha": fecha_local(), **contenido}
        try:
            await self.emisor.validar(data)
        except ProveedorNoDisponible:
            pass
        doc.datos, doc.total, doc.estado, doc.cdc, doc.mensaje = data, total, "POR_ENVIAR", None, None
        await db.commit()
        return await self.enviar(db, doc, usuario)

    async def actualizar_estado(self, db: AsyncSession, doc: DocumentoFiscal) -> DocumentoFiscal:
        if not doc.cdc:
            return doc
        e = await self.emisor.estado(doc.cdc)
        doc.estado, doc.respuesta = e.estado, e.respuesta
        if e.estado == "RECHAZADO":
            doc.mensaje = e.mensaje or e.codigo or "Rechazado por SIFEN"
        elif e.estado == "APROBADO" and not doc.aprobado_en:
            doc.aprobado_en = now_paraguay()
            doc.mensaje = None
        await db.commit()
        return doc

    async def sincronizar_numeracion(self, db: AsyncSession, empresa_id: int) -> list:
        ambiente, _, _ = await self.origen()
        return await numerador.sincronizar(db, empresa_id, ambiente, await self.emisor.numeracion())

    # ------------------------------------------------------------ seguimiento en segundo plano

    async def una_vuelta(self, db: AsyncSession) -> dict:
        """Reenvía los POR_ENVIAR y consulta los que van camino a SIFEN (los más atrasados primero)."""
        cupo = config.CONSULTAS_POR_VUELTA
        enviados = consultados = 0
        pendientes = (await db.execute(select(DocumentoFiscal).where(DocumentoFiscal.estado == "POR_ENVIAR")
                                       .order_by(DocumentoFiscal.actualizado_en).limit(cupo // 2))).scalars().all()
        for doc in pendientes:
            await self.enviar(db, doc)
            enviados += 1
            if doc.estado == "POR_ENVIAR":  # el proveedor sigue sin responder: se prueba en la próxima vuelta
                return {"enviados": enviados, "consultados": 0}
        en_camino = (await db.execute(select(DocumentoFiscal).where(DocumentoFiscal.estado.in_(EN_CAMINO))
                                      .order_by(DocumentoFiscal.actualizado_en).limit(cupo - enviados))).scalars().all()
        for doc in en_camino:
            try:
                await self.actualizar_estado(db, doc)
            except DocumentoNoEncontrado as e:
                # Se anota y pasa al final de la fila: no frena el seguimiento de los demás
                doc.mensaje, doc.actualizado_en = e.mensaje, now_paraguay()
                await db.commit()
            except ProveedorNoDisponible as e:
                logger.warning(f"Facturación: no se pudo consultar {doc.cdc}: {e.mensaje}")
                await db.rollback()
                break
            consultados += 1
        return {"enviados": enviados, "consultados": consultados}

    async def seguir(self) -> None:
        """Seguimiento cada SEGUNDOS_SEGUIMIENTO. Con varios procesos lo corre uno solo (candado)."""
        es_postgres = engine.dialect.name == "postgresql"
        while True:
            conexion = None
            try:
                if es_postgres:
                    conexion = await engine.connect()
                    tengo = (await conexion.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": CANDADO_SEGUIMIENTO})).scalar()
                    await conexion.commit()  # el candado es de sesión; no dejar una transacción abierta
                    if not tengo:
                        await conexion.close()
                        conexion = None
                        await asyncio.sleep(60)
                        continue
                while True:
                    try:
                        async with async_session_maker() as db:
                            await self.una_vuelta(db)
                    except Exception:
                        logger.exception("Facturación: error en el seguimiento de documentos")
                    await asyncio.sleep(config.SEGUNDOS_SEGUIMIENTO)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Facturación: el seguimiento se reinicia")
                await asyncio.sleep(30)
            finally:
                if conexion is not None:
                    await conexion.close()
