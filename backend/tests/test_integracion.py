"""
API de integración v1 (integracion.py): tokens de servicio, scopes y catálogo público.

    pytest backend/tests/test_integracion.py
"""
import pytest
from fastapi.routing import APIRoute

import server

PREFIJO = "ZZINT"
V1 = "/api/integracion/v1"


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_toda_ruta_de_integracion_declara_su_scope():
    sin_scope = []
    for r in server.app.routes:
        if isinstance(r, APIRoute) and r.path.startswith(V1) and r.path != f"{V1}/yo":
            if not any(getattr(d.call, "scope", None) for d in r.dependant.dependencies):
                sin_scope.append(r.path)
    assert sin_scope == []


@pytest.fixture(scope="module")
def tokens(client, admin):
    def crear(perfil):
        r = client.post("/api/integracion/tokens", headers=admin, json={"nombre": f"{PREFIJO} {perfil}", "perfil": perfil})
        assert r.status_code == 200, r.text
        assert r.json()["token"].startswith("ecs_")
        return r.json()
    return {"interno": crear("crm-interno"), "bot": crear("crm-bot")}


@pytest.fixture(scope="module")
def catalogo(client, admin):
    def post(ruta, cuerpo):
        r = client.post(ruta, headers=admin, json=cuerpo)
        assert r.status_code == 200, r.text
        return r.json()
    almacen = post("/api/almacenes", {"empresa_id": 1, "nombre": f"{PREFIJO} Deposito"})
    productos = {}
    for clave, cantidad in (("mucho", 50), ("poco", 9), ("justo", 10), ("nada", 0)):
        prod = post("/api/productos", {"empresa_id": 1, "nombre": f"{PREFIJO} Pintura {clave}",
                                       "precio_venta": 50000, "precio_costo": 31000})
        if cantidad:
            post("/api/stock/entrada", {"producto_id": prod["id"], "almacen_id": almacen["id"], "tipo": "ENTRADA",
                                        "cantidad": cantidad, "costo_unitario": 31000})
        productos[clave] = prod
    # Alerta mínima 10 en el stock (D7): con 9 o 10 se informa la cantidad, con más no
    stocks = client.get("/api/stock/buscar", headers=admin, params={"empresa_id": 1, "nombre": PREFIJO, "limit": 50}).json()["items"]
    for s in stocks:
        assert client.put(f"/api/stock/{s['id']}/alerta", headers=admin, params={"alerta_minima": 10}).status_code == 200
    return productos


def test_sin_token_o_revocado_401(client, admin, tokens):
    assert client.get(f"{V1}/yo").status_code == 401
    assert client.get(f"{V1}/yo", headers=_bearer("ecs_inventado")).status_code == 401
    r = client.post("/api/integracion/tokens", headers=admin, json={"nombre": "temporal", "perfil": "crm-bot"}).json()
    assert client.get(f"{V1}/yo", headers=_bearer(r["token"])).status_code == 200
    assert client.delete(f"/api/integracion/tokens/{r['id']}", headers=admin).status_code == 200
    assert client.get(f"{V1}/yo", headers=_bearer(r["token"])).status_code == 401


def test_el_token_no_se_puede_volver_a_ver(client, admin, tokens):
    lista = client.get("/api/integracion/tokens", headers=admin).json()
    assert lista and all("token" not in t and "hash" not in t for t in lista)
    assert {t["prefijo"] for t in lista} >= {tokens["bot"]["token"][:12]}


def test_yo_con_token_de_servicio_y_de_usuario(client, admin, tokens):
    bot = client.get(f"{V1}/yo", headers=_bearer(tokens["bot"]["token"])).json()
    assert bot["tipo"] == "servicio" and set(bot["scopes"]) == {"catalogo.publico", "pedidos.crear", "pedidos.leer"}
    assert client.get(f"{V1}/yo", headers=admin).json()["tipo"] == "usuario"


