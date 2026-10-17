#!/usr/bin/env bash
# ==============================================================================
# TalentMatch - Script Automatizado de Respaldo de Base de Datos PostgreSQL
# Realiza pg_dump con compresión gzip, rotación de archivos y sincronización con S3
# ==============================================================================

set -euo pipefail

# 1. Definición de rutas y directorios
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DATE_LOG=$(date +"%Y-%m-%d %H:%M:%S")

# Cargar variables de entorno si existe .env
if [ -f "$PROJECT_ROOT/backend/.env" ]; then
    # shellcheck disable=SC1091
    set -a; source "$PROJECT_ROOT/backend/.env"; set +a
elif [ -f "$PROJECT_ROOT/.env" ]; then
    # shellcheck disable=SC1091
    set -a; source "$PROJECT_ROOT/.env"; set +a
fi

# 2. Configuración de parámetros con valores por defecto
DB_NAME="${POSTGRES_DB:-talentmatch}"
DB_USER="${POSTGRES_USER:-talentmatch}"
DB_PASSWORD="${POSTGRES_PASSWORD:-talentmatch}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/talentmatch}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
S3_BUCKET="${S3_BUCKET:-}"

BACKUP_FILENAME="talentmatch_backup_${TIMESTAMP}.sql.gz"
BACKUP_FILEPATH="${BACKUP_DIR}/${BACKUP_FILENAME}"

echo "[$DATE_LOG] [INFO] Iniciando respaldo de PostgreSQL para BD '$DB_NAME'..."

# 3. Crear directorio de respaldos si no existe
mkdir -p "$BACKUP_DIR"

# 4. Ejecutar respaldo con pg_dump y compresión gzip
if command -v pg_dump &> /dev/null; then
    echo "[$DATE_LOG] [INFO] Usando pg_dump del sistema..."
    PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --clean \
        --if-exists \
        --no-owner \
        --no-privileges | gzip -9 > "$BACKUP_FILEPATH"
elif docker ps --format '{{.Names}}' | grep -q "talentmatch-postgres"; then
    echo "[$DATE_LOG] [INFO] Usando pg_dump dentro del contenedor Docker 'talentmatch-postgres'..."
    docker exec -e PGPASSWORD="$DB_PASSWORD" talentmatch-postgres pg_dump \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --clean \
        --if-exists \
        --no-owner \
        --no-privileges | gzip -9 > "$BACKUP_FILEPATH"
else
    echo "[$DATE_LOG] [ERROR] No se encontró pg_dump en el host ni contenedor Docker de PostgreSQL." >&2
    exit 1
fi

# 5. Validar integridad del archivo generado
if [ -s "$BACKUP_FILEPATH" ]; then
    FILE_SIZE=$(du -h "$BACKUP_FILEPATH" | cut -f1)
    echo "[$DATE_LOG] [SUCCESS] Respaldo generado con éxito: $BACKUP_FILENAME (Tamaño: $FILE_SIZE)"
else
    echo "[$DATE_LOG] [ERROR] El archivo de respaldo se encuentra vacío o no fue generado." >&2
    rm -f "$BACKUP_FILEPATH"
    exit 1
fi

# 6. Sincronización opcional hacia AWS S3
if [ -n "$S3_BUCKET" ]; then
    if command -v aws &> /dev/null; then
        echo "[$DATE_LOG] [INFO] Subiendo respaldo al bucket AWS S3: s3://$S3_BUCKET/backups/..."
        if aws s3 cp "$BACKUP_FILEPATH" "s3://${S3_BUCKET}/backups/${BACKUP_FILENAME}"; then
            echo "[$DATE_LOG] [SUCCESS] Respaldo sincronizado en AWS S3."
        else
            echo "[$DATE_LOG] [WARNING] Falló la subida a S3, el respaldo local permanece intacto."
        fi
    else
        echo "[$DATE_LOG] [WARNING] S3_BUCKET configurado pero AWS CLI no está instalado."
    fi
fi

# 7. Rotación de respaldos locales (Elimina archivos más antiguos que RETENTION_DAYS días)
echo "[$DATE_LOG] [INFO] Aplicando política de rotación: eliminando respaldos locales con más de $RETENTION_DAYS días..."
DELETED_COUNT=$(find "$BACKUP_DIR" -name "talentmatch_backup_*.sql.gz" -type f -mtime +"$RETENTION_DAYS" | wc -l)
find "$BACKUP_DIR" -name "talentmatch_backup_*.sql.gz" -type f -mtime +"$RETENTION_DAYS" -delete
echo "[$DATE_LOG] [INFO] Rotación finalizada. Archivos antiguos depurados: $DELETED_COUNT."

echo "[$DATE_LOG] [SUCCESS] Proceso de respaldo completado exitosamente."
