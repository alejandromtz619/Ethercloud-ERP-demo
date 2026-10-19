from sqlalchemy import (
    CheckConstraint, UniqueConstraint, Column, Integer, SmallInteger, String, Boolean, DateTime, Numeric, Text, ForeignKey, Enum, Date, Table, JSON
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
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
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
    # Factura electrónica (SIFEN; ver fiscal/constructor.py). Todo opcional.
    tipo_contribuyente = Column(SmallInteger, nullable=True)  # 1 persona física, 2 jurídica (vacío = se deduce del RUC)
    tipo_operacion = Column(SmallInteger, nullable=True)      # 1 B2B, 2 B2C, 3 B2G, 4 B2F (vacío = según tenga RUC)
    numero_casa = Column(Integer, nullable=True)
    departamento = Column(SmallInteger, nullable=True)        # códigos de fiscal/catalogos.json
    distrito = Column(SmallInteger, nullable=True)
    ciudad = Column(Integer, nullable=True)
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
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
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
    creado_en = Column(DateTime(timezone=True), default=now_paraguay)
    # IVA incluido en el precio: 10, 5 o 0 (exento)
    tasa_iva = Column(SmallInteger, CheckConstraint("tasa_iva IN (0, 5, 10)", name="ck_productos_tasa_iva"),
                      nullable=False, default=10, server_default="10")
    # Unidad de medida de SIFEN (fiscal/catalogos.json): 77 = unidad, 83 = kg, 89 = litro...
    unidad_medida = Column(SmallInteger, nullable=False, default=77, server_default="77")

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
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
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
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    almacen_id = Column(Integer, ForeignKey("almacenes.id"), nullable=False)
    cantidad = Column(Integer, default=0)
    alerta_minima = Column(Integer)
    
    producto = relationship("Producto", back_populates="stock")
    almacen = relationship("Almacen", back_populates="stock")

class MovimientoStock(Base):
    __tablename__ = "movimientos_stock"
    
    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
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
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
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
    facturada = Column(Boolean, default=False)
    # Fecha que se imprime en el documento (NO afecta creado_en ni ningun reporte).
    # NULL = usar la fecha real de la venta.
    fecha_impresion_boleta = Column(Date, nullable=True)
    fecha_impresion_factura = Column(Date, nullable=True)

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
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"))
    materia_laboratorio_id = Column(Integer, ForeignKey("materias_laboratorio.id"))
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(15, 2), nullable=False)
    precio_costo = Column(Numeric(15, 2), default=0)
    total = Column(Numeric(15, 2), nullable=False)
    observaciones = Column(Text)
    # Tasa de IVA del producto al momento de la venta (si después cambia, la venta no)
    tasa_iva = Column(SmallInteger, nullable=False, default=10, server_default="10")
    
    venta = relationship("Venta", back_populates="items")
    producto = relationship("Producto", back_populates="venta_items")
    materia_laboratorio = relationship("MateriaLaboratorio", back_populates="venta_items")

class Presupuesto(Base):
    """Cotización comercial para un cliente. No afecta stock ni ventas/reportes."""
    __tablename__ = "presupuestos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    subtotal = Column(Numeric(15, 2), default=0)
    total = Column(Numeric(15, 2), default=0)
    notas = Column(Text, nullable=True)
    creado_en = Column(DateTime(timezone=True), default=now_paraguay)

    empresa = relationship("Empresa")
    cliente = relationship("Cliente")
    usuario = relationship("Usuario")
    items = relationship("PresupuestoItem", back_populates="presupuesto", cascade="all, delete-orphan")

