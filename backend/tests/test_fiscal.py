"""
Facturación electrónica (fiscal/) con el emisor falso: armado del documento, numeración, reintentos,
rechazos y permisos. La prueba contra el SANDBOX real de SIFEN SIS está en test_fiscal_sandbox.py.

    pytest backend/tests/test_fiscal.py
"""
import asyncio
from types import SimpleNamespace

import pytest

import server
from fiscal import constructor
from fiscal.falso import SifenFalso
from fiscal.puerto import DocumentoInvalido
from fiscal.servicio import FacturacionElectronica, ServicioFiscal

PREFIJO = "FISCAL"


def ruc(base: str) -> str:
    return f"{base}-{constructor.dv_ruc(base)}"


@pytest.fixture
def falso(client):
    emisor = SifenFalso()
    server.app.state.facturacion = FacturacionElectronica(fijo=ServicioFiscal(emisor))
    yield emisor
    server.app.state.facturacion = None


def servicio_de_prueba() -> ServicioFiscal:
    return server.app.state.facturacion._fijo


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
                                    "tipo": "ENTRADA", "cantidad": 500, "costo_unitario": 1000})
    clientes = {
        "empresa": post("/api/clientes", {"empresa_id": 1, "nombre": f"{PREFIJO} Ferretería S.A.", "ruc": ruc("80069563"),
                                          "descuento_porcentaje": 10, "limite_credito": 10_000_000,
                                          "acepta_cheque": True}),
        "cedula": post("/api/clientes", {"empresa_id": 1, "nombre": "Juana", "apellido": "Pérez", "cedula": "1.234.567"}),
        "anonimo": post("/api/clientes", {"empresa_id": 1, "nombre": f"{PREFIJO} Mostrador"}),
        "dv_malo": post("/api/clientes", {"empresa_id": 1, "nombre": f"{PREFIJO} DV Malo", "ruc": "80012345-5"}),
        "corto": post("/api/clientes", {"empresa_id": 1, "nombre": "Al", "ruc": ruc("2005001")}),
    }
    yo = client.get("/api/auth/me", headers=admin).json()

    def vender(cliente="empresa", claves=("diez", "cinco", "exento"), tipo_pago="EFECTIVO", confirmar=True):
        venta = post("/api/ventas", {"empresa_id": 1, "usuario_id": yo["id"], "cliente_id": clientes[cliente]["id"],
                                     "tipo_pago": tipo_pago, "items": [
                                         {"producto_id": productos[c]["id"], "cantidad": 2,
                                          "precio_unitario": productos[c]["precio_venta"]} for c in claves]})
        return post(f"/api/ventas/{venta['id']}/confirmar", {}) if confirmar else venta
    return {"clientes": clientes, "vender": vender, "yo": yo}


def facturar(client, admin, venta_id):
    return client.post(f"/api/fiscal/ventas/{venta_id}/factura", headers=admin)


async def venta_facturada(venta_id: int) -> bool:
    from database import async_session_maker
    from models import Venta
    async with async_session_maker() as db:
        return (await db.get(Venta, venta_id)).facturada


def secuencia(client, admin) -> int:
    r = client.get("/api/fiscal/estado", headers=admin).json()
    return next((s["ultimo_numero"] for s in r["secuencias"] if s["tipo_documento"] == 1), 0)


# ---------------------------------------------------------------- armado del documento

def test_digito_verificador_del_ruc():
    assert constructor.dv_ruc("80069563") == 1  # ejemplos de la documentación de SIFEN SIS
    assert constructor.dv_ruc("2005001") == 1
    assert constructor.ruc_con_dv("80.069.563-1") == "80069563-1"
    assert constructor.ruc_con_dv("80069563") == "80069563-1"  # sin DV: se calcula
    assert constructor.ruc_con_dv("abc") is None and constructor.ruc_con_dv(None) is None
    with pytest.raises(DocumentoInvalido, match="debería ser 8"):
        constructor.ruc_con_dv("80077777-7")


