"""Repair missing LINKS_TO relationships in Neo4j notes.

This script scans all notes in Neo4j, extracts wikilinks from their content,
and creates any missing LINKS_TO relationships.

Usage:
    python repair_note_links.py [--dry-run]
"""

import argparse
import logging

from adapters.neo4j import get_neo4j_adapter
from wikilink_parser import get_wikilink_parser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def repair_note_links(dry_run: bool = False) -> dict[str, int]:
    """Repair missing LINKS_TO relationships.

    Args:
        dry_run: If True, only report missing links without creating them

    Returns:
        Dict with stats: total_notes, notes_with_missing_links, links_created
    """
    neo4j = get_neo4j_adapter()
    if not neo4j.is_available():
        raise RuntimeError("Neo4j is not available")

    parser = get_wikilink_parser()

    # Get all notes with their current links
    logger.info("Fetching all notes from Neo4j...")
    notes = neo4j.list_notes()
    logger.info("Found %d notes", len(notes))

    # Get all note IDs for validation
    all_note_ids = neo4j.get_all_note_ids()
    logger.info("Found %d total note IDs", len(all_note_ids))

    stats = {
        "total_notes": len(notes),
        "notes_with_missing_links": 0,
        "links_created": 0,
        "broken_links": 0,
    }

    notes_with_issues = []

    # Check each note for missing links
    for note in notes:
        note_id = note["id"]
        content = note.get("content", "")
        current_links = set(note.get("links", []))

        # Extract wikilinks from content
        extracted_links = parser.extract_links(content)
        expected_links = set(extracted_links)

        # Find missing links
        missing_links = expected_links - current_links

        if missing_links:
            stats["notes_with_missing_links"] += 1
            logger.info(
                "Note %s has %d missing links: %s",
                note_id,
                len(missing_links),
                list(missing_links),
            )

            # Separate valid and broken links
            valid_missing = [link for link in missing_links if link in all_note_ids]
            broken_missing = [link for link in missing_links if link not in all_note_ids]

            if valid_missing:
                logger.info(
                    "  - %d valid missing links: %s",
                    len(valid_missing),
                    valid_missing,
                )

            if broken_missing:
                logger.warning(
                    "  - %d broken links (target notes don't exist): %s",
                    len(broken_missing),
                    broken_missing,
                )
                stats["broken_links"] += len(broken_missing)

            notes_with_issues.append(
                {
                    "note_id": note_id,
                    "title": note.get("title", ""),
                    "valid_missing": valid_missing,
                    "broken_missing": broken_missing,
                }
            )

            # Create missing links
            if valid_missing and not dry_run:
                logger.info("Creating %d missing links for note %s", len(valid_missing), note_id)
                if neo4j.driver:
                    with neo4j.driver.session(database=neo4j.database) as session:
                        neo4j._create_links(session, note_id, valid_missing)
                    stats["links_created"] += len(valid_missing)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("REPAIR SUMMARY")
    logger.info("=" * 60)
    logger.info("Total notes: %d", stats["total_notes"])
    logger.info("Notes with missing links: %d", stats["notes_with_missing_links"])
    logger.info("Links created: %d", stats["links_created"])
    logger.info("Broken links (target notes don't exist): %d", stats["broken_links"])

    if notes_with_issues:
        logger.info("\n" + "=" * 60)
        logger.info("NOTES WITH ISSUES")
        logger.info("=" * 60)
        for note_info in notes_with_issues:
            logger.info("\nNote: %s (%s)", note_info["note_id"], note_info["title"])
            if note_info["valid_missing"]:
                logger.info("  Valid missing links: %s", note_info["valid_missing"])
            if note_info["broken_missing"]:
                logger.warning("  Broken links: %s", note_info["broken_missing"])

    if dry_run:
        logger.info("\n[DRY RUN] No changes were made to the database")

    return stats


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Repair missing LINKS_TO relationships in Neo4j notes"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report missing links without creating them",
    )
    args = parser.parse_args()

    try:
        repair_note_links(dry_run=args.dry_run)
        logger.info("\nRepair completed successfully!")
    except Exception as e:
        logger.error("Repair failed: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    main()
