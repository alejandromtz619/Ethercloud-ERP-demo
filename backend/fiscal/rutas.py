"""
/api/fiscal: facturación electrónica. Sólo responde en instancias con MODULOS=fe y SIFENSIS_API_KEY.

Permisos: emitir y ver documentos, los mismos que imprimir la factura de una venta (quien podía
imprimir la factura en papel puede emitir la electrónica); configuración, sistema.configurar.
"""
from typing import Callable, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import configuracion
from database import get_db
from fiscal import constructor, numerador
from fiscal.puerto import ConflictoFiscal, DocumentoInvalido, DocumentoNoEncontrado, ErrorFiscal
from fiscal.servicio import EN_CAMINO, ServicioFiscal
from models import Cliente, DocumentoFiscal, EstadoVenta, MateriaLaboratorio, Producto, Usuario, Venta, VentaItem

EMITIR = ("facturas.ver", "ventas.crear", "ventas.ver", "ventas.ver_historial")
CONFIGURAR = ("sistema.configurar",)
NOMBRES_TIPO = {1: "Factura electrónica", 5: "Nota de crédito electrónica", 6: "Nota de débito electrónica"}


class Cheque(BaseModel):
    numero: str = Field(min_length=1, max_length=20)
    banco: str = Field(min_length=2, max_length=100)


class PedidoFactura(BaseModel):
    cheque: Optional[Cheque] = None  # sólo para ventas pagadas con cheque


def documento_dict(d: DocumentoFiscal) -> dict:
    return {
        "id": d.id, "tipo_documento": d.tipo_documento, "tipo": NOMBRES_TIPO.get(d.tipo_documento, str(d.tipo_documento)),
        "numero": f"{d.establecimiento}-{d.punto}-{d.numero:07d}", "estado": d.estado, "cdc": d.cdc,
        "total": float(d.total or 0), "mensaje": d.mensaje, "intentos": d.intentos, "ambiente": d.ambiente,
        "origen": d.origen, "venta_id": d.venta_id, "factura_grupal_id": d.factura_grupal_id,
        "creado_en": d.creado_en.isoformat() if d.creado_en else None,
        "aprobado_en": d.aprobado_en.isoformat() if d.aprobado_en else None,
    }


def _error_http(e: ErrorFiscal) -> HTTPException:
    if isinstance(e, DocumentoInvalido):
        return HTTPException(status_code=422, detail={"mensaje": "El documento no pasa la validación de SIFEN", "errores": e.errores})
    if isinstance(e, ConflictoFiscal):
        return HTTPException(status_code=409, detail=e.mensaje)
    if isinstance(e, DocumentoNoEncontrado):
        return HTTPException(status_code=404, detail=e.mensaje)
    return HTTPException(status_code=503, detail=e.mensaje)


