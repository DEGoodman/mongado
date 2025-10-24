---
id: 6
title: "LLM Performance Optimization: From Naive to Production"
tags: ["AI", "Performance", "Architecture"]
created_at: "2025-10-24T00:00:00"
---

## Intro

Local LLMs eliminate API costs and keep data in-house, but naive implementations are unusably slow. This document identifies the performance bottleneck (embedding generation) and presents four optimization levels with concrete tradeoffs.

Lessons from building semantic search with Ollama: naive implementation took 30+ seconds per search. Optimized version: under 6 seconds.

## The Problem

Naive approach: generate embeddings on every search

- 40 document corpus requires 41 embeddings per search (1 query + 40 documents)
- Result: 15-30+ seconds per query
- Users won't wait. Feature is broken.

## Optimization Levels

Four approaches ordered by complexity. Pick the simplest that meets requirements.

### Level 1: In-Memory Caching

Cache embeddings in RAM with content hash as key.

Performance: 15-20s (first), 8-12s (subsequent)

Tradeoffs:
- Simple (< 10 lines of code)
- Cache lost on restart
- No benefit for first search
- Doesn't scale beyond ~100 documents

When to use: small static corpus, infrequent deploys

### Level 2: Persistent Storage

Store embeddings in database. Use content hash to detect changes and skip regeneration.

Performance: 15-20s (first run), 5-6s (production)

Tradeoffs:
- Survives restarts
- Scales to thousands of documents
- Only regenerates changed content
- Requires database integration
- Still slow on cold start

When to use: production systems, dynamic content, multi-instance deployments

Database options:
- PostgreSQL + pgvector: good default, familiar tooling
- Neo4j: if already using graphs
- Weaviate/Pinecone: overkill for small projects

### Level 3: Startup Precomputation

Generate all embeddings during application startup. Check content hashes, only regenerate if changed.

Performance: 5-6s (every search, even first)
Startup cost: 2-5 min (one-time per deploy)

Tradeoffs:
- Fast from first request
- Predictable performance
- Slower startup (acceptable for batch deploys)
- Not suitable for real-time user content

When to use: production systems with acceptable startup delays

Notes:
- First startup: 180s (generate all 40 embeddings)
- Subsequent startups: 5-10s (cached, just verify hashes)

### Level 4: Write-Time Generation

Generate embeddings when content is created/updated, not during search.

Performance: 5-15s (write), 5-6s (search)

Tradeoffs:
- Fast startup
- Works with user-generated content
- Slower writes
- Requires async processing for good UX
- Added complexity (background jobs, failure handling)

When to use: frequent content updates, user-generated platforms

Async options: Celery, RQ, Dramatiq, message queues

## Model Selection

### Embedding Models

| Model | Dims | Speed | Quality | Notes |
|-------|------|-------|---------|-------|
| nomic-embed-text | 768 | 3-5s | Good | Recommended default |
| all-minilm | 384 | 1-2s | Fair | Speed over accuracy |
| mxbai-embed-large | 1024 | 8-12s | Excellent | High-precision needs |

Start with `nomic-embed-text` (speed/quality sweet spot).

### Chat Models

With persistent embeddings, search is fast. Can afford larger chat models:

| Model | Speed | Use Case |
|-------|-------|----------|
| llama3.2 | 5-10s | General Q&A |
| qwen2.5 | 5-10s | Instruction following |
| mistral | 5-10s | Balanced |

Architecture: separate models for separate tasks
- Embeddings: nomic-embed-text (fast)
- Chat: llama3.2 (better reasoning)

Only practical after persistent embeddings. Otherwise search is bottleneck.

## Performance Numbers

Mongado knowledge base (12 articles, 27 notes):

| Level | First Search | Subsequent | Startup |
|-------|-------------|------------|---------|
| Naive | 30+ s | 30+ s | 0s |
| Memory cache | 18s | 10s | 0s |
| Persistent | 20s | 5.7s | 0s |
| Startup precompute | 5.7s | 5.7s | 168s |

Key insight: 168s startup cost paid once per deploy. Every search saves 24s. Break-even at 7 searches.

## Implementation Notes

### Content Hashing

Use SHA256 to detect changed content and skip regeneration.

### Model Versioning

Track model + version per embedding. On model upgrade, know what to regenerate.

### Graceful Degradation

Fallback to text search when Ollama unavailable.

### Storage Considerations

Embedding dimensions affect storage:
- 384 dims: 1.5 KB
- 768 dims: 3 KB
- 1024 dims: 4 KB

1000 documents @ 768 dims = ~3 MB (negligible)

## When to Optimize

Don't optimize until you have a problem. Progression above = months of iteration.

Approach:
1. MVP: naive implementation (test if users want feature)
2. If slow: memory cache (10 min)
3. If popular: persistent storage (few hours)
4. If critical: startup precomputation (half day)
5. If real-time: async generation (1-2 days)

Each level adds complexity. Only climb when pain justifies cost.

## Advanced Topics (Not Covered)

For corpora > 10k documents:
- Approximate Nearest Neighbors (ANN)
- Embedding compression
- Hybrid search (keyword + semantic)
- Re-ranking
- GPU acceleration

Significant complexity. Start simple.

## Key Takeaways

- Measure before optimizing. Know the bottleneck.
- Cache with content hashes, not timestamps
- Separate models for embeddings vs chat
- In-memory cache > no cache (don't prematurely optimize)
- Startup precomputation trades deploy time for query speed

Fastest search = one that doesn't generate embeddings.

---

*Numbers from Mongado (Ollama/nomic-embed-text/M1 Mac). YMMV.*
