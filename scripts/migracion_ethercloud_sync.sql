-- ========================================
-- SCRIPTS DE MIGRACIÓN PostgreSQL
-- LuzBrill ERP - Sincronización con Ethercloud
-- Fecha: Marzo 11, 2026
-- ========================================

-- IMPORTANTE: Ejecutar estos scripts en orden desde pgAdmin o psql
-- Hacer BACKUP de la base de datos antes de ejecutar

-- ========================================
-- 1. AGREGAR ENUM VENTA A TipoMovimientoStock
-- ========================================

-- PostgreSQL: Agregar valor al enum existente
ALTER TYPE tipomovimientostock ADD VALUE IF NOT EXISTS 'VENTA';

-- NOTA: En PostgreSQL no se puede agregar valores a enums si están en una transacción activa.
-- Si el comando anterior falla, usar este enfoque alternativo:

-- BEGIN;
-- ALTER TYPE tipomovimientostock RENAME TO tipomovimientostock_old;
-- CREATE TYPE tipomovimientostock AS ENUM ('ENTRADA', 'SALIDA', 'AJUSTE', 'TRASPASO', 'VENTA');
-- ALTER TABLE movimientos_stock ALTER COLUMN tipo TYPE tipomovimientostock USING tipo::text::tipomovimientostock;
-- DROP TYPE tipomovimientostock_old;
-- COMMIT;

-- ========================================
-- 2. AGREGAR CAMPOS A movimientos_stock
-- ========================================

ALTER TABLE movimientos_stock 
ADD COLUMN IF NOT EXISTS costo_ponderado NUMERIC(15, 2),
ADD COLUMN IF NOT EXISTS cantidad_restante INTEGER;

-- Comentarios para documentación
COMMENT ON COLUMN movimientos_stock.costo_ponderado IS 'Costo Promedio Ponderado (CPP) aplicado al producto al momento de la entrada';
COMMENT ON COLUMN movimientos_stock.cantidad_restante IS 'Unidades restantes en este lote (tracking FIFO). Solo para movimientos tipo ENTRADA';

-- Inicializar cantidad_restante para entradas existentes
-- Esto simula que todos los lotes antiguos están "disponibles" aún
UPDATE movimientos_stock 
SET cantidad_restante = cantidad 
WHERE tipo = 'ENTRADA' AND cantidad_restante IS NULL;

-- ========================================
-- 3. CREAR TABLA gastos
-- ========================================

CREATE TABLE IF NOT EXISTS gastos (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    monto NUMERIC(15, 2) NOT NULL CHECK (monto >= 0),
    responsable_nombre VARCHAR(255) NOT NULL,
    fecha DATE NOT NULL,
    motivo VARCHAR(500) NOT NULL,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para mejorar performance de consultas
CREATE INDEX IF NOT EXISTS idx_gastos_empresa ON gastos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_gastos_fecha ON gastos(fecha);
CREATE INDEX IF NOT EXISTS idx_gastos_empresa_fecha ON gastos(empresa_id, fecha DESC);

-- Comentario para documentación
COMMENT ON TABLE gastos IS 'Gastos operativos de la empresa (agua, combustible, imprevistos, etc.)';
COMMENT ON COLUMN gastos.responsable_nombre IS 'Nombre del empleado o persona responsable del gasto';
COMMENT ON COLUMN gastos.motivo IS 'Descripción o justificación del gasto';

-- ========================================
-- 4. AGREGAR NUEVOS PERMISOS
-- ========================================

-- Insertar permisos de Gastos
INSERT INTO permisos (clave, descripcion) 
VALUES
    ('gastos.ver', 'Ver gastos operativos'),
    ('gastos.crear', 'Crear gastos operativos'),
    ('gastos.editar', 'Editar gastos operativos'),
    ('gastos.eliminar', 'Eliminar gastos operativos'),
    ('reportes.business_intelligence', 'Acceso a Business Intelligence dashboard'),
    ('proveedores.comparacion_mercado', 'Acceso a comparación de mercado de proveedores')
ON CONFLICT (clave) DO NOTHING;

-- Asignar permisos al rol de Administrador (ajustar rol_id según tu BD)
-- IMPORTANTE: Verificar el ID del rol de Administrador en tu base de datos
DO $$
DECLARE
    admin_rol_id INTEGER;
BEGIN
    -- Buscar el rol de admin de la empresa 1 (ajustar según tu configuración)
    SELECT id INTO admin_rol_id 
    FROM roles 
    WHERE LOWER(nombre) LIKE '%admin%' 
    AND empresa_id = 1
    LIMIT 1;
    
    IF admin_rol_id IS NOT NULL THEN
        -- Insertar permisos para el rol admin
        INSERT INTO rol_permisos (rol_id, permiso_id)
        SELECT admin_rol_id, id 
        FROM permisos 
        WHERE clave IN (
            'gastos.ver', 
            'gastos.crear', 
            'gastos.editar', 
            'gastos.eliminar',
            'reportes.business_intelligence',
            'proveedores.comparacion_mercado'
        )
        ON CONFLICT DO NOTHING;
        
        RAISE NOTICE 'Permisos asignados al rol admin (ID: %)', admin_rol_id;
    ELSE
        RAISE NOTICE 'No se encontró rol de administrador. Asignar permisos manualmente.';
    END IF;
END $$;

-- ========================================
-- 5. VERIFICACIÓN DE INTEGRIDAD
-- ========================================

-- Verificar que la tabla gastos se creó correctamente
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'gastos') 
        THEN '✓ Tabla gastos creada correctamente'
        ELSE '✗ ERROR: Tabla gastos NO se creó'
    END AS verificacion_gastos;

