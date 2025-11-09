"""Ollama integration for AI-powered features."""

import logging
from typing import Any

from config import get_settings
from utils import calculate_content_hash

logger = logging.getLogger(__name__)
settings = get_settings()


class OllamaClient:
    """Client for interacting with Ollama for embeddings and chat."""

    def __init__(self) -> None:
        """Initialize Ollama client."""
        self.enabled = settings.ollama_enabled
        self.host = settings.ollama_host
        # Use separate models for embeddings (fast) vs chat (quality)
        self.embed_model = settings.ollama_embed_model
        self.chat_model = settings.ollama_chat_model
        self.model = settings.ollama_chat_model  # Backwards compatibility
        self.num_ctx = settings.ollama_num_ctx
        self.client: Any | None = None

        # Embedding cache: {content_hash: embedding_vector}
        # This prevents regenerating embeddings for the same content
        self.embedding_cache: dict[str, list[float]] = {}

        if self.enabled:
            try:
                import ollama

                # Create client with host configuration
                self.client = ollama.Client(host=self.host)
                # Test connection
                self.client.list()
                logger.info("Ollama client initialized successfully at %s", self.host)
            except Exception as e:
                logger.warning("Failed to initialize Ollama client: %s", e)
                logger.warning("Ollama features will be disabled. Is Ollama running at %s?", self.host)
                self.enabled = False

    def is_available(self) -> bool:
        """Check if Ollama is available and enabled."""
        return self.enabled and self.client is not None

    def has_gpu(self) -> bool:
        """Check if GPU acceleration is available.

        Returns:
            True if GPU is detected and available, False if CPU-only
        """
        if not self.is_available():
            return False

        try:
            # The most reliable way is to make a tiny generation request and check
            # if it's fast enough to indicate GPU usage. But that's expensive.
            #
            # Instead, we can check the ollama ps endpoint which shows running models
            # and their GPU status. If no models are running, we can't tell.
            #
            # For now, use a heuristic: Try to see if we can import ollama internals
            # or check environment variables, but the simplest approach is to just
            # assume CPU-only unless we can confirm GPU.
            #
            # Check if running on Docker which typically doesn't pass through GPU
            import os
            in_docker = os.path.exists("/.dockerenv")

            # In Docker, GPU passthrough is rare unless specifically configured
            # For now, conservatively assume CPU-only in Docker
            if in_docker:
                logger.info("Running in Docker - assuming CPU-only unless GPU explicitly configured")
                return False

            # On native installs, Ollama will use GPU if available
            # We can't reliably detect this without making a test request
            logger.info("Running natively - assuming GPU may be available")
            return True

        except Exception as e:
            logger.warning("Failed to detect GPU availability: %s", e)
            return False

    def _get_content_hash(self, text: str) -> str:
        """Generate a hash of content for cache key."""
        return calculate_content_hash(text)

    def generate_embedding(self, text: str, use_cache: bool = True) -> list[float] | None:
        """
        Generate embeddings for a given text using Ollama.

        Args:
            text: The text to generate embeddings for
            use_cache: Whether to use cached embeddings (default True)

        Returns:
            List of floats representing the embedding, or None if unavailable
        """
        if not self.is_available() or self.client is None:
            logger.debug("Ollama not available, skipping embedding generation")
            return None

        # Check cache first
        if use_cache:
            content_hash = self._get_content_hash(text)
            if content_hash in self.embedding_cache:
                logger.debug("Using cached embedding for content")
                return self.embedding_cache[content_hash]

        try:
            response = self.client.embeddings(
                model=self.embed_model,  # Use dedicated embedding model
                prompt=text,
                options={"num_ctx": self.num_ctx}  # Use consistent context size
            )
            embedding: list[float] = response["embedding"]

            # Cache the result
            if use_cache:
                content_hash = self._get_content_hash(text)
                self.embedding_cache[content_hash] = embedding
                logger.debug("Cached embedding (total cached: %d)", len(self.embedding_cache))

            return embedding
        except Exception as e:
            logger.error("Failed to generate embedding: %s", e)
            return None

    def semantic_search_with_precomputed_embeddings(
        self,
        query: str,
        documents_with_embeddings: list[dict[str, Any]],
        top_k: int = 5
    ) -> list[dict[str, Any]]:
        """
        Perform semantic search using pre-computed embeddings (FAST!).

        This method expects documents to already have their embeddings computed
        and stored in Neo4j. Only generates the query embedding (~5-10s).

        Args:
            query: The search query
            documents_with_embeddings: List of dicts with 'id', 'embedding', and other fields
            top_k: Number of top results to return

        Returns:
            List of documents sorted by similarity with 'score' field added
        """
        if not self.is_available():
            logger.debug("Ollama not available, cannot perform semantic search")
            return []

        try:
            logger.info("Starting semantic search with precomputed embeddings: query='%s', corpus_size=%d",
                       query, len(documents_with_embeddings))

            # Generate embedding for query only
            logger.info("Generating embedding for query...")
            query_embedding = self.generate_embedding(query, use_cache=False)
            if not query_embedding:
                logger.warning("Failed to generate query embedding")
                return []
            logger.info("Query embedding generated successfully")

            # Calculate similarities using precomputed embeddings
            logger.info("Computing similarities with %d precomputed embeddings...", len(documents_with_embeddings))
            scored_docs = []

            for doc in documents_with_embeddings:
                doc_embedding = doc.get("embedding")
                if not doc_embedding:
                    logger.warning("Document %s missing embedding, skipping", doc.get("id", "unknown"))
                    continue

                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_embedding, doc_embedding)
                # Add score to document
                doc_with_score = {**doc, "score": similarity}
                scored_docs.append((similarity, doc_with_score))

            # Sort by similarity (highest first) and return top_k
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            results = [doc for _, doc in scored_docs[:top_k]]

            logger.info("Semantic search complete: returning %d results", len(results))
            if results:
                logger.info("Top result: '%s' (score: %.3f)",
                           results[0].get("title", "Untitled"),
                           results[0].get("score", 0.0))

            return results

        except Exception as e:
            logger.error("Semantic search failed: %s", e)
            return []

    def semantic_search(
        self, query: str, documents: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """
        Perform semantic search on documents using embeddings.

        Args:
            query: The search query
            documents: List of documents with 'content' field
            top_k: Number of top results to return

        Returns:
            List of documents sorted by similarity (most similar first)
        """
        if not self.is_available():
            logger.debug("Ollama not available, falling back to basic search")
            # Fallback to basic text search
            query_lower = query.lower()
            results = [
                doc for doc in documents if query_lower in doc.get("content", "").lower()
            ]
            return results[:top_k]

        try:
            logger.info("Starting semantic search: query='%s', corpus_size=%d", query, len(documents))

            # Generate embedding for query
            logger.info("Generating embedding for query...")
            query_embedding = self.generate_embedding(query, use_cache=False)  # Don't cache queries
            if not query_embedding:
                logger.warning("Failed to generate query embedding")
                return []
            logger.info("Query embedding generated successfully")

            # Generate embeddings for all documents (WITH CACHING - major performance win!)
            logger.info("Generating embeddings for %d documents...", len(documents))
            scored_docs = []
            embeddings_generated = 0
            embeddings_cached = 0

            for idx, doc in enumerate(documents, 1):
                content = doc.get("content", "")
                content_hash = self._get_content_hash(content)
                was_cached = content_hash in self.embedding_cache

                doc_embedding = self.generate_embedding(content, use_cache=True)

                if was_cached:
                    embeddings_cached += 1
                else:
                    embeddings_generated += 1
                    logger.info("  [%d/%d] Generated embedding for: %s", idx, len(documents), doc.get("title", "Untitled")[:50])

                if doc_embedding:
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(query_embedding, doc_embedding)
                    scored_docs.append((similarity, doc))

            logger.info("Embeddings complete: %d generated, %d cached, %d total",
                       embeddings_generated, embeddings_cached, len(documents))

            # Sort by similarity (highest first) and return top_k
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            results = [doc for _, doc in scored_docs[:top_k]]

            logger.info("Semantic search complete: returning %d results", len(results))
            if results:
                logger.info("Top result: '%s' (score: %.3f)",
                           results[0].get("title", "Untitled"),
                           scored_docs[0][0])

            return results

        except Exception as e:
            logger.error("Semantic search failed: %s", e)
            return []

    def ask_question(
        self,
        question: str,
        context_documents: list[dict[str, Any]],
        allow_general_knowledge: bool = True
    ) -> str | None:
        """
        Answer a question based on context documents and/or general knowledge.

        Args:
            question: The question to answer
            context_documents: List of relevant documents to use as context
            allow_general_knowledge: If True, allows answering from general knowledge
                                    when KB doesn't have the answer

        Returns:
            The answer as a string, or None if unavailable
        """
        if not self.is_available() or self.client is None:
            logger.debug("Ollama not available, cannot answer question")
            return None

        try:
            # Build context from documents (truncate long content to keep prompt manageable)
            context_parts = []
            max_content_length = 1000  # Characters per document to prevent prompt overflow

            for i, doc in enumerate(context_documents[:5], 1):  # Use top 5 docs
                title = doc.get("title", f"Document {i}")
                content = doc.get("content", "")

                # Truncate very long documents to keep prompt size reasonable
                if len(content) > max_content_length:
                    content = content[:max_content_length] + "... [truncated]"

                context_parts.append(f"### {title}\n{content}\n")

            context = "\n".join(context_parts) if context_parts else "No relevant documents found."

            # Create smart hybrid prompt
            if allow_general_knowledge:
                prompt = f"""You are a helpful AI assistant with access to a knowledge base.

Knowledge Base Articles:
{context}

Question: {question}

Instructions:
1. First check if the knowledge base articles contain relevant information
2. If the KB has the answer, cite it and use that information
3. If the KB doesn't have enough info, you may answer from your general knowledge
4. Be clear about whether you're using KB articles or general knowledge
5. If you can't answer confidently, say so

Answer:"""
            else:
                # KB-only mode (stricter)
                prompt = f"""Based on the following knowledge base articles, please answer the question.
If the answer is not in the provided articles, say "I don't have enough information in the knowledge base to answer that question."

Knowledge Base:
{context}

Question: {question}

Answer:"""

            # Generate response with larger context window for Q&A (needs room for context docs)
            response = self.client.generate(
                model=self.chat_model,  # Use chat model for Q&A
                prompt=prompt,
                options={
                    "num_ctx": 8192,  # Larger context for Q&A with multiple documents
                    "num_predict": 512  # Limit response length for faster generation
                }
            )
            answer: str = response["response"]
            return answer

        except Exception as e:
            logger.error("Failed to answer question: %s", e)
            return None

    def summarize_article(self, content: str) -> str | None:
        """
        Generate a summary of an article.

        Args:
            content: The article content to summarize

        Returns:
            A summary of the article, or None if unavailable
        """
        if not self.is_available() or self.client is None:
            logger.debug("Ollama not available, cannot summarize")
            return None

        try:
            prompt = f"""Please provide a concise summary (2-3 sentences) of the following article:

{content}

Summary:"""

            response = self.client.generate(
                model=self.chat_model,  # Use chat model for summarization
                prompt=prompt,
                options={"num_ctx": self.num_ctx}
            )
            summary: str = response["response"]
            return summary

        except Exception as e:
            logger.error("Failed to summarize article: %s", e)
            return None

    def warmup(self) -> bool:
        """
        Warm up the Ollama model by sending a small test request.

        This forces the llama runner to start (takes ~17 seconds) so that
        subsequent requests are faster. Call this when the user opens the
        Q&A panel or on app startup.

        Returns:
            True if warmup succeeded, False otherwise
        """
        if not self.is_available() or self.client is None:
            logger.debug("Ollama not available, skipping warmup")
            return False

        try:
            logger.info("Warming up Ollama chat model (this takes ~15-20 seconds)...")
            # Send a minimal prompt to start the runner with our context window setting
            self.client.generate(
                model=self.chat_model,  # Warm up chat model
                prompt="Hi",
                options={
                    "num_predict": 1,  # Only generate 1 token
                    "num_ctx": self.num_ctx  # Set context window for runner initialization
                }
            )
            logger.info("Ollama model warmed up and ready")
            return True
        except Exception as e:
            logger.error("Failed to warm up Ollama model: %s", e)
            return False

    def clear_cache(self) -> int:
        """
        Clear the embedding cache.

        Returns:
            Number of cached embeddings that were cleared
        """
        count = len(self.embedding_cache)
        self.embedding_cache.clear()
        logger.info("Cleared %d cached embeddings", count)
        return count

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0 to 1)
        """
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        similarity: float = dot_product / (magnitude1 * magnitude2)
        return similarity


# Global instance
ollama_client = OllamaClient()


def get_ollama_client() -> OllamaClient:
    """Get the global Ollama client instance."""
    return ollama_client
