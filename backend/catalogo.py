"""
Catálogo de permisos y roles base del ERP, en un solo lugar. Lo usan el arranque (crea los permisos que
falten), el alta de una instancia nueva (alta.py) y los datos de desarrollo (seed_data.py, /api/seed).

Los permisos de módulos opcionales o agregados después (PERMISOS_REQUERIDOS en server.py) se suman
al arrancar; los administradores los reciben solos.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Permiso, Rol, RolPermiso

PERMISOS_BASE = [
    # Dashboard
    ("dashboard.ver", "Ver dashboard"),
    # Ventas
    ("ventas.crear", "Crear ventas"),
    ("ventas.ver", "Ver ventas"),
    ("ventas.anular", "Anular ventas"),
    ("ventas.modificar_precio", "Modificar precios en ventas"),
    ("ventas.aplicar_descuento", "Aplicar descuentos"),
    ("ventas.imprimir_boleta", "Imprimir boletas"),
    ("ventas.imprimir_factura", "Imprimir facturas"),
    ("ventas.ver_historial", "Ver historial de ventas"),
    # Productos
    ("productos.ver", "Ver productos"),
    ("productos.crear", "Crear productos"),
    ("productos.editar", "Editar productos"),
    ("productos.eliminar", "Eliminar productos"),
    ("productos.modificar_precio", "Modificar precios de productos"),
    ("productos.ver_costo", "Ver costos de productos"),
    # Stock
    ("stock.ver", "Ver inventario"),
    ("stock.entrada", "Registrar entradas de stock"),
    ("stock.salida", "Registrar salidas de stock"),
    ("stock.ajustar", "Ajustar stock"),
    ("stock.traspasar", "Traspasar entre almacenes"),
    ("stock.configurar_alertas", "Configurar alertas de stock"),
    # Clientes
    ("clientes.ver", "Ver clientes"),
    ("clientes.crear", "Crear clientes"),
    ("clientes.editar", "Editar clientes"),
    ("clientes.eliminar", "Eliminar clientes"),
    ("clientes.ver_creditos", "Ver créditos de clientes"),
    ("clientes.modificar_descuento", "Modificar descuento de cliente"),
    # Proveedores
    ("proveedores.ver", "Ver proveedores"),
    ("proveedores.crear", "Crear proveedores"),
    ("proveedores.editar", "Editar proveedores"),
    ("proveedores.eliminar", "Eliminar proveedores"),
    ("proveedores.gestionar_deudas", "Gestionar deudas a proveedores"),
    # Funcionarios
    ("funcionarios.ver", "Ver funcionarios"),
    ("funcionarios.crear", "Crear funcionarios"),
    ("funcionarios.editar", "Editar funcionarios"),
    ("funcionarios.ver_salarios", "Ver salarios"),
    ("funcionarios.adelantos", "Registrar adelantos de salario"),
    ("funcionarios.pagar_salarios", "Marcar salarios como pagados"),
    # Delivery
    ("delivery.ver", "Ver entregas"),
    ("delivery.crear", "Crear entregas"),
    ("delivery.actualizar_estado", "Actualizar estado de entregas"),
    # Flota
    ("flota.ver", "Ver flota"),
    ("flota.gestionar", "Gestionar vehículos"),
    # Laboratorio
    ("laboratorio.crear", "Crear materias de laboratorio"),
    ("laboratorio.ver", "Ver materias de laboratorio"),
    ("laboratorio.editar", "Editar materias de laboratorio"),
    ("laboratorio.eliminar", "Eliminar materias de laboratorio"),
    # Sistema
    ("usuarios.ver", "Ver usuarios"),
    ("usuarios.gestionar", "Gestionar usuarios"),
    ("roles.gestionar", "Gestionar roles y permisos"),
    ("sistema.configurar", "Configurar sistema"),
    # Reportes y BI
    ("reportes.ver", "Ver reportes"),
    ("reportes.exportar", "Exportar reportes"),
    ("bi.ver", "Ver Business Intelligence"),
    # Facturas
    ("facturas.ver", "Ver facturas"),
    # Gastos operativos
    ("gastos.ver", "Ver gastos operativos"),
    ("gastos.gestionar", "Gestionar gastos operativos"),
    # Presupuestos
    ("presupuestos.ver", "Ver presupuestos"),
    ("presupuestos.crear", "Crear presupuestos"),
    ("presupuestos.editar", "Editar presupuestos"),
    ("presupuestos.eliminar", "Eliminar presupuestos"),
]

# Roles con los que arranca una instancia. None = todos los permisos (administrador).
ROLES_BASE = {
    "ADMIN": None,
    "GERENTE": [
        "dashboard.ver",
        "ventas.crear", "ventas.ver", "ventas.anular", "ventas.modificar_precio", "ventas.aplicar_descuento",
        "ventas.imprimir_boleta", "ventas.imprimir_factura", "ventas.ver_historial",
        "productos.ver", "productos.crear", "productos.editar", "productos.modificar_precio",
        "stock.ver", "stock.entrada", "stock.salida", "stock.traspasar",
        "clientes.ver", "clientes.crear", "clientes.editar", "clientes.ver_creditos",
        "proveedores.ver", "proveedores.gestionar_deudas",
        "funcionarios.ver", "funcionarios.ver_salarios", "funcionarios.adelantos",
        "delivery.ver", "delivery.crear", "delivery.actualizar_estado",
        "flota.ver", "laboratorio.ver", "laboratorio.crear", "laboratorio.editar",
        "reportes.ver", "reportes.exportar",
        "bi.ver",
        "gastos.ver", "gastos.gestionar",
        "presupuestos.ver", "presupuestos.crear", "presupuestos.editar", "presupuestos.eliminar",
    ],
    "VENDEDOR": [
        "dashboard.ver",
        "ventas.crear", "ventas.ver", "ventas.imprimir_boleta", "ventas.imprimir_factura", "ventas.ver_historial",
        "productos.ver", "stock.ver",
        "clientes.ver", "clientes.crear",
        "delivery.ver", "delivery.crear",
        "laboratorio.ver",
        "presupuestos.ver", "presupuestos.crear", "presupuestos.editar",
    ],
    "DELIVERY": ["delivery.ver", "delivery.actualizar_estado", "flota.ver"],
}


async def asegurar_permisos(db: AsyncSession, permisos) -> int:
    """Crea los permisos [(clave, descripción)] que no existan. Devuelve cuántos creó (no hace commit)."""
    existentes = set((await db.execute(select(Permiso.clave))).scalars().all())
    nuevos = [Permiso(clave=c, descripcion=d) for c, d in permisos if c not in existentes]
    db.add_all(nuevos)
    await db.flush()
    return len(nuevos)


async def crear_roles_base(db: AsyncSession, empresa_id: int) -> dict:
    """Roles base de la empresa con sus permisos (los que ya existan con ese nombre se dejan como
    están). Devuelve {nombre: Rol}. No hace commit."""
    permisos = {p.clave: p.id for p in (await db.execute(select(Permiso))).scalars().all()}
    roles = {}
    for nombre, claves in ROLES_BASE.items():
        rol = (await db.execute(select(Rol).where(Rol.empresa_id == empresa_id, Rol.nombre == nombre))).scalar_one_or_none()
        if rol is None:
            rol = Rol(empresa_id=empresa_id, nombre=nombre, descripcion=f"Rol {nombre}")
            db.add(rol)
            await db.flush()
            ids = permisos.values() if claves is None else [permisos[c] for c in claves if c in permisos]
            db.add_all(RolPermiso(rol_id=rol.id, permiso_id=i) for i in ids)
        roles[nombre] = rol
    await db.flush()
    return roles
