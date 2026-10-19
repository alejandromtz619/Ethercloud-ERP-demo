"""
Facturación electrónica contra el SANDBOX real de SIFEN SIS (aprueba solo, sin ir a SIFEN). Sólo corre
con la API key de sandbox en el entorno; usa un punto de expedición propio de las pruebas.

    SIFENSIS_API_KEY=gk_... SIFEN_PRUEBA_PUNTO=901 pytest backend/tests/test_fiscal_sandbox.py -s

La key NO se usa como variable de entorno del servidor: la prueba la carga por la pantalla
Configuración (PUT /api/configuracion), como lo haría el cliente.
"""
import asyncio
import os
import time

import pytest

import server
import configuracion
from fiscal.servicio import FacturacionElectronica
from fiscal.sifensis import SifenSis

pytestmark = pytest.mark.skipif(not os.environ.get("SIFENSIS_API_KEY"), reason="sin SIFENSIS_API_KEY de sandbox")
PREFIJO = "SANDBOX"
SALIDA = os.environ.get("SIFEN_PRUEBA_SALIDA")  # carpeta donde guardar los KuDE para mirarlos
PUNTO = os.environ.get("SIFEN_PRUEBA_PUNTO", "901").zfill(3)


@pytest.fixture(scope="module")
def sandbox(client, admin):
    api_key = os.environ.pop("SIFENSIS_API_KEY")  # que no la pise la variable de entorno
    os.environ.setdefault("CLAVE_CIFRADO", "clave-de-cifrado-de-prueba-sandbox-0123456789")
    server.MODULOS_ACTIVOS.add("fe")
    server.app.state.facturacion = FacturacionElectronica()
    r = client.put("/api/configuracion/facturacion_electronica", headers=admin,
                   json={"valores": {"fe.api_key": api_key, "fe.punto": PUNTO}})
    assert r.status_code == 200, r.text
    yield SifenSis(api_key=api_key)
    client.put("/api/configuracion/facturacion_electronica", headers=admin,
               json={"valores": {"fe.api_key": None, "fe.punto": None}})
    server.app.state.facturacion = None
    server.MODULOS_ACTIVOS.discard("fe")
    os.environ["SIFENSIS_API_KEY"] = api_key
    configuracion.invalidar_cache()


def test_probar_conexion_desde_la_pantalla(client, admin, sandbox):
    r = client.post("/api/configuracion/facturacion_electronica/probar", headers=admin).json()
    print("\nprobar conexión:", r)
    assert r["ok"] and r["ambiente"] == "SANDBOX" and r["punto"] == PUNTO


@pytest.fixture(scope="module")
def vender(client, admin, sandbox):
    def post(ruta, cuerpo):
        r = client.post(ruta, headers=admin, json=cuerpo)
        assert r.status_code == 200, r.text
        return r.json()

    almacen = post("/api/almacenes", {"empresa_id": 1, "nombre": f"{PREFIJO} Deposito"})
    productos = {}
    for clave, precio, tasa, unidad in (("diez", 110000, 10, 77), ("cinco", 21000, 5, 77), ("exento", 15000, 0, 77),
                                        ("decimal", 3333.33, 10, 77), ("kilo", 8500, 10, 83)):
        productos[clave] = post("/api/productos", {"empresa_id": 1, "nombre": f"{PREFIJO} Producto {clave}",
                                                   "precio_venta": precio, "precio_costo": 1000, "tasa_iva": tasa,
                                                   "unidad_medida": unidad})
        post("/api/stock/entrada", {"producto_id": productos[clave]["id"], "almacen_id": almacen["id"],
                                    "tipo": "ENTRADA", "cantidad": 100, "costo_unitario": 1000})
    clientes = {
        "empresa": post("/api/clientes", {"empresa_id": 1, "nombre": "Cliente de Prueba S.A.", "ruc": "80069563-1",
                                          "direccion": "Avda. Mcal. López", "numero_casa": 1234, "departamento": 1,
                                          "distrito": 1, "ciudad": 1, "telefono": "021 555 123",
                                          "email": "compras@prueba.com.py", "descuento_porcentaje": 7.5, "limite_credito": 50_000_000}),
        "cedula": post("/api/clientes", {"empresa_id": 1, "nombre": "Juana", "apellido": "Pérez Sandbox", "cedula": "3456789",
                                         "limite_credito": 50_000_000}),
        "anonimo": post("/api/clientes", {"empresa_id": 1, "nombre": f"{PREFIJO} Mostrador"}),
    }
    yo = client.get("/api/auth/me", headers=admin).json()

    def _vender(cliente, claves, tipo_pago="EFECTIVO", cantidad=1):
        venta = post("/api/ventas", {"empresa_id": 1, "usuario_id": yo["id"], "cliente_id": clientes[cliente]["id"],
                                     "tipo_pago": tipo_pago, "items": [
                                         {"producto_id": productos[c]["id"], "cantidad": cantidad,
                                          "precio_unitario": productos[c]["precio_venta"]} for c in claves]})
        return post(f"/api/ventas/{venta['id']}/confirmar", {})
    return _vender


