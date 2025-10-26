"""In-memory storage for ephemeral visitor notes with memory limits."""

import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EphemeralNote:
    """Ephemeral note created by anonymous visitor."""

    id: str
    title: str
    content: str
    session_id: str
    created_at: float
    updated_at: float
    links: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


class EphemeralNotesStore:
    """In-memory storage for visitor notes with memory limits."""

    def __init__(self, max_memory_mb: int = 500, max_notes: int = 10000):
        """Initialize ephemeral notes store.

        Args:
            max_memory_mb: Maximum memory usage in MB (default 500)
            max_notes: Maximum total notes across all sessions (default 10000)
        """
        self.notes: dict[str, EphemeralNote] = {}
        self.sessions: dict[str, list[str]] = {}  # session_id -> [note_ids]
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.max_notes = max_notes

        logger.info(
            "EphemeralNotesStore initialized: max %d MB, max %d notes",
            max_memory_mb,
            max_notes,
        )

    def add_note(self, note: EphemeralNote) -> bool:
        """Add note if limits not exceeded.

        Args:
            note: EphemeralNote to add

        Returns:
            True if added successfully, False if limits exceeded
        """
        # Check note limit
        if len(self.notes) >= self.max_notes:
            logger.warning(
                "Max notes limit reached (%d), evicting oldest", self.max_notes
            )
            self._evict_oldest(1)

        # Check memory limit
        memory_usage = self.get_memory_usage()
        estimated_note_size = sys.getsizeof(note.content) + sys.getsizeof(note.title)

        if memory_usage + estimated_note_size > self.max_memory_bytes:
            logger.warning(
                "Memory limit approaching (%d MB), evicting oldest",
                memory_usage // (1024 * 1024),
            )
            self._evict_oldest(5)  # Evict 5 notes at a time

        # Add note
        self.notes[note.id] = note

        # Track by session
        if note.session_id not in self.sessions:
            self.sessions[note.session_id] = []
        self.sessions[note.session_id].append(note.id)

        logger.debug(
            "Added ephemeral note %s for session %s",
            note.id,
            note.session_id[:8] + "...",
        )
        return True

    def get_note(self, note_id: str) -> EphemeralNote | None:
        """Get note by ID.

        Args:
            note_id: Note ID

        Returns:
            EphemeralNote or None if not found
        """
        return self.notes.get(note_id)

    def get_session_notes(self, session_id: str) -> list[EphemeralNote]:
        """Get all notes for a session.

        Args:
            session_id: Session ID

        Returns:
            List of EphemeralNote objects
        """
        note_ids = self.sessions.get(session_id, [])
        return [self.notes[nid] for nid in note_ids if nid in self.notes]

    def get_all_notes(self) -> list[EphemeralNote]:
        """Get all ephemeral notes.

        Returns:
            List of all EphemeralNote objects
        """
        return list(self.notes.values())

    def update_note(self, note_id: str, content: str, links: list[str]) -> bool:
        """Update note content and links.

        Args:
            note_id: Note ID
            content: New content
            links: New links

        Returns:
            True if updated, False if note not found
        """
        note = self.notes.get(note_id)
        if not note:
            return False

        note.content = content
        note.links = links
        note.updated_at = time.time()

        logger.debug("Updated ephemeral note %s", note_id)
        return True

    def delete_note(self, note_id: str) -> bool:
        """Delete note by ID.

        Args:
            note_id: Note ID

        Returns:
            True if deleted, False if not found
        """
        note = self.notes.pop(note_id, None)
        if not note:
            return False

        # Remove from session tracking
        if note.session_id in self.sessions:
            self.sessions[note.session_id].remove(note_id)
            if not self.sessions[note.session_id]:
                del self.sessions[note.session_id]

        logger.debug("Deleted ephemeral note %s", note_id)
        return True

    def clear_session(self, session_id: str) -> int:
        """Remove all notes from a session.

        Args:
            session_id: Session ID

        Returns:
            Number of notes deleted
        """
        note_ids = self.sessions.get(session_id, [])
        count = 0

        for note_id in note_ids:
            if self.notes.pop(note_id, None):
                count += 1

        self.sessions.pop(session_id, None)

        logger.info("Cleared %d notes from session %s", count, session_id[:8] + "...")
        return count

    def clear_all(self) -> int:
        """Clear all ephemeral notes (admin function).

        Returns:
            Number of notes deleted
        """
        count = len(self.notes)
        self.notes.clear()
        self.sessions.clear()

        logger.warning("Cleared all %d ephemeral notes (admin action)", count)
        return count

    def _evict_oldest(self, count: int = 1) -> int:
        """Evict oldest notes to free memory.

        Args:
            count: Number of notes to evict

        Returns:
            Number of notes evicted
        """
        if not self.notes:
            return 0

        # Sort by creation time
        sorted_notes = sorted(
            self.notes.items(), key=lambda x: x[1].created_at
        )

        evicted = 0
        for note_id, _ in sorted_notes[:count]:
            if self.delete_note(note_id):
                evicted += 1

        logger.info("Evicted %d oldest ephemeral notes", evicted)
        return evicted

    def get_memory_usage(self) -> int:
        """Calculate current memory usage in bytes.

        Returns:
            Memory usage in bytes
        """
        total = 0
        for note in self.notes.values():
            total += sys.getsizeof(note.id)
            total += sys.getsizeof(note.title)
            total += sys.getsizeof(note.content)
            total += sys.getsizeof(note.session_id)
            total += sys.getsizeof(note.links)
            total += sys.getsizeof(note.tags)

        return total

    def get_stats(self) -> dict[str, Any]:
        """Get store statistics.

        Returns:
            Dict with stats (total_notes, total_sessions, memory_usage_mb, etc.)
        """
        memory_bytes = self.get_memory_usage()
        memory_mb = memory_bytes / (1024 * 1024)

        return {
            "total_notes": len(self.notes),
            "total_sessions": len(self.sessions),
            "memory_usage_bytes": memory_bytes,
            "memory_usage_mb": round(memory_mb, 2),
            "memory_limit_mb": self.max_memory_bytes // (1024 * 1024),
            "memory_percent": round((memory_bytes / self.max_memory_bytes) * 100, 1),
            "notes_limit": self.max_notes,
        }


# Global instance
_store: EphemeralNotesStore | None = None


def get_ephemeral_store() -> EphemeralNotesStore:
    """Get global ephemeral notes store (singleton).

    Returns:
        EphemeralNotesStore instance
    """
    global _store
    if _store is None:
        _store = EphemeralNotesStore()
    return _store
