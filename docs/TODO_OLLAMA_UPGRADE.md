# TODO: Upgrade Ollama Conversational Model

## Context

Now that we have persistent embeddings stored in Neo4j, we no longer need to generate embeddings during search operations. This creates an opportunity to upgrade our conversational model to provide better Q&A responses without sacrificing performance.

## Current Setup

- **Embedding Model**: `nomic-embed-text` (fast, efficient, 768 dimensions)
- **Conversational Model**: Currently using the same model for both tasks
- **Performance**: Embeddings are pre-generated and cached in Neo4j
- **Search Speed**: ~5-6 seconds for semantic search (only query embedding needed)

## Proposed Change

Use **different models for different tasks**:

1. **Keep `nomic-embed-text` for embeddings** (fast, works great)
2. **Upgrade to better conversational model for Q&A**:
   - Option A: `llama3.2:latest` (better reasoning, still relatively fast)
   - Option B: `qwen2.5:latest` (excellent instruction following)
   - Option C: `mistral:latest` (good balance of speed and quality)

## Benefits

- Better Q&A responses with more sophisticated reasoning
- No performance impact on search (embeddings already cached)
- Smart resource allocation: small models for speed, larger models for quality
- Can experiment with different chat models without affecting embeddings

## Implementation Steps

1. Update `backend/config.py` to support separate models:
   ```python
   OLLAMA_EMBED_MODEL: str = "nomic-embed-text"  # For embeddings
   OLLAMA_CHAT_MODEL: str = "llama3.2"  # For Q&A
   ```

2. Update `ollama_client.py` to use appropriate model for each task:
   - Embeddings: Use `OLLAMA_EMBED_MODEL`
   - Q&A/Chat: Use `OLLAMA_CHAT_MODEL`

3. Pull the new chat model:
   ```bash
   docker compose exec backend ollama pull llama3.2
   ```

4. Test Q&A quality improvement

## Testing

Before deploying:
- Test Q&A responses with the new model
- Verify embeddings still use `nomic-embed-text`
- Confirm no performance degradation
- Test graceful fallback if chat model unavailable

## Notes

- This is enabled by our persistent embeddings work
- The separation of concerns (embed vs chat) is a best practice
- Can swap chat models freely without regenerating embeddings
- Consider adding model selection to UI for experimentation

## Priority

**Medium** - Nice-to-have improvement, not urgent
Good follow-up project after validating current performance
