"""Business logic for Zettelkasten notes operations."""

import logging
from typing import Any

from adapters.neo4j import get_neo4j_adapter
from core import ai as ai_core
from embedding_sync import EMBEDDING_VERSION
from note_id_generator import get_id_generator
from ollama_client import get_ollama_client
from wikilink_parser import get_wikilink_parser

logger = logging.getLogger(__name__)


class NotesService:
    """Service for managing Zettelkasten notes.

    Requires Neo4j to be available. Will raise an error if Neo4j is not connected.
    """

    def __init__(self) -> None:
        """Initialize notes service."""
        self.neo4j = get_neo4j_adapter()
        self.id_generator = get_id_generator()
        self.wikilink_parser = get_wikilink_parser()
        self.ollama = get_ollama_client()

        if self.neo4j.is_available():
            logger.info("NotesService initialized with Neo4j")
        else:
            logger.warning("NotesService initialized but Neo4j is not available")

    def _require_neo4j(self) -> None:
        """Raise error if Neo4j is not available."""
        if not self.neo4j.is_available():
            raise RuntimeError(
                "Neo4j is required but not available. "
                "Ensure Neo4j is running: docker compose up neo4j"
            )

    def get_note_count(self) -> int:
        """Get total number of notes in the database.

        Returns:
            Number of notes, or 0 if Neo4j is unavailable
        """
        if not self.neo4j.is_available():
            return 0
        return self.neo4j.get_note_count()

    def create_note(
        self,
        content: str,
        title: str | None = None,
        tags: list[str] | None = None,
        is_reference: bool = False,
    ) -> dict[str, Any]:
        """Create a new persistent note.

        Args:
            content: Markdown content
            title: Optional title
            tags: Optional tags
            is_reference: True for quick references, False for insights (default)

        Returns:
            Created note dict

        Raises:
            RuntimeError: If Neo4j is not available
        """
        self._require_neo4j()

        # Extract links from content
        links = self.wikilink_parser.extract_links(content)

        # Generate unique ID
        existing_ids = self._get_all_note_ids()
        note_id = self.id_generator.generate(existing_ids)

        # Create note in Neo4j
        note = self.neo4j.create_note(
            note_id=note_id,
            content=content,
            title=title,
            author="Erik",
            tags=tags or [],
            links=links,
            is_reference=is_reference,
        )
        logger.info("Created note: %s", note_id)

        # Note: Embedding and AI content generation moved to background tasks
        # in routers/notes.py to avoid blocking the API response

        return note

    def get_note(self, note_id: str) -> dict[str, Any] | None:
        """Get note by ID.

        Args:
            note_id: Note ID

        Returns:
            Note dict or None if not found
        """
        self._require_neo4j()
        return self.neo4j.get_note(note_id)

    def list_notes(
        self,
        is_reference: bool | None = None,
        include_full_content: bool = True,
        include_embedding: bool = False,
        minimal: bool = False,
    ) -> list[dict[str, Any]]:
        """List all notes, ordered by created_at descending.

        Args:
            is_reference: Filter by type (True=references, False=insights, None=all)
            include_full_content: If False, return content preview only (default: True)
            include_embedding: If True, include embedding vectors (default: False)
            minimal: If True, return only id+title (default: False)

        Returns:
            List of note dicts, newest first
        """
        self._require_neo4j()
        return self.neo4j.list_notes(
            is_reference=is_reference,
            include_full_content=include_full_content,
            include_embedding=include_embedding,
            minimal=minimal,
        )

    def update_note(
        self,
        note_id: str,
        content: str,
        title: str | None = None,
        tags: list[str] | None = None,
        is_reference: bool | None = None,
    ) -> dict[str, Any] | None:
        """Update note content.

        Args:
            note_id: Note ID
            content: New content
            title: New title
            tags: New tags
            is_reference: New reference status (None to keep existing)

        Returns:
            Updated note dict or None if not found
        """
        self._require_neo4j()

        # Check note exists
        note = self.neo4j.get_note(note_id)
        if not note:
            return None

        # Extract new links
        links = self.wikilink_parser.extract_links(content)

        # Update in Neo4j
        updated = self.neo4j.update_note(
            note_id=note_id,
            content=content,
            title=title,
            tags=tags,
            links=links,
            is_reference=is_reference,
        )
        logger.info("Updated note: %s", note_id)

        # Note: Embedding and AI content regeneration moved to background tasks
        # in routers/notes.py to avoid blocking the API response

        return updated

    def delete_note(self, note_id: str) -> bool:
        """Delete note.

        Args:
            note_id: Note ID

        Returns:
            True if deleted, False if not found
        """
        self._require_neo4j()

        note = self.neo4j.get_note(note_id)
        if not note:
            return False

        deleted = self.neo4j.delete_note(note_id)
        if deleted:
            logger.info("Deleted note: %s", note_id)
        return deleted

    def get_backlinks(self, note_id: str) -> list[dict[str, Any]]:
        """Get notes that link to this note.

        Args:
            note_id: Target note ID

        Returns:
            List of notes with links to this note
        """
        self._require_neo4j()
        return self.neo4j.get_backlinks(note_id)

    def get_outbound_links(self, note_id: str) -> list[dict[str, Any]]:
        """Get notes this note links to.

        Args:
            note_id: Source note ID

        Returns:
            List of linked notes
        """
        self._require_neo4j()
        return self.neo4j.get_outbound_links(note_id)

    def get_random_note(self) -> dict[str, Any] | None:
        """Get a random note for serendipitous discovery.

        Returns:
            Random note dict or None if no notes exist
        """
        self._require_neo4j()
        return self.neo4j.get_random_note()

    def get_orphan_notes(self) -> list[dict[str, Any]]:
        """Get orphan notes (notes with no links and no backlinks).

        Returns:
            List of orphan notes
        """
        self._require_neo4j()
        return self.neo4j.get_orphan_notes()

    def get_dead_end_notes(self) -> list[dict[str, Any]]:
        """Get dead-end notes (notes with no outbound links).

        Returns:
            List of dead-end notes
        """
        self._require_neo4j()
        return self.neo4j.get_dead_end_notes()

    def get_hub_notes(self, min_links: int = 3) -> list[dict[str, Any]]:
        """Get hub notes (notes with many outbound links).

        Args:
            min_links: Minimum number of outbound links

        Returns:
            List of hub notes with link counts
        """
        self._require_neo4j()
        return self.neo4j.get_hub_notes(min_links=min_links)

    def get_central_notes(self, min_backlinks: int = 3) -> list[dict[str, Any]]:
        """Get central concept notes (notes with many backlinks).

        Args:
            min_backlinks: Minimum number of backlinks

        Returns:
            List of central notes with backlink counts
        """
        self._require_neo4j()
        return self.neo4j.get_central_notes(min_backlinks=min_backlinks)

    def get_stale_notes(
        self, days_threshold: int = 60, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get notes not updated in the specified number of days.

        Args:
            days_threshold: Number of days since last update (default: 60)
            limit: Maximum number of notes to return (default: 50)

        Returns:
            List of stale notes sorted by oldest first
        """
        self._require_neo4j()
        return self.neo4j.get_stale_notes(days_threshold=days_threshold, limit=limit)

    def get_random_stale_note(self, days_threshold: int = 60) -> dict[str, Any] | None:
        """Get a random note not updated in the specified number of days.

        Args:
            days_threshold: Number of days since last update (default: 60)

        Returns:
            Random stale note or None if no stale notes exist
        """
        self._require_neo4j()
        return self.neo4j.get_random_stale_note(days_threshold=days_threshold)

    def mark_note_reviewed(self, note_id: str) -> dict[str, Any] | None:
        """Mark a note as reviewed by updating its updated_at timestamp.

        This resets the staleness clock without requiring content changes.

        Args:
            note_id: Note ID

        Returns:
            Updated note dict or None if not found
        """
        self._require_neo4j()
        result = self.neo4j.touch_note_updated_at(note_id)
        if result:
            logger.info("Marked note as reviewed: %s", note_id)
        return result

    # ===== INSPIRE/CONTENT SUGGESTION METHODS =====

    def get_notes_with_stats(self) -> list[dict[str, Any]]:
        """Get all notes with content length, link count, and backlink count.

        Returns:
            List of notes with stats fields for gap analysis
        """
        self._require_neo4j()
        return self.neo4j.get_notes_with_stats()

    def get_notes_with_embeddings(self) -> list[dict[str, Any]]:
        """Get notes that have embeddings for similarity analysis.

        Returns:
            List of dicts with id, title, embedding
        """
        self._require_neo4j()
        return self.neo4j.get_notes_with_embeddings()

    def get_all_links(self) -> dict[str, set[str]]:
        """Get all note links as adjacency dict.

        Returns:
            Dict mapping note_id -> set of linked note_ids (bidirectional)
        """
        self._require_neo4j()
        return self.neo4j.get_all_links()

    def _get_all_note_ids(self) -> set[str]:
        """Get all existing note IDs (for collision detection)."""
        self._require_neo4j()
        return self.neo4j.get_all_note_ids()

    def generate_embedding_for_note(self, note_id: str, content: str) -> None:
        """Generate and store embedding for a note in Neo4j.

        This can be called as a background task to avoid blocking API responses.
        Embeddings are stored in Neo4j for fast semantic search.

        Args:
            note_id: Note ID
            content: Note content to generate embedding from
        """
        import os

        # Skip in test mode to avoid hitting real Ollama
        if os.environ.get("TESTING") == "1":
            logger.debug("Skipping embedding generation for %s (test mode)", note_id)
            return

        if not self.ollama.is_available():
            logger.debug("Skipping embedding generation for %s (Ollama unavailable)", note_id)
            return

        try:
            logger.debug("Generating embedding for note: %s", note_id)
            embedding = self.ollama.generate_embedding(content, use_cache=True)

            if embedding:
                self.neo4j.store_embedding(
                    "Note", note_id, embedding, self.ollama.model, EMBEDDING_VERSION
                )
                logger.info("Generated and stored embedding for note: %s", note_id)
            else:
                logger.warning("Failed to generate embedding for note: %s", note_id)
        except Exception as e:
            # Don't fail note creation/update if embedding generation fails
            logger.error("Error generating embedding for note %s: %s", note_id, e)

    def generate_ai_content_for_note(self, note_id: str, content: str, title: str) -> None:
        """Generate and store AI summary and link suggestions for a note.

        This can be called as a background task to avoid blocking API responses.
        AI content (summary, link suggestions) is stored in Neo4j for fast retrieval.

        Args:
            note_id: Note ID
            content: Note content
            title: Note title
        """
        import os

        # Skip in test mode to avoid hitting real Ollama
        if os.environ.get("TESTING") == "1":
            logger.debug("Skipping AI content generation for %s (test mode)", note_id)
            return

        if not self.ollama.is_available():
            logger.debug("Skipping AI content generation for %s (Ollama unavailable)", note_id)
            return

        if not self.ollama.client:
            return

        # Generate summary
        summary = None
        try:
            logger.debug("Generating AI summary for note: %s", note_id)
            prompt = ai_core.build_summary_prompt(content, content_type="note")
            response = self.ollama.client.generate(
                model=self.ollama.chat_model,
                prompt=prompt,
                options={"num_ctx": 2048, "num_predict": 256},
            )
            summary = response.get("response", "").strip()
            if summary:
                logger.info("Generated AI summary for note: %s", note_id)
        except Exception as e:
            logger.error("Error generating summary for note %s: %s", note_id, e)

        # Generate link suggestions
        link_suggestions = None
        try:
            logger.debug("Generating link suggestions for note: %s", note_id)
            all_notes = self.list_notes(minimal=True)
            note_data = self.get_note(note_id)
            existing_links = note_data.get("links", []) if note_data else []

            candidate_notes = ai_core.filter_link_candidates(
                all_notes=all_notes, current_note_id=note_id, existing_links=existing_links
            )

            if candidate_notes:
                # Get full content for candidates (limited)
                candidates_with_content = []
                for cn in candidate_notes[:50]:
                    full_note = self.get_note(cn["id"])
                    if full_note:
                        candidates_with_content.append(full_note)

                prompt = ai_core.build_link_suggestion_prompt(
                    current_title=title or note_id,
                    current_content=content,
                    candidate_notes=candidates_with_content,
                    max_candidates=50,
                )

                response = self.ollama.client.generate(
                    model=self.ollama.structured_model,
                    prompt=prompt,
                    options={"num_ctx": 8192},
                )

                response_text = response.get("response", "")
                suggestions_data = ai_core.parse_json_response(response_text, expected_type="array")

                if suggestions_data and isinstance(suggestions_data, list):
                    # Validate and enrich suggestions
                    note_map = {n["id"]: n for n in candidates_with_content}
                    link_suggestions = []
                    for s in suggestions_data[:5]:
                        if isinstance(s, dict) and s.get("note_id") in note_map:
                            link_suggestions.append({
                                "note_id": s["note_id"],
                                "title": note_map[s["note_id"]].get("title", "Untitled"),
                                "confidence": s.get("confidence", 0.5),
                                "reason": s.get("reason", ""),
                            })
                    if link_suggestions:
                        logger.info(
                            "Generated %d link suggestions for note: %s",
                            len(link_suggestions),
                            note_id,
                        )
        except Exception as e:
            logger.error("Error generating link suggestions for note %s: %s", note_id, e)

        # Store in Neo4j
        if summary or link_suggestions:
            try:
                self.neo4j.store_ai_content(
                    node_type="Note",
                    node_id=note_id,
                    ai_summary=summary,
                    ai_link_suggestions=link_suggestions,
                )
                logger.info("Stored AI content for note: %s", note_id)
            except Exception as e:
                logger.error("Error storing AI content for note %s: %s", note_id, e)

    def get_ai_content(self, note_id: str) -> dict[str, Any] | None:
        """Get pre-computed AI content for a note.

        Args:
            note_id: Note ID

        Returns:
            Dict with ai_summary, ai_link_suggestions, and timestamps, or None
        """
        self._require_neo4j()
        return self.neo4j.get_ai_content("Note", note_id)

    def regenerate_ai_content(self, note_id: str) -> dict[str, Any] | None:
        """Force regeneration of AI content for a note.

        Args:
            note_id: Note ID

        Returns:
            Updated AI content or None if note not found
        """
        self._require_neo4j()
        note = self.get_note(note_id)
        if not note:
            return None

        # Clear existing and regenerate
        self.neo4j.clear_ai_content("Note", note_id)
        self.generate_ai_content_for_note(
            note_id=note_id,
            content=note.get("content", ""),
            title=note.get("title", ""),
        )

        return self.neo4j.get_ai_content("Note", note_id)


# Global instance
_service: NotesService | None = None


def get_notes_service() -> NotesService:
    """Get global NotesService instance (singleton).

    Returns:
        NotesService instance
    """
    global _service
    if _service is None:
        _service = NotesService()
    return _service
