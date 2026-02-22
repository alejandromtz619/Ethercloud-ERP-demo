# Luz Brill ERP

Sistema ERP full-stack para operaciones comerciales en Paraguay (moneda PYG, IVA 10%).  
Desarrollado para **Luz Brill S.A.** — gestión de ventas, inventario, entregas, laboratorio y empleados.

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | FastAPI + SQLAlchemy (async) |
| Base de datos | PostgreSQL (prod) / SQLite (dev) |
| Frontend | React 19 + Tailwind CSS + shadcn/ui |
| Auth | JWT (bcrypt, 24h expiration) |
| Deploy | Docker / Coolify |

## Estructura del Proyecto

```
backend/          # API FastAPI (server.py, models.py, schemas.py)
frontend/         # React SPA (pages/, components/, context/)
memory/           # PRD y documentación de producto
```

## Desarrollo Local

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

### Variables de Entorno

**Backend:** `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `PORT`  
**Frontend:** `REACT_APP_BACKEND_URL`

## Módulos Principales

- **Ventas** — flujo cliente-primero, scanner de código de barras, crédito, cheques
- **Stock** — multi-almacén, movimientos automáticos (salida/traspaso)
- **Delivery** — workflow de 2 etapas (creación → asignación vehículo)
- **Productos** — catálogo con marcas, proveedores, stock mínimo
- **Laboratorio** — ítems de venta única (DISPONIBLE → VENDIDO)
- **Funcionarios** — salarios, adelantos mensuales
- **Clientes / Proveedores** — gestión completa con límites de crédito
- **Reportes** — ventas, stock, financieros
- **Permisos** — 51+ permisos granulares por rol

## Testing

```bash
pytest backend/tests/
```

## Deployment

El proyecto se despliega mediante **Docker** (Coolify). Cada servicio tiene su propio `dockerfile`:
- `backend/dockerfile` — FastAPI con uvicorn
- `frontend/dockerfile` — Build React + serve estático

## Credenciales de Prueba

`admin@luzbrill.com` / `admin123` (empresa_id: 1)
