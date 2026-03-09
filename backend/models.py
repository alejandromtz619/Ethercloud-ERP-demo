from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Numeric, Text, ForeignKey, Enum, Date
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime
from zoneinfo import ZoneInfo
import enum

# Timezone configuration
PARAGUAY_TZ = ZoneInfo("America/Asuncion")

def now_paraguay():
    """Obtiene la fecha y hora actual en zona horaria de Paraguay"""
    return datetime.now(PARAGUAY_TZ)

# Enums
class RolSistema(str, enum.Enum):
    ADMIN = "ADMIN"
    GERENTE = "GERENTE"
    VENDEDOR = "VENDEDOR"
    DELIVERY = "DELIVERY"

class EstadoVenta(str, enum.Enum):
    BORRADOR = "BORRADOR"
    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    ANULADA = "ANULADA"

class TipoMovimientoStock(str, enum.Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    AJUSTE = "AJUSTE"
    TRASPASO = "TRASPASO"
    VENTA = "VENTA"

class EstadoEntrega(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    EN_CAMINO = "EN_CAMINO"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"

class EstadoMateria(str, enum.Enum):
    DISPONIBLE = "DISPONIBLE"
    VENDIDO = "VENDIDO"

class EstadoDocumentoElectronico(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"

class TipoVehiculo(str, enum.Enum):
    MOTO = "MOTO"
    AUTOMOVIL = "AUTOMOVIL"
    CAMIONETA = "CAMIONETA"

class TipoPago(str, enum.Enum):
    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    TRANSFERENCIA = "TRANSFERENCIA"
    CHEQUE = "CHEQUE"
    CREDITO = "CREDITO"

class TipoDocumento(str, enum.Enum):
    BOLETA = "BOLETA"
    FACTURA = "FACTURA"

# Models
class DocumentoTemporal(Base):
    """Tabla para almacenar documentos PDF temporales con enlaces públicos"""
    __tablename__ = "documentos_temporales"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)  # UUID para URL pública
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False)
    tipo_documento = Column(Enum(TipoDocumento), nullable=False)  # BOLETA o FACTURA
    file_path = Column(String(500), nullable=False)  # Ruta del archivo en disco
    fecha_creacion = Column(DateTime(timezone=True), default=now_paraguay)
    fecha_expiracion = Column(DateTime(timezone=True), nullable=False)  # 30 días desde creación
    descargas = Column(Integer, default=0)  # Contador de descargas
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    
    # Relationships
    venta = relationship("Venta", backref="documentos_temporales")
    empresa = relationship("Empresa")

class Empresa(Base):
    __tablename__ = "empresas"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    ruc = Column(String(50), unique=True, nullable=False)
    direccion = Column(String(500))
    telefono = Column(String(50))
    email = Column(String(255))
    logo_url = Column(String(500))
    estado = Column(Boolean, default=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), onupdate=func.now())
    
    usuarios = relationship("Usuario", back_populates="empresa")
    clientes = relationship("Cliente", back_populates="empresa")
    productos = relationship("Producto", back_populates="empresa")
    proveedores = relationship("Proveedor", back_populates="empresa")
    funcionarios = relationship("Funcionario", back_populates="empresa")
    almacenes = relationship("Almacen", back_populates="empresa")
    vehiculos = relationship("Vehiculo", back_populates="empresa")
    categorias = relationship("Categoria", back_populates="empresa")
    marcas = relationship("Marca", back_populates="empresa")
    materias_laboratorio = relationship("MateriaLaboratorio", back_populates="empresa")
    ventas = relationship("Venta", back_populates="empresa")
    roles = relationship("Rol", back_populates="empresa")

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nombre = Column(String(255), nullable=False)
    apellido = Column(String(255))
    telefono = Column(String(50))
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), onupdate=func.now())
    
    empresa = relationship("Empresa", back_populates="usuarios")
    roles = relationship("UsuarioRol", back_populates="usuario")
    preferencias = relationship("PreferenciaUsuario", back_populates="usuario", uselist=False)
    ventas = relationship("Venta", back_populates="usuario")
    entregas = relationship("Entrega", back_populates="responsable")

class Rol(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(500))
    
    empresa = relationship("Empresa", back_populates="roles")
    permisos = relationship("RolPermiso", back_populates="rol")
    usuarios = relationship("UsuarioRol", back_populates="rol")

class Permiso(Base):
    __tablename__ = "permisos"
    
    id = Column(Integer, primary_key=True, index=True)
    clave = Column(String(100), unique=True, nullable=False)
    descripcion = Column(String(500))
    
    roles = relationship("RolPermiso", back_populates="permiso")

