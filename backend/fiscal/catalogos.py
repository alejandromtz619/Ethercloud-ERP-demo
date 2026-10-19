"""
Catálogos de SIFEN que usa el ERP (departamentos, distritos, ciudades y unidades de medida), guardados en
catalogos.json: son datos estables del Manual Técnico. Así los formularios funcionan sin preguntarle
al proveedor y aunque la instancia todavía no tenga API key. Para actualizarlos: volver a bajar
GET /api/v1/de/constants de SIFEN SIS.
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

ARCHIVO = Path(__file__).with_name("catalogos.json")


@lru_cache(maxsize=1)
def _datos() -> dict:
    datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
    datos["_distritos"] = {d["codigo"]: d for d in datos["distritos"]}
    datos["_ciudades"] = {c["codigo"]: c for c in datos["ciudades"]}
    datos["_departamentos"] = {d["codigo"]: d for d in datos["departamentos"]}
    datos["_unidades"] = {u["codigo"]: u for u in datos["unidades_medida"]}
    return datos


def departamentos() -> list:
    return _datos()["departamentos"]


def distritos(departamento: int) -> list:
    return sorted((d for d in _datos()["distritos"] if d["departamento"] == departamento), key=lambda d: d["nombre"])


def ciudades(distrito: int) -> list:
    return sorted((c for c in _datos()["ciudades"] if c["distrito"] == distrito), key=lambda c: c["nombre"])


def unidades_medida() -> list:
    return _datos()["unidades_medida"]


def unidad_valida(codigo) -> bool:
    return codigo in _datos()["_unidades"]


def validar_ubicacion(departamento: Optional[int], distrito: Optional[int], ciudad: Optional[int]) -> None:
    """Las tres juntas o ninguna, y que se correspondan. ValueError con un mensaje para mostrar."""
    valores = (departamento, distrito, ciudad)
    if all(v is None for v in valores):
        return
    if any(v is None for v in valores):
        raise ValueError("Para la factura electrónica, el domicilio lleva departamento, distrito y ciudad (los tres)")
    datos = _datos()
    if departamento not in datos["_departamentos"]:
        raise ValueError(f"Departamento {departamento} inexistente")
    d = datos["_distritos"].get(distrito)
    if d is None or d["departamento"] != departamento:
        raise ValueError(f"El distrito {distrito} no pertenece al departamento {departamento}")
    c = datos["_ciudades"].get(ciudad)
    if c is None or c["distrito"] != distrito:
        raise ValueError(f"La ciudad {ciudad} no pertenece al distrito {distrito}")


def ubicacion_completa(departamento, distrito, ciudad) -> bool:
    try:
        validar_ubicacion(departamento, distrito, ciudad)
    except ValueError:
        return False
    return departamento is not None


def validar_datos_cliente(datos: dict) -> None:
    """Campos de factura electrónica de un cliente (los que vengan). ValueError si alguno no sirve."""
    if datos.get("tipo_contribuyente") not in (None, 1, 2):
        raise ValueError("Tipo de contribuyente: 1 (persona física) o 2 (persona jurídica)")
    if datos.get("tipo_operacion") not in (None, 1, 2, 3, 4):
        raise ValueError("Tipo de operación: 1 B2B, 2 B2C, 3 B2G o 4 B2F")
    numero = datos.get("numero_casa")
    if numero is not None and (not isinstance(numero, int) or numero < 0):
        raise ValueError("Número de casa inválido")
    validar_ubicacion(datos.get("departamento"), datos.get("distrito"), datos.get("ciudad"))
