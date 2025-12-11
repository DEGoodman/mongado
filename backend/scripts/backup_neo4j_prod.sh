#!/bin/sh
#
# Production Neo4j Backup Script
#
# This script is designed to run from the backup-cron container in production.
# It has access to the Docker socket and manages the Neo4j container lifecycle.
#
# Usage (from backup-cron container):
#   /scripts/backup_neo4j_prod.sh
#
# Environment variables (set in docker-compose.prod.yml):
#   BACKUP_DIR - Directory for backups (default: /var/mongado-backups)
#   BACKUP_RETENTION_COUNT - Minimum backups to keep (default: 14)
#   BACKUP_RETENTION_DAYS - Days before deleting excess backups (default: 30)
#   NEO4J_PASSWORD - Neo4j password for health checks
#
# Retention policy:
#   - Always keeps at least BACKUP_RETENTION_COUNT backups
#   - Only deletes backups older than BACKUP_RETENTION_DAYS when count exceeds minimum
#   - This ensures at least one backup always exists

set -eu

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-/var/mongado-backups}"
RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-14}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
NEO4J_CONTAINER="mongado-neo4j-prod"
NEO4J_IMAGE="neo4j:latest"
VOLUME_NAME="mongado_neo4j-data"

BACKUP_SUBDIR="${BACKUP_DIR}/neo4j_backup_${TIMESTAMP}"

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

# Create backup directory
mkdir -p "${BACKUP_SUBDIR}"

log_info "=== Neo4j Production Backup ==="
log_info "Backup directory: ${BACKUP_SUBDIR}"
log_info "Container: ${NEO4J_CONTAINER}"

# Get current note count for logging
NOTE_COUNT="unknown"
if [ -n "${NEO4J_PASSWORD:-}" ]; then
    NOTE_COUNT=$(docker exec "${NEO4J_CONTAINER}" cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" \
        "MATCH (n:Note) RETURN count(n) as count" 2>/dev/null | tail -1 | tr -d ' ' || echo "unknown")
fi
log_info "Notes in database: ${NOTE_COUNT}"

# Hash-based change detection
HASH_FILE="${BACKUP_DIR}/.last_backup_hash"
if [ -n "${NEO4J_PASSWORD:-}" ]; then
    CONTENT_HASH=$(docker exec "${NEO4J_CONTAINER}" cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" \
        "MATCH (n:Note) RETURN count(n) as c, collect(n.title) as titles" 2>/dev/null | tail -1 | sha256sum | cut -d' ' -f1 || echo "unknown")

    if [ -f "$HASH_FILE" ]; then
        LAST_HASH=$(cat "$HASH_FILE")
        if [ "$CONTENT_HASH" = "$LAST_HASH" ] && [ "$CONTENT_HASH" != "unknown" ]; then
            log_info "No changes detected since last backup - skipping"
            rmdir "${BACKUP_SUBDIR}" 2>/dev/null || true
            exit 0
        fi
        log_info "Changes detected - proceeding with backup"
    else
        log_info "No previous backup hash - creating initial backup"
    fi
else
    log_warn "NEO4J_PASSWORD not set - skipping change detection"
    CONTENT_HASH="unknown"
fi

# Stop Neo4j container
log_info "Stopping Neo4j container..."
DOWNTIME_START=$(date +%s)
docker stop "${NEO4J_CONTAINER}"

# Run neo4j-admin dump in a temporary container
log_info "Creating backup with neo4j-admin..."
if docker run --rm \
    -v "${VOLUME_NAME}:/data" \
    -v "${BACKUP_SUBDIR}:/backups" \
    "${NEO4J_IMAGE}" \
    neo4j-admin database dump neo4j --to-path=/backups --overwrite-destination=true; then
    log_info "Backup created successfully"
else
    log_error "neo4j-admin dump failed"
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

# Save content hash
if [ "$CONTENT_HASH" != "unknown" ]; then
    echo "$CONTENT_HASH" > "$HASH_FILE"
fi

# Get backup size
BACKUP_SIZE=$(du -sh "${BACKUP_SUBDIR}" | cut -f1)

# Safe retention policy cleanup
BACKUP_COUNT=$(ls -1d "${BACKUP_DIR}"/neo4j_backup_* 2>/dev/null | wc -l | tr -d ' ')
log_info "Current backup count: ${BACKUP_COUNT} (keeping minimum ${RETENTION_COUNT})"

if [ "$BACKUP_COUNT" -gt "$RETENTION_COUNT" ]; then
    EXCESS_COUNT=$((BACKUP_COUNT - RETENTION_COUNT))
    OLD_BACKUPS=$(ls -1d "${BACKUP_DIR}"/neo4j_backup_* 2>/dev/null | sort | head -n "$EXCESS_COUNT")
    DELETED=0

    for backup in $OLD_BACKUPS; do
        # Check if older than RETENTION_DAYS
        if find "$backup" -maxdepth 0 -mtime +"${RETENTION_DAYS}" 2>/dev/null | grep -q .; then
            log_info "Deleting old backup: $(basename "$backup")"
            rm -rf "$backup"
            DELETED=$((DELETED + 1))
        fi
    done

    if [ "$DELETED" -gt 0 ]; then
        log_info "Deleted ${DELETED} backup(s) older than ${RETENTION_DAYS} days"
    fi
fi

# Summary
REMAINING_BACKUPS=$(ls -1d "${BACKUP_DIR}"/neo4j_backup_* 2>/dev/null | wc -l | tr -d ' ')

log_info "=== Backup Summary ==="
log_info "Backup: ${BACKUP_SUBDIR}"
log_info "Size: ${BACKUP_SIZE}"
log_info "Downtime: ${DOWNTIME} seconds"
log_info "Notes: ${NOTE_COUNT}"
log_info "Total backups: ${REMAINING_BACKUPS}"
log_info "=== Backup Complete ==="
