# Zettelkasten Implementation Plan

## Overview

Add a Zettelkasten note-taking system to Mongado's Knowledge Base, supporting atomic notes with bidirectional linking. The system will coexist with long-form markdown articles.

## Goals

1. **Atomic Notes**: Short, single-concept notes created via in-app editor
2. **Bidirectional Linking**: `[[adjective-noun]]` wikilink syntax with automatic backlinks
3. **Graph Visualization**: Interactive graph showing note connections
4. **Hybrid System**: Static markdown articles + database-backed atomic notes
5. **Single Admin**: Only you can create persistent notes (via 1Password auth)
6. **Visitor Demo**: Anonymous users can create ephemeral in-memory notes
7. **AI Integration**: Ollama-powered search, link suggestions, and summaries

## Design Decisions

### Note Identification

**Adjective-Noun IDs**: `curious-elephant`, `wise-mountain`, `swift-river`

- **User-visible**: Delightful, memorable identifiers
- **URL-friendly**: `/notes/curious-elephant`
- **Mutable**: Admin can rename to avoid inappropriate combinations
- **Collision handling**: Auto-regenerate until unique ID found
- **Format**: `{adjective}-{noun}` (lowercase, hyphenated)

### Authentication Model

**Single Admin User** (you):
- Authenticate via 1Password secret (API key or token)
- Create persistent notes (saved to SQLite)
- Full CRUD operations on all notes
- Can manually evict ephemeral notes

**Anonymous Visitors**:
- No authentication required
- Create ephemeral notes (in-memory only)
- Read all notes (persistent + ephemeral)
- Notes expire at end of session
- Author shown as "Anonymous"

### Data Storage

**Persistent Notes** (Admin only):
- SQLite database: `mongado.db`
- Tables: `notes`, `note_links`, `note_metadata`
- Written to disk immediately
- Survives server restarts

**Ephemeral Notes** (Visitors):
- In-memory dictionary with session IDs
- TTL: End of browser session (session cookie)
- Memory limit: 500MB total for all ephemeral notes
- Auto-evict oldest when limit reached
- Manual eviction via admin endpoint

**Static Articles** (Unchanged):
- Markdown files in `backend/static/articles/`
- Can reference Zettelkasten notes via `[[note-id]]`
- Notes can link back to articles

## Architecture

### Database Schema (SQLite)

```sql
-- Atomic notes
CREATE TABLE notes (
    id TEXT PRIMARY KEY,              -- e.g., "curious-elephant"
    title TEXT,                       -- Optional human title
    content TEXT NOT NULL,            -- Markdown content
    author TEXT DEFAULT 'admin',      -- 'admin' or 'anonymous'
    is_ephemeral BOOLEAN DEFAULT 0,   -- 0 = persistent, 1 = ephemeral
    session_id TEXT,                  -- For ephemeral notes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tags TEXT,                        -- JSON array: ["tag1", "tag2"]
    metadata TEXT                     -- JSON: {views, ai_summary, etc.}
);

-- Bidirectional links between notes
CREATE TABLE note_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,          -- Note containing the link
    target_id TEXT NOT NULL,          -- Note being linked to
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES notes(id) ON DELETE CASCADE,
    UNIQUE(source_id, target_id)      -- Prevent duplicate links
);

-- Indexes for performance
CREATE INDEX idx_notes_author ON notes(author);
CREATE INDEX idx_notes_ephemeral ON notes(is_ephemeral);
CREATE INDEX idx_notes_created ON notes(created_at DESC);
CREATE INDEX idx_links_source ON note_links(source_id);
CREATE INDEX idx_links_target ON note_links(target_id);
```

### In-Memory Ephemeral Storage

