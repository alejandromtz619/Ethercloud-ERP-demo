"""
/api/fiscal: facturación electrónica. Sólo responde en instancias con MODULOS=fe y SIFENSIS_API_KEY.

Permisos: emitir y ver documentos, los mismos que imprimir la factura de una venta (quien podía
imprimir la factura en papel puede emitir la electrónica); configuración, sistema.configurar.
"""
from typing import Callable, Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import configuracion
from database import get_db
from fiscal import catalogos, constructor, numerador
from fiscal.puerto import ConflictoFiscal, DocumentoInvalido, DocumentoNoEncontrado, ErrorFiscal, SinPermisoConfiguracion
from fiscal.servicio import EN_CAMINO, ServicioFiscal
from models import (
    CambioConfiguracion, Cliente, DocumentoFiscal, EstadoVenta, FacturaGrupal, MateriaLaboratorio, Producto, Usuario, Venta, VentaItem,
    factura_grupal_ventas,
)

EMITIR = ("facturas.ver", "ventas.crear", "ventas.ver", "ventas.ver_historial")
INTEGRACIONES = ("sistema.integraciones",)  # cuenta de SIFEN SIS: certificado, KuDE, correo, timbrado
TOPE_LOGO = 1_000_000          # bytes
TOPE_CERTIFICADO = 200_000
CONFIGURAR = ("sistema.configurar",)
NOMBRES_TIPO = {1: "Factura electrónica", 5: "Nota de crédito electrónica", 6: "Nota de débito electrónica"}


class Cheque(BaseModel):
    numero: str = Field(min_length=1, max_length=20)
    banco: str = Field(min_length=2, max_length=100)


class DisenoKude(BaseModel):
    """Lo que se puede cambiar del KuDE desde el ERP (lo demás queda como esté en SIFEN SIS)."""
    colorPrimario: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    colorSecundario: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    colorAcento: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    colorTexto: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    textoPie: Optional[str] = Field(None, max_length=300)
    tamanoLogo: Optional[Literal["s", "m", "l"]] = None
    mostrarQr: Optional[bool] = None
    mostrarTimbrado: Optional[bool] = None
    mostrarLiquidacion: Optional[bool] = None
    esquinasRedondeadas: Optional[bool] = None


class VistaPrevia(BaseModel):
    formato: Literal["a4", "ticket", "ticket58"] = "a4"
    diseno: DisenoKude = DisenoKude()


class Correo(BaseModel):
    envioActivo: Optional[bool] = None
    nombreRemitente: Optional[str] = Field(None, max_length=100)
    responderA: Optional[str] = Field(None, max_length=255)
    adjuntarXml: Optional[bool] = None
    enviarEnPruebas: Optional[bool] = None


