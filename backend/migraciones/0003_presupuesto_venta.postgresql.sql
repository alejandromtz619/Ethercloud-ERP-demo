-- Presupuesto -> pedido desde el CRM (API de integración v1): la venta PENDIENTE que salió del presupuesto.
ALTER TABLE presupuestos ADD COLUMN IF NOT EXISTS venta_id INTEGER REFERENCES ventas(id);
