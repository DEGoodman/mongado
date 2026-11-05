---
id: 9
title: "Multi-LLM Integration: Choosing the Right Model for Each Task"
summary: "Why Mongado's AI features used three small Ollama models (embeddings, chat, structured JSON) instead of one, what broke with a single model, and how splitting by task made the later move to hosted APIs a config change."
description: "Why Mongado used three specialized models instead of one, and what that bought when production moved to hosted APIs."
tags: ["ai", "llm", "architecture", "ollama"]
draft: false
published_date: "2025-10-25T00:00:00"
updated_date: "2026-11-04T00:00:00"
created_at: "2025-10-25T00:00:00"
---

> **Update (July 2026):** Production now uses hosted APIs instead of Ollama: Groq for generation with Gemini as fallback, and Gemini for embeddings ([#190](https://github.com/DEGoodman/mongado/issues/190)). Ollama is still the local dev default. The task split described here is what made that switch a config change. See [the postscript](#postscript-hosted-apis).

## Intro

Mongado's knowledge base has three kinds of AI work: semantic search, Q&A over articles and notes, and suggestions (tags, related notes) returned as JSON. I started with one small model for all of it. Chat was fine; the JSON was unusable.

Each task has its own model now. The rule I settled on: **use the smallest model that does the task reliably, and pick it per task.**

## Definitions

- **Embedding model**: turns text into a vector for similarity search. Doesn't generate text.
- **Chat model**: generates free-form answers from a prompt and retrieved context.
- **Structured output**: generation that must parse, here a JSON array of suggestions.

## The Three Models

| Task | Model | Size | Why |
|------|-------|------|-----|
| Embeddings | `nomic-embed-text` | 274 MB | 768 dimensions, built for retrieval |
| Chat / Q&A | `llama3.2:1b` | 1.3 GB | Readable answers, fits in memory |
| Structured output | `qwen2.5:1.5b` | 986 MB | Returns valid JSON consistently |

~2.5 GB on disk. On the 4GB production droplet, only one model fit in memory at a time (see [Self-Hosted LLM Optimization](/knowledge-base/articles/6)).

### Embeddings: `nomic-embed-text`

The middle option on speed and quality. `all-minilm` (384 dims) is faster but noticeably worse at matching. `mxbai-embed-large` (1024 dims) is better but about 3x slower. For a corpus under 1,000 documents, nomic was enough.

### Chat: `llama3.2:1b`

`llama3.2:3b` gave better answers but was about 3x slower, and on CPU the 1b model already took 40+ seconds per answer. Quality was acceptable for Q&A grounded in retrieved context, where the model mostly summarizes what it's given.

### Structured output: `qwen2.5:1.5b`

This is where one model stopped working.

Prompt:

```
Suggest tags for this note. Return JSON: [{"tag": "...", "confidence": 0-1, "reason": "..."}]
```

`llama3.2:1b` returned separate objects, one per line, not an array, and the format varied between requests:

```
{"tag": "culture", "confidence": 0.8, "reason": "..."}
{"tag": "teams", "confidence": 0.7, "reason": "..."}
```

`qwen2.5:1.5b`, same prompt:

```json
[
  {"tag": "culture", "confidence": 0.8, "reason": "Discusses team culture"},
  {"tag": "teams", "confidence": 0.75, "reason": "Focuses on team dynamics"}
]
```

500 MB more disk for JSON that parses was an easy trade.

## Implementation Patterns

### 1. One call path per task

Don't build a single `call_llm()`. The tasks need different settings:

- **Embeddings**: cached by content hash, batched during sync
- **Chat**: streamed, so the user sees tokens as they arrive
- **Structured**: not streamed, since you need the full response before parsing

### 2. Parse defensively

Even qwen sometimes wraps JSON in a markdown code fence or returns a single object instead of an array.

```python
def parse_suggestions(raw: str) -> list[dict[str, Any]]:
    text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        pass
    # Fallback: one JSON object per line
    items = []
    for line in text.splitlines():
        if line.strip().startswith("{"):
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return items
```

Log every fallback. A parser that quietly returns `[]` makes a broken model look like a model with no suggestions.

### 3. Different prompts per model

The structured model got terse prompts that end with the expected format and `JSON:`. The chat model got a role, the retrieved context, then the question. A prompt tuned for one model doesn't transfer well to another.

### 4. Degrade in tiers

Search tries the cheapest path that works:

1. Stored embeddings: embed only the query (5–10s on CPU)
2. If the stored embeddings are missing: embed on demand (15–30s)
3. If the model is down: plain text search (<100ms)

Every AI endpoint returns an empty result, not an error, when the model is unavailable. The site works without AI; it just has fewer suggestions.

### 5. Rate-limit every AI endpoint

On CPU, a single generation request held the machine for a minute or more, so a handful of repeated requests could take the site down. Every AI endpoint gets its own per-client rate limit (e.g. 20/minute for Q&A, 5/minute for multi-document synthesis), and the editor tools require an authenticated session.

## Pitfalls

- **Assuming "general-purpose" covers structured output.** Test the exact format you need. Small chat models are especially bad at it.
- **Undocumented model dependencies.** My first production deploy failed because `qwen2.5:1.5b` wasn't pulled. List every required model and check for them at startup.
- **Adding a model when a prompt fix would do.** A new model costs memory and a deploy step. Try the prompt first.

## Postscript: Hosted APIs

In mid-2026, production generation moved to Groq (primary) and Gemini (fallback), and embeddings to Gemini, behind an OpenAI-compatible provider interface. Ollama stays as the local dev default.

Because each task already had its own call path and model setting, the move was mostly configuration:

- **Embeddings** switched to `gemini-embedding-001`. Each stored embedding records its model, so the next sync knew to re-embed everything.
- **Chat and structured output** now share one larger hosted model. The JSON reliability problem largely went away at that size, but the defensive parser stayed.
- **Groq's model changed under us** when `llama-3.1-8b-instant` was decommissioned ([#304](https://github.com/DEGoodman/mongado/issues/304)). One setting changed.

Hosted APIs fail differently from local models. Instead of crashes from running out of memory, you get rate limits, payload-size rejections, and failures that look like empty answers ([#260](https://github.com/DEGoodman/mongado/issues/260), [#279](https://github.com/DEGoodman/mongado/issues/279)). Tiered degradation and loud logging mattered more after the move, not less.

## Conclusion

Pick a model per task, start with the smallest one that works, and assume structured output will sometimes come back malformed. Keeping the tasks separate is what made the move from local models to hosted APIs mostly a config change.

## References

- [Self-Hosted LLM Optimization](/knowledge-base/articles/6): caching and memory tuning for the same setup
- [Ollama model library](https://ollama.com/library)
- [`docs/AI_OPTIMIZATION.md`](https://github.com/DEGoodman/mongado/blob/main/docs/AI_OPTIMIZATION.md): the hosted-API decision
