"""Neo4j database adapter for Zettelkasten notes."""

import logging
import time
from typing import Any

from neo4j import GraphDatabase, Session
from neo4j.exceptions import ServiceUnavailable

from config import get_settings

logger = logging.getLogger(__name__)


class Neo4jAdapter:
    """Adapter for Neo4j graph database operations."""

    def __init__(self) -> None:
        """Initialize Neo4j connection."""
        settings = get_settings()
        self.uri = settings.neo4j_uri
        self.user = settings.neo4j_user
        self.password = settings.neo4j_password
        self.database = settings.neo4j_database
        self.driver = None
        self._available = False

        # Try to connect
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Neo4j."""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            # Test connection
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 AS test")
                result.single()
            self._available = True
            logger.info("Neo4j connection established: %s", self.uri)
            self._initialize_schema()
        except ServiceUnavailable:
            logger.warning(
                "Neo4j not available at %s - persistent notes will not work. "
                "Start Neo4j with: docker run -p 7687:7687 -p 7474:7474 neo4j:latest",
                self.uri,
            )
            self._available = False
        except Exception as e:
            logger.error("Failed to connect to Neo4j: %s", e)
            self._available = False

    def _initialize_schema(self) -> None:
        """Create indexes and constraints for optimal performance."""
        if not self._available or not self.driver:
            return

        with self.driver.session(database=self.database) as session:
            # Unique constraint on Note.id
            session.run(
                """
                CREATE CONSTRAINT note_id_unique IF NOT EXISTS
                FOR (n:Note) REQUIRE n.id IS UNIQUE
                """
            )

            # Index on Note.created_at for sorting
            session.run(
                """
                CREATE INDEX note_created_at IF NOT EXISTS
                FOR (n:Note) ON (n.created_at)
                """
            )

            # Index on Note.author for filtering
            session.run(
                """
                CREATE INDEX note_author IF NOT EXISTS
                FOR (n:Note) ON (n.author)
                """
            )

            logger.info("Neo4j schema initialized")

    def is_available(self) -> bool:
        """Check if Neo4j is available."""
        return self._available

    def close(self) -> None:
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def create_note(
        self,
        note_id: str,
        content: str,
        title: str | None = None,
        author: str = "admin",
        tags: list[str] | None = None,
        links: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new note in Neo4j.

        Args:
            note_id: Unique note ID
            content: Markdown content
            title: Optional title
            author: Note author (default: admin)
            tags: Optional tags
            links: Optional wikilinks to other notes

        Returns:
            Created note as dict
        """
        if not self._available or not self.driver:
            raise RuntimeError("Neo4j not available")

        with self.driver.session(database=self.database) as session:
            # Create note node
            result = session.run(
                """
                CREATE (n:Note {
                    id: $id,
                    title: $title,
                    content: $content,
                    author: $author,
                    tags: $tags,
                    created_at: $created_at,
                    updated_at: $updated_at,
                    is_ephemeral: false
                })
                RETURN n
                """,
                id=note_id,
                title=title or "",
                content=content,
                author=author,
                tags=tags or [],
                created_at=time.time(),
                updated_at=time.time(),
            )

            note_record = result.single()
            if not note_record:
                raise RuntimeError(f"Failed to create note {note_id}")

            # Create links to other notes
            if links:
                self._create_links(session, note_id, links)

            # Return created note
            return self._node_to_dict(note_record["n"])

    def get_note(self, note_id: str) -> dict[str, Any] | None:
        """Get note by ID.

        Args:
            note_id: Note ID

        Returns:
            Note dict or None if not found
        """
        if not self._available or not self.driver:
            return None

        with self.driver.session(database=self.database) as session:
            result = session.run(
                """
                MATCH (n:Note {id: $id})
                OPTIONAL MATCH (n)-[:LINKS_TO]->(target:Note)
                RETURN n, collect(target.id) AS links
                """,
                id=note_id,
            )

            record = result.single()
            if not record:
                return None

            note = self._node_to_dict(record["n"])
            note["links"] = record["links"] or []
            return note

    def list_notes(self, author: str | None = None) -> list[dict[str, Any]]:
        """List all notes, optionally filtered by author.

        Args:
            author: Optional author filter

        Returns:
            List of note dicts sorted by created_at descending
        """
        if not self._available or not self.driver:
            return []

        with self.driver.session(database=self.database) as session:
            if author:
                result = session.run(
                    """
                    MATCH (n:Note {author: $author})
                    OPTIONAL MATCH (n)-[:LINKS_TO]->(target:Note)
                    RETURN n, collect(target.id) AS links
                    ORDER BY n.created_at DESC
                    """,
                    author=author,
                )
            else:
                result = session.run(
                    """
                    MATCH (n:Note)
                    OPTIONAL MATCH (n)-[:LINKS_TO]->(target:Note)
                    RETURN n, collect(target.id) AS links
                    ORDER BY n.created_at DESC
                    """
                )

            notes = []
            for record in result:
                note = self._node_to_dict(record["n"])
                note["links"] = record["links"] or []
                notes.append(note)

            return notes

    def update_note(
        self,
        note_id: str,
        content: str,
        title: str | None = None,
        tags: list[str] | None = None,
        links: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Update note content and metadata.

        Args:
            note_id: Note ID
            content: New content
            title: New title
            tags: New tags
            links: New wikilinks

        Returns:
            Updated note dict or None if not found
        """
        if not self._available or not self.driver:
            return None

        with self.driver.session(database=self.database) as session:
            # Update note properties
            result = session.run(
                """
                MATCH (n:Note {id: $id})
                SET n.content = $content,
                    n.title = $title,
                    n.tags = $tags,
                    n.updated_at = $updated_at
                RETURN n
                """,
                id=note_id,
                content=content,
                title=title or "",
                tags=tags or [],
                updated_at=time.time(),
            )

            record = result.single()
            if not record:
                return None

            # Update links
            if links is not None:
                self._delete_links(session, note_id)
                if links:
                    self._create_links(session, note_id, links)

            # Return updated note
            return self.get_note(note_id)

    def delete_note(self, note_id: str) -> bool:
        """Delete note by ID.

        Args:
            note_id: Note ID

        Returns:
            True if deleted, False if not found
        """
        if not self._available or not self.driver:
            return False

        with self.driver.session(database=self.database) as session:
            result = session.run(
                """
                MATCH (n:Note {id: $id})
                DETACH DELETE n
                RETURN count(n) AS deleted
                """,
                id=note_id,
            )

            record = result.single()
            return record["deleted"] > 0 if record else False

    def get_backlinks(self, note_id: str) -> list[dict[str, Any]]:
        """Get notes that link to this note.

        Args:
            note_id: Target note ID

        Returns:
            List of notes with links to this note
        """
        if not self._available or not self.driver:
            return []

        with self.driver.session(database=self.database) as session:
            result = session.run(
                """
                MATCH (source:Note)-[:LINKS_TO]->(target:Note {id: $id})
                OPTIONAL MATCH (source)-[:LINKS_TO]->(other:Note)
                RETURN source, collect(other.id) AS links
                """,
                id=note_id,
            )

            backlinks = []
            for record in result:
                note = self._node_to_dict(record["source"])
                note["links"] = record["links"] or []
                backlinks.append(note)

            return backlinks

    def get_outbound_links(self, note_id: str) -> list[dict[str, Any]]:
        """Get notes this note links to.

        Args:
            note_id: Source note ID

        Returns:
            List of linked notes
        """
        if not self._available or not self.driver:
            return []

        with self.driver.session(database=self.database) as session:
            result = session.run(
                """
                MATCH (source:Note {id: $id})-[:LINKS_TO]->(target:Note)
                OPTIONAL MATCH (target)-[:LINKS_TO]->(other:Note)
                RETURN target, collect(other.id) AS links
                """,
                id=note_id,
            )

            links = []
            for record in result:
                note = self._node_to_dict(record["target"])
                note["links"] = record["links"] or []
                links.append(note)

            return links

    def get_all_note_ids(self) -> set[str]:
        """Get all note IDs (for collision detection).

        Returns:
            Set of all note IDs
        """
        if not self._available or not self.driver:
            return set()

        with self.driver.session(database=self.database) as session:
            result = session.run("MATCH (n:Note) RETURN n.id AS id")
            return {record["id"] for record in result}

    def _create_links(self, session: Session, source_id: str, target_ids: list[str]) -> None:
        """Create LINKS_TO relationships.

        Args:
            session: Neo4j session
            source_id: Source note ID
            target_ids: List of target note IDs
        """
        for target_id in target_ids:
            # Create link even if target doesn't exist yet (forward reference)
            session.run(
                """
                MATCH (source:Note {id: $source_id})
                MERGE (target:Note {id: $target_id})
                MERGE (source)-[:LINKS_TO]->(target)
                """,
                source_id=source_id,
                target_id=target_id,
            )

    def _delete_links(self, session: Session, source_id: str) -> None:
        """Delete all outbound LINKS_TO relationships.

        Args:
            session: Neo4j session
            source_id: Source note ID
        """
        session.run(
            """
            MATCH (source:Note {id: $source_id})-[r:LINKS_TO]->()
            DELETE r
            """,
            source_id=source_id,
        )

    def _node_to_dict(self, node: Any) -> dict[str, Any]:
        """Convert Neo4j node to dict.

        Args:
            node: Neo4j node

        Returns:
            Dict representation
        """
        return {
            "id": node["id"],
            "title": node.get("title", ""),
            "content": node["content"],
            "author": node.get("author", "admin"),
            "is_ephemeral": node.get("is_ephemeral", False),
            "tags": node.get("tags", []),
            "created_at": node["created_at"],
            "updated_at": node.get("updated_at", node["created_at"]),
        }


# Global instance
_adapter: Neo4jAdapter | None = None


def get_neo4j_adapter() -> Neo4jAdapter:
    """Get global Neo4jAdapter instance (singleton).

    Returns:
        Neo4jAdapter instance
    """
    global _adapter
    if _adapter is None:
        _adapter = Neo4jAdapter()
    return _adapter
