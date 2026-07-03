# AI/LLM Optimization Plan

Analysis and migration plan for making the knowledge base's AI features fast and cheap. Written 2026-07-03. Tracked in [#190](https://github.com/DEGoodman/mongado/issues/190).

## Problem Statement

AI features (Q&A, semantic search, tag/link suggestions) are slow and constrained by the hosting setup:

- **Single 4GB DigitalOcean droplet** runs frontend, backend, Neo4j, and Ollama.
- Memory pressure forces aggressive Ollama settings (`OLLAMA_KEEP_ALIVE=0`, `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_NUM_PARALLEL=1`), so **every AI request pays a 15–20s cold model load** before CPU inference even starts.
- Generation takes **60–120s** on CPU; even semantic search pays ~5–10s for the query embedding because the embed model is unloaded between requests.
- Quality is capped by what fits in RAM: 1B–1.5B models (`llama3.2:1b`, `qwen2.5:1.5b`) produce mediocre answers and unreliable JSON.
- `LLM_FEATURES_ENABLED` defaults to off in production because of all of the above — the features exist but are effectively unusable.

## Current Architecture

| Concern | Implementation | Location |
|---|---|---|
| Embeddings | Ollama `nomic-embed-text`, precomputed and stored in Neo4j | `ollama_client.py`, `embedding_sync.py` |
| Semantic search | Query embedding + cosine similarity vs. precomputed vectors | `routers/search.py`, `core/ai.py` |
| Q&A | RAG: top-5 docs as context → `llama3.2:1b` | `routers/ai.py` `/api/ask` |
| Tag/link suggestions | `qwen2.5:1.5b` JSON output, cached in Neo4j, SSE streaming | `routers/ai.py`, `notes_service.py` |
| Gating | Runtime feature flag (`llm_features`), rate limiting | `feature_flags.py`, `rate_limiter.py` |

Notable strengths to preserve:
- Precomputed embeddings in Neo4j with content-hash/model/version invalidation (`embedding_sync.py`) — already handles a future model change cleanly.
- Prompt building and JSON parsing are pure functions in `core/ai.py` — provider-agnostic already.
- All Ollama I/O funnels through `OllamaClient` — a single seam for a provider abstraction.
- `config.py` already has `anthropic_api_key` / `openai_api_key` placeholders and 1Password secret support.

## Options Analysis

Assumed real-world volume: personal site, admin-heavy usage, rate-limited. Optimistically ~10–50 LLM requests/day at ~3K input + 500 output tokens each → **under 5M tokens/month**. This is tiny; it changes which options make sense.

### Option A: GPU droplet — rejected

