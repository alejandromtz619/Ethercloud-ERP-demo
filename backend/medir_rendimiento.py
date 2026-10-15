"""
Mide el tiempo y el tamaño de respuesta de las llamadas que hace cada pantalla al abrirse.

    python medir_rendimiento.py --url http://localhost:8000 --email admin@ether.com --password admin123

Usar contra una base de prueba cargada con generar_datos_volumen.py. Imprime una tabla
ordenada de la más lenta a la más rápida (mediana de --repeticiones corridas).
"""
import argparse
import statistics
import time
from datetime import date

import httpx

HOY = date.today().isoformat()
INICIO_ANIO = date(date.today().year, 1, 1).isoformat()

# (pantalla, ruta) — mismas consultas que el frontend al abrir cada pantalla
LLAMADAS = [
    ("Productos/Ventas/Stock/…", "/productos?empresa_id=1"),
    ("Clientes/Ventas/…", "/clientes?empresa_id=1"),
    ("Stock", "/stock?empresa_id=1"),
    ("Proveedores/Productos/…", "/proveedores?empresa_id=1"),
    ("Proveedores", "/proveedores/comparacion-mercado?empresa_id=1"),
    ("Presupuestos", "/presupuestos?empresa_id=1"),
    ("Historial de ventas", "/ventas?empresa_id=1&limit=100"),
    ("Delivery", "/entregas?empresa_id=1"),
    ("Facturas", "/facturas/clientes-pendientes?empresa_id=1"),
    ("Facturas", "/facturas/grupales?empresa_id=1"),
    ("Gastos", "/gastos?empresa_id=1"),
    ("Dashboard", "/dashboard/stats?empresa_id=1"),
    ("Dashboard", "/dashboard/ventas-periodo?empresa_id=1&periodo=dia"),
    ("Dashboard", "/alertas?empresa_id=1"),
    ("BI estadísticas", "/bi/estadisticas-productos?empresa_id=1&periodo=semanal&periodos=8"),
    ("BI cierre", f"/bi/cierre?empresa_id=1&fecha_desde={INICIO_ANIO}&fecha_hasta={HOY}"),
    ("BI sugerencias", "/bi/sugerencias-compra?empresa_id=1&semanas_analisis=4&semanas_cobertura=4"),
    ("BI exceso", "/bi/exceso-compras?empresa_id=1&semanas_referencia=4"),
    ("BI aging", "/bi/aging-tandas?empresa_id=1&orden=mas_antiguo"),
    ("Ventas (vendedores)", "/usuarios?empresa_id=1"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--email", default="admin@ether.com")
    ap.add_argument("--password", default="admin123")
    ap.add_argument("--repeticiones", type=int, default=3)
    ap.add_argument("--solo", help="Medir sólo las rutas que contengan este texto")
    args = ap.parse_args()

    with httpx.Client(base_url=f"{args.url}/api", timeout=300) as c:
        r = c.post("/auth/login", json={"email": args.email, "password": args.password})
        r.raise_for_status()
        c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

        filas = []
        for pantalla, ruta in LLAMADAS:
            if args.solo and args.solo not in ruta:
                continue
            tiempos, tam, estado = [], 0, None
            for _ in range(args.repeticiones):
                t0 = time.perf_counter()
                r = c.get(ruta)
                tiempos.append(time.perf_counter() - t0)
                tam, estado = len(r.content), r.status_code
            filas.append((statistics.median(tiempos), tam, estado, pantalla, ruta))

    filas.sort(reverse=True)
    print(f"{'seg':>7} {'KB':>9} {'HTTP':>4}  pantalla — ruta")
    for seg, tam, estado, pantalla, ruta in filas:
        print(f"{seg:7.2f} {tam / 1024:9.0f} {estado:>4}  {pantalla} — {ruta}")
    print(f"\nTotal: {sum(f[0] for f in filas):.1f} s, {sum(f[1] for f in filas) / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
