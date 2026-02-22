# Luz Brill ERP - AI Coding Instructions

## Project Overview
**Full-stack ERP system** for Paraguayan business operations (PYG currency, 10% IVA). Built for Luz Brill S.A. to manage sales, inventory, delivery, laboratory items, and employee operations.

**Stack**: FastAPI + PostgreSQL/SQLite + React + shadcn/ui  
**Deployment**: Docker / Coolify  
**Auth**: JWT tokens with bcrypt, 24h expiration

## Architecture

### Backend (`/backend/`)
- **server.py** (3100+ lines): Monolithic FastAPI app with all endpoints under `/api` prefix via `APIRouter`
- **models.py**: 28+ SQLAlchemy tables (Empresa, Usuario, Producto, Venta, etc.)
- **schemas.py**: Pydantic validation schemas mirroring models
- **database.py**: Async PostgreSQL (asyncpg) or SQLite (aiosqlite) via `DATABASE_URL` env var

### Frontend (`/frontend/src/`)
- **React 19** with React Router, CRACO build, Tailwind + shadcn/ui components
- **AppContext.js**: Global state (user, auth token, permissions, theme, empresa)
- **pages/**: 17 pages (Dashboard, Ventas, Productos, etc.) - access controlled by route-level permissions
- **API_URL**: `${process.env.REACT_APP_BACKEND_URL}/api`

### Key Patterns
1. **Permission System**: 51+ granular permissions (see [models.py](../backend/models.py#L100-L200) `Rol`/`Permiso`). Frontend checks `userPermisos` array; backend verifies via `get_current_usuario()` dependency.
2. **Multi-tenant**: All entities scoped to `empresa_id`. Seed user: `admin@luzbrill.com / admin123`.
3. **Enums**: Shared between models.py and schemas.py (`EstadoVenta`, `TipoPago`, `TipoMovimientoStock`, etc.)

## Development Workflows

### Git Branching Strategy
- **`dev` branch**: Active development - all new features, fixes, and experiments happen here
- **`main` branch**: Production-ready releases only
- **Merge flow**: `dev` → `main` for releases
- **Critical**: Test thoroughly in `dev` before merging to avoid conflicts and broken deployments
- **Best practice**: Keep `dev` commits atomic and well-tested to minimize merge conflicts

### Local Development
```bash
# Backend (http://localhost:8000)
cd backend
pip install -r requirements.txt
uvicorn server:app --reload

# Frontend (http://localhost:3000)
cd frontend
yarn install
yarn start
```

### Testing
- **Backend**: `pytest backend/tests/` (5 test suites covering auth, ventas, permisos, etc.)
- **E2E Tests**: See `test_erp_features.py` - uses admin credentials against deployed API
- **Always run tests in `dev` before merging to `main`**

### Environment Variables
**Backend**: `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `PORT`  
**Frontend**: `REACT_APP_BACKEND_URL`

## Critical Features

### Sales (Ventas) - [pages/Ventas.js](../frontend/src/pages/Ventas.js)
- **Client-first workflow**: Must select client before adding items
- **Barcode scanner**: USB barcode readers trigger search in product input
- **Editable prices**: Requires `ventas.modificar_precio` permission
- **Credit validation**: Checks `cliente.limite_credito - cliente.credito_actual`
- **Cheques**: Only allowed if `cliente.acepta_cheque === true`
- **Delivery**: Checkbox only - creates `Entrega` with null vehicle/responsable, assignment happens in Delivery module
- **Laboratory items**: One-time sale (estado: DISPONIBLE → VENDIDO)

### Delivery Module - [pages/Delivery.js](../frontend/src/pages/Delivery.js)
- **Two-stage workflow**: Ventas creates delivery entry, Delivery module assigns vehicle + responsable
- **Assignment**: Updates `Entrega` with `vehiculo_id` and `responsable_usuario_id` via `/entregas/{id}/asignar`
- **Status flow**: PENDIENTE → EN_CAMINO (on assign) → ENTREGADO
- **Filters**: Date range, vehicle, responsable, status
- **Delete**: Admin-only permission `delivery.eliminar` to remove delivery orders
- **Auto-cancel**: When a sale is voided, associated delivery is auto-canceled/deleted

### Stock System - [server.py](../backend/server.py#L1500-L1800)
- **Multi-warehouse**: `StockActual` tracks quantity per `almacen_id` + `producto_id`
- **Automatic movements**: Ventas create `SALIDA`, traspasos create paired `TRASPASO` records
- **Manual "Salida"**: `POST /api/stock/salida` (e.g., breakage, theft) - see [PRD.md](../memory/PRD.md#L93)

### Permissions - [context/AppContext.js](../frontend/src/context/AppContext.js#L14-L32)
```javascript
const ROUTE_PERMISSIONS = {
  '/ventas': 'ventas.crear',
  '/usuarios': 'usuarios.gestionar',
  // ... route permissions map
};
```
**Backend enforcement**: `Depends(get_current_usuario)` extracts JWT, loads user permissions

### Currency Rates - [server.py](../backend/server.py#L300-L400)
- **ExchangeRate-API**: Fetches USD/PYG, BRL/PYG rates
- **Manual override**: `MANUAL_CURRENCY_RATES` dict allows admin-set rates
- **Dashboard ticker**: [CurrencyTicker.js](../frontend/src/components/CurrencyTicker.js)

### Funcionarios (Employees) - [pages/Funcionarios.js](../frontend/src/pages/Funcionarios.js)
- **Salary advances**: `AdelantoSalario` table, grouped by month
- **Frontend displays**: Base salary, total advances, remaining balance per month

## Design System
See [design_guidelines.json](../design_guidelines.json) for:
- **Typography**: Manrope (headings), Inter (body), JetBrains Mono (currency/IDs)
- **Colors**: Primary `#0044CC`, Accent `#FF6B00`, semantic states
- **Archetype**: "Performance Pro + Swiss Clarity" (dense data, high contrast)

## Common Tasks

### Adding a new endpoint
1. Define Pydantic schemas in `schemas.py`
2. Add SQLAlchemy model to `models.py` if needed
3. Create endpoint in `server.py` under `api_router` (e.g., `@api_router.post("/...)")`)
4. Include `Depends(get_current_usuario)` for auth

### Adding a new page
1. Create in `frontend/src/pages/YourPage.js`
2. Add route in `App.js` wrapped with `<ProtectedRoute>`
3. Add permission mapping in `AppContext.js` `ROUTE_PERMISSIONS`
4. Update sidebar in `Layout.js` with permission check

### Database migrations
- **No Alembic currently used** - schema changes via `Base.metadata.create_all()`
- For production, manually run SQL or add Alembic

## Gotchas
- **server.py size**: 3100 lines - prefer grep_search over full reads
- **Async everywhere**: All DB operations use `async def` + `await`
- **Paraguay specifics**: 10% IVA included in prices, PYG currency (no decimals)
- **Test credentials**: `admin@luzbrill.com / admin123` (empresa_id: 1)
- **CORS issues**: If deployed, update `CORS_ORIGINS` env var in backend with frontend URL (e.g., `https://luzbrill-frontend.ddelvalle.xyz`). For local dev, use `http://localhost:3000` or `*` for testing only.
  - Check logs for: `CORS allowed origins: ['https://...']`
  - If still failing, ensure no trailing slashes in URL

## References
- [PRD.md](../memory/PRD.md): Feature list, module details
- [backend/dockerfile](../backend/dockerfile): Backend Docker config
- [frontend/dockerfile](../frontend/dockerfile): Frontend Docker config
