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

## Automatic Restore (Production)

In production, the system can automatically detect when the database is empty but backups exist, and restore from the latest backup via the admin API.

### How It Works

1. **Health Check Endpoint**: `GET /api/admin/health/database` monitors database state
2. **Detection**: Checks if Neo4j is available, note count is 0, and backups exist
3. **CI/CD Integration**: GitHub Actions deployment can trigger restore if needed
4. **API-Driven**: Uses the same `/api/admin/restore` endpoint as manual restores

### Health Check Response

```bash
# Check database health
curl https://api.mongado.com/api/admin/health/database | jq '.'

# Example responses:

# Healthy database
{
  "status": "healthy",
  "notes_count": 42,
  "backups_available": 14,
  "needs_restore": false,
  "last_backup": "2024-12-01T02:00:00",
  "neo4j_available": true
}

# Empty database with backups (degraded state)
{
  "status": "degraded",
  "notes_count": 0,
  "backups_available": 14,
  "needs_restore": true,
  "last_backup": "2024-12-01T02:00:00",
  "neo4j_available": true
}

# Neo4j unavailable
{
  "status": "unhealthy",
  "notes_count": 0,
  "backups_available": 14,
  "needs_restore": true,
  "last_backup": "2024-12-01T02:00:00",
  "neo4j_available": false
}
```

### Triggering Auto-Restore

The restore can be triggered via the admin API:

```bash
# Restore from latest backup (recommended)
curl -X POST https://api.mongado.com/api/admin/restore \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'

# Restore from specific backup
curl -X POST https://api.mongado.com/api/admin/restore \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"backup_file": "neo4j_backup_20241201_020000"}'

# Response
{
  "status": "success",
  "restored_from": "neo4j_backup_20241201_020000",
  "timestamp": "2024-12-01T15:30:00",
  "downtime_seconds": 85,
  "notes_before": 0,
  "notes_after": 42
}
```

### Dev vs Production Behavior

- **Development**: Empty database auto-seeds with test notes using `seed_test_notes.py`
- **Production**: Empty database with backups triggers restore recommendation via health check
- **Production**: Empty database without backups (first deployment) does nothing

## Manual Restore

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
docker exec -it mongado-neo4j-prod /scripts/restore_neo4j.sh neo4j_backup_20241024_143000.tar.gz

# Restart Neo4j
docker compose restart neo4j
```

### Using Admin API

The admin API provides endpoints for listing and restoring backups:

```bash
# List all available backups
curl https://api.mongado.com/api/admin/backups \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.'

# Response
{
  "backups": [
    {
      "filename": "neo4j_backup_20241201_020000",
      "size": "2.3M",
      "timestamp": "2024-12-01T02:00:00",
      "path": "/var/mongado-backups/neo4j_backup_20241201_020000"
    }
  ],
  "count": 14
}

# Trigger restore from latest
curl -X POST https://api.mongado.com/api/admin/restore \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
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

### Testing Backup and Restore Process

Before relying on backups in production, test the complete backup/restore cycle:

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

### Testing Auto-Restore Flow

To test the automatic restore detection and recovery procedure:

#### 1. Create Test Data and Backup

```bash
# Development environment
make up

# Create some test notes via API
curl -X POST http://localhost:8000/api/notes \
  -H "Content-Type: application/json" \
  -d '{
    "note_id": "test-note-1",
    "title": "Test Note 1",
    "content": "This is a test note for backup testing.",
    "tags": ["test"]
  }'

curl -X POST http://localhost:8000/api/notes \
  -H "Content-Type: application/json" \
  -d '{
    "note_id": "test-note-2",
    "title": "Test Note 2",
    "content": "Another test note with a [[test-note-1|wikilink]].",
    "tags": ["test"]
  }'

# Verify notes were created
curl http://localhost:8000/api/notes | jq '.count'
# Expected: 2

# Create a backup using the admin API
curl -X POST http://localhost:8000/api/admin/backup \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### 2. Simulate Empty Database

```bash
# Get Neo4j password from environment
export NEO4J_PASSWORD=$(docker compose exec backend printenv NEO4J_PASSWORD | tr -d '\r')

