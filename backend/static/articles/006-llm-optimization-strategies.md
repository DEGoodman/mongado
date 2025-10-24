---
id: 6
title: "LLM Performance Optimization: From Naive to Production"
tags: ["AI", "Performance", "Architecture"]
created_at: "2025-10-24T00:00:00"
---

## Intro

Building AI features with local LLMs is appealing - no API costs, full data control, simple architecture. But naive implementations hit performance walls fast. A single semantic search taking 30+ seconds makes features unusable. This article documents the progression from naive to production-ready LLM integration, with concrete performance numbers and tradeoffs at each level.

These lessons come from building Mongado's knowledge base with local Ollama embeddings. We went from ~30 second searches to sub-6 second searches by understanding the bottlenecks and applying targeted optimizations.

## The Performance Problem

**Naive implementation**: Generate embeddings on every search request
**Result**: 15-30+ seconds per search
**Why it fails**: Embedding generation dominates request time. For a corpus of 40 documents (12 articles + 28 notes), you're generating 41 embeddings per search - one for the query plus one for each document.

This isn't a "nice-to-have" optimization. Users won't wait 30 seconds. The feature is effectively broken.

## Optimization Levels

Each level builds on the previous, trading implementation complexity for performance gains. Choose the simplest approach that meets your requirements.

### Level 1: In-Memory Caching (~50% faster)

**Approach**: Cache embeddings in RAM during application lifetime

**Implementation**:
```python
# Simple dictionary cache with content hash as key
embedding_cache: dict[str, list[float]] = {}

def generate_embedding(text: str) -> list[float]:
    content_hash = hashlib.sha256(text.encode()).hexdigest()
    if content_hash in embedding_cache:
        return embedding_cache[content_hash]

    embedding = ollama_client.generate(text)
    embedding_cache[content_hash] = embedding
    return embedding
```

**Performance**: 15-20 seconds (first search), 8-12 seconds (subsequent)
**Tradeoffs**:
- ✅ Simple to implement (< 10 lines)
- ✅ Works for static content
- ❌ Cache lost on restart
- ❌ Doesn't scale to large corpora
- ❌ No benefit for first search

**When to use**: Small, mostly-static corpus (< 100 documents), infrequent deploys

### Level 2: Persistent Storage (~80% faster)

**Approach**: Store embeddings in database, regenerate only when content changes

**Implementation**:
```python
# Store with content hash for change detection
def get_or_generate_embedding(doc_id: str, content: str) -> list[float]:
    content_hash = calculate_content_hash(content)

    # Check if we have a valid embedding
    stored = db.get_embedding(doc_id)
    if stored and stored['content_hash'] == content_hash:
        return stored['embedding']

    # Content changed or no embedding exists - generate new one
    embedding = ollama_client.generate(content)
    db.store_embedding(doc_id, embedding, content_hash)
    return embedding
```

**Performance**: 15-20 seconds (first run), 5-6 seconds (production)
**Tradeoffs**:
- ✅ Survives restarts
- ✅ Scales to thousands of documents
- ✅ Only regenerate when content actually changes
- ❌ Requires database integration
- ❌ Still slow on first run (cold start)
- ❌ Search time scales with corpus size

**When to use**: Production systems with dynamic content, multi-instance deployments

**Database choice**:
- **PostgreSQL + pgvector**: Good all-around choice, familiar tooling
- **Neo4j**: Excellent if you already use graphs, built-in vector support
- **Weaviate/Pinecone**: Purpose-built vector DBs, overkill for small projects

### Level 3: Startup Precomputation (Fast from first request)

**Approach**: Generate all embeddings during application startup

**Implementation**:
```python
def sync_embeddings_on_startup(documents, ollama_client, db):
    for doc in documents:
        content_hash = calculate_content_hash(doc['content'])
        stored = db.get_embedding(doc['id'])

        # Only regenerate if content changed
        if not stored or stored['content_hash'] != content_hash:
            embedding = ollama_client.generate(doc['content'])
            db.store_embedding(doc['id'], embedding, content_hash)
```

**Performance**: 5-6 seconds (even first search after deploy)
**Startup cost**: 2-5 minutes for 40 documents (one-time per deploy)

**Tradeoffs**:
- ✅ Fast from first request
- ✅ Predictable performance
- ✅ Smart caching (only regenerate changed content)
- ❌ Slower startup (1-5 min depending on corpus)
- ❌ Not suitable for user-generated content at write-time
- ❌ Still generating query embedding on each search

**When to use**: Production systems where startup time is acceptable (batch deployments, scheduled restarts)

**Implementation detail**: Use content hashing to detect changes. On subsequent startups, only new/modified documents need embeddings generated. With 40 documents:
- First startup: 180 seconds (generate all 40)
- Subsequent startups: 5-10 seconds (all cached, just verify)

### Level 4: Separate Embedding Generation (Real-time writes)

**Approach**: Generate embeddings when content is created/updated, not during search

**Implementation**:
```python
def create_article(content: str, title: str):
    # Save article
    article = db.create_article(content, title)

    # Generate embedding immediately (async or sync)
    content_hash = calculate_content_hash(content)
    embedding = ollama_client.generate(content)
    db.store_embedding(article.id, embedding, content_hash)

    return article
```

