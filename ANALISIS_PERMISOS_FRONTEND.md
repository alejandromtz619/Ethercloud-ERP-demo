# Análisis de Permisos en Frontend ❌🔒

## Fecha: 2026-02-10

## PROBLEMA IDENTIFICADO
Los módulos se ocultan correctamente según permisos, pero **los botones de editar/eliminar dentro de las páginas NO validan permisos**, permitiendo que usuarios sin permisos ejecuten acciones críticas.

---

## PÁGINAS CON PROBLEMAS DE SEGURIDAD

### ❌ 1. **Productos.js** (CRÍTICO)
**Líneas 368-372**: Botones de Editar y Eliminar sin validación

```javascript
<Button variant="ghost" size="icon" onClick={() => handleEdit(producto)}>
  <Edit className="h-4 w-4" />
</Button>
<Button variant="ghost" size="icon" onClick={() => handleDelete(producto.id)}>
  <Trash2 className="h-4 w-4 text-destructive" />
</Button>
```

**Permisos faltantes:**
- `productos.editar` → Debe validarse antes de mostrar botón Editar
- `productos.eliminar` → Debe validarse antes de mostrar botón Eliminar

**Impacto:** Vendedores y Gerentes pueden eliminar productos sin autorización

---

### ❌ 2. **Clientes.js** (ALTO)
**Líneas 404-408**: Botón de Editar sin validación

```javascript
<Button variant="ghost" size="icon" onClick={() => handleEdit(cliente)}>
  <Edit className="h-4 w-4" />
</Button>
<Button variant="ghost" size="icon" onClick={() => handleDelete(cliente.id)}>
  <Trash2 className="h-4 w-4 text-destructive" />
</Button>
```

**Permisos faltantes:**
- `clientes.editar` → Debe validarse antes de mostrar botón Editar

**Nota:** El botón "Eliminar" NO debería existir (no hay permiso `clientes.eliminar` ni endpoint en backend)

**Impacto:** Vendedores pueden editar límites de crédito de clientes

---

### ❌ 3. **Funcionarios.js** (CRÍTICO)
**Líneas 420-426**: Botones sin validación

```javascript
<Button variant="ghost" size="icon" onClick={() => handleVerAdelantos(funcionario)}>
  <Wallet className="h-4 w-4" />
</Button>
<Button variant="ghost" size="icon" onClick={() => handleEdit(funcionario)}>
  <Edit className="h-4 w-4" />
</Button>
<Button variant="ghost" size="icon" onClick={() => handleDelete(funcionario.id)}>
  <Trash2 className="h-4 w-4 text-destructive" />
</Button>
```

**Permisos faltantes:**
- `funcionarios.ver_salarios` → Para ver adelantos
- `funcionarios.editar` → Para editar funcionario
- `funcionarios.adelantos` → Para registrar adelantos (dentro del diálogo)

**Nota:** El botón "Eliminar" NO debería existir (no hay permiso `funcionarios.eliminar` en seed_data.py)

**Impacto:** Vendedores pueden ver salarios y registrar adelantos

---

### ❌ 4. **Proveedores.js** (MEDIO)
**Líneas 414-420**: Botones sin validación

```javascript
<Button variant="ghost" size="icon" onClick={() => handleEdit(proveedor)}>
  <Edit className="h-4 w-4" />
</Button>
<Button variant="ghost" size="icon" onClick={() => handleDelete(proveedor.id)}>
  <Trash2 className="h-4 w-4 text-destructive" />
</Button>
```

**Permisos faltantes:**
- `proveedores.editar` → Debe validarse
- `proveedores.gestionar_deudas` → Para ver/gestionar deudas

**Nota:** El botón "Eliminar" NO debería existir (no hay permiso en seed_data.py)

**Impacto:** Vendedores pueden editar proveedores y gestionar deudas

---

### ❌ 5. **Flota.js** (ALTO)
**Líneas 272-278**: Botones sin validación

