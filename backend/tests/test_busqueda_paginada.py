"""
Búsqueda paginada en el servidor: /productos/buscar, /stock/buscar y el BI de aging.
Reemplazan descargar listas completas para filtrar en el navegador.

    pytest backend/tests/test_busqueda_paginada.py
"""
import pytest

PREFIJO = "ZZBUSQ"  # nombres únicos para no chocar con otros datos de la base de prueba


@pytest.fixture(scope="module")
def datos(client, admin):
    def post(ruta, cuerpo):
        r = client.post(ruta, headers=admin, json=cuerpo)
        assert r.status_code == 200, r.text
        return r.json()

    cat = post("/api/categorias", {"empresa_id": 1, "nombre": f"{PREFIJO} Pinturas"})
    marca = post("/api/marcas", {"empresa_id": 1, "nombre": f"{PREFIJO} Acme"})
    almacen = post("/api/almacenes", {"empresa_id": 1, "nombre": f"{PREFIJO} Deposito"})

    def producto(nombre, codigo, **extra):
        return post("/api/productos", {"empresa_id": 1, "nombre": nombre, "codigo_barra": codigo,
                                       "precio_venta": 10000, "precio_costo": 6000, **extra})

    p = {
        "latex_blanco": producto(f"{PREFIJO} Latex Blanco 4L", f"{PREFIJO}-001",
                                 categoria_id=cat["id"], marca_id=marca["id"]),
        "latex_negro": producto(f"{PREFIJO} Latex Negro 1L", f"{PREFIJO}-002"),
        "barniz": producto(f"{PREFIJO} Barniz 50% Brillo", f"{PREFIJO}-003"),
        "inactivo": producto(f"{PREFIJO} Latex Viejo", f"{PREFIJO}-004"),
    }
    assert client.delete(f"/api/productos/{p['inactivo']['id']}", headers=admin).status_code == 200
    for clave, cantidad in (("latex_blanco", 7), ("latex_negro", 3)):
        r = client.post("/api/stock/entrada", headers=admin, json={
            "producto_id": p[clave]["id"], "almacen_id": almacen["id"], "tipo": "ENTRADA",
            "cantidad": cantidad, "costo_unitario": 6000,
        })
        assert r.status_code == 200, r.text
    return p


def _buscar(client, admin, ruta, **params):
    r = client.get(ruta, headers=admin, params={"empresa_id": 1, **params})
    assert r.status_code == 200, r.text
    return r.json()


def _nombres(pagina):
    return [x["nombre"] for x in pagina["items"]]


def test_q_busca_por_nombre_y_codigo_sin_inactivos(client, admin, datos):
    pagina = _buscar(client, admin, "/api/productos/buscar", q=f"{PREFIJO} latex")
    assert pagina["total"] == 2
    assert set(_nombres(pagina)) == {f"{PREFIJO} Latex Blanco 4L", f"{PREFIJO} Latex Negro 1L"}

    pagina = _buscar(client, admin, "/api/productos/buscar", q=f"{PREFIJO}-003")
    assert _nombres(pagina) == [f"{PREFIJO} Barniz 50% Brillo"]


def test_comodines_del_usuario_se_toman_literalmente(client, admin, datos):
    pagina = _buscar(client, admin, "/api/productos/buscar", q="50%")
    assert f"{PREFIJO} Barniz 50% Brillo" in _nombres(pagina)
    assert all("50%" in n for n in _nombres(pagina))
    assert _buscar(client, admin, "/api/productos/buscar", q=f"{PREFIJO}_Latex")["total"] == 0


def test_q_numerico_encuentra_por_id_primero(client, admin, datos):
    pid = datos["latex_negro"]["id"]
    pagina = _buscar(client, admin, "/api/productos/buscar", q=str(pid))
    assert pagina["items"][0]["id"] == pid


def test_filtros_de_la_pantalla_productos(client, admin, datos):
    def ids(**params):
        return {x["id"] for x in _buscar(client, admin, "/api/productos/buscar", **params)["items"]}

    assert ids(nombre=f"{PREFIJO} latex") == {datos["latex_blanco"]["id"], datos["latex_negro"]["id"]}
    assert ids(producto_id=datos["barniz"]["id"]) == {datos["barniz"]["id"]}
    assert ids(codigo=f"{PREFIJO}-00", nombre=PREFIJO) == {
        datos["latex_blanco"]["id"], datos["latex_negro"]["id"], datos["barniz"]["id"]}
    assert ids(marca=f"{PREFIJO} acme") == {datos["latex_blanco"]["id"]}
    assert ids(categoria=f"{PREFIJO} pint") == {datos["latex_blanco"]["id"]}


