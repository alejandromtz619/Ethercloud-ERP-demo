"""
IVA por ítem (iva.py): productos al 10 %, 5 % y exentos, con descuento de cliente. Las cuentas se
pueden seguir a mano: descuento 10 %, Gs. 11.000 al 10 %, 10.500 al 5 % y 5.000 exentos.

    pytest backend/tests/test_iva.py
"""
from decimal import Decimal

import pytest

from iva import desglose_iva, iva_total, liquidacion_impresa

PREFIJO = "ZZIVA"


def test_desglose_a_mano():
    d = desglose_iva([(11000, 10), (10500, 5), (5000, 0)], Decimal("23850"))  # 26.500 - 10 %
    assert {t: (v["bruto"], v["neto"], v["iva"]) for t, v in d.items()} == {
        10: (11000, 9900, 900), 5: (10500, 9450, 450), 0: (5000, 4500, 0)}
    assert iva_total(d) == 1350
    assert liquidacion_impresa(d) == {"iva_5": 450, "iva_10": 900, "total_iva": 1350}


def test_todo_al_10_da_lo_de_siempre():
    total = Decimal("123456.78")
    d = desglose_iva([(Decimal("100000"), 10), (Decimal("37174.20"), 10)], total)
    assert iva_total(d) == total * Decimal("10") / Decimal("110")
    viejo = round(float(total) - float(total) / 1.10, 0)
    assert liquidacion_impresa(d) == {"iva_5": 0, "iva_10": viejo, "total_iva": viejo}


@pytest.fixture(scope="module")
def escenario(client, admin):
    def post(ruta, cuerpo):
        r = client.post(ruta, headers=admin, json=cuerpo)
        assert r.status_code == 200, r.text
        return r.json()

    almacen = post("/api/almacenes", {"empresa_id": 1, "nombre": f"{PREFIJO} Deposito"})
    productos = {}
    for clave, precio, tasa in (("diez", 11000, 10), ("cinco", 10500, 5), ("exento", 5000, 0)):
        productos[clave] = post("/api/productos", {"empresa_id": 1, "nombre": f"{PREFIJO} {clave}",
                                                   "precio_venta": precio, "precio_costo": 1000, "tasa_iva": tasa})
        post("/api/stock/entrada", {"producto_id": productos[clave]["id"], "almacen_id": almacen["id"],
                                    "tipo": "ENTRADA", "cantidad": 50, "costo_unitario": 1000})
    cliente = post("/api/clientes", {"empresa_id": 1, "nombre": f"{PREFIJO} Cliente", "ruc": "80077777-7",
                                     "descuento_porcentaje": 10, "limite_credito": 0})
    yo = client.get("/api/auth/me", headers=admin).json()

    def vender(claves, tipo_pago="EFECTIVO"):
        venta = post("/api/ventas", {"empresa_id": 1, "usuario_id": yo["id"], "cliente_id": cliente["id"],
                                     "tipo_pago": tipo_pago, "items": [
                                         {"producto_id": productos[c]["id"], "cantidad": 1,
                                          "precio_unitario": productos[c]["precio_venta"]} for c in claves]})
        return post(f"/api/ventas/{venta['id']}/confirmar", {})
    return {"productos": productos, "cliente": cliente, "vender": vender}


def test_venta_mixta_guarda_el_iva_correcto(escenario):
    venta = escenario["vender"](["diez", "cinco", "exento"])
    assert Decimal(str(venta["total"])) == 23850
    assert Decimal(str(venta["iva"])) == 1350


def test_factura_y_boleta_imprimen_cada_tasa(client, admin, escenario):
    venta = escenario["vender"](["diez", "cinco", "exento"])
    factura = client.get(f"/api/ventas/{venta['id']}/factura", headers=admin).json()
    columnas = {i["descripcion"]: (i["exenta"], i["iva_5"], i["iva_10"]) for i in factura["items"]}
    assert columnas == {f"{PREFIJO} diez": (0, 0, 11000), f"{PREFIJO} cinco": (0, 10500, 0),
                        f"{PREFIJO} exento": (5000, 0, 0)}
    assert (factura["subtotal_exenta"], factura["subtotal_iva_5"], factura["subtotal_iva_10"]) == (5000, 10500, 11000)
    assert factura["liquidacion_iva"] == {"iva_5": 450, "iva_10": 900, "total_iva": 1350}
    boleta = client.get(f"/api/ventas/{venta['id']}/boleta", headers=admin).json()
    assert sorted(i["iva"] for i in boleta["items"]) == [0, 5, 10]
    assert boleta["iva"] == 1350


