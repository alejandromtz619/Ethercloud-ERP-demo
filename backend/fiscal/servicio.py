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
import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Optional

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

import configuracion
from database import async_session_maker, engine
from fiscal import config, constructor, numerador
from fiscal.puerto import (
    ConflictoFiscal, CredencialFiscalInvalida, DocumentoInvalido, DocumentoNoEncontrado, EmisorFiscal, ErrorFiscal, ProveedorNoDisponible,
)
from fiscal.sifensis import SifenSis
from models import PARAGUAY_TZ, AjusteSistema, DocumentoFiscal, EventoFiscal, Venta, now_paraguay

logger = logging.getLogger(__name__)

EN_CAMINO = ("GENERADO", "ENVIADO")
# Plazo para cancelar desde la aprobación (Manual Técnico de SIFEN): 48 h facturas, 168 h el resto. Se deja
# una hora de margen; si igual SIFEN dice que venció, se hace la nota de crédito.
PLAZO_CANCELACION = {1: timedelta(hours=47)}
PLAZO_CANCELACION_OTROS = timedelta(hours=167)
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
    def __init__(self, emisor: EmisorFiscal, identidad: str = ""):
        """identidad: huella de la API key. Los últimos datos del emisor se guardan por key, así al
        pasar de SANDBOX a PRODUCCION nunca se numera con los datos del ambiente anterior."""
        self.emisor = emisor
        self._info: Optional[dict] = None
        self._info_vence = 0.0
        self._clave_emisor = f"{CLAVE_EMISOR}.{identidad}" if identidad else CLAVE_EMISOR

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
                    guardado = await db.get(AjusteSistema, self._clave_emisor)
                if guardado is None:
                    raise
                self._info = guardado.valor
            if refrescar:
                raise
            return self._info
        self._info_vence = time.monotonic() + SEGUNDOS_CACHE_EMISOR
        async with async_session_maker() as db:
            fila = await db.get(AjusteSistema, self._clave_emisor)
            if fila is None:
                db.add(AjusteSistema(clave=self._clave_emisor, valor=self._info))
            elif fila.valor != self._info:
                fila.valor = self._info
            await db.commit()
        return self._info

    async def origen(self) -> tuple[str, str, str]:
        """(ambiente, establecimiento, punto) desde donde emite esta instancia."""
        info = await self.info()
        codigos = [e["codigo"] for e in info.get("establecimientos", [])]
        establecimiento = await configuracion.obtener("fe.establecimiento") or (codigos or [""])[0]
        if establecimiento not in codigos:
            raise ErrorFiscal(f"El establecimiento {establecimiento or '(ninguno)'} no está configurado en SIFEN SIS "
                              f"(configurados: {', '.join(codigos) or 'ninguno'})")
        return info["ambiente"], establecimiento, await configuracion.obtener("fe.punto")

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

    # ------------------------------------------------------------ eventos y notas (etapa 2.3)

    async def _evento(self, db: AsyncSession, *, doc: Optional[DocumentoFiscal], tipo: str, tipo_documento: int,
                      establecimiento: str, punto: str, desde: int, hasta: int, motivo: str, resultado, usuario,
                      ambiente: str, empresa_id: int) -> EventoFiscal:
        evento = EventoFiscal(empresa_id=empresa_id, ambiente=ambiente, tipo=tipo, documento_id=getattr(doc, "id", None),
                              tipo_documento=tipo_documento, establecimiento=establecimiento, punto=punto, desde=desde,
                              hasta=hasta, motivo=motivo, estado=resultado.estado or "RECHAZADO", mensaje=resultado.mensaje,
                              respuesta=resultado.respuesta, usuario_id=getattr(usuario, "id", None))
        db.add(evento)
        return evento

    def dentro_del_plazo(self, doc: DocumentoFiscal) -> bool:
        if not doc.aprobado_en:
            return True  # que lo decida SIFEN
        aprobado = doc.aprobado_en if doc.aprobado_en.tzinfo else doc.aprobado_en.replace(tzinfo=timezone.utc)
        plazo = PLAZO_CANCELACION.get(doc.tipo_documento, PLAZO_CANCELACION_OTROS)
        return datetime.now(timezone.utc) - aprobado < plazo

    async def cancelar(self, db: AsyncSession, doc: DocumentoFiscal, motivo: str, usuario=None) -> EventoFiscal:
        """Evento de cancelación de un documento APROBADO (dentro del plazo). Si SIFEN lo aprueba, el
        documento queda CANCELADO y, si era la factura de una venta, la venta se puede volver a facturar."""
        if doc.estado != "APROBADO" or not doc.cdc:
            raise ConflictoFiscal(f"Sólo se cancela un documento aprobado (este está {doc.estado})")
        r = await self.emisor.cancelar(doc.cdc, motivo, metadata(usuario))
        evento = await self._evento(db, doc=doc, tipo="cancelacion", tipo_documento=doc.tipo_documento,
                                    establecimiento=doc.establecimiento, punto=doc.punto, desde=doc.numero, hasta=doc.numero,
                                    motivo=motivo, resultado=r, usuario=usuario, ambiente=doc.ambiente, empresa_id=doc.empresa_id)
        if r.estado == "APROBADO":
            doc.estado, doc.mensaje = "CANCELADO", f"Cancelado: {motivo}"
            if doc.venta_id and doc.tipo_documento == 1:
                await db.execute(update(Venta).where(Venta.id == doc.venta_id).values(facturada=False))
        await db.commit()
        return evento

    async def inutilizar(self, db: AsyncSession, doc: DocumentoFiscal, motivo: str, usuario=None) -> EventoFiscal:
        """Inutiliza el número de un documento que no llegó a valer (inválido, rechazado o sin enviar) y no
        se va a reemitir. El número queda marcado ante SIFEN como no usado."""
        if doc.estado not in ("INVALIDO", "RECHAZADO", "POR_ENVIAR"):
            raise ConflictoFiscal(f"Sólo se inutiliza el número de un documento inválido o rechazado (este está {doc.estado})")
        if doc.estado == "POR_ENVIAR" and doc.cdc:
            raise ConflictoFiscal("El documento puede haber llegado al proveedor: reintentá el envío antes de inutilizarlo")
        r = await self.emisor.inutilizar(doc.tipo_documento, doc.establecimiento, doc.punto, doc.numero, doc.numero,
                                         motivo, metadata(usuario))
        evento = await self._evento(db, doc=doc, tipo="inutilizacion", tipo_documento=doc.tipo_documento,
                                    establecimiento=doc.establecimiento, punto=doc.punto, desde=doc.numero, hasta=doc.numero,
                                    motivo=motivo, resultado=r, usuario=usuario, ambiente=doc.ambiente, empresa_id=doc.empresa_id)
        if r.estado == "APROBADO":
            doc.estado, doc.mensaje = "INUTILIZADO", f"Número inutilizado: {motivo}"
            if doc.venta_id and doc.tipo_documento == 1:
                await db.execute(update(Venta).where(Venta.id == doc.venta_id).values(facturada=False))
        await db.commit()
        return evento

    async def inutilizar_rango(self, db: AsyncSession, empresa_id: int, tipo_documento: int, desde: int, hasta: int,
                               motivo: str, usuario=None) -> EventoFiscal:
        """Números salteados (de este establecimiento y punto) que no tienen documento."""
        ambiente, establecimiento, punto = await self.origen()
        r = await self.emisor.inutilizar(tipo_documento, establecimiento, punto, desde, hasta, motivo, metadata(usuario))
        evento = await self._evento(db, doc=None, tipo="inutilizacion", tipo_documento=tipo_documento,
                                    establecimiento=establecimiento, punto=punto, desde=desde, hasta=hasta, motivo=motivo,
                                    resultado=r, usuario=usuario, ambiente=ambiente, empresa_id=empresa_id)
        await db.commit()
        return evento

    async def nota_de_credito(self, db: AsyncSession, factura: DocumentoFiscal, motivo: int = 2, usuario=None) -> DocumentoFiscal:
        """Nota de crédito electrónica por el total de una factura aprobada (con su CDC como documento asociado)."""
        if factura.tipo_documento != 1 or factura.estado != "APROBADO":
            raise ConflictoFiscal("La nota de crédito se hace sobre una factura aprobada")
        numero = f"{factura.establecimiento}-{factura.punto}-{factura.numero:07d}"
        contenido = constructor.nota_de_credito_total(factura.datos, factura.cdc, numero, motivo)
        return await self.emitir(db, empresa_id=factura.empresa_id, tipo=5, contenido=contenido, origen="nota_credito",
                                 total=factura.total, usuario=usuario, venta_id=factura.venta_id,
                                 factura_grupal_id=factura.factura_grupal_id, documento_asociado_id=factura.id)

    async def regularizar_anulacion(self, db: AsyncSession, factura: DocumentoFiscal, motivo: str, usuario=None) -> str:
        """Al anular en el ERP una venta con factura electrónica: dentro del plazo se cancela; si no (o si
        SIFEN dice que venció), nota de crédito por el total. Una factura que no llegó a valer se inutiliza.
        Devuelve el texto para mostrar."""
        numero = f"{factura.establecimiento}-{factura.punto}-{factura.numero:07d}"
        if factura.estado == "APROBADO":
            if self.dentro_del_plazo(factura):
                try:
                    evento = await self.cancelar(db, factura, motivo, usuario)
                    if evento.estado == "APROBADO":
                        return f"La factura electrónica {numero} se canceló en SIFEN"
                except ConflictoFiscal:
                    pass  # plazo vencido según SIFEN (no se escribió nada): va la nota de crédito
            nota = await self.nota_de_credito(db, factura, 2, usuario)
            if nota.estado == "INVALIDO":
                return f"No se pudo emitir la nota de crédito de la factura {numero}: {nota.mensaje}"
            return f"Se emitió la nota de crédito electrónica {nota.establecimiento}-{nota.punto}-{nota.numero:07d} por la factura {numero}"
        if factura.estado in ("INVALIDO", "RECHAZADO"):
            evento = await self.inutilizar(db, factura, motivo, usuario)
            return f"El número {numero} se inutilizó en SIFEN" if evento.estado == "APROBADO" else \
                f"No se pudo inutilizar el número {numero}: {evento.mensaje}"
        return ""

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


