---
id: 6
title: "Self-Hosted LLM Optimization: Production Under Resource Constraints"
summary: "Optimizing self-hosted LLMs on a 4GB droplet with no GPU. Four optimization levels that reduced Q&A from 90s timeouts to 45s stable responses and semantic search to 5-10s using caching and batching strategies."
tags: ["ai", "performance", "architecture"]
draft: false
published_date: "2025-11-03T00:00:00"
created_at: "2025-10-24T00:00:00"
updated_at: "2025-11-04T00:00:00"
---

## Intro

Third-party AI APIs (OpenAI, Anthropic) are fast and convenient, but self-hosting eliminates recurring costs, keeps data private, and forces you to understand what's actually happening under the hood. The tradeoff: you inherit the performance and infrastructure challenges.

This document identifies the performance bottleneck (embedding generation) and presents four optimization levels tested on real production hardware: a 4GB DigitalOcean droplet with no GPU. Lessons learned from running semantic search and Q&A on Ollama under memory pressure.

Context: Mongado runs entirely self-hosted. No external AI services, no high-end GPU servers. This constraint-driven approach revealed optimizations and pitfalls you won't find in documentation written for well-resourced production environments.

The naive implementation resulted in 90s timeouts and OOM crashes. After optimization, the system delivers 45s stable Q&A and 5-10s semantic search.

## The Problem

The naive approach generates embeddings on every search.

- A 40 document corpus requires 41 embeddings per search (1 query + 40 documents)
- This results in 15-30+ seconds per query
- Users won't wait for this. The feature is effectively broken.

## Optimization Levels

Four approaches ordered by complexity. Pick the simplest that meets requirements.

### Level 1: In-Memory Caching

This level caches embeddings in RAM with content hash as key.

Performance: 15-20s for first search, 8-12s for subsequent searches.

Tradeoffs:
- Simple (< 10 lines of code)
- Cache lost on restart
- No benefit for first search
- Doesn't scale beyond ~100 documents

When to use: Best for small static corpus with infrequent deploys.

### Level 2: Persistent Storage (Mongado's Production Choice)

This level stores embeddings in a database and uses content hash to detect changes and skip regeneration.

Performance: 15-20s for first run, 5-10s in production.

**Mongado uses Neo4j for embedding persistence:**
- Embeddings stored directly on Article and Note nodes
- Content hash verification prevents unnecessary regeneration
- Embedding version tracking enables safe model upgrades
- Graph database provides natural fit for note relationships

Tradeoffs:
- Survives restarts
- Scales to thousands of documents
- Only regenerates changed content
- Requires database integration
- Still slow on cold start (first search after deploy)

When to use: Best for production systems, dynamic content, and multi-instance deployments.

Database options:
- PostgreSQL + pgvector: good default, familiar tooling
- Neo4j: excellent for knowledge bases with relationships
- Weaviate/Pinecone: overkill for small projects

### Level 3: Startup Precomputation

This level generates all embeddings during application startup. It checks content hashes and only regenerates embeddings if content changed.

Performance: 5-6s for every search, even the first one.
Startup cost: 2-5 minutes one-time cost per deploy.

**Configuration option (disabled by default in Mongado):**
- Manual trigger via admin endpoint: `POST /api/admin/sync-embeddings`
- Run on-demand rather than every startup
- Prevents slow deploys while maintaining embedding freshness

Tradeoffs:
- Fast from first request
- Predictable performance
- Slower startup (acceptable for batch deploys, but annoying in development)
- Not suitable for real-time user content

When to use: Best for production systems with acceptable startup delays.

**Alternative approach:** Prefer lazy generation (on article creation) over startup batch processing.

Notes:
- First startup: 180s (generate all 40 embeddings)
- Subsequent startups: 5-10s (cached, just verify hashes)

### Level 4: Write-Time Generation

This level generates embeddings when content is created or updated, not during search.

Performance: 5-15s for writes, 5-6s for searches.

Tradeoffs:
- Fast startup
- Works with user-generated content
- Slower writes
- Requires async processing for good UX
- Added complexity (background jobs, failure handling)

When to use: Best for platforms with frequent content updates and user-generated content.

Async options include Celery, RQ, Dramatiq, and message queues.

## Model Selection

### Embedding Models

