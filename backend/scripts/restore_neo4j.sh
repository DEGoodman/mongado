#!/bin/bash
#
# Neo4j Restore Script using neo4j-admin
#
# Restores a Neo4j database from a backup created with neo4j-admin dump.
# Requires stopping the Neo4j container (~1-2min downtime).
#
# Usage:
#   make restore                         # Via Makefile - restores latest backup
#   make restore BACKUP=neo4j_backup_20241201_120000.dump  # Specific backup
#   ./backend/scripts/restore_neo4j.sh   # Direct execution (latest)
#   ./backend/scripts/restore_neo4j.sh <backup_file>  # Specific backup
#
# Environment variables:
#   BACKUP_DIR - Directory for backups (default: ./backups for dev, /var/mongado-backups for prod)
#   FORCE - Set to "true" to skip confirmation prompts (for CI/CD)
#   COMPOSE_FILE - Docker compose file to use (default: docker-compose.yml)
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Detect environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Configuration
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
FORCE="${FORCE:-false}"

# Determine backup directory based on environment
if [[ "$COMPOSE_FILE" == *"prod"* ]]; then
    BACKUP_DIR="${BACKUP_DIR:-/var/mongado-backups}"
    VOLUME_NAME="mongado_neo4j-data"
    NEO4J_IMAGE="neo4j:latest"
else
    BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups}"
    VOLUME_NAME="mongado_neo4j-data"
    NEO4J_IMAGE="neo4j:latest"
fi

# Get Neo4j password from docker-compose config or environment
if [[ -z "${NEO4J_PASSWORD:-}" ]]; then
    # Try to extract from docker compose config (handles both "KEY: value" and "KEY=value" formats)
    NEO4J_PASSWORD=$(docker compose -f "$COMPOSE_FILE" config 2>/dev/null | grep -i 'NEO4J_AUTH' | head -1 | sed 's/.*neo4j\///' | tr -d ' "' || echo "")
fi

# Change to project root for docker compose commands
cd "$PROJECT_ROOT"

# Verify docker compose is available
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH"
    exit 1
fi

