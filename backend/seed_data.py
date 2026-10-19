"""
Datos para DESARROLLO: empresa de ejemplo y usuario admin@ether.com / admin123.

    python seed_data.py --desarrollo

No se usa en las instancias de los clientes: una instancia nueva se da de alta desde la web (/alta),
con sus propios datos y la contraseña que elija su administrador (alta.py).
"""
import asyncio
import os
import sys
from sqlalchemy import select
from database import init_db, async_session_maker
from models import Empresa, Usuario, Rol, Permiso, RolPermiso, UsuarioRol
import bcrypt
import catalogo

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

async def seed_database():
    print("🌱 Iniciando seed de base de datos...")
    
    # Inicializar tablas
    await init_db()
    print("✅ Tablas creadas")
    
    async with async_session_maker() as session:
        # 1. Crear Empresa
        result = await session.execute(select(Empresa).where(Empresa.ruc == "5244360-4"))
        empresa = result.scalar_one_or_none()
        
        if not empresa:
            empresa = Empresa(
                ruc="5244360-4",
                nombre="Ether Soluciones Tecnológicas",
                direccion="Dirección Principal 123",
                telefono="000000000",
                email="contacto@empresa.com",
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
        result = await session.execute(select(Usuario).where(Usuario.email == "admin@ether.com"))
        usuario = result.scalar_one_or_none()
        
        if not usuario:
            usuario = Usuario(
                email="admin@ether.com",
                password_hash=hash_password("admin123"),
                nombre="Admin",
                apellido="Ether",
                telefono="000000000",
                empresa_id=empresa.id,
                activo=True
            )
            session.add(usuario)
            await session.commit()
            await session.refresh(usuario)
            print(f"✅ Usuario creado: {usuario.email}")
            print(f"   📧 Email: admin@ether.com")
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
        
        # 5. (Antes se borraban todos los permisos y asignaciones de todos los roles: correrlo
        # en una instancia con datos dejaba sin permisos a gerentes y vendedores. Ahora sólo
        # agrega lo que falta, así sirve para crear el primer admin y se puede repetir.)

        # 6. Crear permisos con formato compuesto (igual a main)
        permisos_data = catalogo.PERMISOS_BASE
        
        print(f"\n📝 Creando {len(permisos_data)} permisos...")
        # El backend crea algunos permisos al arrancar: sólo se agregan los que falten
        result = await session.execute(select(Permiso))
        existentes = {p.clave: p for p in result.scalars().all()}
        permisos_creados = []
        for clave, descripcion in permisos_data:
            permiso = existentes.get(clave)
            if not permiso:
                permiso = Permiso(clave=clave, descripcion=descripcion)
                session.add(permiso)
            permisos_creados.append(permiso)

        await session.commit()
        print(f"✅ {len(permisos_creados)} permisos listos")

        # 7. Asignar TODOS los permisos al rol Administrador
        print(f"\n🔗 Asignando permisos al rol {rol_admin.nombre}...")
        result = await session.execute(
            select(RolPermiso.permiso_id).where(RolPermiso.rol_id == rol_admin.id)
        )
        ya_asignados = set(result.scalars().all())
        for permiso in permisos_creados:
            await session.refresh(permiso)
            if permiso.id in ya_asignados:
                continue
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
        print(f"   📧 Email:    admin@ether.com")
        print(f"   🔑 Password: admin123")
        print("="*50 + "\n")

if __name__ == "__main__":
    if "--desarrollo" not in sys.argv and os.environ.get("PERMITIR_ENDPOINTS_DESARROLLO", "").lower() != "true":
        sys.exit("seed_data.py crea un usuario con contraseña conocida y es sólo para desarrollo "
                 "(python seed_data.py --desarrollo). Una instancia nueva se da de alta desde la web: /alta")
    asyncio.run(seed_database())