| Model | Dims | Speed | Quality | Notes |
|-------|------|-------|---------|-------|
| nomic-embed-text | 768 | 3-5s | Good | Recommended default |
| all-minilm | 384 | 1-2s | Fair | Speed over accuracy |
| mxbai-embed-large | 1024 | 8-12s | Excellent | High-precision needs |

Start with `nomic-embed-text` as it offers the best speed/quality sweet spot.

### Chat Models

With persistent embeddings, search is fast enough that you can afford larger chat models:

| Model | Speed | Use Case |
|-------|-------|----------|
| llama3.2 | 5-10s | General Q&A |
| qwen2.5 | 5-10s | Instruction following |
| mistral | 5-10s | Balanced |

This architecture uses separate models for separate tasks:
- Embeddings: nomic-embed-text (fast)
- Chat: llama3.2 (better reasoning)

This approach is only practical after implementing persistent embeddings. Otherwise search remains the bottleneck.

## Hardware Considerations: GPU vs CPU

**Performance varies dramatically based on hardware.**

GPU-accelerated Ollama:
- Embedding generation: 2-5s per document
- Chat/Q&A: 2-5s per response
- Interactive and responsive

CPU-only (Docker default):
- Embedding generation: 30-60s per document
- Chat/Q&A: 60-120s per response
- Requires aggressive caching to be usable

**Mongado auto-detects GPU availability:**
- Docker deployments default to CPU-only unless explicitly configured with GPU passthrough
- Native installations optimistically assume GPU may be available
- Backend adjusts performance expectations and user messaging accordingly

**Why this matters:**
- CPU-only makes Level 1 (in-memory cache) mandatory, not optional
- GPU acceleration makes Level 2 (persistent storage) a performance boost rather than survival requirement
- Without GPU, any cache miss means 30+ second wait

**Production recommendation:** Use GPU if available, but architect for CPU-only performance as baseline.

## Production Reality: Memory Management

Real-world deployment reveals constraints that theoretical optimization doesn't account for. Mongado runs on a 4GB DigitalOcean droplet, where aggressive memory tuning was required to make LLMs work at all.

**The Problem:**

Ollama models have explicit memory requirements:
- nomic-embed-text: 297 MB
- llama3.2:1b: 1.8 GB (requires loading into RAM)
- Server total: 3.8 GiB physical, ~1.0 GiB available after OS/services

The result was OOM crashes when switching between embedding and chat models.

**Solutions Applied:**