class FacturacionElectronica:
    """El servicio fiscal vigente según la configuración. Si se carga o se cambia la API key en
    Sistema › Configuración, el próximo uso ya trabaja con la nueva, sin reiniciar el servidor (con
    varios procesos, en hasta 30 s: la caché de configuracion.py)."""

    def __init__(self, fabrica: Optional[Callable[[str], EmisorFiscal]] = None, fijo: Optional[ServicioFiscal] = None):
        self._fabrica = fabrica or (lambda api_key: SifenSis(api_key=api_key))
        self._fijo = fijo          # las pruebas inyectan un servicio con el emisor falso
        self._huella: Optional[str] = None
        self._servicio: Optional[ServicioFiscal] = None

    async def servicio(self) -> Optional[ServicioFiscal]:
        """None si todavía no se cargó la API key."""
        if self._fijo is not None:
            return self._fijo
        api_key = await configuracion.obtener("fe.api_key")
        if not api_key:
            return None
        huella = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]
        if huella != self._huella:
            anterior = self._servicio
            self._servicio, self._huella = ServicioFiscal(self._fabrica(api_key), identidad=huella), huella
            if anterior is not None and hasattr(anterior.emisor, "cerrar"):
                asyncio.create_task(anterior.emisor.cerrar())
        return self._servicio

    async def seguir(self) -> None:
        """Seguimiento cada SEGUNDOS_SEGUIMIENTO. Con varios procesos lo corre uno solo (candado).
        Sin API key cargada no hace nada y vuelve a mirar en la vuelta siguiente."""
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
                        servicio = await self.servicio()
                        if servicio is not None:
                            async with async_session_maker() as db:
                                await servicio.una_vuelta(db)
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