def test_venta_toda_al_10_imprime_igual_que_antes(client, admin, escenario):
    venta = escenario["vender"](["diez"])
    factura = client.get(f"/api/ventas/{venta['id']}/factura", headers=admin).json()
    total = float(venta["total"])
    viejo = round(total - total / 1.10, 0)
    assert factura["liquidacion_iva"] == {"iva_5": 0, "iva_10": viejo, "total_iva": viejo}
    assert (factura["subtotal_exenta"], factura["subtotal_iva_5"], factura["subtotal_iva_10"]) == (
        0, 0, float(venta["total"]) + float(venta["descuento"]))


def test_cambiar_la_tasa_no_cambia_ventas_hechas(client, admin, escenario):
    venta = escenario["vender"](["cinco"])
    pid = escenario["productos"]["cinco"]["id"]
    assert client.put(f"/api/productos/{pid}", headers=admin, json={"tasa_iva": 10}).status_code == 200
    factura = client.get(f"/api/ventas/{venta['id']}/factura", headers=admin).json()
    assert factura["liquidacion_iva"]["iva_5"] == 450 and factura["liquidacion_iva"]["iva_10"] == 0
    assert client.put(f"/api/productos/{pid}", headers=admin, json={"tasa_iva": 5}).status_code == 200


def test_tasas_invalidas(client, admin, escenario):
    pid = escenario["productos"]["diez"]["id"]
    assert client.put(f"/api/productos/{pid}", headers=admin, json={"tasa_iva": 7}).status_code == 400
    assert client.post("/api/productos", headers=admin, json={
        "empresa_id": 1, "nombre": "x", "precio_venta": 1, "tasa_iva": 7}).status_code == 422


def test_factura_grupal_suma_el_iva_de_cada_boleta(client, admin, escenario):
    ventas = [escenario["vender"](["diez", "exento"]), escenario["vender"](["cinco"])]
    r = client.post("/api/facturas/grupal", headers=admin, json={
        "empresa_id": 1, "cliente_id": escenario["cliente"]["id"], "venta_ids": [v["id"] for v in ventas],
        "cobrar_credito": True})
    assert r.status_code == 200, r.text
    # Neto: 9.900 al 10 % (IVA 900), 4.500 exento, 9.450 al 5 % (IVA 450)
    assert Decimal(str(r.json()["iva"])) == 1350
    impresa = client.get(f"/api/facturas/grupal/{r.json()['id']}/imprimir", headers=admin).json()
    assert impresa["liquidacion_iva"] == {"iva_5": 450, "iva_10": 900, "total_iva": 1350}
    assert (impresa["subtotal_exenta"], impresa["subtotal_iva_5"], impresa["subtotal_iva_10"]) == (4500, 9450, 9900)
    assert sum(impresa[k] for k in ("subtotal_exenta", "subtotal_iva_5", "subtotal_iva_10")) == impresa["total"]


def test_pdfs_con_tasas_mezcladas(client, admin, escenario):
    venta = escenario["vender"](["diez", "cinco", "exento"])
    for tipo in ("BOLETA", "FACTURA"):
        r = client.post(f"/api/ventas/{venta['id']}/generar-enlace", headers=admin, params={"tipo_documento": tipo})
        assert r.status_code == 200, r.text
    yo = client.get("/api/auth/me", headers=admin).json()
    presupuesto = client.post("/api/presupuestos", headers=admin, json={
        "empresa_id": 1, "cliente_id": escenario["cliente"]["id"], "usuario_id": yo["id"],
        "items": [{"producto_id": escenario["productos"][c]["id"], "cantidad": 1} for c in ("diez", "cinco", "exento")]})
    assert presupuesto.status_code == 200, presupuesto.text
    assert sorted(i["tasa_iva"] for i in presupuesto.json()["items"]) == [0, 5, 10]
    pdf = client.get(f"/api/presupuestos/{presupuesto.json()['id']}/pdf", headers=admin)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
