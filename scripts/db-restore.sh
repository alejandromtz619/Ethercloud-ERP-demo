#!/bin/bash
# ============================================================
# Luz Brill ERP - Script de Restore de PostgreSQL
# ============================================================
# Uso en el nuevo servidor OVHcloud:
#   chmod +x scripts/db-restore.sh
#   ./scripts/db-restore.sh ruta/al/backup.sql
#   ./scripts/db-restore.sh ruta/al/backup.dump
#
# Si la DB corre en Docker:
#   ./scripts/db-restore.sh docker ruta/al/backup.sql
#   ./scripts/db-restore.sh docker ruta/al/backup.dump
# ============================================================

set -euo pipefail

# Configuración
DB_NAME="${POSTGRES_DB:-luzbrill_erp}"
DB_USER="${POSTGRES_USER:-luzbrill}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

echo "============================================"
echo " Luz Brill ERP - Restore de Base de Datos"
echo "============================================"

# Parse argumentos
MODE="direct"
BACKUP_FILE=""

if [ "${1:-}" = "docker" ]; then
    MODE="docker"
    CONTAINER="${2:-luzbrill-db}"
    BACKUP_FILE="${3:-}"
else
    BACKUP_FILE="${1:-}"
fi

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ Error: Especifica el archivo de backup"
    echo ""
    echo "Uso:"
    echo "  $0 <archivo.sql|archivo.dump>"
    echo "  $0 docker [container] <archivo.sql|archivo.dump>"
    echo ""
    echo "Ejemplos:"
    echo "  $0 db-backups/luzbrill_erp_20260222.sql"
    echo "  $0 docker luzbrill-db db-backups/luzbrill_erp_20260222.dump"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Archivo no encontrado: $BACKUP_FILE"
    exit 1
fi

echo "Base de datos: $DB_NAME"
echo "Archivo: $BACKUP_FILE"
echo "Modo: $MODE"
echo ""

# Detectar formato
EXTENSION="${BACKUP_FILE##*.}"

read -p "⚠️  Esto reemplazará TODOS los datos en '$DB_NAME'. ¿Continuar? (si/no): " CONFIRM
if [ "$CONFIRM" != "si" ] && [ "$CONFIRM" != "sí" ] && [ "$CONFIRM" != "s" ]; then
    echo "Cancelado."
    exit 0
fi

echo ""
echo "Restaurando..."

if [ "$MODE" = "docker" ]; then
    if [ "$EXTENSION" = "dump" ]; then
        # Formato custom -> pg_restore
        echo "Formato: custom (.dump) → usando pg_restore"
        cat "$BACKUP_FILE" | docker exec -i "$CONTAINER" \
            pg_restore -U "$DB_USER" -d "$DB_NAME" \
            --no-owner --no-privileges --clean --if-exists \
            --single-transaction 2>&1 || true
    else
        # Formato SQL -> psql
        echo "Formato: SQL (.sql) → usando psql"
        cat "$BACKUP_FILE" | docker exec -i "$CONTAINER" \
            psql -U "$DB_USER" -d "$DB_NAME" \
            --single-transaction 2>&1
    fi
else
    if [ "$EXTENSION" = "dump" ]; then
        echo "Formato: custom (.dump) → usando pg_restore"
        PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_restore -h "$DB_HOST" -p "$DB_PORT" \
            -U "$DB_USER" -d "$DB_NAME" \
            --no-owner --no-privileges --clean --if-exists \
            --single-transaction "$BACKUP_FILE" 2>&1 || true
    else
        echo "Formato: SQL (.sql) → usando psql"
        PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h "$DB_HOST" -p "$DB_PORT" \
            -U "$DB_USER" -d "$DB_NAME" \
            --single-transaction < "$BACKUP_FILE" 2>&1
    fi
fi

echo ""
echo "============================================"
echo " ✅ Restore completado"
echo "============================================"
echo ""
echo "Verifica los datos ejecutando:"
if [ "$MODE" = "docker" ]; then
    echo "  docker exec -it $CONTAINER psql -U $DB_USER -d $DB_NAME -c '\\dt'"
    echo "  docker exec -it $CONTAINER psql -U $DB_USER -d $DB_NAME -c 'SELECT count(*) FROM usuario;'"
else
    echo "  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c '\\dt'"
fi
