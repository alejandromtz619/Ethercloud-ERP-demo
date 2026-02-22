#!/bin/bash
# ============================================================
# Luz Brill ERP - Script de Backup de PostgreSQL
# ============================================================
# Uso desde el servidor ACTUAL (donde está la DB):
#   chmod +x scripts/db-backup.sh
#   ./scripts/db-backup.sh
#
# Si la DB corre en Docker:
#   ./scripts/db-backup.sh docker
# ============================================================

set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./db-backups"
BACKUP_FILE="${BACKUP_DIR}/luzbrill_erp_${TIMESTAMP}.sql"
BACKUP_FILE_CUSTOM="${BACKUP_DIR}/luzbrill_erp_${TIMESTAMP}.dump"

# Configuración - ajustar según tu setup actual
DB_NAME="${POSTGRES_DB:-luzbrill_erp}"
DB_USER="${POSTGRES_USER:-luzbrill}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

mkdir -p "$BACKUP_DIR"

echo "============================================"
echo " Luz Brill ERP - Backup de Base de Datos"
echo "============================================"
echo "Base de datos: $DB_NAME"
echo "Timestamp: $TIMESTAMP"
echo ""

if [ "${1:-}" = "docker" ]; then
    CONTAINER="${2:-luzbrill-db}"
    echo "Modo: Docker (contenedor: $CONTAINER)"
    echo ""

    # Backup en formato SQL (legible, compatible universal)
    echo "[1/2] Generando backup SQL..."
    docker exec "$CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" \
        --no-owner --no-privileges --if-exists --clean \
        > "$BACKUP_FILE"
    echo "  ✅ $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

    # Backup en formato custom (más rápido para restore, comprimido)
    echo "[2/2] Generando backup custom (comprimido)..."
    docker exec "$CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" \
        --format=custom --no-owner --no-privileges \
        > "$BACKUP_FILE_CUSTOM"
    echo "  ✅ $BACKUP_FILE_CUSTOM ($(du -h "$BACKUP_FILE_CUSTOM" | cut -f1))"

else
    echo "Modo: Directo (pg_dump local)"
    echo ""

    # Backup SQL
    echo "[1/2] Generando backup SQL..."
    PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump -h "$DB_HOST" -p "$DB_PORT" \
        -U "$DB_USER" -d "$DB_NAME" \
        --no-owner --no-privileges --if-exists --clean \
        > "$BACKUP_FILE"
    echo "  ✅ $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

    # Backup custom
    echo "[2/2] Generando backup custom (comprimido)..."
    PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump -h "$DB_HOST" -p "$DB_PORT" \
        -U "$DB_USER" -d "$DB_NAME" \
        --format=custom --no-owner --no-privileges \
        > "$BACKUP_FILE_CUSTOM"
    echo "  ✅ $BACKUP_FILE_CUSTOM ($(du -h "$BACKUP_FILE_CUSTOM" | cut -f1))"
fi

echo ""
echo "============================================"
echo " Backup completado exitosamente"
echo "============================================"
echo ""
echo "Archivos generados:"
echo "  SQL:    $BACKUP_FILE"
echo "  Custom: $BACKUP_FILE_CUSTOM"
echo ""
echo "Para transferir al nuevo servidor OVHcloud:"
echo "  scp $BACKUP_FILE user@tu-vps-ovh:/ruta/db-backups/"
echo "  scp $BACKUP_FILE_CUSTOM user@tu-vps-ovh:/ruta/db-backups/"
