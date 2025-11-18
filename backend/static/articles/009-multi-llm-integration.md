---
id: 9
title: "Multi-LLM Integration: Choosing the Right Model for Each Task"
summary: "Why Mongado uses 3 specialized Ollama models instead of one general-purpose model. Covers embeddings, chat/Q&A, and structured output with real performance data and lessons learned building AI features."
description: "Why Mongado uses 3 specialized Ollama models instead of one general-purpose model, and what we learned building AI features for a knowledge base."
tags: ["ai", "llm", "architecture", "ollama"]
draft: false
published_date: "2025-10-25T00:00:00"
updated_date: "2025-10-25T00:00:00"
created_at: "2025-10-25T00:00:00"
---

## Intro

Building AI features with local LLMs isn't about picking one model for everything. Different tasks need different models.

This article documents the multi-LLM strategy I built for Mongado's knowledge base: what models I chose, why, and what I learned building AI-powered tag suggestions, semantic search, and link recommendations.

**Key insight:** Use the smallest, fastest model that does the job well. Specialized models beat general-purpose models.

## The Multi-Model Architecture

I'm using three Ollama models, each optimized for specific tasks:

| Task | Model | Size | Why This Model |
|------|-------|------|----------------|
| **Embeddings** | `nomic-embed-text` | 274 MB | Fast, high-quality semantic vectors |
| **Chat/Q&A** | `llama3.2:1b` | 1.3 GB | Good reasoning, handles long context |
| **Structured Output** | `qwen2.5:1.5b` | 986 MB | Reliable JSON instruction-following |

Total disk space: ~2.5 GB. All running locally on Ollama.

## Model Selection by Task

### Embeddings: `nomic-embed-text`

**Use case:** Generate semantic vectors for search and similarity matching.

**Why this model:**
- 768-dimensional embeddings (good balance of quality and storage)
- Fast generation (~3-5s for typical note)
- Optimized specifically for semantic search

**Alternatives considered:**
- `all-minilm:384` - Faster but lower quality
- `mxbai-embed-large:1024` - Higher quality but 3x slower, larger embeddings

**Decision:** nomic-embed-text hits the sweet spot for a knowledge base of <1000 documents.

### Chat: `llama3.2:1b`

**Use case:** Answer questions using knowledge base context.

**Why this model:**
- Good reasoning capabilities for Q&A
- Wide context window (handles long articles)
- Fast enough for interactive chat while maintaining quality

**Alternatives I considered:**
- `llama3.2:3b` - Better quality but 3x slower
- `qwen2.5:1.5b` - Fast but less natural conversational ability

**Decision:** The 1b model provides sufficient quality for Q&A while keeping response times under 10 seconds.

### Structured Output: `qwen2.5:1.5b`

**Use case:** Generate JSON responses for tag suggestions, link recommendations, and concept extraction.

**The problem I hit:** I initially tried using llama3.2:1b for everything, including structured output. Chat worked great. JSON was a mess.

**Example failure with llama3.2:1b:**

Prompt: `Suggest tags for this note. Return JSON: [{"tag": "...", "confidence": 0-1, "reason": "..."}]`

Response (broken):
```
{"tag": "culture", "confidence": 0.8, "reason": "..."}
{"tag": "teams", "confidence": 0.7, "reason": "..."}
```
Multiple separate JSON objects instead of an array. Inconsistent formatting across requests.

**Solution: Switch to qwen2.5:1.5b**

Same prompt, consistent response:
```json
[
  {"tag": "culture", "confidence": 0.8, "reason": "Discusses team culture"},
  {"tag": "teams", "confidence": 0.75, "reason": "Focuses on team dynamics"}
]
```

**Decision:** qwen2.5 is purpose-built for instruction-following and structured output. The extra 500 MB is worth reliable JSON.

## Implementation Patterns

### Pattern 1: Separate Client Calls

Don't create one "call LLM" function. Each task has different needs:

```python
# Embeddings (cached, batch-friendly)
ollama_client.generate_embedding(text, use_cache=True)

# Chat (streaming for better UX)
ollama_client.client.generate(
    model="llama3.2:1b",
    prompt=chat_prompt,
    stream=True  # Stream tokens as they're generated
)

# Structured output (non-streaming, need complete response to parse)
ollama_client.client.generate(
    model="qwen2.5:1.5b",
    prompt=json_prompt,
    stream=False
)
```

### Pattern 2: Defensive JSON Parsing

Even with qwen2.5, handle edge cases. The model occasionally wraps JSON in markdown code blocks or returns slightly malformed output:

