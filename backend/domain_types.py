"""Type aliases for domain models used across the Mongado backend.

These TypedDicts provide better type safety and IDE support while maintaining
flexibility. They define the structure of dictionaries returned from the database
and passed between services.

For now, we use TypedDict for lightweight type hints. In the future, we may
migrate to Pydantic models or dataclasses if we need validation or methods.
"""

from typing import TypedDict


class NoteDict(TypedDict, total=False):
    """Type definition for Note dictionary.

    Attributes:
        id: Unique note ID (e.g., "curious-elephant")
        title: Optional note title
        content: Markdown content
        author: Author name (e.g., "Erik")
        tags: List of tag strings
        created_at: Unix timestamp (float) or ISO datetime string
        updated_at: Unix timestamp (float) or ISO datetime string
        links: List of note IDs this note links to
    """

    id: str
    title: str
    content: str
    author: str
    tags: list[str]
    created_at: float | str
    updated_at: float | str
    links: list[str]


class ArticleDict(TypedDict, total=False):
    """Type definition for Article dictionary.

    Articles are static markdown files with YAML frontmatter, loaded from
    backend/static/articles/ on startup.

    Attributes:
        id: Unique article slug (e.g., "python-performance")
        title: Article title
        content: Markdown content
        author: Author name
        tags: List of tag strings
        draft: Whether article is a draft (hidden in production)
        published_date: Date article was first published (ISO datetime string)
        updated_date: Date article was last updated (ISO datetime string)
        created_at: Unix timestamp (float) or ISO datetime string (legacy)
        updated_at: Unix timestamp (float) or ISO datetime string (legacy)
        content_hash: SHA256 hash of content (for change detection)
        embedding: Optional embedding vector
        embedding_model: Model used for embedding (e.g., "nomic-embed-text")
        embedding_version: Version number for embedding logic
    """

    id: str
    title: str
    content: str
    author: str
    tags: list[str]
    draft: bool
    published_date: str
    updated_date: str
    created_at: float | str
    updated_at: float | str
    content_hash: str
    embedding: list[float]
    embedding_model: str
    embedding_version: int


class ResourceDict(TypedDict, total=False):
    """Type definition for combined Resource (Article or Note).

    The /api/resources endpoint returns both articles and notes in a unified format.
    This is the superset of both NoteDict and ArticleDict fields.

    Attributes:
        id: Unique resource ID
        title: Resource title
        content: Markdown content
        author: Author name
        tags: List of tag strings
        created_at: Unix timestamp (float) or ISO datetime string
        updated_at: Unix timestamp (float) or ISO datetime string
        links: List of note IDs this note links to (empty for articles)
        content_hash: SHA256 hash (articles only)
    """

    id: str
    title: str
    content: str
    author: str
    tags: list[str]
    created_at: float | str
    updated_at: float | str
    links: list[str]
    content_hash: str


class GraphNodeDict(TypedDict):
    """Type definition for graph visualization node.

    Used by the /api/notes/graph and /api/notes/{id}/graph endpoints.

    Attributes:
        id: Note ID
        title: Note title
        tags: List of tags
    """

    id: str
    title: str
    tags: list[str]


class GraphLinkDict(TypedDict):
    """Type definition for graph visualization link/edge.

    Represents a wikilink connection between two notes.

    Attributes:
        source: Source note ID
        target: Target note ID
    """

    source: str
    target: str


class GraphDict(TypedDict):
    """Type definition for complete graph structure.

    Attributes:
        nodes: List of note nodes
        links: List of connections between notes
    """

    nodes: list[GraphNodeDict]
    links: list[GraphLinkDict]


class SearchResultDict(TypedDict):
    """Type definition for search result.

    Returned by /api/search endpoint (semantic search).

    Attributes:
        id: Resource ID
        title: Resource title
        content: Resource content excerpt
        score: Relevance score (0-1), higher is more relevant
        type: "article" or "note"
        tags: List of tags
    """

    id: str
    title: str
    content: str
    score: float
    type: str  # "article" | "note"
    tags: list[str]
