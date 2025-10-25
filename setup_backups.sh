#!/bin/bash
#
# Setup script for Neo4j backup system
#
# Run this once on the production droplet to set up backup directories
# and permissions.
#
# Usage: ./setup_backups.sh

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

BACKUP_DIR="/var/mongado-backups"

log_info "Setting up Neo4j backup system..."

# Create backup directory if it doesn't exist
if [ ! -d "$BACKUP_DIR" ]; then
    log_info "Creating backup directory: $BACKUP_DIR"
    sudo mkdir -p "$BACKUP_DIR"
else
    log_info "Backup directory already exists: $BACKUP_DIR"
fi

# Set permissions (readable/writable by all since Docker containers may run as different users)
log_info "Setting permissions on backup directory..."
sudo chmod 777 "$BACKUP_DIR"

# Display status
log_info "Backup directory setup complete!"
log_info "Location: $BACKUP_DIR"
log_info "Permissions: $(ls -ld $BACKUP_DIR | awk '{print $1}')"
log_info "Available space: $(df -h $BACKUP_DIR | tail -1 | awk '{print $4}')"

log_warn ""
log_warn "Next steps:"
log_warn "1. Deploy/restart services: docker compose -f docker-compose.prod.yml up -d"
log_warn "2. Test manual backup: docker exec mongado-neo4j-prod /scripts/backup_neo4j.sh"
log_warn "3. Verify cron service: docker logs mongado-backup-cron"
