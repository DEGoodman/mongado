#!/bin/sh
#
# Production Neo4j Restore Script
#
# This script is designed to run from the backup-cron container in production.
# It has access to the Docker socket and manages the Neo4j container lifecycle.
#
# Usage (from backup-cron container):
#   /scripts/restore_neo4j_prod.sh                    # Restore from latest backup
#   /scripts/restore_neo4j_prod.sh neo4j_backup_XXX   # Restore from specific backup
#
# Environment variables (set in docker-compose.prod.yml):
#   BACKUP_DIR - Directory for backups (default: /var/mongado-backups)
#   NEO4J_PASSWORD - Neo4j password for health checks
#   FORCE - Set to "true" to skip confirmation prompt
#

set -eu

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/mongado-backups}"
NEO4J_CONTAINER="mongado-neo4j-prod"
NEO4J_IMAGE="neo4j:latest"
VOLUME_NAME="mongado_neo4j-data"
FORCE="${FORCE:-false}"

log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warn() {
    echo "[WARN] $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $1"
}

# Verify docker is available (via socket)
if ! docker info >/dev/null 2>&1; then
    log_error "Docker not available - is the socket mounted?"
    exit 1
fi

# Determine which backup to use
if [ $# -gt 0 ]; then
    BACKUP_NAME="$1"
else
    # Find latest backup
    BACKUP_NAME=$(ls -1d "${BACKUP_DIR}"/neo4j_backup_* 2>/dev/null | sort | tail -1 | xargs basename 2>/dev/null || echo "")
fi

if [ -z "$BACKUP_NAME" ]; then
    log_error "No backups found in ${BACKUP_DIR}"
    exit 1
fi

BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"
DUMP_FILE="${BACKUP_PATH}/neo4j.dump"

# Verify backup exists
if [ ! -d "$BACKUP_PATH" ]; then
    log_error "Backup directory not found: ${BACKUP_PATH}"
    exit 1
fi

if [ ! -f "$DUMP_FILE" ]; then
    log_error "Dump file not found: ${DUMP_FILE}"
    exit 1
fi

# Get backup info
BACKUP_SIZE=$(du -sh "${BACKUP_PATH}" | cut -f1)
BACKUP_DATE=$(stat -c %y "${DUMP_FILE}" 2>/dev/null | cut -d'.' -f1 || stat -f %Sm "${DUMP_FILE}" 2>/dev/null || echo "unknown")

log_info "=== Neo4j Production Restore ==="
log_info "Backup: ${BACKUP_NAME}"
log_info "Size: ${BACKUP_SIZE}"
log_info "Date: ${BACKUP_DATE}"

# Get current note count
NOTES_BEFORE="unknown"
if [ -n "${NEO4J_PASSWORD:-}" ]; then
    NOTES_BEFORE=$(docker exec "${NEO4J_CONTAINER}" cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" \
        "MATCH (n:Note) RETURN count(n) as count" 2>/dev/null | tail -1 | tr -d ' ' || echo "unknown")
fi
log_info "Notes before restore: ${NOTES_BEFORE}"

log_warn "This will REPLACE the current database!"
log_warn "Estimated downtime: ~1-2 minutes"

# Confirm unless forced
if [ "$FORCE" != "true" ]; then
    printf "Continue with restore? [y/N] "
    read -r REPLY
    case "$REPLY" in
        [Yy]|[Yy][Ee][Ss]) ;;
        *)
            log_info "Restore cancelled"
            exit 0
            ;;
    esac
fi

# Stop Neo4j container
log_info "Stopping Neo4j container..."
DOWNTIME_START=$(date +%s)
docker stop "${NEO4J_CONTAINER}"

# Run neo4j-admin load in a temporary container
log_info "Restoring database with neo4j-admin..."
if docker run --rm --user root \
    -v "${VOLUME_NAME}:/data" \
    -v "${BACKUP_PATH}:/backups" \
    "${NEO4J_IMAGE}" \
    neo4j-admin database load neo4j --from-path=/backups --overwrite-destination=true; then
    log_info "Database restored successfully"
else
    log_error "neo4j-admin load failed"
    log_warn "Starting Neo4j container..."
    docker start "${NEO4J_CONTAINER}"
    exit 1
fi

# Restart Neo4j container
log_info "Starting Neo4j container..."
docker start "${NEO4J_CONTAINER}"
DOWNTIME_END=$(date +%s)
DOWNTIME=$((DOWNTIME_END - DOWNTIME_START))

# Wait for Neo4j to be healthy
log_info "Waiting for Neo4j to become healthy..."
HEALTH_TIMEOUT=120
HEALTH_COUNT=0
while [ $HEALTH_COUNT -lt $HEALTH_TIMEOUT ]; do
    if docker exec "${NEO4J_CONTAINER}" cypher-shell -u neo4j -p "${NEO4J_PASSWORD:-password}" "RETURN 1" >/dev/null 2>&1; then
        break
    fi
    sleep 1
    HEALTH_COUNT=$((HEALTH_COUNT + 1))
done

if [ $HEALTH_COUNT -ge $HEALTH_TIMEOUT ]; then
    log_warn "Neo4j health check timed out after ${HEALTH_TIMEOUT}s"
fi

# Get note count after restore
NOTES_AFTER="unknown"
if [ -n "${NEO4J_PASSWORD:-}" ]; then
    NOTES_AFTER=$(docker exec "${NEO4J_CONTAINER}" cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" \
        "MATCH (n:Note) RETURN count(n) as count" 2>/dev/null | tail -1 | tr -d ' ' || echo "unknown")
fi

# Summary
log_info "=== Restore Summary ==="
log_info "Backup: ${BACKUP_NAME}"
log_info "Downtime: ${DOWNTIME} seconds"
log_info "Notes before: ${NOTES_BEFORE}"
log_info "Notes after: ${NOTES_AFTER}"
log_info "=== Restore Complete ==="
