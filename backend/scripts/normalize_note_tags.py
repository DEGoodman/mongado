"""Script to normalize tags in Neo4j notes to standard format.

This script should be run on the production server to update note tags:
    docker compose exec backend python scripts/normalize_note_tags.py

Standard format: lowercase-with-hyphens (no # prefix, no spaces)
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.neo4j import get_neo4j_adapter

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Tag normalization mapping
TAG_MAPPING = {
    "#1-1s": "one-on-ones",
    "1:1": "one-on-ones",
    "#management": "management",
    "Management": "management",
    "#metrics": "metrics",
    "#sre": "sre",
    "SRE": "sre",
    "#technical-debt": "technical-debt",
    "Technical Debt": "technical-debt",
    "ai": "ai",
    "AI": "ai",
    "architecture": "architecture",
    "Architecture": "architecture",
    "Agile": "agile",
    "Career": "career",
    "Engineering": "engineering",
    "Engineering Management": "engineering-management",
    "engineering-management": "engineering-management",
    "Interviewing": "interviewing",
    "knowledge-management": "knowledge-management",
    "Leadership": "leadership",
    "llm": "llm",
    "management": "management",
    "meta": "meta",
    "ollama": "ollama",
    "Operations": "operations",
    "ops": "sre",  # Consolidate ops -> sre
    "Performance": "performance",
    "pkm": "pkm",
    "productivity": "productivity",
    "Productivity": "productivity",
    "Programming": "programming",
    "Prioritization": "prioritization",
    "Software Development": "software-development",
    "System Design": "system-design",
    "zettelkasten": "zettelkasten",
}


def normalize_tag(tag: str) -> str:
    """Normalize a tag to standard format.

    Args:
        tag: Original tag string

    Returns:
        Normalized tag in lowercase-with-hyphens format
    """
    if tag in TAG_MAPPING:
        return TAG_MAPPING[tag]
    # Fallback: lowercase with hyphens
    return tag.lower().replace(" ", "-")


def main() -> None:
    """Main function to update all note tags in Neo4j."""
    logger.info("=== Neo4j Note Tag Normalization ===\n")

    # Get Neo4j adapter
    neo4j = get_neo4j_adapter()

    if not neo4j.is_available():
        logger.error("❌ Neo4j is not available. Cannot update notes.")
        sys.exit(1)

    # Fetch all notes
    logger.info("Fetching all notes from Neo4j...")
    with neo4j.driver.session(database=neo4j.database) as session:
        result = session.run("MATCH (n:Note) RETURN n")
        notes = [record["n"] for record in result]

    logger.info(f"Found {len(notes)} notes\n")

    if len(notes) == 0:
        logger.warning("No notes found in database. Nothing to update.")
        return

    # Update note tags
    updated_count = 0
    for note in notes:
        note_id = note["id"]
        old_tags = note.get("tags", [])

        # Normalize tags
        new_tags = [normalize_tag(tag) for tag in old_tags]
        # Remove duplicates while preserving order
        new_tags = list(dict.fromkeys(new_tags))

        if old_tags != new_tags:
            logger.info(f"Updating {note_id}: {note.get('title', 'Untitled')}")
            logger.info(f"  Old: {old_tags}")
            logger.info(f"  New: {new_tags}")

            # Update in Neo4j
            with neo4j.driver.session(database=neo4j.database) as session:
                session.run(
                    "MATCH (n:Note {id: $id}) SET n.tags = $tags",
                    id=note_id,
                    tags=new_tags,
                )

            updated_count += 1
            logger.info("  ✓ Updated\n")

    logger.info(f"\n{'='*50}")
    logger.info(f"Summary: Updated {updated_count} of {len(notes)} notes")
    logger.info(f"{'='*50}")


if __name__ == "__main__":
    main()
