"""Business logic for the Library (curated resource catalog, #294).

Mirrors NotesService: a thin orchestration layer over the Neo4j adapter. Library
entries are standalone :LibraryEntry nodes, kept separate from the notes graph.
"""

import logging
from typing import Any

from adapters.neo4j import get_neo4j_adapter
from note_id_generator import get_id_generator

logger = logging.getLogger(__name__)


class LibraryService:
    """Service for managing Library entries.

    Requires Neo4j to be available; raises if it is not.
    """

    def __init__(self) -> None:
        """Initialize the library service."""
        self.neo4j = get_neo4j_adapter()
        self.id_generator = get_id_generator()

        if self.neo4j.is_available():
            logger.info("LibraryService initialized with Neo4j")
        else:
            logger.warning("LibraryService initialized but Neo4j is not available")

    def _require_neo4j(self) -> None:
        """Raise error if Neo4j is not available."""
        if not self.neo4j.is_available():
            raise RuntimeError(
                "Neo4j is required but not available. "
                "Ensure Neo4j is running: docker compose up neo4j"
            )

    def create_entry(
        self,
        title: str,
        source_url: str = "",
        author: str = "",
        type: str = "other",
        summary: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new Library entry.

        Returns:
            Created entry dict

        Raises:
            RuntimeError: If Neo4j is not available
        """
        self._require_neo4j()

        existing_ids = self.neo4j.get_all_library_entry_ids()
        entry_id = self.id_generator.generate(existing_ids)

        entry = self.neo4j.create_library_entry(
            entry_id=entry_id,
            title=title,
            source_url=source_url,
            author=author,
            type=type,
            summary=summary,
            tags=tags or [],
        )
        logger.info("Created library entry: %s", entry_id)
        return entry

    def get_entry(self, entry_id: str) -> dict[str, Any] | None:
        """Get a Library entry by ID."""
        self._require_neo4j()
        return self.neo4j.get_library_entry(entry_id)

    def list_entries(
        self,
        type: str | None = None,
        tag: str | None = None,
    ) -> list[dict[str, Any]]:
        """List Library entries, newest first, optionally filtered."""
        self._require_neo4j()
        return self.neo4j.list_library_entries(type=type, tag=tag)

    def update_entry(
        self,
        entry_id: str,
        title: str | None = None,
        source_url: str | None = None,
        author: str | None = None,
        type: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Update a Library entry. Only provided fields change."""
        self._require_neo4j()

        if not self.neo4j.get_library_entry(entry_id):
            return None

        updated = self.neo4j.update_library_entry(
            entry_id=entry_id,
            title=title,
            source_url=source_url,
            author=author,
            type=type,
            summary=summary,
            tags=tags,
        )
        logger.info("Updated library entry: %s", entry_id)
        return updated

    def delete_entry(self, entry_id: str) -> bool:
        """Delete a Library entry."""
        self._require_neo4j()

        if not self.neo4j.get_library_entry(entry_id):
            return False

        deleted = self.neo4j.delete_library_entry(entry_id)
        if deleted:
            logger.info("Deleted library entry: %s", entry_id)
        return deleted


_library_service: LibraryService | None = None


def get_library_service() -> LibraryService:
    """Get global LibraryService instance (singleton)."""
    global _library_service
    if _library_service is None:
        _library_service = LibraryService()
    return _library_service
