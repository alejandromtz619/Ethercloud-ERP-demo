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
    for ruta in (f"{V1}/eventos", f"{V1}/clientes?telefono=0981111222",
                 f"{V1}/metricas/ventas?desde=2026-01-01&hasta=2026-01-31", f"{V1}/clientes/1/resumen-360"):
        assert client.get(ruta, headers=bot).status_code == 403, ruta
    assert client.post(f"{V1}/clientes", headers=bot, json={"nombre": "x"}).status_code == 403


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


# ---------------------------------------------------------------- clientes, métricas y pedidos
@pytest.fixture(scope="module")
def contacto(client, tokens):
    r = client.post(f"{V1}/clientes", headers=_bearer(tokens["interno"]["token"]), json={
        "nombre": f"{PREFIJO} Contacto", "apellido": "WhatsApp", "telefono": "0981 555-123", "ruc": "80066666-6"})
    assert r.status_code == 200, r.text
    return r.json()


def test_buscar_cliente_por_telefono_en_cualquier_formato(client, tokens, contacto):
    interno = _bearer(tokens["interno"]["token"])
    for formato in ("595981555123", "+595 981 555 123", "0981555123", "981-555-123"):
        ids = [c["id"] for c in client.get(f"{V1}/clientes", headers=interno, params={"telefono": formato}).json()["items"]]
        assert ids == [contacto["id"]], formato
    assert client.get(f"{V1}/clientes", headers=interno, params={"telefono": "0981555124"}).json()["items"] == []
    for doc in ("80066666-6", "80066666"):
        ids = [c["id"] for c in client.get(f"{V1}/clientes", headers=interno, params={"documento": doc}).json()["items"]]
        assert ids == [contacto["id"]], doc
    assert client.get(f"{V1}/clientes", headers=interno).status_code == 400


def test_crear_cliente_duplicado_devuelve_el_existente(client, tokens, contacto):
    r = client.post(f"{V1}/clientes", headers=_bearer(tokens["interno"]["token"]), json={"nombre": "Otro", "ruc": "80066666-6"})
    assert r.status_code == 409 and r.json()["detail"]["cliente_id"] == contacto["id"]


@pytest.fixture(scope="module")
def bot_con_usuario(client, admin):
    yo = client.get("/api/auth/me", headers=admin).json()
    r = client.post("/api/integracion/tokens", headers=admin,
                    json={"nombre": f"{PREFIJO} bot", "perfil": "crm-bot", "usuario_id": yo["id"]})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _pedir(client, token, clave, cuerpo):
    return client.post(f"{V1}/pedidos", headers={**_bearer(token), "Idempotency-Key": clave}, json=cuerpo)


def test_pedido_queda_pendiente_con_precios_del_erp(client, admin, bot_con_usuario, contacto, catalogo):
    cuerpo = {"cliente_id": contacto["id"], "items": [{"producto_id": catalogo["mucho"]["id"], "cantidad": 2}]}
    r = _pedir(client, bot_con_usuario, "pedido-1", cuerpo)
    assert r.status_code == 200, r.text
    pedido = r.json()
    assert pedido["estado"] == "PENDIENTE" and pedido["total"] == 100000
    assert pedido["items"][0]["precio_unitario"] == 50000
    venta = client.get(f"/api/ventas/{pedido['venta_id']}", headers=admin).json()
    assert venta["estado"] == "PENDIENTE" and float(venta["total"]) == 100000
    # Mismo pedido reintentado: la misma venta, no otra
    otra = _pedir(client, bot_con_usuario, "pedido-1", cuerpo).json()
    assert (otra["pedido_id"], otra["venta_id"]) == (pedido["pedido_id"], pedido["venta_id"])
    # Misma clave con otro pedido: 409
    cuerpo2 = {**cuerpo, "items": [{"producto_id": catalogo["mucho"]["id"], "cantidad": 3}]}
    assert _pedir(client, bot_con_usuario, "pedido-1", cuerpo2).status_code == 409
    leido = client.get(f"{V1}/pedidos/{pedido['pedido_id']}", headers=_bearer(bot_con_usuario))
    assert leido.json()["estado"] == "PENDIENTE"