**Performance**: 5-15 seconds at write time, 5-6 seconds for search
**Tradeoffs**:
- ✅ Fast startup (no precomputation needed)
- ✅ Works with user-generated content
- ✅ Separation of concerns (write-time vs read-time)
- ❌ Slower writes (5-15s per document)
- ❌ Need async processing for better UX
- ❌ Complexity: background jobs, failure handling

**When to use**: Systems with frequent content updates, user-generated content platforms

**Async patterns**:
- Background tasks (Celery, RQ, Dramatiq)
- Event-driven (webhooks, message queues)
- Progressive enhancement (show in search after embedding ready)

## Model Selection: Speed vs Quality

Not all models are created equal. Choose based on your use case.

### Embedding Models

| Model | Dimensions | Speed | Quality | Use Case |
|-------|-----------|-------|---------|----------|
| nomic-embed-text | 768 | Fast (3-5s) | Good | General purpose, recommended |
| all-minilm | 384 | Very Fast (1-2s) | Fair | Speed-critical, less accuracy ok |
| mxbai-embed-large | 1024 | Slow (8-12s) | Excellent | High-precision requirements |

**Recommendation**: Start with `nomic-embed-text`. It's the sweet spot of speed and quality.

### Chat/Q&A Models

Once you have persistent embeddings, you can afford bigger chat models since search is fast:

| Model | Speed | Quality | Use Case |
|-------|-------|---------|----------|
| nomic-embed-text | N/A | Poor | Don't use for chat |
| llama3.2 | Medium (5-10s) | Good | General Q&A |
| qwen2.5 | Medium (5-10s) | Good | Instruction following |
| mistral | Medium (5-10s) | Good | Balanced option |

**Architecture**: Use **different models for different tasks**:
- Fast embedding model for search (nomic-embed-text)
- Better conversational model for Q&A (llama3.2)

This separation is only practical after you have persistent embeddings. Otherwise, chat model performance doesn't matter - search is the bottleneck.

## Real-World Numbers

From Mongado's knowledge base (12 articles, 27 notes):

| Optimization Level | First Search | Subsequent | Startup Time |
|-------------------|-------------|------------|--------------|
| Naive (no cache) | 30+ sec | 30+ sec | Instant |
| In-memory cache | 18 sec | 10 sec | Instant |
| Persistent storage | 20 sec | 5.7 sec | Instant |
| Startup precompute | 5.7 sec | 5.7 sec | 168 sec |

**Key insight**: The 168-second startup cost is paid once per deployment. Every search saves 24+ seconds. Break-even after ~7 searches.

## Implementation Gotchas

### 1. Content Hash Collisions

Use SHA256, not MD5. Content hashes detect when documents change and embeddings need regeneration.

```python
def calculate_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()
```

### 2. Model Version Tracking

Track which model generated each embedding. When you upgrade models, you know which embeddings to regenerate:

```python
db.store_embedding(
    doc_id=doc_id,
    embedding=embedding,
    model="nomic-embed-text",
    version=1,
    content_hash=content_hash
)
```

### 3. Graceful Degradation

Always have a fallback when Ollama is unavailable:

```python
def semantic_search(query: str):
    if not ollama_client.is_available():
        # Fallback to text search with fuzzy matching
        return text_search(query)

    # ... semantic search logic
```

### 4. Dimensionality Matters

Embedding dimensions affect storage and compute:
- 384 dims: 1.5 KB per embedding
- 768 dims: 3 KB per embedding
- 1024 dims: 4 KB per embedding

For 1000 documents with 768-dim embeddings: ~3 MB storage. Not prohibitive, but worth tracking.

## When to Stop Optimizing

**Don't optimize until you have a problem**. The progression above represents months of iteration. Start simple:

1. **MVP**: Naive implementation, test if users want the feature
2. **If slow**: Add in-memory caching (10 minutes)
3. **If popular**: Add persistent storage (few hours)
4. **If critical**: Add startup precomputation (half day)
5. **If real-time needed**: Add async embedding generation (1-2 days)

Each level adds complexity. Only climb the ladder when user pain justifies the engineering cost.

## Alternative Approaches Not Covered

- **Approximate Nearest Neighbors (ANN)**: For corpora > 10k documents
- **Embedding compression**: Quantization, dimensionality reduction
- **Hybrid search**: Combine keyword + semantic for better results
- **Re-ranking**: Two-stage search for accuracy + speed
- **GPU acceleration**: Faster embedding generation

These matter at scale but add significant complexity. Start simple.

## Key Takeaways

1. **Measure first**: Profile before optimizing. Know your bottleneck.
2. **Cache smartly**: Use content hashes to detect changes, not timestamps.
3. **Separate concerns**: Different models for embeddings vs chat.
4. **Start simple**: In-memory cache beats no cache. Don't prematurely optimize.
5. **Pay upfront**: Startup precomputation trades deploy time for query performance.

The fastest search is the one that doesn't generate embeddings. Cache aggressively, invalidate intelligently, and your users will thank you.

---

*Performance numbers from Mongado knowledge base running Ollama (nomic-embed-text) on M1 Mac. Your mileage will vary based on hardware, model, and corpus size.*
