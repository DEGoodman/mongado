# Notes - Zettelkasten System Guide

This guide explains how to create and manage atomic notes in the Mongado Knowledge Base using a Zettelkasten-inspired approach.

## Overview

The Notes system implements atomic, interconnected notes with bidirectional linking:

- **Atomic Notes**: Short, single-concept notes created via in-app editor
- **Bidirectional Linking**: `[[adjective-noun]]` wikilink syntax with automatic backlinks
- **Graph Visualization**: Interactive graph showing note connections
- **Hybrid System**: Coexists with static markdown articles
- **Single Admin**: Only you can create persistent notes (via auth)
- **Visitor Demo**: Anonymous users can create ephemeral in-memory notes
- **AI Integration**: Ollama-powered search, link suggestions, and summaries

## Note Identification

### Adjective-Noun IDs

Notes use memorable adjective-noun identifiers like:
- `curious-elephant`
- `wise-mountain`
- `swift-river`

**Benefits:**
- **User-visible**: Delightful, memorable identifiers
- **URL-friendly**: `/notes/curious-elephant`
- **Mutable**: Admin can rename to avoid inappropriate combinations
- **Collision handling**: Auto-regenerate until unique ID found
- **Format**: `{adjective}-{noun}` (lowercase, hyphenated)

### ID Generation

IDs are automatically generated when creating notes:

```bash
GET /api/notes/generate-id
# Returns: {"id": "curious-elephant"}
```

The system:
1. Randomly selects an adjective and noun from curated word lists
2. Checks for collisions with existing notes
3. Regenerates if needed (max 100 attempts)
4. Falls back to appending a number if all combinations exhausted

## Authentication & Permissions

### Single Admin User (You)

- Authenticate via 1Password secret (passkey/API token)
- Create persistent notes (saved to Neo4j database)
- Full CRUD operations on all notes
- Can manually evict ephemeral notes

### Anonymous Visitors

- No authentication required
- Create ephemeral notes (in-memory only)
- Read all notes (persistent + ephemeral)
- Notes expire at end of session
- Author shown as "Anonymous"

### Authentication Flow

**Backend (passkey approach):**

```python
# backend/auth.py
from fastapi import HTTPException, Header

def verify_admin(authorization: str = Header(None)) -> bool:
    """Verify admin passkey from Authorization header.

    Expects: "Bearer your-secret-passkey"
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")

    passkey = authorization.replace("Bearer ", "")

    if passkey != settings.admin_passkey:
        raise HTTPException(status_code=403, detail="Invalid passkey")

    return True

# Usage in endpoints
@app.post("/api/notes")
async def create_note(
    note: NoteCreate,
    is_admin: bool = Depends(verify_admin)
):
    """Create persistent note (requires admin auth)."""
    # Create persistent note in database
```

**Frontend (localStorage approach):**

```typescript
// frontend/src/lib/auth.ts
export const login = (passkey: string) => {
  localStorage.setItem('adminPasskey', passkey);
};

export const getAuthHeaders = () => {
  const passkey = localStorage.getItem('adminPasskey');
  if (!passkey) return {};

  return {
    'Authorization': `Bearer ${passkey}`
  };
};

// Usage in API calls
const response = await fetch('/api/notes', {
  method: 'POST',
  headers: {
    ...getAuthHeaders(),
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(note)
});
```

**Environment Setup:**

```bash
# .env
ADMIN_PASSKEY=your-secret-passkey-here

# Or use 1Password CLI
ADMIN_PASSKEY=$(op read "op://vault/mongado-admin/passkey")
```

## Data Storage

### Persistent Notes (Admin Only)

- **Database**: Neo4j (graph database)
- **Tables**: `notes`, `note_links`, `note_metadata`
- **Persistence**: Written to disk immediately
- **Lifecycle**: Survives server restarts

### Ephemeral Notes (Visitors)

- **Storage**: In-memory dictionary with session IDs
- **TTL**: End of browser session (session cookie)
- **Memory limit**: 500MB total for all ephemeral notes
- **Auto-eviction**: Oldest notes removed when limit reached
- **Manual eviction**: Admin can clear via endpoint

