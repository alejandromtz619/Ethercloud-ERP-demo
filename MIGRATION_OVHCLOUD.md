# Guía de Migración a OVHcloud VPS con Coolify

## Arquitectura Target

```
OVHcloud VPS
├── Coolify (panel de gestión)
│   ├── PostgreSQL 16 (servicio de base de datos)
│   ├── Backend (FastAPI - Docker)
│   └── Frontend (React - Docker)
└── Volúmenes persistentes
    ├── pgdata (datos de PostgreSQL)
    └── uploads (imágenes de productos)
```

---

## Paso 1: Preparar el VPS OVHcloud

### 1.1 Requisitos mínimos
- **OS**: Ubuntu 22.04/24.04 LTS (recomendado)
- **RAM**: 4GB mínimo (2GB para DB + 1GB backend + 1GB frontend)
- **Disco**: 40GB+ SSD
- **Puertos abiertos**: 22 (SSH), 80, 443, 8000 (temporal)

### 1.2 Instalar Coolify
```bash
# Conectar por SSH al VPS
ssh root@TU_IP_OVH

# Instalar Coolify (un solo comando)
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash

# Coolify estará disponible en:
# http://TU_IP_OVH:8000
```

> **Nota**: Coolify usa el puerto 8000 por defecto para su panel. El backend de la app usará otro puerto o un dominio con proxy reverso.

### 1.3 Configurar DNS (si tienes dominio)
Apuntar en tu proveedor DNS:
```
api.tudominio.com    → A → TU_IP_OVH
erp.tudominio.com    → A → TU_IP_OVH
```

---

## Paso 2: Backup de la Base de Datos (servidor actual)

### 2.1 Desde el servidor actual (Render/otro hosting)

**Opción A: La DB está en Docker**
```bash
# En el servidor ACTUAL
chmod +x scripts/db-backup.sh
./scripts/db-backup.sh docker nombre-del-contenedor-db
```

**Opción B: La DB está en un servicio externo (Render PostgreSQL, etc.)**
```bash
# Obtener la connection string de Render/hosting actual
# Formato: postgresql://user:password@host:port/dbname

# Exportar credenciales
export POSTGRES_USER=usuario_render
export POSTGRES_PASSWORD=password_render
export POSTGRES_HOST=host_render.com
export POSTGRES_PORT=5432
export POSTGRES_DB=luzbrill_erp

# Ejecutar backup
./scripts/db-backup.sh
```

**Opción C: pg_dump directo con la URL de Render**
```bash
# Si tienes la URL externa de la DB de Render:
pg_dump "postgresql://user:password@host:5432/dbname" \
  --no-owner --no-privileges --if-exists --clean \
  > db-backups/luzbrill_erp_backup.sql
```

### 2.2 Transferir backup al VPS OVHcloud
```bash
# Desde tu máquina local o servidor actual
scp db-backups/luzbrill_erp_*.sql root@TU_IP_OVH:/root/db-backups/
```

---

## Paso 3: Configurar servicios en Coolify

### 3.1 Opción A: Despliegue con Coolify (recomendado)

Accede al panel de Coolify: `http://TU_IP_OVH:8000`

#### 3.1.1 Crear la Base de Datos PostgreSQL
1. **New Resource** → **Database** → **PostgreSQL**
2. Configurar:
   - **Name**: `luzbrill-db`
   - **Version**: `16-alpine`
   - **Database Name**: `luzbrill_erp`
   - **Username**: `luzbrill`
   - **Password**: (generar password fuerte, ANOTARLO)
   - **Public Port**: `5432` (temporalmente, para importar datos)
3. **Deploy**

#### 3.1.2 Importar los datos
```bash
# Desde el VPS, conectar a la DB de Coolify
# La URL interna de la DB en Coolify aparece en el panel

# Opción 1: Con psql directo
psql "postgresql://luzbrill:TU_PASSWORD@localhost:5432/luzbrill_erp" \
  < /root/db-backups/luzbrill_erp_backup.sql

# Opción 2: Si la DB está en Docker (Coolify crea un contenedor)
# Buscar el contenedor de postgres
docker ps | grep postgres
# Restaurar
cat /root/db-backups/luzbrill_erp_backup.sql | \
  docker exec -i CONTAINER_ID psql -U luzbrill -d luzbrill_erp

# Verificar
docker exec -it CONTAINER_ID psql -U luzbrill -d luzbrill_erp -c '\dt'
docker exec -it CONTAINER_ID psql -U luzbrill -d luzbrill_erp \
  -c 'SELECT count(*) FROM usuario;'
```