def crear_router(usuario_desde_jwt: Callable, tiene_algun_permiso: Callable) -> APIRouter:
    router = APIRouter(prefix="/api/fiscal", tags=["facturación electrónica"])

    def requiere(permisos: tuple):
        async def _dep(request: Request, db: AsyncSession = Depends(get_db)) -> Usuario:
            encabezado = request.headers.get("Authorization", "")
            if not encabezado.lower().startswith("bearer "):
                raise HTTPException(status_code=401, detail="Sesión requerida")
            usuario = await usuario_desde_jwt(encabezado[7:].strip(), db)
            if not await tiene_algun_permiso(db, usuario.id, permisos):
                raise HTTPException(status_code=403, detail="No tiene permisos para realizar esta acción")
            facturacion = getattr(request.app.state, "facturacion", None)
            if facturacion is None:
                raise HTTPException(status_code=404, detail="La facturación electrónica no está habilitada en esta instancia")
            request.state.servicio_fiscal = await facturacion.servicio()
            if request.state.servicio_fiscal is None:
                raise HTTPException(status_code=503, detail="Falta cargar la API key de SIFEN SIS en Sistema › Configuración")
            return usuario
        return _dep

    def servicio(request: Request) -> ServicioFiscal:
        return request.state.servicio_fiscal

    async def probar_conexion(request: Request) -> dict:
        """Prueba de la sección Facturación electrónica de la pantalla Configuración."""
        facturacion = getattr(request.app.state, "facturacion", None)
        srv = await facturacion.servicio() if facturacion else None
        if srv is None:
            return {"ok": False, "error": "Falta cargar la API key de SIFEN SIS"}
        try:
            info = await srv.info(refrescar=True)
            ambiente, establecimiento, punto = await srv.origen()
        except ErrorFiscal as e:
            return {"ok": False, "error": e.mensaje}
        return {"ok": True, "ambiente": ambiente, "ruc": f"{info.get('ruc')}-{info.get('dv')}",
                "razon_social": info.get("razonSocial"), "timbrado": (info.get("timbrado") or {}).get("numero"),
                "establecimientos": [e["codigo"] for e in info.get("establecimientos", [])],
                "establecimiento": establecimiento, "punto": punto}

    configuracion.PROBADORES["facturacion_electronica"] = probar_conexion

    async def _documento(db: AsyncSession, documento_id: int, usuario: Usuario) -> DocumentoFiscal:
        doc = await db.get(DocumentoFiscal, documento_id)
        if not doc or doc.empresa_id != usuario.empresa_id:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        return doc

    async def _contenido_de_venta(db: AsyncSession, venta: Venta, cheque: Optional[dict] = None) -> tuple[dict, object]:
        cliente = await db.get(Cliente, venta.cliente_id)
        vendedor = await db.get(Usuario, venta.usuario_id)
        filas = (await db.execute(select(VentaItem, Producto, MateriaLaboratorio)
                                  .outerjoin(Producto, VentaItem.producto_id == Producto.id)
                                  .outerjoin(MateriaLaboratorio, VentaItem.materia_laboratorio_id == MateriaLaboratorio.id)
                                  .where(VentaItem.venta_id == venta.id).order_by(VentaItem.id))).all()
        contenido = constructor.factura_de_venta(venta, cliente, filas, vendedor,
                                                 await configuracion.obtener("fe.plazo_credito"), cheque)
        return contenido, constructor.total_de(contenido["items"], contenido.get("descuentoGlobal", 0))

    async def _vigente(db: AsyncSession, venta_id: int) -> Optional[DocumentoFiscal]:
        return (await db.execute(select(DocumentoFiscal).where(
            DocumentoFiscal.venta_id == venta_id, DocumentoFiscal.tipo_documento == 1,
            DocumentoFiscal.estado != "CANCELADO").order_by(DocumentoFiscal.id.desc()))).scalars().first()

    @router.get("/estado")
    async def estado(request: Request, usuario: Usuario = Depends(requiere(EMITIR + CONFIGURAR)),
                     db: AsyncSession = Depends(get_db)):
        """Conexión con el proveedor, desde dónde se emite y cómo va la numeración."""
        srv = servicio(request)
        por_estado = dict((await db.execute(select(DocumentoFiscal.estado, func.count()).where(
            DocumentoFiscal.empresa_id == usuario.empresa_id).group_by(DocumentoFiscal.estado))).all())
        try:
            info = await srv.info(refrescar=True)
            ambiente, establecimiento, punto = await srv.origen()
        except ErrorFiscal as e:
            return {"conectado": False, "error": e.mensaje, "documentos": por_estado}
        return {
            "conectado": True, "ambiente": ambiente, "ruc": f"{info.get('ruc')}-{info.get('dv')}",
            "razon_social": info.get("razonSocial"), "timbrado": (info.get("timbrado") or {}).get("numero"),
            "establecimientos": [e["codigo"] for e in info.get("establecimientos", [])],
            "establecimiento": establecimiento, "punto": punto,
            "secuencias": await numerador.secuencias(db, usuario.empresa_id, ambiente),
            "documentos": por_estado,
        }

    @router.post("/numeracion/sincronizar")
    async def sincronizar(request: Request, usuario: Usuario = Depends(requiere(CONFIGURAR)), db: AsyncSession = Depends(get_db)):
        """Adelanta la numeración local a la última que conoce el proveedor (tras restaurar un respaldo)."""
        try:
            return {"cambios": await servicio(request).sincronizar_numeracion(db, usuario.empresa_id)}
        except ErrorFiscal as e:
            raise _error_http(e)

    @router.post("/ventas/{venta_id}/factura")
    async def facturar_venta(venta_id: int, request: Request, pedido: Optional[PedidoFactura] = None,
                             usuario: Usuario = Depends(requiere(EMITIR)), db: AsyncSession = Depends(get_db)):
        """Emite la factura electrónica de una venta confirmada. Si la venta ya tiene una, la devuelve
        (409) en lugar de emitir otra."""
        venta = await db.get(Venta, venta_id)
        if not venta or venta.empresa_id != usuario.empresa_id:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        if venta.estado != EstadoVenta.CONFIRMADA:
            raise HTTPException(status_code=409, detail="Sólo se factura una venta confirmada")
        existente = await _vigente(db, venta_id)
        if existente:
            raise HTTPException(status_code=409, detail={"mensaje": "La venta ya tiene factura electrónica",
                                                         "documento": documento_dict(existente)})
        cheque = pedido.cheque.model_dump() if pedido and pedido.cheque else None
        try:
            contenido, total = await _contenido_de_venta(db, venta, cheque)
        except DocumentoInvalido as e:
            raise _error_http(e)

        async def bloquear_venta(sesion: AsyncSession):
            # Dos clics (o dos cajas) a la vez: el segundo espera acá y encuentra la factura del primero
            await sesion.execute(select(Venta.id).where(Venta.id == venta_id).with_for_update())
            if await _vigente(sesion, venta_id):
                raise HTTPException(status_code=409, detail="La venta ya tiene factura electrónica")

        try:
            doc = await servicio(request).emitir(db, empresa_id=usuario.empresa_id, tipo=1, contenido=contenido,
                                                 origen="venta", total=total, usuario=usuario, venta_id=venta_id,
                                                 antes_de_numerar=bloquear_venta)
        except ErrorFiscal as e:
            raise _error_http(e)
        return documento_dict(doc)

    @router.get("/ventas/{venta_id}/documentos")
    async def documentos_de_venta(venta_id: int, usuario: Usuario = Depends(requiere(EMITIR)), db: AsyncSession = Depends(get_db)):
        filas = (await db.execute(select(DocumentoFiscal).where(DocumentoFiscal.venta_id == venta_id,
                                                                DocumentoFiscal.empresa_id == usuario.empresa_id)
                                  .order_by(DocumentoFiscal.id))).scalars().all()
        return [documento_dict(d) for d in filas]

    @router.get("/documentos")
    async def listar(estado: Optional[str] = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                     usuario: Usuario = Depends(requiere(EMITIR)), db: AsyncSession = Depends(get_db)):
        consulta = select(DocumentoFiscal).where(DocumentoFiscal.empresa_id == usuario.empresa_id)
        if estado:
            consulta = consulta.where(DocumentoFiscal.estado == estado.upper())
        total = await db.scalar(select(func.count()).select_from(consulta.subquery()))
        filas = (await db.execute(consulta.order_by(DocumentoFiscal.id.desc()).limit(limit).offset(offset))).scalars().all()
        return {"items": [documento_dict(d) for d in filas], "total": total}

    @router.get("/documentos/{documento_id}")
    async def ver(documento_id: int, usuario: Usuario = Depends(requiere(EMITIR)), db: AsyncSession = Depends(get_db)):
        return documento_dict(await _documento(db, documento_id, usuario))

    @router.post("/documentos/{documento_id}/reintentar")
    async def reintentar(documento_id: int, request: Request, usuario: Usuario = Depends(requiere(EMITIR)),
                         db: AsyncSession = Depends(get_db)):
        """Según el estado: reenvía (POR_ENVIAR), consulta a SIFEN (en camino) o arma el documento de
        nuevo con los datos actuales de la venta y lo reemite con el mismo número (inválido o rechazado)."""
        doc = await _documento(db, documento_id, usuario)
        srv = servicio(request)
        try:
            if doc.estado == "POR_ENVIAR":
                doc = await srv.enviar(db, doc, usuario)
            elif doc.estado in EN_CAMINO:
                doc = await srv.actualizar_estado(db, doc)
            elif doc.estado in ("INVALIDO", "RECHAZADO") and doc.venta_id:
                venta = await db.get(Venta, doc.venta_id)
                info = ((doc.datos.get("condicion") or {}).get("entregas") or [{}])[0].get("infoCheque")
                cheque = {"numero": info["numeroCheque"], "banco": info["banco"]} if info else None
                contenido, total = await _contenido_de_venta(db, venta, cheque)
                doc = await srv.reemitir(db, doc, contenido, total, usuario)
            else:
                raise HTTPException(status_code=409, detail=f"No hay nada que reintentar: el documento está {doc.estado}")
        except ErrorFiscal as e:
            raise _error_http(e)
        return documento_dict(doc)

    @router.get("/documentos/{documento_id}/kude")
    async def kude(documento_id: int, request: Request, formato: Literal["a4", "ticket", "ticket58"] = "a4",
                   usuario: Usuario = Depends(requiere(EMITIR)), db: AsyncSession = Depends(get_db)):
        """KuDE en PDF (A4, ticket de 80 mm o de 58 mm) generado por el proveedor."""
        doc = await _documento(db, documento_id, usuario)
        if not doc.cdc:
            raise HTTPException(status_code=409, detail="El documento todavía no tiene CDC (no se pudo enviar)")
        try:
            pdf = await servicio(request).emisor.descargar(doc.cdc, formato)
        except ErrorFiscal as e:
            raise _error_http(e)
        nombre = f"factura-{doc.establecimiento}-{doc.punto}-{doc.numero:07d}.pdf"
        return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{nombre}"'})

    @router.get("/documentos/{documento_id}/xml")
    async def xml(documento_id: int, request: Request, usuario: Usuario = Depends(requiere(EMITIR)),
                  db: AsyncSession = Depends(get_db)):
        doc = await _documento(db, documento_id, usuario)
        if not doc.cdc:
            raise HTTPException(status_code=409, detail="El documento todavía no tiene CDC (no se pudo enviar)")
        try:
            contenido = await servicio(request).emisor.descargar(doc.cdc, "xml")
        except ErrorFiscal as e:
            raise _error_http(e)
        return Response(contenido, media_type="application/xml",
                        headers={"Content-Disposition": f'attachment; filename="{doc.cdc}.xml"'})

    return router