def test_paginacion_y_stock_total(client, admin, datos):
    todas = _buscar(client, admin, "/api/productos/buscar", nombre=PREFIJO, limit=50)
    assert todas["total"] == 3
    primera = _buscar(client, admin, "/api/productos/buscar", nombre=PREFIJO, limit=2, offset=0)
    segunda = _buscar(client, admin, "/api/productos/buscar", nombre=PREFIJO, limit=2, offset=2)
    assert primera["total"] == segunda["total"] == 3
    assert len(primera["items"]) == 2 and len(segunda["items"]) == 1
    assert {x["id"] for x in primera["items"] + segunda["items"]} == {x["id"] for x in todas["items"]}
    stock = {x["id"]: x["stock_total"] for x in todas["items"]}
    assert stock[datos["latex_blanco"]["id"]] == 7
    assert stock[datos["barniz"]["id"]] == 0


def test_limites_de_parametros(client, admin):
    for params in ({"limit": 0}, {"limit": 501}, {"offset": -1}):
        r = client.get("/api/productos/buscar", headers=admin, params={"empresa_id": 1, **params})
        assert r.status_code == 422


def test_stock_buscar_filtra_y_pagina(client, admin, datos):
    pagina = _buscar(client, admin, "/api/stock/buscar", nombre=PREFIJO)
    assert pagina["total"] == 2
    assert [x["producto_nombre"] for x in pagina["items"]] == [
        f"{PREFIJO} Latex Blanco 4L", f"{PREFIJO} Latex Negro 1L"]  # ordenado por nombre
    assert _buscar(client, admin, "/api/stock/buscar", codigo=f"{PREFIJO}-002")["items"][0]["cantidad"] == 3
    assert _buscar(client, admin, "/api/stock/buscar",
                   producto_id=datos["latex_blanco"]["id"])["items"][0]["cantidad"] == 7
    assert len(_buscar(client, admin, "/api/stock/buscar", nombre=PREFIJO, limit=1)["items"]) == 1


def test_aging_paginado_con_resumen_completo(client, admin, datos):
    completo = _buscar(client, admin, "/api/bi/aging-tandas", limit=1000)
    pagina = _buscar(client, admin, "/api/bi/aging-tandas", limit=1)
    assert pagina["resumen"] == completo["resumen"]
    assert pagina["total_productos"] == completo["total_productos"] == len(completo["productos"])
    assert pagina["productos"] == completo["productos"][:1]
    filtrado = _buscar(client, admin, "/api/bi/aging-tandas", q=f"{PREFIJO} latex")
    assert {p["producto_nombre"] for p in filtrado["productos"]} == {
        f"{PREFIJO} Latex Blanco 4L", f"{PREFIJO} Latex Negro 1L"}


def test_totales_por_almacen(client, admin, datos):
    totales = {t["almacen_id"]: t["total_unidades"]
               for t in _buscar(client, admin, "/api/stock/totales-por-almacen")}
    deposito = _buscar(client, admin, "/api/stock/buscar", nombre=PREFIJO)["items"][0]["almacen_id"]
    assert totales[deposito] == 7 + 3


@pytest.fixture(scope="module")
def clientes(client, admin):
    creados = {}
    for clave, datos_cliente in {
        "ana": {"nombre": f"{PREFIJO}Ana", "apellido": "Benitez", "ruc": "80012345-6", "telefono": "0981111222"},
        "luis": {"nombre": f"{PREFIJO}Luis", "apellido": "Gimenez", "cedula": "4567890"},
        "bajo": {"nombre": f"{PREFIJO}Baja", "apellido": "Inactiva", "ruc": "80099999-1"},
    }.items():
        r = client.post("/api/clientes", headers=admin, json={"empresa_id": 1, **datos_cliente})
        assert r.status_code == 200, r.text
        creados[clave] = r.json()
    assert client.delete(f"/api/clientes/{creados['bajo']['id']}", headers=admin).status_code == 200
    return creados


def test_clientes_buscar(client, admin, clientes):
    def ids(**params):
        return {c["id"] for c in _buscar(client, admin, "/api/clientes/buscar", **params)["items"]}

    assert ids(q=PREFIJO) == {clientes["ana"]["id"], clientes["luis"]["id"]}  # sin el inactivo
    assert ids(q="80012345") == {clientes["ana"]["id"]}                       # RUC
    assert ids(q="4567890") == {clientes["luis"]["id"]}                       # cédula
    assert ids(q="0981111") == {clientes["ana"]["id"]}                        # teléfono
    assert ids(q=f"{PREFIJO}ana benitez") == {clientes["ana"]["id"]}          # nombre + apellido
    assert _buscar(client, admin, "/api/clientes/buscar",
                   q=str(clientes["luis"]["id"]))["items"][0]["id"] == clientes["luis"]["id"]
    pagina = _buscar(client, admin, "/api/clientes/buscar", q=PREFIJO, limit=1)
    assert pagina["total"] == 2 and len(pagina["items"]) == 1


