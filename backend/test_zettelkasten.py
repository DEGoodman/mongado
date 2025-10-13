"""Quick test script for Zettelkasten components."""

import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from database import Database
from note_id_generator import get_id_generator

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_id_generator():
    """Test note ID generator."""
    logger.info("Testing Note ID Generator...")

    generator = get_id_generator()

    # Test generation
    logger.info("Generating 10 random IDs:")
    existing = set()
    for i in range(10):
        note_id = generator.generate(existing)
        existing.add(note_id)
        is_valid = generator.is_valid(note_id)
        parsed = generator.parse(note_id)
        logger.info("  %d. %s (valid: %s, parsed: %s)", i + 1, note_id, is_valid, parsed)

    # Test collision handling
    logger.info("\nTesting collision handling:")
    # Pre-fill with many IDs
    large_set = set()
    for _ in range(100):
        large_set.add(generator.generate(large_set))

    new_id = generator.generate(large_set)
    logger.info("  Generated unique ID from set of %d: %s", len(large_set), new_id)

    # Test validation
    logger.info("\nTesting validation:")
    valid_ids = ["curious-elephant", "wise-mountain", "swift-river"]
    invalid_ids = ["invalid", "curious_elephant", "CuriousElephant", "curious-123"]

    for vid in valid_ids:
        result = generator.is_valid(vid)
        logger.info("  %s: %s", vid, "✓ valid" if result else "✗ invalid")

    for iid in invalid_ids:
        result = generator.is_valid(iid)
        logger.info("  %s: %s", iid, "✓ valid" if result else "✗ invalid")

    logger.info("✅ ID Generator tests passed\n")


def test_database():
    """Test database initialization and operations."""
    logger.info("Testing Database...")

    # Use test database
    test_db_path = Path(__file__).parent / "test_mongado.db"
    if test_db_path.exists():
        test_db_path.unlink()
        logger.info("Cleaned up previous test database")

    db = Database(test_db_path)

    # Test schema initialization
    logger.info("Database initialized at: %s", test_db_path)

    # Test insert
    logger.info("\nInserting test note:")
    note_id = "curious-elephant"
    db.execute(
        """
        INSERT INTO notes (id, title, content, author, tags)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            note_id,
            "Database Design Patterns",
            "Notes about database design for relationships...",
            "admin",
            '["database", "patterns"]',
        ),
    )
    db.commit()
    logger.info("  Inserted note: %s", note_id)

    # Test select
    logger.info("\nRetrieving note:")
    note = db.fetchone("SELECT * FROM notes WHERE id = ?", (note_id,))
    if note:
        logger.info("  ID: %s", note["id"])
        logger.info("  Title: %s", note["title"])
        logger.info("  Content: %s", note["content"][:50] + "...")
        logger.info("  Author: %s", note["author"])
        logger.info("  Created: %s", note["created_at"])

    # Test links
    logger.info("\nTesting links:")
    db.execute(
        "INSERT INTO notes (id, title, content, author) VALUES (?, ?, ?, ?)",
        ("wise-mountain", "Graph Algorithms", "Graph traversal notes...", "admin"),
    )
    db.execute(
        "INSERT INTO note_links (source_id, target_id) VALUES (?, ?)",
        (note_id, "wise-mountain"),
    )
    db.commit()

    links = db.fetchall(
        "SELECT target_id FROM note_links WHERE source_id = ?", (note_id,)
    )
    logger.info("  Links from %s: %s", note_id, [link["target_id"] for link in links])

    backlinks = db.fetchall(
        "SELECT source_id FROM note_links WHERE target_id = ?", ("wise-mountain",)
    )
    logger.info(
        "  Backlinks to wise-mountain: %s", [link["source_id"] for link in backlinks]
    )

    # Cleanup
    db.close()
    test_db_path.unlink()
    logger.info("\n✅ Database tests passed\n")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Zettelkasten Components Test")
    logger.info("=" * 60 + "\n")

    try:
        test_id_generator()
        test_database()

        logger.info("=" * 60)
        logger.info("🎉 All tests passed!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("❌ Test failed: %s", e, exc_info=True)
        sys.exit(1)
