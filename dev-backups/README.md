# Development Backups

This directory contains Neo4j database backups for development and testing.

## test-notes-backup.tar.gz

Neo4j backup with **87 notes** structured as an ideal Zettelkasten corpus:

**Graph Structure:**
- 5 entry point notes (broad concepts, 10-13 links each)
- 8 hub notes (well-connected concepts, 5-11 links)
- 40 regular atomic notes (2-3 links each)
- 15 stub notes (TODOs for testing incomplete states)
- 10 question notes (exploring open ideas)
- 10 orphan notes (0 links for testing orphan detection)
- **Total:** 308 bidirectional links, 3.5 avg links/note

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

## Restoring the Backup

See the [README.md](../README.md#quick-start) for restore instructions.

Quick reference:
```bash
docker compose up -d
cat dev-backups/test-notes-backup.tar.gz | docker compose exec -T neo4j sh -c 'cat > /var/mongado-backups/test-notes.tar.gz'
docker compose exec -it neo4j /scripts/restore_neo4j.sh test-notes.tar.gz
docker compose restart neo4j
```

## Note Characteristics

- **Interconnected**: Dense wikilink network between related concepts
- **Varied lengths**: From short stubs to detailed explanations
- **Realistic states**: Mix of complete notes and stubs with TODOs
- **Hub notes**: Core concepts referenced by many other notes
- **Categories**: Engineering, AI/ML, knowledge management, productivity

Articles are loaded automatically from `backend/static/articles/` and don't need to be restored.