```python
# backend/ephemeral_notes.py
from typing import Dict, List
from dataclasses import dataclass
import time

@dataclass
class EphemeralNote:
    id: str
    title: str
    content: str
    session_id: str
    created_at: float
    links: List[str]

class EphemeralNotesStore:
    """In-memory storage for visitor notes."""

    def __init__(self, max_memory_mb: int = 500):
        self.notes: Dict[str, EphemeralNote] = {}
        self.sessions: Dict[str, List[str]] = {}  # session_id -> [note_ids]
        self.max_memory_bytes = max_memory_mb * 1024 * 1024

    def add_note(self, note: EphemeralNote) -> bool:
        """Add note if memory limit not exceeded."""
        pass

    def get_memory_usage(self) -> int:
        """Calculate current memory usage."""
        pass

    def evict_oldest(self) -> None:
        """Remove oldest notes to free memory."""
        pass

    def clear_session(self, session_id: str) -> None:
        """Remove all notes from a session."""
        pass

    def clear_all(self) -> None:
        """Admin function: clear all ephemeral notes."""
        pass
```

### Adjective-Noun ID Generator

```python
# backend/note_id_generator.py
import random
from pathlib import Path

class NoteIDGenerator:
    """Generate memorable adjective-noun note IDs."""

    def __init__(self):
        self.adjectives = self._load_words("adjectives.txt")
        self.nouns = self._load_words("nouns.txt")

    def _load_words(self, filename: str) -> List[str]:
        """Load word list from file."""
        path = Path(__file__).parent / "data" / "wordlists" / filename
        with open(path) as f:
            return [line.strip().lower() for line in f if line.strip()]

    def generate(self, existing_ids: Set[str]) -> str:
        """Generate unique ID, regenerating on collision."""
        max_attempts = 100
        for _ in range(max_attempts):
            adj = random.choice(self.adjectives)
            noun = random.choice(self.nouns)
            note_id = f"{adj}-{noun}"

            if note_id not in existing_ids:
                return note_id

        # Fallback: append number
        return f"{adj}-{noun}-{random.randint(1000, 9999)}"

    def is_valid(self, note_id: str) -> bool:
        """Validate ID format."""
        parts = note_id.split("-")
        if len(parts) < 2:
            return False
        adj, noun = parts[0], parts[1]
        return adj in self.adjectives and noun in self.nouns
```

**Word Lists** (curated, ~500 each):
- `backend/data/wordlists/adjectives.txt` - Positive, professional adjectives
- `backend/data/wordlists/nouns.txt` - Concrete, appropriate nouns
- Filter out: profanity, brand names, potentially offensive combinations

### API Endpoints

```python
# New endpoints in backend/main.py

# === Notes CRUD ===
GET    /api/notes                      # List all notes (persistent + ephemeral for session)
POST   /api/notes                      # Create note (requires auth for persistent)
GET    /api/notes/{note_id}            # Get single note
PUT    /api/notes/{note_id}            # Update note (admin only for persistent)
DELETE /api/notes/{note_id}            # Delete note (admin only for persistent)

# === Links ===
GET    /api/notes/{note_id}/links      # Get outbound links
GET    /api/notes/{note_id}/backlinks  # Get inbound links (who links to this)
POST   /api/notes/{note_id}/links      # Manually add link
DELETE /api/notes/{note_id}/links/{target_id}  # Remove link

# === Graph ===
GET    /api/notes/graph                # Get full graph (nodes + edges)
GET    /api/notes/{note_id}/graph      # Get subgraph around note (depth=2)

# === ID Generation ===
GET    /api/notes/generate-id          # Get random adjective-noun ID

# === Search & AI ===
POST   /api/notes/search               # Semantic search with Ollama
POST   /api/notes/{note_id}/suggest-links  # AI-suggested related notes
GET    /api/notes/{note_id}/summary    # AI-generated summary

# === Admin ===
POST   /api/admin/auth                 # Authenticate with 1Password key
DELETE /api/admin/ephemeral            # Clear all ephemeral notes
GET    /api/admin/stats                # Memory usage, note counts
```

### Authentication Middleware

**Simple Passkey Approach:**

