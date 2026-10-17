#!/usr/bin/env bash
# ==============================================================================
# TalentMatch - Script de Restauración de Base de Datos PostgreSQL
# Restaura un respaldo comprimido .sql.gz generado por backup_db.sh
# Uso: ./restore_db.sh [ruta_al_archivo_backup.sql.gz]
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_ROOT/backend/.env" ]; then
    # shellcheck disable=SC1091
    set -a; source "$PROJECT_ROOT/backend/.env"; set +a
elif [ -f "$PROJECT_ROOT/.env" ]; then
    # shellcheck disable=SC1091
    set -a; source "$PROJECT_ROOT/.env"; set +a
fi

DB_NAME="${POSTGRES_DB:-talentmatch}"
DB_USER="${POSTGRES_USER:-talentmatch}"
DB_PASSWORD="${POSTGRES_PASSWORD:-talentmatch}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

if [ $# -lt 1 ]; then
    echo "Uso: $0 <archivo_backup.sql.gz>"
    echo "Ejemplo: $0 ~/backups/talentmatch/talentmatch_backup_20261012_020000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "[ERROR] El archivo de respaldo '$BACKUP_FILE' no existe." >&2
    exit 1
fi

echo "[ADVERTENCIA] Este proceso restaurará la base de datos '$DB_NAME'."
echo "Archivo: $BACKUP_FILE"

if command -v psql &> /dev/null; then
    echo "[INFO] Restaurando mediante psql local..."
    gunzip -c "$BACKUP_FILE" | PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"
elif docker ps --format '{{.Names}}' | grep -q "talentmatch-postgres"; then
    echo "[INFO] Restaurando mediante contenedor Docker 'talentmatch-postgres'..."
    gunzip -c "$BACKUP_FILE" | docker exec -i -e PGPASSWORD="$DB_PASSWORD" talentmatch-postgres psql -U "$DB_USER" -d "$DB_NAME"
else
    echo "[ERROR] No se encontró cliente psql ni contenedor Docker de PostgreSQL." >&2
    exit 1
fi

echo "[SUCCESS] Base de datos '$DB_NAME' restaurada exitosamente."
