-- ============================================
-- SQLs PARA CORREGIR PERMISOS DE ROLES
-- Luz Brill ERP - Corrección de Permisos
-- ============================================
-- IMPORTANTE: Ejecutar DESPUÉS de verificar con VERIFICACION_PERMISOS.sql
-- ============================================

-- ==========================================
-- 1. ELIMINAR PERMISOS PELIGROSOS DEL ROL GERENTE
-- ==========================================

-- Gerente NO debe gestionar usuarios ni sistema
DELETE FROM rol_permisos 
WHERE rol_id = (SELECT id FROM roles WHERE nombre = 'Gerente')
  AND permiso_id IN (
    SELECT id FROM permisos 
    WHERE clave IN (
      'usuarios.gestionar',
      'roles.gestionar',
      'sistema.configurar',
      'productos.eliminar'  -- Gerente puede editar pero no eliminar productos
    )
  );

-- ==========================================
-- 2. ELIMINAR TODOS LOS PERMISOS DEL ROL VENDEDOR
-- Vendedor tendrá solo permisos básicos de lectura y creación
-- ==========================================

DELETE FROM rol_permisos 
WHERE rol_id = (SELECT id FROM roles WHERE nombre = 'Vendedor');

-- ==========================================
-- 3. ASIGNAR PERMISOS CORRECTOS PARA VENDEDOR
-- Solo lectura y creación básica
-- ==========================================

INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT 
  (SELECT id FROM roles WHERE nombre = 'Vendedor'),
  p.id
FROM permisos p
WHERE p.clave IN (
  -- Ventas (solo crear y ver, no anular ni modificar precios)
  'ventas.crear',
  'ventas.ver',
  'ventas.imprimir_boleta',
  'ventas.imprimir_factura',
  
  -- Productos (solo ver)
  'productos.ver',
  
  -- Stock (solo ver)
  'stock.ver',
  
  -- Clientes (ver y crear)
  'clientes.ver',
  'clientes.crear',
  
  -- Delivery (solo ver)
  'delivery.ver',
  
  -- Laboratorio (ver)
  'laboratorio.ver'
)
ON CONFLICT DO NOTHING;  -- Para PostgreSQL
-- Para SQLite, usar: ON CONFLICT(rol_id, permiso_id) DO NOTHING

-- ==========================================
-- 4. VERIFICAR PERMISOS ASIGNADOS DESPUÉS DE LA CORRECCIÓN
-- ==========================================

-- Ver permisos del Gerente después de corrección
SELECT 
  p.clave AS permiso,
  p.descripcion
FROM roles r
JOIN rol_permisos rp ON r.id = rp.rol_id
JOIN permisos p ON rp.permiso_id = p.id
WHERE r.nombre = 'Gerente'
ORDER BY p.clave;

-- Ver permisos del Vendedor después de corrección
SELECT 
  p.clave AS permiso,
  p.descripcion
FROM roles r
JOIN rol_permisos rp ON r.id = rp.rol_id
JOIN permisos p ON rp.permiso_id = p.id
WHERE r.nombre = 'Vendedor'
ORDER BY p.clave;

-- ==========================================
-- 5. VERIFICAR CONTEO DE PERMISOS POR ROL
-- ==========================================
SELECT 
  r.nombre AS rol,
  COUNT(rp.permiso_id) AS total_permisos
FROM roles r
LEFT JOIN rol_permisos rp ON r.id = rp.rol_id
GROUP BY r.id, r.nombre
ORDER BY r.id;

-- Resultado esperado:
-- Administrador: ~60 permisos (todos)
-- Gerente: ~45 permisos (sin usuarios/sistema)
-- Vendedor: ~9 permisos (solo lectura y creación básica)

-- ==========================================
-- 6. SCRIPT COMPLETO PARA RECONFIGURAR GERENTE
-- (Si se quiere definir explícitamente todos los permisos)
-- ==========================================

