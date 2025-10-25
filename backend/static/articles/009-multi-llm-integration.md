---
title: "Multi-LLM Integration: Choosing the Right Model for Each Task"
description: "Lessons from building AI features for the Mongado knowledge base using specialized Ollama models for embeddings, chat, and structured output generation."
tags: ["ai", "llm", "architecture", "ollama"]
created_at: "2025-10-25"
updated_at: "2025-10-25"
---

## Intro

Building AI features with local LLMs isn't about picking one model for everything. Different tasks need different models. This article documents the multi-LLM strategy for Mongado's knowledge base: what models we use, why, and what we learned building AI-powered tag suggestions, semantic search, and concept extraction.

Key insight: **Specialized models beat general-purpose models.** Use the smallest, fastest model that can do the job well.

## The Multi-Model Architecture

Mongado uses three Ollama models, each optimized for specific tasks:

| Task | Model | Size | Why This Model |
|------|-------|------|----------------|
| **Embeddings** | `nomic-embed-text` | 274 MB | Fast, high-quality semantic vectors |
| **Chat/Q&A** | `llama3.2:1b` | 1.3 GB | Balanced reasoning, good context understanding |
| **Structured Output** | `qwen2.5:1.5b` | 986 MB | Excellent JSON instruction-following |

Total disk space: ~2.5 GB (reasonable for local development and production)

## Model Selection by Task

### Embeddings: `nomic-embed-text`

**Use case:** Generate semantic vectors for search and similarity

**Why nomic-embed-text:**
- 768-dimensional embeddings (good balance of quality and storage)
- Optimized for semantic search
- Fast generation (~3-5s for typical note)
- State-of-the-art performance for size

**Alternatives considered:**
- `all-minilm:384` - Faster but lower quality
- `mxbai-embed-large:1024` - Better quality but 3x slower, larger embeddings

**Decision:** nomic-embed-text hits the sweet spot for a knowledge base of <1000 documents.

### Chat: `llama3.2:1b`

**Use case:** Answer questions using knowledge base context

**Why llama3.2:1b:**
- Good reasoning capabilities
- Handles multi-turn conversations
- Balances speed with quality
- Wide context window (supports long articles)

**Prompt example:**
```
Based on these articles and notes:

[...context...]

Answer this question: How do DORA metrics help improve software delivery?
```

**Alternatives considered:**
- `llama3.2:3b` - Better quality but 3x slower
- `qwen2.5:1.5b` - Fast but less natural conversational ability

**Decision:** 1b model is fast enough for interactive chat while maintaining good answer quality.

### Structured Output: `qwen2.5:1.5b`

**Use case:** Generate JSON responses (tag suggestions, concept extraction)

**Why qwen2.5:1.5b:**
- **Exceptional JSON instruction-following** (critical)
- Handles structured output formats reliably
- Fast enough for real-time suggestions
- Good at understanding nuanced prompts

**What we tried:**
1. **llama3.2:1b first** - Failed with inconsistent JSON formatting
2. **Parsing workarounds** - Added multi-line JSON parsing, markdown stripping
3. **Switched to qwen2.5:1.5b** - Immediately got clean, valid JSON

**Concrete example:**

Prompt to llama3.2:1b:
```
Suggest tags for this note. Return JSON: [{"tag": "...", "confidence": 0-1, "reason": "..."}]
```

llama3.2:1b response (inconsistent):
```
{"tag": "culture", "confidence": 0.8, "reason": "..."}
{"tag": "teams", "confidence": 0.7, "reason": "..."}
{"tag": "innovation", "confidence": 0.6, "reason": "..."}
```
(Multiple separate JSON objects, not an array)

qwen2.5:1.5b response (clean):
```json
[
  {"tag": "culture", "confidence": 0.8, "reason": "..."},
  {"tag": "teams", "confidence": 0.75, "reason": "..."}
]
```

**Decision:** qwen2.5 is purpose-built for instruction-following and structured output. Worth the extra 500 MB.

## Implementation Patterns

### Pattern 1: Separate Client Calls

Don't create one "call LLM" function. Each task has different needs:

```python
# Embeddings (cached, batch-friendly)
ollama_client.generate_embedding(text, use_cache=True)

# Chat (streaming, conversational)
ollama_client.client.generate(
    model="llama3.2:1b",
    prompt=chat_prompt,
    stream=True  # for UX
)

# Structured output (non-streaming, strict format)
ollama_client.client.generate(
    model="qwen2.5:1.5b",
    prompt=json_prompt,
    stream=False  # need complete response to parse JSON
)
```

### Pattern 2: Defensive JSON Parsing

Even with qwen2.5, handle edge cases:

```python
# Strip markdown code blocks
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

This handles:
- Markdown-wrapped JSON
- Single objects vs arrays
- Line-separated JSON objects
- Malformed responses (graceful degradation)

### Pattern 3: Model-Specific Prompts

Don't reuse prompts across models. Each has different strengths:

**qwen2.5 (structured):**
```
Analyze this note and suggest 2-4 relevant tags.

Focus on:
- Topic/domain (e.g., "management", "sre")
- Type (e.g., "framework", "concept")

Return ONLY a JSON array of suggestions.
Example: [{"tag": "...", "confidence": 0-1, "reason": "..."}]