### Database Schema (Neo4j)

Notes are stored as nodes with properties:

```cypher
// Note node
CREATE (n:Note {
  id: "curious-elephant",
  title: "Database Design Patterns",
  content: "When designing for relationships...",
  author: "admin",
  is_ephemeral: false,
  session_id: null,
  created_at: datetime(),
  updated_at: datetime(),
  tags: ["database", "patterns"],
  metadata: {}
})

// Link relationship
CREATE (source:Note {id: "curious-elephant"})
  -[:LINKS_TO {created_at: datetime()}]->
  (target:Note {id: "wise-mountain"})
```

Indexes for performance:
- `Note.id` (unique)
- `Note.author`
- `Note.is_ephemeral`
- `Note.created_at`

## Wikilink Syntax

### Creating Links

Use double square brackets to link between notes or to articles:

```markdown
See [[curious-elephant]] for database design patterns.

For billing context, read [[swift-river]] and [[saas-billing-models]] (article).
```

### Link Rendering

The system automatically:
- **Extracts links**: Parses `[[note-id]]` patterns from markdown
- **Creates relationships**: Stores bidirectional links in database
- **Renders HTML**: Converts to clickable links in the UI
- **Shows backlinks**: Displays all notes linking to current note
- **Handles broken links**: Shows gray dotted underline for missing notes

### Link Types

```css
/* Visual distinction in UI */
.wikilink-note {
  color: #3b82f6;      /* Blue for notes */
  border-bottom: 1px solid #3b82f6;
}

.wikilink-article {
  color: #8b5cf6;      /* Purple for articles */
  border-bottom: 1px solid #8b5cf6;
}

.wikilink-broken {
  color: #9ca3af;      /* Gray for broken */
  border-bottom: 1px dotted #9ca3af;
}
```

### Link Parser Implementation

```python
# backend/link_parser.py
import re

class WikilinkParser:
    """Parse and extract [[note-id]] wikilinks from markdown."""

    WIKILINK_PATTERN = r'\[\[([a-z0-9-]+)\]\]'

    def extract_links(self, content: str) -> list[str]:
        """Extract all [[note-id]] links from content."""
        return re.findall(self.WIKILINK_PATTERN, content)

    def render_links(self, content: str, notes_dict: dict) -> str:
        """Convert [[note-id]] to clickable links in HTML."""
        def replace_link(match):
            note_id = match.group(1)
            if note_id in notes_dict:
                note = notes_dict[note_id]
                title = note.title or note_id
                return f'<a href="/notes/{note_id}" class="wikilink">{title}</a>'
            else:
                # Broken link
                return f'<span class="wikilink-broken">[[{note_id}]]</span>'

        return re.sub(self.WIKILINK_PATTERN, replace_link, content)

    def validate_links(self, content: str, existing_ids: set[str]) -> list[str]:
        """Return list of broken links."""
        links = self.extract_links(content)
        return [link for link in links if link not in existing_ids]
```

## API Endpoints

### Notes CRUD

```bash
# List all notes (persistent + ephemeral for current session)
GET /api/notes

# Create note (requires auth for persistent, session ID for ephemeral)
POST /api/notes
{
  "title": "Database Design Patterns",
  "content": "When designing relationships, consider [[graph-databases]]...",
  "tags": ["database", "architecture"]
}

# Get single note
GET /api/notes/{note_id}

# Update note (admin only for persistent)
PUT /api/notes/{note_id}

# Delete note (admin only for persistent)
DELETE /api/notes/{note_id}
```

### Links & Backlinks

```bash
# Get outbound links from a note
GET /api/notes/{note_id}/links

# Get inbound links (backlinks) to a note
GET /api/notes/{note_id}/backlinks

# Manually add a link
POST /api/notes/{note_id}/links
{
  "target_id": "wise-mountain"
}

# Remove a link
DELETE /api/notes/{note_id}/links/{target_id}
```

### Graph Endpoints

```bash
# Get full graph (all nodes and edges)
GET /api/notes/graph

# Get local subgraph around a note (depth=2)
GET /api/notes/{note_id}/graph
```