```python
# backend/config.py
class Settings(BaseSettings):
    """Application settings."""
    admin_passkey: str = ""  # Load from .env or 1Password vault

# backend/auth.py
from fastapi import HTTPException, Header, Depends
from config import get_settings

settings = get_settings()

def verify_admin(authorization: str = Header(None)) -> bool:
    """Verify admin passkey from Authorization header.

    Expects: "Bearer your-secret-passkey"

    Usage:
    - Store passkey in 1Password vault
    - Copy to frontend localStorage on login
    - Include in Authorization header for admin requests
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

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
    pass
```

**Frontend Login:**

```typescript
// frontend/src/lib/auth.ts
export const login = (passkey: string) => {
  localStorage.setItem('adminPasskey', passkey);
};

export const logout = () => {
  localStorage.removeItem('adminPasskey');
};

export const isAuthenticated = () => {
  return !!localStorage.getItem('adminPasskey');
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

**Benefits:**
- Simple to implement and understand
- No API dependencies
- Store passkey in 1Password vault
- Copy-paste on login (or use 1Password browser extension)
- Stateless (no sessions to manage)

### Link Parsing & Extraction

```python
# backend/link_parser.py
import re

class WikilinkParser:
    """Parse and extract [[note-id]] wikilinks from markdown."""

    WIKILINK_PATTERN = r'\[\[([a-z0-9-]+)\]\]'

    def extract_links(self, content: str) -> List[str]:
        """Extract all [[note-id]] links from content."""
        return re.findall(self.WIKILINK_PATTERN, content)

    def render_links(self, content: str, notes_dict: Dict[str, Note]) -> str:
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

    def validate_links(self, content: str, existing_ids: Set[str]) -> List[str]:
        """Return list of broken links."""
        links = self.extract_links(content)
        return [link for link in links if link not in existing_ids]
```

## UI/UX: Articles vs Notes

### Content Type Distinction

**Articles** (Static Markdown):
- Long-form, curated content
- Written outside the app, checked into git
- Professional, polished essays
- Examples: "SaaS Billing Models", "Engineering Management 1-on-1s"

**Notes** (Zettelkasten):
- Atomic, single-concept ideas
- Written in-app with rich editor
- Personal knowledge, work-in-progress thoughts
- Examples: "curious-elephant", "wise-mountain"

### Navigation Structure (Recommended)

```
/knowledge-base                    Landing page (search + links to both)
├── /knowledge-base/articles       Browse articles (grid view)
│   └── /knowledge-base/articles/[slug]  Single article
│
└── /knowledge-base/notes          Browse notes (list + graph toggle)
    ├── /knowledge-base/notes/graph       Graph visualization
    └── /knowledge-base/notes/[id]        Single note (e.g., curious-elephant)
```

**Why separate routes:**
- Clear mental model (Articles = essays, Notes = thoughts)
- Different UX patterns (Articles in grid, Notes in graph/list)
- Can still cross-link with [[wikilinks]]
- Future: unified search across both

### Landing Page Design

```
┌─────────────────────────────────────────────────────────┐
│  Knowledge Base                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🔍 Search Everything                                   │
│  [Search articles and notes........................]    │
│                                                         │
│  ┌──────────────────────┐  ┌──────────────────────┐   │
│  │ 📚 Articles          │  │ 🔗 Notes             │   │
│  │                      │  │                      │   │
│  │ Long-form curated    │  │ Atomic ideas,        │   │
│  │ content              │  │ connected            │   │
│  │                      │  │                      │   │
│  │ [Browse →]           │  │ [Browse →] [Graph →] │   │
│  └──────────────────────┘  └──────────────────────┘   │
│                                                         │
│  Recent Activity                                        │
│  • Updated: wise-mountain (note, 2h ago)                │
│  • Created: curious-elephant (note, 5h ago)             │
│  • Viewed: SaaS Billing Models (article, 1d ago)        │
└─────────────────────────────────────────────────────────┘
```

### Articles Page (/knowledge-base/articles)

```
┌─────────────────────────────────────────────────────────┐
│  ← Knowledge Base                                       │
│  Articles                                               │
├─────────────────────────────────────────────────────────┤
│  [Search...] [Tag: All ▼] [Sort: Recent ▼]             │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ 📄           │  │ 📄           │  │ 📄           │ │
│  │ SaaS Billing │  │ Engineering  │  │ SRE Golden   │ │
│  │ Models       │  │ Management   │  │ Signals      │ │
│  │              │  │              │  │              │ │
│  │ #saas #$     │  │ #management  │  │ #sre #ops    │ │
│  │ 2 weeks ago  │  │ 1 month ago  │  │ 3 weeks ago  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Notes Page (/knowledge-base/notes)