class CorreoDePrueba(BaseModel):
    destino: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Timbrado(BaseModel):
    ambiente: Literal["HOMOLOGACION", "PRODUCCION"]
    numero: str = Field(pattern=r"^\d{8}$")
    fecha_inicio: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


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
    if isinstance(e, SinPermisoConfiguracion):
        return HTTPException(status_code=403, detail=e.mensaje)
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

    def con_sesion(permisos: tuple):
        """Para los catálogos: pide sesión, permiso y el módulo fe, pero no la API key."""
        async def _dep(request: Request, db: AsyncSession = Depends(get_db)) -> Usuario:
            encabezado = request.headers.get("Authorization", "")
            if not encabezado.lower().startswith("bearer "):
                raise HTTPException(status_code=401, detail="Sesión requerida")
            usuario = await usuario_desde_jwt(encabezado[7:].strip(), db)
            if not await tiene_algun_permiso(db, usuario.id, permisos):
                raise HTTPException(status_code=403, detail="No tiene permisos para realizar esta acción")
            if getattr(request.app.state, "facturacion", None) is None:
                raise HTTPException(status_code=404, detail="La facturación electrónica no está habilitada en esta instancia")
            return usuario
        return _dep

    CARGAN_DATOS = ("clientes.ver", "clientes.crear", "clientes.editar", "productos.ver", "productos.crear",
                    "productos.editar", "ventas.crear")

    @router.get("/catalogos")
    async def ver_catalogos(usuario: Usuario = Depends(con_sesion(CARGAN_DATOS))):
        """Departamentos y unidades de medida de SIFEN (para los formularios de clientes y productos)."""
        return {"departamentos": catalogos.departamentos(), "unidades_medida": catalogos.unidades_medida()}

    @router.get("/catalogos/distritos")
    async def ver_distritos(departamento: int, usuario: Usuario = Depends(con_sesion(CARGAN_DATOS))):
        return catalogos.distritos(departamento)

    @router.get("/catalogos/ciudades")
    async def ver_ciudades(distrito: int, usuario: Usuario = Depends(con_sesion(CARGAN_DATOS))):
        return catalogos.ciudades(distrito)

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
        filas = await _filas(db, venta.id)
        contenido = constructor.factura_de_venta(venta, cliente, filas, vendedor,
                                                 await configuracion.obtener("fe.plazo_credito"), cheque)
        return contenido, constructor.total_de(contenido["items"], contenido.get("descuentoGlobal", 0))

    async def _filas(db: AsyncSession, venta_id: int) -> list:
        return (await db.execute(select(VentaItem, Producto, MateriaLaboratorio)
                                 .outerjoin(Producto, VentaItem.producto_id == Producto.id)
                                 .outerjoin(MateriaLaboratorio, VentaItem.materia_laboratorio_id == MateriaLaboratorio.id)
                                 .where(VentaItem.venta_id == venta_id).order_by(VentaItem.id))).all()

    async def _contenido_de_grupal(db: AsyncSession, grupal: FacturaGrupal, cheque: Optional[dict] = None) -> tuple[dict, object]:
        cliente = await db.get(Cliente, grupal.cliente_id)
        ventas = (await db.execute(select(Venta).join(factura_grupal_ventas, factura_grupal_ventas.c.venta_id == Venta.id)
                                   .where(factura_grupal_ventas.c.factura_grupal_id == grupal.id).order_by(Venta.id))).scalars().all()
        ventas_y_filas = [(v, await _filas(db, v.id)) for v in ventas]
        contenido = constructor.factura_de_grupal(grupal, cliente, ventas_y_filas,
                                                  await configuracion.obtener("fe.plazo_credito"), cheque)
        return contenido, constructor.total_de(contenido["items"], contenido.get("descuentoGlobal", 0))

    async def _vigente_grupal(db: AsyncSession, grupal_id: int) -> Optional[DocumentoFiscal]:
        return (await db.execute(select(DocumentoFiscal).where(
            DocumentoFiscal.factura_grupal_id == grupal_id, DocumentoFiscal.tipo_documento == 1,
            DocumentoFiscal.estado != "CANCELADO").order_by(DocumentoFiscal.id.desc()))).scalars().first()

    def _cheque_de(doc: DocumentoFiscal) -> Optional[dict]:
        info = ((doc.datos.get("condicion") or {}).get("entregas") or [{}])[0].get("infoCheque")
        return {"numero": info["numeroCheque"], "banco": info["banco"]} if info else None

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
        if venta.facturada:
            raise HTTPException(status_code=409, detail="La venta ya está incluida en una factura agrupada: "
                                                        "se factura desde Facturas")
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

    @router.get("/ventas/estados")
    async def estados_de_ventas(ids: str = Query(..., max_length=2000), usuario: Usuario = Depends(requiere(EMITIR)),
                                db: AsyncSession = Depends(get_db)):
        """Factura electrónica vigente de cada venta pedida (para marcarlas en el historial)."""
        try:
            venta_ids = sorted({int(x) for x in ids.split(",") if x.strip()})[:200]
        except ValueError:
            raise HTTPException(status_code=422, detail="ids: números separados por coma")
        filas = (await db.execute(select(DocumentoFiscal).where(
            DocumentoFiscal.empresa_id == usuario.empresa_id, DocumentoFiscal.venta_id.in_(venta_ids),
            DocumentoFiscal.tipo_documento == 1, DocumentoFiscal.estado != "CANCELADO")
            .order_by(DocumentoFiscal.id))).scalars().all()
        return {str(d.venta_id): documento_dict(d) for d in filas}

    @router.post("/facturas-grupales/{grupal_id}/factura")
    async def facturar_grupal(grupal_id: int, request: Request, pedido: Optional[PedidoFactura] = None,
                              usuario: Usuario = Depends(requiere(EMITIR)), db: AsyncSession = Depends(get_db)):
        """Factura electrónica englobada de una factura agrupada (varias boletas del mismo cliente)."""
        grupal = await db.get(FacturaGrupal, grupal_id)
        if not grupal or grupal.empresa_id != usuario.empresa_id:
            raise HTTPException(status_code=404, detail="Factura agrupada no encontrada")
        existente = await _vigente_grupal(db, grupal_id)
        if existente:
            raise HTTPException(status_code=409, detail={"mensaje": "La factura agrupada ya tiene factura electrónica",
                                                         "documento": documento_dict(existente)})
        cheque = pedido.cheque.model_dump() if pedido and pedido.cheque else None
        try:
            contenido, total = await _contenido_de_grupal(db, grupal, cheque)
        except DocumentoInvalido as e:
            raise _error_http(e)

        async def bloquear(sesion: AsyncSession):
            await sesion.execute(select(FacturaGrupal.id).where(FacturaGrupal.id == grupal_id).with_for_update())
            if await _vigente_grupal(sesion, grupal_id):
                raise HTTPException(status_code=409, detail="La factura agrupada ya tiene factura electrónica")

        try:
            doc = await servicio(request).emitir(db, empresa_id=usuario.empresa_id, tipo=1, contenido=contenido,
                                                 origen="factura_grupal", total=total, usuario=usuario,
                                                 factura_grupal_id=grupal_id, antes_de_numerar=bloquear)
        except ErrorFiscal as e:
            raise _error_http(e)
        return documento_dict(doc)

    @router.get("/facturas-grupales/estados")
    async def estados_de_grupales(ids: str = Query(..., max_length=2000), usuario: Usuario = Depends(requiere(EMITIR)),
                                  db: AsyncSession = Depends(get_db)):
        try:
            grupal_ids = sorted({int(x) for x in ids.split(",") if x.strip()})[:200]
        except ValueError:
            raise HTTPException(status_code=422, detail="ids: números separados por coma")
        filas = (await db.execute(select(DocumentoFiscal).where(
            DocumentoFiscal.empresa_id == usuario.empresa_id, DocumentoFiscal.factura_grupal_id.in_(grupal_ids),
            DocumentoFiscal.tipo_documento == 1, DocumentoFiscal.estado != "CANCELADO")
            .order_by(DocumentoFiscal.id))).scalars().all()
        return {str(d.factura_grupal_id): documento_dict(d) for d in filas}

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
            elif doc.estado in ("INVALIDO", "RECHAZADO") and (doc.venta_id or doc.factura_grupal_id):
                if doc.venta_id:
                    contenido, total = await _contenido_de_venta(db, await db.get(Venta, doc.venta_id), _cheque_de(doc))
                else:
                    contenido, total = await _contenido_de_grupal(db, await db.get(FacturaGrupal, doc.factura_grupal_id),
                                                                  _cheque_de(doc))
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

    # ------------------------------------------------------------ cuenta de SIFEN SIS
    async def _registrar(db: AsyncSession, usuario: Usuario, clave: str, nuevo: str) -> None:
        """Cambios en la cuenta del proveedor: quedan en el historial de Configuración."""
        db.add(CambioConfiguracion(clave=clave, valor_anterior=None, valor_nuevo=nuevo[:500], usuario_id=usuario.id))
        await db.commit()

    @router.get("/cuenta")
    async def ver_cuenta(request: Request, usuario: Usuario = Depends(requiere(INTEGRACIONES))):
        """Estado de la cuenta (lo puede leer cualquier key) y, si la key tiene permiso de configuración,
        la configuración de la empresa en SIFEN SIS."""
        emisor = servicio(request).emisor
        try:
            cuenta = await emisor.cuenta()
        except ErrorFiscal as e:
            raise _error_http(e)
        try:
            config, permiso = await emisor.config(), True
        except SinPermisoConfiguracion as e:
            config, permiso = None, False
        except ErrorFiscal as e:
            raise _error_http(e)
        return {"cuenta": cuenta, "configuracion": config, "permiso_configuracion": permiso}

    @router.put("/cuenta/kude")
    async def guardar_kude(datos: DisenoKude, request: Request, usuario: Usuario = Depends(requiere(INTEGRACIONES)),
                           db: AsyncSession = Depends(get_db)):
        diseno = datos.model_dump(exclude_none=True)
        try:
            guardado = await servicio(request).emisor.guardar_kude(diseno)
        except ErrorFiscal as e:
            raise _error_http(e)
        await _registrar(db, usuario, "sifensis.kude", ", ".join(f"{k}={v}" for k, v in diseno.items()))
        return guardado

    @router.post("/cuenta/kude/vista-previa")
    async def vista_previa(datos: VistaPrevia, request: Request, usuario: Usuario = Depends(requiere(INTEGRACIONES))):
        """KuDE de un documento de ejemplo con el diseño (sin guardarlo). X-Datos-Ejemplo dice qué datos
        de la empresa faltan cargar (los completa con valores ficticios)."""
        try:
            pdf, ejemplo = await servicio(request).emisor.vista_previa_kude(datos.formato, datos.diseno.model_dump(exclude_none=True))
        except ErrorFiscal as e:
            raise _error_http(e)
        return Response(pdf, media_type="application/pdf",
                        headers={"X-Datos-Ejemplo": ejemplo, "Access-Control-Expose-Headers": "X-Datos-Ejemplo"})

    @router.get("/cuenta/kude/logo")
    async def ver_logo(request: Request, usuario: Usuario = Depends(requiere(INTEGRACIONES))):
        try:
            logo = await servicio(request).emisor.ver_logo()
        except ErrorFiscal as e:
            raise _error_http(e)
        if not logo:
            raise HTTPException(status_code=404, detail="Sin logo")
        return Response(logo[0], media_type=logo[1])

    @router.post("/cuenta/kude/logo")
    async def subir_logo(request: Request, archivo: UploadFile = File(...), usuario: Usuario = Depends(requiere(INTEGRACIONES)),
                         db: AsyncSession = Depends(get_db)):
        if archivo.content_type not in ("image/png", "image/jpeg"):
            raise HTTPException(status_code=422, detail="El logo tiene que ser PNG o JPG")
        contenido = await archivo.read(TOPE_LOGO + 1)
        if len(contenido) > TOPE_LOGO:
            raise HTTPException(status_code=422, detail="El logo no puede pasar de 1 MB")
        try:
            await servicio(request).emisor.subir_logo(archivo.filename or "logo", contenido, archivo.content_type)
        except ErrorFiscal as e:
            raise _error_http(e)
        await _registrar(db, usuario, "sifensis.logo", f"subido ({archivo.filename}, {len(contenido)} bytes)")
        return {"ok": True}

    @router.delete("/cuenta/kude/logo")
    async def borrar_logo(request: Request, usuario: Usuario = Depends(requiere(INTEGRACIONES)), db: AsyncSession = Depends(get_db)):
        try:
            await servicio(request).emisor.borrar_logo()
        except ErrorFiscal as e:
            raise _error_http(e)
        await _registrar(db, usuario, "sifensis.logo", "quitado")
        return {"ok": True}

    @router.post("/cuenta/certificado")
    async def subir_certificado(request: Request, archivo: UploadFile = File(...), password: str = Form(..., min_length=1),
                                usuario: Usuario = Depends(requiere(INTEGRACIONES)), db: AsyncSession = Depends(get_db)):
        """Certificado digital (.p12 / .pfx) con su contraseña. Se pasa a SIFEN SIS; el ERP no guarda ni el
        archivo ni la contraseña. Reemplaza al anterior: desde ahí los documentos se firman con éste."""
        nombre = archivo.filename or "certificado.p12"
        if not nombre.lower().endswith((".p12", ".pfx")):
            raise HTTPException(status_code=422, detail="El certificado tiene que ser un archivo .p12 o .pfx")
        contenido = await archivo.read(TOPE_CERTIFICADO + 1)
        if len(contenido) > TOPE_CERTIFICADO:
            raise HTTPException(status_code=422, detail="El archivo es demasiado grande para ser un certificado")
        try:
            emisor = servicio(request).emisor
            await emisor.subir_certificado(nombre, contenido, password)
            vigente = await emisor.certificado()
        except ErrorFiscal as e:
            raise _error_http(e)
        await _registrar(db, usuario, "sifensis.certificado", f"subido ({nombre}); válido hasta {vigente.get('validoHasta')}")
        return vigente

    @router.put("/cuenta/correo")
    async def guardar_correo(datos: Correo, request: Request, usuario: Usuario = Depends(requiere(INTEGRACIONES)),
                             db: AsyncSession = Depends(get_db)):
        """Envío automático del KuDE y el XML al cliente, desde SIFEN SIS."""
        cambios = datos.model_dump(exclude_none=True)
        try:
            guardado = await servicio(request).emisor.guardar_correo(cambios)
        except ErrorFiscal as e:
            raise _error_http(e)
        await _registrar(db, usuario, "sifensis.correo", ", ".join(f"{k}={v}" for k, v in cambios.items()))
        return guardado

    @router.post("/cuenta/correo/prueba")
    async def correo_de_prueba(datos: CorreoDePrueba, request: Request, usuario: Usuario = Depends(requiere(INTEGRACIONES))):
        try:
            return await servicio(request).emisor.probar_correo(datos.destino)
        except ErrorFiscal as e:
            raise _error_http(e)

    @router.put("/cuenta/timbrado")
    async def guardar_timbrado(datos: Timbrado, request: Request, usuario: Usuario = Depends(requiere(INTEGRACIONES)),
                               db: AsyncSession = Depends(get_db)):
        srv = servicio(request)
        try:
            await srv.emisor.guardar_timbrado(datos.ambiente, datos.numero, datos.fecha_inicio)
            await srv.info(refrescar=True)  # el timbrado nuevo se ve enseguida en Probar conexión
        except ErrorFiscal as e:
            raise _error_http(e)
        await _registrar(db, usuario, "sifensis.timbrado", f"{datos.ambiente}: {datos.numero} desde {datos.fecha_inicio}")
        return {"ok": True}

    return router
