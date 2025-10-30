#!/usr/bin/env python3
"""Clean up ghost/placeholder nodes (anonymous with empty content).

More targeted than v1 - only deletes nodes that have:
- author = "anonymous" AND
- created_at = 0.0 AND
- content = ""
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.neo4j import Neo4jAdapter


def cleanup_anonymous_ghosts() -> None:
    """Remove anonymous ghost nodes only."""
    adapter = Neo4jAdapter()

    if not adapter._available or not adapter.driver:
        print("ERROR: Neo4j not available")
        return

    with adapter.driver.session(database=adapter.database) as session:
        # Find anonymous ghost nodes only (content could be NULL or empty)
        result = session.run(
            """
            MATCH (n:Note)
            WHERE (n.author = 'anonymous' OR n.author IS NULL)
              AND (n.created_at = 0.0 OR n.created_at IS NULL)
              AND (n.content = '' OR n.content IS NULL)
            RETURN count(n) AS ghost_count
            """
        )
        ghost_count = result.single()["ghost_count"]
        print(f"Found {ghost_count} anonymous ghost nodes to delete")

        if ghost_count == 0:
            print("No anonymous ghost nodes found. Database is clean!")
            return

        # Show which notes
        result = session.run(
            """
            MATCH (n:Note)
            WHERE (n.author = 'anonymous' OR n.author IS NULL)
              AND (n.created_at = 0.0 OR n.created_at IS NULL)
              AND (n.content = '' OR n.content IS NULL)
            RETURN COALESCE(n.id, n.note_id) AS note_id
            ORDER BY note_id
            """
        )

        print("\nAnonymous ghost nodes to delete:")
        for record in result:
            print(f"  - {record['note_id']}")

        # Confirm
        response = input(f"\nDelete {ghost_count} anonymous ghost nodes? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            return

        # Delete
        result = session.run(
            """
            MATCH (n:Note)
            WHERE (n.author = 'anonymous' OR n.author IS NULL)
              AND (n.created_at = 0.0 OR n.created_at IS NULL)
              AND (n.content = '' OR n.content IS NULL)
            DETACH DELETE n
            RETURN count(*) AS deleted_count
            """
        )

        deleted_count = result.single()["deleted_count"]
        print(f"\n✅ Deleted {deleted_count} anonymous ghost nodes")

        # Verify
        result = session.run(
            """
            MATCH (n:Note)
            WITH COALESCE(n.id, n.note_id) AS note_id, count(*) AS count, collect(n.author) AS authors
            WHERE count > 1
            RETURN note_id, count, authors
            ORDER BY note_id
            """
        )

        duplicates = list(result)
        if duplicates:
            print(f"\n⚠️  Warning: {len(duplicates)} notes still have duplicates:")
            for dup in duplicates:
                print(f"  - {dup['note_id']}: {dup['count']} nodes (authors: {dup['authors']})")
        else:
            print("\n✅ No duplicate notes found. Database is clean!")


if __name__ == "__main__":
    cleanup_anonymous_ghosts()
