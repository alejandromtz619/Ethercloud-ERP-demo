-- Datos para la factura electrónica (SIFEN). Clientes: tipo de contribuyente, tipo de operación y
-- domicilio con los códigos de los catálogos de SIFEN (departamento, distrito, ciudad); todo opcional:
-- sin ellos la factura sale sin dirección del receptor. Productos: unidad de medida (77 = unidad).
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS tipo_contribuyente SMALLINT;
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS tipo_operacion SMALLINT;
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS numero_casa INTEGER;
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS departamento SMALLINT;
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS distrito SMALLINT;
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS ciudad INTEGER;
ALTER TABLE productos ADD COLUMN IF NOT EXISTS unidad_medida SMALLINT NOT NULL DEFAULT 77;
