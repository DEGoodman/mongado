#!/bin/bash
#
# Neo4j Backup Script with Hash-based Change Detection
#
# This script creates a backup of the Neo4j database only if content has changed.
# Backups are stored as compressed dumps on the local server.
#
# Usage: docker compose exec neo4j /scripts/backup_neo4j.sh
#
# Environment variables:
#   BACKUP_DIR - Directory for backups (default: /var/mongado-backups)
#   BACKUP_RETENTION_COUNT - Number of backups to keep (default: 14)
#   BACKUP_RETENTION_DAYS - Days to keep backups (default: 30)

set -euo pipefail

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-/var/mongado-backups}"
TEMP_DIR="/tmp/neo4j-backup-${TIMESTAMP}"
BACKUP_NAME="neo4j_backup_${TIMESTAMP}"
RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-14}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

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

# Cleanup function
cleanup() {
    if [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
        log_debug "Cleaned up temp directory"
    fi
}

trap cleanup EXIT

# Check if Neo4j admin tool exists
if [ ! -f /var/lib/neo4j/bin/neo4j-admin ]; then
    log_error "This script must be run inside the Neo4j container"
    log_info "Usage: docker compose exec neo4j /scripts/backup_neo4j.sh"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"
mkdir -p "${TEMP_DIR}"

log_info "Starting Neo4j backup check..."

# Create temporary database dump
log_debug "Creating temporary database dump..."
# Use Cypher export instead of neo4j-admin dump (which requires database to be stopped)
# We'll export using APOC if available, otherwise use a simple tar of the data directory
if cypher-shell -u neo4j -p "${NEO4J_AUTH#neo4j/}" "RETURN 1" > /dev/null 2>&1; then
    # Database is running, use data directory snapshot
    log_debug "Creating snapshot from live database..."

    # Export nodes and relationships as JSON via APOC
    # For now, just tar the data directory (this is safe for read operations)
    tar -czf "${TEMP_DIR}/neo4j.dump" -C /data databases/neo4j 2>/dev/null || {
        log_error "Failed to create database snapshot"
        exit 1
    }
    TEMP_DUMP="${TEMP_DIR}/neo4j.dump"
    log_debug "Temporary snapshot created"
else
    log_error "Cannot connect to Neo4j database"
    exit 1
fi

# Calculate hash of current dump
CURRENT_HASH=$(sha256sum "$TEMP_DUMP" | cut -d' ' -f1)
log_debug "Current database hash: ${CURRENT_HASH:0:16}..."

# Check if we have a previous hash
HASH_FILE="${BACKUP_DIR}/.last_backup_hash"
if [ -f "$HASH_FILE" ]; then
    LAST_HASH=$(cat "$HASH_FILE")
    log_debug "Previous database hash: ${LAST_HASH:0:16}..."

    # Compare hashes
    if [ "$CURRENT_HASH" = "$LAST_HASH" ]; then
        log_info "No changes detected - skipping backup"
        exit 0
    else
        log_info "Changes detected - creating backup"
    fi
else
    log_info "No previous backup found - creating initial backup"
fi

# Compress the dump
BACKUP_ARCHIVE="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
log_info "Compressing backup..."
if tar -czf "${BACKUP_ARCHIVE}" -C "${TEMP_DIR}" neo4j.dump; then
    BACKUP_SIZE=$(du -h "${BACKUP_ARCHIVE}" | cut -f1)
    log_info "Backup created: ${BACKUP_NAME}.tar.gz (${BACKUP_SIZE})"
else
    log_error "Failed to compress backup"
    exit 1
fi

# Save current hash
echo "$CURRENT_HASH" > "$HASH_FILE"
log_debug "Saved current hash for next comparison"

# Clean up old backups by count (keep last N backups)
log_info "Cleaning up old backups (keeping last ${RETENTION_COUNT})..."
BACKUP_COUNT=$(find "${BACKUP_DIR}" -name "neo4j_backup_*.tar.gz" -type f | wc -l)
if [ "$BACKUP_COUNT" -gt "$RETENTION_COUNT" ]; then
    BACKUPS_TO_DELETE=$((BACKUP_COUNT - RETENTION_COUNT))
    log_info "Deleting ${BACKUPS_TO_DELETE} old backup(s)..."
    find "${BACKUP_DIR}" -name "neo4j_backup_*.tar.gz" -type f -printf '%T+ %p\n' | \
        sort | \
        head -n "$BACKUPS_TO_DELETE" | \
        cut -d' ' -f2- | \
        xargs rm -f
fi

# Also clean up by age (delete anything older than retention days)
log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "neo4j_backup_*.tar.gz" -type f -mtime +${RETENTION_DAYS} -delete

# Display summary
log_info "=== Backup Summary ==="
log_info "Timestamp: ${TIMESTAMP}"
log_info "File: ${BACKUP_ARCHIVE}"
log_info "Size: ${BACKUP_SIZE}"
log_info "Hash: ${CURRENT_HASH:0:16}..."
log_info "Retention: Last ${RETENTION_COUNT} backups OR ${RETENTION_DAYS} days"

# List current backups
REMAINING_BACKUPS=$(find "${BACKUP_DIR}" -name "neo4j_backup_*.tar.gz" -type f | wc -l)
log_info "Total backups: ${REMAINING_BACKUPS}"
