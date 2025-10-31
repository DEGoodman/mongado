# Knowledge Base Documentation

The Mongado Knowledge Base is a personal knowledge management system that combines static long-form articles with dynamic atomic notes in a Zettelkasten-style system.

## Architecture Overview

The Knowledge Base consists of two complementary content types:

### Articles (Static Content)
- **Format**: Markdown files with YAML frontmatter
- **Storage**: `backend/static/articles/*.md` (version controlled)
- **Purpose**: Long-form, curated essays and tutorials
- **Characteristics**: Professional, polished, published content
- **Examples**: "SaaS Billing Models", "Engineering Management Best Practices"

### Notes (Dynamic Content)
- **Format**: Atomic notes with bidirectional wikilinks
- **Storage**: Database (Neo4j)
- **Purpose**: Personal thoughts, work-in-progress ideas, interconnected concepts
- **Characteristics**: Short, single-concept, heavily linked
- **Examples**: `curious-elephant`, `wise-mountain` (adjective-noun IDs)

## Key Features

### 1. Unified Content Model
Both articles and notes are treated as "resources" in the API, allowing:
- Cross-linking between articles and notes using `[[wikilinks]]`
- Unified search across both content types
- Consistent metadata (tags, timestamps, authors)

### 2. Hybrid Storage Strategy
- **Articles**: Static markdown files, cached at startup, auto-reload on changes
- **Notes**: Database-backed (Neo4j), for admin-created content

### 3. AI Integration (Ollama)
- Semantic search across articles and notes
- AI-suggested related content and wikilinks
- Auto-generated summaries for navigation
- Q&A with context from knowledge base

### 4. Graph Visualization
- Interactive force-directed graph of note relationships
- Visual distinction between articles, notes, and authors
- Backlinks panel showing incoming references
- Local subgraph view for each note

## Content Authoring

### For Articles
See **[ARTICLES.md](ARTICLES.md)** for the complete guide on:
- Creating markdown articles with frontmatter
- Adding and optimizing images (WebP format)
- Creating diagrams with external tools
- Managing static assets and caching

### For Notes
See **[NOTES.md](NOTES.md)** for the complete guide on:
- Creating atomic notes with adjective-noun IDs
- Using wikilink syntax `[[note-id]]` for bidirectional linking
- Admin authentication and permissions
- Working with the graph visualization

## API Structure

### Resource Endpoints
```
GET    /api/resources           # List all resources (articles + notes)
POST   /api/resources           # Create resource
GET    /api/resources/{id}      # Get single resource
DELETE /api/resources/{id}      # Delete resource (notes only)
```

### Notes-Specific Endpoints
```
GET    /api/notes                      # List all notes
POST   /api/notes                      # Create note (auth required for persistent)
GET    /api/notes/{note_id}            # Get single note
PUT    /api/notes/{note_id}            # Update note
DELETE /api/notes/{note_id}            # Delete note

GET    /api/notes/{note_id}/links      # Get outbound links
GET    /api/notes/{note_id}/backlinks  # Get inbound links (who links here)
GET    /api/notes/graph                # Get full graph (nodes + edges)
GET    /api/notes/{note_id}/graph      # Get local subgraph around note
```

### AI Endpoints
```
POST   /api/search                        # Semantic search (articles + notes)
POST   /api/ask                           # Q&A with context
POST   /api/notes/{note_id}/suggest-links # AI-suggested related notes
GET    /api/notes/{note_id}/summary       # AI-generated summary
GET    /api/articles/{id}/summary         # AI-generated article summary
```

## Navigation Structure

```
/knowledge-base                       # Landing page (search + links to both)
├── /knowledge-base/articles          # Browse articles (grid view)
│   └── /knowledge-base/articles/[slug]  # Single article view
│
└── /knowledge-base/notes             # Browse notes (list + graph toggle)
    ├── /knowledge-base/notes/graph   # Full graph visualization
    └── /knowledge-base/notes/[id]    # Single note view (e.g., curious-elephant)
```

## Technical Details

### Backend Stack
- **Framework**: FastAPI (Python 3.13)
- **Database**: Neo4j (graph database for notes and relationships)
- **Storage**: Filesystem (articles) + Database (notes)
- **AI**: Ollama (local LLM for embeddings and chat)
- **Caching**: In-memory with file modification time tracking

### Frontend Stack
- **Framework**: Next.js 14 with App Router
- **UI**: React 18 + TypeScript + Tailwind CSS
- **Graph**: react-force-graph or @xyflow/react
- **Editor**: TipTap (markdown with wikilink autocomplete)