1. **Neo4j Memory Tuning** (issue #60)
   ```yaml
   NEO4J_dbms_memory_heap_max__size=512m  # Down from default ~2.5GB
   ```
   This freed approximately 1.5GB RAM for Ollama operations.

2. **Ollama Model Unloading** (issue #59)
   ```yaml
   OLLAMA_MAX_LOADED_MODELS=1      # Only one model in memory at a time
   OLLAMA_KEEP_ALIVE=0              # Prod: unload immediately after use
   ```
   This ensures the embedding model unloads completely before the chat model loads.

3. **Swap Space** (issue #64)
   ```bash
   sudo fallocate -l 2G /swapfile
   sudo sysctl vm.swappiness=10     # Prefer RAM but allow graceful swap
   ```
   This enables graceful performance degradation instead of OOM crashes.

**Result:** The 1.8GB chat model now fits comfortably in 2.5GB available RAM, and the system remains stable under load.

**Key Insight:** Resource tuning isn't optional at small scales. Optimization strategies only work if the system has memory to execute them.

## The Critical Bug: Using Your Own Cache

Having an optimization isn't enough. Every code path must actually use it.

**What Went Wrong:**

Mongado implemented Level 2 optimization (persistent embeddings in Neo4j) but the Q&A endpoint wasn't using the cached embeddings. It regenerated all embeddings on every request.

```python
# WRONG (what we had)
def ask_question(question):
    # Regenerates ALL embeddings on every request
    relevant_docs = ollama_client.semantic_search(question, all_resources)

# RIGHT (after fix)
def ask_question(question):
    # Fetches cached embeddings from Neo4j
    embeddings = neo4j.get_all_embeddings()
    relevant_docs = ollama_client.semantic_search_with_precomputed_embeddings(
        question, embeddings
    )
```

**Impact:**
- Before: 90s timeout, OOM crash (regenerating 26 embeddings × 30-60s each)
- After: 45s stable (only query embedding generated, ~1-2s)
- **~50% faster** by actually using the cache we built

**Lesson:** Build the optimization, then verify every endpoint uses it. One missed code path negates the entire effort.

## Environment-Specific Tuning

Different environments need different tradeoffs. Don't use the same settings everywhere.

| Setting | Dev | Prod | Why Different? |
|---------|-----|------|----------------|
| `OLLAMA_KEEP_ALIVE` | 5m | 0 | Dev: iteration speed; Prod: memory conservation |
| Neo4j Heap | 512m | 512m | Same (small knowledge base in both) |
| Swap Space | Optional | Required | Prod: uptime critical, graceful degradation |

**Dev Optimization:**
- Keep model loaded for 5 minutes to enable fast iteration during development
- First request: 2-3s (model load)
- Subsequent requests (< 5min): <1s (model already loaded)

**Prod Optimization:**
- Unload immediately to maximize available RAM for concurrent requests
- Every request: 2-3s model reload overhead
- Prevents OOM when multiple requests arrive simultaneously

**Tradeoff:** Development prioritizes iteration speed while production prioritizes stability and memory efficiency.

## Performance Numbers

Mongado knowledge base (12 articles, 27 notes) running on 4GB DigitalOcean droplet (CPU-only).

**Production Performance (mongado.com):**

Before optimizations:
- Q&A request: 90s timeout leading to OOM crash
- Root cause: Regenerating all 26 embeddings on every request
- Memory: 1.0 GiB available, 1.8 GiB needed (OOM)
- Error: "model requires more system memory than is available"

After optimizations (Neo4j caching + memory tuning):
- Q&A request: **45s stable**
- Breakdown:
  - Query embedding generation: 1-2s
  - Fetch cached embeddings from Neo4j: <1s
  - Load chat model + generate answer: 40-43s
- Memory: 2.5 GiB available, 1.8 GiB needed (comfortable headroom)

**Search Performance (CPU-only):**

| Level | First Search | Subsequent | Startup | Notes |
|-------|-------------|------------|---------|-------|
| Naive | 30+ s | 30+ s | 0s | Unusable |
| Memory cache | 18s | 10s | 0s | Lost on restart |
| Neo4j persistent | 15-30s | 5-10s | 0s | Production baseline |

**GPU-accelerated performance (reference):**

| Level | First Search | Subsequent | Startup | Notes |
|-------|-------------|------------|---------|-------|
| Neo4j + GPU | 5-10s | 5-10s | 0s | Production optimal |
| With warmup | 2-5s | 2-5s | 0s | Best case |

**Key insights:**
- Resource tuning (Neo4j heap, Ollama unloading, swap) unlocked the performance optimizations
- Using cached embeddings reduced Q&A from 90s timeout to 45s stable, but only after fixing the bug
- GPU acceleration reduces search time by 3-6x (5-10s vs 15-30s)
- CPU-only is usable with persistent embeddings, but requires memory management
- Pre-warming model (via `/api/ollama/warmup`) eliminates cold-start penalty on GPU setups

## Implementation Notes

### Content Hashing

Use SHA256 to detect changed content and skip regeneration when content is unchanged.

### Model Versioning

Track the model name and version for each embedding. This allows you to know which embeddings to regenerate when upgrading models.

### Graceful Degradation

Implement fallback to text search when Ollama is unavailable.

### Storage Considerations

Embedding dimensions affect storage:
- 384 dims: 1.5 KB
- 768 dims: 3 KB
- 1024 dims: 4 KB

1000 documents @ 768 dims = ~3 MB (negligible)

## When to Optimize

Don't optimize until you have a problem. The progression described above represents months of iteration.

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

These add significant complexity. Start simple and only add complexity when needed.

## Key Takeaways

- Measure before optimizing. Know the bottleneck.
- Cache with content hashes, not timestamps
- **Verify every code path uses your optimization.** Having the cache isn't enough if endpoints bypass it.
- Resource constraints (memory, CPU) determine which optimization levels are viable
- Environment-specific tuning: development prioritizes speed, production prioritizes stability
- Use separate models for embeddings versus chat
- In-memory cache is better than no cache (don't prematurely optimize)
- Startup precomputation trades deploy time for query speed

The fastest search is one that doesn't generate embeddings.
The best optimization is one you actually use in all code paths.

---

*Numbers from Mongado production (Ollama/nomic-embed-text/4GB DigitalOcean droplet, CPU-only). YMMV.*

**Related Issues:** #57 (Q&A cached embeddings fix), #59 (Ollama model unloading), #60 (Neo4j memory tuning), #64 (Swap space setup)