-- Verificar que los campos se agregaron a movimientos_stock
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'movimientos_stock' 
AND column_name IN ('costo_ponderado', 'cantidad_restante')
ORDER BY column_name;

-- Verificar permisos nuevos
SELECT clave, descripcion 
FROM permisos 
WHERE clave LIKE 'gastos.%' OR clave LIKE 'reportes.business%' OR clave LIKE 'proveedores.comparacion%'
ORDER BY clave;

-- Contar registros de entrada con cantidad_restante inicializada
SELECT 
    COUNT(*) as total_entradas,
    COUNT(cantidad_restante) as con_cantidad_restante,
    COUNT(*) - COUNT(cantidad_restante) as sin_cantidad_restante
FROM movimientos_stock 
WHERE tipo = 'ENTRADA';

-- ========================================
-- 6. ROLLBACK (En caso de error - OPCIONAL)
-- ========================================

-- SOLO EJECUTAR SI NECESITAS REVERTIR LOS CAMBIOS
-- COMENTADO POR SEGURIDAD - DESCOMENTAR SOLO SI ES NECESARIO

/*
-- Eliminar tabla gastos
-- DROP TABLE IF EXISTS gastos CASCADE;

-- Eliminar permisos nuevos
-- DELETE FROM rol_permisos WHERE permiso_id IN (
--     SELECT id FROM permisos WHERE clave IN (
--         'gastos.ver', 'gastos.crear', 'gastos.editar', 'gastos.eliminar',
--         'reportes.business_intelligence', 'proveedores.comparacion_mercado'
--     )
-- );

-- DELETE FROM permisos WHERE clave IN (
--     'gastos.ver', 'gastos.crear', 'gastos.editar', 'gastos.eliminar',
--     'reportes.business_intelligence', 'proveedores.comparacion_mercado'
-- );

-- Eliminar columnas de movimientos_stock
-- ALTER TABLE movimientos_stock 
-- DROP COLUMN IF EXISTS costo_ponderado,
-- DROP COLUMN IF EXISTS cantidad_restante;

-- Nota: Revertir enum es más complejo y requiere recrear el tipo
*/

-- ========================================
-- 7. NOTAS ADICIONALES
-- ========================================

-- IMPORTANTE:
-- 1. Estos cambios son RETROCOMPATIBLES y no rompen funcionalidad existente
-- 2. Los campos nuevos son OPCIONALES (nullable)
-- 3. Se recomienda probar en entorno de desarrollo antes de producción
-- 4. Hacer BACKUP completo antes de ejecutar en producción
-- 5. Revisar logs después de la migración para detectar errores

-- Para verificar que todo funcionó:
-- SELECT * FROM gastos LIMIT 1;  -- Debe estar vacío pero sin errores
-- SELECT costo_ponderado, cantidad_restante FROM movimientos_stock WHERE tipo = 'ENTRADA' LIMIT 5;

-- ========================================
-- FIN DE SCRIPTS DE MIGRACIÓN
-- ========================================