class RolPermiso(Base):
    __tablename__ = "rol_permisos"
    
    rol_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    permiso_id = Column(Integer, ForeignKey("permisos.id"), primary_key=True)
    
    rol = relationship("Rol", back_populates="permisos")
    permiso = relationship("Permiso", back_populates="roles")

class UsuarioRol(Base):
    __tablename__ = "usuario_roles"
    
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), primary_key=True)
    rol_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    
    usuario = relationship("Usuario", back_populates="roles")
    rol = relationship("Rol", back_populates="usuarios")

class Cliente(Base):
    __tablename__ = "clientes"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    nombre = Column(String(255), nullable=False)
    apellido = Column(String(255))
    ruc = Column(String(50))
    cedula = Column(String(50))
    direccion = Column(String(500))
    telefono = Column(String(50))
    email = Column(String(255))
    acepta_cheque = Column(Boolean, default=False)
    descuento_porcentaje = Column(Numeric(5, 2), default=0)
    limite_credito = Column(Numeric(15, 2), default=1)  # Límite máximo de crédito (por defecto 1 Gs)
    estado = Column(Boolean, default=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    
    empresa = relationship("Empresa", back_populates="clientes")
    creditos = relationship("CreditoCliente", back_populates="cliente")
    ventas = relationship("Venta", back_populates="cliente", foreign_keys="Venta.cliente_id")

class CreditoCliente(Base):
    """Cada transacción a crédito de un cliente"""
    __tablename__ = "creditos_clientes"
    
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=True)
    monto_original = Column(Numeric(15, 2), nullable=False)  # Monto inicial del crédito
    monto_pendiente = Column(Numeric(15, 2), nullable=False)  # Lo que falta pagar
    descripcion = Column(Text)
    fecha_venta = Column(Date, default=func.current_date())
    pagado = Column(Boolean, default=False)
    creado_en = Column(DateTime(timezone=True), default=now_paraguay)
    
    cliente = relationship("Cliente", back_populates="creditos")
    pagos = relationship("PagoCredito", back_populates="credito")

class PagoCredito(Base):
    """Pagos parciales o totales a un crédito"""
    __tablename__ = "pagos_creditos"
    
    id = Column(Integer, primary_key=True, index=True)
    credito_id = Column(Integer, ForeignKey("creditos_clientes.id"), nullable=False)
    monto = Column(Numeric(15, 2), nullable=False)
    fecha_pago = Column(DateTime(timezone=True), default=now_paraguay)
    observacion = Column(Text)
    
    credito = relationship("CreditoCliente", back_populates="pagos")

class Proveedor(Base):
    __tablename__ = "proveedores"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    nombre = Column(String(255), nullable=False)
    ruc = Column(String(50))
    direccion = Column(String(500))
    telefono = Column(String(50))
    email = Column(String(255))
    estado = Column(Boolean, default=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    
    empresa = relationship("Empresa", back_populates="proveedores")
    productos = relationship("ProveedorProducto", back_populates="proveedor")
    deudas = relationship("DeudaProveedor", back_populates="proveedor")

class ProveedorProducto(Base):
    __tablename__ = "proveedor_productos"
    
    id = Column(Integer, primary_key=True, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    sku = Column(String(100), nullable=True)
    costo = Column(Numeric(15, 2), nullable=True)
    link = Column(String(1000), nullable=True)
    
    proveedor = relationship("Proveedor", back_populates="productos")
    producto = relationship("Producto", back_populates="proveedores")

class DeudaProveedor(Base):
    __tablename__ = "deudas_proveedores"
    
    id = Column(Integer, primary_key=True, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False)
    monto = Column(Numeric(15, 2), nullable=False)
    descripcion = Column(Text)
    fecha_emision = Column(Date, default=func.current_date())
    fecha_limite = Column(Date, nullable=True)
    fecha_pago = Column(Date, nullable=True)
    pagado = Column(Boolean, default=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    
    proveedor = relationship("Proveedor", back_populates="deudas")

class Categoria(Base):
    __tablename__ = "categorias"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    nombre = Column(String(255), nullable=False)
    
    empresa = relationship("Empresa", back_populates="categorias")
    productos = relationship("Producto", back_populates="categoria")

class Marca(Base):
    __tablename__ = "marcas"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    nombre = Column(String(255), nullable=False)
    
    empresa = relationship("Empresa", back_populates="marcas")
    productos = relationship("Producto", back_populates="marca")

class Producto(Base):
    __tablename__ = "productos"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias.id"))
    marca_id = Column(Integer, ForeignKey("marcas.id"))
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)
    codigo_barra = Column(String(100), unique=True, nullable=True)
    precio_venta = Column(Numeric(15, 2), nullable=False)
    precio_costo = Column(Numeric(15, 2), default=0)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True)
    stock_minimo = Column(Integer, default=10)  # Stock mínimo para alertas
    fecha_vencimiento = Column(Date)
    activo = Column(Boolean, default=True)
    imagen_url = Column(String(500))
    
    empresa = relationship("Empresa", back_populates="productos")
    categoria = relationship("Categoria", back_populates="productos")
    marca = relationship("Marca", back_populates="productos")
    proveedores = relationship("ProveedorProducto", back_populates="producto")
    proveedor = relationship("Proveedor")
    stock = relationship("StockActual", back_populates="producto")
    movimientos = relationship("MovimientoStock", back_populates="producto")
    venta_items = relationship("VentaItem", back_populates="producto")

class MateriaLaboratorio(Base):
    __tablename__ = "materias_laboratorio"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)
    codigo_barra = Column(String(100), unique=True, nullable=True)
    precio = Column(Numeric(15, 2), nullable=False)
    estado = Column(Enum(EstadoMateria), default=EstadoMateria.DISPONIBLE)
    creado_en = Column(DateTime(timezone=True), default=now_paraguay)
    
    empresa = relationship("Empresa", back_populates="materias_laboratorio")
    venta_items = relationship("VentaItem", back_populates="materia_laboratorio")

