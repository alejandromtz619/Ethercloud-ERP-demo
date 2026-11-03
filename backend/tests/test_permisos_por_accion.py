"""
Permisos por acción: las rutas que cambian datos piden el permiso de la acción, no el de ver la pantalla;
algunas acciones se controlan según lo que cambia (precio en la venta, precio del producto, descuento del
cliente). La migración 0004 le da a cada rol las acciones que ya podía hacer.

    pytest backend/tests/test_permisos_por_accion.py
"""
import itertools
import sqlite3
from pathlib import Path

import pytest

from tests.test_configuracion import usuario_con

PREFIJO = "ZZACC"
_n = itertools.count(1)


def nuevo_usuario(client, admin, *permisos):
    return usuario_con(client, admin, f"accion{next(_n)}@test.com", list(permisos))


@pytest.fixture(scope="module")
def producto(client, admin):
    r = client.post("/api/productos", headers=admin, json={"empresa_id": 1, "nombre": f"{PREFIJO} Batería", "precio_venta": 500000,
                                                           "precio_costo": 300000})
    assert r.status_code == 200, r.text
    almacen = client.post("/api/almacenes", headers=admin, json={"empresa_id": 1, "nombre": f"{PREFIJO} Depósito"}).json()
    client.post("/api/stock/entrada", headers=admin, json={"producto_id": r.json()["id"], "almacen_id": almacen["id"],
                                                           "tipo": "ENTRADA", "cantidad": 50, "costo_unitario": 300000})
    return r.json()


def test_ver_la_pantalla_no_alcanza_para_cambiar(client, admin, producto):
    solo_ver = nuevo_usuario(client, admin, "productos.ver", "clientes.ver", "stock.ver")
    assert client.get("/api/productos", headers=solo_ver, params={"empresa_id": 1}).status_code == 200
    assert client.post("/api/productos", headers=solo_ver, json={"empresa_id": 1, "nombre": "x", "precio_venta": 1}).status_code == 403
    assert client.put(f"/api/productos/{producto['id']}", headers=solo_ver, json={"nombre": "x"}).status_code == 403
    assert client.delete(f"/api/productos/{producto['id']}", headers=solo_ver).status_code == 403
    assert client.post("/api/clientes", headers=solo_ver, json={"empresa_id": 1, "nombre": "x"}).status_code == 403
    assert client.post("/api/stock/entrada", headers=solo_ver, json={"producto_id": producto["id"], "almacen_id": 1, "tipo": "ENTRADA",
                                                                    "cantidad": 1, "costo_unitario": 1}).status_code == 403


def test_precio_del_producto_aparte_de_editarlo(client, admin, producto):
    editor = nuevo_usuario(client, admin, "productos.ver", "productos.editar")
    r = client.put(f"/api/productos/{producto['id']}", headers=editor, json={"descripcion": "Libre de mantenimiento"})
    assert r.status_code == 200, r.text
    # Mandar el mismo precio (como hace el formulario) no es cambiarlo
    assert client.put(f"/api/productos/{producto['id']}", headers=editor, json={"precio_venta": "500000.00"}).status_code == 200
    r = client.put(f"/api/productos/{producto['id']}", headers=editor, json={"precio_venta": 520000})
    assert r.status_code == 403 and "precio" in r.json()["detail"]
    con_precio = nuevo_usuario(client, admin, "productos.ver", "productos.editar", "productos.modificar_precio")
    assert client.put(f"/api/productos/{producto['id']}", headers=con_precio, json={"precio_venta": 500000, "precio_costo": 310000}).status_code == 200


def test_vender_a_otro_precio_pide_permiso(client, admin, producto):
    cajero = nuevo_usuario(client, admin, "ventas.crear")
    yo = client.get("/api/auth/me", headers=cajero).json()
    cliente = client.post("/api/clientes", headers=admin, json={"empresa_id": 1, "nombre": f"{PREFIJO} Cliente"}).json()

    def vender(headers, precio):
        return client.post("/api/ventas", headers=headers, json={
            "empresa_id": 1, "usuario_id": yo["id"], "cliente_id": cliente["id"], "tipo_pago": "EFECTIVO",
            "items": [{"producto_id": producto["id"], "cantidad": 1, "precio_unitario": precio}]})
    assert vender(cajero, 500000).status_code == 200
    r = vender(cajero, 450000)
    assert r.status_code == 403 and "precio" in r.json()["detail"]
    supervisor = nuevo_usuario(client, admin, "ventas.crear", "ventas.modificar_precio")
    assert vender(supervisor, 450000).status_code == 200


