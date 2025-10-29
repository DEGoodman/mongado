"""Unit tests for core.notes module (pure business logic).

These tests verify pure functions with no I/O dependencies.
All functions should be deterministic: same input → same output.
"""

from core import notes


class TestExtractWikilinks:
    """Tests for wikilink extraction from markdown."""

    def test_extracts_single_wikilink(self):
        """Should extract single [[note-id]] wikilink."""
        content = "See [[foo-bar]] for details"
        links = notes.extract_wikilinks(content)

        assert links == ["foo-bar"]

    def test_extracts_multiple_wikilinks(self):
        """Should extract all wikilinks in order."""
        content = "See [[foo-bar]] and [[baz-qux]] and [[another-note]]"
        links = notes.extract_wikilinks(content)

        assert links == ["foo-bar", "baz-qux", "another-note"]

    def test_returns_empty_for_no_links(self):
        """Content with no wikilinks should return empty list."""
        content = "This has no links at all"
        links = notes.extract_wikilinks(content)

        assert links == []

    def test_handles_multiline_content(self):
        """Should find wikilinks across multiple lines."""
        content = """First line with [[first-link]]

        Second paragraph with [[second-link]]

        Third paragraph with [[third-link]]"""

        links = notes.extract_wikilinks(content)
        assert len(links) == 3
        assert "first-link" in links
        assert "second-link" in links
        assert "third-link" in links

    def test_ignores_invalid_formats(self):
        """Should only match valid lowercase-hyphen format."""
        content = """
        Valid: [[valid-link]]
        Invalid: [[Invalid-Link]]
        Invalid: [[invalid_underscore]]
        Invalid: [[spaces in link]]
        """

        links = notes.extract_wikilinks(content)
        assert links == ["valid-link"]

    def test_handles_numbers_in_links(self):
        """Should accept numbers in note IDs."""
        content = "See [[note-123]] and [[version-2]]"
        links = notes.extract_wikilinks(content)

        assert "note-123" in links
        assert "version-2" in links


class TestValidateNoteId:
    """Tests for note ID validation."""

    def test_valid_adjective_noun_format(self):
        """Valid adjective-noun format should return True."""
        assert notes.validate_note_id("curious-elephant") is True
        assert notes.validate_note_id("wise-mountain") is True
        assert notes.validate_note_id("happy-tree") is True

    def test_rejects_uppercase(self):
        """Uppercase letters should be invalid."""
        assert notes.validate_note_id("Curious-Elephant") is False
        assert notes.validate_note_id("LOUD-NOISE") is False

    def test_rejects_underscores(self):
        """Underscores should be invalid."""
        assert notes.validate_note_id("curious_elephant") is False

    def test_rejects_spaces(self):
        """Spaces should be invalid."""
        assert notes.validate_note_id("curious elephant") is False

    def test_requires_hyphen(self):
        """Must have exactly one hyphen."""
        assert notes.validate_note_id("curiouselephant") is False
        assert notes.validate_note_id("curious-big-elephant") is False

    def test_accepts_numbers(self):
        """Numbers are allowed in note IDs."""
        assert notes.validate_note_id("note-123") is True
        assert notes.validate_note_id("version-2") is True


class TestBuildGraphData:
    """Tests for building graph data structure."""

    def test_builds_nodes_from_notes(self):
        """Should create node for each note."""
        notes_list = [
            {
                "id": "note-1",
                "title": "First Note",
                "author": "admin",
                "tags": ["test"],
                "links": []
            },
            {
                "id": "note-2",
                "title": "Second Note",
                "author": "visitor",
                "tags": [],
                "links": []
            }
        ]

        graph = notes.build_graph_data(notes_list)

        assert len(graph["nodes"]) == 2
        assert graph["nodes"][0]["id"] == "note-1"
        assert graph["nodes"][0]["title"] == "First Note"
        assert graph["nodes"][1]["id"] == "note-2"
        assert graph["count"]["nodes"] == 2

    def test_builds_edges_from_links(self):
        """Should create edges from note links."""
        notes_list = [
            {
                "id": "note-1",
                "title": "First",
                "author": "admin",
                "tags": [],
                "links": ["note-2", "note-3"]
            },
            {
                "id": "note-2",
                "title": "Second",
                "author": "admin",
                "tags": [],
                "links": ["note-3"]
            },
            {
                "id": "note-3",
                "title": "Third",
                "author": "admin",
                "tags": [],
                "links": []
            }
        ]

        graph = notes.build_graph_data(notes_list)

        assert len(graph["edges"]) == 3
        assert graph["count"]["edges"] == 3

        # Check edges exist
        edge_pairs = [(e["source"], e["target"]) for e in graph["edges"]]
        assert ("note-1", "note-2") in edge_pairs
        assert ("note-1", "note-3") in edge_pairs
        assert ("note-2", "note-3") in edge_pairs

    def test_handles_empty_notes(self):
        """Empty notes list should return empty graph."""
        graph = notes.build_graph_data([])

        assert graph["nodes"] == []
        assert graph["edges"] == []
        assert graph["count"]["nodes"] == 0
        assert graph["count"]["edges"] == 0

    def test_handles_missing_title(self):
        """Missing title should default to note ID."""
        notes_list = [
            {
                "id": "note-1",
                "author": "admin",
                "tags": [],
                "links": []
            }
        ]

        graph = notes.build_graph_data(notes_list)
        assert graph["nodes"][0]["title"] == "note-1"