DigitalOcean GPU droplets start around **$1.69/GPU/hr (~$1,200+/mo always-on)**. Even the cheapest GPU cloud instances elsewhere are $50–100+/mo. Three orders of magnitude past budget for this workload. ([DO GPU pricing](https://www.digitalocean.com/products/gradient/gpu-droplets))

### Option B: Bigger/dedicated CPU box for Ollama (existing issue #150) — viable but dominated

Hetzner CX32 (~$7.50/mo) running Ollama with `KEEP_ALIVE=5m` fixes the cold-start problem but:
- Still CPU inference: ~3–5s at best, and only for 1B–3B models. Quality stays low.
- Adds a second server to patch, monitor, and secure (exposed Ollama endpoint).
- Costs more than the API options below while delivering less.

### Option C: Third-party inference API — recommended

Move generation (Q&A, suggestions) to a hosted API. All serious candidates speak the OpenAI-compatible chat API, so one integration covers all of them:

| Provider | Free tier | Paid cost at our volume | Speed | Notes |
|---|---|---|---|---|
| **Groq** | 14,400 req/day on `llama-3.1-8b-instant` (500K tokens/day) | $0.05/$0.08 per MTok → **<$1/mo** | ~300 tok/s (fastest) | Free tier alone covers expected volume; prepaid credits = hard spend cap |
| **Gemini Flash** | 1,500 req/day free | Pennies/mo | Fast | Good fallback provider; free tier per GCP project |
| **Cloudflare Workers AI** | 10K neurons/day | $5/mo Workers Paid + $0.011/1K extra neurons | Fast | The "fixed $5/mo" option; also hosts `bge` embedding models |
| **OpenRouter** | 50 req/day (1,000/day after one-time $10 credit) | Model-dependent | Varies | Meta-router; good escape hatch, weakest free tier |
| **Anthropic Haiku 4.5** | None | $1/$5 per MTok → ~$1–5/mo | Fast | Best output quality; console spend limits give a hard cap |

Sources: [Groq pricing](https://groq.com/pricing), [Groq free tier](https://tokenmix.ai/blog/groq-free-tier-limits-2026), [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), [Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/), [OpenRouter limits](https://openrouter.ai/docs/api/reference/limits), [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing).

Every option here beats the current setup **and** option B on all three axes:
- **Speed**: 1–3s responses instead of 60–120s.
- **Quality**: 8B–flash-class models (or Haiku) instead of 1B–1.5B; reliable JSON via native structured-output/JSON modes instead of defensive parsing.
- **Cost**: $0–5/mo with hard caps, vs. $7.50/mo (Hetzner) or being RAM-hostage on the current droplet.

### Embeddings sub-decision

Semantic search embeddings can stay local or move to an API:

| Approach | Pros | Cons |
|---|---|---|
| **Keep Ollama for embeddings only** (`nomic-embed-text`, ~274MB) with `OLLAMA_KEEP_ALIVE=-1` | No re-embedding; no per-query API call; model small enough to stay resident once chat models are gone | Ollama container stays in prod (~500MB–1GB RAM) |
| **API embeddings** (Workers AI `bge-m3`, Gemini `text-embedding`, OpenAI `text-embedding-3-small`) | Ollama fully removed from prod → frees 1–2GB RAM → droplet can downsize 4GB→2GB (−$12/mo) | One-time full re-embed (already supported by `embedding_sync.py` model-change detection); external dependency for search |

Recommendation: **move embeddings to the same API provider** and drop Ollama from prod entirely. The droplet downsizing pays for the entire AI budget. Keep Ollama in dev compose for offline work.

## Decision (2026-07-03)

**Groq free tier (primary) + Gemini free tier (fallback)**, hard-gated to free tiers (no payment method attached). May switch to Anthropic Haiku 4.5 later — the abstraction makes that a config change. Provider selection is a runtime feature flag (`llm_use_api` in the admin panel), so everything deploys dark with Ollama as the default until API keys are added.

### Activation runbook (once implementation is merged)

1. Create a [Groq](https://console.groq.com) account and API key (free tier, no card).
2. Create a [Gemini](https://aistudio.google.com) API key (free tier, no card).
3. Add GitHub Actions secrets `GROQ_API_KEY` and `GEMINI_API_KEY` (repo → Settings → Secrets); the deploy workflow writes them into `backend/.env` on the droplet.
4. Deploy (push to main). Behavior is unchanged — flag defaults off.
5. In the admin panel, toggle `llm_use_api` on. Generation now routes Groq → Gemini; toggle off to revert to Ollama instantly.

Local dev override: put the keys in `backend/.env` and toggle the flag in the local admin panel.

## Recommended Plan

**Target state:** Provider-agnostic LLM client. Production uses Groq free tier (primary) + Gemini free tier (fallback), or Cloudflare Workers AI if a single fixed $5/mo bill is preferred. Ollama remains the dev/offline default. Prod droplet loses Ollama and can downsize.

**Projected monthly cost: $0–5 for AI + $12 saved on the droplet → net cheaper than today, ~30x faster, better quality.**

### Phase 1: Provider abstraction (no behavior change)

1. Define an `LLMProvider` protocol: `generate(prompt, *, json_mode, max_tokens) -> str`, `generate_stream(...)`, `embed(text) -> list[float]`, `is_available()`.
2. Implement `OllamaProvider` (wraps existing `OllamaClient` logic) and `OpenAICompatProvider` (base URL + API key + model names via config — covers Groq/Gemini/OpenRouter/Cloudflare in one class).
3. Config: `llm_provider` (`ollama` | `openai_compat`), `llm_api_base_url`, `llm_api_key` (1Password ref), `llm_chat_model`, `llm_structured_model`, `embedding_provider`, `embedding_model`.
4. Route `dependencies.get_ollama` → `get_llm_provider`; update `routers/ai.py`, `routers/search.py`, `notes_service.py`, `embedding_sync.py` call sites.
5. Provider selection is orthogonal to the existing `llm_features` runtime flag (flag = on/off, provider = where).

### Phase 2: Production cutover

1. Create provider account, set spend cap / stay on free tier, store key in 1Password.
2. Set prod env to the API provider; use native JSON mode for tag/link suggestions (simplifies `parse_json_response` usage).
3. Re-embed corpus with the new embedding model (startup sync already handles this via model-change detection; corpus is small).
4. Warmup endpoints become no-ops for API providers; `gpu-status` endpoint reports provider instead.
5. Add a fallback chain: primary provider → secondary → graceful "AI unavailable" (pattern already exists).
6. Verify rate limits (`rate_limiter.py`) are tight enough that even abusive traffic can't exceed the free tier / spend cap. Add a daily request budget counter if needed.

### Phase 3: Infra cleanup and savings

1. Remove Ollama service from `docker-compose.prod.yml`; keep it in dev compose.
2. Restore Neo4j memory settings (currently squeezed to leave room for Ollama, issues #59/#60).
3. Evaluate droplet downsize 4GB → 2GB (−$12/mo) once memory headroom is confirmed.
4. Close/supersede #150 (dedicated Ollama server) — no longer needed.

### Explicit non-goals

- GPU hosting in any form.
- Self-hosting larger models.
- Changing the RAG design, caching strategy, or feature flag system — they're sound; only the inference backend changes.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Free tier terms change | OpenAI-compatible abstraction makes switching providers a config change |
| Surprise bills | Prepaid credits (Groq) or console spend caps (Anthropic/Cloudflare); public endpoints already rate-limited |
| Embedding model switch degrades search | `embedding_sync.py` versioning allows clean re-embed; validate search quality before removing Ollama |
| API outage kills AI features | Fallback chain + existing graceful degradation (features already fail soft) |
| Dev/prod divergence | Ollama stays the dev default; CI tests mock the provider interface (already done for Ollama, #124) |