class PresupuestoItem(Base):
    __tablename__ = "presupuesto_items"

    id = Column(Integer, primary_key=True, index=True)
    presupuesto_id = Column(Integer, ForeignKey("presupuestos.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=True)
    # Snapshot de datos del producto al momento de cotizar (el producto puede cambiar después)
    nombre_producto = Column(String(255), nullable=False)
    imagen_url = Column(String(500), nullable=True)
    cantidad = Column(Integer, nullable=False)
    precio_venta_unitario = Column(Numeric(15, 2), nullable=False)
    subtotal = Column(Numeric(15, 2), nullable=False)
    tasa_iva = Column(SmallInteger, nullable=False, default=10, server_default="10")

    presupuesto = relationship("Presupuesto", back_populates="items")
    producto = relationship("Producto")

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

# Association table for FacturaGrupal <-> Venta (many-to-many)
factura_grupal_ventas = Table(
    'factura_grupal_ventas',
    Base.metadata,
    Column('factura_grupal_id', Integer, ForeignKey('facturas_grupales.id'), primary_key=True),
    Column('venta_id', Integer, ForeignKey('ventas.id'), primary_key=True)
)

class FacturaGrupal(Base):
    """Factura que engloba múltiples boletas de un mismo cliente"""
    __tablename__ = "facturas_grupales"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    numero = Column(String(50), nullable=False)
    condicion = Column(String(10), nullable=False, default='CONTADO')  # CONTADO o CREDITO
    total = Column(Numeric(15, 2), nullable=False)
    iva = Column(Numeric(15, 2), nullable=False)
    creado_en = Column(DateTime(timezone=True), default=now_paraguay)

    empresa = relationship("Empresa")
    cliente = relationship("Cliente")
    ventas = relationship("Venta", secondary=factura_grupal_ventas)

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


# Estado que antes vivía en la memoria del proceso. En la base lo comparten todos los
# procesos de la API y sobrevive a reinicios y deploys.
class AjusteSistema(Base):
    """Ajustes de la instancia por clave (p. ej. la cotización manual)."""
    __tablename__ = "ajustes_sistema"

    clave = Column(String(100), primary_key=True)
    valor = Column(JSON, nullable=False)
    actualizado_en = Column(DateTime(timezone=True), default=now_paraguay, onupdate=now_paraguay)


class IntentoLoginFallido(Base):
    """Un intento de login fallido; se cuentan los recientes para bloquear por e-mail."""
    __tablename__ = "intentos_login_fallidos"

    id = Column(Integer, primary_key=True)
    clave = Column(String(255), nullable=False, index=True)
    creado_en = Column(DateTime(timezone=True), nullable=False, index=True)


class TokenServicio(Base):
    """Token con el que otro servicio (CRM, bot) usa la API de integración (/api/integracion/v1).
    Se guarda sólo el hash; el token se muestra una vez, al crearlo."""
    __tablename__ = "tokens_servicio"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    nombre = Column(String(100), nullable=False)
    prefijo = Column(String(16), nullable=False)  # comienzo del token, para reconocerlo en la lista
    hash = Column(String(64), nullable=False, unique=True, index=True)
    scopes = Column(JSON, nullable=False)
    # Usuario a cuyo nombre quedan los pedidos que crea el token (p. ej. un usuario "Bot WhatsApp")
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime(timezone=True), default=now_paraguay)
    ultimo_uso = Column(DateTime(timezone=True), nullable=True)


class EventoIntegracion(Base):
    """Outbox: un cambio del ERP que le interesa al CRM (venta confirmada, cliente creado...). Se
    escribe en la misma transacción que el cambio (integracion.registrar_eventos) y el CRM lo lee
    con un cursor (GET /api/integracion/v1/eventos?desde=<id>). Se borran a los 30 días."""
    __tablename__ = "eventos_integracion"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tipo = Column(String(50), nullable=False)
    entidad_id = Column(Integer, nullable=False)
    datos = Column(JSON, nullable=False)
    creado_en = Column(DateTime(timezone=True), nullable=False, index=True)


class PedidoIntegracion(Base):
    """Pedido creado por la API de integración (CRM o bot): queda como una venta PENDIENTE que
    confirma un vendedor (D8). La clave de idempotencia evita duplicarla si el CRM reintenta."""
    __tablename__ = "pedidos_integracion"
    __table_args__ = (UniqueConstraint("empresa_id", "clave_idempotencia", name="uq_pedidos_integracion_clave"),)

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    clave_idempotencia = Column(String(100), nullable=False)
    huella = Column(String(64), nullable=False)  # hash del pedido, para detectar la misma clave con otro pedido
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False)
    token_id = Column(Integer, ForeignKey("tokens_servicio.id"), nullable=True)  # quién lo creó
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    creado_en = Column(DateTime(timezone=True), default=now_paraguay)


