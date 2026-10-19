"""
Contenido del documento electrónico (el "data" de SIFEN SIS) a partir de una venta del ERP. La
numeración y la fecha las agrega el servicio al emitir.

Receptor, según lo que tenga cargado el cliente:
- RUC (con o sin DV; si falta el DV se calcula) → contribuyente, venta B2B.
- Sin RUC pero con cédula → consumidor final identificado (B2C).
- Ni RUC ni cédula, o el RUC genérico de consumidor final 44444401-7 → "Sin Nombre" (innominado).
"""
import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from fiscal import catalogos
from fiscal.puerto import DocumentoInvalido

CONSUMIDOR_FINAL = "44444401"
FORMA_DE_PAGO = {"EFECTIVO": 1, "CHEQUE": 2, "TARJETA": 3, "TRANSFERENCIA": 5}
AFECTACION_IVA = {10: (1, 100), 5: (1, 100), 0: (3, 0)}  # tasa -> (ivaTipo, ivaBase): gravado o exento


def dv_ruc(numero: str) -> int:
    """Dígito verificador del RUC paraguayo (módulo 11, pesos 2 a 11 de derecha a izquierda)."""
    total, peso = 0, 2
    for digito in reversed(numero):
        total += int(digito) * peso
        peso = peso + 1 if peso < 11 else 2
    resto = total % 11
    return 11 - resto if resto > 1 else 0


def ruc_con_dv(ruc: Optional[str]) -> Optional[str]:
    """'80069563-1', '80069563' o '80.069.563-1' → '80069563-1'. None si no es un RUC.
    DocumentoInvalido si trae un DV que no corresponde (así el error se ve antes de enviar)."""
    texto = re.sub(r"[\s.]", "", ruc or "")
    m = re.fullmatch(r"(\d{3,8})(?:-(\d))?", texto)
    if not m:
        return None
    base, dv = m.group(1), m.group(2)
    correcto = dv_ruc(base)
    if dv is not None and int(dv) != correcto:
        raise DocumentoInvalido([f"El RUC {base}-{dv} no es válido: el dígito verificador debería ser {correcto}"])
    return f"{base}-{correcto}"


def _nombre(cliente) -> str:
    return " ".join(p.strip() for p in (cliente.nombre, cliente.apellido) if p and p.strip())


def receptor(cliente) -> dict:
    nombre = _nombre(cliente)
    ruc = ruc_con_dv(cliente.ruc)
    if ruc and not ruc.startswith(CONSUMIDOR_FINAL + "-"):
        base = ruc.split("-")[0]
        # Lo cargado en el cliente manda; si no, las personas jurídicas tienen RUC de 8 dígitos que empieza con 80
        tipo = getattr(cliente, "tipo_contribuyente", None) or (2 if len(base) == 8 and base.startswith("80") else 1)
        datos = {"contribuyente": True, "ruc": ruc, "razonSocial": nombre, "pais": "PRY", "tipoContribuyente": tipo,
                 "tipoOperacion": getattr(cliente, "tipo_operacion", None) or 1}
    else:
        cedula = re.sub(r"\D", "", cliente.cedula or "")
        if cedula and not ruc:
            datos = {"contribuyente": False, "documentoTipo": 1, "documentoNumero": cedula, "razonSocial": nombre,
                     "tipoOperacion": 2, "pais": "PRY"}
        else:
            return {"contribuyente": False, "documentoTipo": 5, "documentoNumero": "0", "razonSocial": "Sin Nombre",
                    "tipoOperacion": 2, "pais": "PRY"}
    # Con dirección, SIFEN exige número de casa, departamento, distrito y ciudad (códigos de su catálogo):
    # sólo se informa si el cliente tiene el domicilio completo y coherente.
    direccion = (cliente.direccion or "").strip()
    ubicacion = (getattr(cliente, "departamento", None), getattr(cliente, "distrito", None), getattr(cliente, "ciudad", None))
    if direccion and catalogos.ubicacion_completa(*ubicacion):
        datos.update(direccion=direccion[:255], numeroCasa=getattr(cliente, "numero_casa", None) or 0,
                     departamento=ubicacion[0], distrito=ubicacion[1], ciudad=ubicacion[2])
    # Datos de contacto: sólo si cumplen los largos que acepta SIFEN
    telefono = re.sub(r"\D", "", cliente.telefono or "")
    if 6 <= len(telefono) <= 15:
        datos["telefono"] = telefono
    email = (cliente.email or "").strip()
    if 3 <= len(email) <= 80 and "@" in email:
        datos["email"] = email
    datos["codigo"] = f"CLI-{cliente.id}"
    return datos


