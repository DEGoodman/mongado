# Development Notes Database

This directory contains tools and backups for managing test notes in development.

## Automatic Seeding

**The Neo4j database automatically seeds itself with test notes when empty!**

When you start the backend in debug mode (`DEBUG=true`), it checks if Neo4j is empty and automatically runs the seed script. No manual intervention needed.

To trigger re-seeding:
```bash
# Clear the database
docker compose exec backend python -c "
from adapters.neo4j import Neo4jAdapter
adapter = Neo4jAdapter()
with adapter.driver.session() as session:
    session.run('MATCH (n) DETACH DELETE n')
"

# Restart backend to trigger auto-seed
docker compose restart backend
```

## Manual Seeding

You can also manually seed the database:
```bash
docker compose exec backend python scripts/seed_test_notes.py
```

## Test Notes Structure

The seed script creates **90 notes** structured as an ideal Zettelkasten corpus:

**Graph Structure:**
- 5 entry point notes (broad concepts, 10-14 links each)
- 8 hub notes (well-connected concepts, 5-11 links)
- 42 atomic notes (2-3 links each)
- 15 stub notes (TODOs for testing incomplete states)
- 10 question notes (exploring open ideas)
- 10 orphan notes (0 links for testing orphan detection)
- **Total:** ~197 bidirectional links, ~2.2 avg links/note

**Topics:**
- Engineering management & leadership
- SRE & operations (SLOs, incidents, monitoring)
- Knowledge management (Zettelkasten, PARA, PKM)
- Software development (CI/CD, testing, architecture)
- AI/ML (MLOps, model serving, feature stores)

**Use Cases:**
- Testing AI features (semantic search, Q&A, link suggestions)
- Performance testing with realistic corpus (~90 notes)
- Graph visualization (hubs, clusters, orphans)
- Entry point discovery
- Orphan detection validation
- Resetting to known good state during development

## Seed Script Location

The seed script is located at `backend/scripts/seed_test_notes.py` and:
- Generates 90 notes with realistic Zettelkasten structure
- Creates bidirectional wikilinks between related concepts
- Uses WikilinkParser to extract and validate links
- Creates notes first, then links (two-pass approach)

## Note Characteristics

- **Interconnected**: Dense wikilink network between related concepts
- **Varied lengths**: From short stubs to detailed explanations
- **Realistic states**: Mix of complete notes and stubs with TODOs
- **Hub notes**: Core concepts referenced by many other notes
- **Categories**: Engineering management, SRE, knowledge management, software architecture, AI/ML

## Backups

This directory also contains backup files (`.tar.gz`) which are created manually or by the backup script for testing backup/restore functionality. The auto-seed functionality makes these less necessary for development.
