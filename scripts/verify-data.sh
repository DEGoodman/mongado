#!/bin/bash
# Quick script to verify Neo4j data exists

set -e

echo "🔍 Verifying Neo4j data..."
echo ""

# Check volume exists
if docker volume ls | grep -q mongado_neo4j-data; then
    echo "✅ Volume 'mongado_neo4j-data' exists"
else
    echo "❌ Volume 'mongado_neo4j-data' NOT FOUND!"
    echo "   Run: docker compose up -d neo4j"
    exit 1
fi

# Check Neo4j is running
if ! docker ps --filter "name=mongado-neo4j" --filter "status=running" | grep -q mongado-neo4j; then
    echo "⚠️  Neo4j container not running. Starting..."
    docker compose up -d neo4j
    sleep 5
fi

# Count notes directly in Neo4j
echo ""
echo "📊 Checking Neo4j database..."
NOTE_COUNT=$(docker compose exec -T neo4j cypher-shell -u neo4j -p mongado-dev-password \
    "MATCH (n:Note) RETURN count(n) AS count" | grep -o '[0-9]\+' | head -1)

if [ "$NOTE_COUNT" -gt 0 ]; then
    echo "✅ Neo4j has $NOTE_COUNT notes"
else
    echo "⚠️  Neo4j has 0 notes"
    echo "   To generate test data:"
    echo "   docker compose exec backend python scripts/generate_zettelkasten_corpus.py"
fi

# Check API if backend is running
if docker ps --filter "name=mongado-backend" --filter "status=running" | grep -q mongado-backend; then
    echo ""
    echo "📊 Checking API..."
    sleep 2  # Give backend time to be ready
    API_COUNT=$(curl -s http://localhost:8000/api/notes 2>/dev/null | jq '.notes | length' 2>/dev/null || echo "error")

    if [ "$API_COUNT" = "error" ]; then
        echo "⚠️  Could not reach API (backend may still be starting)"
    elif [ "$API_COUNT" = "$NOTE_COUNT" ]; then
        echo "✅ API returns $API_COUNT notes (matches Neo4j)"
    else
        echo "⚠️  API returns $API_COUNT notes (Neo4j has $NOTE_COUNT)"
        echo "   Try restarting backend: docker compose restart backend"
    fi
else
    echo ""
    echo "⚠️  Backend not running. Start with: docker compose up -d backend"
fi

echo ""
echo "✅ Verification complete"
