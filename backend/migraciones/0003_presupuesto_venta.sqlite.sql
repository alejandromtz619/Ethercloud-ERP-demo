-- Presupuesto -> pedido desde el CRM. Ver la versión de PostgreSQL.
ALTER TABLE presupuestos ADD COLUMN venta_id INTEGER REFERENCES ventas(id);
