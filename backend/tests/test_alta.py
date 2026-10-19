"""
Alta de una instancia nueva (alta.py): empresa, roles base y primer administrador con su contraseña,
una sola vez y con CODIGO_ALTA. Sin usuario ni contraseña conocidos.

    pytest backend/tests/test_alta.py
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import alta
import catalogo
import server
from database import Base
from models import Empresa, Permiso, Rol, RolPermiso, Usuario, UsuarioRol

CODIGO = "codigo-de-alta-de-prueba-123"
BACKEND = Path(__file__).resolve().parent.parent


def pedido(**cambios) -> alta.PedidoAlta:
    datos = {"codigo": CODIGO,
             "empresa": {"nombre": "Baterías del Este S.A.", "ruc": "80069563", "direccion": "Ruta 7 km 5",
                         "telefono": "061 500 000", "email": "Ventas@Baterias.com.py"},
             "administrador": {"nombre": "Josefina", "apellido": "Martínez", "email": "Jose@Baterias.com.py",
                               "password": "una-clave-propia-2026"}}
    for clave, valor in cambios.items():
        seccion, campo = clave.split("__")
        datos[seccion][campo] = valor
    return alta.PedidoAlta(**datos)


@pytest.fixture
def base_nueva(client):
    """Una base vacía, aparte de la de las demás pruebas (como una instancia recién creada)."""
    carpeta = tempfile.mkdtemp(prefix="alta-")
    engine = create_async_engine(f"sqlite+aiosqlite:///{Path(carpeta, 'nueva.db').as_posix()}")

    async def crear():
        async with engine.begin() as conexion:
            await conexion.run_sync(Base.metadata.create_all)
    client.portal.call(crear)
    sesiones = async_sessionmaker(engine, expire_on_commit=False)

    def correr(funcion):
        async def _con_sesion():
            async with sesiones() as db:
                return await funcion(db)
        return client.portal.call(_con_sesion)

    yield correr
    client.portal.call(engine.dispose)


def test_alta_completa_en_una_base_nueva(base_nueva):
    assert base_nueva(alta.pendiente) is True
    usuario = base_nueva(lambda db: alta.dar_de_alta(db, pedido(), server.hash_password))
    assert usuario.email == "jose@baterias.com.py"

    async def revisar(db):
        empresa = (await db.execute(select(Empresa))).scalar_one()
        admin = (await db.execute(select(Usuario))).scalar_one()
        roles = {r.nombre: r for r in (await db.execute(select(Rol))).scalars().all()}
        permisos_de = {}
        for nombre, rol in roles.items():
            permisos_de[nombre] = set((await db.execute(select(Permiso.clave).join(RolPermiso, RolPermiso.permiso_id == Permiso.id)
                                                        .where(RolPermiso.rol_id == rol.id))).scalars().all())
        rol_admin = (await db.execute(select(UsuarioRol.rol_id).where(UsuarioRol.usuario_id == admin.id))).scalar_one()
        return empresa, admin, roles, permisos_de, rol_admin

    empresa, admin, roles, permisos_de, rol_admin = base_nueva(revisar)
    assert (empresa.nombre, empresa.ruc, empresa.email) == ("Baterías del Este S.A.", "80069563-1", "ventas@baterias.com.py")
    assert set(roles) == {"ADMIN", "GERENTE", "VENDEDOR", "DELIVERY"} and rol_admin == roles["ADMIN"].id
    assert {c for c, _ in catalogo.PERMISOS_BASE} <= permisos_de["ADMIN"]
    assert permisos_de["VENDEDOR"] == set(catalogo.ROLES_BASE["VENDEDOR"])
    assert server.verify_password("una-clave-propia-2026", admin.password_hash)
    assert admin.password_hash != "una-clave-propia-2026"
    # Una sola vez
    assert base_nueva(alta.pendiente) is False
    with pytest.raises(alta.AltaYaHecha):
        base_nueva(lambda db: alta.dar_de_alta(db, pedido(administrador__email="otro@x.com"), server.hash_password))


@pytest.mark.parametrize("cambio, mensaje", [
    ({"empresa__ruc": "80012345-5"}, "debería ser 0"),
    ({"empresa__ruc": "no-es-ruc"}, "RUC inválido"),
    ({"administrador__password": "corta"}, "al menos 8"),
    ({"administrador__email": "sin-arroba"}, "E-mail"),
])
def test_datos_invalidos_no_crean_nada(base_nueva, cambio, mensaje):
    with pytest.raises(alta.AltaInvalida, match=mensaje):
        base_nueva(lambda db: alta.dar_de_alta(db, pedido(**cambio), server.hash_password))
    assert base_nueva(alta.pendiente) is True
    assert base_nueva(lambda db: db.scalar(select(func.count()).select_from(Empresa))) == 0


def test_en_una_instancia_con_usuarios_el_alta_no_existe(client):
    assert client.get("/api/alta").json()["pendiente"] is False
    r = client.post("/api/alta", json=pedido().model_dump())
    assert r.status_code == 404


def test_codigo_de_alta(client, monkeypatch):
    """Con la instancia vacía: sin CODIGO_ALTA no se puede; con uno equivocado, 403 y después 429."""
    async def sin_usuarios(db):
        return True

    async def alta_simulada(db, p, hash_password):
        return SimpleNamespace(email=p.administrador.email.lower())

    monkeypatch.setattr(alta, "pendiente", sin_usuarios)
    monkeypatch.setattr(alta, "dar_de_alta", alta_simulada)
    monkeypatch.delenv("CODIGO_ALTA", raising=False)
    cuerpo = pedido().model_dump()
    assert client.get("/api/alta").json() == {"pendiente": True, "codigo_configurado": False}
    assert client.post("/api/alta", json=cuerpo).status_code == 503
    monkeypatch.setenv("CODIGO_ALTA", "corto")  # menos de 12 caracteres: no cuenta
    assert client.post("/api/alta", json=cuerpo).status_code == 503

    monkeypatch.setenv("CODIGO_ALTA", CODIGO)
    try:
        r = client.post("/api/alta", json={**cuerpo, "codigo": CODIGO + "x"})
        assert r.status_code == 403 and "código" in r.json()["detail"]
        r = client.post("/api/alta", json=cuerpo)
        assert r.status_code == 200 and r.json() == {"ok": True, "email": "jose@baterias.com.py"}
        for _ in range(5):
            client.post("/api/alta", json={**cuerpo, "codigo": "equivocado-123456"})
        assert client.post("/api/alta", json=cuerpo).status_code == 429  # bloqueado aunque ahora sea el correcto
    finally:
        async def limpiar():
            from database import async_session_maker
            async with async_session_maker() as db:
                await server.LOGIN_FALLOS_POR_EMAIL.limpiar(db, "alta")
        client.portal.call(limpiar)


def test_el_arranque_crea_el_catalogo_completo(base_nueva):
    async def asegurar(db):
        creados = await catalogo.asegurar_permisos(db, catalogo.PERMISOS_BASE)
        await db.commit()
        return creados
    assert base_nueva(asegurar) == len(catalogo.PERMISOS_BASE)
    assert base_nueva(asegurar) == 0  # repetirlo no duplica


def test_seed_data_solo_para_desarrollo():
    entorno = {k: v for k, v in os.environ.items() if k != "PERMITIR_ENDPOINTS_DESARROLLO"}
    entorno["DATABASE_URL"] = f"sqlite+aiosqlite:///{Path(tempfile.mkdtemp(), 'x.db').as_posix()}"
    r = subprocess.run([sys.executable, "seed_data.py"], cwd=BACKEND, env=entorno, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=60)
    salida = r.stdout.decode("utf-8", errors="replace")
    assert r.returncode != 0 and "/alta" in salida, salida