class TestBuildLocalSubgraph:
    """Tests for building depth-limited subgraphs."""

    def test_includes_center_node(self):
        """Center node should always be included."""
        notes_list = [
            {
                "id": "center",
                "title": "Center",
                "author": "admin",
                "tags": [],
                "links": []
            }
        ]

        subgraph = notes.build_local_subgraph(notes_list, "center", depth=1)
        assert len(subgraph["nodes"]) == 1
        assert subgraph["nodes"][0]["id"] == "center"

    def test_includes_direct_neighbors(self):
        """Direct neighbors (depth=1) should be included."""
        notes_list = [
            {
                "id": "center",
                "title": "Center",
                "author": "admin",
                "tags": [],
                "links": ["neighbor"]
            },
            {
                "id": "neighbor",
                "title": "Neighbor",
                "author": "admin",
                "tags": [],
                "links": ["distant"]
            },
            {
                "id": "distant",
                "title": "Distant",
                "author": "admin",
                "tags": [],
                "links": []
            }
        ]

        subgraph = notes.build_local_subgraph(notes_list, "center", depth=1)

        # Should include center + neighbor, but not distant (depth=2)
        node_ids = [n["id"] for n in subgraph["nodes"]]
        assert "center" in node_ids
        assert "neighbor" in node_ids
        assert "distant" not in node_ids

    def test_respects_depth_limit(self):
        """Should only include nodes within depth hops."""
        notes_list = [
            {
                "id": "center",
                "title": "Center",
                "author": "admin",
                "tags": [],
                "links": ["hop1"]
            },
            {
                "id": "hop1",
                "title": "Hop 1",
                "author": "admin",
                "tags": [],
                "links": ["hop2"]
            },
            {
                "id": "hop2",
                "title": "Hop 2",
                "author": "admin",
                "tags": [],
                "links": ["hop3"]
            },
            {
                "id": "hop3",
                "title": "Hop 3",
                "author": "admin",
                "tags": [],
                "links": []
            }
        ]

        # depth=2 should include center, hop1, hop2 but not hop3
        subgraph = notes.build_local_subgraph(notes_list, "center", depth=2)

        node_ids = [n["id"] for n in subgraph["nodes"]]
        assert "center" in node_ids
        assert "hop1" in node_ids
        assert "hop2" in node_ids
        assert "hop3" not in node_ids

    def test_handles_disconnected_graph(self):
        """Disconnected nodes should not be included."""
        notes_list = [
            {
                "id": "center",
                "title": "Center",
                "author": "admin",
                "tags": [],
                "links": []
            },
            {
                "id": "isolated",
                "title": "Isolated",
                "author": "admin",
                "tags": [],
                "links": []
            }
        ]

        subgraph = notes.build_local_subgraph(notes_list, "center", depth=1)

        # Should only include center, not isolated
        node_ids = [n["id"] for n in subgraph["nodes"]]
        assert node_ids == ["center"]

    def test_handles_cycles(self):
        """Should handle circular references without infinite loop."""
        notes_list = [
            {
                "id": "a",
                "title": "A",
                "author": "admin",
                "tags": [],
                "links": ["b"]
            },
            {
                "id": "b",
                "title": "B",
                "author": "admin",
                "tags": [],
                "links": ["c"]
            },
            {
                "id": "c",
                "title": "C",
                "author": "admin",
                "tags": [],
                "links": ["a"]  # Cycle back to A
            }
        ]

        # Should complete without hanging
        subgraph = notes.build_local_subgraph(notes_list, "a", depth=5)

        # All nodes should be included (all within 5 hops)
        assert len(subgraph["nodes"]) == 3