def test_descuento_del_cliente_pide_permiso(client, admin):
    vendedor = nuevo_usuario(client, admin, "clientes.ver", "clientes.crear", "clientes.editar")
    r = client.post("/api/clientes", headers=vendedor, json={"empresa_id": 1, "nombre": f"{PREFIJO} Con descuento", "descuento_porcentaje": 10})
    assert r.status_code == 403
    c = client.post("/api/clientes", headers=vendedor, json={"empresa_id": 1, "nombre": f"{PREFIJO} Sin descuento", "descuento_porcentaje": 0}).json()
    assert client.put(f"/api/clientes/{c['id']}", headers=vendedor, json={"telefono": "0981 111 222", "descuento_porcentaje": 0}).status_code == 200
    assert client.put(f"/api/clientes/{c['id']}", headers=vendedor, json={"descuento_porcentaje": 5}).status_code == 403
    jefe = nuevo_usuario(client, admin, "clientes.ver", "clientes.editar", "clientes.modificar_descuento")
    assert client.put(f"/api/clientes/{c['id']}", headers=jefe, json={"descuento_porcentaje": 5}).status_code == 200


def test_anular_una_venta_pide_ventas_anular(client, admin, producto):
    historial = nuevo_usuario(client, admin, "ventas.ver_historial")
    yo = client.get("/api/auth/me", headers=admin).json()
    cliente = client.post("/api/clientes", headers=admin, json={"empresa_id": 1, "nombre": f"{PREFIJO} Anular"}).json()
    venta = client.post("/api/ventas", headers=admin, json={
        "empresa_id": 1, "usuario_id": yo["id"], "cliente_id": cliente["id"], "tipo_pago": "EFECTIVO",
        "items": [{"producto_id": producto["id"], "cantidad": 1, "precio_unitario": 500000}]}).json()
    client.post(f"/api/ventas/{venta['id']}/confirmar", headers=admin)
    assert client.post(f"/api/ventas/{venta['id']}/anular", headers=historial).status_code == 403
    anulador = nuevo_usuario(client, admin, "ventas.ver_historial", "ventas.anular")
    assert client.post(f"/api/ventas/{venta['id']}/anular", headers=anulador).status_code == 200


def test_la_migracion_da_a_cada_rol_lo_que_ya_podia_hacer(tmp_path):
    """Sobre una base aparte. Cada rol recibe sólo lo que la pantalla le dejaba hacer sin pedir el permiso:
    no gana botones que no veía (un vendedor que sólo ve productos no pasa a poder crearlos ni a anular
    ventas). Correrla dos veces no duplica; crea los permisos que falten."""
    sql = (Path(__file__).resolve().parent.parent / "migraciones" / "0004_permisos_por_accion.sqlite.sql").read_text(encoding="utf-8")
    db = sqlite3.connect(tmp_path / "m.db")
    db.executescript("""
        CREATE TABLE permisos (id INTEGER PRIMARY KEY, clave TEXT UNIQUE NOT NULL, descripcion TEXT);
        CREATE TABLE rol_permisos (rol_id INTEGER, permiso_id INTEGER, PRIMARY KEY (rol_id, permiso_id));
        INSERT INTO permisos (clave) VALUES ('clientes.ver'), ('clientes.editar'), ('productos.ver'), ('ventas.ver_historial'),
                                           ('stock.ver'), ('ventas.crear');
        INSERT INTO rol_permisos VALUES (1, 1), (1, 2), (2, 3), (2, 6), (3, 4), (4, 5);
    """)
    db.executescript(sql)
    db.executescript(sql)
    de = lambda rol: sorted(r[0] for r in db.execute(
        "SELECT p.clave FROM rol_permisos rp JOIN permisos p ON p.id = rp.permiso_id WHERE rp.rol_id = ?", (rol,)))
    assert de(1) == ["clientes.editar", "clientes.modificar_descuento", "clientes.ver"]
    assert de(2) == ["productos.ver", "ventas.crear"]  # ni productos.crear, ni precios, ni descuentos
    assert de(3) == ["reportes.exportar", "ventas.ver_historial"]  # Excel sí; anular no (la pantalla ya lo pedía)
    assert de(4) == ["stock.ajustar", "stock.configurar_alertas", "stock.ver"]
    assert db.execute("SELECT COUNT(*) FROM rol_permisos").fetchone()[0] == sum(len(de(r)) for r in (1, 2, 3, 4))
    assert db.execute("SELECT descripcion FROM permisos WHERE clave = 'delivery.eliminar'").fetchone()[0] == "Eliminar entregas"


def test_descuento_del_cliente_solo_con_permiso_de_aplicarlo(client, admin, producto):
    """La pantalla de Ventas no muestra el descuento a quien no puede aplicarlo: el total guardado coincide."""
    cliente = client.post("/api/clientes", headers=admin, json={"empresa_id": 1, "nombre": f"{PREFIJO} 10 %", "descuento_porcentaje": 10}).json()

    def vender(headers):
        yo = client.get("/api/auth/me", headers=headers).json()
        r = client.post("/api/ventas", headers=headers, json={
            "empresa_id": 1, "usuario_id": yo["id"], "cliente_id": cliente["id"], "tipo_pago": "EFECTIVO",
            "items": [{"producto_id": producto["id"], "cantidad": 2, "precio_unitario": 500000}]})
        assert r.status_code == 200, r.text
        return float(r.json()["total"])
    assert vender(nuevo_usuario(client, admin, "ventas.crear")) == 1000000
    assert vender(nuevo_usuario(client, admin, "ventas.crear", "ventas.aplicar_descuento")) == 900000
