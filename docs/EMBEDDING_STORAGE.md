# Persistent Embedding Storage Design

## Overview

This document describes the implementation of persistent embedding storage in Neo4j to optimize semantic search performance.

## Problem Statement

**Current State:**
- Semantic search generates embeddings for ALL documents on every search
- 12 articles = ~2 minutes for first search (1 query + 12 document embeddings × ~10s each)
- Subsequent searches use in-memory cache (faster but lost on restart)
- Does NOT scale: 100 articles = ~17 minutes per search
- Notes are not included in semantic search

**Goal:**
- Semantic search in ~5-10 seconds regardless of corpus size
- Support both Articles and Notes in semantic search
- Persist embeddings across restarts
- Pre-compute embeddings on startup (acceptable delay)

## Architecture Design

### Data Model

#### Article Nodes (NEW)
```cypher
CREATE (a:Article {
    id: string,              // Unique article ID (slug)
    title: string,           // Article title
    content: string,         // Full markdown content
    created_at: float,       // Unix timestamp
    updated_at: float,       // Unix timestamp
    embedding: [float],      // 768-dimensional vector (nomic-embed-text)
    embedding_model: string, // Model used (e.g., "nomic-embed-text")
    embedding_version: int,  // Version for cache invalidation
    content_hash: string     // SHA256 hash for change detection
})
```

#### Note Nodes (EXTENDED)
```cypher
// Existing Note properties + new embedding fields:
(n:Note {
    // ... existing fields ...
    embedding: [float],      // 768-dimensional vector
    embedding_model: string, // Model used
    embedding_version: int,  // Version for cache invalidation
    content_hash: string     // SHA256 hash for change detection
})
```

### Embedding Lifecycle

#### 1. Startup Process
```
Backend starts
  ↓
Load static articles from markdown files
  ↓
Sync articles to Neo4j (upsert based on content_hash)
  ↓
Check which articles/notes lack embeddings or have stale embeddings
  ↓
Generate missing embeddings (can be parallelized in future)
  ↓
Store embeddings in Neo4j
  ↓
Server ready (total time: ~2-3 min first run, ~5s subsequent)
```

#### 2. Semantic Search Process
```
User searches "billing"
  ↓
Generate query embedding (~5s)
  ↓
Fetch all article/note embeddings from Neo4j (~instant)
  ↓
Compute cosine similarities in Python (~instant)
  ↓
Return top-k results
  ↓
Total: ~5-10 seconds regardless of corpus size!
```

#### 3. Content Updates
```
Article file modified → content_hash changes → embedding invalidated
Note updated via API → content_hash changes → embedding invalidated
Next search → regenerates missing embeddings OR
Background job → async regeneration (future enhancement)
```

## Implementation Plan

### Phase 1: Neo4j Schema & Storage ✅ COMPLETE
- [x] Extend `neo4j_adapter.py` with Article node support
- [x] Add embedding storage methods
- [x] Add content hash tracking
- [x] Create indexes for efficient queries

### Phase 2: Embedding Sync Service ✅ COMPLETE
- [x] Create `embedding_sync.py` service
- [x] Sync static articles to Neo4j on startup
- [x] Detect missing/stale embeddings
- [x] Generate and store embeddings
- [x] Progress logging for visibility

### Phase 3: Update Semantic Search ✅ COMPLETE
- [x] Created `semantic_search_with_precomputed_embeddings()` method
- [x] Updated `/api/search` endpoint to fetch embeddings from Neo4j
- [x] Added fallback to on-demand generation if Neo4j unavailable
- [x] Improved logging for visibility

### Phase 4: Testing & Optimization 🔄 IN PROGRESS
- [ ] Test with 12 articles (baseline)
- [ ] Verify ~5-10s search times
- [ ] Test with notes included
- [ ] Monitor startup time
- [ ] Add metrics/logging

## Performance Targets

| Metric | Current | Target | Achieved |
|--------|---------|--------|----------|
| First search (12 articles) | ~120s | ~10s | TBD |
| Subsequent searches | ~10s | ~10s | TBD |
| Startup (cold) | ~5s | ~180s | TBD |
| Startup (warm) | ~5s | ~10s | TBD |
| Search with 100 articles | ~1000s | ~10s | TBD |

## Cache Invalidation Strategy

**Embedding Version:** Global version counter incremented when:
- Ollama model changes
- Embedding generation logic changes
- Manual cache clear requested

**Content Hash:** Per-document hash to detect content changes

**Invalidation Logic:**
```python
needs_embedding = (
    not node.embedding or
    node.embedding_model != current_model or
    node.embedding_version < current_version or
    node.content_hash != calculate_hash(node.content)
)
```

## Future Enhancements