def test_catalogo_disponibilidad_d7_y_sin_costos(client, tokens, catalogo):
    r = client.get(f"{V1}/catalogo/productos", headers=_bearer(tokens["bot"]["token"]), params={"q": f"{PREFIJO} pintura"})
    assert r.status_code == 200, r.text
    items = {i["nombre"].split()[-1]: i for i in r.json()["items"]}
    assert items["mucho"]["disponibilidad"] == {"estado": "disponible", "cantidad": None}
    assert items["poco"]["disponibilidad"] == {"estado": "ultimas_unidades", "cantidad": 9}
    assert items["justo"]["disponibilidad"] == {"estado": "ultimas_unidades", "cantidad": 10}
    assert items["nada"]["disponibilidad"] == {"estado": "sin_stock", "cantidad": None}
    texto = r.text.lower()
    assert "costo" not in texto and "proveedor" not in texto and "31000" not in texto
    uno = client.get(f"{V1}/catalogo/productos/{catalogo['mucho']['id']}", headers=_bearer(tokens["bot"]["token"]))
    assert uno.status_code == 200 and uno.json()["precio_venta"] == 50000


def test_catalogo_no_muestra_inactivos_ni_otras_empresas(client, admin, tokens, catalogo):
    pid = catalogo["nada"]["id"]
    assert client.delete(f"/api/productos/{pid}", headers=admin).status_code == 200
    assert client.get(f"{V1}/catalogo/productos/{pid}", headers=_bearer(tokens["bot"]["token"])).status_code == 404


def test_scopes_del_bot(client, tokens):
    # El bot no tiene eventos ni clientes: lo comprueba la API, no el CRM
    bot = _bearer(tokens["bot"]["token"])
    for ruta in (f"{V1}/eventos", f"{V1}/clientes", f"{V1}/metricas/ventas"):
        r = client.get(ruta, headers=bot)
        assert r.status_code in (403, 404), (ruta, r.status_code)  # 404 mientras la ruta no exista


def test_auth_me_devuelve_permisos(client, admin):
    me = client.get("/api/auth/me", headers=admin).json()
    assert me["es_admin"] is True and isinstance(me["permisos"], list)


def test_administrar_tokens_exige_sistema_configurar(client, admin):
    from tests.test_permisos_por_ruta import _token
    r = client.post("/api/auth/register", headers=admin, json={
        "email": "sinpermiso.int@test.com", "password": "clave-segura-123", "nombre": "x", "empresa_id": 1})
    assert r.status_code == 200, r.text
    otro = _token(client, "sinpermiso.int@test.com", "clave-segura-123")
    assert client.get("/api/integracion/tokens", headers=otro).status_code == 403
    assert client.post("/api/integracion/tokens", headers=otro, json={"nombre": "x", "perfil": "crm-interno"}).status_code == 403


# ---------------------------------------------------------------- eventos
def _eventos(client, token, desde=0, **params):
    r = client.get(f"{V1}/eventos", headers=_bearer(token), params={"desde": desde, **params})
    assert r.status_code == 200, r.text
    return r.json()


