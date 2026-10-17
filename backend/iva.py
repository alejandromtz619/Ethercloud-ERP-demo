"""
IVA incluido en los precios (Paraguay): tasas 10 %, 5 % y 0 (exento).

Los precios ya traen el IVA. Por cada tasa:
    bruto = suma de los ítems a esa tasa (antes del descuento de la venta)
    neto  = bruto prorrateado al total con descuento
    iva   = neto * tasa / (100 + tasa)
Con todos los ítems al 10 % el resultado es el de siempre (total * 10 / 110).
"""
from collections import defaultdict
from decimal import Decimal

TASAS_IVA = (10, 5, 0)


def validar_tasa(tasa) -> int:
    if tasa not in TASAS_IVA:
        raise ValueError(f"Tasa de IVA inválida: {tasa} (se admite 10, 5 o 0)")
    return tasa


def desglose_iva(items, total) -> dict:
    """items: [(monto_bruto, tasa)]; total: monto final, ya con el descuento.
    Devuelve {tasa: {"bruto", "neto", "iva"}} (Decimal, sin redondear) sólo con las tasas presentes."""
    bruto = defaultdict(Decimal)
    for monto, tasa in items:
        bruto[tasa] += Decimal(monto)
    subtotal = sum(bruto.values(), Decimal(0))
    total = Decimal(total)
    desglose = {}
    for tasa, b in bruto.items():
        neto = b * total / subtotal if subtotal else Decimal(0)
        desglose[tasa] = {"bruto": b, "neto": neto, "iva": neto * tasa / (100 + tasa)}
    return desglose


def iva_total(desglose: dict) -> Decimal:
    return sum((d["iva"] for d in desglose.values()), Decimal(0))


def liquidacion_impresa(desglose: dict) -> dict:
    """Liquidación del IVA como se imprime en boletas y facturas (guaraníes redondeados)."""
    divisor = {10: 1.10, 5: 1.05}
    iva = {t: round(float(d["neto"]) - float(d["neto"]) / divisor[t], 0) for t, d in desglose.items() if t in divisor}
    return {"iva_5": iva.get(5, 0), "iva_10": iva.get(10, 0), "total_iva": iva.get(5, 0) + iva.get(10, 0)}
