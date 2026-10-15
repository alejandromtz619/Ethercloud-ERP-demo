"""
Seguridad de la API: autenticación por defecto, permisos en rutas sensibles,
endpoints de desarrollo desactivados y límite de intentos de login.

Corre contra la app en memoria con una SQLite temporal (no usa red ni la API desplegada):
    pytest backend/tests/test_seguridad_rutas.py
"""
import os
import re
import sys
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="ethercloud-test-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{Path(_TMP, 'test.db').as_posix()}"
os.environ.pop("JWT_SECRET", None)
os.environ.pop("PERMITIR_ENDPOINTS_DESARROLLO", None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import server  # noqa: E402

# Rutas que deben responder sin token. Cualquier otra ruta /api nueva tiene que exigirlo.
RUTAS_PUBLICAS = {
    ("GET", "/api/"),
    ("GET", "/api/health"),
    ("GET", "/api/empresas/{empresa_id}/publico"),
    ("POST", "/api/auth/login"),
    ("GET", "/api/documentos/{token}"),
    ("POST", "/api/seed"),  # público, pero 404 salvo PERMITIR_ENDPOINTS_DESARROLLO=true
}


def _rutas_api():
    for route in server.app.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/api"):
            for method in route.methods:
                yield method, route.path


@pytest.fixture(scope="module")
def client():
    with TestClient(server.app) as c:
        server.PERMITIR_ENDPOINTS_DESARROLLO = True
        assert c.post("/api/seed").status_code == 200
        server.PERMITIR_ENDPOINTS_DESARROLLO = False
        yield c


def _token(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_lista_publica_coincide_con_lo_registrado():
    publicas = {
        (m, r.path)
        for r in server.public_router.routes
        for m in r.methods
    }
    assert publicas == RUTAS_PUBLICAS


@pytest.mark.parametrize("method,path", sorted(set(_rutas_api()) - RUTAS_PUBLICAS))
def test_ruta_privada_rechaza_anonimo(client, method, path):
    url = re.sub(r"\{[^}]+\}", "1", path)
    r = client.request(method, url)
    assert r.status_code == 401, f"{method} {path} respondió {r.status_code} sin token"


@pytest.mark.parametrize("method,path", sorted(set(_rutas_api()) - RUTAS_PUBLICAS))
def test_ruta_privada_rechaza_token_falsificado_con_secreto_viejo(client, method, path):
    import jwt
    falso = jwt.encode({"sub": "1"}, "ethercloud-secret-key-change-in-production", algorithm="HS256")
    url = re.sub(r"\{[^}]+\}", "1", path)
    r = client.request(method, url, headers={"Authorization": f"Bearer {falso}"})
    assert r.status_code == 401, f"{method} {path} aceptó un token firmado con el secreto público"


def test_rutas_fuera_de_routers_no_exponen_nada(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.post("/api/admin/migrate-documentos-temporales").status_code in (404, 405)


def test_endpoints_de_desarrollo_desactivados(client):
    assert client.post("/api/seed").status_code == 404
    admin = _token(client, "admin@ether.com", "admin123")
    assert client.post("/api/reset-database", headers=admin).status_code == 404


def test_login_publico_y_marca_de_empresa(client):
    r = client.get("/api/empresas/1/publico")
    assert r.status_code == 200
    assert set(r.json()) == {"id", "nombre", "logo_url"}


def test_sin_permiso_no_puede_crear_usuarios_ni_escalar(client):
    admin = _token(client, "admin@ether.com", "admin123")
    r = client.post("/api/auth/register", headers=admin, json={
        "email": "vendedor@test.com", "password": "clave-segura-123",
        "nombre": "Vendedor", "empresa_id": 1,
    })
    assert r.status_code == 200, r.text
    vendedor_id = r.json()["usuario"]["id"]
    roles = {x["nombre"]: x["id"] for x in client.get("/api/roles?empresa_id=1", headers=admin).json()}
    assert client.post(f"/api/usuarios/{vendedor_id}/roles/{roles['VENDEDOR']}", headers=admin).status_code == 200

    vendedor = _token(client, "vendedor@test.com", "clave-segura-123")
    # Puede usar la API normal…
    assert client.get("/api/productos?empresa_id=1", headers=vendedor).status_code == 200
    # …pero no crear usuarios, darse el rol ADMIN, tocar permisos ni la configuración.
    assert client.post("/api/auth/register", headers=vendedor, json={
        "email": "x@test.com", "password": "x", "nombre": "x", "empresa_id": 1,
    }).status_code == 403
    assert client.post(f"/api/usuarios/{vendedor_id}/roles/{roles['ADMIN']}", headers=vendedor).status_code == 403
    assert client.post(f"/api/roles/{roles['VENDEDOR']}/permisos/1", headers=vendedor).status_code == 403
    assert client.post("/api/sistema/sync-permisos", headers=vendedor).status_code == 403
    assert client.put("/api/empresas/1", headers=vendedor, json={"nombre": "x"}).status_code == 403


def test_login_bloquea_tras_intentos_fallidos(client):
    datos = {"email": "admin@ether.com", "password": "incorrecta"}
    for _ in range(5):
        assert client.post("/api/auth/login", json=datos).status_code == 401
    assert client.post("/api/auth/login", json=datos).status_code == 429
    # Otro usuario no queda afectado
    assert client.post("/api/auth/login", json={"email": "vendedor@test.com", "password": "mala"}).status_code == 401
    server.LOGIN_FALLOS_POR_EMAIL.limpiar("admin@ether.com")
