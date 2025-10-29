"""Business logic for Zettelkasten notes operations."""

import json
import logging
from typing import Any

from adapters.neo4j import get_neo4j_adapter
from database import get_database
from embedding_sync import EMBEDDING_VERSION
from note_id_generator import get_id_generator
from ollama_client import get_ollama_client
from wikilink_parser import get_wikilink_parser

logger = logging.getLogger(__name__)


class NotesService:
    """Service for managing Zettelkasten notes."""

    def __init__(self) -> None:
        """Initialize notes service."""
        self.db = get_database()  # Fallback for when Neo4j unavailable

        # Try to initialize Neo4j adapter
        self.neo4j = get_neo4j_adapter()
        if self.neo4j.is_available():
            logger.info("Using Neo4j for persistent notes")
        else:
            logger.info("Using SQLite for persistent notes (Neo4j unavailable)")

        self.id_generator = get_id_generator()
        self.wikilink_parser = get_wikilink_parser()
        self.ollama = get_ollama_client()  # For real-time embedding generation

    def create_note(
        self,
        content: str,
        title: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new persistent note.

        Args:
            content: Markdown content
            title: Optional title
            tags: Optional tags

        Returns:
            Created note dict
        """
        # Extract links from content
        links = self.wikilink_parser.extract_links(content)

        # Generate unique ID
        existing_ids = self._get_all_note_ids()
        note_id = self.id_generator.generate(existing_ids)

        # Create persistent note in Neo4j
        if self.neo4j and self.neo4j.is_available():
            note = self.neo4j.create_note(
                note_id=note_id,
                content=content,
                title=title,
                author="Erik",
                tags=tags or [],
                links=links,
            )
            logger.info("Created persistent note in Neo4j: %s", note_id)

            # Generate and store embedding for immediate semantic search availability
            self._generate_and_store_embedding(note_id, content)

            return note
        else:
            # Fallback to SQLite if Neo4j unavailable
            self.db.execute(
                """
                INSERT INTO notes (id, title, content, author, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    note_id,
                    title,
                    content,
                    "Erik",
                    json.dumps(tags or []),
                    json.dumps({"links": links}),
                ),
            )
            self.db.commit()

            # Create links in database
            if links:
                self._create_links(note_id, links)

            logger.info("Created persistent note in SQLite (Neo4j unavailable): %s", note_id)

            # Return created note (must exist since we just created it)
            retrieved_note: dict[str, Any] | None = self.get_note(note_id)
            if retrieved_note is None:
                raise RuntimeError(f"Failed to retrieve note {note_id} immediately after creation")
            return retrieved_note

    def get_note(self, note_id: str) -> dict[str, Any] | None:
        """Get note by ID.

        Args:
            note_id: Note ID

        Returns:
            Note dict or None if not found
        """
        # Check persistent notes
        if self.neo4j and self.neo4j.is_available():
            note = self.neo4j.get_note(note_id)
            if note:
                return note
        else:
            # Fallback to SQLite
            note = self.db.fetchone("SELECT * FROM notes WHERE id = ?", (note_id,))
            if note:
                return self._db_row_to_dict(note)

        return None

    def list_notes(self) -> list[dict[str, Any]]:
        """List all notes, ordered by created_at descending.

        Returns:
            List of note dicts, newest first
        """
        # Get persistent notes
        if self.neo4j and self.neo4j.is_available():
            notes = self.neo4j.list_notes()
        else:
            # Fallback to SQLite
            persistent = self.db.fetchall(
                "SELECT * FROM notes ORDER BY created_at DESC"
            )
            notes = [self._db_row_to_dict(row) for row in persistent]

        return notes

    def update_note(
        self,
        note_id: str,
        content: str,
        title: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Update note content.

        Args:
            note_id: Note ID
            content: New content
            title: New title
            tags: New tags

        Returns:
            Updated note dict or None if not found
        """
        # Extract new links
        links = self.wikilink_parser.extract_links(content)

        # Update in Neo4j
        if self.neo4j and self.neo4j.is_available():
            note = self.neo4j.get_note(note_id)
            if note:
                updated = self.neo4j.update_note(
                    note_id=note_id,
                    content=content,
                    title=title,
                    tags=tags,
                    links=links,
                )
                logger.info("Updated persistent note in Neo4j: %s", note_id)

                # Regenerate embedding after update for accurate semantic search
                self._generate_and_store_embedding(note_id, content)

                return updated
        else:
            # Fallback to SQLite
            note = self.db.fetchone("SELECT * FROM notes WHERE id = ?", (note_id,))
            if note:
                self.db.execute(
                    """
                    UPDATE notes
                    SET content = ?, title = ?, tags = ?, metadata = ?
                    WHERE id = ?
                    """,
                    (
                        content,
                        title,
                        json.dumps(tags or []),
                        json.dumps({"links": links}),
                        note_id,
                    ),
                )
                self.db.commit()

                # Update links
                self._delete_links(note_id)
                if links:
                    self._create_links(note_id, links)

                logger.info("Updated persistent note in SQLite: %s", note_id)
                return self.get_note(note_id)

        return None

    def delete_note(self, note_id: str) -> bool:
        """Delete note.

        Args:
            note_id: Note ID

        Returns:
            True if deleted, False if not found
        """
        # Delete from Neo4j
        if self.neo4j and self.neo4j.is_available():
            note = self.neo4j.get_note(note_id)
            if note:
                deleted = self.neo4j.delete_note(note_id)
                if deleted:
                    logger.info("Deleted persistent note from Neo4j: %s", note_id)
                return deleted
        else:
            # Fallback to SQLite
            note = self.db.fetchone("SELECT * FROM notes WHERE id = ?", (note_id,))
            if note:
                self.db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
                self.db.commit()
                logger.info("Deleted persistent note from SQLite: %s", note_id)
                return True

        return False

    def get_backlinks(self, note_id: str) -> list[dict[str, Any]]:
        """Get notes that link to this note.

        Args:
            note_id: Target note ID

        Returns:
            List of notes with links to this note
        """
        # Query database backlinks
        if self.neo4j and self.neo4j.is_available():
            return self.neo4j.get_backlinks(note_id)
        else:
            # Fallback to SQLite
            backlinks = self.db.fetchall(
                """
                SELECT n.* FROM notes n
                JOIN note_links l ON n.id = l.source_id
                WHERE l.target_id = ?
                """,
                (note_id,),
            )

            return [self._db_row_to_dict(row) for row in backlinks]

    def get_outbound_links(self, note_id: str) -> list[dict[str, Any]]:
        """Get notes this note links to.

        Args:
            note_id: Source note ID

        Returns:
            List of linked notes
        """
        if self.neo4j and self.neo4j.is_available():
            return self.neo4j.get_outbound_links(note_id)
        else:
            # Fallback to SQLite
            links = self.db.fetchall(
                """
                SELECT n.* FROM notes n
                JOIN note_links l ON n.id = l.target_id
                WHERE l.source_id = ?
                """,
                (note_id,),
            )

            return [self._db_row_to_dict(row) for row in links]

    def _get_all_note_ids(self) -> set[str]:
        """Get all existing note IDs (for collision detection)."""
        if self.neo4j and self.neo4j.is_available():
            return self.neo4j.get_all_note_ids()
        else:
            # Fallback to SQLite
            persistent = self.db.fetchall("SELECT id FROM notes")
            return {row["id"] for row in persistent}

    def _generate_and_store_embedding(self, note_id: str, content: str) -> None:
        """Generate and store embedding for a note in Neo4j.

        This is called automatically when creating or updating notes to ensure
        embeddings are immediately available for semantic search.

        Args:
            note_id: Note ID
            content: Note content to generate embedding from
        """
        # Only generate if both Neo4j and Ollama are available
        if not (self.neo4j and self.neo4j.is_available()):
            logger.debug("Skipping embedding generation for %s (Neo4j unavailable)", note_id)
            return

        if not self.ollama.is_available():
            logger.debug("Skipping embedding generation for %s (Ollama unavailable)", note_id)
            return

        try:
            logger.debug("Generating embedding for note: %s", note_id)
            embedding = self.ollama.generate_embedding(content, use_cache=True)

            if embedding:
                self.neo4j.store_embedding(
                    "Note",
                    note_id,
                    embedding,
                    self.ollama.model,
                    EMBEDDING_VERSION
                )
                logger.info("Generated and stored embedding for note: %s", note_id)
            else:
                logger.warning("Failed to generate embedding for note: %s", note_id)
        except Exception as e:
            # Don't fail note creation/update if embedding generation fails
            logger.error("Error generating embedding for note %s: %s", note_id, e)

    def _create_links(self, source_id: str, target_ids: list[str]) -> None:
        """Create links in database."""
        for target_id in target_ids:
            try:
                self.db.execute(
                    "INSERT INTO note_links (source_id, target_id) VALUES (?, ?)",
                    (source_id, target_id),
                )
            except Exception:
                # Ignore duplicate link errors
                logger.debug("Link already exists: %s -> %s", source_id, target_id)

        self.db.commit()

    def _delete_links(self, source_id: str) -> None:
        """Delete all outbound links from a note."""
        self.db.execute("DELETE FROM note_links WHERE source_id = ?", (source_id,))
        self.db.commit()

    def _db_row_to_dict(self, row: dict[str, Any]) -> dict[str, Any]:
        """Convert database row to note dict."""
        metadata = json.loads(row.get("metadata", "{}"))
        return {
            "id": row["id"],
            "title": row.get("title"),
            "content": row["content"],
            "author": row.get("author", "Erik"),
            "tags": json.loads(row.get("tags", "[]")),
            "created_at": row["created_at"],
            "updated_at": row.get("updated_at", row["created_at"]),
            "links": metadata.get("links", []),
        }


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