# Delete all notes from database (simulates data loss)
docker compose exec neo4j cypher-shell \
  -u neo4j \
  -p "$NEO4J_PASSWORD" \
  "MATCH (n:Note) DETACH DELETE n"

# Verify database is empty
curl http://localhost:8000/api/notes | jq '.count'
# Expected: 0
```

#### 3. Check Health Endpoint

```bash
# Check database health status
curl http://localhost:8000/api/admin/health/database | jq '.'

# Expected response (degraded state):
{
  "status": "degraded",
  "notes_count": 0,
  "backups_available": 1,
  "needs_restore": true,
  "last_backup": "2024-12-09T...",
  "neo4j_available": true
}

# Verify the needs_restore flag is true
curl http://localhost:8000/api/admin/health/database | jq '.needs_restore'
# Expected: true
```

#### 4. Trigger Auto-Restore

```bash
# List available backups
curl http://localhost:8000/api/admin/backups \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.'

# Restore from latest backup
curl -X POST http://localhost:8000/api/admin/restore \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'

# Expected response:
{
  "status": "success",
  "restored_from": "neo4j_backup_20241209_...",
  "timestamp": "2024-12-09T...",
  "downtime_seconds": 85,
  "notes_before": 0,
  "notes_after": 2
}
```

#### 5. Verify Restore Success

```bash
# Check note count
curl http://localhost:8000/api/notes | jq '.count'
# Expected: 2

# Verify specific notes were restored
curl http://localhost:8000/api/notes/test-note-1 | jq '.title'
# Expected: "Test Note 1"

curl http://localhost:8000/api/notes/test-note-2 | jq '.title'
# Expected: "Test Note 2"

# Check health status (should be healthy now)
curl http://localhost:8000/api/admin/health/database | jq '.'
# Expected: status = "healthy", needs_restore = false
```

#### 6. Test Edge Cases

**Empty database, no backups (first deployment):**

```bash
# Delete all backups
docker compose exec backend rm -rf /backups/neo4j_backup_*

# Check health
curl http://localhost:8000/api/admin/health/database | jq '.'
# Expected: needs_restore = false (no backups available)
```

**Neo4j unavailable:**

```bash
# Stop Neo4j
docker compose stop neo4j

# Check health
curl http://localhost:8000/api/admin/health/database | jq '.'
# Expected: status = "unhealthy", neo4j_available = false
```

### Production Testing

For testing in production:

```bash
# 1. Check current health
curl https://api.mongado.com/api/admin/health/database | jq '.'

# 2. If needs_restore is true, trigger restore
curl -X POST https://api.mongado.com/api/admin/restore \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'

# 3. Monitor restore progress
# Check backend logs during restore (takes 1-2 minutes)
# Via SSH: docker logs -f mongado-backend-prod

# 4. Verify restoration
curl https://api.mongado.com/api/notes | jq '.count'
curl https://api.mongado.com/api/admin/health/database | jq '.status'
```

### CI/CD Integration Testing

The GitHub Actions workflow can automatically check and restore after deployment:

```yaml
# Example workflow step (to be implemented in #132)
- name: Check database health and auto-restore if needed
  run: |
    # Check if restore is needed
    HEALTH=$(curl -s https://api.mongado.com/api/admin/health/database)
    NEEDS_RESTORE=$(echo $HEALTH | jq -r '.needs_restore')

    if [ "$NEEDS_RESTORE" = "true" ]; then
      echo "Database needs restore, triggering auto-restore..."

      RESTORE_RESULT=$(curl -s -X POST https://api.mongado.com/api/admin/restore \
        -H "Authorization: Bearer ${{ secrets.ADMIN_TOKEN }}" \
        -H "Content-Type: application/json" \
        -d '{}')

      echo "Restore result: $RESTORE_RESULT"

      # Verify restore succeeded
      NOTES_AFTER=$(echo $RESTORE_RESULT | jq -r '.notes_after')
      if [ "$NOTES_AFTER" -gt "0" ]; then
        echo "Auto-restore successful: $NOTES_AFTER notes restored"
      else
        echo "WARNING: Auto-restore may have failed"
        exit 1
      fi
    else
      echo "Database healthy, no restore needed"
    fi
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