> **Después de importar**: Desactivar el Public Port de la DB en Coolify por seguridad.

#### 3.1.3 Crear el Backend
1. **New Resource** → **Application**
2. **Source**: GitHub repository (conectar el repo) o Docker Image
3. **Build Pack**: Dockerfile
4. **Dockerfile Path**: `backend/dockerfile`
5. **Base Directory**: `backend`
6. **Port Expuesto**: `8000`
7. **Domain**: `api.tudominio.com` (o configurar después)
8. **Variables de entorno**:
   ```
   DATABASE_URL=postgresql://luzbrill:TU_PASSWORD@luzbrill-db:5432/luzbrill_erp
   JWT_SECRET=tu_secreto_jwt_generado
   CORS_ORIGINS=https://erp.tudominio.com
   PORT=8000
   ```
   > **Nota**: En `DATABASE_URL`, usar el hostname interno del servicio de DB en Coolify (aparece en el panel como "Internal URL"). Normalmente es el nombre del servicio o su UUID.

9. **Deploy**

#### 3.1.4 Crear el Frontend
1. **New Resource** → **Application**
2. **Build Pack**: Dockerfile
3. **Dockerfile Path**: `frontend/dockerfile`
4. **Base Directory**: `frontend`
5. **Port Expuesto**: `3000`
6. **Domain**: `erp.tudominio.com`
7. **Build Arguments** (importante, es build-time):
   ```
   REACT_APP_BACKEND_URL=https://api.tudominio.com
   ```
8. **Deploy**

### 3.2 Opción B: docker-compose directo (sin Coolify UI)

Si prefieres manejar todo por CLI en el VPS:

```bash
# En el VPS
cd /opt/luzbrill-erp   # o donde clones el repo

# Clonar repo
git clone https://github.com/tu-usuario/tu-repo.git .

# Configurar variables
cp .env.example .env
nano .env
# Editar: DB_PASSWORD, JWT_SECRET, CORS_ORIGINS, REACT_APP_BACKEND_URL

# Levantar todo
docker compose up -d --build

# Verificar
docker compose ps
docker compose logs -f backend

# Importar datos
./scripts/db-restore.sh docker luzbrill-db db-backups/luzbrill_erp_backup.sql
```

---

## Paso 4: Configuración SSL/HTTPS

### Con Coolify (automático)
Coolify configura SSL automáticamente con Let's Encrypt cuando asignas un dominio a un servicio. Solo necesitas:
1. Tener el dominio apuntando al VPS (DNS A record)
2. Asignar el dominio en la configuración del servicio en Coolify
3. Coolify genera y renueva certificados automáticamente

### Sin Coolify (manual con Caddy/Nginx)
Si usas docker-compose directo, agrega un reverse proxy. Ejemplo con Caddy:

```bash
# Agregar al docker-compose.yml o correr por separado
# Caddy maneja SSL automáticamente
docker run -d --name caddy \
  -p 80:80 -p 443:443 \
  -v caddy_data:/data \
  -v $PWD/Caddyfile:/etc/caddy/Caddyfile \
  --network luzbrill-network \
  caddy:2-alpine
```

```
# Caddyfile
api.tudominio.com {
    reverse_proxy backend:8000
}

erp.tudominio.com {
    reverse_proxy frontend:3000
}
```

---

## Paso 5: Verificación Post-Migración

