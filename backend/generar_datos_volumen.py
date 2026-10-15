"""
Llena una base PostgreSQL VACÍA con datos sintéticos de volumen para medir rendimiento.

    DATABASE_URL=postgresql://... python generar_datos_volumen.py --confirmar-base-de-prueba
    (opcionales: --productos 50000 --clientes 5000 --ventas 100000 --items-por-venta 5)

Crea primero las tablas y el admin (seed_data.py). Se niega a correr si la base ya tiene
productos o ventas: nunca apuntarlo a la base de un cliente.
"""
import argparse
import asyncio
import io
import os
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import psycopg2

PY = ZoneInfo("America/Asuncion")
PALABRAS = ("Pintura Latex Esmalte Sintetico Barniz Sellador Enduido Rodillo Pincel Lija Thinner "
            "Masilla Impermeabilizante Fondo Antioxido Aerosol Silicona Cinta Espatula Balde").split()
COLORES = "Blanco Negro Gris Rojo Azul Verde Amarillo Marfil Cemento Natural Cedro Caoba".split()
MEDIDAS = ["1 L", "4 L", "18 L", "250 ml", "500 ml", "1 kg", "4 kg", "N° 10", "N° 20", "23 cm"]
NOMBRES = "Juan Maria Carlos Ana Luis Rosa Pedro Lucia Jorge Elena Diego Sofia Miguel Laura".split()
APELLIDOS = "Gonzalez Benitez Martinez Lopez Gimenez Vera Ortiz Duarte Rojas Caceres Acosta Romero".split()


def _copy(cur, tabla, columnas, filas):
    buf = io.StringIO()
    for fila in filas:
        buf.write("\t".join("\\N" if v is None else str(v) for v in fila) + "\n")
    buf.seek(0)
    cur.copy_from(buf, tabla, columns=columnas)


def _max_id(cur, tabla):
    cur.execute(f"SELECT COALESCE(MAX(id), 0) FROM {tabla}")
    return cur.fetchone()[0]


def _ajustar_secuencias(cur, tablas):
    for t in tablas:
        cur.execute(f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), (SELECT COALESCE(MAX(id), 1) FROM {t}))")


