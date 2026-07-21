"""Unit tests for content inspiration features (#259 rewrite).

Note length is deliberately not a signal (see core/inspire.py module
docstring): a short, atomic note is correct in a Zettelkasten. Tests here
guard against that heuristic creeping back in.
"""

import os
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient

# Set testing mode before importing app modules
os.environ["TESTING"] = "1"

from core import inspire as inspire_core
from main import app
from routers.inspire import _cache

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client() -> Generator[TestClient]:
    """Get test client for API testing (no default dependency overrides)."""
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_inspire_cache() -> Generator[None]:
    """Reset the module-level suggestion cache between tests.

    routers/inspire.py holds a process-wide `_cache` singleton keyed by a KB
    fingerprint. Without resetting it, one test's cached suggestions would
    leak into the next test that happens to produce the same fingerprint.
    """
    _cache.reset("")
    yield
    _cache.reset("")


class FakeNotesService:
    """Minimal stand-in for NotesService, exposing only what inspire needs."""

    def __init__(
        self,
        notes_with_stats: list[dict[str, Any]] | None = None,
        notes_with_embeddings: list[dict[str, Any]] | None = None,
        all_links: dict[str, set[str]] | None = None,
    ) -> None:
        self._notes_with_stats = notes_with_stats or []
        self._notes_with_embeddings = notes_with_embeddings or []
        self._all_links = all_links or {}

    def get_notes_with_stats(self) -> list[dict[str, Any]]:
        return self._notes_with_stats

    def get_notes_with_embeddings(self) -> list[dict[str, Any]]:
        return self._notes_with_embeddings

    def get_all_links(self) -> dict[str, set[str]]:
        return self._all_links


