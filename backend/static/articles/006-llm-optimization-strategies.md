---
id: 6
title: "Self-Hosted LLM Optimization: Production Under Resource Constraints"
summary: "Running semantic search and Q&A on Ollama on a 4GB, CPU-only droplet. A caching ladder, the memory tuning that stopped the OOM crashes, and the bug that kept the cache from being used. Q&A went from 90s timeouts to 45s, before inference eventually moved to hosted APIs."
tags: ["ai", "performance", "architecture"]
draft: false
published_date: "2025-11-03T00:00:00"
created_at: "2025-10-24T00:00:00"
updated_date: "2026-11-04T00:00:00"
---

> **Update (July 2026):** Production no longer runs Ollama. Generation moved to hosted APIs (Groq, with Gemini as fallback) and embeddings to Gemini ([#190](https://github.com/DEGoodman/mongado/issues/190)). Responses dropped from 60–120s to 1–3s, and the droplet shrank from 4GB to 2GB. The caching and memory lessons below still apply to anyone self-hosting on small hardware. The [postscript](#postscript-why-i-stopped-self-hosting) explains why I stopped.

## Intro

Self-hosting an LLM avoids per-request costs and keeps data on your own box. In exchange, every performance problem is yours.

Mongado's knowledge base ran semantic search and Q&A on Ollama on a 4GB DigitalOcean droplet with no GPU. The first version timed out at 90s and crashed with out-of-memory errors. After the changes below, Q&A was stable at 45s and search took 5–10s.

This covers:

- Where the time went (embedding generation)
- A four-step caching ladder, simplest first
- The memory tuning that made any of it possible
- One bug that kept the cache from being used

## Definitions

- **Embedding**: a vector representing a document's meaning. Search compares the query's embedding to each document's.
- **Content hash**: SHA-256 of a document's text. If the hash hasn't changed, the stored embedding is still valid.
- **Cold start**: the first request after a deploy or model unload, which pays the model load cost.

## The Problem

The naive implementation embedded every document on every search.

- 40 documents = 41 embeddings per query (1 query + 40 documents)
- On CPU, that's 30+ seconds per search
- Nobody waits that long, so the feature was effectively broken

Document embeddings almost never change between searches. Compute them once and store them.

## The Caching Ladder

Climb only as far as you need.

| Level | Where embeddings live | First search | Later searches | Cost |
|-------|----------------------|--------------|----------------|------|
| 0. Naive | Nowhere | 30+s | 30+s | None |
| 1. In-memory | Process RAM, keyed by content hash | ~18s | ~10s | <10 lines; lost on restart |
| 2. Persistent | Database (Neo4j node properties) | 15–30s | 5–10s | DB integration |
| 3. Precompute | Database, filled at startup or on demand | 5–6s | 5–6s | Slow deploys |
| 4. Write-time | Database, filled when content is saved | 5–6s | 5–6s | Slow writes, needs a background job |

Numbers are CPU-only on the 4GB droplet with a ~40-document corpus.

### Level 1: In-memory cache

Key each embedding by content hash. Good enough for a small, static corpus with infrequent deploys. Every restart starts from zero.

### Level 2: Persistent storage (what Mongado used)

Store the embedding on the Article or Note node in Neo4j, along with its content hash and model name. On sync, skip any document whose hash and model match.

- Survives restarts
- Only regenerates changed content
- Changing the embedding model invalidates everything automatically

If you don't already have a database, PostgreSQL + pgvector is the usual default. Mongado already had Neo4j for the note graph, so embeddings went there too.

### Level 3: Precompute

Fill the cache before anyone searches. Mongado exposes this as `POST /api/admin/sync-embeddings` rather than running it on every startup, because a full sync took about 3 minutes and made every dev restart painful.

### Level 4: Write-time generation

Embed on create/update. This is the right answer for user-generated content, but it needs a background job queue (Celery, RQ, Dramatiq) and failure handling. Mongado's corpus changes rarely enough that Level 3 was sufficient.

## Memory: The Actual Bottleneck

None of the caching mattered until the box stopped running out of memory.

**Budget on the 4GB droplet:**

- Physical RAM: 3.8 GiB
- Available after OS, Neo4j, backend, frontend: ~1.0 GiB
- `llama3.2:1b` (chat): 1.8 GB to load
- `nomic-embed-text` (embeddings): 297 MB

Q&A needs both models. Loading the chat model while the embedding model was resident crashed the process: `model requires more system memory than is available`.

**Three fixes:**

1. **Cap Neo4j's heap** ([#60](https://github.com/DEGoodman/mongado/issues/60)). Neo4j defaults to a large heap; the knowledge base needs very little.
   ```yaml
   NEO4J_dbms_memory_heap_max__size=512m
   ```
   Freed ~1.5 GB.

2. **One model at a time** ([#59](https://github.com/DEGoodman/mongado/issues/59)).
   ```yaml
   OLLAMA_MAX_LOADED_MODELS=1
   OLLAMA_KEEP_ALIVE=0   # prod: unload right after each request
   ```
   The embedding model unloads before the chat model loads.

3. **Swap as a safety net** ([#64](https://github.com/DEGoodman/mongado/issues/64)).
   ```bash
   sudo fallocate -l 2G /swapfile
   sudo sysctl vm.swappiness=10   # prefer RAM, swap only under pressure
   ```
   Requests that run short on memory get slower instead of crashing.

Result: ~2.5 GiB available for a 1.8 GB model.

**Dev vs prod:** Dev used `OLLAMA_KEEP_ALIVE=5m` so repeated requests skipped the model load. Prod used `0` to keep memory free, which means every prod request paid a 15–20s cold load.

## The Bug: Not Using the Cache

Level 2 was built and working for search. Q&A didn't use it. The Q&A endpoint called the original search function, which re-embedded the whole corpus on every question.

```python
# Before: re-embeds every document on every question
relevant_docs = ollama_client.semantic_search(question, all_resources)

# After: reads stored embeddings, embeds only the question
embeddings = neo4j.get_all_embeddings()
relevant_docs = ollama_client.semantic_search_with_precomputed_embeddings(
    question, embeddings
)
```

| | Before | After |
|-|--------|-------|
| Q&A response | 90s timeout, then OOM | 45s |
| Embeddings per question | 26 | 1 |
| Breakdown | — | 1–2s query embedding, <1s fetch, 40–43s chat model load + generation |

When you add a cache, check every code path that does the expensive work, not only the one you were looking at.

## Pitfalls

- **Optimizing before fixing memory.** On small hardware, an OOM crash hides every other problem. Check the memory budget first.
- **Timestamps as cache keys.** A re-save without edits invalidates the cache. Hash the content instead.
- **Not recording the model.** Without the model name stored next to each embedding, you can't tell which vectors to regenerate after switching models. Vectors from different models aren't comparable.
- **Silent fallbacks.** Fall back to text search when the LLM is down, but log it. Otherwise a broken embedding path looks like "search got a bit worse."

## Postscript: Why I Stopped Self-Hosting

45s for Q&A was stable, but nobody would use it. The floor on CPU was a 15–20s model load plus 40s of generation, and only for 1B-class models.

The alternatives ([`docs/AI_OPTIMIZATION.md`](https://github.com/DEGoodman/mongado/blob/main/docs/AI_OPTIMIZATION.md)):

- **GPU hosting**: ~$1,200+/month. Not for a personal site.
- **Bigger CPU droplet**: costs more than an API and is still slow.
- **Hosted inference on free tiers**: Groq and Gemini free tiers cover this site's volume many times over (<50 requests/day).

Moving to hosted APIs cut responses to 1–3s, moved from 1B-class models to much larger ones, and removed Ollama from prod. The droplet dropped to 2GB, which saved more than the APIs cost.

The work above still paid off. Content-hashed, model-tagged embeddings in Neo4j meant switching embedding providers was a re-sync, not a rewrite. Hosted APIs bring their own problems, though: rate limits, payload-size errors, and providers that fail silently. See [#213](https://github.com/DEGoodman/mongado/issues/213), [#260](https://github.com/DEGoodman/mongado/issues/260), and [#279](https://github.com/DEGoodman/mongado/issues/279).

## Conclusion

On small hardware, fix memory first, then cache embeddings by content hash, then confirm every endpoint reads from the cache. That took Mongado from crashes to a stable 45s. Getting under a few seconds meant leaving CPU inference entirely.

---

*Numbers are from Mongado production in late 2025 (Ollama, `nomic-embed-text`, `llama3.2:1b`, 4GB CPU-only droplet).*
