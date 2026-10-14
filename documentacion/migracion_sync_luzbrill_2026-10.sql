-- =====================================================================
-- Migración de esquema: sincronización con las funciones de LuzBrill
-- (presupuestos, facturación englobada, fecha de impresión, etc.)
--
-- PostgreSQL. Ejecutar en pgAdmin DESPUÉS de hacer backup (pg_dump).
-- Es idempotente: se puede correr más de una vez sin romper nada.
-- Aplicar ANTES de desplegar el backend nuevo.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0. Enum de movimientos de stock
--    En PostgreSQL < 12 esta sentencia no puede ir dentro de una
--    transacción: si da error, ejecutarla sola.
-- ---------------------------------------------------------------------
ALTER TYPE tipomovimientostock ADD VALUE IF NOT EXISTS 'VENTA';

BEGIN;

-- ---------------------------------------------------------------------
-- 1. CPP / FIFO (por si la base es anterior a esas funciones)
-- ---------------------------------------------------------------------
ALTER TABLE movimientos_stock ADD COLUMN IF NOT EXISTS costo_ponderado NUMERIC(15,2);
ALTER TABLE movimientos_stock ADD COLUMN IF NOT EXISTS cantidad_restante INTEGER;

-- ---------------------------------------------------------------------
-- 2. Vínculo producto <-> proveedor (SKU, costo, link)
-- ---------------------------------------------------------------------
ALTER TABLE proveedor_productos ADD COLUMN IF NOT EXISTS sku VARCHAR(100);
ALTER TABLE proveedor_productos ADD COLUMN IF NOT EXISTS link VARCHAR(1000);
ALTER TABLE proveedor_productos ALTER COLUMN costo DROP NOT NULL;

