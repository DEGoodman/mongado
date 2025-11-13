#!/bin/bash
# Restore Neo4j notes from backup
set -e

echo "🔄 Restoring Neo4j notes from backup..."

# Stop Neo4j
echo "Stopping Neo4j container..."
docker compose stop neo4j

# Extract and restore
echo "Extracting backup..."
cd /Users/goerik/Code/mongado
mkdir -p /tmp/notes-restore
tar -xzf dev-backups/test-notes-backup.tar.gz -C /tmp/notes-restore

echo "Restoring database..."
# Get the neo4j data volume and extract the backup into it
docker run --rm \
  -v mongado_neo4j_data:/data \
  -v /tmp/notes-restore:/backup \
  busybox sh -c "
    echo 'Cleaning old database...' &&
    rm -rf /data/databases/neo4j/* &&
    echo 'Extracting backup...' &&
    tar -xzf /backup/neo4j.dump -C /data &&
    echo 'Setting permissions...' &&
    chown -R 7474:7474 /data/databases/neo4j 2>/dev/null || true
  "

# Clean up
rm -rf /tmp/notes-restore

# Start Neo4j
echo "Starting Neo4j container..."
docker compose start neo4j

echo "⏳ Waiting for Neo4j to start..."
sleep 10

# Verify
echo "✅ Restore complete! Checking notes..."
curl -s http://localhost:8000/api/notes | jq -r '"Found \(.count) notes"'

echo ""
echo "🎉 Done! Your notes have been restored."
