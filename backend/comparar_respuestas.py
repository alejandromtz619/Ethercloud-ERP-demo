"""
Red de seguridad para optimizaciones: guarda las respuestas de la API y después verifica
que un backend modificado devuelva exactamente lo mismo.

    python comparar_respuestas.py guardar   --url http://localhost:8000 --dir antes/
    (cambiar el código y reiniciar el backend)
    python comparar_respuestas.py comparar  --url http://localhost:8000 --dir antes/

Usar contra una base de prueba (generar_datos_volumen.py) que no cambie entre las dos corridas.
"""
import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

import httpx

HOY = date.today().isoformat()
INICIO_ANIO = date(date.today().year, 1, 1).isoformat()

RUTAS = [
    "/productos?empresa_id=1",
    "/clientes?empresa_id=1",
    "/stock?empresa_id=1",
    "/proveedores?empresa_id=1",
    "/presupuestos?empresa_id=1",
    "/ventas?empresa_id=1&limit=100",
    "/ventas?empresa_id=1&limit=50&estado=CONFIRMADA&fecha_desde=2025-06-01&fecha_hasta=2025-06-30",
    "/ventas/1", "/ventas/500", "/ventas/99999",
    "/entregas?empresa_id=1",
    "/entregas?empresa_id=1&estado=PENDIENTE",
    "/facturas/clientes-pendientes?empresa_id=1",
    "/gastos?empresa_id=1",
    "/dashboard/stats?empresa_id=1",
    "/dashboard/ventas-periodo?empresa_id=1&periodo=dia",
    "/dashboard/ventas-periodo?empresa_id=1&periodo=mes",
    "/alertas?empresa_id=1",
    "/bi/estadisticas-productos?empresa_id=1&periodo=semanal&periodos=8",
    f"/bi/cierre?empresa_id=1&fecha_desde={INICIO_ANIO}&fecha_hasta={HOY}",
    "/bi/sugerencias-compra?empresa_id=1&semanas_analisis=4&semanas_cobertura=4",
    "/bi/exceso-compras?empresa_id=1&semanas_referencia=4",
    "/bi/aging-tandas?empresa_id=1&orden=mas_antiguo",
    "/bi/producto-evolucion?empresa_id=1&producto_id=7&periodo=semanal&periodos=8",
    "/clientes/1/creditos",
    "/stock/historial/7",
    "/funcionarios?empresa_id=1",
]


def _archivo(directorio: Path, ruta: str) -> Path:
    return directorio / (hashlib.sha1(ruta.encode()).hexdigest()[:16] + ".json")


def _normalizar(datos):
    """Quita campos que cambian solos entre corridas (marcas de tiempo de 'ahora')."""
    if isinstance(datos, dict):
        return {k: _normalizar(v) for k, v in datos.items() if k not in ("timestamp", "generado_en")}
    if isinstance(datos, list):
        return [_normalizar(v) for v in datos]
    return datos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("accion", choices=["guardar", "comparar"])
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--email", default="admin@ether.com")
    ap.add_argument("--password", default="admin123")
    args = ap.parse_args()
    directorio = Path(args.dir)
    directorio.mkdir(parents=True, exist_ok=True)

    with httpx.Client(base_url=f"{args.url}/api", timeout=600) as c:
        r = c.post("/auth/login", json={"email": args.email, "password": args.password})
        r.raise_for_status()
        c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        distintas = 0
        for ruta in RUTAS:
            r = c.get(ruta)
            actual = {"status": r.status_code, "body": _normalizar(r.json()) if r.content else None}
            archivo = _archivo(directorio, ruta)
            if args.accion == "guardar":
                archivo.write_text(json.dumps(actual, ensure_ascii=False, sort_keys=True), encoding="utf-8")
                print(f"guardada  {r.status_code}  {ruta}")
            else:
                antes = json.loads(archivo.read_text(encoding="utf-8"))
                igual = antes == json.loads(json.dumps(actual, ensure_ascii=False, sort_keys=True))
                distintas += not igual
                print(f"{'igual   ' if igual else 'DISTINTA'}  {r.status_code}  {ruta}")
        if args.accion == "comparar":
            print(f"\n{len(RUTAS) - distintas}/{len(RUTAS)} iguales")
            raise SystemExit(1 if distintas else 0)


if __name__ == "__main__":
    main()
