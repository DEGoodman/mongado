# TODO: Next Session Tasks

## High Priority: Neo4j Backup Automation

**Goal**: Implement automated daily backups of Neo4j persistent notes

**Requirements**:
1. Create backup script that exports Neo4j data
2. Set up automated daily execution (cron job in Docker)
3. Upload backups to DigitalOcean Spaces (or S3-compatible storage)
4. Create restore procedure documentation
5. Test backup and restore process

**Why Critical**: Currently no backups = risk of total data loss for all persistent notes

**Implementation Notes**:
- Neo4j dump command: `neo4j-admin database dump neo4j`
- Consider retention policy (e.g., keep last 30 days)
- Compress backups to save space
- Add monitoring/alerts for failed backups

**Files to Create**:
- `backend/scripts/backup_neo4j.sh` - Backup script
- `backend/scripts/restore_neo4j.sh` - Restore script
- `docs/knowledge-base/BACKUP_RESTORE.md` - Documentation
- Update `docker-compose.prod.yml` - Add cron job

---

**Session Notes (2025-10-14)**:
- User wanted to prioritize Neo4j backups after homepage work
- User has DigitalOcean monitoring agent already running
- User wants Mongado to be: knowledge tool + content platform + portfolio
