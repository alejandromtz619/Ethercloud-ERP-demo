-- IVA por producto (10, 5 o 0 = exento). Ver la versión de PostgreSQL.
ALTER TABLE productos ADD COLUMN tasa_iva SMALLINT NOT NULL DEFAULT 10;
ALTER TABLE venta_items ADD COLUMN tasa_iva SMALLINT NOT NULL DEFAULT 10;
ALTER TABLE presupuesto_items ADD COLUMN tasa_iva SMALLINT NOT NULL DEFAULT 10;
