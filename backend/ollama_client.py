"""Ollama integration for AI-powered features."""

import logging
from typing import Any

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OllamaClient:
    """Client for interacting with Ollama for embeddings and chat."""

    def __init__(self) -> None:
        """Initialize Ollama client."""
        self.enabled = settings.ollama_enabled
        self.host = settings.ollama_host
        self.model = settings.ollama_model
        self.client = None

        if self.enabled:
            try:
                import ollama

                # Test connection
                ollama.list(host=self.host)
                self.client = ollama
                logger.info("Ollama client initialized successfully at %s", self.host)
            except Exception as e:
                logger.warning("Failed to initialize Ollama client: %s", e)
                logger.warning("Ollama features will be disabled. Is Ollama running at %s?", self.host)
                self.enabled = False

    def is_available(self) -> bool:
        """Check if Ollama is available and enabled."""
        return self.enabled and self.client is not None

    def generate_embedding(self, text: str) -> list[float] | None:
        """
        Generate embeddings for a given text using Ollama.

        Args:
            text: The text to generate embeddings for

        Returns:
            List of floats representing the embedding, or None if unavailable
        """
        if not self.is_available():
            logger.debug("Ollama not available, skipping embedding generation")
            return None

        try:
            response = self.client.embeddings(model=self.model, prompt=text, host=self.host)
            return response["embedding"]
        except Exception as e:
            logger.error("Failed to generate embedding: %s", e)
            return None

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
            # Generate embedding for query
            query_embedding = self.generate_embedding(query)
            if not query_embedding:
                return []

            # Generate embeddings for all documents (in production, cache these)
            scored_docs = []
            for doc in documents:
                content = doc.get("content", "")
                doc_embedding = self.generate_embedding(content)
                if doc_embedding:
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(query_embedding, doc_embedding)
                    scored_docs.append((similarity, doc))

            # Sort by similarity (highest first) and return top_k
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            return [doc for _, doc in scored_docs[:top_k]]

        except Exception as e:
            logger.error("Semantic search failed: %s", e)
            return []

    def ask_question(
        self, question: str, context_documents: list[dict[str, Any]]
    ) -> str | None:
        """
        Answer a question based on the provided context documents.

        Args:
            question: The question to answer
            context_documents: List of relevant documents to use as context

        Returns:
            The answer as a string, or None if unavailable
        """
        if not self.is_available():
            logger.debug("Ollama not available, cannot answer question")
            return None

        try:
            # Build context from documents
            context_parts = []
            for i, doc in enumerate(context_documents[:5], 1):  # Use top 5 docs
                title = doc.get("title", f"Document {i}")
                content = doc.get("content", "")
                context_parts.append(f"### {title}\n{content}\n")

            context = "\n".join(context_parts)

            # Create prompt
            prompt = f"""Based on the following knowledge base articles, please answer the question.
If the answer is not in the provided articles, say "I don't have enough information to answer that question."

Knowledge Base:
{context}

Question: {question}

Answer:"""

            # Generate response
            response = self.client.generate(model=self.model, prompt=prompt, host=self.host)
            return response["response"]

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
        if not self.is_available():
            logger.debug("Ollama not available, cannot summarize")
            return None

        try:
            prompt = f"""Please provide a concise summary (2-3 sentences) of the following article:

{content}

Summary:"""

            response = self.client.generate(model=self.model, prompt=prompt, host=self.host)
            return response["response"]

        except Exception as e:
            logger.error("Failed to summarize article: %s", e)
            return None

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

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)


# Global instance
ollama_client = OllamaClient()


def get_ollama_client() -> OllamaClient:
    """Get the global Ollama client instance."""
    return ollama_client