class FakeLLM:
    """Minimal stand-in for the LLM client used by /api/inspire/suggestions."""

    def __init__(
        self,
        available: bool = True,
        response: str | None = None,
        raise_error: bool = False,
    ) -> None:
        self._available = available
        self._response = response
        self._raise_error = raise_error

    def is_available(self) -> bool:
        return self._available

    def generate(
        self,
        prompt: str,
        *,
        role: str = "chat",
        num_ctx: int | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> str | None:
        if self._raise_error:
            raise RuntimeError("simulated LLM failure")
        return self._response


def _override_dependencies(
    notes_service: FakeNotesService | None = None,
    llm: FakeLLM | None = None,
    articles: list[dict[str, Any]] | None = None,
) -> None:
    """Install dependency_overrides for the inspire router's dependencies."""
    from dependencies import get_llm, get_notes, get_static_articles

    if notes_service is not None:
        app.dependency_overrides[get_notes] = lambda: notes_service
    if llm is not None:
        app.dependency_overrides[get_llm] = lambda: llm
    if articles is not None:
        app.dependency_overrides[get_static_articles] = lambda: articles


def _note(
    note_id: str,
    title: str | None = None,
    content_length: int = 100,
    link_count: int = 0,
    backlink_count: int = 0,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Build a minimal note-with-stats dict."""
    return {
        "id": note_id,
        "title": title or note_id,
        "content_length": content_length,
        "link_count": link_count,
        "backlink_count": backlink_count,
        "tags": tags or [],
    }


# ============================================================================
# Pure function tests: core/inspire.py
# ============================================================================


class TestNormalizeTag:
    """normalize_tag: casing and separator normalization."""

    def test_lowercases(self) -> None:
        assert inspire_core.normalize_tag("Leadership") == "leadership"

    def test_normalizes_underscores(self) -> None:
        assert inspire_core.normalize_tag("one_on_ones") == "one-on-ones"

    def test_normalizes_spaces(self) -> None:
        assert inspire_core.normalize_tag("site reliability") == "site-reliability"

    def test_strips_whitespace(self) -> None:
        assert inspire_core.normalize_tag("  leadership  ") == "leadership"


class TestTitleOverlap:
    """title_overlap: the heart of duplicate-vs-sibling detection (#259)."""

    def test_number_word_normalization_makes_titles_identical(self) -> None:
        """'5 Dysfunctions' and 'Five Dysfunctions' are the same title."""
        overlap = inspire_core.title_overlap(
            "5 Dysfunctions of a Team", "Five Dysfunctions of a Team"
        )
        assert overlap >= 0.8

    def test_deliberate_siblings_are_not_duplicates(self) -> None:
        """Distinct sibling topics must not score as near-identical titles."""
        overlap = inspire_core.title_overlap(
            "Developer Productivity: People Factors",
            "Developer Productivity: Process Factors",
        )
        assert overlap < 0.8

    def test_identical_titles_score_one(self) -> None:
        assert inspire_core.title_overlap("Same Title", "Same Title") == 1.0

    def test_completely_different_titles_score_zero(self) -> None:
        assert inspire_core.title_overlap("Apples", "Xylophone") == 0.0

    def test_empty_title_scores_zero(self) -> None:
        assert inspire_core.title_overlap("", "Something") == 0.0
        assert inspire_core.title_overlap("Something", "") == 0.0

    def test_stopwords_ignored(self) -> None:
        overlap = inspire_core.title_overlap("The Team of Leaders", "Team Leaders")
        assert overlap == 1.0


class TestFindOrphanNotes:
    """find_orphan_notes: link_count==0 AND backlink_count==0 only."""

    def test_empty_notes(self) -> None:
        assert inspire_core.find_orphan_notes([]) == []

    def test_only_fully_disconnected_notes_are_orphans(self) -> None:
        notes = [
            _note("orphan-1", content_length=100, link_count=0, backlink_count=0),
            _note("has-outbound", content_length=100, link_count=1, backlink_count=0),
            _note("has-inbound", content_length=100, link_count=0, backlink_count=1),
            _note("well-connected", content_length=100, link_count=2, backlink_count=2),
        ]
        result = inspire_core.find_orphan_notes(notes)

        assert [r["note_id"] for r in result] == ["orphan-1"]

    def test_short_but_well_linked_note_is_not_returned(self) -> None:
        """Regression test for #259: length is not a signal on its own."""
        notes = [
            _note("short-but-linked", content_length=50, link_count=3, backlink_count=2),
            _note("true-orphan", content_length=500, link_count=0, backlink_count=0),
        ]
        result = inspire_core.find_orphan_notes(notes)

        note_ids = [r["note_id"] for r in result]
        assert "short-but-linked" not in note_ids
        assert "true-orphan" in note_ids

    def test_sorted_by_content_length_descending(self) -> None:
        notes = [
            _note("small", content_length=100),
            _note("large", content_length=900),
            _note("medium", content_length=400),
        ]
        result = inspire_core.find_orphan_notes(notes)

        assert [r["note_id"] for r in result] == ["large", "medium", "small"]

    def test_respects_limit(self) -> None:
        notes = [_note(f"orphan-{i}", content_length=i) for i in range(10)]
        result = inspire_core.find_orphan_notes(notes, limit=3)

        assert len(result) == 3

    def test_tags_are_normalized(self) -> None:
        notes = [_note("orphan-1", tags=["Leadership", "one_on_ones"])]
        result = inspire_core.find_orphan_notes(notes)

        assert result[0]["tags"] == ["leadership", "one-on-ones"]


class TestFindOversizedNotes:
    """find_oversized_notes: content_length > min_length only."""

    def test_empty_notes(self) -> None:
        assert inspire_core.find_oversized_notes([]) == []

    def test_strictly_greater_than_min_length(self) -> None:
        notes = [
            _note("at-boundary", content_length=1000),
            _note("just-over", content_length=1001),
            _note("well-under", content_length=999),
        ]
        result = inspire_core.find_oversized_notes(notes, min_length=1000)

        assert [r["note_id"] for r in result] == ["just-over"]

    def test_sorted_longest_first(self) -> None:
        notes = [
            _note("medium", content_length=1500),
            _note("longest", content_length=3000),
            _note("shortest-oversized", content_length=1100),
        ]
        result = inspire_core.find_oversized_notes(notes, min_length=1000)

        assert [r["note_id"] for r in result] == ["longest", "medium", "shortest-oversized"]

    def test_respects_limit(self) -> None:
        notes = [_note(f"note-{i}", content_length=2000 + i) for i in range(10)]
        result = inspire_core.find_oversized_notes(notes, limit=2)

        assert len(result) == 2

    def test_default_threshold_matches_editor_guidance(self) -> None:
        assert inspire_core.SPLIT_MIN_LENGTH == 1000


class TestFindPromotionCandidates:
    """find_promotion_candidates: backlink_count >= min_backlinks only."""

    def test_empty_notes(self) -> None:
        assert inspire_core.find_promotion_candidates([]) == []

    def test_boundary_is_inclusive(self) -> None:
        notes = [
            _note("at-threshold", backlink_count=5),
            _note("below-threshold", backlink_count=4),
        ]
        result = inspire_core.find_promotion_candidates(notes, min_backlinks=5)

        assert [r["note_id"] for r in result] == ["at-threshold"]

    def test_sorted_most_referenced_first(self) -> None:
        notes = [
            _note("moderate", backlink_count=6),
            _note("most", backlink_count=20),
            _note("least", backlink_count=5),
        ]
        result = inspire_core.find_promotion_candidates(notes, min_backlinks=5)

        assert [r["note_id"] for r in result] == ["most", "moderate", "least"]

    def test_respects_limit(self) -> None:
        notes = [_note(f"note-{i}", backlink_count=10 + i) for i in range(10)]
        result = inspire_core.find_promotion_candidates(notes, limit=3)

        assert len(result) == 3

    def test_default_threshold(self) -> None:
        assert inspire_core.PROMOTE_MIN_BACKLINKS == 5


class TestFindUnlinkedSimilarNotes:
    """find_unlinked_similar_notes: similarity + link exclusion + kind."""

    def test_empty_embeddings(self) -> None:
        assert inspire_core.find_unlinked_similar_notes([], {}) == []

    def test_similar_unlinked_pair_is_found(self) -> None:
        embedding = [1.0, 0.0, 0.0]
        note_embeddings = [
            ("note-a", "Note A", embedding),
            ("note-b", "Note B", embedding),
        ]
        result = inspire_core.find_unlinked_similar_notes(
            note_embeddings=note_embeddings,
            existing_links={},
            similarity_threshold=0.7,
        )

        assert len(result) == 1
        assert result[0]["note_a_id"] == "note-a"
        assert result[0]["note_b_id"] == "note-b"
        assert result[0]["similarity"] == 1.0

    def test_excludes_pair_linked_forward(self) -> None:
        embedding = [1.0, 0.0, 0.0]
        note_embeddings = [("note-a", "Note A", embedding), ("note-b", "Note B", embedding)]
        existing_links = {"note-a": {"note-b"}}

        result = inspire_core.find_unlinked_similar_notes(
            note_embeddings=note_embeddings,
            existing_links=existing_links,
            similarity_threshold=0.7,
        )

        assert result == []

    def test_excludes_pair_linked_backward(self) -> None:
        embedding = [1.0, 0.0, 0.0]
        note_embeddings = [("note-a", "Note A", embedding), ("note-b", "Note B", embedding)]
        existing_links = {"note-b": {"note-a"}}

        result = inspire_core.find_unlinked_similar_notes(
            note_embeddings=note_embeddings,
            existing_links=existing_links,
            similarity_threshold=0.7,
        )

        assert result == []

    def test_below_threshold_excluded(self) -> None:
        note_embeddings = [
            ("note-a", "Note A", [1.0, 0.0, 0.0]),
            ("note-b", "Note B", [0.0, 1.0, 0.0]),
        ]
        result = inspire_core.find_unlinked_similar_notes(
            note_embeddings=note_embeddings,
            existing_links={},
            similarity_threshold=0.7,
        )

        assert result == []

    def test_high_similarity_high_title_overlap_is_duplicate(self) -> None:
        embedding = [1.0, 0.0, 0.0]
        note_embeddings = [
            ("note-a", "5 Dysfunctions of a Team", embedding),
            ("note-b", "Five Dysfunctions of a Team", embedding),
        ]
        result = inspire_core.find_unlinked_similar_notes(
            note_embeddings=note_embeddings, existing_links={}
        )

        assert len(result) == 1
        assert result[0]["kind"] == "duplicate"

    def test_high_similarity_low_title_overlap_is_connection(self) -> None:
        """Same embeddings, unrelated titles: siblings, not duplicates."""
        embedding = [1.0, 0.0, 0.0]
        note_embeddings = [
            ("note-a", "Developer Productivity: People Factors", embedding),
            ("note-b", "Developer Productivity: Process Factors", embedding),
        ]
        result = inspire_core.find_unlinked_similar_notes(
            note_embeddings=note_embeddings, existing_links={}
        )

        assert len(result) == 1
        assert result[0]["kind"] == "connection"

    def test_respects_limit(self) -> None:
        embedding = [1.0, 0.0, 0.0]
        note_embeddings = [(f"note-{i}", f"Note {i}", embedding) for i in range(5)]
        result = inspire_core.find_unlinked_similar_notes(
            note_embeddings=note_embeddings, existing_links={}, limit=2
        )

        assert len(result) == 2


class TestFindHubOpportunities:
    """find_hub_opportunities: connected components over similar-pairs."""

    def _pair(
        self, a: str, a_title: str, b: str, b_title: str, similarity: float = 0.9
    ) -> dict[str, Any]:
        return {
            "note_a_id": a,
            "note_a_title": a_title,
            "note_b_id": b,
            "note_b_title": b_title,
            "similarity": similarity,
            "title_overlap": 0.0,
            "kind": "connection",
        }

    def test_empty_pairs(self) -> None:
        assert inspire_core.find_hub_opportunities([]) == []

    def test_builds_connected_component_of_three(self) -> None:
        pairs = [
            self._pair("a", "A", "b", "B"),
            self._pair("b", "B", "c", "C"),
        ]
        result = inspire_core.find_hub_opportunities(pairs, min_cluster_size=3)

        assert len(result) == 1
        assert result[0]["note_ids"] == ["a", "b", "c"]
        assert result[0]["size"] == 3

    def test_below_min_cluster_size_excluded(self) -> None:
        pairs = [self._pair("d", "D", "e", "E")]
        result = inspire_core.find_hub_opportunities(pairs, min_cluster_size=3)

        assert result == []

    def test_largest_cluster_first(self) -> None:
        pairs = [
            # cluster of 3: a-b-c
            self._pair("a", "A", "b", "B"),
            self._pair("b", "B", "c", "C"),
            # cluster of 4: w-x-y-z
            self._pair("w", "W", "x", "X"),
            self._pair("x", "X", "y", "Y"),
            self._pair("y", "Y", "z", "Z"),
        ]
        result = inspire_core.find_hub_opportunities(pairs, min_cluster_size=3)

        assert [r["size"] for r in result] == [4, 3]

    def test_deterministic_ordering(self) -> None:
        pairs = [
            self._pair("c", "C", "a", "A"),
            self._pair("a", "A", "b", "B"),
        ]
        result = inspire_core.find_hub_opportunities(pairs, min_cluster_size=3)

        assert result[0]["note_ids"] == ["a", "b", "c"]

    def test_respects_limit(self) -> None:
        pairs = []
        # Three independent clusters of 3
        for group in (("a1", "a2", "a3"), ("b1", "b2", "b3"), ("c1", "c2", "c3")):
            pairs.append(self._pair(group[0], group[0], group[1], group[1]))
            pairs.append(self._pair(group[1], group[1], group[2], group[2]))

        result = inspire_core.find_hub_opportunities(pairs, min_cluster_size=3, limit=1)

        assert len(result) == 1


class TestFindUncoveredTagClusters:
    """find_uncovered_tag_clusters: tag frequency vs. article coverage."""

    def test_empty(self) -> None:
        assert inspire_core.find_uncovered_tag_clusters([], []) == []

    def test_uncovered_tag_with_enough_notes_is_returned(self) -> None:
        notes = [_note(f"note-{i}", tags=["leadership"]) for i in range(4)]
        result = inspire_core.find_uncovered_tag_clusters(notes, [], min_notes=4)

        assert len(result) == 1
        assert result[0]["tag"] == "leadership"
        assert result[0]["note_count"] == 4

    def test_below_min_notes_excluded(self) -> None:
        notes = [_note(f"note-{i}", tags=["leadership"]) for i in range(3)]
        result = inspire_core.find_uncovered_tag_clusters(notes, [], min_notes=4)

        assert result == []

    def test_covered_tag_is_excluded(self) -> None:
        notes = [_note(f"note-{i}", tags=["leadership"]) for i in range(4)]
        articles = [{"id": "article-1", "tags": ["leadership"]}]

        result = inspire_core.find_uncovered_tag_clusters(notes, articles, min_notes=4)

        assert result == []

    def test_tag_casing_normalized_on_both_sides(self) -> None:
        notes = [_note(f"note-{i}", tags=["Leadership"]) for i in range(4)]
        articles = [{"id": "article-1", "tags": ["leadership"]}]

        result = inspire_core.find_uncovered_tag_clusters(notes, articles, min_notes=4)

        assert result == []

    def test_respects_limit(self) -> None:
        notes: list[dict[str, Any]] = []
        for tag_num in range(5):
            notes.extend(
                _note(f"note-{tag_num}-{i}", tags=[f"tag-{tag_num}"]) for i in range(4)
            )
        result = inspire_core.find_uncovered_tag_clusters(notes, [], min_notes=4, limit=2)

        assert len(result) == 2


class TestComposeCandidates:
    """compose_candidates: round-robin interleaving across types."""

    def test_limit_zero_or_negative_returns_empty(self) -> None:
        candidates = {"orphan": [{"note_id": "a"}]}
        assert inspire_core.compose_candidates(candidates, limit=0) == []
        assert inspire_core.compose_candidates(candidates, limit=-1) == []

    def test_no_single_type_dominates(self) -> None:
        candidates = {
            "orphan": [{"note_id": f"orphan-{i}"} for i in range(10)],
            "duplicate": [{"note_a_id": "d1", "note_b_id": "d2"}],
        }
        result = inspire_core.compose_candidates(candidates, limit=5)

        assert len(result) == 5
        types = [item["type"] for item in result]
        assert "duplicate" in types
        assert types != ["orphan"] * 5

    def test_offset_changes_ordering(self) -> None:
        candidates = {"orphan": [{"note_id": f"orphan-{i}"} for i in range(5)]}

        result_a = inspire_core.compose_candidates(candidates, limit=5, offset=0)
        result_b = inspire_core.compose_candidates(candidates, limit=5, offset=2)

        ids_a = [item["data"]["note_id"] for item in result_a]
        ids_b = [item["data"]["note_id"] for item in result_b]
        assert ids_a != ids_b

    def test_empty_candidates_returns_empty(self) -> None:
        assert inspire_core.compose_candidates({}, limit=5) == []

    def test_stops_when_all_types_exhausted(self) -> None:
        candidates = {"orphan": [{"note_id": "only-one"}]}
        result = inspire_core.compose_candidates(candidates, limit=10)

        assert len(result) == 1


class TestComputeKbFingerprint:
    """compute_kb_fingerprint: stable, order-independent, change-sensitive."""

    def test_stable_regardless_of_list_order(self) -> None:
        notes = [
            _note("a", content_length=100, link_count=1, backlink_count=0),
            _note("b", content_length=200, link_count=0, backlink_count=2),
        ]
        articles = [{"id": "article-1"}, {"id": "article-2"}]

        fp1 = inspire_core.compute_kb_fingerprint(notes, articles)
        fp2 = inspire_core.compute_kb_fingerprint(list(reversed(notes)), list(reversed(articles)))

        assert fp1 == fp2

    def test_changes_when_content_length_changes(self) -> None:
        notes_a = [_note("a", content_length=100)]
        notes_b = [_note("a", content_length=101)]

        assert inspire_core.compute_kb_fingerprint(
            notes_a, []
        ) != inspire_core.compute_kb_fingerprint(notes_b, [])

    def test_changes_when_link_counts_change(self) -> None:
        notes_a = [_note("a", link_count=0, backlink_count=0)]
        notes_b = [_note("a", link_count=1, backlink_count=0)]

        assert inspire_core.compute_kb_fingerprint(
            notes_a, []
        ) != inspire_core.compute_kb_fingerprint(notes_b, [])

    def test_empty_input_is_stable(self) -> None:
        assert inspire_core.compute_kb_fingerprint([], []) == inspire_core.compute_kb_fingerprint(
            [], []
        )


class TestParseInspirationResponse:
    """parse_inspiration_response: tolerant JSON parsing + validation."""

    VALID_ITEM = (
        '{"type": "orphan", "title": "Test", "description": "Test", '
        '"related_notes": ["a"], "action_text": "Edit"}'
    )

    def test_valid_json_array(self) -> None:
        result = inspire_core.parse_inspiration_response(f"[{self.VALID_ITEM}]")

        assert len(result) == 1
        assert result[0]["type"] == "orphan"

    def test_markdown_fenced(self) -> None:
        response = f"```json\n[{self.VALID_ITEM}]\n```"
        result = inspire_core.parse_inspiration_response(response)

        assert len(result) == 1

    def test_json_wrapped_in_prose_on_both_sides(self) -> None:
        response = f"Sure! Here you go:\n[{self.VALID_ITEM}]\nHope that helps!"
        result = inspire_core.parse_inspiration_response(response)

        assert len(result) == 1
        assert result[0]["type"] == "orphan"

    def test_brackets_inside_string_values_do_not_break_extraction(self) -> None:
        item = (
            '{"type": "orphan", "title": "Test [1]", '
            '"description": "See [related] notes for context", '
            '"related_notes": ["a"], "action_text": "Edit"}'
        )
        response = f"Preamble text\n[{item}]\nTrailing text"
        result = inspire_core.parse_inspiration_response(response)

        assert len(result) == 1
        assert result[0]["title"] == "Test [1]"

    def test_invalid_type_rejected(self) -> None:
        item = (
            '{"type": "invalid", "title": "Test", "description": "Test", '
            '"related_notes": ["a"], "action_text": "Edit"}'
        )
        result = inspire_core.parse_inspiration_response(f"[{item}]")

        assert result == []

    def test_missing_required_fields_rejected(self) -> None:
        result = inspire_core.parse_inspiration_response('[{"type": "orphan", "title": "Test"}]')

        assert result == []

    def test_non_list_related_notes_rejected(self) -> None:
        item = (
            '{"type": "orphan", "title": "Test", "description": "Test", '
            '"related_notes": "not-a-list", "action_text": "Edit"}'
        )
        result = inspire_core.parse_inspiration_response(f"[{item}]")

        assert result == []

    def test_empty_input_returns_empty_list(self) -> None:
        assert inspire_core.parse_inspiration_response("") == []

    def test_single_object_wrapped_as_list(self) -> None:
        result = inspire_core.parse_inspiration_response(self.VALID_ITEM)

        assert len(result) == 1

    def test_unparseable_garbage_returns_empty_list(self) -> None:
        assert inspire_core.parse_inspiration_response("not json at all") == []


class TestBuildInspirationPrompt:
    """build_inspiration_prompt: includes candidate data and guardrails."""

    def test_includes_candidate_titles_and_ids(self) -> None:
        composed = [
            {
                "type": "orphan",
                "data": {"note_id": "lonely-note", "title": "Lonely Note"},
            }
        ]
        prompt = inspire_core.build_inspiration_prompt(composed)

        assert "Lonely Note" in prompt
        assert "lonely-note" in prompt

    def test_forbids_lengthening_notes(self) -> None:
        prompt = inspire_core.build_inspiration_prompt([])

        assert "never suggest making a note longer" in prompt.lower()

    def test_empty_composed_still_produces_prompt(self) -> None:
        prompt = inspire_core.build_inspiration_prompt([])

        assert "No opportunities found." in prompt


class TestBuildFallbackSuggestions:
    """build_fallback_suggestions: templated suggestions, no LLM required."""

    REQUIRED_FIELDS = {"type", "title", "description", "related_notes", "action_text"}

    def _composed_for_every_type(self) -> list[dict[str, Any]]:
        data_by_type: dict[str, dict[str, Any]] = {
            "orphan": {"note_id": "n1", "title": "Orphan Note"},
            "duplicate": {
                "note_a_id": "n1",
                "note_a_title": "Note A",
                "note_b_id": "n2",
                "note_b_title": "Note B",
                "similarity": 0.9,
            },
            "connection": {
                "note_a_id": "n1",
                "note_a_title": "Note A",
                "note_b_id": "n2",
                "note_b_title": "Note B",
                "similarity": 0.75,
            },
            "hub": {
                "note_ids": ["n1", "n2", "n3"],
                "titles": ["Note A", "Note B", "Note C"],
                "size": 3,
            },
            "promote": {"note_id": "n1", "title": "Popular Note", "backlink_count": 8},
            "split": {"note_id": "n1", "title": "Long Note", "content_length": 2000},
            "article": {
                "tag": "leadership",
                "note_count": 5,
                "note_ids": ["n1", "n2"],
                "titles": ["Note A", "Note B"],
            },
        }
        return [
            {"type": suggestion_type, "data": data_by_type[suggestion_type]}
            for suggestion_type in inspire_core.SUGGESTION_TYPES
        ]

    def test_produces_suggestion_for_every_type(self) -> None:
        composed = self._composed_for_every_type()
        result = inspire_core.build_fallback_suggestions(
            composed, limit=len(inspire_core.SUGGESTION_TYPES)
        )

        result_types = {item["type"] for item in result}
        assert result_types == set(inspire_core.SUGGESTION_TYPES)

    def test_every_suggestion_has_required_fields(self) -> None:
        composed = self._composed_for_every_type()
        result = inspire_core.build_fallback_suggestions(
            composed, limit=len(inspire_core.SUGGESTION_TYPES)
        )

        for suggestion in result:
            assert self.REQUIRED_FIELDS.issubset(suggestion.keys())

    def test_respects_limit(self) -> None:
        composed = self._composed_for_every_type()
        result = inspire_core.build_fallback_suggestions(composed, limit=3)

        assert len(result) == 3

    def test_no_suggestion_asks_to_expand_or_lengthen(self) -> None:
        """Regression guard for #259: fallback text must never ask for more content."""
        composed = self._composed_for_every_type()
        result = inspire_core.build_fallback_suggestions(
            composed, limit=len(inspire_core.SUGGESTION_TYPES)
        )

        for suggestion in result:
            description = suggestion["description"].lower()
            assert "expand" not in description
            assert "add more content" not in description


class TestSanitizeSuggestions:
    """sanitize_suggestions: the LLM is trusted for wording only."""

    COMPOSED: list[dict[str, Any]] = [
        {"type": "orphan", "data": {"note_id": "lonely-note", "title": "Lonely"}},
        {
            "type": "promote",
            "data": {"note_id": "popular-note", "title": "Popular", "backlink_count": 8},
        },
        {
            "type": "article",
            "data": {
                "tag": "sre",
                "note_count": 6,
                "note_ids": ["golden-signals", "error-budgets"],
                "titles": ["Golden Signals", "Error Budgets"],
            },
        },
    ]

    def _suggestion(self, **overrides: Any) -> dict[str, Any]:
        base = {
            "type": "orphan",
            "title": "A title",
            "description": "A description",
            "related_notes": ["lonely-note"],
            "action_text": "Do It",
        }
        base.update(overrides)
        return base

    def test_keeps_valid_note_ids(self) -> None:
        result = inspire_core.sanitize_suggestions([self._suggestion()], self.COMPOSED)

        assert len(result) == 1
        assert result[0]["related_notes"] == ["lonely-note"]

    def test_drops_hallucinated_note_ids(self) -> None:
        suggestion = self._suggestion(related_notes=["lonely-note", "does-not-exist"])
        result = inspire_core.sanitize_suggestions([suggestion], self.COMPOSED)

        assert result[0]["related_notes"] == ["lonely-note"]

    def test_drops_suggestion_with_no_valid_ids(self) -> None:
        """The LLM echoing a tag name where note IDs belong must not survive."""
        suggestion = self._suggestion(type="article", related_notes=["sre"])
        result = inspire_core.sanitize_suggestions([suggestion], self.COMPOSED)

        assert result == []

    def test_corrects_mislabelled_type(self) -> None:
        """A promote finding tagged 'hub' by the LLM is retyped from the analysis."""
        suggestion = self._suggestion(type="hub", related_notes=["popular-note"])
        result = inspire_core.sanitize_suggestions([suggestion], self.COMPOSED)

        assert result[0]["type"] == "promote"

    def test_matches_multi_note_candidate(self) -> None:
        suggestion = self._suggestion(
            type="connection", related_notes=["golden-signals", "error-budgets"]
        )
        result = inspire_core.sanitize_suggestions([suggestion], self.COMPOSED)

        assert result[0]["type"] == "article"
        assert result[0]["related_notes"] == ["golden-signals", "error-budgets"]

    def test_preserves_wording(self) -> None:
        """Sanitizing must not touch the text the LLM was actually useful for."""
        suggestion = self._suggestion(title="Nicely phrased", description="Well argued.")
        result = inspire_core.sanitize_suggestions([suggestion], self.COMPOSED)

        assert result[0]["title"] == "Nicely phrased"
        assert result[0]["description"] == "Well argued."

    def test_empty_composed_drops_everything(self) -> None:
        result = inspire_core.sanitize_suggestions([self._suggestion()], [])

        assert result == []


class TestCandidateNoteIds:
    """candidate_note_ids: extracting IDs from each candidate shape."""

    def test_single_note_candidate(self) -> None:
        assert inspire_core.candidate_note_ids({"note_id": "n1"}) == ["n1"]

    def test_pair_candidate(self) -> None:
        result = inspire_core.candidate_note_ids({"note_a_id": "n1", "note_b_id": "n2"})

        assert set(result) == {"n1", "n2"}

    def test_cluster_candidate(self) -> None:
        result = inspire_core.candidate_note_ids({"note_ids": ["n1", "n2", "n3"]})

        assert set(result) == {"n1", "n2", "n3"}

    def test_candidate_without_ids(self) -> None:
        assert inspire_core.candidate_note_ids({"tag": "sre"}) == []


# ============================================================================
# Endpoint integration tests: routers/inspire.py
# ============================================================================


class TestSuggestionsEndpoint:
    """Integration tests for GET /api/inspire/suggestions."""

    def test_empty_kb(self, client: TestClient) -> None:
        _override_dependencies(
            notes_service=FakeNotesService(), llm=FakeLLM(available=False), articles=[]
        )

        response = client.get("/api/inspire/suggestions")

        assert response.status_code == 200
        data = response.json()
        assert data["suggestions"] == []
        assert data["has_llm"] is False

    def test_with_notes_and_working_llm(self, client: TestClient) -> None:
        notes = [_note("orphan-1", title="Orphan One", content_length=200)]
        llm_response = (
            '[{"type": "orphan", "title": "Connect: Orphan One", '
            '"description": "Add a link.", "related_notes": ["orphan-1"], '
            '"action_text": "Connect Note"}]'
        )
        _override_dependencies(
            notes_service=FakeNotesService(notes_with_stats=notes),
            llm=FakeLLM(available=True, response=llm_response),
            articles=[],
        )

        response = client.get("/api/inspire/suggestions")

        assert response.status_code == 200
        data = response.json()
        assert data["has_llm"] is True
        assert len(data["suggestions"]) == 1
        assert data["suggestions"][0]["type"] == "orphan"

    def test_limit_honored(self, client: TestClient) -> None:
        notes = [_note(f"orphan-{i}", content_length=100 + i) for i in range(10)]
        _override_dependencies(
            notes_service=FakeNotesService(notes_with_stats=notes),
            llm=FakeLLM(available=False),
            articles=[],
        )

        response = client.get("/api/inspire/suggestions?limit=2")

        assert response.status_code == 200
        assert len(response.json()["suggestions"]) <= 2

    def test_refresh_returns_different_slice(self, client: TestClient) -> None:
        notes = [_note(f"orphan-{i}", content_length=100 + i) for i in range(5)]
        _override_dependencies(
            notes_service=FakeNotesService(notes_with_stats=notes),
            llm=FakeLLM(available=False),
            articles=[],
        )

        first = client.get("/api/inspire/suggestions?limit=1")
        second = client.get("/api/inspire/suggestions?limit=1&refresh=true")

        assert first.status_code == 200
        assert second.status_code == 200
        first_ids = first.json()["suggestions"][0]["related_notes"]
        second_ids = second.json()["suggestions"][0]["related_notes"]
        assert first_ids != second_ids

    def test_second_identical_call_is_cached(self, client: TestClient) -> None:
        notes = [_note("orphan-1", content_length=100)]
        _override_dependencies(
            notes_service=FakeNotesService(notes_with_stats=notes),
            llm=FakeLLM(available=False),
            articles=[],
        )

        first = client.get("/api/inspire/suggestions?limit=1")
        second = client.get("/api/inspire/suggestions?limit=1")

        assert first.json()["cached"] is False
        assert second.json()["cached"] is True

    def test_llm_exception_falls_back_to_templated_suggestions(
        self, client: TestClient
    ) -> None:
        notes = [_note("orphan-1", content_length=100)]
        _override_dependencies(
            notes_service=FakeNotesService(notes_with_stats=notes),
            llm=FakeLLM(available=True, raise_error=True),
            articles=[],
        )

        response = client.get("/api/inspire/suggestions")

        assert response.status_code == 200
        data = response.json()
        assert data["has_llm"] is False
        assert len(data["suggestions"]) >= 1

    def test_llm_garbage_response_falls_back_to_templated_suggestions(
        self, client: TestClient
    ) -> None:
        notes = [_note("orphan-1", content_length=100)]
        _override_dependencies(
            notes_service=FakeNotesService(notes_with_stats=notes),
            llm=FakeLLM(available=True, response="not valid json at all"),
            articles=[],
        )

        response = client.get("/api/inspire/suggestions")

        assert response.status_code == 200
        data = response.json()
        assert data["has_llm"] is False
        assert len(data["suggestions"]) >= 1


class TestGapsEndpoint:
    """Integration tests for GET /api/inspire/gaps."""

    def test_returns_expected_keys(self, client: TestClient) -> None:
        _override_dependencies(notes_service=FakeNotesService(), articles=[])

        response = client.get("/api/inspire/gaps")

        assert response.status_code == 200
        data = response.json()
        assert "orphans" in data
        assert "oversized" in data
        assert "promotable" in data
        assert "uncovered_topics" in data
        assert data["count"] == 0

    def test_populated_kb(self, client: TestClient) -> None:
        notes = [
            _note("orphan-1", content_length=200, link_count=0, backlink_count=0),
            _note("oversized-1", content_length=1500),
            _note("popular-1", backlink_count=6),
        ]
        _override_dependencies(notes_service=FakeNotesService(notes_with_stats=notes), articles=[])

        response = client.get("/api/inspire/gaps")

        assert response.status_code == 200
        data = response.json()
        assert any(o["note_id"] == "orphan-1" for o in data["orphans"])
        assert any(o["note_id"] == "oversized-1" for o in data["oversized"])
        assert any(o["note_id"] == "popular-1" for o in data["promotable"])


class TestConnectionsEndpoint:
    """Integration tests for GET /api/inspire/connections."""

    def test_returns_expected_keys(self, client: TestClient) -> None:
        _override_dependencies(notes_service=FakeNotesService())

        response = client.get("/api/inspire/connections")

        assert response.status_code == 200
        data = response.json()
        assert "connections" in data
        assert "duplicates" in data
        assert "hubs" in data
        assert data["count"] == 0

    def test_populated_kb(self, client: TestClient) -> None:
        embedding = [1.0, 0.0, 0.0]
        notes_with_embeddings = [
            {"id": "note-a", "title": "5 Dysfunctions of a Team", "embedding": embedding},
            {"id": "note-b", "title": "Five Dysfunctions of a Team", "embedding": embedding},
        ]
        _override_dependencies(
            notes_service=FakeNotesService(notes_with_embeddings=notes_with_embeddings)
        )

        response = client.get("/api/inspire/connections")

        assert response.status_code == 200
        data = response.json()
        assert len(data["duplicates"]) == 1