def esperar_aprobacion(client, admin, doc_id, tope=90):
    inicio = time.time()
    while time.time() - inicio < tope:
        doc = client.post(f"/api/fiscal/documentos/{doc_id}/reintentar", headers=admin).json()
        if doc.get("estado") in ("APROBADO", "RECHAZADO"):
            return doc, time.time() - inicio
        time.sleep(3)
    return doc, None


def test_estado_de_la_cuenta(client, admin, sandbox):
    r = client.get("/api/fiscal/estado", headers=admin).json()
    print("\nemisor:", r)
    assert r["conectado"] and r["ambiente"] == "SANDBOX" and "001" in r["establecimientos"]


def test_ciclo_completo_factura_contado(client, admin, vender):
    """Emitir → APROBADO → KuDE (A4 y ticket), con IVA 10/5/exento y descuento del cliente."""
    venta = vender("empresa", ("diez", "cinco", "exento"), cantidad=2)
    r = client.post(f"/api/fiscal/ventas/{venta['id']}/factura", headers=admin)
    assert r.status_code == 200, r.text
    doc = r.json()
    print("\nemitida:", doc["numero"], doc["estado"], doc["cdc"], "total", doc["total"], "venta", venta["total"])
    assert doc["estado"] in ("GENERADO", "ENVIADO", "APROBADO") and len(doc["cdc"]) == 44
    doc, segundos = esperar_aprobacion(client, admin, doc["id"])
    print("estado final:", doc["estado"], f"en {segundos:.0f} s" if segundos else "(sin respuesta)", doc["mensaje"])
    assert doc["estado"] == "APROBADO"
    for formato in ("a4", "ticket"):
        pdf = client.get(f"/api/fiscal/documentos/{doc['id']}/kude", headers=admin, params={"formato": formato})
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF"), pdf.text[:200]
        if SALIDA:
            with open(os.path.join(SALIDA, f"kude_{formato}.pdf"), "wb") as f:
                f.write(pdf.content)
    xml = client.get(f"/api/fiscal/documentos/{doc['id']}/xml", headers=admin)
    assert xml.status_code == 200 and b"<" in xml.content[:100]


def test_consumidor_final_cedula_credito_y_decimales(client, admin, vender):
    casos = [("anonimo", ("diez",), "TARJETA"), ("cedula", ("cinco", "exento"), "CREDITO"), ("empresa", ("kilo",), "TRANSFERENCIA"),
             ("anonimo", ("decimal",), "TRANSFERENCIA"), ("empresa", ("decimal", "diez"), "EFECTIVO")]
    for cliente, claves, pago in casos:
        venta = vender(cliente, claves, pago, cantidad=3)
        r = client.post(f"/api/fiscal/ventas/{venta['id']}/factura", headers=admin)
        print(f"\n{cliente} {pago}:", r.status_code, r.json().get("numero"), r.json().get("estado"),
              r.json().get("total"), "venta", venta["total"], r.json().get("mensaje") or r.json().get("detail"))
        assert r.status_code == 200 and r.json()["estado"] != "INVALIDO", r.text


def test_reintento_identico_devuelve_el_mismo_documento(client, admin, vender, sandbox):
    """El proveedor reconoce la numeración: reenviar lo mismo no duplica (lo que hace el seguimiento
    cuando una respuesta se pierde)."""
    venta = vender("anonimo", ("diez",))
    doc = client.post(f"/api/fiscal/ventas/{venta['id']}/factura", headers=admin).json()

    async def reenviar():
        from database import async_session_maker
        from models import DocumentoFiscal
        from fiscal.servicio import metadata
        async with async_session_maker() as db:
            fila = await db.get(DocumentoFiscal, doc["id"])
            return await sandbox.emitir(fila.datos, metadata())

    r = client.portal.call(reenviar)
    print("\nreintento:", r.duplicado, r.cdc == doc["cdc"], r.estado)
    assert r.duplicado and r.cdc == doc["cdc"]