```javascript
<Button variant="ghost" size="icon" onClick={() => handleEdit(vehiculo)}>
  <Edit className="h-4 w-4" />
</Button>
<Button variant="ghost" size="icon" onClick={() => handleDelete(vehiculo.id)}>
  <Trash2 className="h-4 w-4 text-destructive" />
</Button>
```

**Permisos faltantes:**
- `flota.gestionar` → Debe validarse para crear/editar/eliminar vehículos

**Impacto:** Gerentes y Vendedores pueden modificar y eliminar vehículos de la flota

---

### ❌ 6. **Usuarios.js** (CRÍTICO)
**Líneas 324-330**: Botones sin validación

```javascript
<Button variant="ghost" size="icon" onClick={() => handleEdit(usuario)}>
  <Edit className="h-4 w-4" />
</Button>
<Button variant="ghost" size="icon" onClick={() => handleDelete(usuario.id)}>
  <Trash2 className="h-4 w-4 text-destructive" />
</Button>
```

**Permisos faltantes:**
- `usuarios.gestionar` → Ya se valida en ruta, pero falta en botones individuales

**Nota:** Esta página solo debe ser accesible por Administrador

**Impacto:** Aunque la ruta está protegida, si alguien accede puede modificar cualquier usuario

---

## ✅ PÁGINAS QUE SÍ VALIDAN PERMISOS CORRECTAMENTE

### ✅ **Ventas.js**
- Valida `ventas.modificar_precio` antes de permitir edición de precios
- Valida `ventas.aplicar_descuento` antes de mostrar descuentos

### ✅ **Delivery.js** (línea 572)
```javascript
{userPermisos.includes('delivery.eliminar') && (
  <Button onClick={handleEliminarEntrega}>
    <Trash2 className="h-4 w-4" />
    Eliminar
  </Button>
)}
```

---

## RESUMEN DE CORRECCIONES NECESARIAS

| Página | Permiso a Validar | Acción |
|--------|------------------|--------|
| **Productos.js** | `productos.editar` | Ocultar botón Editar |
| | `productos.eliminar` | Ocultar botón Eliminar |
| **Clientes.js** | `clientes.editar` | Ocultar botón Editar |
| | - | **REMOVER** botón Eliminar (no existe endpoint) |
| **Funcionarios.js** | `funcionarios.ver_salarios` | Ocultar botón Ver Adelantos |
| | `funcionarios.editar` | Ocultar botón Editar |
| | - | **REMOVER** botón Eliminar (no existe permiso) |
| | `funcionarios.adelantos` | Validar dentro del diálogo de adelantos |
| **Proveedores.js** | `proveedores.editar` | Ocultar botón Editar |
| | - | **REMOVER** botón Eliminar (no existe permiso) |
| | `proveedores.gestionar_deudas` | Ocultar botón Ver Deudas |
| **Flota.js** | `flota.gestionar` | Ocultar botones Editar/Eliminar |
| | `flota.gestionar` | Ocultar botón "Nuevo Vehículo" |
| **Usuarios.js** | `usuarios.gestionar` | Ya validado en ruta (OK) |

---

## PATRÓN DE CÓDIGO CORRECTO

```javascript
// ❌ INCORRECTO (sin validación)
<Button onClick={() => handleEdit(item)}>
  <Edit className="h-4 w-4" />
</Button>

// ✅ CORRECTO (con validación)
{userPermisos.includes('modulo.editar') && (
  <Button onClick={() => handleEdit(item)}>
    <Edit className="h-4 w-4" />
  </Button>
)}
```

---

## PRÓXIMOS PASOS

1. **Ejecutar SQLs de verificación** (VERIFICACION_PERMISOS.sql) para confirmar permisos actuales
2. **Aplicar correcciones en frontend** (agregar validaciones condicionales)
3. **Limpiar permisos incorrectos** en roles Gerente y Vendedor
4. **Testing final** con usuarios de cada rol
