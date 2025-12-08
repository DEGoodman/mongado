#!/bin/bash
#
# Neo4j Backup Script using neo4j-admin
#
# Creates a consistent backup using Neo4j's official dump tool.
# Requires briefly stopping the Neo4j container (~30-60s downtime).
#
# Usage:
#   make backup                    # Via Makefile (recommended)
#   ./backend/scripts/backup_neo4j.sh   # Direct execution
#
# Environment variables:
#   BACKUP_DIR - Directory for backups (default: ./backups for dev, /var/mongado-backups for prod)
#   BACKUP_RETENTION_COUNT - Number of backups to keep (default: 14)
#   BACKUP_RETENTION_DAYS - Days to keep backups (default: 30)
#   NON_INTERACTIVE - Set to "true" to skip prompts (for CI/CD)
#   FORCE_BACKUP - Set to "true" to backup even if no changes detected
#   COMPOSE_FILE - Docker compose file to use (default: docker-compose.yml)
#
# Features:
#   - Hash-based change detection: skips backup if database unchanged
#   - Safe retention policy: always keeps minimum N backups, only deletes old excess
#   - Health check: waits for Neo4j to recover after backup
#
# Retention policy:
#   - Always keeps at least BACKUP_RETENTION_COUNT backups (default: 14)
#   - Only deletes backups older than BACKUP_RETENTION_DAYS when count exceeds minimum
#   - This ensures at least one backup always exists, even during low-activity periods
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
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
NON_INTERACTIVE="${NON_INTERACTIVE:-false}"
FORCE_BACKUP="${FORCE_BACKUP:-false}"
RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-14}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

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

BACKUP_NAME="neo4j_backup_${TIMESTAMP}.dump"

# Get Neo4j password from docker-compose config or environment
if [[ -z "${NEO4J_PASSWORD:-}" ]]; then
    # Try to extract from docker compose config (handles both "KEY: value" and "KEY=value" formats)
    NEO4J_PASSWORD=$(docker compose -f "$COMPOSE_FILE" config 2>/dev/null | grep -i 'NEO4J_AUTH' | head -1 | sed 's/.*neo4j\///' | tr -d ' "' || echo "")
fi
if [[ -z "$NEO4J_PASSWORD" ]]; then
    log_warn "Could not determine Neo4j password - note count may show as 'unknown'"
    log_info "Tip: Set NEO4J_PASSWORD env var or ensure NEO4J_AUTH is in docker-compose.yml"
fi

# Change to project root for docker compose commands
cd "$PROJECT_ROOT"

# Verify docker compose is available
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH"
    exit 1
fi

# Check if Neo4j container exists
if ! docker compose -f "$COMPOSE_FILE" ps neo4j --format json 2>/dev/null | grep -q "neo4j"; then
    log_error "Neo4j service not found in ${COMPOSE_FILE}"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

log_info "=== Neo4j Backup ==="
log_info "Backup directory: ${BACKUP_DIR}"
log_info "Volume: ${VOLUME_NAME}"
log_warn "This will cause ~30-60 seconds of downtime"

# Confirm unless non-interactive
if [[ "$NON_INTERACTIVE" != "true" ]]; then
    read -p "Continue with backup? [y/N] " -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Backup cancelled"
        exit 0
    fi
fi

