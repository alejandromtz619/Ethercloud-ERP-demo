from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

# Enums
class RolSistema(str, Enum):
    ADMIN = "ADMIN"
    GERENTE = "GERENTE"
    VENDEDOR = "VENDEDOR"
    DELIVERY = "DELIVERY"

class EstadoVenta(str, Enum):
    BORRADOR = "BORRADOR"
    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    ANULADA = "ANULADA"

class TipoMovimientoStock(str, Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    AJUSTE = "AJUSTE"
    TRASPASO = "TRASPASO"

class EstadoEntrega(str, Enum):
    PENDIENTE = "PENDIENTE"
    EN_CAMINO = "EN_CAMINO"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"

class EstadoMateria(str, Enum):
    DISPONIBLE = "DISPONIBLE"
    VENDIDO = "VENDIDO"

class TipoVehiculo(str, Enum):
    MOTO = "MOTO"
    AUTOMOVIL = "AUTOMOVIL"
    CAMIONETA = "CAMIONETA"

class TipoPago(str, Enum):
    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    TRANSFERENCIA = "TRANSFERENCIA"
    CHEQUE = "CHEQUE"
    CREDITO = "CREDITO"

class TipoDocumento(str, Enum):
    BOLETA = "BOLETA"
    FACTURA = "FACTURA"

# Base Schemas
class EmpresaBase(BaseModel):
    nombre: str
    ruc: str
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaResponse(EmpresaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    estado: bool
    creado_en: Optional[datetime] = None

# Usuario
class UsuarioBase(BaseModel):
    email: str
    nombre: str
    apellido: Optional[str] = None
    telefono: Optional[str] = None

class UsuarioCreate(UsuarioBase):
    password: str
    empresa_id: int

class UsuarioLogin(BaseModel):
    email: str
    password: str

class UsuarioResponse(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    rol_id: Optional[int] = None
    activo: bool
    creado_en: Optional[datetime] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse

# Rol y Permisos
class RolBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

class RolCreate(RolBase):
    empresa_id: int

class RolResponse(RolBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int

class PermisoBase(BaseModel):
    clave: str
    descripcion: Optional[str] = None

class PermisoResponse(PermisoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

# Cliente
class ClienteBase(BaseModel):
    nombre: str
    apellido: Optional[str] = None
    ruc: Optional[str] = None
    cedula: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    acepta_cheque: bool = False
    descuento_porcentaje: Optional[Decimal] = 0
    limite_credito: Optional[Decimal] = 0

class ClienteCreate(ClienteBase):
    empresa_id: int

class ClienteResponse(ClienteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    estado: bool
    creado_en: Optional[datetime] = None

class ClienteConCredito(ClienteResponse):
    credito_usado: Decimal = 0
    credito_disponible: Decimal = 0

# Credito Cliente
class CreditoClienteBase(BaseModel):
    monto_original: Decimal
    monto_pendiente: Decimal
    descripcion: Optional[str] = None

class CreditoClienteCreate(BaseModel):
    cliente_id: int
    venta_id: Optional[int] = None
    monto_original: Decimal
    descripcion: Optional[str] = None

class CreditoClienteResponse(CreditoClienteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cliente_id: int
    venta_id: Optional[int] = None
    fecha_venta: Optional[date] = None
    pagado: bool
    creado_en: Optional[datetime] = None

# Pago Credito
class PagoCreditoCreate(BaseModel):
    monto: Decimal
    observacion: Optional[str] = None

class PagoCreditoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    credito_id: int
    monto: Decimal
    fecha_pago: Optional[datetime] = None
    observacion: Optional[str] = None

class CreditoClienteCreate(CreditoClienteBase):
    cliente_id: int

class CreditoClienteResponse(CreditoClienteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cliente_id: int

# Proveedor
class ProveedorBase(BaseModel):
    nombre: str
    ruc: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None

class ProveedorCreate(ProveedorBase):
    empresa_id: int

class ProveedorResponse(ProveedorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    estado: bool
    creado_en: Optional[datetime] = None

# Deuda Proveedor
class DeudaProveedorBase(BaseModel):
    monto: Decimal
    descripcion: Optional[str] = None
    fecha_emision: Optional[date] = None
    fecha_limite: Optional[date] = None
    pagado: bool = False

class DeudaProveedorCreate(DeudaProveedorBase):
    proveedor_id: int

class DeudaProveedorResponse(DeudaProveedorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    proveedor_id: int
    fecha_pago: Optional[date] = None
    creado_en: Optional[datetime] = None

# Categoria
class CategoriaBase(BaseModel):
    nombre: str

class CategoriaCreate(CategoriaBase):
    empresa_id: int

class CategoriaResponse(CategoriaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int

# Marca
class MarcaBase(BaseModel):
    nombre: str

class MarcaCreate(MarcaBase):
    empresa_id: int

class MarcaResponse(MarcaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int

# Producto
class ProductoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    codigo_barra: Optional[str] = None
    precio_venta: Decimal
    fecha_vencimiento: Optional[date] = None
    imagen_url: Optional[str] = None
    categoria_id: Optional[int] = None
    marca_id: Optional[int] = None

class ProductoCreate(ProductoBase):
    empresa_id: int

class ProductoResponse(ProductoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    activo: bool

class ProductoConStock(ProductoResponse):
    stock_total: int = 0
    categoria_nombre: Optional[str] = None
    marca_nombre: Optional[str] = None

# Materia Laboratorio
class MateriaLaboratorioBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    codigo_barra: Optional[str] = None
    precio: Decimal

class MateriaLaboratorioCreate(MateriaLaboratorioBase):
    empresa_id: int

class MateriaLaboratorioResponse(MateriaLaboratorioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    estado: EstadoMateria
    creado_en: Optional[datetime] = None

# Almacen
class AlmacenBase(BaseModel):
    nombre: str
    ubicacion: Optional[str] = None

class AlmacenCreate(AlmacenBase):
    empresa_id: int

class AlmacenResponse(AlmacenBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int

# Stock
class StockActualBase(BaseModel):
    producto_id: int
    almacen_id: int
    cantidad: int = 0
    alerta_minima: Optional[int] = None

class StockActualCreate(StockActualBase):
    pass

class StockActualResponse(StockActualBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

class StockConDetalles(StockActualResponse):
    producto_nombre: Optional[str] = None
    almacen_nombre: Optional[str] = None

# Movimiento Stock
class MovimientoStockBase(BaseModel):
    producto_id: int
    almacen_id: int
    tipo: TipoMovimientoStock
    cantidad: int
    referencia_tipo: Optional[str] = None
    referencia_id: Optional[int] = None

class MovimientoStockCreate(MovimientoStockBase):
    pass

class MovimientoStockResponse(MovimientoStockBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    creado_en: Optional[datetime] = None

# Traspaso Stock
class TraspasoStockCreate(BaseModel):
    producto_id: int
    almacen_origen_id: int
    almacen_destino_id: int
    cantidad: int

# Salida Stock
class SalidaStockCreate(BaseModel):
    producto_id: int
    almacen_id: int
    cantidad: int
    motivo: Optional[str] = None

# Venta
class VentaItemBase(BaseModel):
    producto_id: Optional[int] = None
    materia_laboratorio_id: Optional[int] = None
    cantidad: int
    precio_unitario: Decimal
    observaciones: Optional[str] = None

class VentaItemCreate(VentaItemBase):
    pass

class VentaItemResponse(VentaItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    venta_id: int
    total: Decimal
    producto_nombre: Optional[str] = None
    materia_nombre: Optional[str] = None
    descripcion: Optional[str] = None

class VentaBase(BaseModel):
    cliente_id: int
    representante_cliente_id: Optional[int] = None
    tipo_pago: TipoPago = TipoPago.EFECTIVO
    es_delivery: bool = False

class VentaCreate(VentaBase):
    empresa_id: int
    usuario_id: int
    items: List[VentaItemCreate]

class VentaUpdate(BaseModel):
    cliente_id: Optional[int] = None
    representante_cliente_id: Optional[int] = None
    tipo_pago: Optional[TipoPago] = None
    es_delivery: Optional[bool] = None
    items: Optional[List[VentaItemCreate]] = None

class VentaResponse(VentaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    usuario_id: int
    total: Decimal
    iva: Decimal
    descuento: Decimal
    estado: EstadoVenta
    creado_en: Optional[datetime] = None

class VentaConDetalles(VentaResponse):
    items: List[VentaItemResponse] = []
    cliente_nombre: Optional[str] = None
    cliente_ruc: Optional[str] = None

# Funcionario
class FuncionarioBase(BaseModel):
    nombre: str
    apellido: Optional[str] = None
    cedula: Optional[str] = None
    cargo: Optional[str] = None
    salario_base: Decimal = 0
    ips: Optional[Decimal] = None
    fecha_nacimiento: Optional[date] = None

class FuncionarioCreate(FuncionarioBase):
    empresa_id: int

class FuncionarioResponse(FuncionarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    activo: bool

# Adelanto Salario
class AdelantoSalarioBase(BaseModel):
    monto: Decimal

class AdelantoSalarioCreate(AdelantoSalarioBase):
    funcionario_id: int

class AdelantoSalarioResponse(AdelantoSalarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    funcionario_id: int
    creado_en: Optional[datetime] = None

# Ciclo Salario
class CicloSalarioBase(BaseModel):
    periodo: str
    total_adelantos: Decimal = 0
    pago_final: Decimal = 0
    pagado: bool = False

class CicloSalarioCreate(CicloSalarioBase):
    funcionario_id: int

class CicloSalarioResponse(CicloSalarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    funcionario_id: int

# Vehiculo
class VehiculoBase(BaseModel):
    tipo: TipoVehiculo
    chapa: str
    vencimiento_habilitacion: Optional[date] = None
    vencimiento_cedula_verde: Optional[date] = None

class VehiculoCreate(VehiculoBase):
    empresa_id: int

class VehiculoResponse(VehiculoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int

# Entrega
class EntregaBase(BaseModel):
    venta_id: int
    vehiculo_id: Optional[int] = None
    responsable_usuario_id: Optional[int] = None
    fecha_entrega: Optional[datetime] = None

class EntregaCreate(EntregaBase):
    pass

class AsignarEntrega(BaseModel):
    vehiculo_id: int
    responsable_usuario_id: int

class EntregaResponse(EntregaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    estado: EstadoEntrega

class EntregaConDetalles(EntregaResponse):
    cliente_nombre: Optional[str] = None
    cliente_telefono: Optional[str] = None
    cliente_direccion: Optional[str] = None
    vehiculo_chapa: Optional[str] = None
    responsable_nombre: Optional[str] = None
    items: Optional[List[dict]] = []

# Factura
class FacturaBase(BaseModel):
    venta_id: int
    numero: str
    total: Decimal
    iva: Decimal

class FacturaCreate(FacturaBase):
    pass

class FacturaResponse(FacturaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    estado: str
    creado_en: Optional[datetime] = None

# Preferencias Usuario
class PreferenciaUsuarioBase(BaseModel):
    tema: str = "light"
    color_primario: str = "#0044CC"

class PreferenciaUsuarioCreate(PreferenciaUsuarioBase):
    usuario_id: int

class PreferenciaUsuarioResponse(PreferenciaUsuarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    usuario_id: int

# Dashboard Stats
class VentasPorHora(BaseModel):
    hora: int
    cantidad: int
    monto: Decimal
    unidades: int = 0

class StockBajo(BaseModel):
    producto_id: int
    producto_nombre: str
    stock_total: int
    alerta_minima: int

class DashboardStats(BaseModel):
    ventas_hoy: Decimal = 0
    cantidad_ventas_hoy: int = 0
    ventas_mes: Decimal = 0
    cantidad_ventas_mes: int = 0
    deliverys_pendientes: int = 0
    productos_stock_bajo: int = 0
    creditos_por_vencer: int = 0
    ventas_por_hora: List[VentasPorHora] = []
    productos_bajo_stock: List[StockBajo] = []
    productos_alto_stock: List[dict] = []

# Cotizacion
class CotizacionDivisa(BaseModel):
    usd_pyg: Decimal
    brl_pyg: Decimal
    manual: bool = False
    fecha_actualizacion: datetime

# Alertas
class Alerta(BaseModel):
    tipo: str
    mensaje: str
    nivel: str  # info, warning, danger
    referencia_id: Optional[int] = None

# Documentos Temporales
class DocumentoTemporalBase(BaseModel):
    venta_id: int
    tipo_documento: TipoDocumento

class DocumentoTemporalCreate(DocumentoTemporalBase):
    pass

class DocumentoTemporal(DocumentoTemporalBase):
    id: int
    token: str
    file_path: str
    fecha_creacion: datetime
    fecha_expiracion: datetime
    descargas: int
    empresa_id: int
    url_publica: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