def test_receptor_segun_los_datos_del_cliente():
    def cli(**k):
        return SimpleNamespace(**{"id": 7, "nombre": "Cliente", "apellido": None, "ruc": None, "cedula": None,
                                  "direccion": None, "telefono": None, "email": None, **k})
    r = constructor.receptor(cli(nombre="Ferretería", apellido="S.A.", ruc="80069563-1", telefono="0981 123 456"))
    assert r["contribuyente"] and r["ruc"] == "80069563-1" and r["tipoContribuyente"] == 2 and r["tipoOperacion"] == 1
    assert r["razonSocial"] == "Ferretería S.A." and r["telefono"] == "0981123456"
    assert constructor.receptor(cli(ruc="2005001-1"))["tipoContribuyente"] == 1  # persona física
    r = constructor.receptor(cli(cedula="1.234.567"))
    assert r["documentoTipo"] == 1 and r["documentoNumero"] == "1234567" and r["tipoOperacion"] == 2
    for anonimo in (cli(), cli(ruc="44444401-7")):
        assert constructor.receptor(anonimo)["razonSocial"] == "Sin Nombre"


# ---------------------------------------------------------------- emisión

def test_factura_de_venta_contado_con_iva_mixto_y_descuento(client, admin, falso, escenario):
    venta = escenario["vender"]()
    antes = secuencia(client, admin)
    r = facturar(client, admin, venta["id"])
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["estado"] == "GENERADO" and len(doc["cdc"]) == 44 and doc["numero"] == f"001-001-{antes + 1:07d}"
    data = falso.documentos[(1, "001", "001", antes + 1)]["data"]
    assert [(i["iva"], i["ivaTipo"], i["ivaBase"]) for i in data["items"]] == [(10, 1, 100), (5, 1, 100), (0, 3, 0)]
    # 2 x (11.000 + 10.500 + 5.000) = 53.000, menos 10 % del cliente = 47.700
    assert data["descuentoGlobal"] == 5300 and data["condicion"]["entregas"][0]["monto"] == "47700"
    assert doc["total"] == 47700 == float(venta["total"])
    assert data["cliente"]["ruc"] == "80069563-1" and data["fecha"].startswith("20")
    # La venta queda facturada (no aparece para la factura agrupada) y no se factura dos veces
    assert client.portal.call(venta_facturada, venta["id"]) is True
    r = facturar(client, admin, venta["id"])
    assert r.status_code == 409 and r.json()["detail"]["documento"]["id"] == doc["id"]


def test_credito_cedula_y_tarjeta(client, admin, falso, escenario):
    credito = facturar(client, admin, escenario["vender"](tipo_pago="CREDITO")["id"]).json()
    data = falso.documentos[(1, "001", "001", int(credito["numero"][-7:]))]["data"]
    assert data["condicion"] == {"tipo": 2, "credito": {"tipo": 1, "plazo": "30 días"}}
    cedula = facturar(client, admin, escenario["vender"]("cedula", tipo_pago="TARJETA")["id"]).json()
    data = falso.documentos[(1, "001", "001", int(cedula["numero"][-7:]))]["data"]
    assert data["cliente"]["documentoNumero"] == "1234567" and data["cliente"]["razonSocial"] == "Juana Pérez"
    assert data["condicion"]["entregas"][0]["tipo"] == 3 and data["condicion"]["entregas"][0]["infoTarjeta"]["tipo"] == 99


def test_cheque_pide_numero_y_banco(client, admin, falso, escenario):
    venta = escenario["vender"](tipo_pago="CHEQUE")
    r = facturar(client, admin, venta["id"])
    assert r.status_code == 422 and "cheque" in r.json()["detail"]["errores"][0]
    r = client.post(f"/api/fiscal/ventas/{venta['id']}/factura", headers=admin, json={"cheque": {"numero": "4521", "banco": "Banco Basa"}})
    assert r.status_code == 200, r.text
    data = falso.documentos[(1, "001", "001", int(r.json()["numero"][-7:]))]["data"]
    assert data["condicion"]["entregas"][0]["infoCheque"] == {"numeroCheque": "00004521", "banco": "Banco Basa"}


def test_datos_invalidos_no_consumen_numero(client, admin, falso, escenario):
    antes = secuencia(client, admin)
    r = facturar(client, admin, escenario["vender"]("dv_malo")["id"])  # lo detecta el ERP
    assert r.status_code == 422 and "dígito verificador" in r.json()["detail"]["errores"][0]
    r = facturar(client, admin, escenario["vender"]("corto")["id"])    # lo detecta el proveedor al validar
    assert r.status_code == 422 and "razonSocial" in r.json()["detail"]["errores"][0]
    assert secuencia(client, admin) == antes and not falso.documentos