def _numero(valor) -> float | int:
    d = Decimal(str(valor))
    return int(d) if d == d.to_integral_value() else float(d)


def _guaranies(valor: Decimal) -> Decimal:
    return Decimal(valor).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def items_de_venta(filas) -> list:
    """filas: [(VentaItem, Producto | None, MateriaLaboratorio | None)]"""
    items = []
    for item, producto, materia in filas:
        if producto:
            codigo, descripcion = producto.codigo_barra or f"P{producto.id}", producto.nombre
        elif materia:
            codigo, descripcion = f"M{materia.id}", f"{materia.nombre} {materia.descripcion or ''}".strip()
        else:
            codigo, descripcion = f"I{item.id}", "Ítem"
        iva_tipo, iva_base = AFECTACION_IVA[item.tasa_iva]
        unidad = getattr(producto, "unidad_medida", None) or 77
        items.append({"codigo": codigo[:50], "descripcion": descripcion[:2000], "unidadMedida": unidad,
                      "cantidad": _numero(item.cantidad), "precioUnitario": _numero(item.precio_unitario),
                      "ivaTipo": iva_tipo, "ivaBase": iva_base, "iva": item.tasa_iva})
    return items


def total_de(items: list, descuento_global: Decimal) -> Decimal:
    """Total como lo calcula SIFEN: ítems menos el descuento global, en guaraníes enteros."""
    bruto = sum((Decimal(str(i["cantidad"])) * Decimal(str(i["precioUnitario"])) for i in items), Decimal(0))
    return _guaranies(bruto - descuento_global)


def _condicion(tipo_pago: str, total: Decimal, plazo_credito: str, cheque: Optional[dict]) -> dict:
    """Condición de la operación: crédito a plazo, o contado con la forma de pago."""
    if tipo_pago == "CREDITO":
        return {"tipo": 2, "credito": {"tipo": 1, "plazo": plazo_credito}}
    if tipo_pago == "VARIOS":  # factura agrupada de boletas pagadas de distintas formas
        return {"tipo": 1, "entregas": [{"tipo": 99, "tipoDescripcion": "Pagos varios", "monto": str(total), "moneda": "PYG"}]}
    entrega = {"tipo": FORMA_DE_PAGO.get(tipo_pago, 1), "monto": str(total), "moneda": "PYG"}
    if entrega["tipo"] == 3:  # el ERP no registra la marca de la tarjeta
        entrega["infoTarjeta"] = {"tipo": 99, "tipoDescripcion": "No especificada", "medioPago": 1}
    elif entrega["tipo"] == 2:
        numero = re.sub(r"\D", "", str((cheque or {}).get("numero") or ""))
        banco = str((cheque or {}).get("banco") or "").strip()
        if not numero or not banco:
            raise DocumentoInvalido(["Para facturar una venta pagada con cheque hacen falta el número del cheque y el banco"])
        entrega["infoCheque"] = {"numeroCheque": numero.zfill(8)[-8:], "banco": banco[:255]}
    return {"tipo": 1, "entregas": [entrega]}


