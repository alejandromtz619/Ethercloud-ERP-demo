"""Emisor en memoria para las pruebas: se comporta como SIFEN SIS en lo que importa al ERP
(validación básica, reintento con el mismo número, 409 con otro contenido, estados asíncronos)."""
import hashlib
import json
import re
from decimal import Decimal

from fiscal.puerto import (
    ConflictoFiscal, DocumentoInvalido, DocumentoNoEncontrado, EstadoDocumento, ProveedorNoDisponible, ResultadoEmision, ResultadoEvento,
)

RUC = re.compile(r"^\d{3,8}-\d$")


def total_documento(data: dict) -> Decimal:
    bruto = sum(Decimal(str(i["cantidad"])) * (Decimal(str(i["precioUnitario"])) - Decimal(str(i.get("descuento", 0))))
                for i in data.get("items", []))
    return bruto - Decimal(str(data.get("descuentoGlobal", 0)))


class SifenFalso:
    def __init__(self, ambiente: str = "SANDBOX"):
        self.ambiente = ambiente
        self.documentos = {}          # (tipo, establecimiento, punto, numero) -> dict
        self.inutilizados = set()     # (tipo, establecimiento, punto, numero)
        self.caido = False            # todo responde como si el proveedor no estuviera
        self.perder_respuestas = 0    # cuántas emisiones registra pero "se corta" antes de responder
        self.rechazar = set()         # números que SIFEN rechazará
        self.llamadas = []

    def _verificar(self, operacion: str):
        self.llamadas.append(operacion)
        if self.caido:
            raise ProveedorNoDisponible("SIFEN SIS no respondió (simulado)")

    async def emisor(self) -> dict:
        self._verificar("emisor")
        return {"ambiente": self.ambiente, "ruc": "99434715", "dv": 4, "razonSocial": "EMPRESA DE PRUEBA S.A.",
                "timbrado": {"numero": "12345678"}, "establecimientos": [{"codigo": "001", "denominacion": "Casa matriz"}]}

    async def numeracion(self) -> list:
        self._verificar("numeracion")
        ultimos = {}
        for (tipo, est, punto, numero) in self.documentos:
            clave = (tipo, est, punto)
            ultimos[clave] = max(ultimos.get(clave, 0), numero)
        return [{"tipoDocumento": t, "establecimiento": e, "puntoExpedicion": p, "ultimoNumero": n, "siguienteNumero": n + 1}
                for (t, e, p), n in ultimos.items()]

    async def validar(self, data: dict) -> dict:
        self._verificar("validar")
        errores = []
        cliente = data.get("cliente") or {}
        if cliente.get("contribuyente") and not RUC.match(cliente.get("ruc") or ""):
            errores.append("data.cliente.ruc: RUC inválido (formato 1234567-8)")
        if len(cliente.get("razonSocial") or "") < 4:
            errores.append("data.cliente.razonSocial: mínimo 4 caracteres")
        if not data.get("items"):
            errores.append("Debe especificar los items del documento en data.items")
        total = total_documento(data)
        condicion = data.get("condicion") or {}
        if data.get("tipoDocumento") == 1 and condicion.get("tipo") == 1:
            pagado = sum(Decimal(str(e["monto"])) for e in condicion.get("entregas", []))
            if pagado != total:
                errores.append(f"data.condicion.entregas: la suma ({pagado}) no coincide con el total ({total})")
        if errores:
            raise DocumentoInvalido(errores, {"valido": False, "errores": errores})
        return {"valido": True, "ambiente": self.ambiente, "totales": {"dTotGralOpe": float(total)}}

    def _clave(self, data: dict) -> tuple:
        return (int(data["tipoDocumento"]), str(data["establecimiento"]).zfill(3), str(data["punto"]).zfill(3), int(data["numero"]))

    async def emitir(self, data: dict, metadata: dict) -> ResultadoEmision:
        self._verificar("emitir")
        await self.validar(data)
        clave = self._clave(data)
        if clave in self.inutilizados:
            raise ConflictoFiscal(f"La numeración {clave} está inutilizada")
        huella = json.dumps(data, sort_keys=True, default=str)
        existente = self.documentos.get(clave)
        if existente and existente["estado"] != "RECHAZADO":
            if existente["huella"] != huella:
                raise ConflictoFiscal(f"Ya existe un documento vigente con la numeración {clave} y otro contenido")
            return ResultadoEmision(cdc=existente["cdc"], estado=existente["estado"], duplicado=True,
                                    respuesta={"cdc": existente["cdc"], "estado": existente["estado"], "duplicado": True})
        cdc = ("01" + hashlib.sha256(huella.encode()).hexdigest())
        cdc = "".join(str(int(c, 16) % 10) for c in cdc)[:44]
        self.documentos[clave] = {"cdc": cdc, "estado": "GENERADO", "huella": huella, "data": data, "metadata": metadata}
        if self.perder_respuestas:
            self.perder_respuestas -= 1
            raise ProveedorNoDisponible("Se cortó la conexión antes de la respuesta (simulado)")
        return ResultadoEmision(cdc=cdc, estado="GENERADO", respuesta={"cdc": cdc, "estado": "GENERADO"})

    def _por_cdc(self, cdc: str) -> tuple:
        for clave, doc in self.documentos.items():
            if doc["cdc"] == cdc:
                return clave, doc
        raise DocumentoNoEncontrado(f"Documento {cdc} no encontrado")

    async def estado(self, cdc: str) -> EstadoDocumento:
        self._verificar("estado")
        clave, doc = self._por_cdc(cdc)
        siguiente = {"GENERADO": "ENVIADO", "ENVIADO": "RECHAZADO" if clave[3] in self.rechazar else "APROBADO"}
        doc["estado"] = siguiente.get(doc["estado"], doc["estado"])
        mensaje = "RUC del receptor inexistente (simulado)" if doc["estado"] == "RECHAZADO" else None
        return EstadoDocumento(cdc=cdc, estado=doc["estado"], mensaje=mensaje,
                               fecha_aprobacion="2026-10-18T17:00:00" if doc["estado"] == "APROBADO" else None,
                               respuesta={"estado": doc["estado"], "mensajeRespuesta": mensaje})

    async def cancelar(self, cdc: str, motivo: str, metadata: dict) -> ResultadoEvento:
        self._verificar("cancelar")
        _, doc = self._por_cdc(cdc)
        if doc["estado"] != "APROBADO":
            raise ConflictoFiscal("Sólo se cancela un documento aprobado")
        doc["estado"] = "CANCELADO"
        return ResultadoEvento(estado="APROBADO", mensaje="Evento registrado correctamente")

    async def inutilizar(self, tipo_documento: int, establecimiento: str, punto: str, desde: int, hasta: int,
                         motivo: str, metadata: dict) -> ResultadoEvento:
        self._verificar("inutilizar")
        claves = [(tipo_documento, establecimiento.zfill(3), punto.zfill(3), n) for n in range(desde, hasta + 1)]
        if any(c in self.documentos and self.documentos[c]["estado"] != "RECHAZADO" for c in claves):
            raise ConflictoFiscal("Hay números usados en el rango")
        self.inutilizados.update(claves)
        return ResultadoEvento(estado="APROBADO", mensaje="Evento registrado correctamente")

    async def descargar(self, cdc: str, formato: str) -> bytes:
        self._verificar("descargar")
        self._por_cdc(cdc)
        return (b"<xml/>" if formato == "xml" else b"%PDF-1.4 KuDE falso ") + cdc.encode()
