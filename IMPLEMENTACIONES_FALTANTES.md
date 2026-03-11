# Implementaciones Faltantes en LuzBrill ERP

**Fecha de Análisis:** Marzo 11, 2026  
**Repositorio de Referencia:** [Ethercloud-ERP-demo](https://github.com/alejandromtz619/Ethercloud-ERP-demo)

---

## 📊 RESUMEN EJECUTIVO

Este documento detalla las diferencias identificadas entre el repositorio principal **Ethercloud-ERP-demo** y el repositorio **LuzBrill_ERP**. Las implementaciones faltantes se clasifican en tres categorías: Backend, Frontend y Base de Datos.

---

## 🔴 BACKEND - IMPLEMENTACIONES FALTANTES

### 1. MODELOS (models.py)

#### 1.1 Enum TipoMovimientoStock - Falta valor `VENTA`
**Actual en LuzBrill:**
```python
class TipoMovimientoStock(str, enum.Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    AJUSTE = "AJUSTE"
    TRASPASO = "TRASPASO"
```

**Debe ser:**
```python
class TipoMovimientoStock(str, enum.Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    AJUSTE = "AJUSTE"
    TRASPASO = "TRASPASO"
    VENTA = "VENTA"  # ← FALTA
```

#### 1.2 Modelo MovimientoStock - Faltan campos para FIFO
**Campos faltantes:**
```python
costo_ponderado = Column(Numeric(15, 2), nullable=True)  # CPP (Costo Promedio Ponderado)
cantidad_restante = Column(Integer, nullable=True)       # Para tracking FIFO
```

**Descripción:**
- `costo_ponderado`: Almacena el Costo Promedio Ponderado calculado al momento de la entrada
- `cantidad_restante`: Tracking de unidades restantes en un lote de entrada (método FIFO)

#### 1.3 Modelo Gasto - FALTA COMPLETAMENTE
**Modelo completo a agregar:**
```python
class Gasto(Base):
    """Gastos operativos de la empresa (agua, combustible, imprevistos, etc.)"""
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    monto = Column(Numeric(15, 2), nullable=False)
    responsable_nombre = Column(String(255), nullable=False)
    fecha = Column(Date, nullable=False)
    motivo = Column(String(500), nullable=False)
    creado_en = Column(DateTime(timezone=True), default=now_paraguay)

    empresa = relationship("Empresa", backref="gastos")
```

---

### 2. SCHEMAS (schemas.py)

#### 2.1 Schemas de Gasto - FALTAN COMPLETAMENTE
**Schemas a agregar:**
```python
class GastoBase(BaseModel):
    monto: Decimal
    responsable_nombre: str
    fecha: date
    motivo: str

class GastoCreate(GastoBase):
    empresa_id: int

class GastoUpdate(GastoBase):
    pass

class GastoResponse(GastoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    creado_en: Optional[datetime] = None
```

#### 2.2 MovimientoStockCreate - Faltan campos
**Campos a agregar en MovimientoStockCreate:**
```python
class MovimientoStockCreate(MovimientoStockBase):
    proveedor_id: Optional[int] = None
    costo_unitario: Optional[Decimal] = None
    costo_ponderado: Optional[Decimal] = None  # ← FALTA
    precio_venta: Optional[Decimal] = None
    condicion_pago: Optional[str] = None
    fecha_limite_pago: Optional[date] = None
    notas: Optional[str] = None
```

#### 2.3 EntradaStockHistorialResponse - Faltan campos
**Campos a agregar:**
```python
class EntradaStockHistorialResponse(BaseModel):
    # ... campos existentes ...
    costo_ponderado: Optional[Decimal] = None      # ← FALTA
    total_compra: Optional[Decimal] = None         # ← FALTA
    cantidad_restante: Optional[int] = None        # ← FALTA
    estado: Optional[str] = None                   # ← FALTA ("Activo" | "Agotado")
```

---

### 3. ENDPOINTS (server.py)

#### 3.1 Endpoints de Gastos - FALTAN COMPLETAMENTE
**Endpoints a implementar:**

```python
# POST /api/gastos - Crear gasto
@api_router.post("/gastos", response_model=GastoResponse)
async def crear_gasto(data: GastoCreate, db: AsyncSession = Depends(get_db))

# GET /api/gastos - Listar gastos por empresa
@api_router.get("/gastos", response_model=List[GastoResponse])
async def listar_gastos(empresa_id: int, db: AsyncSession = Depends(get_db))

# PUT /api/gastos/{gasto_id} - Actualizar gasto
@api_router.put("/gastos/{gasto_id}", response_model=GastoResponse)
async def actualizar_gasto(gasto_id: int, data: GastoUpdate, db: AsyncSession = Depends(get_db))

# DELETE /api/gastos/{gasto_id} - Eliminar gasto
@api_router.delete("/gastos/{gasto_id}")
async def eliminar_gasto(gasto_id: int, db: AsyncSession = Depends(get_db))
```

#### 3.2 Endpoint de Comparación de Mercado de Proveedores - FALTA
**Endpoint a implementar:**

```python
# GET /api/proveedores/comparacion-mercado
@api_router.get("/proveedores/comparacion-mercado")
async def comparacion_mercado(empresa_id: int, db: AsyncSession = Depends(get_db))
```

**Descripción:** Retorna tabla pivote: productos × proveedores con costo, SKU y link por celda.

#### 3.3 Lógica FIFO en Stock - FALTA IMPLEMENTAR
**Funciones auxiliares a agregar:**

```python
async def _consume_entrada_fifo(db: AsyncSession, producto_id: int, almacen_id: int, cantidad: int):
    """Consume entradas FIFO (First In, First Out) restando de cantidad_restante"""
    # Obtener entradas con cantidad_restante > 0, ordenadas por fecha (FIFO)
    # Descontar de cantidad_restante hasta agotar la cantidad solicitada

async def _recalculate_precio_costo_fifo(db: AsyncSession, producto_id: int):
    """Recalcula precio_costo del producto basado en entradas FIFO activas"""
    # Calcula el costo promedio de las entradas con cantidad_restante > 0
    # Actualiza producto.precio_costo con el resultado
```

**Modificaciones necesarias en endpoints existentes:**
- `POST /stock/entrada`: Inicializar `cantidad_restante = cantidad`
- `POST /ventas/{venta_id}/confirmar`: Llamar a `_consume_entrada_fifo()` y `_recalculate_precio_costo_fifo()`
- `POST /stock/salida`: Llamar a `_consume_entrada_fifo()` y `_recalculate_precio_costo_fifo()`

---

## 🎨 FRONTEND - IMPLEMENTACIONES FALTANTES

### 1. PÁGINAS FALTANTES

#### 1.1 Gastos.js - FALTA COMPLETAMENTE
**Ubicación:** `frontend/src/pages/Gastos.js`

**Funcionalidades requeridas:**
- CRUD completo de gastos operativos
- Filtros por fecha, responsable, monto
- Tabla con columnas: Fecha, Monto, Responsable, Motivo, Acciones
- Formulario modal para crear/editar gasto
- Suma total de gastos en el periodo seleccionado
- Permisos: `gastos.crear`, `gastos.ver`, `gastos.editar`, `gastos.eliminar`

#### 1.2 BusinessIntelligence.js - FALTA COMPLETAMENTE
**Ubicación:** `frontend/src/pages/BusinessIntelligence.js`

**Funcionalidades requeridas:**
- **6 tabs de análisis avanzado:**
  1. **Análisis de Ventas**: Gráficos por periodo, top productos, top clientes
  2. **Rentabilidad**: Márgenes de ganancia, análisis de costos
  3. **Stock**: Movimientos, alertas, rotación de inventario
  4. **Sugerencias**: Recomendaciones de reposición basadas en rotación
  5. **Exceso**: Productos con stock excesivo
  6. **Aging**: Antigüedad de inventario
- Gráficos con recharts (Bar, Line, Pie, Composed)
- Filtros de fecha personalizables
- Permisos: `reportes.business_intelligence`

### 2. COMPONENTES A ACTUALIZAR

#### 2.1 Stock.js - Actualizar para mostrar FIFO
**Cambios necesarios:**
- Agregar columna "Cant. Restante" en tabla de historial
- Agregar columna "CPP" (Costo Promedio Ponderado)
- Badge de estado "Activo"/"Agotado" para entradas FIFO
- Mostrar total_compra (costo_unitario × cantidad)

#### 2.2 Proveedores.js - Agregar comparación de mercado
**Funcionalidad a agregar:**
- Botón "Comparación de Mercado"
- Modal con tabla pivote: productos (filas) × proveedores (columnas)
- Cada celda muestra: costo, SKU, link (si disponible)
- Resaltar mejor precio por producto
- Permite editar costos inline

### 3. RUTAS Y PERMISOS

#### 3.1 App.js - Agregar rutas
```javascript
<ProtectedRoute path="/gastos" component={Gastos} />
<ProtectedRoute path="/business-intelligence" component={BusinessIntelligence} />
```

#### 3.2 AppContext.js - Agregar permisos de ruta
```javascript
const ROUTE_PERMISSIONS = {
  // ... existentes ...
  '/gastos': 'gastos.ver',
  '/business-intelligence': 'reportes.business_intelligence',
};
```

#### 3.3 Layout.js - Agregar enlaces en sidebar
```javascript
{ name: 'Gastos', href: '/gastos', icon: DollarSign, permission: 'gastos.ver' },
{ name: 'Business Intelligence', href: '/business-intelligence', icon: TrendingUp, permission: 'reportes.business_intelligence' },
```

---

## 🗄️ BASE DE DATOS - SCRIPTS SQL DE MIGRACIÓN

### 1. Agregar enum VENTA a TipoMovimientoStock
```sql
-- PostgreSQL
ALTER TYPE tipomovimientostock ADD VALUE IF NOT EXISTS 'VENTA' AFTER 'TRASPASO';

-- SQLite (requires drop and recreate)
-- Este cambio requiere migración manual en SQLite
```

### 2. Agregar campos a MovimientoStock
```sql
ALTER TABLE movimientos_stock 
ADD COLUMN costo_ponderado NUMERIC(15, 2),
ADD COLUMN cantidad_restante INTEGER;

-- Inicializar cantidad_restante para entradas existentes
UPDATE movimientos_stock 
SET cantidad_restante = cantidad 
WHERE tipo = 'ENTRADA' AND cantidad_restante IS NULL;
```

### 3. Crear tabla Gastos
```sql
CREATE TABLE gastos (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    monto NUMERIC(15, 2) NOT NULL,
    responsable_nombre VARCHAR(255) NOT NULL,
    fecha DATE NOT NULL,
    motivo VARCHAR(500) NOT NULL,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_gastos_empresa ON gastos(empresa_id);
CREATE INDEX idx_gastos_fecha ON gastos(fecha);
```

### 4. Agregar nuevos permisos
```sql
INSERT INTO permisos (clave, descripcion) VALUES
    ('gastos.ver', 'Ver gastos operativos'),
    ('gastos.crear', 'Crear gastos operativos'),
    ('gastos.editar', 'Editar gastos operativos'),
    ('gastos.eliminar', 'Eliminar gastos operativos'),
    ('reportes.business_intelligence', 'Acceso a Business Intelligence');

-- Asignar permisos al rol de Administrador (ajustar rol_id según tu BD)
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT 1, id FROM permisos WHERE clave IN (
    'gastos.ver', 'gastos.crear', 'gastos.editar', 'gastos.eliminar',
    'reportes.business_intelligence'
);
```

---

## 📝 NOTAS ADICIONALES

### Prioridad de Implementación
1. **Alta:** Campos FIFO (costo_ponderado, cantidad_restante) - Crítico para costeo preciso
2. **Alta:** Modelo y endpoints de Gastos - Feature completa nuevaalta:** Página Gastos en frontend
4. **Media:** Comparación de mercado de proveedores
5. **Media:** Business Intelligence dashboard
6. **Baja:** Mejoras visuales en Stock para FIFO

### Compatibilidad
- Todos los cambios son **retrocompatibles**
- Los campos nuevos son opcionales (nullable)
- No rompe funcionalidad existente

### Testing Requerido
- ✅ Tests de FIFO: consumo correcto de lotes por fecha
- ✅ Tests de Gastos: CRUD completo
- ✅ Tests de permisos: nuevos permisos correctamente validados
- ✅ Tests de UI: nuevas páginas responsive

---

**Fin del documento**