-- ---------------------------------------------------------------------
-- 3. Gastos operativos
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gastos (
    id                  SERIAL PRIMARY KEY,
    empresa_id          INTEGER NOT NULL REFERENCES empresas(id),
    monto               NUMERIC(15,2) NOT NULL,
    responsable_nombre  VARCHAR(255) NOT NULL,
    fecha               DATE NOT NULL,
    motivo              VARCHAR(500) NOT NULL,
    creado_en           TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- 4. Ventas: facturada (facturación englobada) y fecha de impresión
--    Las fechas de impresión NO afectan reportes, cierres ni stock.
--    NULL = se imprime la fecha real de la venta.
-- ---------------------------------------------------------------------
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS facturada BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS fecha_impresion_boleta DATE;
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS fecha_impresion_factura DATE;

-- ---------------------------------------------------------------------
-- 5. Productos: fecha de alta (detección de código de barras duplicado)
-- ---------------------------------------------------------------------
ALTER TABLE productos ADD COLUMN IF NOT EXISTS creado_en TIMESTAMPTZ DEFAULT NOW();

-- ---------------------------------------------------------------------
-- 6. Facturación englobada
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS facturas_grupales (
    id          SERIAL PRIMARY KEY,
    empresa_id  INTEGER NOT NULL REFERENCES empresas(id),
    cliente_id  INTEGER NOT NULL REFERENCES clientes(id),
    numero      VARCHAR(50) NOT NULL,
    condicion   VARCHAR(10) NOT NULL DEFAULT 'CONTADO',
    total       NUMERIC(15,2) NOT NULL,
    iva         NUMERIC(15,2) NOT NULL,
    creado_en   TIMESTAMPTZ DEFAULT NOW()
);
-- Por si la tabla ya existía sin esta columna (el SQL original de LuzBrill no la tenía)
ALTER TABLE facturas_grupales ADD COLUMN IF NOT EXISTS condicion VARCHAR(10) NOT NULL DEFAULT 'CONTADO';

CREATE TABLE IF NOT EXISTS factura_grupal_ventas (
    factura_grupal_id  INTEGER NOT NULL REFERENCES facturas_grupales(id),
    venta_id           INTEGER NOT NULL REFERENCES ventas(id),
    PRIMARY KEY (factura_grupal_id, venta_id)
);

-- ---------------------------------------------------------------------
-- 7. Presupuestos (no afectan stock ni ventas)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS presupuestos (
    id          SERIAL PRIMARY KEY,
    empresa_id  INTEGER NOT NULL REFERENCES empresas(id),
    cliente_id  INTEGER NOT NULL REFERENCES clientes(id),
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
    subtotal    NUMERIC(15,2) DEFAULT 0,
    total       NUMERIC(15,2) DEFAULT 0,
    notas       TEXT,
    creado_en   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS presupuesto_items (
    id                     SERIAL PRIMARY KEY,
    presupuesto_id         INTEGER NOT NULL REFERENCES presupuestos(id),
    producto_id            INTEGER REFERENCES productos(id),
    nombre_producto        VARCHAR(255) NOT NULL,
    imagen_url             VARCHAR(500),
    cantidad               INTEGER NOT NULL,
    precio_venta_unitario  NUMERIC(15,2) NOT NULL,
    subtotal               NUMERIC(15,2) NOT NULL
);

-- ---------------------------------------------------------------------
-- 8. Índices (el backend también los crea al arrancar: ensure_indices)
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_materias_laboratorio_empresa_id ON materias_laboratorio (empresa_id);
CREATE INDEX IF NOT EXISTS ix_materias_laboratorio_estado     ON materias_laboratorio (estado);
CREATE INDEX IF NOT EXISTS ix_materias_laboratorio_creado_en  ON materias_laboratorio (creado_en);
CREATE INDEX IF NOT EXISTS ix_productos_empresa_id            ON productos (empresa_id);
CREATE INDEX IF NOT EXISTS ix_productos_activo                ON productos (activo);
CREATE INDEX IF NOT EXISTS ix_stock_actual_producto_id        ON stock_actual (producto_id);
CREATE INDEX IF NOT EXISTS ix_movimientos_stock_producto_id   ON movimientos_stock (producto_id);
CREATE INDEX IF NOT EXISTS ix_clientes_empresa_id             ON clientes (empresa_id);
CREATE INDEX IF NOT EXISTS ix_ventas_empresa_id               ON ventas (empresa_id);
CREATE INDEX IF NOT EXISTS ix_venta_items_venta_id            ON venta_items (venta_id);

-- ---------------------------------------------------------------------
-- 9. Permisos nuevos (el backend también los crea al arrancar:
--    ensure_permisos) y asignación a todos los roles ADMIN
-- ---------------------------------------------------------------------
INSERT INTO permisos (clave, descripcion)
SELECT v.clave, v.descripcion
FROM (VALUES
    ('dashboard.ver',          'Ver dashboard'),
    ('bi.ver',                 'Ver Business Intelligence'),
    ('gastos.ver',             'Ver gastos operativos'),
    ('gastos.gestionar',       'Gestionar gastos operativos'),
    ('delivery.eliminar',      'Eliminar entregas'),
    ('laboratorio.editar',     'Editar materias de laboratorio'),
    ('laboratorio.eliminar',   'Eliminar materias de laboratorio'),
    ('presupuestos.ver',       'Ver presupuestos'),
    ('presupuestos.crear',     'Crear presupuestos'),
    ('presupuestos.editar',    'Editar presupuestos'),
    ('presupuestos.eliminar',  'Eliminar presupuestos')
) AS v(clave, descripcion)
WHERE NOT EXISTS (SELECT 1 FROM permisos p WHERE p.clave = v.clave);

INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r
JOIN permisos p ON p.clave IN (
    'dashboard.ver', 'bi.ver', 'gastos.ver', 'gastos.gestionar', 'delivery.eliminar',
    'laboratorio.editar', 'laboratorio.eliminar',
    'presupuestos.ver', 'presupuestos.crear', 'presupuestos.editar', 'presupuestos.eliminar'
)
WHERE r.nombre IN ('ADMIN', 'Administrador')
  AND NOT EXISTS (
      SELECT 1 FROM rol_permisos rp WHERE rp.rol_id = r.id AND rp.permiso_id = p.id
  );

COMMIT;

-- ---------------------------------------------------------------------
-- 10. (OPCIONAL) Empresa por defecto del sistema madre
--     Verificar antes el id con:  SELECT id, nombre, ruc FROM empresas;
-- ---------------------------------------------------------------------
-- UPDATE empresas
--    SET nombre = 'Ether Soluciones Tecnológicas',
--        ruc    = '5244360-4'
--  WHERE id = 1;

-- ---------------------------------------------------------------------
-- 11. (OPCIONAL) Activar FIFO en entradas antiguas
--     Las entradas sin cantidad_restante figuran como "sin FIFO" en el
--     historial y en el BI. Esto las marca como completamente disponibles;
--     sólo tiene sentido si no se vendió nada de esos lotes.
-- ---------------------------------------------------------------------
-- UPDATE movimientos_stock
--    SET cantidad_restante = cantidad
--  WHERE tipo = 'ENTRADA' AND cantidad_restante IS NULL;