1. **Parallel Embedding Generation** - Use asyncio/threads for faster startup
2. **Background Sync** - Regenerate embeddings async without blocking search
3. **Vector Index** - Use Neo4j vector index for native similarity search (requires Neo4j 5.11+)
4. **Incremental Updates** - Only process changed files on restart
5. **GPU Support** - 10-50x speedup when GPU available

## Files Modified

- `backend/neo4j_adapter.py` - Add Article nodes, embedding storage
- `backend/embedding_sync.py` - NEW: Startup sync service
- `backend/ollama_client.py` - Update semantic_search to accept embeddings
- `backend/main.py` - Update search endpoint, add startup hook
- `backend/config.py` - Add embedding version config

## Migration Notes

**Breaking Changes:** None - graceful fallback to in-memory cache if Neo4j unavailable

**Data Migration:** None - Articles created on first startup, Notes extended with new properties

**Rollback:** Remove embedding properties from nodes, system falls back to in-memory cache

## Testing Checklist

- [ ] Startup sync creates Article nodes
- [ ] Embeddings persisted correctly (768 dimensions)
- [ ] Content hash detects changes
- [ ] Search uses stored embeddings
- [ ] Search performance ~5-10s
- [ ] Works without Neo4j (fallback mode)
- [ ] Notes included in semantic search

## Progress Log

**2025-10-24 - Initial Implementation COMPLETE:**

**Phase 1 - Schema & Storage:**
- Extended Neo4j adapter with Article nodes
- Added `upsert_article()`, `get_article()`, `get_all_articles()`
- Added embedding storage: `store_embedding()`, `get_embedding()`, `get_all_embeddings()`
- Created schema with constraints and indexes for Articles
- File: `backend/neo4j_adapter.py` (added ~240 lines)

**Phase 2 - Embedding Sync:**
- Created embedding sync service with startup integration
- Syncs static articles to Neo4j on startup
- Detects missing/stale embeddings via content_hash
- Generates embeddings with progress logging
- File: `backend/embedding_sync.py` (new file, ~240 lines)
- Integration: `backend/main.py` calls `sync_embeddings_on_startup()`

**Phase 3 - Fast Semantic Search:**
- Created `semantic_search_with_precomputed_embeddings()` in ollama_client
- Updated `/api/search` to fetch embeddings from Neo4j
- Graceful fallback to on-demand generation if Neo4j unavailable
- Improved logging throughout search pipeline
- Files modified: `backend/ollama_client.py`, `backend/main.py`

**Phase 4 - Auto-Reload in Development:**
- Updated Dockerfile to watch `.md` files for hot reload
- When article added/modified, backend auto-restarts and syncs
- File: `backend/Dockerfile` (line 37)

## How to Test

### Step 1: Restart the Backend
```bash
docker compose restart backend
```

Watch for startup logs showing:
```
Starting embedding sync on startup...
Syncing 12 articles to Neo4j...
Checking articles for missing embeddings...
  [1/12] Generating embedding for article: Building a Modern Billing System...
  [2/12] Generating embedding for article: ...
Embedding sync complete: 12 generated, 0 cached
```

First startup: ~2-3 minutes (generates all embeddings)
Subsequent restarts: ~5-10 seconds (embeddings cached in Neo4j)

### Step 2: Test Semantic Search
1. Open browser to `http://localhost:3000/knowledge-base`
2. Wait for Ollama warmup (~45s)
3. Check "Use AI semantic search"
4. Search for "billing"
5. Observe: **~5-10 second response time** (vs ~120s before!)

### Step 3: Verify Logs
Backend logs should show:
```
Search request received: query=billing, semantic=True, limit=5
Using semantic search via Ollama (corpus size: 12)
Using fast semantic search with precomputed embeddings from Neo4j
Fetched 12 precomputed embeddings from Neo4j
Matched 12 documents with embeddings
Starting semantic search with precomputed embeddings: query='billing', corpus_size=12
Generating embedding for query...
Query embedding generated successfully
Computing similarities with 12 precomputed embeddings...
Semantic search complete: returning 5 results
Top result: 'Building a Modern Billing System...' (score: 0.842)
Fast semantic search complete: 5 results in 7.23s
```

### Step 4: Test Auto-Reload (Dev Mode)
1. Add a new article to `backend/static/articles/test-article.md`
2. Watch backend logs - should auto-restart
3. New article synced to Neo4j
4. Embedding generated on startup
5. Article now searchable!

## Next Steps

1. **Verify performance** - Confirm ~5-10s search times
2. **Test with Notes** - Add some notes and verify they're included in search
3. **Production optimization** - Consider parallel embedding generation for faster startup
4. **Monitoring** - Add metrics for embedding cache hit rates

---

*Last updated: 2025-10-24 - Implementation Complete, Ready for Testing*