### ID Generation

```bash
# Get a random adjective-noun ID
GET /api/notes/generate-id
# Returns: {"id": "curious-elephant"}
```

### Search & AI

```bash
# Semantic search across notes and articles
POST /api/notes/search
{
  "query": "database design",
  "top_k": 5
}

# AI-suggested related notes
POST /api/notes/{note_id}/suggest-links
# Returns: [
#   {
#     "noteId": "wise-mountain",
#     "title": "Graph Database Basics",
#     "reason": "Discusses database design for relationships",
#     "similarity": 0.87
#   }
# ]

# AI-generated summary
GET /api/notes/{note_id}/summary
```

### Admin Controls

```bash
# Authenticate with passkey
POST /api/admin/auth
{
  "passkey": "your-secret-passkey"
}

# Clear all ephemeral notes
DELETE /api/admin/ephemeral

# Get system statistics
GET /api/admin/stats
# Returns: {
#   "ephemeral_count": 42,
#   "ephemeral_memory_mb": 12.5,
#   "persistent_count": 156,
#   "active_sessions": 3
# }
```

## Creating Notes

### Via Web Interface

1. Navigate to `/knowledge-base/notes`
2. Click **"+ New Note"**
3. Choose "Persistent" (requires login) or "Ephemeral"
4. Write content with markdown and wikilinks
5. Add tags (comma-separated)
6. Save

### Via API

```bash
# Create persistent note (with auth)
curl -X POST http://localhost:8000/api/notes \
  -H "Authorization: Bearer YOUR_PASSKEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Database Design Patterns",
    "content": "When designing relationships:\n\n1. [[graph-databases]]\n2. [[relational-models]]\n3. [[document-stores]]",
    "tags": ["database", "architecture"]
  }'

# Create ephemeral note (no auth, with session cookie)
curl -X POST http://localhost:8000/api/notes \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=abc123" \
  -d '{
    "title": "Quick Thought",
    "content": "This is a temporary note for testing.",
    "tags": ["test"]
  }'
```

## Graph Visualization

### Full Graph View

Navigate to `/knowledge-base/notes/graph` to see:
- **Force-directed layout**: Nodes repel, connected nodes attract
- **Color coding**: Your notes vs anonymous notes
- **Interactive**: Click node to navigate, drag to reposition
- **Filters**: By author, tags, date range
- **Zoom/pan**: Mouse wheel to zoom, click-drag to pan

### Local Subgraph

On each note page (`/knowledge-base/notes/{id}`):
- Shows notes within 2 hops (direct + indirect connections)
- Highlights current note
- Click to navigate to connected notes

### Graph Component

```typescript
// frontend/src/components/NoteGraph.tsx
interface GraphNode {
  id: string;           // Note ID
  label: string;        // Title or ID
  author: 'admin' | 'anonymous';
  type: 'note' | 'article';
}

interface GraphEdge {
  source: string;       // Source note ID
  target: string;       // Target note ID
}

// Using react-force-graph or @xyflow/react
```

## AI Features

### Semantic Search

Search across all notes and articles using natural language:

```bash
POST /api/search
{
  "query": "How do I design a database for relationships?",
  "top_k": 5
}

# Returns top 5 most relevant notes/articles with:
# - Relevance score
# - Snippet with highlights
# - Link to full content
```

### Link Suggestions

Get AI-powered suggestions for related notes:

```bash
POST /api/notes/curious-elephant/suggest-links

# Returns:
[
  {
    "noteId": "wise-mountain",
    "title": "Graph Database Basics",
    "reason": "Both discuss database design patterns",
    "similarity": 0.87
  },
  {
    "noteId": "swift-river",
    "title": "Payment Processing",
    "reason": "Shares database architecture concepts",
    "similarity": 0.72
  }
]
```

### Auto-Summaries

Each note gets an AI-generated summary:
- Created automatically when note is saved
- Displayed as tooltip on hover in graph
- Helps understand what a note is about without opening it
- Cached in note metadata

## UI/UX Guidelines