class Almacen(Base):
    __tablename__ = "almacenes"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    nombre = Column(String(255), nullable=False)
    ubicacion = Column(String(500))
    
    empresa = relationship("Empresa", back_populates="almacenes")
    stock = relationship("StockActual", back_populates="almacen")
    movimientos = relationship("MovimientoStock", back_populates="almacen")

class StockActual(Base):
    __tablename__ = "stock_actual"
    
    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    almacen_id = Column(Integer, ForeignKey("almacenes.id"), nullable=False)
    cantidad = Column(Integer, default=0)
    alerta_minima = Column(Integer)
    
    producto = relationship("Producto", back_populates="stock")
    almacen = relationship("Almacen", back_populates="stock")

class MovimientoStock(Base):
    __tablename__ = "movimientos_stock"
    
    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    almacen_id = Column(Integer, ForeignKey("almacenes.id"), nullable=False)
    tipo = Column(Enum(TipoMovimientoStock), nullable=False)
    cantidad = Column(Integer, nullable=False)
    referencia_tipo = Column(String(50))
    referencia_id = Column(Integer)
    # Campos para entrada con proveedor, costo y condición de pago
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True)
    costo_unitario = Column(Numeric(15, 2), nullable=True)   # real purchase cost per unit
    costo_ponderado = Column(Numeric(15, 2), nullable=True)  # CPP applied to product pricing at time of entry
    condicion_pago = Column(String(20), nullable=True)  # 'contado' o 'credito'
    fecha_limite_pago = Column(Date, nullable=True)
    notas = Column(Text, nullable=True)
    cantidad_restante = Column(Integer, nullable=True)  # For ENTRADA batches: remaining units (FIFO tracking)
    creado_en = Column(DateTime(timezone=True), default=now_paraguay)
    
    producto = relationship("Producto", back_populates="movimientos")
    almacen = relationship("Almacen", back_populates="movimientos")
    proveedor = relationship("Proveedor", foreign_keys=[proveedor_id])

class Venta(Base):
    __tablename__ = "ventas"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    representante_cliente_id = Column(Integer, ForeignKey("clientes.id"))
    total = Column(Numeric(15, 2), default=0)
    iva = Column(Numeric(15, 2), default=0)
    descuento = Column(Numeric(15, 2), default=0)
    costo_total = Column(Numeric(15, 2), default=0)
    ganancia = Column(Numeric(15, 2), default=0)
    tipo_pago = Column(Enum(TipoPago), default=TipoPago.EFECTIVO)
    es_delivery = Column(Boolean, default=False)
    estado = Column(Enum(EstadoVenta), default=EstadoVenta.BORRADOR)
    creado_en = Column(DateTime(timezone=True), default=now_paraguay)
    
    empresa = relationship("Empresa", back_populates="ventas")
    cliente = relationship("Cliente", back_populates="ventas", foreign_keys=[cliente_id])
    representante = relationship("Cliente", foreign_keys=[representante_cliente_id])
    usuario = relationship("Usuario", back_populates="ventas")
    items = relationship("VentaItem", back_populates="venta", cascade="all, delete-orphan")
    factura = relationship("Factura", back_populates="venta", uselist=False)
    entrega = relationship("Entrega", back_populates="venta", uselist=False)

class VentaItem(Base):
    __tablename__ = "venta_items"
    
    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"))
    materia_laboratorio_id = Column(Integer, ForeignKey("materias_laboratorio.id"))
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(15, 2), nullable=False)
    precio_costo = Column(Numeric(15, 2), default=0)
    total = Column(Numeric(15, 2), nullable=False)
    observaciones = Column(Text)
    
    venta = relationship("Venta", back_populates="items")
    producto = relationship("Producto", back_populates="venta_items")
    materia_laboratorio = relationship("MateriaLaboratorio", back_populates="venta_items")

