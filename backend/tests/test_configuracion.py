"""
Configuración de la instancia (configuracion.py): valores desde la pantalla, secretos cifrados que
nunca salen por la API, variables de entorno que ganan, permisos por clave y registro de cambios.

    pytest backend/tests/test_configuracion.py
"""
import pytest

import configuracion

CLAVE_CIFRADO = "clave-de-cifrado-de-prueba-0123456789abcdef"
API_KEY = "gk_prueba_super_secreta_1234"


@pytest.fixture(autouse=True)
def cifrado(monkeypatch):
    monkeypatch.setenv("CLAVE_CIFRADO", CLAVE_CIFRADO)
    for variable in ("SIFENSIS_API_KEY", "SIFEN_PUNTO", "SIFEN_ESTABLECIMIENTO", "SIFEN_PLAZO_CREDITO", "LAB_MARGEN_GANANCIA"):
        monkeypatch.delenv(variable, raising=False)
    configuracion.invalidar_cache()
    yield
    configuracion.invalidar_cache()


def campo(respuesta: dict, clave: str) -> dict:
    for seccion in respuesta["secciones"]:
        for c in seccion["campos"]:
            if c["clave"] == clave:
                return c
    raise KeyError(clave)


def ver(client, headers) -> dict:
    r = client.get("/api/configuracion", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def cambiar(client, headers, seccion, valores):
    return client.put(f"/api/configuracion/{seccion}", headers=headers, json={"valores": valores})


def usuario_con(client, admin, email, permisos):
    """Usuario con un rol que sólo tiene esos permisos."""
    ids = {p["clave"]: p["id"] for p in client.get("/api/permisos", headers=admin).json()}
    rol = client.post("/api/roles", headers=admin, json={"nombre": f"ROL {email}", "empresa_id": 1}).json()
    for p in permisos:
        client.post(f"/api/roles/{rol['id']}/permisos/{ids[p]}", headers=admin)
    u = client.post("/api/auth/register", headers=admin, json={"email": email, "password": "clave-segura-123",
                                                               "nombre": "Prueba", "empresa_id": 1}).json()
    client.post(f"/api/usuarios/{u['usuario']['id']}/roles/{rol['id']}", headers=admin)
    token = client.post("/api/auth/login", json={"email": email, "password": "clave-segura-123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_secciones_y_valores_por_defecto(client, admin):
    r = ver(client, admin)
    assert [s["seccion"] for s in r["secciones"]] == ["documentos", "facturacion_electronica", "laboratorio"]
    assert r["cifrado_disponible"] is True
    punto = campo(r, "fe.punto")
    assert punto["valor"] == "001" and punto["origen"] == "defecto" and punto["editable"]
    key = campo(r, "fe.api_key")
    assert key["secreta"] and key["configurado"] is False and "valor" not in key


def test_guardar_y_leer(client, admin):
    r = cambiar(client, admin, "facturacion_electronica", {"fe.punto": "7", "fe.plazo_credito": "60 días"})
    assert r.status_code == 200, r.text
    assert sorted(r.json()["cambios"]) == ["fe.plazo_credito", "fe.punto"]
    assert campo(ver(client, admin), "fe.punto")["origen"] == "guardado"
    assert client.portal.call(configuracion.obtener, "fe.punto") == "007"  # normalizado a 3 dígitos
    assert client.portal.call(configuracion.obtener, "fe.plazo_credito") == "60 días"
    # None vuelve al valor por defecto
    cambiar(client, admin, "facturacion_electronica", {"fe.punto": None, "fe.plazo_credito": None})
    assert campo(ver(client, admin), "fe.punto")["origen"] == "defecto"
    assert client.portal.call(configuracion.obtener, "fe.punto") == "001"


def test_secreto_cifrado_y_nunca_devuelto(client, admin):
    r = cambiar(client, admin, "facturacion_electronica", {"fe.api_key": API_KEY})
    assert r.status_code == 200, r.text
    assert API_KEY not in r.text
    pantalla = client.get("/api/configuracion", headers=admin)
    assert API_KEY not in pantalla.text
    key = campo(pantalla.json(), "fe.api_key")
    assert key["configurado"] and key["termina_en"] == "…1234" and key["origen"] == "guardado"
    assert client.portal.call(configuracion.obtener, "fe.api_key") == API_KEY

    async def en_la_base():
        from database import async_session_maker
        from models import AjusteSistema
        async with async_session_maker() as db:
            return (await db.get(AjusteSistema, "config.fe.api_key")).valor
    guardado = client.portal.call(en_la_base)
    assert API_KEY not in str(guardado) and set(guardado) == {"cifrado"}
    # Historial: el secreto aparece enmascarado
    historial = client.get("/api/configuracion/cambios", headers=admin).json()
    assert API_KEY not in str(historial)
    ultimo = next(h for h in historial if h["clave"] == "fe.api_key")
    assert ultimo["valor_nuevo"] == "…1234" and ultimo["usuario"]


def test_otra_clave_de_cifrado_no_puede_leerlo(client, admin, monkeypatch):
    cambiar(client, admin, "facturacion_electronica", {"fe.api_key": API_KEY})
    monkeypatch.setenv("CLAVE_CIFRADO", "otra-clave-de-cifrado-distinta-0123456789")
    configuracion.invalidar_cache()
    assert client.portal.call(configuracion.obtener, "fe.api_key") is None
    key = campo(ver(client, admin), "fe.api_key")
    assert key["configurado"] is False and key["ilegible"] is True


def test_sin_clave_de_cifrado_no_se_guardan_secretos(client, admin, monkeypatch):
    monkeypatch.delenv("CLAVE_CIFRADO")
    assert ver(client, admin)["cifrado_disponible"] is False
    r = cambiar(client, admin, "facturacion_electronica", {"fe.api_key": API_KEY})
    assert r.status_code == 422 and "CLAVE_CIFRADO" in r.json()["detail"]
    # Lo que no es secreto se sigue pudiendo guardar
    assert cambiar(client, admin, "documentos", {"documentos.ciudad_factura": "Encarnación"}).status_code == 200


def test_la_variable_de_entorno_gana(client, admin, monkeypatch):
    cambiar(client, admin, "facturacion_electronica", {"fe.punto": "002"})
    monkeypatch.setenv("SIFEN_PUNTO", "9")
    monkeypatch.setenv("SIFENSIS_API_KEY", "gk_desde_el_entorno_abcd")
    r = ver(client, admin)
    punto, key = campo(r, "fe.punto"), campo(r, "fe.api_key")
    assert punto["valor"] == "009" and punto["origen"] == "entorno" and punto["editable"] is False
    assert key["origen"] == "entorno" and key["termina_en"] == "…abcd" and "valor" not in key
    r = cambiar(client, admin, "facturacion_electronica", {"fe.punto": "003"})
    assert r.status_code == 422 and "SIFEN_PUNTO" in r.json()["detail"]
    assert client.portal.call(configuracion.obtener, "fe.api_key") == "gk_desde_el_entorno_abcd"


def test_validaciones(client, admin):
    for seccion, valores, texto in (
        ("facturacion_electronica", {"fe.punto": "abcd"}, "Punto de expedición"),
        ("facturacion_electronica", {"fe.api_key": "corta"}, "API key"),
        ("laboratorio", {"laboratorio.margen": 1.5}, "entre 0 y 0.95"),
        ("documentos", {"documentos.ajuste_x_mm": "mucho"}, "número"),
        ("documentos", {"fe.punto": "001"}, "no es una clave de esta sección"),
        ("documentos", {"no.existe": 1}, "no es una clave de esta sección"),
    ):
        r = cambiar(client, admin, seccion, valores)
        assert r.status_code == 422 and texto in r.json()["detail"], (valores, r.text)
    assert cambiar(client, admin, "inexistente", {}).status_code == 404
    # Nada se guardó a medias: un lote con un valor malo no guarda los buenos
    r = cambiar(client, admin, "documentos", {"documentos.ciudad_factura": "Luque", "documentos.ajuste_y_mm": 99})
    assert r.status_code == 422
    assert client.portal.call(configuracion.obtener, "documentos.ciudad_factura") != "Luque"


def test_margen_de_laboratorio_se_lee_de_la_configuracion(client, admin):
    assert client.portal.call(configuracion.obtener, "laboratorio.margen") == 0.30
    cambiar(client, admin, "laboratorio", {"laboratorio.margen": "0,25"})
    assert client.portal.call(configuracion.obtener, "laboratorio.margen") == 0.25
    cambiar(client, admin, "laboratorio", {"laboratorio.margen": None})


def test_permisos(client, admin):
    assert client.get("/api/configuracion").status_code == 401
    nadie = usuario_con(client, admin, "config-nadie@test.com", [])
    assert client.get("/api/configuracion", headers=nadie).status_code == 403
    # sistema.configurar: edita documentos, ve la sección de facturación pero no la API key
    configurador = usuario_con(client, admin, "config-sistema@test.com", ["sistema.configurar"])
    r = ver(client, configurador)
    assert campo(r, "documentos.ciudad_factura")["editable"] and not campo(r, "fe.api_key")["editable"]
    assert cambiar(client, configurador, "documentos", {"documentos.ciudad_factura": "Asunción"}).status_code == 200
    r = cambiar(client, configurador, "facturacion_electronica", {"fe.api_key": API_KEY})
    assert r.status_code == 403 and "API key" in r.json()["detail"]
    # sistema.integraciones: la API key sí
    integrador = usuario_con(client, admin, "config-integra@test.com", ["sistema.integraciones"])
    assert cambiar(client, integrador, "facturacion_electronica", {"fe.api_key": API_KEY}).status_code == 200
    assert cambiar(client, integrador, "documentos", {"documentos.ciudad_factura": "Luque"}).status_code == 403