def test_presupuestos_y_entregas_paginan_sin_romper_lo_anterior(client, admin, datos, clientes):
    for _ in range(3):
        r = client.post("/api/presupuestos", headers=admin, json={
            "empresa_id": 1, "cliente_id": clientes["ana"]["id"], "usuario_id": 1,
            "items": [{"producto_id": datos["latex_blanco"]["id"], "cantidad": 1}],
        })
        assert r.status_code == 200, r.text
    todos = client.get("/api/presupuestos", headers=admin,
                       params={"empresa_id": 1, "cliente_id": clientes["ana"]["id"]}).json()
    assert len(todos) == 3
    pagina = client.get("/api/presupuestos", headers=admin,
                        params={"empresa_id": 1, "cliente_id": clientes["ana"]["id"], "limit": 2, "offset": 2}).json()
    assert [p["id"] for p in pagina] == [todos[2]["id"]]
    r = client.get("/api/entregas", headers=admin, params={"empresa_id": 1, "limit": 5, "estado": "ENTREGADO"})
    assert r.status_code == 200 and isinstance(r.json(), list)


def test_exceso_limita_listas_con_resumen_completo(client, admin, datos):
    completo = _buscar(client, admin, "/api/bi/exceso-compras", limite=10000)
    recortado = _buscar(client, admin, "/api/bi/exceso-compras", limite=1)
    assert recortado["resumen"] == completo["resumen"]
    assert recortado["sin_ventas_recientes"] == completo["sin_ventas_recientes"][:1]
    assert recortado["exceso_stock"] == completo["exceso_stock"][:1]
    assert completo["resumen"]["productos_sin_ventas"] == len(completo["sin_ventas_recientes"])


def test_aging_totales_por_producto(client, admin, datos):
    """Tandas sin FIFO (restante NULL), sin fecha y con costo con decimales: los totales que
    calcula la base coinciden con el detalle de cada tanda."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    from sqlalchemy import text
    import server

    prod = client.post("/api/productos", headers=admin, json={
        "empresa_id": 1, "nombre": f"{PREFIJO} Aging Sellador", "precio_venta": 10000, "precio_costo": 6000}).json()
    almacen = _buscar(client, admin, "/api/stock/buscar", nombre=PREFIJO)["items"][0]["almacen_id"]
    r = client.post("/api/stock/entrada", headers=admin, json={
        "producto_id": prod["id"], "almacen_id": almacen, "tipo": "ENTRADA", "cantidad": 5, "costo_unitario": 6000})
    assert r.status_code == 200, r.text
    hace_10_dias = datetime.now(ZoneInfo("America/Asuncion")) - timedelta(days=10)

    async def insertar():
        async with server.engine.begin() as conn:
            await conn.execute(text(
                "INSERT INTO movimientos_stock (producto_id, almacen_id, tipo, cantidad, cantidad_restante, costo_unitario, creado_en) "
                "VALUES (:p, :a, 'ENTRADA', 3, NULL, 2.5, :f), (:p, :a, 'ENTRADA', 2, 2, 1000, NULL)"),
                {"p": prod["id"], "a": almacen, "f": hace_10_dias.strftime("%Y-%m-%d %H:%M:%S.%f")})
    client.portal.call(insertar)

    pagina = _buscar(client, admin, "/api/bi/aging-tandas", q=f"{PREFIJO} aging")
    assert pagina["total_productos"] == 1
    p = pagina["productos"][0]
    assert sorted((t["dias_aging"], t["cantidad_restante"], t["valor_inmovilizado"], t["sin_fifo"])
                  for t in p["tandas"]) == [(0, 2, 2000, False), (0, 5, 30000, False), (10, 3, 8, True)]
    assert (p["num_tandas"], p["dias_aging_max"], p["dias_aging_min"]) == (3, 10, 0)
    assert p["total_unidades_restantes"] == 10
    assert p["valor_total_inmovilizado"] == sum(t["valor_inmovilizado"] for t in p["tandas"]) == 32008
    assert (p["stock_real"], p["fifo_diferencia"], p["fifo_concuerda"]) == (5, 5, False)

    completo = _buscar(client, admin, "/api/bi/aging-tandas", limit=1000)
    for orden, clave, invertido in (("mas_antiguo", "dias_aging_max", True), ("mas_nuevo", "dias_aging_min", False),
                                    ("mayor_valor", "valor_total_inmovilizado", True)):
        lista = _buscar(client, admin, "/api/bi/aging-tandas", orden=orden, limit=1000)["productos"]
        assert [x[clave] for x in lista] == sorted((x[clave] for x in lista), reverse=invertido)
    assert completo["resumen"]["valor_stock_activo"] == sum(x["valor_total_inmovilizado"] for x in completo["productos"])
    assert completo["resumen"]["total_tandas_activas"] == sum(x["num_tandas"] for x in completo["productos"])
