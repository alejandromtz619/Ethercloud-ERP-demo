"""Adaptador de SIFEN SIS (https://docs.sifensis.guaratec.com). Una URL para los tres ambientes: el
ambiente lo define la API key."""
import asyncio
import logging
from typing import Optional

import httpx

from fiscal import config
from fiscal.puerto import (
    ConflictoFiscal, CredencialFiscalInvalida, DocumentoInvalido, DocumentoNoEncontrado, EstadoDocumento, ProveedorNoDisponible,
    ResultadoEmision, ResultadoEvento,
)

logger = logging.getLogger(__name__)

INTENTOS = 4
ESPERA_MAXIMA = 15  # segundos; un Retry-After más largo se corta acá y se deja para el seguimiento


def _cuerpo(r: httpx.Response) -> dict:
    try:
        datos = r.json()
        return datos if isinstance(datos, dict) else {"datos": datos}
    except ValueError:
        return {"message": r.text[:500]}


def _mensaje(datos: dict, defecto: str) -> str:
    return datos.get("message") or datos.get("error") or defecto


class SifenSis:
    def __init__(self, api_key: str = None, base_url: str = None, transport: httpx.AsyncBaseTransport = None):
        self._http = httpx.AsyncClient(base_url=(base_url or config.SIFENSIS_URL) + "/api/v1",
                                       headers={"X-API-Key": api_key or config.SIFENSIS_API_KEY},
                                       timeout=httpx.Timeout(30, connect=10), transport=transport)

    async def cerrar(self):
        await self._http.aclose()

    async def _pedir(self, metodo: str, ruta: str, **kwargs) -> httpx.Response:
        """Hace la petición con reintentos ante cortes, 5xx y 429. Reintentar una emisión es seguro: el
        proveedor reconoce la numeración y devuelve el documento ya emitido."""
        ultimo: Optional[Exception] = None
        for intento in range(INTENTOS):
            espera = 2 ** intento
            try:
                r = await self._http.request(metodo, ruta, **kwargs)
            except httpx.HTTPError as e:
                ultimo = ProveedorNoDisponible(f"SIFEN SIS no respondió ({type(e).__name__})")
            else:
                if r.status_code < 400:
                    return r
                datos = _cuerpo(r)
                if r.status_code == 400:
                    raise DocumentoInvalido(datos.get("errores") or [_mensaje(datos, "Documento inválido")], datos)
                if r.status_code in (401, 402, 403):
                    textos = {401: "La API key de SIFEN SIS no es válida", 402: "El plan de SIFEN SIS está vencido",
                              403: "La empresa está suspendida en SIFEN SIS"}
                    raise CredencialFiscalInvalida(_mensaje(datos, textos[r.status_code]) if r.status_code != 401
                                                   else textos[401], datos)
                if r.status_code == 404:
                    raise DocumentoNoEncontrado(_mensaje(datos, "No encontrado en SIFEN SIS"), datos)
                if r.status_code == 409:
                    raise ConflictoFiscal(_mensaje(datos, "Conflicto con la numeración o el estado"), datos)
                if r.status_code == 429:
                    if datos.get("codigo") == "LIMITE_EMPRESA_EXCEDIDO":
                        raise ProveedorNoDisponible(_mensaje(datos, "Se alcanzó el tope de documentos"), datos)
                    try:
                        espera = float(r.headers.get("Retry-After", espera))
                    except ValueError:
                        pass
                ultimo = ProveedorNoDisponible(_mensaje(datos, f"SIFEN SIS respondió {r.status_code}"), datos)
            if intento < INTENTOS - 1:
                await asyncio.sleep(min(espera, ESPERA_MAXIMA))
        raise ultimo

    async def emisor(self) -> dict:
        return (await self._pedir("GET", "/emisor")).json()

    async def numeracion(self) -> list:
        return (await self._pedir("GET", "/numeracion")).json().get("numeraciones", [])

    async def validar(self, data: dict) -> dict:
        datos = (await self._pedir("POST", "/de/validar", json={"data": data})).json()
        if datos.get("valido") is False:
            raise DocumentoInvalido(datos.get("errores") or ["Documento inválido"], datos)
        return datos

    async def emitir(self, data: dict, metadata: dict) -> ResultadoEmision:
        d = (await self._pedir("POST", "/de/emitir", json={"data": data, "metadata": metadata})).json()
        return ResultadoEmision(cdc=d["cdc"], estado=d["estado"], duplicado=bool(d.get("duplicado")),
                                advertencias=d.get("advertencias") or [], respuesta=d)

    async def estado(self, cdc: str) -> EstadoDocumento:
        d = (await self._pedir("GET", f"/de/{cdc}/estado")).json()
        return EstadoDocumento(cdc=cdc, estado=d["estado"], codigo=d.get("codigoRespuesta"),
                               mensaje=d.get("mensajeRespuesta"), fecha_aprobacion=d.get("fechaAprobacion"), respuesta=d)

    def _evento(self, d: dict) -> ResultadoEvento:
        sifen = d.get("sifenRespuesta") or {}
        return ResultadoEvento(estado=d.get("estado", ""), mensaje=sifen.get("dMsgRes"),
                               respuesta={k: v for k, v in d.items() if k != "xmlFirmado"})

    async def cancelar(self, cdc: str, motivo: str, metadata: dict) -> ResultadoEvento:
        return self._evento((await self._pedir("POST", "/de/evento/cancelacion",
                                               json={"cdc": cdc, "motivo": motivo, "metadata": metadata})).json())

    async def inutilizar(self, tipo_documento: int, establecimiento: str, punto: str, desde: int, hasta: int,
                         motivo: str, metadata: dict) -> ResultadoEvento:
        cuerpo = {"tipoDocumento": tipo_documento, "establecimiento": int(establecimiento), "puntoExpedicion": int(punto),
                  "desde": desde, "hasta": hasta, "motivo": motivo, "metadata": metadata}
        return self._evento((await self._pedir("POST", "/de/evento/inutilizacion", json=cuerpo)).json())

    async def descargar(self, cdc: str, formato: str) -> bytes:
        if formato == "xml":
            return (await self._pedir("GET", f"/de/{cdc}/xml")).content
        params = {} if formato == "a4" else {"formato": formato}
        return (await self._pedir("GET", f"/de/{cdc}/kude", params=params)).content