JSON:
```

**llama3.2 (conversational):**
```
You are a helpful assistant with expertise in software engineering.

Based on these articles:
[...context...]

Please answer this question concisely:
[...question...]
```

Notice:
- qwen gets terse, example-heavy prompts
- llama gets conversational framing
- Both specify format explicitly

## Deployment Considerations

### Model Installation

**Auto-download (development):**
```bash
docker compose up  # Pulls nomic-embed-text, llama3.2:1b automatically
```

**Manual pull (production):**
```bash
docker compose exec ollama ollama pull qwen2.5:1.5b
```

Why manual? qwen2.5:1.5b is ~1 GB download. Don't want to block startup.

**Alternative:** Add to startup script with background pull.

### Graceful Degradation

All AI features return empty/fallback responses if Ollama unavailable:

```python
if not ollama.is_available():
    logger.warning("Ollama unavailable, returning empty suggestions")
    return TagSuggestionsResponse(suggestions=[], count=0)
```

This means:
- Core features work without AI
- Ollama can restart without breaking app
- Good developer experience (don't need Ollama running for all work)

### Performance Characteristics

From production monitoring:

| Task | Model | Avg Time | P95 Time |
|------|-------|----------|----------|
| Generate embedding | nomic-embed-text | 3-5s | 8s |
| Answer question | llama3.2:1b | 5-10s | 15s |
| Suggest tags | qwen2.5:1.5b | 6-8s | 12s |

All acceptable for interactive use. Optimize if needed via:
- Caching (embeddings already cached)
- Warming models on startup
- Batching requests

## Lessons Learned

### 1. Don't Assume General-Purpose Works

We started with llama3.2:1b for everything. Chat worked great. JSON was a mess.

**Lesson:** Test your specific use case. General-purpose ≠ good at structured output.

### 2. Smaller Models Often Suffice

qwen2.5:1.5b beats larger models at JSON tasks. llama3.2:1b (1 GB) handles chat well enough.

**Lesson:** Start small. Upgrade only when quality isn't good enough.

### 3. JSON Parsing Must Be Robust

Even qwen2.5 occasionally wraps JSON in markdown or returns slightly malformed output.

**Lesson:** Add defensive parsing. Log failures. Degrade gracefully.

### 4. Document Model Requirements

Initial production deploy failed because qwen2.5:1.5b wasn't pulled.

**Lesson:** README must list all models. Consider startup health checks.

### 5. Separate Models = Flexibility

Using 3 models seems complex but enables independent optimization:
- Swap embedding model without touching chat
- Upgrade chat model without breaking tags
- Test new models on one task at a time

**Lesson:** Loose coupling between AI tasks pays off.

## When to Add More Models

**Add a model when:**
- Existing model can't handle task well (we added qwen for JSON)
- Performance bottleneck on specific task (could add faster embedding model)
- New capability needed (image analysis, code generation)

**Don't add a model when:**
- Existing model "mostly works" (improve prompts first)
- Trying to optimize prematurely (measure first)
- Following trends (use what solves your problem)

Current setup (3 models) handles:
- Semantic search (embeddings)
- Q&A (chat)
- Tag suggestions (structured)
- Article concept extraction (structured)
- Link suggestions (structured)

That covers all planned AI features. No need for more models yet.

## Future Considerations

### Potential additions:

**Specialized code model:**
- Use case: Extract code examples from articles, suggest related repos
- Candidate: `codellama:7b` or `deepseek-coder:1.3b`
- When: If we add code-heavy content

**Larger reasoning model:**
- Use case: Complex multi-step analysis, clustering notes
- Candidate: `llama3.2:3b` or `qwen2.5:7b`
- When: If Q&A quality isn't good enough

**Multimodal model:**
- Use case: Analyze diagrams in articles
- Candidate: `llava:7b`
- When: If we add visual content

### Model versioning strategy:

Track which model version generated each embedding/output:
```python
{
  "embedding": [...],
  "model": "nomic-embed-text",
  "model_version": "v1.5"
}
```

Enables:
- Detecting drift when models update
- Selective re-generation after upgrades
- A/B testing model changes

Not implemented yet but planned before scaling to 10k+ notes.

## Conclusion

Multi-LLM architecture isn't over-engineering for Mongado. It's the right tool for each job:

- **nomic-embed-text:** Fast, high-quality embeddings
- **llama3.2:1b:** Natural chat and Q&A
- **qwen2.5:1.5b:** Reliable structured output

Total cost: 2.5 GB disk, all running locally on Ollama.

Key principles:
1. Specialize models by task
2. Start with smallest viable model
3. Add defensive parsing for structured output
4. Gracefully degrade when models unavailable
5. Document requirements clearly

This foundation supports current features and scales to planned additions (real-time suggestions, graph analysis, batch extraction).

**Next evolution:** Background processing for expensive tasks, model fine-tuning on knowledge base content, automated model selection based on task complexity.

---

## References

- [LLM Performance Optimization article](./006-llm-performance-optimization.md) - Embedding caching strategies
- [Ollama Model Library](https://ollama.ai/library) - Model catalog and specs
- [Qwen2.5 announcement](https://qwenlm.github.io/blog/qwen2.5/) - Why it excels at structured output
- Mongado codebase - Real implementation examples
