#!/usr/bin/env python3
"""
Clean up broken notes in Neo4j production database.

This script:
1. Finds all notes with empty content or zero timestamps
2. Deletes them (they're broken duplicates or test data)
3. Ensures all remaining notes have proper 'id' property (migrates from 'note_id')

Run on production with:
    docker compose exec backend python3 /path/to/this/script.py --dry-run
    docker compose exec backend python3 /path/to/this/script.py --execute
"""

import argparse
import logging
import sys

# Add backend to path when run from container
sys.path.insert(0, '/app')

from adapters.neo4j import get_neo4j_adapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_broken_notes(neo4j):
    """Find all notes with empty content or zero timestamps."""
    if not neo4j.is_available():
        logger.error("Neo4j not available")
        return []

    with neo4j.driver.session(database=neo4j.database) as session:
        result = session.run("""
            MATCH (n:Note)
            WHERE (n.content IS NULL OR n.content = '')
               OR (n.created_at IS NULL OR n.created_at = 0.0)
            RETURN
                COALESCE(n.id, n.note_id, '<no-id>') as note_id,
                n.id as id_prop,
                n.note_id as note_id_prop,
                n.title as title,
                size(n.content) as content_length,
                n.author as author,
                n.created_at as created_at
            ORDER BY created_at DESC
        """)

        broken_notes = []
        for record in result:
            broken_notes.append({
                'note_id': record['note_id'],
                'id_prop': record['id_prop'],
                'note_id_prop': record['note_id_prop'],
                'title': record['title'],
                'content_length': record['content_length'],
                'author': record['author'],
                'created_at': record['created_at']
            })

        return broken_notes


def delete_broken_notes(neo4j, dry_run=True):
    """Delete notes with no content and no timestamp (completely broken)."""
    if not neo4j.is_available():
        logger.error("Neo4j not available")
        return 0

    with neo4j.driver.session(database=neo4j.database) as session:
        if dry_run:
            # Just count what would be deleted
            result = session.run("""
                MATCH (n:Note)
                WHERE (n.content IS NULL OR n.content = '')
                  AND (n.created_at IS NULL OR n.created_at = 0.0)
                  AND (n.title IS NULL OR n.title = '')
                RETURN count(n) as count
            """)
            count = result.single()['count']
            logger.info(f"[DRY RUN] Would delete {count} completely broken notes")
            return count
        else:
            # Actually delete
            result = session.run("""
                MATCH (n:Note)
                WHERE (n.content IS NULL OR n.content = '')
                  AND (n.created_at IS NULL OR n.created_at = 0.0)
                  AND (n.title IS NULL OR n.title = '')
                DETACH DELETE n
                RETURN count(n) as count
            """)
            count = result.single()['count']
            logger.info(f"Deleted {count} completely broken notes")
            return count


def migrate_note_id_to_id(neo4j, dry_run=True):
    """Migrate note_id property to id property for backward compatibility."""
    if not neo4j.is_available():
        logger.error("Neo4j not available")
        return 0

    with neo4j.driver.session(database=neo4j.database) as session:
        if dry_run:
            result = session.run("""
                MATCH (n:Note)
                WHERE n.id IS NULL AND n.note_id IS NOT NULL
                RETURN count(n) as count
            """)
            count = result.single()['count']
            logger.info(f"[DRY RUN] Would migrate {count} notes from note_id to id property")
            return count
        else:
            result = session.run("""
                MATCH (n:Note)
                WHERE n.id IS NULL AND n.note_id IS NOT NULL
                SET n.id = n.note_id
                RETURN count(n) as count
            """)
            count = result.single()['count']
            logger.info(f"Migrated {count} notes from note_id to id property")
            return count


def main():
    parser = argparse.ArgumentParser(description='Clean up broken notes in Neo4j')
    parser.add_argument('--execute', action='store_true',
                        help='Actually execute changes (default is dry-run)')
    args = parser.parse_args()

    dry_run = not args.execute

    if dry_run:
        logger.info("=" * 70)
        logger.info("DRY RUN MODE - No changes will be made")
        logger.info("Run with --execute to apply changes")
        logger.info("=" * 70)
    else:
        logger.warning("=" * 70)
        logger.warning("EXECUTE MODE - Changes will be made to database!")
        logger.warning("=" * 70)

    neo4j = get_neo4j_adapter()
    if not neo4j.is_available():
        logger.error("Neo4j is not available. Cannot proceed.")
        sys.exit(1)

    # Step 1: Find broken notes
    logger.info("\n" + "=" * 70)
    logger.info("Step 1: Finding broken notes...")
    logger.info("=" * 70)
    broken = find_broken_notes(neo4j)

    if broken:
        logger.info(f"\nFound {len(broken)} broken notes:")
        for note in broken:
            logger.info(f"  {note['note_id']}: "
                        f"content_len={note['content_length']}, "
                        f"created={note['created_at']}, "
                        f"title='{note['title']}'")
    else:
        logger.info("No broken notes found!")

    # Step 2: Delete completely broken notes (no content, no timestamp, no title)
    logger.info("\n" + "=" * 70)
    logger.info("Step 2: Deleting completely broken notes...")
    logger.info("=" * 70)
    deleted = delete_broken_notes(neo4j, dry_run=dry_run)

    # Step 3: Migrate note_id to id property
    logger.info("\n" + "=" * 70)
    logger.info("Step 3: Migrating note_id to id property...")
    logger.info("=" * 70)
    migrated = migrate_note_id_to_id(neo4j, dry_run=dry_run)

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Broken notes found: {len(broken)}")
    logger.info(f"Notes deleted: {deleted}")
    logger.info(f"Notes migrated: {migrated}")

    if dry_run:
        logger.info("\nThis was a DRY RUN. Run with --execute to apply changes.")
    else:
        logger.info("\nChanges have been applied to the database.")


if __name__ == '__main__':
    main()