def generar(dsn, n_productos, n_clientes, n_ventas, items_por_venta):
    rnd = random.Random(42)
    ahora = datetime.now(PY)
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()

    cur.execute("SELECT (SELECT COUNT(*) FROM productos), (SELECT COUNT(*) FROM ventas)")
    productos_existentes, ventas_existentes = cur.fetchone()
    if productos_existentes or ventas_existentes:
        raise SystemExit("La base ya tiene productos o ventas: este script sólo corre sobre una base vacía.")
    cur.execute("SELECT id FROM empresas ORDER BY id LIMIT 1")
    empresa_id = cur.fetchone()[0]
    cur.execute("SELECT password_hash FROM usuarios ORDER BY id LIMIT 1")
    hash_admin = cur.fetchone()[0]

    def fecha_al_azar(dias=730):
        return (ahora - timedelta(days=rnd.random() * dias)).isoformat()

    # Catálogos chicos
    base = _max_id(cur, "categorias")
    categorias = list(range(base + 1, base + 41))
    _copy(cur, "categorias", ("id", "empresa_id", "nombre"),
          [(i, empresa_id, f"Categoria {i}") for i in categorias])
    base = _max_id(cur, "marcas")
    marcas = list(range(base + 1, base + 81))
    _copy(cur, "marcas", ("id", "empresa_id", "nombre"), [(i, empresa_id, f"Marca {i}") for i in marcas])
    base = _max_id(cur, "proveedores")
    proveedores = list(range(base + 1, base + 151))
    _copy(cur, "proveedores", ("id", "empresa_id", "nombre", "ruc", "telefono", "estado", "creado_en"),
          [(i, empresa_id, f"Proveedor {i} S.A.", f"80{i:06d}-1", "0981000000", "t", fecha_al_azar()) for i in proveedores])
    base = _max_id(cur, "almacenes")
    almacenes = [base + 1, base + 2]
    _copy(cur, "almacenes", ("id", "empresa_id", "nombre", "ubicacion"),
          [(almacenes[0], empresa_id, "Deposito central", "Central"), (almacenes[1], empresa_id, "Salon", "Local")])

    # Vendedores (misma contraseña que el admin)
    base = _max_id(cur, "usuarios")
    vendedores = list(range(base + 1, base + 11))
    _copy(cur, "usuarios", ("id", "empresa_id", "email", "password_hash", "nombre", "apellido", "activo"),
          [(i, empresa_id, f"vendedor{i}@volumen.test", hash_admin, rnd.choice(NOMBRES), rnd.choice(APELLIDOS), "t")
           for i in vendedores])

    # Productos + stock + lotes de entrada
    base = _max_id(cur, "productos")
    productos = []
    filas_prod, filas_stock, filas_mov = [], [], []
    for k in range(n_productos):
        pid = base + 1 + k
        costo = rnd.randrange(5_000, 600_000, 500)
        precio = int(costo * rnd.uniform(1.2, 1.8)) // 500 * 500
        productos.append((pid, precio, costo))
        nombre = f"{rnd.choice(PALABRAS)} {rnd.choice(COLORES)} {rnd.choice(MEDIDAS)} #{pid}"
        filas_prod.append((pid, empresa_id, rnd.choice(categorias), rnd.choice(marcas), nombre,
                           f"Descripcion de {nombre}", f"77{pid:011d}", precio, costo,
                           rnd.choice(proveedores), rnd.choice((5, 10, 20)), "t", fecha_al_azar()))
        for alm in almacenes:
            cantidad = rnd.randint(0, 120)
            filas_stock.append((pid, alm, cantidad, rnd.choice((None, 5, 10))))
            filas_mov.append((pid, alm, "ENTRADA", cantidad + 40, "compra", rnd.choice(proveedores),
                              costo, costo, "contado", cantidad, fecha_al_azar()))
    _copy(cur, "productos", ("id", "empresa_id", "categoria_id", "marca_id", "nombre", "descripcion", "codigo_barra",
                             "precio_venta", "precio_costo", "proveedor_id", "stock_minimo", "activo", "creado_en"),
          filas_prod)
    _copy(cur, "stock_actual", ("producto_id", "almacen_id", "cantidad", "alerta_minima"), filas_stock)
    mov_cols = ("producto_id", "almacen_id", "tipo", "cantidad", "referencia_tipo", "proveedor_id",
                "costo_unitario", "costo_ponderado", "condicion_pago", "cantidad_restante", "creado_en")
    _copy(cur, "movimientos_stock", mov_cols, filas_mov)

    # Clientes
    base = _max_id(cur, "clientes")
    clientes = list(range(base + 1, base + 1 + n_clientes))
    _copy(cur, "clientes", ("id", "empresa_id", "nombre", "apellido", "ruc", "cedula", "telefono", "email",
                            "acepta_cheque", "descuento_porcentaje", "limite_credito", "estado", "creado_en"),
          [(i, empresa_id, rnd.choice(NOMBRES), rnd.choice(APELLIDOS), f"{1_000_000 + i}-{i % 10}", str(1_000_000 + i),
            f"09{rnd.randint(71, 99)}{rnd.randint(100000, 999999)}", f"cliente{i}@volumen.test",
            "f", 0, 5_000_000, "t", fecha_al_azar()) for i in clientes])

    # Ventas + ítems + salidas de stock + créditos + entregas
    base_v = _max_id(cur, "ventas")
    filas_v, filas_items, filas_salidas, filas_cred, filas_ent = [], [], [], [], []
    tipos_pago = ["EFECTIVO"] * 6 + ["TARJETA", "TRANSFERENCIA", "CREDITO"]
    for k in range(n_ventas):
        vid = base_v + 1 + k
        fecha = fecha_al_azar()
        total = costo_total = 0
        for _ in range(rnd.randint(1, items_por_venta * 2 - 1)):
            pid, precio, costo = rnd.choice(productos)
            cant = rnd.randint(1, 6)
            total += precio * cant
            costo_total += costo * cant
            filas_items.append((vid, pid, cant, precio, costo, precio * cant))
            filas_salidas.append((pid, rnd.choice(almacenes), "SALIDA", -cant, "venta", vid, fecha))
        tipo_pago = rnd.choice(tipos_pago)
        delivery = rnd.random() < 0.1
        cliente = rnd.choice(clientes)
        filas_v.append((vid, empresa_id, cliente, rnd.choice(vendedores), total, round(total / 11), 0,
                        costo_total, total - costo_total, tipo_pago, "t" if delivery else "f", "CONFIRMADA", fecha,
                        "t" if rnd.random() < 0.3 else "f"))
        if tipo_pago == "CREDITO":
            pagado = rnd.random() < 0.7
            filas_cred.append((cliente, vid, total, 0 if pagado else total, fecha[:10], "t" if pagado else "f", fecha))
        if delivery:
            filas_ent.append((vid, "ENTREGADO" if rnd.random() < 0.9 else "PENDIENTE", fecha))
    _copy(cur, "ventas", ("id", "empresa_id", "cliente_id", "usuario_id", "total", "iva", "descuento", "costo_total",
                          "ganancia", "tipo_pago", "es_delivery", "estado", "creado_en", "facturada"), filas_v)
    _copy(cur, "venta_items", ("venta_id", "producto_id", "cantidad", "precio_unitario", "precio_costo", "total"),
          filas_items)
    _copy(cur, "movimientos_stock", ("producto_id", "almacen_id", "tipo", "cantidad", "referencia_tipo",
                                     "referencia_id", "creado_en"), filas_salidas)
    _copy(cur, "creditos_clientes", ("cliente_id", "venta_id", "monto_original", "monto_pendiente", "fecha_venta",
                                     "pagado", "creado_en"), filas_cred)
    _copy(cur, "entregas", ("venta_id", "estado", "fecha_entrega"), filas_ent)

    # Presupuestos y gastos
    base_p = _max_id(cur, "presupuestos")
    filas_p, filas_pi = [], []
    for k in range(max(1, n_ventas // 20)):
        prid = base_p + 1 + k
        total = 0
        for _ in range(rnd.randint(1, 6)):
            pid, precio, _costo = rnd.choice(productos)
            cant = rnd.randint(1, 10)
            total += precio * cant
            filas_pi.append((prid, pid, f"Producto #{pid}", cant, precio, precio * cant))
        filas_p.append((prid, empresa_id, rnd.choice(clientes), rnd.choice(vendedores), total, total, fecha_al_azar()))
    _copy(cur, "presupuestos", ("id", "empresa_id", "cliente_id", "usuario_id", "subtotal", "total", "creado_en"), filas_p)
    _copy(cur, "presupuesto_items", ("presupuesto_id", "producto_id", "nombre_producto", "cantidad",
                                     "precio_venta_unitario", "subtotal"), filas_pi)
    _copy(cur, "gastos", ("empresa_id", "monto", "responsable_nombre", "fecha", "motivo", "creado_en"),
          [(empresa_id, rnd.randrange(10_000, 2_000_000, 1000), rnd.choice(NOMBRES), fecha_al_azar()[:10],
            "Gasto operativo", fecha_al_azar()) for _ in range(2000)])

    _ajustar_secuencias(cur, ["categorias", "marcas", "proveedores", "almacenes", "usuarios", "productos",
                              "clientes", "ventas", "presupuestos"])
    conn.commit()
    cur.execute("ANALYZE")
    conn.commit()
    conn.close()
    print(f"Listo: {n_productos} productos, {n_clientes} clientes, {n_ventas} ventas, "
          f"{len(filas_items)} ítems, {len(filas_p)} presupuestos.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--productos", type=int, default=50_000)
    ap.add_argument("--clientes", type=int, default=5_000)
    ap.add_argument("--ventas", type=int, default=100_000)
    ap.add_argument("--items-por-venta", type=int, default=5)
    ap.add_argument("--confirmar-base-de-prueba", action="store_true",
                    help="Obligatorio: confirma que DATABASE_URL es una base de prueba")
    args = ap.parse_args()
    if not args.confirmar_base_de_prueba:
        raise SystemExit("Falta --confirmar-base-de-prueba (este script carga datos falsos).")
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith(("postgresql://", "postgres://")):
        raise SystemExit("DATABASE_URL debe ser una URL postgresql:// de una base de prueba.")

    import seed_data  # crea tablas, empresa y admin
    asyncio.run(seed_data.seed_database())
    generar(url.replace("postgres://", "postgresql://", 1), args.productos, args.clientes, args.ventas,
            args.items_por_venta)


if __name__ == "__main__":
    main()