def test_venta_no_confirmada(client, admin, falso, escenario):
    venta = escenario["vender"](confirmar=False)
    assert facturar(client, admin, venta["id"]).status_code == 409
    assert facturar(client, admin, 999999).status_code == 404


def test_proveedor_caido_queda_por_enviar_y_el_seguimiento_lo_completa(client, admin, falso, escenario):
    falso.caido = True
    doc = facturar(client, admin, escenario["vender"]()["id"]).json()
    assert doc["estado"] == "POR_ENVIAR" and doc["cdc"] is None and "no respondió" in doc["mensaje"]
    falso.caido = False
    servicio = servicio_de_prueba()

    async def vuelta():
        from database import async_session_maker
        async with async_session_maker() as db:
            return await servicio.una_vuelta(db)

    estados = []
    for _ in range(3):  # reenvía; luego GENERADO -> ENVIADO -> APROBADO
        client.portal.call(vuelta)
        estados.append(client.get(f"/api/fiscal/documentos/{doc['id']}", headers=admin).json()["estado"])
    assert estados == ["ENVIADO", "APROBADO", "APROBADO"] or estados[-1] == "APROBADO", estados
    final = client.get(f"/api/fiscal/documentos/{doc['id']}", headers=admin).json()
    assert final["aprobado_en"] and final["mensaje"] is None


def test_respuesta_perdida_se_reintenta_sin_duplicar(client, admin, falso, escenario):
    falso.perder_respuestas = 1
    doc = facturar(client, admin, escenario["vender"]()["id"]).json()
    assert doc["estado"] == "POR_ENVIAR" and len(falso.documentos) == 1  # el proveedor sí lo recibió
    r = client.post(f"/api/fiscal/documentos/{doc['id']}/reintentar", headers=admin).json()
    assert r["estado"] == "GENERADO" and r["cdc"] == next(iter(falso.documentos.values()))["cdc"]
    assert len(falso.documentos) == 1 and r["numero"] == doc["numero"]


def test_numero_ocupado_en_el_proveedor_se_renumera(client, admin, falso, escenario):
    """Si se restauró un respaldo viejo del ERP, el próximo número local ya existe en el proveedor."""
    siguiente = secuencia(client, admin) + 1
    falso.documentos[(1, "001", "001", siguiente)] = {"cdc": "9" * 44, "estado": "APROBADO", "huella": "otro", "data": {}}
    falso.documentos[(1, "001", "001", siguiente + 1)] = {"cdc": "8" * 44, "estado": "APROBADO", "huella": "otro", "data": {}}
    doc = facturar(client, admin, escenario["vender"]()["id"]).json()
    assert doc["estado"] == "GENERADO" and doc["numero"] == f"001-001-{siguiente + 2:07d}"
    assert secuencia(client, admin) == siguiente + 2


def test_rechazado_se_corrige_y_se_reemite_con_el_mismo_numero(client, admin, falso, escenario):
    siguiente = secuencia(client, admin) + 1
    falso.rechazar.add(siguiente)
    doc = facturar(client, admin, escenario["vender"]()["id"]).json()
    for _ in range(2):
        r = client.post(f"/api/fiscal/documentos/{doc['id']}/reintentar", headers=admin).json()
    assert r["estado"] == "RECHAZADO" and "RUC" in r["mensaje"]
    falso.rechazar.clear()
    r = client.post(f"/api/fiscal/documentos/{doc['id']}/reintentar", headers=admin).json()
    assert r["estado"] == "GENERADO" and r["numero"] == doc["numero"] and r["mensaje"] is None
    assert falso.documentos[(1, "001", "001", siguiente)]["estado"] == "GENERADO"  # se volvió a emitir
    assert secuencia(client, admin) == siguiente  # no se usó otro número


def test_kude_y_xml(client, admin, falso, escenario):
    doc = facturar(client, admin, escenario["vender"]()["id"]).json()
    for formato in ("a4", "ticket", "ticket58"):
        r = client.get(f"/api/fiscal/documentos/{doc['id']}/kude", headers=admin, params={"formato": formato})
        assert r.status_code == 200 and r.headers["content-type"] == "application/pdf" and r.content.startswith(b"%PDF")
    assert client.get(f"/api/fiscal/documentos/{doc['id']}/xml", headers=admin).content.startswith(b"<xml")
    documentos = client.get(f"/api/fiscal/ventas/{doc['venta_id']}/documentos", headers=admin).json()
    assert [d["id"] for d in documentos] == [doc["id"]]