```python
# Strip markdown wrappers
response = response.strip()
if response.startswith("```json"):
    response = response[7:]
if response.startswith("```"):
    response = response[3:]
if response.endswith("```"):
    response = response[:-3]

# Try array parse first
try:
    data = json.loads(response)
    if isinstance(data, dict):
        data = [data]  # Single object -> array
except json.JSONDecodeError:
    # Fallback: parse line-by-line for multiple objects
    data = []
    for line in response.split('\n'):
        if line.strip().startswith('{'):
            try:
                data.append(json.loads(line))
            except:
                continue
```

This handles markdown wrapping, single objects vs arrays, line-separated objects, and gracefully degrades on malformed responses.

### Pattern 3: Model-Specific Prompts

Don't reuse prompts across models. Each has different strengths:

**qwen2.5 (structured output):** Terse, example-heavy
```
Suggest 2-4 tags. Return JSON: [{"tag": "...", "confidence": 0-1, "reason": "..."}]

JSON:
```

**llama3.2 (conversational):** Natural language framing
```
You are a helpful assistant with expertise in software engineering.

Based on these articles: [...]

Answer this question: [...]
```

Notice qwen gets straight to the point with clear examples, while llama gets conversational context.

### Pattern 4: Hybrid Search Strategy

**Problem:** Embedding generation is expensive. Need fast search even when embeddings aren't available.

**Solution:** Multi-tier search with graceful fallback.

```python
# Fast path: Use precomputed embeddings from Neo4j
try:
    results = await semantic_search_with_precomputed_embeddings(query)
    if results:
        return results  # 5-10s response time
except Exception:
    pass  # Neo4j unavailable

# Fallback path: Generate embeddings on-demand
try:
    results = await semantic_search(query)
    return results  # 15-30s response time
except Exception:
    pass  # Ollama unavailable

# Final fallback: Text search (no AI)
return fuzzy_text_search(query)  # <100ms response time
```

**Performance impact:**
- Neo4j path: 5-10 seconds (only query embedding needed)
- On-demand path: 15-30 seconds (full corpus embedding)
- Text fallback: instant

**Why this works:**
- Gracefully handles Neo4j unavailability without breaking features
- Maintains good UX even during database restarts
- Text search provides immediate results when AI unavailable
- Each tier independently optimized

## Production Safeguards

### AI Kill Switch for Anonymous Users

**Problem:** AI features use compute resources. Need control over who can access them.

**Solution:** Unauthenticated users see AI features but with safeguards:
- Tag/link suggestions visible but gated
- Requires authentication to use
- Prevents abuse while showcasing capabilities

**Implementation:** Backend checks session authentication before processing AI requests.

```python
# Backend enforcement
if not is_authenticated(request):
    raise HTTPException(
        status_code=401,
        detail="Authentication required for AI features"
    )
```

**Why this matters:**
- AI operations are expensive (60-120s on CPU)
- Prevent denial-of-service via repeated AI requests
- Demonstrate features to visitors without giving full access
- Clear upgrade path: anonymous → authenticated for AI features

### Cold Start Optimization

**Warmup endpoint:** `POST /api/ollama/warmup`
- Pre-loads llama3.2:1b model into memory
- Takes 15-20 seconds (one-time cost)
- Subsequent requests skip model loading phase
- Reduces first-request latency from 60s+ to 2-5s

**When to use:** After deployment or Ollama restart.

**How it works:**
```python
# Frontend pre-warms when entering edit mode
if isEditing and settings.aiMode !== "off":
    await fetch(`${API_URL}/api/ollama/warmup`, { method: "POST" })
```

**Production pattern:**
- User enters edit mode → warmup triggers in background
- By the time they click "Get AI Suggestions," model is ready
- Eliminates frustrating wait on first AI request

## Deployment Considerations

### Model Installation

**Development:**
```bash
docker compose up  # Auto-pulls nomic-embed-text and llama3.2:1b
```

**Production:**
qwen2.5:1.5b requires manual pull (~1 GB download, don't want to block startup):
```bash
docker compose exec ollama ollama pull qwen2.5:1.5b
```

### Graceful Degradation

All AI features return empty/fallback responses if Ollama is unavailable:

```python
if not ollama.is_available():
    logger.warning("Ollama unavailable, returning empty suggestions")
    return TagSuggestionsResponse(suggestions=[], count=0)
