# Cómo revertir una anulación de venta accidental

Cuando un usuario anula una venta por error desde Historial de Ventas, el sistema ejecuta varias operaciones encadenadas que deben revertirse manualmente desde pgAdmin.

---

## Qué hace el sistema al anular una venta

1. **Devuelve stock** a los almacenes originales (movimientos `ANULACION_VENTA` tipo `ENTRADA`, sin lote FIFO propio)
   - **FIFO:** suma las unidades devueltas a `cantidad_restante` de los lotes de entrada de origen (del más nuevo al más viejo) y recalcula `productos.precio_costo`
2. **Elimina la entrega** (`Entrega`) asociada a la venta ⚠️ *irrecuperable*
3. **Crédito** (si era venta a crédito):
   - Sin pagos → elimina el registro `creditos_clientes`
   - Con pagos → setea `monto_pendiente = 0` y agrega `" (ANULADO)"` a la descripción
4. **Laboratorio** (si tenía ítems de materia): devuelve materias a estado `DISPONIBLE`

---

## Paso 1 — Diagnóstico

```sql
-- Ver la venta
SELECT id, cliente_id, total, tipo_pago, estado, creado_en FROM ventas WHERE id = <VENTA_ID>;

-- Ver ítems de la venta
SELECT vi.id, vi.venta_id, vi.producto_id, vi.cantidad, vi.precio_unitario, vi.subtotal, vi.materia_laboratorio_id, p.nombre 
FROM venta_items vi
LEFT JOIN productos p ON vi.producto_id = p.id
WHERE vi.venta_id = <VENTA_ID>;

-- Ver movimientos de devolución creados
SELECT * FROM movimientos_stock 
WHERE referencia_tipo = 'ANULACION_VENTA' AND referencia_id = <VENTA_ID>;

-- Ver crédito (si era venta a crédito)
SELECT v.tipo_pago, cc.* 
FROM ventas v
LEFT JOIN creditos_clientes cc ON cc.venta_id = v.id
WHERE v.id = <VENTA_ID>;
```

---

## Paso 2 — Script de reversión

Reemplazar `<VENTA_ID>`, `<CLIENTE_ID>`, `<TOTAL>`, `<FECHA>` con los valores reales del diagnóstico.

```sql
BEGIN;

-- 1. Revertir estado de la venta
UPDATE ventas SET estado = 'CONFIRMADA' WHERE id = <VENTA_ID>;

-- 2. Descontar stock devuelto incorrectamente
--    (repetir un UPDATE por cada fila de movimientos_stock del diagnóstico)
UPDATE stock_actual SET cantidad = cantidad - <CANTIDAD>
WHERE producto_id = <PRODUCTO_ID> AND almacen_id = <ALMACEN_ID>;
-- ... (una línea por cada movimiento de ANULACION_VENTA)

-- 2b. FIFO: volver a descontar las unidades de los lotes de entrada.
--     Ver los lotes del producto (el sistema restauró primero los más nuevos):
--     SELECT id, cantidad, cantidad_restante, costo_unitario, creado_en FROM movimientos_stock
--      WHERE producto_id = <PRODUCTO_ID> AND tipo = 'ENTRADA' AND cantidad_restante IS NOT NULL
--      ORDER BY creado_en ASC;
--     y descontar las unidades empezando por el lote MÁS VIEJO con saldo (orden FIFO):
UPDATE movimientos_stock SET cantidad_restante = cantidad_restante - <UNIDADES>
WHERE id = <ID_LOTE>;
-- ... (una línea por lote hasta cubrir la cantidad vendida)

-- 3. Eliminar movimientos falsos de devolución
DELETE FROM movimientos_stock 
WHERE referencia_tipo = 'ANULACION_VENTA' AND referencia_id = <VENTA_ID>;

-- 4a. Si era crédito SIN pagos (el registro fue eliminado): recrearlo
INSERT INTO creditos_clientes 
    (cliente_id, venta_id, monto_original, monto_pendiente, descripcion, fecha_venta, pagado, creado_en)
VALUES 
    (<CLIENTE_ID>, <VENTA_ID>, <TOTAL>, <TOTAL>, 'Crédito venta #<VENTA_ID>', '<FECHA>', false, '<TIMESTAMP>');

-- 4b. Si era crédito CON pagos (el registro existe pero fue modificado): restaurarlo
-- UPDATE creditos_clientes 
--    SET monto_pendiente = <MONTO_PENDIENTE_ORIGINAL>,
--        descripcion = REPLACE(descripcion, ' (ANULADO)', '')
--    WHERE venta_id = <VENTA_ID>;

-- 5. Verificar stock no quedó negativo
SELECT producto_id, almacen_id, cantidad FROM stock_actual 
WHERE producto_id IN (<lista de producto_ids>) AND almacen_id = <ALMACEN_ID>;

-- Si todos los valores son >= 0:
COMMIT;
-- Si algo quedó negativo:
-- ROLLBACK;
```

---

## Paso 3 — Post-verificación en la app

- Abrir Historial de Ventas y confirmar que la venta aparece como `CONFIRMADA`
- Revisar el módulo de Créditos del cliente para verificar que el saldo es correcto
- Revisar el stock en el módulo Stock si aplica
- Revisar en Stock > Historial del producto que la columna **Restante** de los lotes sume lo mismo que el stock actual

---

## Limitaciones conocidas

- **La entrega (Delivery) no se puede recuperar** — fue eliminada permanentemente. Debe recrearse manualmente desde el módulo de Ventas o Delivery si corresponde.
- **Ítems de laboratorio**: si la materia fue revendida después de la anulación accidental, hay que revisar manualmente el estado en la tabla `materias_laboratorio`.

---

## Tablas involucradas

| Tabla | Acción en anulación | Cómo revertir |
|---|---|---|
| `ventas` | `estado` → `ANULADA` | `UPDATE estado = 'CONFIRMADA'` |
| `stock_actual` | `cantidad` += devuelto | `UPDATE cantidad -= devuelto` |
| `movimientos_stock` (lotes ENTRADA) | `cantidad_restante` += devuelto | `UPDATE cantidad_restante -= devuelto` (orden FIFO) |
| `movimientos_stock` | INSERT `ANULACION_VENTA` ENTRADA | `DELETE` esos registros |
| `creditos_clientes` | DELETE (sin pagos) o monto→0 | INSERT o UPDATE |
| `entregas` | DELETE | ⚠️ Irrecuperable |
| `materias_laboratorio` | `estado` → `DISPONIBLE` | `UPDATE estado = 'VENDIDO'` |