### Articles vs Notes

**Articles** (Long-form):
- Professional, curated content
- Written outside the app, checked into git
- Examples: "SaaS Billing Models", "Engineering Management 1-on-1s"

**Notes** (Atomic):
- Personal knowledge, work-in-progress
- Written in-app with rich editor
- Examples: `curious-elephant`, `wise-mountain`

### Navigation Structure

```
/knowledge-base                       # Landing page
├── /knowledge-base/articles          # Browse articles (grid view)
│   └── /knowledge-base/articles/[slug]  # Single article
│
└── /knowledge-base/notes             # Browse notes (list + graph toggle)
    ├── /knowledge-base/notes/graph   # Graph visualization
    └── /knowledge-base/notes/[id]    # Single note (e.g., curious-elephant)
```

### Note Browser View

**List View** (default):
```
┌─────────────────────────────────────────────────────┐
│  Notes  [List] [Graph]                [+ New Note]  │
├─────────────────────────────────────────────────────┤
│  • curious-elephant                  (you, 2h ago)  │
│    Database design patterns for relationships...    │
│    → 3 links | ← 2 backlinks | #database #patterns │
│                                                     │
│  • wise-mountain                    (anon, 5h ago)  │
│    Graph traversal algorithms and complexity...     │
│    → 1 link  | ← 0 backlinks | #algorithms          │
└─────────────────────────────────────────────────────┘
```

**Graph View**:
```
┌─────────────────────────────────────────────────────┐
│  Notes  [List] [Graph]                [+ New Note]  │
├─────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────┐ │
│  │        ●─────●  curious-elephant               │ │
│  │        │      ╲                                │ │
│  │    wise-   swift-river                        │ │
│  │   mountain    │                                │ │
│  │         ╲    ●─────●                           │ │
│  │          ╲  /    calm-ocean                    │ │
│  │           ●●                                   │ │
│  │        brave-tiger                             │ │
│  └───────────────────────────────────────────────┘ │
│  ● your notes  ○ anonymous notes                    │
└─────────────────────────────────────────────────────┘
```

### Single Note View

```
┌─────────────────────────────────────────────────────┐
│  ← Notes                                [Edit] [⋮]  │
│  curious-elephant                                   │
├─────────────────────────────────────────────────────┤
│  Database Design Patterns                           │
│  by Erik • 2 hours ago • Updated 1 hour ago         │
│  #database #patterns #architecture                  │
├─────────────────────────────────────────────────────┤
│  When designing for relationships, consider:        │
│  1. Graph-based storage ([[wise-mountain]])         │
│  2. Relational with foreign keys                    │
│  3. Document with embedded refs                     │
├─────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌────────────────────────────┐  │
│  │ ← Backlinks  │  │ → Links                    │  │
│  │ • calm-ocean │  │ • wise-mountain            │  │
│  │ • brave-tiger│  │ • saas-billing... (art.)   │  │
│  └──────────────┘  └────────────────────────────┘  │
│                                                     │
│  🤖 AI Suggested Links                              │
│  • quiet-forest - SQL optimization (87%)            │
│  [Add Link]                                         │
└─────────────────────────────────────────────────────┘
```

## Abuse Mitigation

### Rate Limiting

Per-session limits for anonymous users:
- **Create note**: 10/hour
- **Search**: 60/hour
- **AI requests**: 20/hour

No limits for authenticated admin.

### Content Filtering

```python
# Maximum note size
MAX_NOTE_LENGTH = 50000  # ~50KB

# Per-session limits
MAX_NOTES_PER_SESSION = 50
MAX_EPHEMERAL_NOTES = 10000  # Total across all sessions
MAX_EPHEMERAL_MEMORY_MB = 500
```

### Memory Management

Auto-eviction strategy:
1. Remove notes from expired sessions first
2. If still over limit, remove oldest notes
3. Log evictions for monitoring

Admin controls:
```bash
# View stats
GET /api/admin/stats

# Clear all ephemeral notes
DELETE /api/admin/ephemeral

# Clear specific session
DELETE /api/admin/ephemeral/{session_id}
```

