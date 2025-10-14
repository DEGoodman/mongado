"""Generate memorable adjective-noun IDs for Zettelkasten notes."""

import logging
import random
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class NoteIDGenerator:
    """Generate unique adjective-noun note IDs (e.g., curious-elephant)."""

    # Pattern for valid note IDs
    ID_PATTERN = re.compile(r"^[a-z]+-[a-z]+(-\d+)?$")

    def __init__(self) -> None:
        """Initialize generator with word lists."""
        self.adjectives = self._load_words("adjectives.txt")
        self.nouns = self._load_words("nouns.txt")

        logger.info(
            "NoteIDGenerator initialized: %d adjectives, %d nouns (%d combinations)",
            len(self.adjectives),
            len(self.nouns),
            len(self.adjectives) * len(self.nouns),
        )

    def _load_words(self, filename: str) -> list[str]:
        """Load word list from file.

        Args:
            filename: Name of word list file

        Returns:
            List of lowercase words
        """
        path = Path(__file__).parent / "data" / "wordlists" / filename

        if not path.exists():
            logger.error("Word list not found: %s", path)
            return []

        with open(path) as f:
            words = [line.strip().lower() for line in f if line.strip()]

        logger.debug("Loaded %d words from %s", len(words), filename)
        return words

    def generate(self, existing_ids: set[str] | None = None) -> str:
        """Generate unique note ID.

        Attempts to generate an adjective-noun ID, regenerating on collision.
        Falls back to adding a random number suffix if collisions persist.

        Args:
            existing_ids: Set of IDs to avoid (for collision detection)

        Returns:
            Unique note ID in format "adjective-noun" or "adjective-noun-1234"
        """
        if existing_ids is None:
            existing_ids = set()

        max_attempts = 100

        for attempt in range(max_attempts):
            adj = random.choice(self.adjectives)
            noun = random.choice(self.nouns)
            note_id = f"{adj}-{noun}"

            if note_id not in existing_ids:
                logger.debug("Generated note ID: %s (attempt %d)", note_id, attempt + 1)
                return note_id

        # Fallback: append random number
        adj = random.choice(self.adjectives)
        noun = random.choice(self.nouns)
        suffix = random.randint(1000, 9999)
        note_id = f"{adj}-{noun}-{suffix}"

        logger.warning("Used fallback ID with suffix: %s", note_id)
        return note_id

    def is_valid(self, note_id: str) -> bool:
        """Validate note ID format and word list membership.

        Args:
            note_id: Note ID to validate

        Returns:
            True if ID matches pattern and words are in lists
        """
        if not self.ID_PATTERN.match(note_id):
            return False

        parts = note_id.split("-")
        adj = parts[0]
        noun = parts[1]

        # Check word list membership
        return adj in self.adjectives and noun in self.nouns

    def parse(self, note_id: str) -> dict[str, str] | None:
        """Parse note ID into components.

        Args:
            note_id: Note ID to parse

        Returns:
            Dict with 'adjective', 'noun', and optional 'suffix' keys,
            or None if invalid
        """
        if not self.ID_PATTERN.match(note_id):
            return None

        parts = note_id.split("-")

        result = {
            "adjective": parts[0],
            "noun": parts[1],
        }

        if len(parts) > 2:
            result["suffix"] = parts[2]

        return result


# Global instance
_generator: NoteIDGenerator | None = None


def get_id_generator() -> NoteIDGenerator:
    """Get global Note ID generator instance (singleton).

    Returns:
        NoteIDGenerator instance
    """
    global _generator
    if _generator is None:
        _generator = NoteIDGenerator()
    return _generator