### 5.1 Checklist
```bash
# 1. Backend responde
curl https://api.tudominio.com/api/health

# 2. Login funciona
curl -X POST https://api.tudominio.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@luzbrill.com","password":"admin123"}'

# 3. Frontend carga
curl -s https://erp.tudominio.com | head -5

# 4. Datos migrados correctamente
# Desde el panel de Coolify o Docker:
docker exec -it CONTAINER_DB psql -U luzbrill -d luzbrill_erp \
  -c 'SELECT count(*) as usuarios FROM usuario;
      SELECT count(*) as productos FROM producto;
      SELECT count(*) as ventas FROM venta;
      SELECT count(*) as clientes FROM cliente;'
```

### 5.2 Verificar funcionalidades clave
- [ ] Login con admin@luzbrill.com / admin123
- [ ] Dashboard carga con datos
- [ ] Crear una venta de prueba
- [ ] Verificar stock se descuenta
- [ ] Delivery funciona
- [ ] Cotizaciones de moneda cargan
- [ ] Imágenes de productos cargan (uploads)

---

## Paso 6: Apagar servidor anterior

Una vez verificado que todo funciona en OVHcloud:

1. **Mantener el servidor antiguo 48-72 horas** como backup
2. **Hacer un backup final** de la DB antigua
3. **Actualizar DNS** si aún apuntan al servidor viejo
4. **Dar de baja** el servicio en Render/hosting anterior

---

## Variables de entorno - Resumen

### Backend
| Variable       | Ejemplo                                                        | Descripción                        |
| -------------- | -------------------------------------------------------------- | ---------------------------------- |
| `DATABASE_URL` | `postgresql://luzbrill:pass@luzbrill-db:5432/luzbrill_erp`     | URL de conexión a PostgreSQL       |
| `JWT_SECRET`   | `a1b2c3d4e5...` (output de `openssl rand -hex 32`)            | Secreto para tokens JWT            |
| `CORS_ORIGINS` | `https://erp.tudominio.com`                                    | Frontend(s) permitidos (CSV)       |
| `PORT`         | `8000`                                                         | Puerto del servidor                |

### Frontend (Build Arguments)
| Variable                  | Ejemplo                            | Descripción             |
| ------------------------- | ---------------------------------- | ----------------------- |
| `REACT_APP_BACKEND_URL`   | `https://api.tudominio.com`        | URL del backend API     |

### PostgreSQL
| Variable            | Ejemplo           | Descripción               |
| ------------------- | ----------------- | ------------------------- |
| `POSTGRES_DB`       | `luzbrill_erp`    | Nombre de la base de datos|
| `POSTGRES_USER`     | `luzbrill`        | Usuario de la DB          |
| `POSTGRES_PASSWORD` | (password seguro) | Password de la DB         |

---

## Troubleshooting

### Error: Backend no conecta con la DB
```bash
# Verificar que la DB está corriendo
docker ps | grep postgres

# Verificar la URL interna en Coolify
# En Coolify panel → Database → Internal URL
# Usar esa URL en DATABASE_URL del backend

# Probar conexión desde el backend
docker exec -it luzbrill-backend python -c "
import asyncio
from database import engine
async def test():
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT 1'))
        print('DB OK:', result.scalar())
asyncio.run(test())
"
```

### Error: CORS bloqueado
```bash
# Verificar que CORS_ORIGINS incluye la URL exacta del frontend
# SIN slash final, con protocolo
# ✅ https://erp.tudominio.com
# ❌ https://erp.tudominio.com/
# ❌ erp.tudominio.com

# Ver logs del backend
docker logs luzbrill-backend | grep CORS
```

### Error: Frontend muestra "Network Error"
```bash
# El REACT_APP_BACKEND_URL se embebe en build time
# Si cambias la URL del backend, necesitas REBUILD del frontend
# En Coolify: cambiar Build Argument y re-deploy
```

### Volúmenes / uploads de productos
```bash
# Si tenías imágenes de productos subidas, transferirlas:
# Desde servidor antiguo:
tar czf uploads_backup.tar.gz backend/uploads/
scp uploads_backup.tar.gz root@TU_IP_OVH:/tmp/

# En el VPS nuevo, copiar al volumen del contenedor:
docker cp /tmp/uploads_backup.tar.gz luzbrill-backend:/app/
docker exec luzbrill-backend tar xzf /app/uploads_backup.tar.gz -C /app/
```
