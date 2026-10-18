"""
Numeración de los documentos electrónicos: correlativa por tipo de documento, establecimiento y punto
de expedición, e independiente en cada ambiente de SIFEN.

El número se toma con un UPDATE ... SET ultimo_numero = ultimo_numero + 1 RETURNING: la fila queda
bloqueada hasta el commit, así dos cajas que facturan a la vez esperan una a la otra unos
milisegundos y nunca reciben el mismo número (también en SQLite, que no tiene SELECT ... FOR UPDATE).
Quien llama hace el commit enseguida (con el documento ya guardado) para soltar el bloqueo antes de
hablar con el proveedor.
"""
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models import SecuenciaDocumento


def _consulta(empresa_id: int, ambiente: str, tipo: int, establecimiento: str, punto: str):
    return select(SecuenciaDocumento).where(
        SecuenciaDocumento.empresa_id == empresa_id, SecuenciaDocumento.ambiente == ambiente,
        SecuenciaDocumento.tipo_documento == tipo, SecuenciaDocumento.establecimiento == establecimiento,
        SecuenciaDocumento.punto == punto)


async def _bloquear(db: AsyncSession, empresa_id: int, ambiente: str, tipo: int, establecimiento: str, punto: str):
    consulta = _consulta(empresa_id, ambiente, tipo, establecimiento, punto).with_for_update()
    secuencia = (await db.execute(consulta.execution_options(populate_existing=True))).scalar_one_or_none()
    if secuencia is None:
        try:
            async with db.begin_nested():  # la primera vez; si otra caja la crea a la vez, se usa la suya
                db.add(SecuenciaDocumento(empresa_id=empresa_id, ambiente=ambiente, tipo_documento=tipo,
                                          establecimiento=establecimiento, punto=punto, ultimo_numero=0))
        except IntegrityError:
            pass
        secuencia = (await db.execute(consulta.execution_options(populate_existing=True))).scalar_one()
    return secuencia


async def siguiente_numero(db: AsyncSession, empresa_id: int, ambiente: str, tipo: int, establecimiento: str, punto: str) -> int:
    for _ in range(2):
        numero = (await db.execute(
            update(SecuenciaDocumento)
            .where(SecuenciaDocumento.empresa_id == empresa_id, SecuenciaDocumento.ambiente == ambiente,
                   SecuenciaDocumento.tipo_documento == tipo, SecuenciaDocumento.establecimiento == establecimiento,
                   SecuenciaDocumento.punto == punto)
            .values(ultimo_numero=SecuenciaDocumento.ultimo_numero + 1)
            .returning(SecuenciaDocumento.ultimo_numero)
            .execution_options(synchronize_session=False))).scalar_one_or_none()
        if numero is not None:
            return numero
        try:
            async with db.begin_nested():  # la primera vez; si otra caja la crea a la vez, se usa la suya
                db.add(SecuenciaDocumento(empresa_id=empresa_id, ambiente=ambiente, tipo_documento=tipo,
                                          establecimiento=establecimiento, punto=punto, ultimo_numero=0))
        except IntegrityError:
            pass
    raise RuntimeError("No se pudo crear la secuencia de numeración")


async def sincronizar(db: AsyncSession, empresa_id: int, ambiente: str, numeraciones: list) -> list:
    """Adelanta las secuencias locales al último número que conoce el proveedor (nunca las atrasa).
    Sirve tras restaurar un respaldo o si otro sistema emitió con el mismo punto. Hace commit."""
    cambios = []
    for n in numeraciones:
        tipo, establecimiento = int(n["tipoDocumento"]), str(n["establecimiento"]).zfill(3)
        punto, remoto = str(n["puntoExpedicion"]).zfill(3), int(n["ultimoNumero"])
        secuencia = await _bloquear(db, empresa_id, ambiente, tipo, establecimiento, punto)
        if remoto > secuencia.ultimo_numero:
            cambios.append({"tipo_documento": tipo, "establecimiento": establecimiento, "punto": punto,
                            "antes": secuencia.ultimo_numero, "ahora": remoto})
            secuencia.ultimo_numero = remoto
    await db.commit()
    return cambios


async def secuencias(db: AsyncSession, empresa_id: int, ambiente: str) -> list:
    filas = (await db.execute(select(SecuenciaDocumento).where(
        SecuenciaDocumento.empresa_id == empresa_id, SecuenciaDocumento.ambiente == ambiente)
        .order_by(SecuenciaDocumento.tipo_documento, SecuenciaDocumento.establecimiento, SecuenciaDocumento.punto))).scalars().all()
    return [{"tipo_documento": s.tipo_documento, "establecimiento": s.establecimiento, "punto": s.punto,
             "ultimo_numero": s.ultimo_numero} for s in filas]