def test_pedidos_invalidos(client, tokens, bot_con_usuario, contacto, catalogo):
    base = {"cliente_id": contacto["id"], "items": [{"producto_id": catalogo["mucho"]["id"], "cantidad": 1}]}
    assert client.post(f"{V1}/pedidos", headers=_bearer(bot_con_usuario), json=base).status_code == 400  # sin clave
    assert _pedir(client, bot_con_usuario, "p-credito", {**base, "tipo_pago": "CREDITO"}).status_code == 422
    inactivo = {**base, "items": [{"producto_id": catalogo["nada"]["id"], "cantidad": 1}]}
    assert _pedir(client, bot_con_usuario, "p-inactivo", inactivo).status_code == 400
    cero = {**base, "items": [{"producto_id": catalogo["mucho"]["id"], "cantidad": 0}]}
    assert _pedir(client, bot_con_usuario, "p-cero", cero).status_code == 422
    assert _pedir(client, bot_con_usuario, "p-cliente", {**base, "cliente_id": 999999}).status_code == 404
    # Un token sin usuario asignado no puede registrar pedidos
    assert _pedir(client, tokens["bot"]["token"], "p-sin-usuario", base).status_code == 400


def test_el_bot_solo_ve_sus_pedidos(client, admin, bot_con_usuario, tokens, contacto, catalogo):
    yo = client.get("/api/auth/me", headers=admin).json()
    otro_bot = client.post("/api/integracion/tokens", headers=admin, json={
        "nombre": f"{PREFIJO} otro bot", "perfil": "crm-bot", "usuario_id": yo["id"]}).json()["token"]
    pedido = _pedir(client, bot_con_usuario, "pedido-propio", {
        "cliente_id": contacto["id"], "items": [{"producto_id": catalogo["mucho"]["id"], "cantidad": 1}]}).json()
    assert client.get(f"{V1}/pedidos/{pedido['pedido_id']}", headers=_bearer(otro_bot)).status_code == 404
    assert client.get(f"{V1}/pedidos/{pedido['pedido_id']}", headers=_bearer(tokens["interno"]["token"])).status_code == 200


def test_resumen_360_y_credito_segun_permiso(client, admin, tokens, contacto, catalogo, bot_con_usuario):
    from tests.test_permisos_por_ruta import _token
    pedido = _pedir(client, bot_con_usuario, "pedido-360", {
        "cliente_id": contacto["id"], "items": [{"producto_id": catalogo["mucho"]["id"], "cantidad": 4}]}).json()
    assert client.post(f"/api/ventas/{pedido['venta_id']}/confirmar-pendiente", headers=admin).status_code == 200
    interno = _bearer(tokens["interno"]["token"])
    resumen = client.get(f"{V1}/clientes/{contacto['id']}/resumen-360", headers=interno).json()
    assert resumen["compras"]["cantidad"] >= 1 and resumen["compras"]["total"] >= 200000
    assert resumen["productos_mas_comprados"][0]["producto_id"] == catalogo["mucho"]["id"]
    assert "credito" in resumen
    # Un usuario con clientes.ver pero sin clientes.ver_creditos no ve el crédito
    permisos = {p["clave"]: p["id"] for p in client.get("/api/permisos", headers=admin).json()}
    rol = client.post("/api/roles", headers=admin, json={"nombre": "VENDEDOR CRM", "empresa_id": 1}).json()
    client.post(f"/api/roles/{rol['id']}/permisos/{permisos['clientes.ver']}", headers=admin)
    r = client.post("/api/auth/register", headers=admin, json={
        "email": "vendedor.crm@test.com", "password": "clave-segura-123", "nombre": "Vendedor", "empresa_id": 1})
    client.post(f"/api/usuarios/{r.json()['usuario']['id']}/roles/{rol['id']}", headers=admin)
    vendedor = _token(client, "vendedor.crm@test.com", "clave-segura-123")
    sin_credito = client.get(f"{V1}/clientes/{contacto['id']}/resumen-360", headers=vendedor)
    assert sin_credito.status_code == 200 and "credito" not in sin_credito.json()
    assert client.get(f"{V1}/clientes/999999/resumen-360", headers=interno).status_code == 404


def test_metricas_de_ventas(client, tokens, contacto):
    from datetime import date, timedelta
    hoy = date.today()
    interno = _bearer(tokens["interno"]["token"])
    params = {"desde": (hoy - timedelta(days=30)).isoformat(), "hasta": hoy.isoformat(), "por": "dia",
              "cliente_id": contacto["id"]}
    r = client.get(f"{V1}/metricas/ventas", headers=interno, params=params)
    assert r.status_code == 200, r.text
    series = r.json()["series"]
    assert sum(p["cantidad"] for p in series) >= 1 and sum(p["total"] for p in series) >= 200000
    mes = client.get(f"{V1}/metricas/ventas", headers=interno, params={**params, "por": "mes"}).json()
    assert sum(p["total"] for p in mes["series"]) == sum(p["total"] for p in series)
    largo = {**params, "desde": (hoy - timedelta(days=400)).isoformat()}
    assert client.get(f"{V1}/metricas/ventas", headers=interno, params=largo).status_code == 400