**List View (Default):**
```
┌─────────────────────────────────────────────────────────┐
│  ← Knowledge Base                                       │
│  Notes  [List] [Graph]                [+ New Note]      │
├─────────────────────────────────────────────────────────┤
│  [Search...] [Author: All ▼] [Sort: Recent ▼]          │
├─────────────────────────────────────────────────────────┤
│  • curious-elephant                  (you, 2h ago)      │
│    Database design patterns for relationships...        │
│    → 3 links | ← 2 backlinks | #database #patterns     │
│                                                         │
│  • wise-mountain                    (anon, 5h ago)      │
│    Graph traversal algorithms and complexity...         │
│    → 1 link  | ← 0 backlinks | #algorithms              │
│                                                         │
│  • swift-river                       (you, 1d ago)      │
│    Payment processing implementation notes...           │
│    → 5 links | ← 3 backlinks | #payments #api           │
└─────────────────────────────────────────────────────────┘
```

**Graph View:**
```
┌─────────────────────────────────────────────────────────┐
│  ← Knowledge Base                                       │
│  Notes  [List] [Graph]                [+ New Note]      │
├─────────────────────────────────────────────────────────┤
│  [Search...] [Filter ▼]                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │        ●─────●  curious-elephant                 │   │
│  │        │      ╲                                  │   │
│  │    wise-   swift-river                          │   │
│  │   mountain    │                                  │   │
│  │         ╲    ●─────●                             │   │
│  │          ╲  /    calm-ocean                      │   │
│  │           ●●                                     │   │
│  │        brave-tiger                               │   │
│  │                                                  │   │
│  │  [Zoom -/+] [Reset View]                        │   │
│  └─────────────────────────────────────────────────┘   │
│  ● your notes  ○ anonymous notes                        │
└─────────────────────────────────────────────────────────┘
```

### Single Note View (/knowledge-base/notes/curious-elephant)

```
┌─────────────────────────────────────────────────────────┐
│  ← Notes                                    [Edit] [⋮]  │
│  curious-elephant                                       │
├─────────────────────────────────────────────────────────┤
│  Database Design Patterns                               │
│  by Erik • 2 hours ago • Updated 1 hour ago             │
│  #database #patterns #architecture                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  When designing for relationships, consider:            │
│                                                         │
│  1. Graph-based storage ([[wise-mountain]])             │
│  2. Relational with foreign keys                        │
│  3. Document with embedded refs                         │
│                                                         │
│  For billing context, see [[swift-river]].              │
│  Also relevant: [[saas-billing-models]] (article)       │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  ┌────────────────────┐  ┌──────────────────────────┐  │
│  │ ← Backlinks (2)    │  │ → Links (3)              │  │
│  │                    │  │                          │  │
│  │ • calm-ocean       │  │ • wise-mountain          │  │
│  │   "This relates    │  │ • swift-river            │  │
│  │   to..."           │  │ • saas-billing... (art.) │  │
│  │                    │  │                          │  │
│  │ • brave-tiger      │  │                          │  │
│  │   "Building on..." │  │                          │  │
│  └────────────────────┘  └──────────────────────────┘  │
│                                                         │
│  🤖 AI Suggested Links                                  │
│  • quiet-forest - SQL optimization (87% similar)        │
│  • ancient-tree - Database indexing (82% similar)       │
│  [Add Link]                                             │
├─────────────────────────────────────────────────────────┤
│  📊 Local Graph                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │      ●───curious-elephant───●                    │   │
│  │     /         │              ╲                   │   │
│  │    ●          ●               ●                  │   │
│  │  wise-    swift-river     calm-ocean             │   │
│  │ mountain                                         │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Cross-Linking Between Articles & Notes

**Wikilink Syntax:**
```markdown
[[curious-elephant]]      → Link to note
[[saas-billing-models]]   → Link to article
```

**Link Rendering:**
- Notes: Show note ID + title on hover
- Articles: Show article title on hover
- Both: Click to navigate to content
- Broken links: Gray with dotted underline

**Visual Distinction:**
```css
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

