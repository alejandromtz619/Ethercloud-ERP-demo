# Luz Brill ERP - PRD (Product Requirements Document)

## Información General
- **Nombre**: Luz Brill ERP
- **Versión**: 1.3.0
- **Stack**: FastAPI + SQLAlchemy (PostgreSQL/SQLite) + React
- **País**: Paraguay
- **IVA**: 10% (incluido en precios)
- **Moneda**: PYG (Guaraní Paraguayo)

## Credenciales de Acceso
- **Admin**: admin@luzbrill.com / admin123
- **Empresa**: Luz Brill S.A. (RUC: 80012345-6)

## Arquitectura Implementada

### Backend (/app/backend/)
- **server.py**: API FastAPI con todos los endpoints (>2500 líneas - NECESITA REFACTORIZACIÓN)
- **models.py**: Modelos SQLAlchemy (28+ tablas)
- **schemas.py**: Pydantic schemas para validación
- **database.py**: Conexión PostgreSQL/SQLite async

### Frontend (/app/frontend/src/)
- **pages/**: 17 páginas (Login, Home, Dashboard, Marcas, Permisos, HistorialVentas, Reportes, etc.)
- **components/**: Layout, CurrencyTicker, PrintModal
- **context/**: AppContext (auth, tema, API, permisos)

## Módulos Implementados

### 1. Login y Autenticación
- JWT con bcrypt
- Sesión persistente en localStorage
- Redirect a /home post-login

### 2. Home
- 3 botones grandes: Dashboard, Ventas, Delivery
- Acceso rápido a módulos principales

### 3. Dashboard
- Cotización USD/PYG y BRL/PYG en tiempo real (ExchangeRate-API)
- Estadísticas: Ventas Hoy, Deliverys Pendientes, Stock Bajo
- Gráfico: Ventas por Hora (Recharts)
- Panel de Alertas (vencimientos, stock bajo)

### 4. Ventas ✅ (ACTUALIZADO v1.3)
- Selección obligatoria de cliente
- **Soporte para representación de otro cliente** (hereda descuentos y crédito)
- Scanner código de barras USB
- **Búsqueda de productos por ID, nombre o código de barra**
- **Precio editable en carrito** (requiere permiso ventas.modificar_precio)
- Productos y Materias de Laboratorio
- Cálculo automático: Subtotal, Descuento %, IVA 10%, Total
- Tipos de pago: Efectivo, Tarjeta, Transferencia, Cheque, Crédito
- Validación de cheques: Solo clientes con `acepta_cheque=true`
- Opción delivery con vehículo y responsable

### 5. Historial de Ventas ✅ (NUEVO v1.2)
- Listado completo de ventas con filtros
- Filtros: fecha, cliente, vendedor, monto
- **Muestra nombres de productos (no IDs)**
- Detalle de venta con items
- Reimpresión de Boleta/Factura
- Anulación de ventas

### 6. Laboratorio
- Items únicos con código de barra
- Estado: DISPONIBLE / VENDIDO
- Solo una venta por materia
- **Nombre y descripción incluidos en Boleta/Factura**

### 7. Productos ✅ (ACTUALIZADO v1.3)
- CRUD completo con imagen
- **Columna ID visible en tabla**
- **Modal para zoom de imagen**
- Código de barra único
- Categorías y Marcas
- Stock total calculado

### 8. Stock/Inventario ✅ (ACTUALIZADO v1.3)
- Multi-almacén (Depósito, Tienda, etc.)
- Entradas y salidas automáticas
- **Función "Salida" para retirar productos** (POST /api/stock/salida)
- Traspasos entre almacenes
- Alertas de stock mínimo

### 9. Funcionarios ✅ (ACTUALIZADO v1.3)
- CRUD con cargo, salario, IPS
- Sistema de adelantos de salario
- **Muestra: Salario Base, Total Adelantos Mes, Salario Restante**
- Cálculo mensual automático

### 10. Sistema de Permisos ✅ (ACTUALIZADO v1.3)
- 51+ permisos granulares por rol
- **Permisos por defecto para ADMIN, GERENTE, VENDEDOR, DELIVERY**
- Restricción de módulos en sidebar según permisos
- Interfaz visual para gestionar permisos por rol

### 11. Proveedores
- CRUD con datos fiscales
- Sistema de deudas transaccional
- Fecha de emisión, límite de pago, estado

### 12. Clientes
- CRUD con RUC, cédula, dirección
- Descuento % por cliente
- Flag "Acepta Cheque"
- Sistema de créditos transaccional

### 13. Flota
- Vehículos: Moto, Automóvil, Camioneta
- Alertas de vencimiento

### 14. Reportes PDF ✅ (NUEVO v1.2)
- Ventas por período
- Stock actual
- Deudas de proveedores
- Créditos de clientes

### 15. Marcas
- CRUD completo
- Vinculación con productos

### 16. Sistema
- Modo Oscuro / Claro
- 6 colores personalizables
- Cotización manual de divisas
- Soporte técnico

## Correcciones Verificadas (v1.3 - Verificado)
1. ✅ Historial Ventas - Muestra nombres de productos
2. ✅ Boleta/Factura - Incluye nombre de Materia de Laboratorio
3. ✅ Ventas - Precio editable en carrito
4. ✅ Stock - Función "Salida" para retirar productos
5. ✅ Ventas - Lógica de representante con descuentos
6. ✅ Funcionarios - Muestra salario base, adelantos y restante
7. ✅ Permisos - Permisos por defecto para roles
8. ✅ Productos - Columna ID y zoom de imagen
9. ✅ Ventas - Búsqueda por ID de producto
10. ✅ Dashboard - Filtro tipo de pago aplicado a TODOS los períodos (v1.3.1)

## Próximos Pasos (P1)
- [ ] **REFACTORIZAR server.py** - Dividir en módulos (routes/ventas.py, routes/clientes.py, etc.)
- [ ] Integración SIFEN para facturación electrónica
- [ ] Automatización de ciclos de salario

## Backlog (P2)
- [ ] Backup automático de base de datos
- [ ] Notificaciones push de alertas
- [ ] Dashboard con métricas históricas
- [ ] Multi-empresa desde selector
- [ ] API móvil optimizada
- [ ] Integración con impresora fiscal

## Historial de Versiones
- **v1.0.0** - 28 Enero 2026: MVP inicial
- **v1.1.0** - 29 Enero 2026: Corrección de bugs + Marcas, Permisos, Cotización manual
- **v1.2.0** - 29 Enero 2026: Historial de Ventas, Impresión Facturas/Boletas, Reportes PDF
- **v1.3.0** - Enero 2026: Verificación y corrección de 10 funcionalidades críticas
- **v1.3.1** - Enero 2026: Fix filtro tipo_pago en todos los períodos del dashboard

## Test Reports
- `/app/test_reports/iteration_6.json` - Verificación completa de las 10 correcciones (100% passed)