# Get current note count for verification
log_debug "Getting current note count..."
NOTE_COUNT_BEFORE=$(docker compose -f "$COMPOSE_FILE" exec -T neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" "MATCH (n:Note) RETURN count(n) as count" 2>/dev/null | tail -1 | tr -d ' ' || echo "unknown")
log_info "Notes in database: ${NOTE_COUNT_BEFORE}"

# Hash-based change detection
# We use a query-based hash of the database content to detect changes
# This avoids unnecessary backups when nothing has changed
log_debug "Calculating database content hash..."
CONTENT_HASH=$(docker compose -f "$COMPOSE_FILE" exec -T neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" \
    "MATCH (n:Note) WITH n ORDER BY n.id RETURN apoc.util.sha256(collect(n{.*})) as hash" 2>/dev/null | tail -1 | tr -d ' ' || echo "")

if [[ -z "$CONTENT_HASH" ]]; then
    # Fallback: use note count + titles hash if APOC not available
    CONTENT_HASH=$(docker compose -f "$COMPOSE_FILE" exec -T neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" \
        "MATCH (n:Note) RETURN count(n) as c, collect(n.title) as titles" 2>/dev/null | tail -1 | sha256sum | cut -d' ' -f1 || echo "unknown")
fi

HASH_FILE="${BACKUP_DIR}/.last_backup_hash"
if [[ -f "$HASH_FILE" ]] && [[ "$FORCE_BACKUP" != "true" ]]; then
    LAST_HASH=$(cat "$HASH_FILE")
    if [[ "$CONTENT_HASH" == "$LAST_HASH" ]] && [[ "$CONTENT_HASH" != "unknown" ]]; then
        log_info "No changes detected since last backup - skipping"
        log_info "Use FORCE_BACKUP=true to force a backup"
        exit 0
    fi
    log_info "Changes detected - proceeding with backup"
else
    if [[ "$FORCE_BACKUP" == "true" ]]; then
        log_info "Forced backup requested"
    else
        log_info "No previous backup hash found - creating initial backup"
    fi
fi

# Stop Neo4j container
log_info "Stopping Neo4j container..."
DOWNTIME_START=$(date +%s)
docker compose -f "$COMPOSE_FILE" stop neo4j

# Create timestamped backup directory
BACKUP_SUBDIR="${BACKUP_DIR}/${BACKUP_NAME%.dump}"
mkdir -p "${BACKUP_SUBDIR}"

# Run neo4j-admin dump in a temporary container
log_info "Creating backup with neo4j-admin..."
if docker run --rm \
    -v "${VOLUME_NAME}:/data" \
    -v "${BACKUP_SUBDIR}:/backups" \
    "${NEO4J_IMAGE}" \
    neo4j-admin database dump neo4j --to-path=/backups --overwrite-destination=true; then

    # The dump creates neo4j.dump in the backup subdirectory
    if [[ -f "${BACKUP_SUBDIR}/neo4j.dump" ]]; then
        log_info "Backup created: ${BACKUP_NAME%.dump}/neo4j.dump"
    else
        log_error "Dump file not found at expected location"
        docker compose -f "$COMPOSE_FILE" start neo4j
        exit 1
    fi
else
    log_error "neo4j-admin dump failed"
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
HEALTH_TIMEOUT=60
HEALTH_COUNT=0
while [[ $HEALTH_COUNT -lt $HEALTH_TIMEOUT ]]; do
    if docker compose -f "$COMPOSE_FILE" exec -T neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" "RETURN 1" &>/dev/null; then
        break
    fi
    sleep 1
    HEALTH_COUNT=$((HEALTH_COUNT + 1))
done

if [[ $HEALTH_COUNT -ge $HEALTH_TIMEOUT ]]; then
    log_warn "Neo4j health check timed out after ${HEALTH_TIMEOUT}s"
fi

# Get backup size
BACKUP_SIZE=$(du -sh "${BACKUP_SUBDIR}" | cut -f1)

# Save content hash for change detection (not file hash - content hash is more meaningful)
echo "$CONTENT_HASH" > "${BACKUP_DIR}/.last_backup_hash"
log_debug "Saved content hash: ${CONTENT_HASH:0:16}..."

# Also calculate file hash for integrity verification
BACKUP_HASH=$(sha256sum "${BACKUP_SUBDIR}/neo4j.dump" | cut -d' ' -f1)

# Clean up old backups (macOS compatible)
# Backups are directories named neo4j_backup_YYYYMMDD_HHMMSS
#
# Retention policy (safe):
# 1. Always keep at least RETENTION_COUNT backups (default: 14)
# 2. Among backups beyond RETENTION_COUNT, delete those older than RETENTION_DAYS
#
# This ensures we NEVER delete all backups, even during low-activity periods.

BACKUP_COUNT=$(ls -1d "${BACKUP_DIR}"/neo4j_backup_* 2>/dev/null | wc -l | tr -d ' ')
log_info "Current backup count: ${BACKUP_COUNT} (keeping minimum ${RETENTION_COUNT})"

if [[ "$BACKUP_COUNT" -gt "$RETENTION_COUNT" ]]; then
    # We have more than the minimum - safe to apply age-based cleanup
    # But only delete old backups that are BEYOND the retention count
    EXCESS_COUNT=$((BACKUP_COUNT - RETENTION_COUNT))

    # Get the oldest backups (beyond retention count) that are also older than RETENTION_DAYS
    OLD_BACKUPS=$(ls -1d "${BACKUP_DIR}"/neo4j_backup_* 2>/dev/null | sort | head -n "$EXCESS_COUNT")
    DELETED=0

    for backup in $OLD_BACKUPS; do
        # Check if this backup is older than RETENTION_DAYS
        if find "$backup" -maxdepth 0 -mtime +"${RETENTION_DAYS}" 2>/dev/null | grep -q .; then
            log_info "Deleting old backup: $(basename "$backup")"
            rm -rf "$backup"
            DELETED=$((DELETED + 1))
        fi
    done

    if [[ "$DELETED" -gt 0 ]]; then
        log_info "Deleted ${DELETED} backup(s) older than ${RETENTION_DAYS} days"
    else
        log_debug "No backups older than ${RETENTION_DAYS} days to delete"
    fi
else
    log_debug "Backup count (${BACKUP_COUNT}) <= retention minimum (${RETENTION_COUNT}), skipping cleanup"
fi

# Summary
REMAINING_BACKUPS=$(ls -1d "${BACKUP_DIR}"/neo4j_backup_* 2>/dev/null | wc -l | tr -d ' ')

log_info "=== Backup Summary ==="
log_info "Backup: ${BACKUP_SUBDIR}/"
log_info "Size: ${BACKUP_SIZE}"
log_info "Downtime: ${DOWNTIME} seconds"
log_info "Notes backed up: ${NOTE_COUNT_BEFORE}"
log_info "Hash: ${BACKUP_HASH:0:16}..."
log_info "Total backups: ${REMAINING_BACKUPS}"
log_info "=== Backup Complete ==="