### Mobile Considerations

- **Graph view**: Simplified on mobile (fewer nodes, pinch-to-zoom)
- **Note list**: Full-width cards, swipe for actions
- **Single note**: Collapsible backlinks/suggestions panels
- **Navigation**: Bottom tab bar (Home | Articles | Notes | Search)

## Frontend Components

### Note Editor with Link Autocomplete

```typescript
// frontend/src/components/NoteEditor.tsx
interface NoteEditorProps {
  initialContent?: string;
  onSave: (content: string, links: string[]) => void;
}

// Features:
// - Rich text editor (reuse existing TipTap)
// - Autocomplete for [[ typing (shows note ID + title)
// - Real-time link extraction
// - Show AI-suggested related notes
// - Preview mode with rendered wikilinks
```

### Graph Visualization

```typescript
// frontend/src/components/NoteGraph.tsx
// Using: react-force-graph or @xyflow/react

interface GraphNode {
  id: string;           // Note ID
  label: string;        // Title or ID
  author: 'admin' | 'anonymous';
  type: 'note' | 'article';
}

interface GraphEdge {
  source: string;
  target: string;
}

// Features:
// - Interactive force-directed graph
// - Click node to open note
// - Highlight connected nodes on hover
// - Filter by author/tags
// - Zoom/pan controls
// - Mini-map for large graphs
```

### Backlinks Panel

```typescript
// frontend/src/components/BacklinksPanel.tsx
// Shows notes that link to current note

interface Backlink {
  noteId: string;
  title: string;
  excerpt: string;      // Context around the link
  createdAt: string;
}

// Display as sidebar or bottom panel
```

### Note Browser

```typescript
// frontend/src/app/notes/page.tsx
// Main notes listing page

// Features:
// - Grid or list view
// - Filter by author (admin/anonymous)
// - Search with Ollama
// - Sort by date, links, relevance
// - Quick preview on hover
```

### Single Note View

```typescript
// frontend/src/app/notes/[noteId]/page.tsx

// Features:
// - Rendered markdown with clickable wikilinks
// - Edit button (admin only for persistent)
// - Backlinks panel
// - Related notes (AI-suggested)
// - Graph visualization (local subgraph)
// - Metadata (created, modified, author, tags)
```

## Abuse Mitigation

### Rate Limiting

```python
# backend/rate_limiter.py
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

# Per-session limits for anonymous users
LIMITS = {
    "create_note": "10/hour",      # Max 10 notes per hour
    "search": "60/hour",           # Max 60 searches per hour
    "ai_suggest": "20/hour",       # Max 20 AI requests per hour
}

# No limits for authenticated admin
```

### Content Filtering

```python
# backend/content_filter.py

class ContentFilter:
    """Filter malicious or inappropriate content."""

    def validate_note(self, content: str) -> tuple[bool, str]:
        """
        Validate note content.

        Returns: (is_valid, error_message)
        """
        # Max length (prevent abuse)
        if len(content) > 50000:  # ~50KB
            return False, "Note too long (max 50KB)"

        # Check for spam patterns
        if self._is_spam(content):
            return False, "Content appears to be spam"

        # Basic profanity filter (optional)
        if self._contains_profanity(content):
            return False, "Content contains inappropriate language"

        return True, ""

    def _is_spam(self, content: str) -> bool:
        """Detect spam patterns."""
        # Repeated URLs
        # Excessive capitalization
        # Known spam phrases
        pass
```

