"""Pure business logic for notes/Zettelkasten operations (Functional Core).

This module contains pure functions with no I/O or side effects.
All functions are deterministic and fully unit-testable.
"""

import re
from typing import Any


def extract_wikilinks(content: str) -> list[str]:
    """Extract [[note-id]] wikilinks from markdown content.

    Pure function: No I/O, no side effects, deterministic.

    Args:
        content: Markdown content to parse

    Returns:
        List of note IDs referenced in content

    Examples:
        >>> extract_wikilinks("See [[foo-bar]] and [[baz-qux]]")
        ['foo-bar', 'baz-qux']
        >>> extract_wikilinks("No links here")
        []
    """
    pattern = r'\[\[([a-z0-9-]+)\]\]'
    return re.findall(pattern, content)


def validate_note_id(note_id: str) -> bool:
    """Validate note ID format (adjective-noun pattern).

    Pure function: No I/O, no side effects, deterministic.

    Args:
        note_id: Note ID to validate

    Returns:
        True if valid format, False otherwise

    Examples:
        >>> validate_note_id("curious-elephant")
        True
        >>> validate_note_id("note-123")
        True
        >>> validate_note_id("invalid_format")
        False
        >>> validate_note_id("UPPERCASE")
        False
    """
    pattern = r'^[a-z0-9]+-[a-z0-9]+$'
    return bool(re.match(pattern, note_id))


def build_graph_data(notes: list[dict[str, Any]]) -> dict[str, Any]:
    """Build graph data structure from notes list.

    Pure function: No I/O, no side effects, deterministic.
    Constructs nodes and edges for graph visualization.

    Args:
        notes: List of note dictionaries with id, title, author, tags, links fields

    Returns:
        Dictionary with 'nodes', 'edges', and 'count' fields

    Example:
        >>> notes = [
        ...     {"id": "note-1", "title": "First", "author": "admin",
        ...      "tags": ["test"], "links": ["note-2"]},
        ...     {"id": "note-2", "title": "Second", "author": "admin",
        ...      "tags": [], "links": []}
        ... ]
        >>> graph = build_graph_data(notes)
        >>> len(graph['nodes'])
        2
        >>> len(graph['edges'])
        1
    """
    # Build nodes list
    nodes = [
        {
            "id": note["id"],
            "title": note.get("title") or note["id"],
            "author": note["author"],
            "tags": note.get("tags", []),
        }
        for note in notes
    ]

    # Build edges list from all notes' links
    edges = []
    for note in notes:
        source_id = note["id"]
        for target_id in note.get("links", []):
            edges.append({
                "source": source_id,
                "target": target_id,
            })

    return {
        "nodes": nodes,
        "edges": edges,
        "count": {
            "nodes": len(nodes),
            "edges": len(edges),
        }
    }


def build_local_subgraph(
    notes: list[dict[str, Any]],
    center_note_id: str,
    depth: int = 2
) -> dict[str, Any]:
    """Build a local subgraph centered on a specific note.

    Pure function: No I/O, no side effects, deterministic.
    Returns only notes within 'depth' hops from the center note.

    Args:
        notes: List of all note dictionaries
        center_note_id: ID of the center note
        depth: Maximum number of hops from center (default: 2)

    Returns:
        Dictionary with 'nodes', 'edges', and 'count' fields for local graph

    Example:
        >>> notes = [
        ...     {"id": "center", "title": "Center", "author": "admin",
        ...      "tags": [], "links": ["neighbor"]},
        ...     {"id": "neighbor", "title": "Neighbor", "author": "admin",
        ...      "tags": [], "links": ["distant"]},
        ...     {"id": "distant", "title": "Distant", "author": "admin",
        ...      "tags": [], "links": []}
        ... ]
        >>> subgraph = build_local_subgraph(notes, "center", depth=1)
        >>> len(subgraph['nodes'])  # center + neighbor only
        2
    """
    # Build adjacency map for efficient traversal
    adjacency: dict[str, set[str]] = {}
    for note in notes:
        note_id = note["id"]
        adjacency[note_id] = set(note.get("links", []))

    # BFS to find all notes within depth hops
    visited = {center_note_id}
    current_level = {center_note_id}

    for _ in range(depth):
        next_level = set()
        for node_id in current_level:
            if node_id in adjacency:
                neighbors = adjacency[node_id]
                next_level.update(neighbors - visited)

        visited.update(next_level)
        current_level = next_level

        if not current_level:
            break  # No more nodes to explore

    # Filter notes and build graph with only visited nodes
    filtered_notes = [note for note in notes if note["id"] in visited]
    return build_graph_data(filtered_notes)