```

This means core features work without AI, Ollama can restart without breaking the app, and good developer experience (don't need Ollama running for all work).

### Performance Characteristics

From production monitoring:

**GPU-accelerated (optimal):**

| Task | Model | Avg Time | P95 Time |
|------|-------|----------|----------|
| Generate embedding | nomic-embed-text | 2-5s | 8s |
| Answer question | llama3.2:1b | 2-5s | 10s |
| Suggest tags | qwen2.5:1.5b | 2-5s | 8s |

**CPU-only (Docker default):**

| Task | Model | Avg Time | P95 Time |
|------|-------|----------|----------|
| Generate embedding | nomic-embed-text | 30-60s | 90s |
| Answer question | llama3.2:1b | 60-120s | 180s |
| Suggest tags | qwen2.5:1.5b | 60-120s | 180s |

**Key insights:**
- GPU provides 10-30x speedup
- Docker deployments default to CPU-only unless configured with GPU passthrough
- CPU-only is usable but requires patience and aggressive caching
- Embeddings cached in Neo4j, so repeated searches remain fast even on CPU

## Lessons Learned

### 1. Don't Assume General-Purpose Works

I started with llama3.2:1b for everything. Chat worked great. JSON was a mess.

Lesson: Test your specific use case. "General-purpose" doesn't mean "good at everything."

### 2. Smaller Models Often Suffice

qwen2.5:1.5b beats larger models at JSON tasks. llama3.2:1b handles Q&A well enough for my needs.

Lesson: Start with the smallest viable model. Upgrade only when quality isn't good enough.

### 3. JSON Parsing Must Be Robust

Even qwen2.5 occasionally wraps JSON in markdown or returns slightly malformed output.

Lesson: Add defensive parsing. Log failures. Degrade gracefully. Don't assume perfect output.

### 4. Document Model Requirements

My initial production deploy failed because qwen2.5:1.5b wasn't pulled. Lost time debugging.

Lesson: README must list all required models. Consider startup health checks.

### 5. Separate Models = Flexibility

Using 3 models seems complex but enables independent optimization:
- Swap embedding model without touching chat
- Upgrade chat model without breaking tag suggestions
- Test new models on one task at a time

Lesson: Loose coupling between AI tasks pays off long-term.

## When to Add More Models

**Add a model when:**
- Existing model can't handle task well (we added qwen for JSON)
- Performance bottleneck on specific task (could add faster embedding model)
- New capability needed (image analysis, code generation)

**Don't add a model when:**
- Existing model "mostly works" (improve prompts first)
- Trying to optimize prematurely (measure first)
- Following trends (use what solves your problem)

My current setup (3 models) handles semantic search, Q&A, tag suggestions, link recommendations, and concept extraction. That covers all planned AI features for now.

## Future Considerations

### Potential Additions

**Specialized code model:**
- Use case: Extract code examples from articles, suggest related repos
- Candidate: `codellama:7b` or `deepseek-coder:1.3b`
- When: If I add code-heavy content

**Larger reasoning model:**
- Use case: Complex multi-step analysis, clustering notes
- Candidate: `llama3.2:3b` or `qwen2.5:7b`
- When: If Q&A quality drops (haven't hit this yet, but keeping an eye on it)

**Multimodal model:**
- Use case: Analyze diagrams in articles
- Candidate: `llava:7b`
- When: If I start adding visual content (would be cool for architecture diagrams)

### Model Versioning Strategy

Track which model version generated each embedding/output:
```python
{
  "embedding": [...],
  "model": "nomic-embed-text",
  "model_version": "v1.5"
}
```

This enables detecting drift when models update, selective re-generation after upgrades, and A/B testing model changes. Not implemented yet but planned before scaling to 10k+ notes.

## Conclusion

The multi-LLM approach isn't over-engineering—it's about picking the right tool for each job:

- **nomic-embed-text:** Fast, high-quality embeddings (274 MB)
- **llama3.2:1b:** Natural chat and Q&A (1.3 GB)
- **qwen2.5:1.5b:** Reliable structured output (986 MB)

Total cost: 2.5 GB disk, all running locally on Ollama.

Key principles:
1. Specialize models by task
2. Start with smallest viable model
3. Add defensive parsing for structured output
4. Gracefully degrade when models unavailable
5. Document requirements clearly

This foundation supports current features and scales to planned additions like real-time suggestions and graph analysis.

---

## References

- [LLM Performance Optimization](./006-llm-performance-optimization.md) - Caching strategies
- [Ollama Model Library](https://ollama.ai/library) - Model specs
- [Qwen2.5 announcement](https://qwenlm.github.io/blog/qwen2.5/) - Structured output excellence