def _factura(cliente, items: list, descuento, tipo_pago: str, observacion: str, plazo_credito: str,
             cheque: Optional[dict]) -> dict:
    if not items:
        raise DocumentoInvalido(["La venta no tiene ítems"])
    descuento = _guaranies(descuento or 0)
    datos = {
        "tipoEmision": 1, "tipoTransaccion": 1, "tipoImpuesto": 1, "moneda": "PYG",
        "factura": {"presencia": 1},
        "cliente": receptor(cliente),
        "items": items,
        "condicion": _condicion(tipo_pago, total_de(items, descuento), plazo_credito, cheque),
        "observacion": observacion,
    }
    if descuento > 0:
        datos["descuentoGlobal"] = int(descuento)
    return datos


def _tipo_pago(venta) -> str:
    return getattr(venta.tipo_pago, "value", venta.tipo_pago) or "EFECTIVO"


def factura_de_venta(venta, cliente, filas, vendedor=None, plazo_credito: str = "30 días",
                     cheque: Optional[dict] = None) -> dict:
    """Factura (tipo 1) de una venta confirmada, sin numeración ni fecha. cheque = {"numero", "banco"}
    para las ventas pagadas con cheque (SIFEN los exige y la venta no los guarda)."""
    observacion = f"Venta N° {venta.id}" + (f" · Vendedor: {_nombre(vendedor)}" if vendedor else "")
    return _factura(cliente, items_de_venta(filas), venta.descuento, _tipo_pago(venta), observacion, plazo_credito, cheque)


def factura_de_grupal(grupal, cliente, ventas_y_filas, plazo_credito: str = "30 días", cheque: Optional[dict] = None) -> dict:
    """Factura englobada: una factura con los ítems de varias boletas del mismo cliente (FacturaGrupal).
    ventas_y_filas: [(Venta, filas de items_de_venta)]. A crédito si la agrupada es a crédito; si no,
    contado con la forma de pago de las boletas (o "Pagos varios" si fueron distintas)."""
    items = [i for _, filas in ventas_y_filas for i in items_de_venta(filas)]
    descuento = sum((Decimal(str(v.descuento or 0)) for v, _ in ventas_y_filas), Decimal(0))
    if grupal.condicion == "CREDITO":
        tipo_pago = "CREDITO"
    else:
        formas = {_tipo_pago(v) for v, _ in ventas_y_filas} - {"CREDITO"}  # las de crédito se cobran al facturar
        tipo_pago = formas.pop() if len(formas) == 1 else "EFECTIVO" if not formas else "VARIOS"
    numeros = ", ".join(str(v.id) for v, _ in ventas_y_filas)
    return _factura(cliente, items, descuento, tipo_pago, f"Factura agrupada {grupal.numero} · Ventas N° {numeros}",
                    plazo_credito, cheque)


MOTIVOS_NOTA_CREDITO = {1: "Devolución y ajuste de precios", 2: "Devolución", 3: "Descuento", 4: "Bonificación",
                        5: "Crédito incobrable", 6: "Recupero de costo", 7: "Recupero de gasto", 8: "Ajuste de precio"}


def nota_de_credito_total(factura_datos: dict, cdc: str, numero_factura: str, motivo: int = 2) -> dict:
    """Nota de crédito (tipo 5) por el total de una factura aprobada: mismo receptor, mismos ítems y mismo
    descuento que se facturaron (se copian del documento enviado, no de la venta, que pudo cambiar)."""
    if motivo not in MOTIVOS_NOTA_CREDITO:
        raise DocumentoInvalido([f"Motivo de nota de crédito inválido: {motivo}"])
    datos = {k: factura_datos[k] for k in ("tipoEmision", "tipoImpuesto", "moneda", "cliente", "items") if k in factura_datos}
    if factura_datos.get("descuentoGlobal"):
        datos["descuentoGlobal"] = factura_datos["descuentoGlobal"]
    datos["notaCreditoDebito"] = {"motivo": motivo}
    datos["documentoAsociado"] = {"formato": 1, "cdc": cdc}
    datos["observacion"] = f"{MOTIVOS_NOTA_CREDITO[motivo]} · anula la factura {numero_factura}"
    return datos