## Testing

### Backend Tests

```bash
cd backend
make test-unit         # Unit tests
make test-integration  # Integration tests
make test              # All tests
```

Located in `backend/tests/`:

```python
# tests/unit/test_note_id_generator.py
def test_generate_unique_ids():
    """IDs should not collide."""

def test_collision_handling():
    """Regenerate on collision."""

# tests/unit/test_link_parser.py
def test_extract_wikilinks():
    """Parse [[note-id]] syntax."""

def test_broken_links():
    """Identify non-existent links."""

# tests/integration/test_notes_api.py
def test_create_persistent_note_requires_auth():
    """Anonymous users cannot create persistent notes."""

def test_ephemeral_note_lifecycle():
    """Ephemeral notes expire with session."""

def test_backlinks_updated():
    """Creating link updates backlinks."""
```

### Frontend Tests

```bash
cd frontend
npm test            # Component tests
npm run test:e2e    # E2E tests
```

```typescript
// tests/NoteEditor.test.tsx
test('autocomplete shows matching notes on [[ input')
test('saves note with extracted links')
test('validates links before save')

// tests/NoteGraph.test.tsx
test('renders graph with nodes and edges')
test('clicking node navigates to note')
test('filters graph by author')
```

## Best Practices

### Writing Atomic Notes

1. **One idea per note**: Keep notes focused on a single concept
2. **Use your own words**: Don't just copy-paste, internalize the idea
3. **Link liberally**: Connect related concepts with wikilinks
4. **Add context**: Write enough so you'll understand it later
5. **Use tags sparingly**: Only for broad categories

### Link Strategy

1. **Link as you write**: Add `[[wikilinks]]` while drafting
2. **Follow suggestions**: Check AI link suggestions after saving
3. **Review backlinks**: See what other notes reference this one
4. **Create missing notes**: Broken links are invitations to write new notes

### Organization

1. **Don't over-organize**: Let the graph structure emerge naturally
2. **Use tags for themes**: Broad categories like "database", "architecture"
3. **Leverage search**: Use semantic search to find related notes
4. **Explore the graph**: Visual browsing reveals unexpected connections

### Maintenance

1. **Review regularly**: Revisit old notes to add new connections
2. **Refactor as needed**: Split large notes, merge redundant ones
3. **Clean up broken links**: Either create the missing note or remove the link
4. **Monitor graph health**: Check for isolated clusters or over-connected hubs

## Troubleshooting

### Notes not persisting

1. Verify you're logged in (check for Authorization header)
2. Check Neo4j is running: `docker compose ps`
3. Review backend logs: `docker compose logs backend`
4. Test connection: `curl http://localhost:8000/api/notes`

### Links not working

1. Verify wikilink syntax: `[[note-id]]` (lowercase, hyphens)
2. Check note ID exists: `GET /api/notes/{note-id}`
3. Review link parser logs for parsing errors
4. Test with simple link first: `[[test-note]]`

### Graph not rendering

1. Check browser console for JavaScript errors
2. Verify graph endpoint returns data: `GET /api/notes/graph`
3. Test with smaller dataset first
4. Clear browser cache and reload

### AI features not working

1. Verify Ollama is running: `ollama list`
2. Check model is downloaded: `ollama pull mistral`
3. Test Ollama directly: `ollama run mistral "test"`
4. Review backend logs for connection errors

### Ephemeral notes disappearing

1. Check session cookie is set and valid
2. Verify memory limits not exceeded: `GET /api/admin/stats`
3. Review auto-eviction logs
4. Test with persistent note instead (requires auth)

## Related Documentation

- **[README.md](README.md)** - Knowledge Base overview and architecture
- **[ARTICLES.md](ARTICLES.md)** - Article authoring guide
- **[../SETUP.md](../SETUP.md)** - Environment setup and 1Password
- **[../TESTING.md](../TESTING.md)** - Testing tools and commands
- **[../ROADMAP.md](../ROADMAP.md)** - Future enhancements

---

For general development questions, see [CLAUDE.md](../../CLAUDE.md) and the root [README.md](../../README.md).