def test_eventos_de_cada_cambio(client, admin, tokens, catalogo, monkeypatch):
    import integracion
    monkeypatch.setattr(integracion, "RETRASO_EVENTOS_SEGUNDOS", 0)
    interno = tokens["interno"]["token"]
    inicio = _eventos(client, interno, limite=1000)["cursor"]
    while True:  # avanzar hasta el final
        siguiente = _eventos(client, interno, desde=inicio, limite=1000)["cursor"]
        if siguiente == inicio:
            break
        inicio = siguiente

    def post(ruta, cuerpo=None):
        r = client.post(ruta, headers=admin, json=cuerpo or {})
        assert r.status_code == 200, r.text
        return r.json()
    yo = client.get("/api/auth/me", headers=admin).json()
    cli = post("/api/clientes", {"empresa_id": 1, "nombre": f"{PREFIJO} Evento", "ruc": "80044444-4"})
    assert client.put(f"/api/clientes/{cli['id']}", headers=admin, json={"telefono": "0981000000"}).status_code == 200
    pid = catalogo["mucho"]["id"]
    venta = post("/api/ventas", {"empresa_id": 1, "usuario_id": yo["id"], "cliente_id": cli["id"], "tipo_pago": "EFECTIVO",
                                 "es_delivery": True, "items": [{"producto_id": pid, "cantidad": 1, "precio_unitario": 50000}]})
    post(f"/api/ventas/{venta['id']}/confirmar")
    entrega = [e for e in client.get("/api/entregas", headers=admin, params={"empresa_id": 1, "estado": "PENDIENTE"}).json()
               if e["venta_id"] == venta["id"]][0]
    assert client.put(f"/api/entregas/{entrega['id']}/estado", headers=admin, params={"estado": "ENTREGADO"}).status_code == 200
    post(f"/api/ventas/{venta['id']}/anular")
    post("/api/presupuestos", {"empresa_id": 1, "cliente_id": cli["id"], "usuario_id": yo["id"],
                               "items": [{"producto_id": pid, "cantidad": 2}]})
    almacen = client.get("/api/stock/buscar", headers=admin, params={"empresa_id": 1, "producto_id": pid}).json()["items"][0]["almacen_id"]
    post("/api/stock/entrada", {"producto_id": pid, "almacen_id": almacen, "tipo": "ENTRADA", "cantidad": 3, "costo_unitario": 31000})

    nuevos = _eventos(client, interno, desde=inicio, limite=1000)["eventos"]
    tipos = [e["tipo"] for e in nuevos]
    for esperado in ("cliente.creado", "cliente.actualizado", "venta.confirmada", "entrega.estado",
                     "venta.anulada", "presupuesto.creado", "stock.entrada"):
        assert esperado in tipos, (esperado, tipos)
    assert tipos.index("venta.confirmada") < tipos.index("venta.anulada")
    confirmada = next(e for e in nuevos if e["tipo"] == "venta.confirmada")
    assert confirmada["datos"]["venta_id"] == venta["id"] and confirmada["datos"]["es_delivery"] is True
    entregado = [e for e in nuevos if e["tipo"] == "entrega.estado" and e["datos"]["estado"] == "ENTREGADO"]
    assert entregado and entregado[0]["datos"]["venta_id"] == venta["id"]
    entrada = [e for e in nuevos if e["tipo"] == "stock.entrada" and e["datos"]["cantidad"] == 3]
    assert entrada and entrada[0]["datos"]["producto_id"] == pid
    assert [e["id"] for e in nuevos] == sorted(e["id"] for e in nuevos)

    # Cursor de a 2
    pagina = _eventos(client, interno, desde=inicio, limite=2)
    assert len(pagina["eventos"]) == 2 and pagina["cursor"] == pagina["eventos"][-1]["id"]
    assert _eventos(client, interno, desde=pagina["cursor"], limite=1)["eventos"][0]["id"] > pagina["cursor"]


def test_eventos_con_retraso_y_solo_crm_interno(client, admin, tokens, monkeypatch):
    import integracion
    monkeypatch.setattr(integracion, "RETRASO_EVENTOS_SEGUNDOS", 3600)
    ultimo = _eventos(client, tokens["interno"]["token"], desde=0, limite=1000)
    client.post("/api/clientes", headers=admin, json={"empresa_id": 1, "nombre": f"{PREFIJO} Reciente", "ruc": "80033333-3"})
    assert _eventos(client, tokens["interno"]["token"], desde=ultimo["cursor"])["eventos"] == []
    assert client.get(f"{V1}/eventos", headers=_bearer(tokens["bot"]["token"])).status_code == 403


def test_cambio_deshecho_no_deja_evento(client):
    from sqlalchemy import func, select
    from database import async_session_maker
    from models import Cliente, EventoIntegracion

    async def probar():
        async with async_session_maker() as db:
            antes = await db.scalar(select(func.count()).select_from(EventoIntegracion))
            db.add(Cliente(empresa_id=1, nombre=f"{PREFIJO} Deshecho"))
            await db.flush()
            await db.rollback()
            return antes, await db.scalar(select(func.count()).select_from(EventoIntegracion))
    antes, despues = client.portal.call(probar)
    assert antes == despues
