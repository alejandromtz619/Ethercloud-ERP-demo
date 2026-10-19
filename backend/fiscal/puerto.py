"""Interfaz con el proveedor de facturación electrónica. Cambiar de proveedor (o hablar directo con
SIFEN) es escribir otro adaptador con estos métodos, sin tocar ventas ni el servicio."""
from dataclasses import dataclass, field
from typing import Optional, Protocol


class ErrorFiscal(Exception):
    def __init__(self, mensaje: str, respuesta: Optional[dict] = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.respuesta = respuesta or {}


class DocumentoInvalido(ErrorFiscal):
    """El contenido no pasa la validación (400). Hay que corregir los datos; reintentar no sirve."""
    def __init__(self, errores: list, respuesta: Optional[dict] = None):
        super().__init__("; ".join(errores) or "Documento inválido", respuesta)
        self.errores = errores


class ConflictoFiscal(ErrorFiscal):
    """409: el número ya está usado con otro contenido o inutilizado, o el evento no corresponde."""


class ProveedorNoDisponible(ErrorFiscal):
    """Sin respuesta, 5xx o límite de peticiones agotado tras los reintentos. Se puede reintentar."""


class DocumentoNoEncontrado(ErrorFiscal):
    """404: el proveedor no conoce ese CDC (para esta API key)."""


class SinPermisoConfiguracion(ErrorFiscal):
    """403 en /config: la API key sólo emite. Para configurar la cuenta hace falta una key con permiso de
    configuración ("Emisión + configuración" en el portal del proveedor)."""


class CredencialFiscalInvalida(ErrorFiscal):
    """API key inválida (401), empresa suspendida (403) o plan vencido (402). Lo resuelve una persona."""


@dataclass
class ResultadoEmision:
    cdc: str
    estado: str                 # GENERADO en una emisión nueva; en un reintento, el estado actual
    duplicado: bool = False     # era un reintento de un documento ya emitido
    advertencias: list = field(default_factory=list)
    respuesta: dict = field(default_factory=dict)


@dataclass
class EstadoDocumento:
    cdc: str
    estado: str                 # GENERADO | ENVIADO | APROBADO | RECHAZADO | CANCELADO
    codigo: Optional[str] = None
    mensaje: Optional[str] = None
    fecha_aprobacion: Optional[str] = None
    respuesta: dict = field(default_factory=dict)


@dataclass
class ResultadoEvento:
    estado: str                 # APROBADO | RECHAZADO
    mensaje: Optional[str] = None
    respuesta: dict = field(default_factory=dict)


class EmisorFiscal(Protocol):
    async def emisor(self) -> dict:
        """Datos configurados: ambiente, RUC, timbrado, establecimientos."""

    async def numeracion(self) -> list:
        """Último número usado por tipo de documento, establecimiento y punto."""

    async def validar(self, data: dict) -> dict:
        """Valida sin emitir ni consumir el número. Devuelve los totales calculados."""

    async def emitir(self, data: dict, metadata: dict) -> ResultadoEmision: ...

    async def estado(self, cdc: str) -> EstadoDocumento: ...

    async def cancelar(self, cdc: str, motivo: str, metadata: dict) -> ResultadoEvento: ...

    async def inutilizar(self, tipo_documento: int, establecimiento: str, punto: str, desde: int, hasta: int,
                         motivo: str, metadata: dict) -> ResultadoEvento: ...

    async def descargar(self, cdc: str, formato: str) -> bytes:
        """formato: a4 | ticket | ticket58 (KuDE en PDF) o xml."""


class CuentaDelProveedor(Protocol):
    """Estado y configuración de la empresa en el proveedor (opcional: sólo lo usa la pantalla
    Configuración › Cuenta de SIFEN SIS). Lo que modifica requiere una key con permiso de configuración."""

    async def cuenta(self) -> dict: ...
    async def config(self) -> dict: ...
    async def guardar_kude(self, diseno: dict) -> dict: ...
    async def vista_previa_kude(self, formato: str, diseno: dict) -> tuple[bytes, str]: ...
    async def ver_logo(self) -> Optional[tuple[bytes, str]]: ...
    async def subir_logo(self, nombre: str, contenido: bytes, tipo: str) -> None: ...
    async def borrar_logo(self) -> None: ...
    async def certificado(self) -> dict: ...
    async def subir_certificado(self, nombre: str, contenido: bytes, password: str) -> dict: ...
    async def guardar_correo(self, datos: dict) -> dict: ...
    async def probar_correo(self, destino: str) -> dict: ...
    async def guardar_timbrado(self, ambiente: str, numero: str, fecha_inicio: str) -> None: ...
