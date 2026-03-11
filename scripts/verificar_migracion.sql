-- ========================================
-- SCRIPT DE VERIFICACIÓN - Migración Ethercloud
-- LuzBrill ERP
-- Ejecutar DESPUÉS de migracion_ethercloud_sync.sql
-- ========================================

-- 1. Verificar nuevo valor VENTA en enum
SELECT 
    '1. Verificando ENUM TipoMovimientoStock' as paso,
    unnest(enum_range(NULL::tipomovimientostock)) as valores_permitidos;

-- 2. Verificar tabla gastos existe
SELECT 
    '2. Verificando tabla gastos' as paso,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'gastos') 
        THEN '✓ Tabla gastos creada correctamente'
        ELSE '✗ ERROR: Tabla gastos NO existe'
    END AS estado;

-- 3. Verificar columnas FIFO en movimientos_stock
SELECT 
    '3. Verificando columnas FIFO' as paso,
    column_name, 
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'movimientos_stock' 
AND column_name IN ('costo_ponderado', 'cantidad_restante')
ORDER BY column_name;

-- 4. Ver estructura completa de movimientos_stock
SELECT 
    '4. Estructura completa movimientos_stock' as paso,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'movimientos_stock'
ORDER BY ordinal_position;

-- 5. Verificar nuevos permisos
SELECT 
    '5. Verificando permisos nuevos' as paso,
    id,
    clave,
    descripcion
FROM permisos 
WHERE clave IN (
    'gastos.ver', 
    'gastos.crear', 
    'gastos.editar', 
    'gastos.eliminar',
    'reportes.business_intelligence',
    'proveedores.comparacion_mercado'
)
ORDER BY clave;

-- 6. Contar permisos asignados a rol admin
SELECT 
    '6. Permisos asignados al administrador' as paso,
    r.nombre as rol,
    COUNT(rp.permiso_id) as total_permisos_nuevos
FROM roles r
LEFT JOIN rol_permisos rp ON r.id = rp.rol_id
LEFT JOIN permisos p ON rp.permiso_id = p.id
WHERE LOWER(r.nombre) LIKE '%admin%'
AND p.clave IN (
    'gastos.ver', 
    'gastos.crear', 
    'gastos.editar', 
    'gastos.eliminar',
    'reportes.business_intelligence',
    'proveedores.comparacion_mercado'
)
GROUP BY r.id, r.nombre;

-- 7. Verificar inicialización cantidad_restante
SELECT 
    '7. Estado cantidad_restante en entradas' as paso,
    COUNT(*) as total_entradas,
    COUNT(cantidad_restante) as con_cantidad_restante,
    COUNT(*) - COUNT(cantidad_restante) as sin_cantidad_restante,
    CASE 
        WHEN COUNT(*) = COUNT(cantidad_restante) THEN '✓ Todas las entradas inicializadas'
        ELSE '⚠ Hay entradas sin inicializar'
    END as estado
FROM movimientos_stock 
WHERE tipo = 'ENTRADA';

-- 8. Ver sample de datos FIFO
SELECT 
    '8. Sample de entradas con FIFO' as paso,
    id,
    producto_id,
    almacen_id,
    cantidad,
    cantidad_restante,
    costo_ponderado,
    creado_en
FROM movimientos_stock 
WHERE tipo = 'ENTRADA'
ORDER BY creado_en DESC
LIMIT 5;

-- 9. Ver índices de tabla gastos
SELECT 
    '9. Índices de tabla gastos' as paso,
    indexname as nombre_indice,
    indexdef as definicion
FROM pg_indexes
WHERE tablename = 'gastos'
ORDER BY indexname;

-- 10. Resumen final
SELECT 
    '10. RESUMEN FINAL' as paso,
    'Migración completa' as estado,
    (SELECT COUNT(*) FROM permisos WHERE clave LIKE 'gastos.%' OR clave IN ('reportes.business_intelligence', 'proveedores.comparacion_mercado')) as permisos_nuevos,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'gastos') 
        THEN 'SI'
        ELSE 'NO'
    END as tabla_gastos_existe,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'movimientos_stock' 
            AND column_name IN ('costo_ponderado', 'cantidad_restante')
            HAVING COUNT(*) = 2
        )
        THEN 'SI'
        ELSE 'NO'
    END as columnas_fifo_existen;