# ---------------------------------------------------------------- Facturación electrónica (módulo fe)
# Diseño en backend/fiscal/__init__.py. La tabla documentos_electronicos (de la primera versión)
# nunca se usó y queda como está; los documentos de SIFEN van en documentos_fiscales.

class SecuenciaDocumento(Base):
    """Último número usado por tipo de documento, establecimiento y punto de expedición. La
    numeración es independiente en cada ambiente de SIFEN (SANDBOX, HOMOLOGACION, PRODUCCION)."""
    __tablename__ = "secuencias_documento"
    __table_args__ = (UniqueConstraint("empresa_id", "ambiente", "tipo_documento", "establecimiento", "punto",
                                       name="uq_secuencias_documento"),)

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    ambiente = Column(String(20), nullable=False)
    tipo_documento = Column(SmallInteger, nullable=False)  # 1 factura, 5 nota de crédito, 6 nota de débito...
    establecimiento = Column(String(3), nullable=False)
    punto = Column(String(3), nullable=False)
    ultimo_numero = Column(Integer, nullable=False, default=0)


class DocumentoFiscal(Base):
    """Un documento electrónico (factura, nota de crédito...) con su numeración, lo que se envió al
    proveedor y en qué estado está en SIFEN.

    Estados: POR_ENVIAR (tiene número, falta que el proveedor confirme la recepción; se reintenta
    solo), GENERADO / ENVIADO (en camino a SIFEN), APROBADO, RECHAZADO (se corrige y se reemite con
    el mismo número), INVALIDO (el proveedor lo rechazó por datos; ídem) y CANCELADO."""
    __tablename__ = "documentos_fiscales"
    __table_args__ = (UniqueConstraint("empresa_id", "ambiente", "tipo_documento", "establecimiento", "punto", "numero",
                                       name="uq_documentos_fiscales_numeracion"),)

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    ambiente = Column(String(20), nullable=False)
    tipo_documento = Column(SmallInteger, nullable=False)
    establecimiento = Column(String(3), nullable=False)
    punto = Column(String(3), nullable=False)
    numero = Column(Integer, nullable=False)
    origen = Column(String(20), nullable=False)  # venta | factura_grupal | nota_credito
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=True, index=True)
    factura_grupal_id = Column(Integer, ForeignKey("facturas_grupales.id"), nullable=True, index=True)
    documento_asociado_id = Column(Integer, ForeignKey("documentos_fiscales.id"), nullable=True)
    estado = Column(String(15), nullable=False, default="POR_ENVIAR", index=True)
    cdc = Column(String(44), nullable=True, unique=True)
    total = Column(Numeric(15, 2), nullable=False, default=0)
    datos = Column(JSON, nullable=False)       # el "data" enviado (los reintentos mandan exactamente esto)
    respuesta = Column(JSON, nullable=True)    # última respuesta del proveedor
    mensaje = Column(Text, nullable=True)      # motivo de rechazo, errores o advertencias
    intentos = Column(Integer, nullable=False, default=0)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    creado_en = Column(DateTime(timezone=True), default=now_paraguay)
    actualizado_en = Column(DateTime(timezone=True), default=now_paraguay, onupdate=now_paraguay)
    aprobado_en = Column(DateTime(timezone=True), nullable=True)


class CambioConfiguracion(Base):
    """Registro de cada cambio de la configuración de la instancia (configuracion.py): quién, cuándo
    y qué. Los valores secretos se guardan enmascarados."""
    __tablename__ = "cambios_configuracion"

    id = Column(Integer, primary_key=True)
    clave = Column(String(100), nullable=False, index=True)
    valor_anterior = Column(Text, nullable=True)
    valor_nuevo = Column(Text, nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    creado_en = Column(DateTime(timezone=True), default=now_paraguay, index=True)
