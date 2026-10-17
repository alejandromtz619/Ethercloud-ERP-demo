-- IVA por producto (10, 5 o 0 = exento). Los ítems de venta y de presupuesto guardan la tasa del
-- momento en que se cargaron. Todo lo existente queda en 10, que era el único IVA que se aplicaba.
ALTER TABLE productos ADD COLUMN IF NOT EXISTS tasa_iva SMALLINT NOT NULL DEFAULT 10;
ALTER TABLE venta_items ADD COLUMN IF NOT EXISTS tasa_iva SMALLINT NOT NULL DEFAULT 10;
ALTER TABLE presupuesto_items ADD COLUMN IF NOT EXISTS tasa_iva SMALLINT NOT NULL DEFAULT 10;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_productos_tasa_iva') THEN
        ALTER TABLE productos ADD CONSTRAINT ck_productos_tasa_iva CHECK (tasa_iva IN (0, 5, 10));
    END IF;
END $$;
