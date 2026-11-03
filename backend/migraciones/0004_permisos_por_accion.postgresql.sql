-- Permisos por acción: las rutas que cambian datos pasan a pedir el permiso de la acción, el mismo con el
-- que las pantallas ya mostraban u ocultaban cada botón. Para que nadie pierda nada (ni gane botones que no
-- veía), cada rol recibe sólo las acciones que la pantalla le dejaba hacer sin pedir ese permiso.
-- Los permisos tienen que existir antes de otorgarlos (las migraciones corren antes que el catálogo)
INSERT INTO permisos (clave, descripcion) SELECT 'clientes.modificar_descuento', 'Modificar descuento de cliente'
WHERE NOT EXISTS (SELECT 1 FROM permisos WHERE clave = 'clientes.modificar_descuento');
INSERT INTO permisos (clave, descripcion) SELECT 'delivery.actualizar_estado', 'Actualizar estado de entregas'
WHERE NOT EXISTS (SELECT 1 FROM permisos WHERE clave = 'delivery.actualizar_estado');
INSERT INTO permisos (clave, descripcion) SELECT 'delivery.eliminar', 'Eliminar entregas'
WHERE NOT EXISTS (SELECT 1 FROM permisos WHERE clave = 'delivery.eliminar');
INSERT INTO permisos (clave, descripcion) SELECT 'laboratorio.crear', 'Crear materias de laboratorio'
WHERE NOT EXISTS (SELECT 1 FROM permisos WHERE clave = 'laboratorio.crear');
INSERT INTO permisos (clave, descripcion) SELECT 'productos.modificar_precio', 'Modificar precios de productos'
WHERE NOT EXISTS (SELECT 1 FROM permisos WHERE clave = 'productos.modificar_precio');
INSERT INTO permisos (clave, descripcion) SELECT 'reportes.exportar', 'Exportar reportes'
WHERE NOT EXISTS (SELECT 1 FROM permisos WHERE clave = 'reportes.exportar');
INSERT INTO permisos (clave, descripcion) SELECT 'stock.ajustar', 'Ajustar stock'
WHERE NOT EXISTS (SELECT 1 FROM permisos WHERE clave = 'stock.ajustar');
INSERT INTO permisos (clave, descripcion) SELECT 'stock.configurar_alertas', 'Configurar alertas de stock'
WHERE NOT EXISTS (SELECT 1 FROM permisos WHERE clave = 'stock.configurar_alertas');
-- laboratorio.crear: el botón Nueva materia no pedía permiso
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT DISTINCT rp.rol_id, pn.id FROM rol_permisos rp
JOIN permisos pv ON pv.id = rp.permiso_id AND pv.clave IN ('laboratorio.ver')
JOIN permisos pn ON pn.clave = 'laboratorio.crear'
WHERE NOT EXISTS (SELECT 1 FROM rol_permisos x WHERE x.rol_id = rp.rol_id AND x.permiso_id = pn.id);
-- stock.configurar_alertas: la alerta mínima se editaba en la tabla de Stock
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT DISTINCT rp.rol_id, pn.id FROM rol_permisos rp
JOIN permisos pv ON pv.id = rp.permiso_id AND pv.clave IN ('stock.ver')
JOIN permisos pn ON pn.clave = 'stock.configurar_alertas'
WHERE NOT EXISTS (SELECT 1 FROM rol_permisos x WHERE x.rol_id = rp.rol_id AND x.permiso_id = pn.id);
-- stock.ajustar: el botón Almacén no pedía permiso
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT DISTINCT rp.rol_id, pn.id FROM rol_permisos rp
JOIN permisos pv ON pv.id = rp.permiso_id AND pv.clave IN ('stock.ver')
JOIN permisos pn ON pn.clave = 'stock.ajustar'
WHERE NOT EXISTS (SELECT 1 FROM rol_permisos x WHERE x.rol_id = rp.rol_id AND x.permiso_id = pn.id);
-- clientes.modificar_descuento: el descuento estaba en el formulario del cliente
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT DISTINCT rp.rol_id, pn.id FROM rol_permisos rp
JOIN permisos pv ON pv.id = rp.permiso_id AND pv.clave IN ('clientes.crear', 'clientes.editar')
JOIN permisos pn ON pn.clave = 'clientes.modificar_descuento'
WHERE NOT EXISTS (SELECT 1 FROM rol_permisos x WHERE x.rol_id = rp.rol_id AND x.permiso_id = pn.id);
-- productos.modificar_precio: los precios estaban en el formulario de edición
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT DISTINCT rp.rol_id, pn.id FROM rol_permisos rp
JOIN permisos pv ON pv.id = rp.permiso_id AND pv.clave IN ('productos.editar')
JOIN permisos pn ON pn.clave = 'productos.modificar_precio'
WHERE NOT EXISTS (SELECT 1 FROM rol_permisos x WHERE x.rol_id = rp.rol_id AND x.permiso_id = pn.id);
-- delivery.actualizar_estado: asignar y marcar entregado no pedían permiso
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT DISTINCT rp.rol_id, pn.id FROM rol_permisos rp
JOIN permisos pv ON pv.id = rp.permiso_id AND pv.clave IN ('delivery.ver')
JOIN permisos pn ON pn.clave = 'delivery.actualizar_estado'
WHERE NOT EXISTS (SELECT 1 FROM rol_permisos x WHERE x.rol_id = rp.rol_id AND x.permiso_id = pn.id);
-- reportes.exportar: los botones Excel no pedían permiso
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT DISTINCT rp.rol_id, pn.id FROM rol_permisos rp
JOIN permisos pv ON pv.id = rp.permiso_id AND pv.clave IN ('reportes.ver', 'ventas.ver_historial')
JOIN permisos pn ON pn.clave = 'reportes.exportar'
WHERE NOT EXISTS (SELECT 1 FROM rol_permisos x WHERE x.rol_id = rp.rol_id AND x.permiso_id = pn.id);
