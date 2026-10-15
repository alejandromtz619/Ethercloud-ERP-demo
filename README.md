# Ethercloud ERP

Sistema ERP full-stack para operaciones comerciales en Paraguay (moneda PYG, IVA 10%).  
Desarrollado por **Ether Soluciones Tecnológicas** — gestión de ventas, inventario, entregas, laboratorio y empleados.

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
- `JWT_SECRET` es **obligatorio** con PostgreSQL: el backend no arranca si falta o si usa un valor por defecto público. Generarlo con `openssl rand -hex 32`.
- `PERMITIR_ENDPOINTS_DESARROLLO=true` habilita `POST /api/seed` y `POST /api/reset-database` (sólo desarrollo; en producción responden 404).  
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

`admin@ether.com` / `admin123` (empresa_id: 1)

En una instancia **nueva**, el primer administrador se crea dentro del contenedor del backend con `python seed_data.py`. No borra datos, pero si no encuentra la empresa y el usuario por defecto los crea: no usarlo en instancias en uso. **Cambiar la contraseña después del primer ingreso.**
