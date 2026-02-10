# 🧪 GUÍA DE TESTING - VERIFICACIÓN DE PERMISOS POR ROL
**Fecha:** 2026-02-10  
**Sistema:** Luz Brill ERP

---

## 📋 CÓMO USAR ESTA GUÍA

1. Inicia sesión con cada tipo de usuario
2. Navega por los módulos
3. Verifica que los botones/acciones que aparecen coincidan con esta lista
4. Marca ✅ o ❌ según corresponda

---

## 👤 ROL: VENDEDOR (13 permisos)

### ✅ **Módulos que DEBE VER:**
- [ ] Dashboard
- [ ] Ventas
- [ ] Delivery
- [ ] Productos (solo lista, sin botón "Nuevo")
- [ ] Stock (solo lista)
- [ ] Clientes (solo lista, sin botón "Nuevo")
- [ ] Flota (solo lista)

### ❌ **Módulos que NO DEBE VER:**
- [ ] Funcionarios
- [ ] Proveedores
- [ ] Usuarios
- [ ] Sistema
- [ ] Permisos
- [ ] Reportes
- [ ] Facturas
- [ ] Laboratorio
- [ ] Marcas

---

### 🔍 **PÁGINA: Ventas**
**DEBE poder:**
- [ ] ✅ Ver botón "Nueva Venta"
- [ ] ✅ Crear ventas
- [ ] ✅ Ver lista de ventas
- [ ] ✅ Imprimir boletas
- [ ] ✅ Aplicar descuentos (si el cliente lo permite)

**NO debe poder:**
- [ ] ❌ Modificar precios unitarios (input deshabilitado)
- [ ] ❌ Anular ventas
- [ ] ❌ Imprimir facturas
- [ ] ❌ Ver botón "Ver Historial"

---

### 🔍 **PÁGINA: Productos**
**DEBE ver:**
- [ ] ✅ Lista de productos
- [ ] ✅ Buscador
- [ ] ✅ Ver precios

**NO debe ver:**
- [ ] ❌ Botón "Nuevo Producto"
- [ ] ❌ Botón "Editar" (ícono lápiz) en cada fila
- [ ] ❌ Botón "Eliminar" (ícono basura) en cada fila

---

### 🔍 **PÁGINA: Clientes**
**DEBE ver:**
- [ ] ✅ Lista de clientes
- [ ] ✅ Buscador

**NO debe ver:**
- [ ] ❌ Botón "Nuevo Cliente"
- [ ] ❌ Botón "Editar" (ícono lápiz)
- [ ] ❌ Botón "Ver Créditos" (ícono tarjeta)

---

### 🔍 **PÁGINA: Delivery**
**DEBE poder:**
- [ ] ✅ Ver lista de entregas
- [ ] ✅ Crear entregas
- [ ] ✅ Actualizar estado de entregas
- [ ] ✅ Eliminar entregas

---

### 🔍 **PÁGINA: Stock**
**DEBE ver:**
- [ ] ✅ Lista de stock por almacén
- [ ] ✅ Ver cantidades

**NO debe ver:**
- [ ] ❌ Botón "Entrada de Stock"
- [ ] ❌ Botón "Salida de Stock"
- [ ] ❌ Botón "Traspaso"
- [ ] ❌ Botón "Ajustar Stock"

---

### 🔍 **PÁGINA: Flota**
**DEBE ver:**
- [ ] ✅ Lista de vehículos

**NO debe ver:**
- [ ] ❌ Botón "Nuevo Vehículo"
- [ ] ❌ Botón "Editar" en cada vehículo
- [ ] ❌ Botón "Eliminar" en cada vehículo

---

## 👔 ROL: GERENTE (41 permisos)

### ✅ **Módulos que DEBE VER:**
- [ ] Dashboard
- [ ] Ventas
- [ ] Delivery
- [ ] Productos
- [ ] Stock
- [ ] Clientes
- [ ] Proveedores
- [ ] Funcionarios (solo lectura)
- [ ] Flota (solo lectura)
- [ ] Laboratorio
- [ ] Reportes
- [ ] Facturas
- [ ] Historial de Ventas

### ❌ **Módulos que NO DEBE VER:**
- [ ] Usuarios
- [ ] Permisos
- [ ] Sistema
- [ ] Marcas

---

### 🔍 **PÁGINA: Ventas**
**DEBE poder:**
- [ ] ✅ Ver botón "Nueva Venta"
- [ ] ✅ Crear ventas
- [ ] ✅ Ver lista de ventas
- [ ] ✅ Modificar precios unitarios
- [ ] ✅ Aplicar descuentos
- [ ] ✅ Imprimir boletas
- [ ] ✅ Imprimir facturas
- [ ] ✅ Ver historial de ventas

**NO debe poder:**
- [ ] ❌ Anular ventas (no hay botón "Anular")

---

### 🔍 **PÁGINA: Productos**
**DEBE ver:**
- [ ] ✅ Botón "Nuevo Producto"
- [ ] ✅ Botón "Editar" en cada producto
- [ ] ✅ Poder modificar precios

**NO debe ver:**
- [ ] ❌ Botón "Eliminar" en cada producto

---

### 🔍 **PÁGINA: Clientes**
**DEBE ver:**
- [ ] ✅ Botón "Nuevo Cliente"
- [ ] ✅ Botón "Editar"
- [ ] ✅ Botón "Ver Créditos"
- [ ] ✅ Poder registrar pagos de créditos

