"""Seed local Neo4j with notes from production.

This script reads notes from a JSON file (downloaded from production API)
and creates them in the local Neo4j database.

Usage:
    docker compose exec backend python scripts/seed_from_production.py /path/to/notes.json
"""

import json
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.neo4j import get_neo4j_adapter

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def seed_notes(notes_file: Path) -> None:
    """Seed local Neo4j with notes from JSON file.

    Args:
        notes_file: Path to JSON file with notes array
    """
    logger.info("=== Seeding Local Neo4j from Production ===\n")

    # Load notes from file
    with open(notes_file) as f:
        notes = json.load(f)

    logger.info(f"Loaded {len(notes)} notes from {notes_file}")

    # Get Neo4j adapter
    neo4j = get_neo4j_adapter()

    if not neo4j.is_available():
        logger.error("❌ Neo4j is not available. Cannot seed notes.")
        sys.exit(1)

    # Create each note
    created_count = 0
    skipped_count = 0

    for note in notes:
        note_id = note["id"]

        # Check if note already exists
        existing = neo4j.get_note(note_id)
        if existing:
            logger.info(f"⏭  Skipping {note_id} (already exists)")
            skipped_count += 1
            continue

        # Create the note (without embedding for now)
        try:
            neo4j.create_note(
                note_id=note_id,
                title=note.get("title", ""),
                content=note.get("content", ""),
                author=note.get("author", "admin"),
                tags=note.get("tags", []),
                links=note.get("links", []),
            )
            logger.info(f"✓ Created {note_id}: {note.get('title', 'Untitled')}")
            created_count += 1
        except Exception as e:
            logger.error(f"✗ Failed to create {note_id}: {e}")

    logger.info(f"\n{'=' * 50}")
    logger.info(f"Summary: Created {created_count}, Skipped {skipped_count}")
    logger.info(f"{'=' * 50}")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        logger.error("Usage: python seed_from_production.py <notes.json>")
        sys.exit(1)

    notes_file = Path(sys.argv[1])
    if not notes_file.exists():
        logger.error(f"File not found: {notes_file}")
        sys.exit(1)

    seed_notes(notes_file)


if __name__ == "__main__":
    main()
