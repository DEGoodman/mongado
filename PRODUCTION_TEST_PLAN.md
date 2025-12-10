# Production Testing Plan: Backup Management API & Auto-Restore

## Overview

This document outlines the testing plan for verifying the backup management API endpoints and auto-restore functionality work correctly in production after deployment.

**Related Issues:**
- #131: API endpoints for backup management
- #132: Pre-deployment backup in CI/CD
- #133: Production auto-restore from backups

## Pre-Deployment Checklist

Before pushing to production, verify locally:

- [x] All 162 tests pass (`make test-backend`)
- [x] Type checking passes (`make typecheck-backend`)
- [x] Linting passes (`make lint-backend`)
- [x] Security scan passes (`make security`)
- [x] Path traversal vulnerability fixed and tested

## Deployment Verification

### 1. Watch GitHub Actions Deployment

Monitor the deployment workflow:

```bash
# Push changes
git push origin main

# Watch GitHub Actions
gh run watch
```

**Expected CI/CD Steps:**
1. ✅ Pre-deployment backup succeeds (with retry/error handling)
2. ✅ SSH into droplet
3. ✅ Pull latest code
4. ✅ Tag deployment for rollback (new)
5. ✅ Rebuild containers
6. ✅ Health checks pass (all with retry logic):
   - Backend (localhost:8000): 5 retries x 5s = 25s max
   - Frontend (localhost:3000): 5 retries x 5s = 25s max
7. ✅ Database health check runs (12 retries x 5s = 60s max)
8. ✅ Auto-restore (if needed)
9. ✅ Post-deployment backup succeeds (with retry/error handling)
10. ✅ Verify deployment (external endpoints):
    - Backend API (https://api.mongado.com): 6 retries x 10s = 60s max
    - Frontend (https://mongado.com): 6 retries x 10s = 60s max

**What to watch for:**
- Pre-deployment backup should complete in ~60 seconds (may skip if API not ready)
- Deployment gets tagged with timestamp (e.g., `deployment-1702234567`)
- All health checks show retry attempts if services aren't ready immediately
- If database is empty, auto-restore should trigger
- Post-deployment backup should use API (not SSH)
- External endpoint verification should succeed within 60 seconds

**Retry Logic Summary:**
- **Internal health checks** (localhost): 5 attempts x 5s = max 25s wait
- **Database health check** (API): 12 attempts x 5s = max 60s wait
- **External verification**: 6 attempts x 10s = max 60s wait
- Total max deployment time: ~15 minutes (including build, health checks, backups)

### 2. Verify API Endpoints

After deployment completes, test the admin API endpoints:

#### Test 1: Health Check (No Auth)

```bash
curl https://api.mongado.com/api/admin/health/database | jq '.'
```

**Expected Response:**
```json
{
  "status": "healthy",
  "notes_count": 100,
  "backups_available": 5,
  "needs_restore": false,
  "last_backup": "2025-12-10T04:00:00",
  "neo4j_available": true
}
```

**Verify:**
- ✅ Status is "healthy"
- ✅ Notes count matches expected
- ✅ Backups available > 0
- ✅ needs_restore is false
- ✅ Neo4j available is true

#### Test 2: List Backups (Requires Auth)

```bash
# Set your admin token
export ADMIN_TOKEN="your-admin-token-from-1password"

curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://api.mongado.com/api/admin/backups | jq '.'
```

**Expected Response:**
```json
{
  "backups": [
    {
      "filename": "neo4j_backup_20251210_040000",
      "size": "2.3M",
      "timestamp": "2025-12-10T04:00:00",
      "path": "/var/mongado-backups/neo4j_backup_20251210_040000"
    },
    ...
  ],
  "count": 5
}
```

**Verify:**
- ✅ Returns list of backups sorted by newest first
- ✅ Count matches number of backups
- ✅ Timestamps are in ISO 8601 format
- ✅ Sizes are human-readable

#### Test 3: Trigger Manual Backup (Requires Auth)

**⚠️ WARNING: This causes ~30-60 seconds of downtime!**

```bash
curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://api.mongado.com/api/admin/backup | jq '.'
```

**Expected Response:**
```json
{
  "status": "success",
  "backup_file": "neo4j_backup_20251210_050000",
  "timestamp": "2025-12-10T05:00:00",
  "downtime_seconds": 45,
  "note_count": 100
}
```

**Verify:**
- ✅ Status is "success"
- ✅ Backup file created with correct timestamp
- ✅ Downtime is reasonable (30-90 seconds)
- ✅ Note count matches expected

**After backup, verify it appears in list:**

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://api.mongado.com/api/admin/backups | jq '.backups[0]'
```

### 3. Test Security Protections

#### Test 3a: Verify Auth Required

```bash
# Should fail with 401
curl https://api.mongado.com/api/admin/backups
# Expected: {"detail":"Authorization required"}

# Should fail with 403
curl -H "Authorization: Bearer invalid-token" \
  https://api.mongado.com/api/admin/backups
# Expected: {"detail":"Invalid token"}
```

#### Test 3b: Verify Path Traversal Protection

```bash
# Should fail with 422 validation error
curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"backup_file":"../../../etc/passwd"}' \
  https://api.mongado.com/api/admin/restore
# Expected: 422 Unprocessable Entity

curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"backup_file":"../../config.yml"}' \
  https://api.mongado.com/api/admin/restore
