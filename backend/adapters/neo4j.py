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
            # Set connection timeout to 0.5 seconds to avoid blocking startup
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                connection_timeout=0.5,
                max_connection_lifetime=3600,
            )
            # Test connection with short timeout
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
            logger.warning("Failed to connect to Neo4j: %s - using SQLite fallback", e)
            self._available = False

    def _initialize_schema(self) -> None:
        """Create indexes and constraints for optimal performance."""
        if not self._available or not self.driver:
            return

        with self.driver.session(database=self.database) as session:
            # ===== NOTE SCHEMA =====
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

            # ===== ARTICLE SCHEMA =====
            # Unique constraint on Article.id
            session.run(
                """
                CREATE CONSTRAINT article_id_unique IF NOT EXISTS
                FOR (a:Article) REQUIRE a.id IS UNIQUE
                """
            )

            # Index on Article.content_hash for change detection
            session.run(
                """
                CREATE INDEX article_content_hash IF NOT EXISTS
                FOR (a:Article) ON (a.content_hash)
                """
            )

            # Index on Article.updated_at for sorting
            session.run(
                """
                CREATE INDEX article_updated_at IF NOT EXISTS
                FOR (a:Article) ON (a.updated_at)
                """
            )

            logger.info("Neo4j schema initialized (Notes + Articles + embeddings support)")

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

    def get_all_notes(self) -> list[dict[str, Any]]:
        """Get all notes.

        Returns:
            List of note dicts
        """
        if not self._available or not self.driver:
            return []

        with self.driver.session(database=self.database) as session:
            result = session.run("MATCH (n:Note) RETURN n ORDER BY n.created_at DESC")
            return [self._node_to_dict(record["n"]) for record in result]

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
        """Convert Neo4j node to dict (works for both Note and Article nodes).

        This method intelligently handles both Note and Article nodes by checking
        which fields are present, following DRY principles.

        Args:
            node: Neo4j node (Note or Article)

        Returns:
            Dict representation including all available fields
        """
        # Handle both 'id' and 'note_id' properties for backward compatibility
        node_id = node.get("id") or node.get("note_id") or node.get("article_id")

        result = {
            "id": node_id,
            "title": node.get("title", ""),
            "content": node.get("content", ""),
            "created_at": node.get("created_at", 0.0),
            "updated_at": node.get("updated_at", node.get("created_at", 0.0)),
        }

        # Note-specific fields (only present in Note nodes)
        if "author" in node:
            result["author"] = node["author"]
        if "is_ephemeral" in node:
            result["is_ephemeral"] = node["is_ephemeral"]
        if "tags" in node:
            result["tags"] = node["tags"]

        # Embedding-related fields (present in both Notes and Articles)
        if "content_hash" in node:
            result["content_hash"] = node["content_hash"]
        if "embedding" in node:
            result["embedding"] = node["embedding"]
        if "embedding_model" in node:
            result["embedding_model"] = node["embedding_model"]
        if "embedding_version" in node:
            result["embedding_version"] = node["embedding_version"]

        return result

    # ===== ARTICLE METHODS =====

    def upsert_article(
        self,
        article_id: str,
        title: str,
        content: str,
        content_hash: str,
        created_at: float,
        updated_at: float,
    ) -> dict[str, Any]:
        """Create or update an article in Neo4j.

        Args:
            article_id: Unique article ID (slug)
            title: Article title
            content: Full markdown content
            content_hash: SHA256 hash of content
            created_at: Unix timestamp
            updated_at: Unix timestamp

        Returns:
            Article dict with id, title, content, etc.
        """
        if not self._available or not self.driver:
            raise RuntimeError("Neo4j not available")

        with self.driver.session(database=self.database) as session:
            result = session.run(
                """
                MERGE (a:Article {id: $id})
                SET a.title = $title,
                    a.content = $content,
                    a.content_hash = $content_hash,
                    a.created_at = $created_at,
                    a.updated_at = $updated_at
                RETURN a
                """,
                id=article_id,
                title=title,
                content=content,
                content_hash=content_hash,
                created_at=created_at,
                updated_at=updated_at,
            )
            node = result.single()["a"]
            return self._node_to_dict(node)

    def get_article(self, article_id: str) -> dict[str, Any] | None:
        """Get an article by ID.

        Args:
            article_id: Article ID

        Returns:
            Article dict or None if not found
        """
        if not self._available or not self.driver:
            return None

        with self.driver.session(database=self.database) as session:
            result = session.run(
                """
                MATCH (a:Article {id: $id})
                RETURN a
                """,
                id=article_id,
            )
            record = result.single()
            if not record:
                return None
            return self._node_to_dict(record["a"])

    def get_all_articles(self) -> list[dict[str, Any]]:
        """Get all articles.

        Returns:
            List of article dicts
        """
        if not self._available or not self.driver:
            return []

        with self.driver.session(database=self.database) as session:
            result = session.run("MATCH (a:Article) RETURN a ORDER BY a.created_at DESC")
            return [self._node_to_dict(record["a"]) for record in result]

    # ===== EMBEDDING METHODS =====

    def store_embedding(
        self,
        node_type: str,  # "Article" or "Note"
        node_id: str,
        embedding: list[float],
        model: str,
        version: int,
    ) -> bool:
        """Store embedding for an article or note.

        Args:
            node_type: "Article" or "Note"
            node_id: ID of the article or note
            embedding: Embedding vector (768 dimensions)
            model: Model name (e.g., "nomic-embed-text")
            version: Embedding version for cache invalidation

        Returns:
            True if successful
        """
        if not self._available or not self.driver:
            return False

        with self.driver.session(database=self.database) as session:
            session.run(
                f"""
                MATCH (n:{node_type} {{id: $id}})
                SET n.embedding = $embedding,
                    n.embedding_model = $model,
                    n.embedding_version = $version
                """,
                id=node_id,
                embedding=embedding,
                model=model,
                version=version,
            )
            return True

    def get_embedding(
        self, node_type: str, node_id: str
    ) -> dict[str, Any] | None:
        """Get embedding for an article or note.

        Args:
            node_type: "Article" or "Note"
            node_id: ID of the article or note

        Returns:
            Dict with embedding, model, version or None if not found
        """
        if not self._available or not self.driver:
            return None

        with self.driver.session(database=self.database) as session:
            result = session.run(
                f"""
                MATCH (n:{node_type} {{id: $id}})
                RETURN n.embedding as embedding,
                       n.embedding_model as model,
                       n.embedding_version as version,
                       n.content_hash as content_hash
                """,
                id=node_id,
            )
            record = result.single()
            if not record or not record["embedding"]:
                return None

            return {
                "embedding": record["embedding"],
                "model": record["model"],
                "version": record["version"],
                "content_hash": record["content_hash"],
            }

    def get_all_embeddings(
        self, node_type: str | None = None
    ) -> list[dict[str, Any]]:
        """Get all embeddings for articles and/or notes.

        Args:
            node_type: Optional filter for "Article" or "Note" (None = both)

        Returns:
            List of dicts with id, type, embedding, model, version
        """
        if not self._available or not self.driver:
            return []

        with self.driver.session(database=self.database) as session:
            if node_type:
                query = f"""
                    MATCH (n:{node_type})
                    WHERE n.embedding IS NOT NULL
                    RETURN n.id as id,
                           '{node_type}' as type,
                           n.embedding as embedding,
                           n.embedding_model as model,
                           n.embedding_version as version
                """
            else:
                query = """
                    MATCH (n)
                    WHERE (n:Article OR n:Note) AND n.embedding IS NOT NULL
                    RETURN n.id as id,
                           labels(n)[0] as type,
                           n.embedding as embedding,
                           n.embedding_model as model,
                           n.embedding_version as version
                """

            result = session.run(query)
            return [
                {
                    "id": record["id"],
                    "type": record["type"],
                    "embedding": record["embedding"],
                    "model": record["model"],
                    "version": record["version"],
                }
                for record in result
            ]

    # ===== HELPER METHODS =====
    # (Removed _article_node_to_dict - now using unified _node_to_dict for both Notes and Articles)


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