### Authentication
- **Admin**: Simple passkey-based auth (stored in 1Password)
- **Permissions**: Only admin can create notes

### Performance Optimizations
- **Article caching**: Loaded once at startup, cached in memory
- **Static assets**: 1-year browser cache with content hashing
- **Response compression**: Gzip for all responses > 1KB
- **Graph queries**: Optimized with Neo4j's native graph algorithms

## Directory Structure

```
backend/
├── static/
│   ├── articles/              # Markdown articles (source control)
│   │   ├── 001-topic.md
│   │   └── 002-another.md
│   └── assets/               # Static media files
│       ├── images/           # WebP images
│       ├── icons/            # SVG icons
│       └── downloads/        # PDFs, etc.
├── models/                   # Pydantic models
├── services/                 # Business logic
│   ├── article_service.py    # Article loading/caching
│   ├── note_service.py       # Note CRUD operations
│   └── ai_service.py         # Ollama integration
└── main.py                   # FastAPI app

frontend/
└── src/
    ├── app/
    │   └── knowledge-base/
    │       ├── page.tsx          # Landing page
    │       ├── articles/         # Article views
    │       └── notes/            # Note views + graph
    └── components/
        ├── NoteEditor.tsx        # Markdown editor with wikilinks
        ├── NoteGraph.tsx         # Graph visualization
        └── BacklinksPanel.tsx    # Backlinks display
```

## Testing Strategy

### Backend Tests
```bash
cd backend
make test              # Run all tests
make test-unit         # Unit tests only
make test-integration  # Integration tests only
```

Located in `backend/tests/`:
- `unit/` - Pure business logic (article parsing, link extraction)
- `integration/` - API endpoints with TestClient

### Frontend Tests
```bash
cd frontend
npm test               # Unit tests (Vitest)
npm run test:e2e       # E2E tests (Playwright)
```

Located in `frontend/src/__tests__/` and `frontend/tests/e2e/`

## Common Tasks

### Adding a New Article
```bash
# 1. Create markdown file
cd backend/static/articles
nano 008-new-topic.md

# 2. Add frontmatter and content (see ARTICLES.md)

# 3. Optimize images if needed
cd backend
./venv/bin/python image_optimizer.py input.jpg static/assets/images/new-topic.webp

# 4. Test locally
make run  # Starts server at http://localhost:8000

# 5. Commit to git
git add backend/static/
git commit -m "Add new article: Topic Name"
```

### Creating a Note
Use the web interface at `/knowledge-base/notes` or via API:

```bash
# Create persistent note (requires admin auth)
curl -X POST http://localhost:8000/api/notes \
  -H "Authorization: Bearer YOUR_PASSKEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Database Design Patterns",
    "content": "When designing relationships, consider [[graph-databases]] and [[relational-models]].",
    "tags": ["database", "architecture"]
  }'
```

### Viewing the Graph
Navigate to `/knowledge-base/notes/graph` to see the full interactive graph visualization.

## Troubleshooting

### Articles not loading
1. Check file location: `backend/static/articles/*.md`
2. Verify YAML frontmatter format
3. Check server logs: `make run`
4. Ensure unique `id` field

### Notes not persisting
1. Verify Neo4j is running
2. Check authentication for admin user
3. Review backend logs for errors

### Graph not rendering
1. Check browser console for errors
2. Verify `/api/notes/graph` endpoint returns data
3. Test with smaller dataset first
4. Check for circular dependencies in links

### AI features not working
1. Verify Ollama is running: `ollama list`
2. Check model is downloaded: `ollama pull mistral`
3. Review backend logs for connection errors
4. Test Ollama directly: `ollama run mistral "test"`

## Related Documentation

- **[ARTICLES.md](ARTICLES.md)** - Complete guide to creating and managing articles
- **[NOTES.md](NOTES.md)** - Complete guide to the Zettelkasten note system
- **[../SETUP.md](../SETUP.md)** - Environment setup and 1Password configuration
- **[../TESTING.md](../TESTING.md)** - Testing tools and commands
- **[../ROADMAP.md](../ROADMAP.md)** - Future enhancements and TODOs

## Support

For issues or questions:
- Check the troubleshooting sections in ARTICLES.md and NOTES.md
- Review backend logs: `docker compose logs backend`
- Check frontend console for client-side errors
- See [CLAUDE.md](../../CLAUDE.md) for development patterns