### Memory Management

```python
# Ephemeral notes limits
MAX_EPHEMERAL_NOTES = 10000        # Total across all sessions
MAX_NOTES_PER_SESSION = 50         # Per visitor
MAX_EPHEMERAL_MEMORY_MB = 500      # Total memory cap

# Auto-eviction strategy
# 1. Remove notes from expired sessions first
# 2. If still over limit, remove oldest notes
# 3. Log evictions for monitoring
```

### Admin Controls

```python
# Admin panel endpoints
GET    /api/admin/ephemeral/stats     # Count, memory usage
DELETE /api/admin/ephemeral            # Clear all
DELETE /api/admin/ephemeral/{session_id}  # Clear specific session
GET    /api/admin/sessions             # List active sessions
```

## AI Integration (Ollama)

### Semantic Search

```python
# Enhanced version of existing search
# - Search across notes + articles
# - Return relevance scores
# - Include snippets with highlights
```

### Link Suggestions

```python
@app.post("/api/notes/{note_id}/suggest-links")
def suggest_links(note_id: str) -> List[SuggestedLink]:
    """
    AI-powered link suggestions.

    1. Get note content
    2. Generate embedding with Ollama
    3. Find similar notes (cosine similarity)
    4. Return top 5 suggestions with reasons
    """
    pass

# Response:
# [
#   {
#     "noteId": "wise-mountain",
#     "title": "Graph Database Basics",
#     "reason": "Discusses database design for relationships",
#     "similarity": 0.87
#   }
# ]
```

### Auto-Summaries

```python
# Generate summary on note creation (async)
# Store in note metadata
# Display as tooltip on hover in graph
# Helps with ID-based linking (see what note is about)
```

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)

1. **Database Setup**
   - SQLite schema creation
   - Migration scripts
   - Database connection pooling

2. **ID Generator**
   - Curate word lists (500 adjectives, 500 nouns)
   - Implement generator with collision handling
   - Add validation

3. **Basic CRUD**
   - Create persistent notes (admin only)
   - Read notes
   - Update notes
   - Delete notes

4. **Link Parser**
   - Extract `[[note-id]]` from markdown
   - Store links in `note_links` table
   - Query backlinks

### Phase 2: Authentication & Ephemeral Notes (Week 2-3)

1. **1Password Auth**
   - Admin API key storage
   - Authentication middleware
   - Protected endpoints

2. **Ephemeral Storage**
   - In-memory store with session tracking
   - Memory limits and eviction
   - Session management

3. **Unified API**
   - Merge persistent + ephemeral in responses
   - Author attribution
   - Filter by author

### Phase 3: Frontend (Week 3-5)

1. **Note Editor**
   - Markdown editor with link autocomplete
   - Real-time link validation
   - Save with automatic link extraction

2. **Note Viewer**
   - Rendered markdown with clickable links
   - Backlinks panel
   - Edit mode (admin only)

3. **Note Browser**
   - List/grid view
   - Search and filter
   - Sort options

### Phase 4: Graph Visualization (Week 5-6)

1. **Graph API**
   - Full graph endpoint
   - Subgraph around note
   - Graph statistics

2. **Graph Component**
   - Interactive force-directed layout
   - Click to navigate
   - Hover previews
   - Filter controls

### Phase 5: AI Features (Week 6-7)

1. **Enhanced Search**
   - Semantic search with Ollama
   - Relevance ranking
   - Snippet highlights

2. **Link Suggestions**
   - Related notes based on content
   - Similarity scores
   - One-click add link

3. **Auto-Summaries**
   - Generate on note creation
   - Display in graph tooltips
   - Help with ID-based navigation

### Phase 6: Polish & Optimization (Week 7-8)

1. **Abuse Mitigation**
   - Rate limiting
   - Content filtering
   - Memory monitoring

