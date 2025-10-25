#!/bin/bash
#
# Neo4j Restore Script
#
# This script restores a Neo4j database from a backup file.
#
# Usage:
#   ./restore_neo4j.sh                    # Restore from latest backup
#   ./restore_neo4j.sh <backup_file>      # Restore from specific backup
#
# Environment variables:
#   BACKUP_DIR - Directory for backups (default: /var/mongado-backups)

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/mongado-backups}"
TEMP_DIR="/tmp/neo4j-restore-$$"

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
    log_info "Usage: docker compose exec neo4j /scripts/restore_neo4j.sh [backup_file]"
    exit 1
fi

# Determine which backup to restore
if [ $# -eq 0 ]; then
    # Find latest backup
    LATEST_BACKUP=$(find "${BACKUP_DIR}" -name "neo4j_backup_*.tar.gz" -type f -printf '%T+ %p\n' | sort -r | head -n 1 | cut -d' ' -f2-)

    if [ -z "$LATEST_BACKUP" ]; then
        log_error "No backups found in ${BACKUP_DIR}"
        exit 1
    fi

    BACKUP_FILE="$LATEST_BACKUP"
    log_info "Using latest backup: $(basename "$BACKUP_FILE")"
else
    BACKUP_FILE="$1"

    # If only filename provided, look in backup dir
    if [ ! -f "$BACKUP_FILE" ]; then
        BACKUP_FILE="${BACKUP_DIR}/$1"
    fi

    if [ ! -f "$BACKUP_FILE" ]; then
        log_error "Backup file not found: $1"
        exit 1
    fi

    log_info "Using specified backup: $(basename "$BACKUP_FILE")"
fi

# Display backup info
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
BACKUP_DATE=$(stat -c %y "$BACKUP_FILE" 2>/dev/null || stat -f %Sm "$BACKUP_FILE")
log_info "Backup size: ${BACKUP_SIZE}"
log_info "Backup date: ${BACKUP_DATE}"

# Confirm restore
log_warn "⚠️  This will REPLACE the current database with the backup!"
read -p "Are you sure you want to continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log_info "Restore cancelled"
    exit 0
fi

# Create temp directory
mkdir -p "$TEMP_DIR"

# Extract backup
log_info "Extracting backup..."
if tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"; then
    log_debug "Backup extracted to ${TEMP_DIR}"
else
    log_error "Failed to extract backup"
    exit 1
fi

# Find the dump file
DUMP_FILE=$(find "$TEMP_DIR" -name "neo4j.dump" -type f | head -n 1)
if [ -z "$DUMP_FILE" ]; then
    log_error "No neo4j.dump file found in backup"
    exit 1
fi

# This backup is a tar of the data directory, not a neo4j-admin dump
# We need to stop Neo4j, restore the data directory, and restart
log_warn "This restore requires Neo4j to be stopped"
read -p "Stop Neo4j and proceed? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log_info "Restore cancelled"
    exit 0
fi

log_info "Restoring database from backup..."

# Extract the tar backup to the data directory
if tar -xzf "$DUMP_FILE" -C /data; then
    log_info "Database restored successfully!"
    log_warn "Restart Neo4j service to load restored data"
else
    log_error "Failed to restore database"
    exit 1
fi

# Update the hash file to match restored backup
RESTORED_HASH=$(sha256sum "$DUMP_FILE" | cut -d' ' -f1)
HASH_FILE="${BACKUP_DIR}/.last_backup_hash"
echo "$RESTORED_HASH" > "$HASH_FILE"
log_debug "Updated backup hash to match restored state"

log_info "=== Restore Summary ==="
log_info "Backup file: $(basename "$BACKUP_FILE")"
log_info "Backup size: ${BACKUP_SIZE}"
log_info "Backup date: ${BACKUP_DATE}"
log_info ""
log_warn "⚠️  You may need to restart the Neo4j service:"
log_info "   docker compose restart neo4j"