def test_cincuenta_facturas_simultaneas_numeros_correlativos(client, admin, falso, escenario):
    """50 emisiones a la vez (servicio directo, una sesión cada una): 50 números distintos y seguidos."""
    from database import async_session_maker
    servicio = servicio_de_prueba()
    contenido = {"tipoEmision": 1, "tipoTransaccion": 1, "tipoImpuesto": 1, "moneda": "PYG", "factura": {"presencia": 1},
                 "cliente": {"contribuyente": False, "documentoTipo": 5, "documentoNumero": "0", "razonSocial": "Sin Nombre",
                             "tipoOperacion": 2, "pais": "PRY"},
                 "items": [{"codigo": "1", "descripcion": "x", "unidadMedida": 77, "cantidad": 1, "precioUnitario": 1000,
                            "ivaTipo": 1, "ivaBase": 100, "iva": 10}],
                 "condicion": {"tipo": 1, "entregas": [{"tipo": 1, "monto": "1000", "moneda": "PYG"}]}}
    antes = secuencia(client, admin)

    async def una():
        async with async_session_maker() as db:
            return (await servicio.emitir(db, empresa_id=1, tipo=1, contenido=contenido, origen="venta", total=1000)).numero

    async def todas():
        return await asyncio.gather(*(una() for _ in range(50)))

    numeros = client.portal.call(todas)
    assert sorted(numeros) == list(range(antes + 1, antes + 51))


# ---------------------------------------------------------------- estado y permisos

def test_estado_de_la_conexion(client, admin, falso):
    r = client.get("/api/fiscal/estado", headers=admin).json()
    assert r["conectado"] and r["ambiente"] == "SANDBOX" and r["establecimiento"] == "001" and r["punto"] == "001"
    falso.caido = True
    r = client.get("/api/fiscal/estado", headers=admin).json()
    assert r["conectado"] is False and "no respondió" in r["error"]


def test_permisos_y_modulo(client, admin, falso, escenario):
    assert client.post("/api/fiscal/ventas/1/factura").status_code == 401
    r = client.post("/api/auth/register", headers=admin, json={
        "email": "sinfactura@test.com", "password": "clave-segura-123", "nombre": "Sin", "empresa_id": 1})
    token = client.post("/api/auth/login", json={"email": "sinfactura@test.com", "password": "clave-segura-123"}).json()["access_token"]
    sin_permiso = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/fiscal/ventas/1/factura", headers=sin_permiso).status_code == 403
    assert client.post("/api/fiscal/numeracion/sincronizar", headers=sin_permiso).status_code == 403
    server.app.state.facturacion = None  # módulo fe no contratado
    assert client.get("/api/fiscal/estado", headers=admin).status_code == 404


def test_la_api_key_se_carga_desde_la_pantalla_sin_reiniciar(client, admin, escenario, monkeypatch):
    """Sin key: 503 con el aviso. Al cargarla en Configuración se emite; al cambiarla se usa la nueva."""
    import configuracion
    monkeypatch.setenv("CLAVE_CIFRADO", "clave-de-cifrado-de-prueba-0123456789abcdef")
    monkeypatch.delenv("SIFENSIS_API_KEY", raising=False)
    monkeypatch.setattr(server, "MODULOS_ACTIVOS", server.MODULOS_ACTIVOS)
    server.MODULOS_ACTIVOS.add("fe")
    creados = {}

    def fabrica(api_key):
        creados[api_key] = SifenFalso()
        return creados[api_key]

    server.app.state.facturacion = FacturacionElectronica(fabrica=fabrica)
    try:
        client.put("/api/configuracion/facturacion_electronica", headers=admin, json={"valores": {"fe.api_key": None}})
        r = client.get("/api/fiscal/estado", headers=admin)
        assert r.status_code == 503 and "Configuración" in r.json()["detail"]
        assert client.post("/api/configuracion/facturacion_electronica/probar", headers=admin).json()["ok"] is False

        r = client.put("/api/configuracion/facturacion_electronica", headers=admin,
                       json={"valores": {"fe.api_key": "gk_primera_key_0001", "fe.punto": "33"}})
        assert r.status_code == 200, r.text
        probar = client.post("/api/configuracion/facturacion_electronica/probar", headers=admin).json()
        assert probar["ok"] and probar["ambiente"] == "SANDBOX" and probar["punto"] == "033"
        doc = facturar(client, admin, escenario["vender"]()["id"]).json()
        assert doc["estado"] == "GENERADO" and doc["numero"].startswith("001-033-")
        assert len(creados["gk_primera_key_0001"].documentos) == 1

        client.put("/api/configuracion/facturacion_electronica", headers=admin,
                   json={"valores": {"fe.api_key": "gk_segunda_key_0002"}})
        doc = facturar(client, admin, escenario["vender"]()["id"]).json()
        assert doc["estado"] == "GENERADO" and len(creados["gk_segunda_key_0002"].documentos) == 1
        assert len(creados["gk_primera_key_0001"].documentos) == 1  # la key vieja ya no se usa
    finally:
        client.put("/api/configuracion/facturacion_electronica", headers=admin,
                   json={"valores": {"fe.api_key": None, "fe.punto": None}})
        server.MODULOS_ACTIVOS.discard("fe")
        server.app.state.facturacion = None
        configuracion.invalidar_cache()


