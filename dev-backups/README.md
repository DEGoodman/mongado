# Development Backups

This directory contains Neo4j database backups for development and testing.

## test-notes-backup.tar.gz

Neo4j backup with ~50 test notes covering diverse topics:
- Engineering management & leadership
- DevOps & SRE practices
- Software architecture patterns
- AI & ML concepts
- Knowledge management methods
- Programming fundamentals
- Testing strategies
- Productivity & learning techniques

**Use cases:**
- Testing AI features (semantic search, Q&A, suggestions)
- Performance testing with realistic corpus
- Graph traversal and backlink testing
- Search result ranking validation
- Resetting to known state during development

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
