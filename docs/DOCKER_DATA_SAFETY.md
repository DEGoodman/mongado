# Docker Data Safety Guide

## TL;DR - Safe Commands

**✅ SAFE - Data is preserved:**
```bash
docker compose down              # Stop containers, keep volumes
docker compose restart backend   # Restart service, keep volumes
docker compose stop              # Stop containers, keep volumes
```

**❌ DANGEROUS - Data is deleted:**
```bash
docker compose down -v           # Deletes ALL volumes including Neo4j data!
docker compose down --volumes    # Same as above
docker volume rm mongado_neo4j-data  # Deletes Neo4j volume
```

## How Docker Volumes Work

Your Neo4j data is stored in a **named volume** called `mongado_neo4j-data`:

```yaml
# docker-compose.yml
services:
  neo4j:
    volumes:
      - neo4j-data:/data    # Named volume (persists across down/up)

volumes:
  neo4j-data:               # Volume definition
```

**Named volumes persist** unless you explicitly delete them with:
- `docker compose down -v`
- `docker volume rm mongado_neo4j-data`

## Checking Your Data

Verify your data exists:

```bash
# Check volume exists
docker volume ls | grep neo4j

# Count notes in Neo4j directly
docker compose exec neo4j cypher-shell -u neo4j -p mongado-dev-password \
  "MATCH (n:Note) RETURN count(n) AS note_count"

# Check via API (requires backend running)
curl http://localhost:8000/api/notes | jq '.notes | length'
```

## Common Data Loss Scenarios

### 1. Accidentally running `docker compose down -v`

**Prevention:**
- Create shell alias to prevent accidents
- Add to your `.bashrc` or `.zshrc`:

```bash
# Safer docker compose down
alias dcd='docker compose down'     # Safe
alias dcdv='echo "⚠️  WARNING: This will DELETE volumes! Press Ctrl+C to cancel..." && sleep 5 && docker compose down -v'
```

### 2. Running seed script accidentally

**Prevention:**
The `generate_zettelkasten_corpus.py` script now has a safety check:
- Warns if notes exist
- Requires confirmation before deleting

```bash
# This script will now prompt before deleting
docker compose exec backend python scripts/generate_zettelkasten_corpus.py

# Output:
# ⚠️  WARNING: 87 notes currently exist in Neo4j
# ⚠️  This script will DELETE ALL EXISTING NOTES
# ⚠️  Press Ctrl+C now to cancel, or Enter to continue...
```

### 3. Backend not showing notes after restart

**Symptom:** Neo4j has notes, but API returns 0

**Solution:** Restart backend to refresh connection:
```bash
docker compose restart backend
```

## Backup & Restore

### Manual Backup

Create a backup of your Neo4j data:

```bash
# Create backup directory
mkdir -p dev-backups

# Backup Neo4j data volume
docker run --rm \
  -v mongado_neo4j-data:/data \
  -v $(pwd)/dev-backups:/backup \
  alpine tar czf /backup/neo4j-backup-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .

# List backups
ls -lh dev-backups/
```

### Restore from Backup

```bash
# Stop Neo4j
docker compose stop neo4j

# Restore backup (replace with your backup filename)
docker run --rm \
  -v mongado_neo4j-data:/data \
  -v $(pwd)/dev-backups:/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/neo4j-backup-YYYYMMDD-HHMMSS.tar.gz -C /data"

# Start Neo4j
docker compose start neo4j
docker compose restart backend  # Refresh backend connection
```

### Seed from Production

Pull notes from production API:

```bash
docker compose exec backend python scripts/seed_from_production.py
```

## Testing Data Persistence

Prove to yourself that data persists:

```bash
# 1. Check current notes
curl http://localhost:8000/api/notes | jq '.notes | length'

# 2. Stop everything (SAFE - no -v flag)
docker compose down

# 3. Verify volume still exists
docker volume ls | grep neo4j

# 4. Start everything
docker compose up -d

# 5. Wait for backend to start
sleep 5

# 6. Check notes again - should be same count
curl http://localhost:8000/api/notes | jq '.notes | length'
```

## Best Practices

1. **Never use `-v` flag** unless you explicitly want to delete data
2. **Create backups** before major changes
3. **Use seed script cautiously** - it clears all notes
4. **Test restoration** process to ensure you know how
5. **Document custom data** if you create notes you want to keep

## Troubleshooting

### "I lost my notes!"

1. Check if volume exists:
   ```bash
   docker volume ls | grep neo4j
   ```

2. Check Neo4j directly:
   ```bash
   docker compose exec neo4j cypher-shell -u neo4j -p mongado-dev-password \
     "MATCH (n:Note) RETURN count(n)"
   ```

3. If Neo4j has notes but API shows 0:
   ```bash
   docker compose restart backend
   ```

4. If volume is empty, restore from backup or regenerate test data:
   ```bash
   docker compose exec backend python scripts/generate_zettelkasten_corpus.py
   ```

### "When does data get deleted?"

Data is ONLY deleted when:
- You run `docker compose down -v` (or `--volumes`)
- You run `docker volume rm mongado_neo4j-data`
- You run `docker volume prune` (removes unused volumes)
- You run the seed script (clears notes to regenerate)

Data is NOT deleted when:
- Running `docker compose down` (without `-v`)
- Running `docker compose restart`
- Running `docker compose stop`
- Rebooting your computer
- Updating Docker

## Summary

**Remember:** `docker compose down` is SAFE. Adding `-v` is NOT.

The volume `mongado_neo4j-data` is your persistent data store. It survives everything except explicit deletion commands.
