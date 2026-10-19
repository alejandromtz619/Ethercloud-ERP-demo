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

### Variables de Entorno (infraestructura; las carga Ether al crear la instancia)

Cada cliente tiene su propia instancia. Las variables son sólo de infraestructura: lo que es del
cliente (datos de la empresa, RUC, claves de APIs, conexiones) se carga desde la web, en
**Sistema › Configuración** (`backend/configuracion.py`). Plan: `PLAN_CONFIGURACION_POR_INSTANCIA.md`.

| Variable | Para qué |
|---|---|
| `DATABASE_URL` | Base PostgreSQL de la instancia |
| `JWT_SECRET` | **Obligatorio** con PostgreSQL (el backend no arranca sin él). `openssl rand -hex 32` |
| `CLAVE_CIFRADO` | 32+ caracteres al azar, uno por instancia. Cifra las API keys que se guardan desde la pantalla. Si cambia, hay que volver a cargarlas |
| `CODIGO_ALTA` | 12+ caracteres al azar. Lo pide el alta de la instancia (ver abajo); después del alta se puede quitar |
| `MODULOS` | Módulos contratados: `fe` (facturación electrónica), `crm`… separados por coma |
| `WEB_CONCURRENCY` | Procesos de la API (2 por defecto) |
| `PERMITIR_ENDPOINTS_DESARROLLO=true` | Sólo desarrollo: habilita `POST /api/seed` y `POST /api/reset-database` (en producción, 404) |

Frontend: `REACT_APP_BACKEND_URL`.

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

## Alta de una instancia nueva

1. En Coolify, con las variables de arriba (incluido un `CODIGO_ALTA` nuevo).
2. Abrir la web: con la base vacía aparece **Configuración inicial** (`/alta`). Se cargan el código de
   alta, los datos de la empresa (RUC con su dígito verificador) y el primer administrador con su propia
   contraseña. Crea los roles base (ADMIN, GERENTE, VENDEDOR, DELIVERY) y entra.
3. En **Sistema › Configuración**: logo, documentos impresos, facturación electrónica (API key de
   SIFEN SIS) y tokens de integración.

El alta funciona una sola vez: con un usuario en la base responde 404. Los intentos con un código
equivocado se limitan igual que los del login.

## Datos de desarrollo

`python seed_data.py --desarrollo` (o `POST /api/seed` con `PERMITIR_ENDPOINTS_DESARROLLO=true`)
crea una empresa de ejemplo y el usuario `admin@ether.com` / `admin123`. **Nunca en la instancia de un
cliente**: sin `--desarrollo` el script no corre.