# ---------------------------------------------------------------- datos fiscales (etapa 2.1)

def test_catalogos_de_ubicacion_y_unidades(client, admin, falso):
    r = client.get("/api/fiscal/catalogos", headers=admin).json()
    assert len(r["departamentos"]) == 18 and {"codigo": 77, "sigla": "UNI", "nombre": "Unidad"} in r["unidades_medida"]
    alto_parana = next(d["codigo"] for d in r["departamentos"] if d["nombre"] == "ALTO PARANA")
    distritos = client.get("/api/fiscal/catalogos/distritos", headers=admin, params={"departamento": alto_parana}).json()
    cde = next(d for d in distritos if d["nombre"].startswith("CIUDAD DEL ESTE"))
    ciudades = client.get("/api/fiscal/catalogos/ciudades", headers=admin, params={"distrito": cde["codigo"]}).json()
    assert ciudades and all(c["distrito"] == cde["codigo"] for c in ciudades)
    server.app.state.facturacion = None  # sin el módulo fe, no
    assert client.get("/api/fiscal/catalogos", headers=admin).status_code == 404


def test_domicilio_fiscal_del_cliente_se_valida(client, admin, falso):
    base = {"empresa_id": 1, "nombre": f"{PREFIJO} Domicilio", "direccion": "Avda. España"}
    for malo, texto in (({"departamento": 1}, "los tres"), ({"departamento": 1, "distrito": 2, "ciudad": 3}, "no pertenece"),
                        ({"tipo_contribuyente": 3}, "Input should be")):
        r = client.post("/api/clientes", headers=admin, json={**base, **malo})
        assert r.status_code == 422 and texto in r.text, (malo, r.text)
    cliente = client.post("/api/clientes", headers=admin, json={**base, "departamento": 1, "distrito": 1, "ciudad": 1,
                                                                "numero_casa": 1234}).json()
    assert (cliente["departamento"], cliente["distrito"], cliente["ciudad"], cliente["numero_casa"]) == (1, 1, 1, 1234)
    # Al editar se valida con lo que ya tenía: cambiar sólo el distrito deja el domicilio incoherente
    r = client.put(f"/api/clientes/{cliente['id']}", headers=admin, json={"distrito": 2})
    assert r.status_code == 422
    r = client.put(f"/api/clientes/{cliente['id']}", headers=admin, json={"departamento": "", "distrito": "", "ciudad": ""})
    assert r.status_code == 200 and r.json()["departamento"] is None