/*
-- Limpiar permisos de Gerente
DELETE FROM rol_permisos 
WHERE rol_id = (SELECT id FROM roles WHERE nombre = 'Gerente');

-- Asignar permisos correctos para Gerente
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT 
  (SELECT id FROM roles WHERE nombre = 'Gerente'),
  p.id
FROM permisos p
WHERE p.clave IN (
  -- VENTAS (todas las operaciones)
  'ventas.crear',
  'ventas.ver',
  'ventas.anular',
  'ventas.modificar_precio',
  'ventas.aplicar_descuento',
  'ventas.imprimir_boleta',
  'ventas.imprimir_factura',
  'ventas.ver_historial',
  
  -- PRODUCTOS (todo excepto eliminar)
  'productos.ver',
  'productos.crear',
  'productos.editar',
  'productos.modificar_precio',
  
  -- STOCK (todas las operaciones)
  'stock.ver',
  'stock.entrada',
  'stock.salida',
  'stock.traspasar',
  'stock.ajustar',
  
  -- CLIENTES (todas las operaciones)
  'clientes.ver',
  'clientes.crear',
  'clientes.editar',
  'clientes.ver_creditos',
  
  -- PROVEEDORES (todas las operaciones)
  'proveedores.ver',
  'proveedores.crear',
  'proveedores.editar',
  'proveedores.gestionar_deudas',
  
  -- FUNCIONARIOS (solo ver, no gestionar)
  'funcionarios.ver',
  'funcionarios.ver_salarios',
  
  -- DELIVERY (todas las operaciones)
  'delivery.ver',
  'delivery.crear',
  'delivery.actualizar_estado',
  'delivery.eliminar',
  
  -- FLOTA (solo ver)
  'flota.ver',
  
  -- LABORATORIO (todas las operaciones)
  'laboratorio.crear',
  'laboratorio.ver',
  
  -- REPORTES (todas las operaciones)
  'reportes.ver',
  'reportes.exportar',
  
  -- FACTURAS (ver)
  'facturas.ver'
)
ON CONFLICT DO NOTHING;
*/

-- ==========================================
-- 7. ROLLBACK EN CASO DE ERROR
-- (Guardar estos scripts antes de ejecutar los DELETE)
-- ==========================================

-- Para respaldar permisos actuales antes de la corrección:
/*
CREATE TEMP TABLE backup_rol_permisos_gerente AS
SELECT * FROM rol_permisos 
WHERE rol_id = (SELECT id FROM roles WHERE nombre = 'Gerente');

CREATE TEMP TABLE backup_rol_permisos_vendedor AS
SELECT * FROM rol_permisos 
WHERE rol_id = (SELECT id FROM roles WHERE nombre = 'Vendedor');
*/

-- Para restaurar si algo sale mal:
/*
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT rol_id, permiso_id FROM backup_rol_permisos_gerente;

INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT rol_id, permiso_id FROM backup_rol_permisos_vendedor;
*/

-- ==========================================
-- 8. NOTAS IMPORTANTES
-- ==========================================

/*
PERMISOS QUE SOLO DEBE TENER ADMINISTRADOR:
- usuarios.gestionar
- roles.gestionar
- sistema.configurar
- productos.eliminar
- funcionarios.crear
- funcionarios.editar
- funcionarios.adelantos
- funcionarios.pagar_salarios
- flota.gestionar

PERMISOS QUE PUEDE TENER GERENTE:
- Todo lo relacionado a operaciones comerciales (ventas, clientes, productos, stock)
- Ver reportes y exportarlos
- Ver información de funcionarios (sin modificar)
- Ver flota (sin gestionar)

PERMISOS QUE PUEDE TENER VENDEDOR:
- Crear y ver ventas (sin anular ni modificar precios)
- Ver productos, stock, clientes
- Crear clientes nuevos
- Ver deliveries
- Ver laboratorio
*/
