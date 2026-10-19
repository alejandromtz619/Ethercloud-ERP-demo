"""
Alta de una instancia nueva: la base no tiene usuarios y la web muestra /alta, donde se cargan los datos
de la empresa y el primer administrador con su propia contraseña. Así ninguna instancia arranca con un
usuario y una contraseña conocidos por todos.

Para que nadie más se adueñe de una instancia recién creada, el alta pide CODIGO_ALTA: un código al
azar que Ether carga en las variables de la instancia (Coolify) y le pasa a quien la configura. Funciona
una sola vez: con un usuario en la base, el alta ya no existe (404).
"""
import hmac
import os
import re
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

import catalogo
from fiscal.constructor import ruc_con_dv
from fiscal.puerto import DocumentoInvalido
from models import Empresa, Usuario, UsuarioRol

LARGO_MINIMO_CODIGO = 12
LARGO_MINIMO_CONTRASENA = 8
CANDADO_ALTA = 7_311_002_028


class AltaInvalida(ValueError):
    """Un dato del alta que no sirve (mensaje para mostrar)."""


class AltaYaHecha(Exception):
    """La instancia ya tiene usuarios."""


class DatosEmpresa(BaseModel):
    nombre: str = Field(min_length=2, max_length=255)
    ruc: str = Field(min_length=3, max_length=20)
    direccion: Optional[str] = Field(None, max_length=500)
    telefono: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)


class DatosAdministrador(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    apellido: Optional[str] = Field(None, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)


class PedidoAlta(BaseModel):
    codigo: str = Field(min_length=1, max_length=200)
    empresa: DatosEmpresa
    administrador: DatosAdministrador


def codigo_configurado() -> Optional[str]:
    codigo = os.environ.get("CODIGO_ALTA", "").strip()
    return codigo if len(codigo) >= LARGO_MINIMO_CODIGO else None


def codigo_correcto(codigo: str) -> bool:
    esperado = codigo_configurado()
    return bool(esperado) and hmac.compare_digest(codigo.strip().encode("utf-8"), esperado.encode("utf-8"))


async def pendiente(db: AsyncSession) -> bool:
    """True mientras la instancia no tenga ningún usuario."""
    return not await db.scalar(select(func.count()).select_from(Usuario))


async def dar_de_alta(db: AsyncSession, pedido: PedidoAlta, hash_password) -> Usuario:
    """Crea la empresa (o completa la que haya), los roles base y el primer administrador. Valida los
    datos y lanza AltaInvalida o AltaYaHecha. Hace commit."""
    ruc_texto = pedido.empresa.ruc.strip()
    try:
        ruc = ruc_con_dv(ruc_texto)
    except DocumentoInvalido as e:
        raise AltaInvalida(e.errores[0])
    if not ruc:
        raise AltaInvalida("RUC inválido (formato: 80012345-6)")
    email = pedido.administrador.email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise AltaInvalida("E-mail del administrador inválido")
    if len(pedido.administrador.password) < LARGO_MINIMO_CONTRASENA:
        raise AltaInvalida(f"La contraseña debe tener al menos {LARGO_MINIMO_CONTRASENA} caracteres")

    if db.get_bind().dialect.name == "postgresql":
        # Dos altas a la vez: la segunda espera acá y después encuentra al administrador de la primera
        await db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": CANDADO_ALTA})
    if not await pendiente(db):
        raise AltaYaHecha()

    empresa = (await db.execute(select(Empresa).order_by(Empresa.id))).scalars().first()
    if empresa is None:
        empresa = Empresa(nombre="", ruc=ruc, estado=True)
        db.add(empresa)
    empresa.nombre = pedido.empresa.nombre.strip()
    empresa.ruc = ruc
    empresa.direccion = (pedido.empresa.direccion or "").strip() or None
    empresa.telefono = (pedido.empresa.telefono or "").strip() or None
    empresa.email = (pedido.empresa.email or "").strip().lower() or None
    empresa.estado = True
    await db.flush()

    await catalogo.asegurar_permisos(db, catalogo.PERMISOS_BASE)
    roles = await catalogo.crear_roles_base(db, empresa.id)
    usuario = Usuario(email=email, password_hash=hash_password(pedido.administrador.password),
                      nombre=pedido.administrador.nombre.strip(),
                      apellido=(pedido.administrador.apellido or "").strip() or None,
                      empresa_id=empresa.id, activo=True)
    db.add(usuario)
    await db.flush()
    db.add(UsuarioRol(usuario_id=usuario.id, rol_id=roles["ADMIN"].id))
    await db.commit()
    return usuario