def test_factura_con_domicilio_tipo_y_unidad(client, admin, falso, escenario):
    def post(ruta, cuerpo):
        r = client.post(ruta, headers=admin, json=cuerpo)
        assert r.status_code == 200, r.text
        return r.json()
    cliente = post("/api/clientes", {"empresa_id": 1, "nombre": f"{PREFIJO} Estado S.A.", "ruc": ruc("3009001"),
                                     "direccion": "Mcal. López 456", "numero_casa": 456, "departamento": 1, "distrito": 1,
                                     "ciudad": 1, "tipo_contribuyente": 2, "tipo_operacion": 3, "limite_credito": 0})
    assert client.post("/api/productos", headers=admin, json={"empresa_id": 1, "nombre": "x", "precio_venta": 1,
                                                              "unidad_medida": 9999}).status_code == 422
    prod = post("/api/productos", {"empresa_id": 1, "nombre": f"{PREFIJO} Cemento kg", "precio_venta": 2200, "unidad_medida": 83})
    alm = post("/api/almacenes", {"empresa_id": 1, "nombre": f"{PREFIJO} Depósito kg"})
    post("/api/stock/entrada", {"producto_id": prod["id"], "almacen_id": alm["id"], "tipo": "ENTRADA", "cantidad": 100, "costo_unitario": 1})
    venta = post("/api/ventas", {"empresa_id": 1, "usuario_id": escenario["yo"]["id"], "cliente_id": cliente["id"], "tipo_pago": "EFECTIVO",
                                 "items": [{"producto_id": prod["id"], "cantidad": 10, "precio_unitario": 2200}]})
    post(f"/api/ventas/{venta['id']}/confirmar", {})
    doc = facturar(client, admin, venta["id"]).json()
    data = falso.documentos[(1, "001", "001", int(doc["numero"][-7:]))]["data"]
    receptor = data["cliente"]
    assert (receptor["direccion"], receptor["numeroCasa"], receptor["departamento"], receptor["distrito"], receptor["ciudad"]) == \
        ("Mcal. López 456", 456, 1, 1, 1)
    assert receptor["tipoContribuyente"] == 2 and receptor["tipoOperacion"] == 3  # lo cargado gana sobre lo deducido
    assert data["items"][0]["unidadMedida"] == 83
    # Con dirección pero sin domicilio completo, no se informa (SIFEN la rechazaría)
    sin_ubicacion = constructor.receptor(SimpleNamespace(id=1, nombre="Cliente", apellido=None, ruc="80069563-1", cedula=None,
                                                         direccion="Calle 1", telefono=None, email=None))
    assert "direccion" not in sin_ubicacion


# ---------------------------------------------------------------- emisión desde ventas (etapa 2.2)

def test_estados_de_varias_ventas(client, admin, falso, escenario):
    con = escenario["vender"]()
    sin = escenario["vender"]()
    doc = facturar(client, admin, con["id"]).json()
    r = client.get("/api/fiscal/ventas/estados", headers=admin, params={"ids": f"{con['id']},{sin['id']}"}).json()
    assert list(r) == [str(con["id"])] and r[str(con["id"])]["numero"] == doc["numero"]
    assert client.get("/api/fiscal/ventas/estados", headers=admin, params={"ids": "a,b"}).status_code == 422


def test_factura_agrupada_electronica(client, admin, falso, escenario):
    efectivo = escenario["vender"](claves=("diez",))
    tarjeta = escenario["vender"](claves=("cinco",), tipo_pago="TARJETA")
    grupal = client.post("/api/facturas/grupal", headers=admin, json={
        "empresa_id": 1, "cliente_id": escenario["clientes"]["empresa"]["id"], "venta_ids": [efectivo["id"], tarjeta["id"]],
        "cobrar_credito": True})
    assert grupal.status_code == 200, grupal.text
    grupal = grupal.json()
    # Las ventas de la agrupada ya no se facturan solas
    r = facturar(client, admin, efectivo["id"])
    assert r.status_code == 409 and "agrupada" in r.json()["detail"]

    r = client.post(f"/api/fiscal/facturas-grupales/{grupal['id']}/factura", headers=admin)
    assert r.status_code == 200, r.text
    doc = r.json()
    data = falso.documentos[(1, "001", "001", int(doc["numero"][-7:]))]["data"]
    assert [i["iva"] for i in data["items"]] == [10, 5]
    assert data["condicion"]["entregas"][0] == {"tipo": 99, "tipoDescripcion": "Pagos varios",
                                               "monto": str(int(doc["total"])), "moneda": "PYG"}
    assert doc["total"] == float(efectivo["total"]) + float(tarjeta["total"]) and doc["origen"] == "factura_grupal"
    assert grupal["numero"] in data["observacion"]
    assert client.post(f"/api/fiscal/facturas-grupales/{grupal['id']}/factura", headers=admin).status_code == 409
    estados = client.get("/api/fiscal/facturas-grupales/estados", headers=admin, params={"ids": grupal["id"]}).json()
    assert estados[str(grupal["id"])]["id"] == doc["id"]