# Determine which backup to restore
# Backups are directories named neo4j_backup_YYYYMMDD_HHMMSS containing neo4j.dump
if [[ $# -eq 0 ]]; then
    # Find latest backup directory (sort by name which includes timestamp)
    BACKUP_SUBDIR=$(ls -1d "${BACKUP_DIR}"/neo4j_backup_* 2>/dev/null | sort -r | head -n 1)

    if [[ -z "$BACKUP_SUBDIR" ]] || [[ ! -d "$BACKUP_SUBDIR" ]]; then
        log_error "No backups found in ${BACKUP_DIR}"
        log_info "Looking for directories matching: neo4j_backup_*"
        exit 1
    fi

    log_info "Using latest backup: $(basename "$BACKUP_SUBDIR")"
else
    BACKUP_INPUT="$1"

    # If only directory name provided, look in backup dir
    if [[ -d "$BACKUP_INPUT" ]]; then
        BACKUP_SUBDIR="$BACKUP_INPUT"
    elif [[ -d "${BACKUP_DIR}/$BACKUP_INPUT" ]]; then
        BACKUP_SUBDIR="${BACKUP_DIR}/$BACKUP_INPUT"
    else
        log_error "Backup directory not found: $BACKUP_INPUT"
        log_info "Available backups:"
        ls -1d "${BACKUP_DIR}"/neo4j_backup_* 2>/dev/null | xargs -I{} basename {} || echo "  (none)"
        exit 1
    fi

    log_info "Using specified backup: $(basename "$BACKUP_SUBDIR")"
fi

# Verify the dump file exists in the backup directory
if [[ ! -f "${BACKUP_SUBDIR}/neo4j.dump" ]]; then
    log_error "neo4j.dump not found in backup directory: ${BACKUP_SUBDIR}"
    exit 1
fi

# Get backup info
BACKUP_SIZE=$(du -sh "${BACKUP_SUBDIR}" | cut -f1)
BACKUP_DATE=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "${BACKUP_SUBDIR}/neo4j.dump" 2>/dev/null || stat -c "%y" "${BACKUP_SUBDIR}/neo4j.dump" 2>/dev/null | cut -d'.' -f1)

log_info "=== Neo4j Restore ==="
log_info "Backup: $(basename "$BACKUP_SUBDIR")"
log_info "Backup size: ${BACKUP_SIZE}"
log_info "Backup date: ${BACKUP_DATE}"
log_warn "This will REPLACE the current database!"
log_warn "Estimated downtime: ~1-2 minutes"

# Confirm unless forced
if [[ "$FORCE" != "true" ]]; then
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    echo
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Restore cancelled"
        exit 0
    fi
fi

# Get current note count for comparison
log_debug "Getting current note count..."
NOTE_COUNT_BEFORE=$(docker compose -f "$COMPOSE_FILE" exec -T neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" "MATCH (n:Note) RETURN count(n) as count" 2>/dev/null | tail -1 | tr -d ' ' || echo "unknown")
log_info "Notes before restore: ${NOTE_COUNT_BEFORE}"

# Stop Neo4j container
log_info "Stopping Neo4j container..."
DOWNTIME_START=$(date +%s)
docker compose -f "$COMPOSE_FILE" stop neo4j

# Run neo4j-admin load in a temporary container
# Run as root to ensure write access to data volume
log_info "Restoring database with neo4j-admin..."

# Mount the backup subdirectory which contains neo4j.dump
if docker run --rm --user root \
    -v "${VOLUME_NAME}:/data" \
    -v "${BACKUP_SUBDIR}:/backups:ro" \
    "${NEO4J_IMAGE}" \
    neo4j-admin database load neo4j --from-path=/backups --overwrite-destination=true; then
    log_info "Database restored successfully"
else
    log_error "neo4j-admin load failed"
    log_warn "Starting Neo4j with existing data..."
    docker compose -f "$COMPOSE_FILE" start neo4j
    exit 1
fi

# Restart Neo4j container
log_info "Starting Neo4j container..."
docker compose -f "$COMPOSE_FILE" start neo4j
DOWNTIME_END=$(date +%s)
DOWNTIME=$((DOWNTIME_END - DOWNTIME_START))

# Wait for Neo4j to be healthy
log_info "Waiting for Neo4j to become healthy..."
HEALTH_TIMEOUT=120
HEALTH_COUNT=0
while [[ $HEALTH_COUNT -lt $HEALTH_TIMEOUT ]]; do
    if docker compose -f "$COMPOSE_FILE" exec -T neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" "RETURN 1" &>/dev/null; then
        break
    fi
    sleep 1
    HEALTH_COUNT=$((HEALTH_COUNT + 1))
done

if [[ $HEALTH_COUNT -ge $HEALTH_TIMEOUT ]]; then
    log_error "Neo4j health check timed out after ${HEALTH_TIMEOUT}s"
    log_warn "Neo4j may still be starting - check logs with: docker compose logs neo4j"
    exit 1
fi

# Verify restore
log_debug "Verifying restore..."
NOTE_COUNT_AFTER=$(docker compose -f "$COMPOSE_FILE" exec -T neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" "MATCH (n:Note) RETURN count(n) as count" 2>/dev/null | tail -1 | tr -d ' ' || echo "unknown")

# Update hash file to match restored state
RESTORED_HASH=$(sha256sum "${BACKUP_SUBDIR}/neo4j.dump" | cut -d' ' -f1)
echo "$RESTORED_HASH" > "${BACKUP_DIR}/.last_backup_hash"

# Summary
log_info "=== Restore Summary ==="
log_info "Backup: $(basename "$BACKUP_SUBDIR")"
log_info "Backup size: ${BACKUP_SIZE}"
log_info "Backup date: ${BACKUP_DATE}"
log_info "Downtime: ${DOWNTIME} seconds"
log_info "Notes before: ${NOTE_COUNT_BEFORE}"
log_info "Notes after: ${NOTE_COUNT_AFTER}"

if [[ "$NOTE_COUNT_BEFORE" != "$NOTE_COUNT_AFTER" ]] && [[ "$NOTE_COUNT_BEFORE" != "unknown" ]] && [[ "$NOTE_COUNT_AFTER" != "unknown" ]]; then
    log_warn "Note count changed from ${NOTE_COUNT_BEFORE} to ${NOTE_COUNT_AFTER}"
fi

log_info "=== Restore Complete ==="
