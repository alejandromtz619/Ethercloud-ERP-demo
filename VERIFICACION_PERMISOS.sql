-- ============================================
-- SQLs PARA VERIFICAR PERMISOS POR ROL
-- Luz Brill ERP - Sistema de Permisos
-- ============================================

-- ==========================================
-- 1. VER TODOS LOS PERMISOS DISPONIBLES EN EL SISTEMA
-- ==========================================
SELECT 
    id,
    clave AS permiso,
    descripcion
FROM permisos
ORDER BY clave;

-- ==========================================
-- 2. VER TODOS LOS ROLES
-- ==========================================
SELECT 
    r.id,
    r.nombre,
    r.descripcion,
    e.nombre_comercial AS empresa
FROM roles r
JOIN empresas e ON r.empresa_id = e.id
ORDER BY r.id;

-- ==========================================
-- 3. VER PERMISOS POR CADA ROL (RESUMEN CONTEO)
-- ==========================================
SELECT 
    r.nombre AS rol,
    COUNT(rp.permiso_id) AS total_permisos
FROM roles r
LEFT JOIN rol_permisos rp ON r.id = rp.rol_id
GROUP BY r.id, r.nombre
ORDER BY r.id;

-- ==========================================
-- 4. VER TODOS LOS PERMISOS DE CADA ROL (DETALLADO)
-- ==========================================
SELECT 
    r.nombre AS rol,
    p.clave AS permiso,
    p.descripcion
FROM roles r
LEFT JOIN rol_permisos rp ON r.id = rp.rol_id
LEFT JOIN permisos p ON rp.permiso_id = p.id
ORDER BY r.nombre, p.clave;

-- ==========================================
-- 5. VER PERMISOS DEL ROL ADMINISTRADOR
-- ==========================================
SELECT 
    p.clave AS permiso,
    p.descripcion
FROM roles r
JOIN rol_permisos rp ON r.id = rp.rol_id
JOIN permisos p ON rp.permiso_id = p.id
WHERE r.nombre = 'Administrador'
ORDER BY p.clave;

-- ==========================================
-- 6. VER PERMISOS DEL ROL GERENTE
-- ==========================================
SELECT 
    p.clave AS permiso,
    p.descripcion
FROM roles r
JOIN rol_permisos rp ON r.id = rp.rol_id
JOIN permisos p ON rp.permiso_id = p.id
WHERE r.nombre = 'Gerente'
ORDER BY p.clave;

-- ==========================================
-- 7. VER PERMISOS DEL ROL VENDEDOR
-- ==========================================
SELECT 
    p.clave AS permiso,
    p.descripcion
FROM roles r
JOIN rol_permisos rp ON r.id = rp.rol_id
JOIN permisos p ON rp.permiso_id = p.id
WHERE r.nombre = 'Vendedor'
ORDER BY p.clave;

-- ==========================================
-- 8. COMPARAR PERMISOS ENTRE ROLES (Formato Matricial)
-- ==========================================
SELECT 
    p.clave AS permiso,
    MAX(CASE WHEN r.nombre = 'Administrador' THEN '✓' ELSE '-' END) AS Administrador,
    MAX(CASE WHEN r.nombre = 'Gerente' THEN '✓' ELSE '-' END) AS Gerente,
    MAX(CASE WHEN r.nombre = 'Vendedor' THEN '✓' ELSE '-' END) AS Vendedor
FROM permisos p
LEFT JOIN rol_permisos rp ON p.id = rp.permiso_id
LEFT JOIN roles r ON rp.rol_id = r.id
GROUP BY p.id, p.clave
ORDER BY p.clave;

-- ==========================================
-- 9. VER PERMISOS PELIGROSOS (ELIMINAR, MODIFICAR, GESTIONAR)
-- ==========================================
SELECT 
    r.nombre AS rol,
    p.clave AS permiso_peligroso,
    p.descripcion
FROM roles r
JOIN rol_permisos rp ON r.id = rp.rol_id
JOIN permisos p ON rp.permiso_id = p.id
WHERE p.clave LIKE '%eliminar%' 
   OR p.clave LIKE '%gestionar%'
   OR p.clave LIKE '%modificar%'
   OR p.clave LIKE '%anular%'
ORDER BY r.nombre, p.clave;

-- ==========================================
-- 10. PERMISOS QUE TIENE GERENTE PERO NO DEBERÍA
-- Estos son permisos que generalmente solo Admin debería tener
-- ==========================================
SELECT 
    p.clave AS permiso,
    p.descripcion
FROM roles r
JOIN rol_permisos rp ON r.id = rp.rol_id
JOIN permisos p ON rp.permiso_id = p.id
WHERE r.nombre = 'Gerente'
  AND (
      p.clave LIKE '%eliminar%' 
      OR p.clave LIKE '%gestionar%'
      OR p.clave LIKE 'usuarios.%'
      OR p.clave LIKE 'roles.%'
      OR p.clave LIKE 'sistema.%'
  )
ORDER BY p.clave;

-- ==========================================
-- 11. PERMISOS QUE TIENE VENDEDOR PERO NO DEBERÍA
-- Vendedores solo deberían crear/ver, no eliminar o modificar config
-- ==========================================
SELECT 
    p.clave AS permiso,
    p.descripcion
FROM roles r
JOIN rol_permisos rp ON r.id = rp.rol_id
JOIN permisos p ON rp.permiso_id = p.id
WHERE r.nombre = 'Vendedor'
  AND (
      p.clave LIKE '%eliminar%' 
      OR p.clave LIKE '%gestionar%'
      OR p.clave LIKE '%editar%'
      OR p.clave LIKE 'usuarios.%'
      OR p.clave LIKE 'roles.%'
      OR p.clave LIKE 'sistema.%'
      OR p.clave LIKE '%salarios%'
  )
ORDER BY p.clave;

-- ==========================================
-- 12. PERMISOS SUGERIDOS POR ROL
-- ==========================================

-- VENDEDOR: Solo debería tener permisos de lectura y creación básica
/*
PERMISOS SUGERIDOS PARA VENDEDOR:
- ventas.crear
- ventas.ver
- ventas.imprimir_boleta
- productos.ver
- stock.ver
- clientes.ver
- clientes.crear
- delivery.ver
- laboratorio.ver
*/

-- GERENTE: Puede ver todo y editar, pero no eliminar ni gestionar usuarios/sistema
/*
PERMISOS SUGERIDOS PARA GERENTE:
- ventas.* (todos)
- productos.* (todos)
- stock.* (todos)
- clientes.* (todos)
- proveedores.* (todos)
- funcionarios.ver
- funcionarios.ver_salarios
- delivery.* (todos)
- flota.ver
- laboratorio.* (todos)
- reportes.* (todos)
- facturas.ver

NO DEBE TENER:
- usuarios.gestionar
- roles.gestionar
- sistema.configurar
- funcionarios.crear/editar/adelantos/pagar_salarios
- flota.gestionar
- productos.eliminar
*/

-- ADMINISTRADOR: Tiene todos los permisos (sin restricciones)

-- ==========================================
-- 13. VER USUARIOS Y SUS ROLES
-- ==========================================
SELECT 
    u.username,
    u.nombres,
    u.apellidos,
    r.nombre AS rol
FROM usuarios u
JOIN usuario_roles ur ON u.id = ur.usuario_id
JOIN roles r ON ur.rol_id = r.id
ORDER BY r.nombre, u.username;
