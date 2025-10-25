# Neo4j Backup and Restore

This document describes the automated backup system for Neo4j persistent notes and how to restore from backups.

## Overview

The backup system uses hash-based change detection to create backups only when the database content has changed. Backups are stored as compressed dumps on the server's local filesystem.

**Key features:**
- Automatic daily backup checks (runs at 2 AM)
- Only creates backups when content changes (hash comparison)
- Keeps last 14 backups OR 30 days of history (whichever provides more coverage)
- Stored locally on droplet at `/var/mongado-backups/`
- Simple flat files (tar.gz) - easy to inspect and restore

## Initial Setup (Production Only)

**Run this once on your production droplet** to set up the backup directory:

```bash
# SSH into droplet
ssh user@droplet

# Navigate to mongado directory
cd /path/to/mongado

# Run setup script
./setup_backups.sh
```

This creates `/var/mongado-backups/` with proper permissions.

**Then deploy with the new backup configuration:**

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## Automated Backups

### How It Works

1. **Daily cron job** runs at 2:00 AM via `backup-cron` service
2. **Hash check**: Compares current database hash with previous backup
3. **Conditional backup**: Only creates new backup if content changed
4. **Cleanup**: Removes old backups based on retention policy

### Configuration

Backup settings are configured in `docker-compose.prod.yml`:

```yaml
environment:
  - BACKUP_DIR=/var/mongado-backups
  - BACKUP_RETENTION_COUNT=14    # Keep last 14 backups
  - BACKUP_RETENTION_DAYS=30     # OR keep 30 days of backups
```

### Manual Backup

To manually trigger a backup:

```bash
# From droplet (production)
docker exec mongado-neo4j-prod /scripts/backup_neo4j.sh

# From local dev environment
docker compose exec neo4j /scripts/backup_neo4j.sh
```

### View Backup Status

```bash
# List all backups
ls -lh /var/mongado-backups/

# View backup log
docker logs mongado-backup-cron

# Check last backup hash
cat /var/mongado-backups/.last_backup_hash
```

## Restoring from Backup

### Restore Latest Backup

```bash
# Interactive restore (will prompt for confirmation)
docker exec -it mongado-neo4j-prod /scripts/restore_neo4j.sh

# Then restart Neo4j to load the restored data
docker compose restart neo4j
```

### Restore Specific Backup

```bash
# List available backups
docker exec mongado-neo4j-prod ls -lh /var/mongado-backups/

# Restore specific backup
docker exec -it mongado-neo4j-prod /scripts/restore_neo4j.sh neo4j_backup_20251024_143000.tar.gz

# Restart Neo4j
docker compose restart neo4j
```

### Restore from Local Backup (Disaster Recovery)

If you've downloaded backups to your local machine:

```bash
# 1. Copy backup to droplet
scp local-backups/neo4j_backup_20251024_143000.tar.gz user@droplet:/var/mongado-backups/

# 2. SSH into droplet
ssh user@droplet

# 3. Restore the backup
docker exec -it mongado-neo4j-prod /scripts/restore_neo4j.sh neo4j_backup_20251024_143000.tar.gz

# 4. Restart Neo4j
docker compose -f docker-compose.prod.yml restart neo4j
```

## Backup File Format

Backups are stored as compressed tar.gz archives:

```
/var/mongado-backups/
├── neo4j_backup_20251024_020000.tar.gz
├── neo4j_backup_20251025_020000.tar.gz
├── neo4j_backup_20251026_020000.tar.gz
└── .last_backup_hash
```

**Filename format**: `neo4j_backup_YYYYMMDD_HHMMSS.tar.gz`

Each archive contains a `neo4j.dump` file which is the Neo4j database dump.

## Storage Requirements

Typical storage usage for personal knowledge base:

- **Empty database**: ~100KB - 500KB compressed
- **100 notes**: ~2-5MB compressed
- **1,000 notes**: ~20-50MB compressed

With 14 backup retention:
- **100 notes**: ~28-70MB total
- **1,000 notes**: ~280-700MB total

The 50GB droplet has plenty of space for backups.

## Disaster Recovery

### Download Backups Locally

Periodically download backups to your local machine for extra safety:

```bash
# Download all backups
scp -r user@droplet:/var/mongado-backups/ ./local-backups/

# Or just download latest
scp user@droplet:/var/mongado-backups/neo4j_backup_*.tar.gz ./local-backups/
```

### Complete Restore Procedure

If you lose the entire droplet and need to rebuild:

1. **Set up new droplet** and deploy Mongado
2. **Copy backup to new server**:
   ```bash
   scp local-backups/neo4j_backup_20251024_143000.tar.gz user@new-droplet:/var/mongado-backups/
   ```
3. **Restore database**:
   ```bash
   ssh user@new-droplet
   docker exec -it mongado-neo4j-prod /scripts/restore_neo4j.sh
   docker compose -f docker-compose.prod.yml restart neo4j
   ```

## Monitoring

### Check Backup Health

```bash
# View recent backup activity
docker logs --tail 50 mongado-backup-cron

# Check if backups are being created
ls -lt /var/mongado-backups/ | head -n 5

# Verify backup script is accessible
docker exec mongado-neo4j-prod ls -l /scripts/
```

### Troubleshooting

**No backups being created:**
1. Check cron service is running: `docker ps | grep backup-cron`
2. Check cron logs: `docker logs mongado-backup-cron`
3. Verify scripts are mounted: `docker exec mongado-neo4j-prod ls /scripts/`
4. Test manual backup: `docker exec mongado-neo4j-prod /scripts/backup_neo4j.sh`

**Backup script fails:**
1. Check Neo4j is healthy: `docker ps | grep neo4j`
2. Check script permissions: `docker exec mongado-neo4j-prod ls -l /scripts/backup_neo4j.sh`
3. Check disk space: `df -h /var/mongado-backups/`

**Restore fails:**
1. Verify backup file exists: `docker exec mongado-neo4j-prod ls -l /var/mongado-backups/`
2. Check backup file integrity: Extract and inspect the dump
3. Review Neo4j logs: `docker logs mongado-neo4j-prod`

## Testing

Before relying on backups in production, test the process:

```bash
# 1. Create some test notes (via UI or API)

# 2. Trigger a backup
docker exec mongado-neo4j-prod /scripts/backup_neo4j.sh

# 3. Create more notes

# 4. Restore from backup
docker exec -it mongado-neo4j-prod /scripts/restore_neo4j.sh

# 5. Restart and verify
docker compose restart neo4j
# Check UI - should see notes from backup, not the newer ones
```

## Future Enhancements

See [Issue #22](https://github.com/DEGoodman/mongado/issues/22) for potential future improvements:
- Export notes as markdown files (human-readable, git-friendly)
- Optional cloud backup integration (DigitalOcean Spaces, S3)
- Real-time backup notifications/alerts
- Automated restore testing

## Related Documentation

- [Notes System Guide](./NOTES.md) - Understanding the Zettelkasten note system
- [Articles Guide](./ARTICLES.md) - Static article management
- [Knowledge Base Architecture](./README.md) - Overall KB system design
