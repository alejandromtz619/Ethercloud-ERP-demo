"""
Permisos por ruta (permisos_rutas.py): cada ruta de la API exige el permiso de alguna de las
pantallas que la usan, igual que el frontend.

    pytest backend/tests/test_permisos_por_ruta.py
"""
import pytest
from fastapi.routing import APIRoute

import server
from permisos_rutas import PERMISOS_POR_RUTA

PUBLICAS = {r.path for r in server.public_router.routes}


def _token(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_toda_ruta_tiene_entrada_y_no_sobran():
    registradas = {(m, r.path[len("/api"):]) for r in server.app.routes
                   if isinstance(r, APIRoute) and r.path.startswith("/api") and r.path not in PUBLICAS
                   for m in r.methods}
    assert registradas - set(PERMISOS_POR_RUTA) == set(), "rutas nuevas sin permiso en permisos_rutas.py"
    assert set(PERMISOS_POR_RUTA) - registradas == set(), "entradas de rutas que ya no existen"


def test_con_control_propio_coincide_con_requiere_permiso():
    """None en la tabla sólo para rutas que declaran requiere_permiso(...) en server.py."""
    for r in server.app.routes:
        if not isinstance(r, APIRoute) or r.path in PUBLICAS or not r.path.startswith("/api"):
            continue
        propio = any("requiere_permiso" in getattr(d.call, "__qualname__", "") for d in r.dependant.dependencies)
        for m in r.methods:
            assert (PERMISOS_POR_RUTA[(m, r.path[4:])] is None) == propio, (m, r.path)


@pytest.fixture(scope="module")
def usuarios(client, admin):
    """Un cajero (rol con sólo ventas.crear) y un usuario sin roles."""
    permisos = {p["clave"]: p["id"] for p in client.get("/api/permisos", headers=admin).json()}
    rol = client.post("/api/roles", headers=admin, json={"nombre": "CAJERO PRUEBA", "empresa_id": 1}).json()
    assert client.post(f"/api/roles/{rol['id']}/permisos/{permisos['ventas.crear']}", headers=admin).status_code == 200
    tokens = {}
    for email, con_rol in (("cajero@test.com", True), ("sinrol@test.com", False)):
        r = client.post("/api/auth/register", headers=admin, json={
            "email": email, "password": "clave-segura-123", "nombre": email, "empresa_id": 1})
        assert r.status_code == 200, r.text
        if con_rol:
            uid = r.json()["usuario"]["id"]
            assert client.post(f"/api/usuarios/{uid}/roles/{rol['id']}", headers=admin).status_code == 200
        tokens[email] = _token(client, email, "clave-segura-123")
    return tokens


def test_cajero_usa_lo_de_ventas_y_nada_mas(client, admin, usuarios):
    cajero = usuarios["cajero@test.com"]
    for ruta in ("/api/productos/buscar?empresa_id=1&q=a", "/api/clientes/buscar?empresa_id=1",
                 "/api/usuarios?empresa_id=1", "/api/materias-laboratorio/disponibles?empresa_id=1",
                 "/api/vehiculos?empresa_id=1", "/api/auth/me", "/api/empresas/1"):
        assert client.get(ruta, headers=cajero).status_code == 200, ruta
    for metodo, ruta in (("GET", "/api/bi/cierre?empresa_id=1&fecha_desde=2026-01-01&fecha_hasta=2026-01-31"),
                         ("GET", "/api/funcionarios?empresa_id=1"), ("GET", "/api/gastos?empresa_id=1"),
                         ("GET", "/api/dashboard/stats?empresa_id=1"), ("GET", "/api/reportes/stock?empresa_id=1"),
                         ("POST", "/api/stock/entrada"), ("DELETE", "/api/clientes/1"), ("DELETE", "/api/productos/1"),
                         ("POST", "/api/ventas/1/anular")):
        assert client.request(metodo, ruta, headers=cajero).status_code == 403, (metodo, ruta)


def test_sin_roles_solo_lo_comun(client, usuarios):
    sin_rol = usuarios["sinrol@test.com"]
    assert client.get("/api/auth/me", headers=sin_rol).status_code == 200
    assert client.get("/api/empresas/1", headers=sin_rol).status_code == 200
    for ruta in ("/api/productos/buscar?empresa_id=1", "/api/clientes/buscar?empresa_id=1", "/api/ventas?empresa_id=1",
                 "/api/stock/buscar?empresa_id=1", "/api/usuarios?empresa_id=1"):
        assert client.get(ruta, headers=sin_rol).status_code == 403, ruta


def test_admin_pasa_todo(client, admin):
    assert client.get("/api/bi/cierre?empresa_id=1&fecha_desde=2026-01-01&fecha_hasta=2026-01-31",
                      headers=admin).status_code == 200


def test_modulos_de_la_instancia(client, usuarios, monkeypatch):
    monkeypatch.setattr(server, "MODULOS_ACTIVOS", {"fe"})
    r = client.get("/api/sistema/modulos", headers=usuarios["sinrol@test.com"])  # cualquier usuario con sesión
    assert r.status_code == 200
    assert r.json() == {"fe": True, "crm": False, "crm_ia": False, "crm_ads": False}
    assert client.get("/api/sistema/modulos").status_code == 401
