-- =============================================================
-- Migración v2 - Nuevos campos para costos, ganancias y stock
-- Ejecutar sobre la base de datos existente (PostgreSQL)
-- =============================================================

-- 1. productos: precio_costo + proveedor_id
ALTER TABLE productos
    ADD COLUMN IF NOT EXISTS precio_costo   NUMERIC(15, 2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS proveedor_id   INTEGER REFERENCES proveedores(id) ON DELETE SET NULL;

-- 2. productos.codigo_barra: permitir NULL (antes era NOT NULL en algunos setups)
ALTER TABLE productos
    ALTER COLUMN codigo_barra DROP NOT NULL;

-- 3. materias_laboratorio.codigo_barra: permitir NULL
ALTER TABLE materias_laboratorio
    ALTER COLUMN codigo_barra DROP NOT NULL;

-- 4. movimientos_stock: campos de compra
ALTER TABLE movimientos_stock
    ADD COLUMN IF NOT EXISTS proveedor_id       INTEGER REFERENCES proveedores(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS costo_unitario     NUMERIC(15, 2),
    ADD COLUMN IF NOT EXISTS condicion_pago     VARCHAR(20),
    ADD COLUMN IF NOT EXISTS fecha_limite_pago  DATE,
    ADD COLUMN IF NOT EXISTS notas              TEXT;

-- 5. ventas: costo_total + ganancia
ALTER TABLE ventas
    ADD COLUMN IF NOT EXISTS costo_total  NUMERIC(15, 2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS ganancia     NUMERIC(15, 2) NOT NULL DEFAULT 0;

-- 6. venta_items: precio_costo
ALTER TABLE venta_items
    ADD COLUMN IF NOT EXISTS precio_costo  NUMERIC(15, 2) NOT NULL DEFAULT 0;

-- 7. clientes.limite_credito: cambiar default a 1
ALTER TABLE clientes
    ALTER COLUMN limite_credito SET DEFAULT 1;
