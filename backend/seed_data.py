"""
Script para poblar la base de datos con datos iniciales
Ejecutar: python seed_data.py
"""
import asyncio
from sqlalchemy import select, delete
from database import init_db, async_session_maker
from models import Empresa, Usuario, Rol, Permiso, RolPermiso, UsuarioRol
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

async def seed_database():
    print("🌱 Iniciando seed de base de datos...")
    
    # Inicializar tablas
    await init_db()
    print("✅ Tablas creadas")
    
    async with async_session_maker() as session:
        # 1. Crear Empresa
        result = await session.execute(select(Empresa).where(Empresa.ruc == "12345678901"))
        empresa = result.scalar_one_or_none()
        
        if not empresa:
            empresa = Empresa(
                ruc="12345678901",
                nombre="Luz Brill S.A.",
                direccion="Av. Principal 123",
                telefono="123456789",
                email="contacto@luzbrill.com",
                estado=True
            )
            session.add(empresa)
            await session.commit()
            await session.refresh(empresa)
            print(f"✅ Empresa creada: {empresa.nombre}")
        else:
            print(f"ℹ️  Empresa ya existe: {empresa.nombre}")
        
        # 2. Crear Rol Administrador
        result = await session.execute(select(Rol).where(Rol.nombre == "Administrador"))
        rol_admin = result.scalar_one_or_none()
        
        if not rol_admin:
            rol_admin = Rol(
                nombre="Administrador",
                descripcion="Acceso total al sistema",
                empresa_id=empresa.id
            )
            session.add(rol_admin)
            await session.commit()
            await session.refresh(rol_admin)
            print(f"✅ Rol creado: {rol_admin.nombre}")
        else:
            print(f"ℹ️  Rol ya existe: {rol_admin.nombre}")
        
        # 3. Crear Usuario Administrador
        result = await session.execute(select(Usuario).where(Usuario.email == "admin@luzbrill.com"))
        usuario = result.scalar_one_or_none()
        
        if not usuario:
            usuario = Usuario(
                email="admin@luzbrill.com",
                password_hash=hash_password("admin123"),
                nombre="Admin",
                apellido="Sistema",
                telefono="123456789",
                empresa_id=empresa.id,
                activo=True
            )
            session.add(usuario)
            await session.commit()
            await session.refresh(usuario)
            print(f"✅ Usuario creado: {usuario.email}")
            print(f"   📧 Email: admin@luzbrill.com")
            print(f"   🔑 Password: admin123")
        else:
            print(f"ℹ️  Usuario ya existe: {usuario.email}")
        
        # 4. Asignar Rol al Usuario
        result = await session.execute(
            select(UsuarioRol).where(
                UsuarioRol.usuario_id == usuario.id,
                UsuarioRol.rol_id == rol_admin.id
            )
        )
        usuario_rol = result.scalar_one_or_none()
        
        if not usuario_rol:
            usuario_rol = UsuarioRol(
                usuario_id=usuario.id,
                rol_id=rol_admin.id
            )
            session.add(usuario_rol)
            await session.commit()
            print(f"✅ Rol asignado al usuario")
        else:
            print(f"ℹ️  Usuario ya tiene el rol asignado")
        
        # 5. Limpiar y recrear permisos con formato correcto (modulo.accion)
        print("\n🔄 Limpiando permisos antiguos...")
        await session.execute(delete(RolPermiso))
        await session.execute(delete(Permiso))
        await session.commit()
        print("✅ Permisos antiguos eliminados")
        
        # 6. Crear permisos con formato compuesto (igual a main)
        permisos_data = [
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
            # Stock
            ("stock.ver", "Ver stock"),
            ("stock.entrada", "Registrar entrada de stock"),
            ("stock.salida", "Registrar salida de stock"),
            ("stock.traspasar", "Traspasar stock entre almacenes"),
            ("stock.ajustar", "Ajustar stock manualmente"),
            # Clientes
            ("clientes.ver", "Ver clientes"),
            ("clientes.crear", "Crear clientes"),
            ("clientes.editar", "Editar clientes"),
            ("clientes.ver_creditos", "Ver créditos de clientes"),
            # Proveedores
            ("proveedores.ver", "Ver proveedores"),
            ("proveedores.crear", "Crear proveedores"),
            ("proveedores.editar", "Editar proveedores"),
            ("proveedores.gestionar_deudas", "Gestionar deudas con proveedores"),
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
            ("delivery.eliminar", "Eliminar entregas"),
            # Flota
            ("flota.ver", "Ver flota"),
            ("flota.gestionar", "Gestionar vehículos"),
            # Laboratorio
            ("laboratorio.crear", "Crear materias de laboratorio"),
            ("laboratorio.ver", "Ver materias de laboratorio"),
            # Sistema
            ("usuarios.ver", "Ver usuarios"),
            ("usuarios.gestionar", "Gestionar usuarios"),
            ("roles.gestionar", "Gestionar roles y permisos"),
            ("sistema.configurar", "Configurar sistema"),
            # Reportes
            ("reportes.ver", "Ver reportes"),
            ("reportes.exportar", "Exportar reportes"),
            # Facturas
            ("facturas.ver", "Ver facturas"),
        ]
        
        print(f"\n📝 Creando {len(permisos_data)} permisos...")
        permisos_creados = []
        for clave, descripcion in permisos_data:
            permiso = Permiso(clave=clave, descripcion=descripcion)
            session.add(permiso)
            permisos_creados.append(permiso)
        
        await session.commit()
        print(f"✅ {len(permisos_creados)} permisos creados")
        
        # 7. Asignar TODOS los permisos al rol Administrador
        print(f"\n🔗 Asignando permisos al rol {rol_admin.nombre}...")
        for permiso in permisos_creados:
            await session.refresh(permiso)
            rol_permiso = RolPermiso(
                rol_id=rol_admin.id,
                permiso_id=permiso.id
            )
            session.add(rol_permiso)
        
        await session.commit()
        print(f"✅ {len(permisos_creados)} permisos asignados al rol Administrador")
        
        print("\n" + "="*50)
        print("🎉 Base de datos poblada exitosamente!")
        print("="*50)
        print("\n📋 CREDENCIALES DE LOGIN:")
        print(f"   📧 Email:    admin@luzbrill.com")
        print(f"   🔑 Password: admin123")
        print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(seed_database())