class Funcionario(Base):
    __tablename__ = "funcionarios"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    nombre = Column(String(255), nullable=False)
    apellido = Column(String(255))
    cedula = Column(String(50))
    cargo = Column(String(255))
    salario_base = Column(Numeric(15, 2), default=0)
    ips = Column(Numeric(15, 2))
    fecha_nacimiento = Column(Date)
    activo = Column(Boolean, default=True)
    
    empresa = relationship("Empresa", back_populates="funcionarios")
    adelantos = relationship("AdelantoSalario", back_populates="funcionario")
    ciclos = relationship("CicloSalario", back_populates="funcionario")

class AdelantoSalario(Base):
    __tablename__ = "adelantos_salario"
    
    id = Column(Integer, primary_key=True, index=True)
    funcionario_id = Column(Integer, ForeignKey("funcionarios.id"), nullable=False)
    monto = Column(Numeric(15, 2), nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    
    funcionario = relationship("Funcionario", back_populates="adelantos")

class CicloSalario(Base):
    __tablename__ = "ciclos_salario"
    
    id = Column(Integer, primary_key=True, index=True)
    funcionario_id = Column(Integer, ForeignKey("funcionarios.id"), nullable=False)
    periodo = Column(String(7))  # YYYY-MM
    fecha_inicio = Column(Date)
    fecha_fin = Column(Date)
    salario_base = Column(Numeric(15, 2), default=0)
    descuentos = Column(Numeric(15, 2), default=0)  # Adelantos y otros descuentos
    salario_neto = Column(Numeric(15, 2), default=0)
    pagado = Column(Boolean, default=False)
    fecha_pago = Column(DateTime(timezone=True), nullable=True)
    
    funcionario = relationship("Funcionario", back_populates="ciclos")

class Vehiculo(Base):
    __tablename__ = "vehiculos"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    tipo = Column(Enum(TipoVehiculo), nullable=False)
    chapa = Column(String(20), nullable=False)
    vencimiento_habilitacion = Column(Date)
    vencimiento_cedula_verde = Column(Date)
    
    empresa = relationship("Empresa", back_populates="vehiculos")
    entregas = relationship("Entrega", back_populates="vehiculo")

class Entrega(Base):
    __tablename__ = "entregas"
    
    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=True)
    responsable_usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha_entrega = Column(DateTime(timezone=True))
    estado = Column(Enum(EstadoEntrega), default=EstadoEntrega.PENDIENTE)
    
    venta = relationship("Venta", back_populates="entrega")
    vehiculo = relationship("Vehiculo", back_populates="entregas")
    responsable = relationship("Usuario", back_populates="entregas")

class Factura(Base):
    __tablename__ = "facturas"
    
    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), unique=True, nullable=False)
    numero = Column(String(50), nullable=False)
    total = Column(Numeric(15, 2), nullable=False)
    iva = Column(Numeric(15, 2), nullable=False)
    estado = Column(String(50), default="EMITIDA")
    creado_en = Column(DateTime(timezone=True), default=now_paraguay)
    
    venta = relationship("Venta", back_populates="factura")
    documento = relationship("DocumentoElectronico", back_populates="factura", uselist=False)

class DocumentoElectronico(Base):
    __tablename__ = "documentos_electronicos"
    
    id = Column(Integer, primary_key=True, index=True)
    factura_id = Column(Integer, ForeignKey("facturas.id"), unique=True, nullable=False)
    ruta_xml = Column(String(500))
    cdc = Column(String(100))
    estado_sifen = Column(Enum(EstadoDocumentoElectronico), default=EstadoDocumentoElectronico.PENDIENTE)
    mensaje_respuesta = Column(Text)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    
    factura = relationship("Factura", back_populates="documento")

class PreferenciaUsuario(Base):
    __tablename__ = "preferencias_usuario"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), unique=True, nullable=False)
    tema = Column(String(50), default="light")
    color_primario = Column(String(50), default="#0044CC")
    
    usuario = relationship("Usuario", back_populates="preferencias")


class Gasto(Base):
    """Gastos operativos de la empresa (agua, combustible, imprevistos, etc.)"""
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    monto = Column(Numeric(15, 2), nullable=False)
    responsable_nombre = Column(String(255), nullable=False)
    fecha = Column(Date, nullable=False)
    motivo = Column(String(500), nullable=False)
    creado_en = Column(DateTime(timezone=True), default=now_paraguay)

    empresa = relationship("Empresa", backref="gastos")