2. **Admin Panel**
   - Ephemeral notes management
   - System statistics
   - Manual eviction

3. **Performance**
   - Query optimization
   - Caching strategies
   - Graph rendering for large datasets

4. **Documentation**
   - User guide for Zettelkasten workflow
   - API documentation
   - Admin guide

## Future Enhancements (Post-MVP)

### Database Migration

```markdown
# TODO: Evaluate PostgreSQL vs Neo4j

**PostgreSQL Benefits:**
- Mature, well-understood
- JSON types for flexible metadata
- Recursive CTEs for graph queries
- Already in ecosystem

**Neo4j Benefits:**
- Native graph database
- Optimized for traversals
- Cypher query language (intuitive for graphs)
- Better performance for deep relationship queries

**Decision Factors:**
- Graph size (how many notes?)
- Query patterns (deep traversals vs simple lookups?)
- Operational complexity
- Cost

**Recommendation:** Start with PostgreSQL, migrate to Neo4j if:
- >10,000 notes with heavy linking
- Complex graph traversal queries
- Performance becomes bottleneck
```

### Advanced Features

1. **Note Templates**
   - Pre-defined structures for common note types
   - Person, Book, Concept, Project templates

2. **Bi-temporal Versioning**
   - Track note history
   - Diff views
   - Restore previous versions

3. **Collaborative Features**
   - Share notes publicly (opt-in)
   - Comments on notes
   - Suggestion mode

4. **Export/Import**
   - Export to Obsidian vault
   - Import from Roam/Notion
   - Backup as markdown files

5. **Mobile App**
   - Quick capture
   - Offline support
   - Sync via API

6. **Advanced AI**
   - Auto-tag notes
   - Cluster related notes
   - Suggest note structure
   - Question-answering over full graph

## Testing Strategy

### Backend Tests

```python
# tests/unit/test_note_id_generator.py
def test_generate_unique_ids():
    """IDs should not collide."""
    pass

def test_collision_handling():
    """Regenerate on collision."""
    pass

# tests/unit/test_link_parser.py
def test_extract_wikilinks():
    """Parse [[note-id]] syntax."""
    pass

def test_broken_links():
    """Identify non-existent links."""
    pass

# tests/integration/test_notes_api.py
def test_create_persistent_note_requires_auth():
    """Anonymous users cannot create persistent notes."""
    pass

def test_ephemeral_note_lifecycle():
    """Ephemeral notes expire with session."""
    pass

def test_backlinks_updated():
    """Creating link updates backlinks."""
    pass
```

### Frontend Tests

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

## Rollout Plan

### Local Development

1. Implement on feature branch
2. SQLite in `backend/mongado.db`
3. Seed with sample notes
4. Test linking, graph, AI features

### Staging

1. Deploy to staging environment
2. Test with larger dataset
3. Load test ephemeral notes
4. Verify memory limits

### Production

1. Backup existing database
2. Run migrations
3. Deploy backend + frontend
4. Monitor memory usage
5. Gradual rollout of AI features (cost monitoring)

## Success Metrics

1. **Notes Created**: Track admin note creation rate
2. **Links Formed**: Average links per note
3. **Graph Growth**: Nodes and edges over time
4. **AI Usage**: Search queries, link suggestions used
5. **Visitor Engagement**: Ephemeral notes created
6. **Performance**: API response times, graph render time
7. **Abuse Prevention**: Rate limit hits, evictions

## Open Questions

1. **Word List Source**: Use existing lists or curate manually?
2. **Link by ID vs Title**: Start with ID, add title alias later?
3. **Graph Layout**: Force-directed, hierarchical, or circular?
4. **Mobile Experience**: Full graph on mobile or simplified view?
5. **Public Sharing**: Allow sharing individual notes publicly?

---

**Next Steps:**
1. Review and approve plan
2. Create word lists for ID generation
3. Set up SQLite schema
4. Implement Phase 1: Core Infrastructure
