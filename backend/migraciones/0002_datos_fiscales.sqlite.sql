-- Datos para la factura electrónica (SIFEN). Ver la versión de PostgreSQL.
ALTER TABLE clientes ADD COLUMN tipo_contribuyente SMALLINT;
ALTER TABLE clientes ADD COLUMN tipo_operacion SMALLINT;
ALTER TABLE clientes ADD COLUMN numero_casa INTEGER;
ALTER TABLE clientes ADD COLUMN departamento SMALLINT;
ALTER TABLE clientes ADD COLUMN distrito SMALLINT;
ALTER TABLE clientes ADD COLUMN ciudad INTEGER;
ALTER TABLE productos ADD COLUMN unidad_medida SMALLINT NOT NULL DEFAULT 77;