**NO debe ver:**
- [ ] ❌ Botón "Eliminar"

---

### 🔍 **PÁGINA: Proveedores**
**DEBE ver:**
- [ ] ✅ Botón "Nuevo Proveedor"
- [ ] ✅ Botón "Editar"
- [ ] ✅ Botón "Ver Deudas"
- [ ] ✅ Poder gestionar deudas

**NO debe ver:**
- [ ] ❌ Botón "Eliminar"

---

### 🔍 **PÁGINA: Stock**
**DEBE poder:**
- [ ] ✅ Ver stock
- [ ] ✅ Registrar entradas
- [ ] ✅ Registrar salidas
- [ ] ✅ Hacer traspasos
- [ ] ✅ Ajustar stock

---

### 🔍 **PÁGINA: Funcionarios**
**DEBE ver:**
- [ ] ✅ Lista de funcionarios
- [ ] ✅ Botón "Editar" en cada funcionario
- [ ] ✅ Botón "Ver Adelantos" (ícono billetera)
- [ ] ✅ Poder registrar adelantos
- [ ] ✅ Poder marcar salarios como pagados

**NO debe ver:**
- [ ] ❌ Botón "Nuevo Funcionario"

---

### 🔍 **PÁGINA: Flota**
**DEBE ver:**
- [ ] ✅ Lista de vehículos
- [ ] ✅ Ver información de vencimientos

**NO debe ver:**
- [ ] ❌ Botón "Nuevo Vehículo"
- [ ] ❌ Botón "Editar"
- [ ] ❌ Botón "Eliminar"

---

### 🔍 **PÁGINA: Delivery**
**DEBE poder:**
- [ ] ✅ Ver entregas
- [ ] ✅ Crear entregas
- [ ] ✅ Actualizar estado
- [ ] ✅ Eliminar entregas

---

### 🔍 **PÁGINA: Laboratorio**
**DEBE poder:**
- [ ] ✅ Crear materias de laboratorio
- [ ] ✅ Ver materias

---

### 🔍 **PÁGINA: Reportes**
**DEBE poder:**
- [ ] ✅ Ver reportes
- [ ] ✅ Exportar reportes

---

### 🔍 **PÁGINA: Facturas**
**DEBE poder:**
- [ ] ✅ Ver facturas

---

## 🔑 ROL: ADMINISTRADOR (48 permisos)

### ✅ **Todos los módulos visibles**
### ✅ **Todos los botones visibles**
### ✅ **Todas las acciones permitidas**

**Verificaciones clave:**
- [ ] ✅ Ve módulo "Usuarios"
- [ ] ✅ Ve módulo "Permisos"
- [ ] ✅ Ve módulo "Sistema"
- [ ] ✅ Puede eliminar productos
- [ ] ✅ Puede anular ventas
- [ ] ✅ Puede crear funcionarios
- [ ] ✅ Puede gestionar flota (crear/editar/eliminar vehículos)
- [ ] ✅ Puede gestionar usuarios (crear/editar/eliminar)

---

## 🚨 ROL: DELIVERY (3 permisos)

### ✅ **Módulos que DEBE VER:**
- [ ] Delivery

### ❌ **Módulos que NO DEBE VER:**
- [ ] Todos los demás

### 🔍 **PÁGINA: Delivery**
**DEBE poder:**
- [ ] ✅ Ver entregas asignadas
- [ ] ✅ Crear entregas
- [ ] ✅ Actualizar estado (EN_CAMINO, ENTREGADO)

**NO debe poder:**
- [ ] ❌ Ver otros módulos
- [ ] ❌ Acceder a configuración

---

## 📝 REGISTRO DE TESTING

### Vendedor
**Usuario de prueba:** _____________  
**Fecha:** _____________  
**Resultado:** [ ] ✅ APROBADO  [ ] ❌ FALLÓ  
**Notas:**
```
_____________________________________________________
_____________________________________________________
```

### Gerente
**Usuario de prueba:** _____________  
**Fecha:** _____________  
**Resultado:** [ ] ✅ APROBADO  [ ] ❌ FALLÓ  
**Notas:**
```
_____________________________________________________
_____________________________________________________
```

### Administrador
**Usuario de prueba:** _____________  
**Fecha:** _____________  
**Resultado:** [ ] ✅ APROBADO  [ ] ❌ FALLÓ  
**Notas:**
```
_____________________________________________________
_____________________________________________________
```

---

## 🐛 REPORTE DE PROBLEMAS

Si encuentras algún botón o acción que no coincide con esta guía:

1. Anota el ROL del usuario
2. Anota la PÁGINA donde ocurre
3. Anota el BOTÓN o ACCIÓN que aparece/desaparece incorrectamente
4. Toma screenshot si es posible

**Formato de reporte:**
```
ROL: [Vendedor/Gerente/Admin/Delivery]
PÁGINA: [Nombre de la página]
PROBLEMA: [Descripción del problema]
ESPERADO: [Qué debería pasar]
ACTUAL: [Qué está pasando]
```

---

## ✅ CHECKLIST FINAL

- [ ] Vendedor testeado y aprobado
- [ ] Gerente testeado y aprobado
- [ ] Administrador testeado y aprobado
- [ ] Delivery testeado y aprobado
- [ ] Sin problemas encontrados
- [ ] Listo para producción