# Expected: 422 Unprocessable Entity
```

**Verify:**
- ✅ Both requests return 422 validation error
- ✅ Error message mentions invalid format

### 4. Test Auto-Restore Flow (Optional - Use Caution)

**⚠️ WARNING: This test deletes all notes! Only run if you understand the risks!**

This test should only be run if you want to verify the auto-restore functionality works correctly.

#### Step 1: Record Current State

```bash
# Get current note count
BEFORE=$(curl -s https://api.mongado.com/api/notes | jq '.count')
echo "Notes before test: $BEFORE"
```

#### Step 2: Create Fresh Backup

```bash
curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://api.mongado.com/api/admin/backup | jq '.'
```

#### Step 3: Simulate Empty Database

**⚠️ DANGER: This deletes all notes!**

```bash
# SSH into droplet
ssh your-droplet

# Delete all notes (simulates database loss)
docker compose -f docker-compose.prod.yml exec -T neo4j \
  cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "MATCH (n:Note) DETACH DELETE n"
```

#### Step 4: Check Health Status

```bash
# Should show needs_restore: true
curl https://api.mongado.com/api/admin/health/database | jq '.'
```

**Expected:**
```json
{
  "status": "degraded",
  "notes_count": 0,
  "backups_available": 5,
  "needs_restore": true,
  "last_backup": "2025-12-10T05:00:00",
  "neo4j_available": true
}
```

#### Step 5: Trigger Restore

```bash
curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' \
  https://api.mongado.com/api/admin/restore | jq '.'
```

**Expected Response:**
```json
{
  "status": "success",
  "restored_from": "neo4j_backup_20251210_050000",
  "timestamp": "2025-12-10T05:10:00",
  "downtime_seconds": 90,
  "notes_before": 0,
  "notes_after": 100
}
```

#### Step 6: Verify Restoration

```bash
# Get note count after restore
AFTER=$(curl -s https://api.mongado.com/api/notes | jq '.count')
echo "Notes after restore: $AFTER"

# Should match BEFORE
if [ "$BEFORE" -eq "$AFTER" ]; then
  echo "✅ Restore successful"
else
  echo "❌ Restore failed: expected $BEFORE, got $AFTER"
fi
```

## CI/CD Integration Verification

### Verify Pre-Deployment Backup

Check GitHub Actions logs for:

```
📦 Creating pre-deployment backup...
✅ Pre-deployment backup created
{
  "status": "success",
  "backup_file": "neo4j_backup_20251210_040000",
  ...
}
```

### Verify Database Health Check

Check GitHub Actions logs for:

```
🏥 Checking database health...
{
  "status": "healthy",
  "notes_count": 100,
  "needs_restore": false,
  ...
}
✅ Database is healthy
```

### Verify Post-Deployment Backup

Check GitHub Actions logs for:

```
📦 Creating post-deployment backup...
✅ Post-deployment backup created
```

## Rollback Plan

If any issues occur during testing:

### 1. Automatic Rollback (Issue #127 - Tag-Based)

**NEW**: If deployment fails, GitHub Actions will automatically trigger rollback to the previous successful deployment.

The rollback process:
1. Finds the previous deployment tag (e.g., `deployment-1702234567`)
2. Resets git to that tag
3. Rebuilds and restarts containers
4. Verifies backend and frontend health
5. Reports rollback status

**Fallback**: If no deployment tags exist (first deployment), falls back to `HEAD~1`.

**View deployment tags:**
```bash
ssh your-droplet
cd /opt/mongado
git tag -l 'deployment-*' | sort -V | tail -10
```

### 2. Manual Rollback to Specific Deployment

```bash
ssh your-droplet
cd /opt/mongado

# List recent deployments
git tag -l 'deployment-*' | sort -V | tail -10

# Rollback to specific tag
git reset --hard deployment-TIMESTAMP
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### 3. If Backup API Fails

```bash
# Fallback to manual backup via SSH
ssh your-droplet
docker compose -f docker-compose.prod.yml exec neo4j /scripts/backup_neo4j.sh
```

### 4. If Restore Fails

```bash
# Manual restore via SSH
ssh your-droplet
docker compose -f docker-compose.prod.yml exec neo4j /scripts/restore_neo4j.sh
```

### 5. Emergency Rollback (Outside CI/CD)

```bash
# Revert to previous commit and force push
git revert HEAD
git push origin main

# Or manually restore from backup on droplet
ssh your-droplet
cd /opt/mongado
git tag -l 'deployment-*' | sort -V | tail -2 | head -1  # Get previous tag
git reset --hard deployment-PREVIOUS
docker compose -f docker-compose.prod.yml up -d
```

## Success Criteria

All of the following must pass:

- ✅ Deployment completes successfully
- ✅ Pre-deployment backup runs (visible in GitHub Actions)
- ✅ Post-deployment backup runs via API (not SSH)
- ✅ Health check endpoint returns correct status
- ✅ List backups endpoint returns available backups
- ✅ Manual backup endpoint works and creates backup
- ✅ Authentication is enforced on admin endpoints
- ✅ Path traversal attacks are blocked
- ✅ Auto-restore works when database is empty (optional test)
- ✅ Site remains functional after deployment

## Post-Deployment Monitoring

After deployment, monitor for the next 24 hours:

### Check Logs

```bash
ssh your-droplet
docker compose -f docker-compose.prod.yml logs -f backend | grep -i "backup\|restore\|admin"
```

**Watch for:**
- Backup cron job runs successfully at 2 AM
- No error messages related to backup/restore
- Admin API requests are logged

### Check Disk Space

```bash
ssh your-droplet
du -sh /var/mongado-backups/
ls -lht /var/mongado-backups/ | head -10
```

**Verify:**
- Backup directory is not growing too fast
- Old backups are being cleaned up (retention policy)
- Newest backup is from today

### Check Backup Schedule

```bash
ssh your-droplet
docker compose -f docker-compose.prod.yml exec neo4j cat /etc/crontabs/root
```

**Verify:**
- Cron job is configured for 2 AM
- Script path is correct

## Questions for Consideration

1. **Backup notification**: Should we add email/webhook notification on backup success/failure?
2. **Backup timing**: Is 2 AM the right time for daily backups?
3. **Retention policy**: Current policy keeps 7 daily backups. Is this sufficient?
4. **Monitoring**: Should we add Prometheus metrics for backup success/failure?

## Related Documentation

- `docs/knowledge-base/BACKUP_RESTORE.md` - Complete backup/restore documentation
- Issue #111 - Parent epic for backup/restore improvements
- Issue #130 - Script rewrite (completed)
- Issue #131 - API endpoints (this deployment)
- Issue #132 - CI/CD integration (this deployment)
- Issue #133 - Auto-restore (this deployment)
