"""Unit tests for core.ai module (pure business logic).

These tests verify pure functions with no I/O dependencies.
All functions should be deterministic: same input → same output.
"""

import pytest

from core import ai


class TestCosineSimilarity:
    """Tests for cosine similarity calculation."""

    def test_identical_vectors(self):
        """Identical vectors should have similarity of 1.0."""
        vec = [1.0, 2.0, 3.0]
        assert ai.cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """Orthogonal vectors should have similarity of 0.0."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        assert ai.cosine_similarity(vec1, vec2) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        """Opposite vectors should have similarity of -1.0."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [-1.0, -2.0, -3.0]
        assert ai.cosine_similarity(vec1, vec2) == pytest.approx(-1.0)

    def test_different_lengths(self):
        """Vectors of different lengths should return 0.0."""
        vec1 = [1.0, 2.0]
        vec2 = [1.0, 2.0, 3.0]
        assert ai.cosine_similarity(vec1, vec2) == 0.0

    def test_zero_vectors(self):
        """Zero vectors should return 0.0 (avoid division by zero)."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 2.0, 3.0]
        assert ai.cosine_similarity(vec1, vec2) == 0.0


class TestRankDocumentsBySimilarity:
    """Tests for document ranking by similarity."""

    def test_ranks_by_similarity(self):
        """Documents should be ranked by descending similarity."""
        query_emb = [1.0, 0.0, 0.0]
        docs = [
            {"id": "doc1", "embedding": [0.5, 0.5, 0.0]},  # Low similarity
            {"id": "doc2", "embedding": [1.0, 0.0, 0.0]},  # High similarity
            {"id": "doc3", "embedding": [0.8, 0.2, 0.0]},  # Medium similarity
        ]

        results = ai.rank_documents_by_similarity(query_emb, docs, top_k=3)

        assert len(results) == 3
        assert results[0]["id"] == "doc2"  # Highest similarity first
        assert results[1]["id"] == "doc3"
        assert results[2]["id"] == "doc1"
        assert "score" in results[0]
        assert results[0]["score"] > results[1]["score"]

    def test_respects_top_k(self):
        """Should return at most top_k results."""
        query_emb = [1.0, 0.0]
        docs = [{"id": f"doc{i}", "embedding": [1.0, 0.0]} for i in range(10)]

        results = ai.rank_documents_by_similarity(query_emb, docs, top_k=3)
        assert len(results) == 3

    def test_skips_docs_without_embeddings(self):
        """Documents without embeddings should be skipped."""
        query_emb = [1.0, 0.0]
        docs = [
            {"id": "doc1", "embedding": [1.0, 0.0]},
            {"id": "doc2"},  # No embedding
            {"id": "doc3", "embedding": [0.5, 0.5]},
        ]

        results = ai.rank_documents_by_similarity(query_emb, docs, top_k=10)
        assert len(results) == 2
        assert all("score" in doc for doc in results)


class TestBuildContextFromDocuments:
    """Tests for building context strings from documents."""

    def test_formats_documents_correctly(self):
        """Should format documents with titles and content."""
        docs = [
            {"title": "Doc 1", "content": "Content 1"},
            {"title": "Doc 2", "content": "Content 2"},
        ]

        context = ai.build_context_from_documents(docs)

        assert "### Doc 1" in context
        assert "Content 1" in context
        assert "### Doc 2" in context
        assert "Content 2" in context

    def test_handles_empty_list(self):
        """Empty document list should return 'No relevant documents'."""
        context = ai.build_context_from_documents([])
        assert context == "No relevant documents found."

    def test_respects_max_docs(self):
        """Should only include up to max_docs."""
        docs = [{"title": f"Doc {i}", "content": f"Content {i}"} for i in range(10)]

        context = ai.build_context_from_documents(docs, max_docs=3)

        assert "### Doc 0" in context
        assert "### Doc 1" in context
        assert "### Doc 2" in context
        assert "### Doc 3" not in context

    def test_handles_missing_titles(self):
        """Missing titles should default to 'Document N'."""
        docs = [
            {"content": "Content without title"},
        ]

        context = ai.build_context_from_documents(docs)
        assert "### Document 1" in context


class TestBuildQAPrompt:
    """Tests for Q&A prompt construction."""

    def test_includes_question_and_context(self):
        """Prompt should include question and context documents."""
        question = "What is the answer?"
        docs = [{"title": "Test Doc", "content": "Test content"}]

        prompt = ai.build_qa_prompt(question, docs)

        assert "What is the answer?" in prompt
        assert "Test Doc" in prompt
        assert "Test content" in prompt

    def test_allows_general_knowledge(self):
        """With allow_general_knowledge=True, should mention general knowledge."""
        question = "Test question"
        docs = [{"title": "Doc", "content": "Content"}]

        prompt = ai.build_qa_prompt(question, docs, allow_general_knowledge=True)
        assert "general knowledge" in prompt.lower()

    def test_kb_only_mode(self):
        """With allow_general_knowledge=False, should restrict to KB."""
        question = "Test question"
        docs = [{"title": "Doc", "content": "Content"}]

        prompt = ai.build_qa_prompt(question, docs, allow_general_knowledge=False)
        assert "don't have enough information" in prompt.lower()


class TestParseJSONResponse:
    """Tests for defensive JSON parsing."""

    def test_parses_valid_array(self):
        """Valid JSON array should parse correctly."""
        response = '[{"tag": "test", "confidence": 0.9}]'
        result = ai.parse_json_response(response, expected_type="array")

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["tag"] == "test"

    def test_strips_markdown_wrappers(self):
        """Should strip ```json and ``` wrappers."""
        response = '```json\n[{"tag": "test"}]\n```'
        result = ai.parse_json_response(response, expected_type="array")

        assert result is not None
        assert isinstance(result, list)

    def test_converts_object_to_array(self):
        """Single object should be wrapped in array if expected_type is array."""
        response = '{"tag": "test", "confidence": 0.9}'
        result = ai.parse_json_response(response, expected_type="array")

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 1

    def test_parses_line_by_line_json(self):
        """Should handle newline-delimited JSON objects."""
        response = '{"tag": "test1"}\n{"tag": "test2"}\n'
        result = ai.parse_json_response(response, expected_type="array")

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 2

    def test_returns_none_for_invalid_json(self):
        """Invalid JSON should return None."""
        response = "This is not JSON at all"
        result = ai.parse_json_response(response, expected_type="array")
        assert result is None

    def test_handles_empty_response(self):
        """Empty response should return None."""
        result = ai.parse_json_response("", expected_type="array")
        assert result is None


class TestPromptBuilders:
    """Tests for specialized prompt builders."""

    def test_build_tag_suggestion_prompt(self):
        """Tag suggestion prompt should include note info and existing tags."""
        title = "Test Note"
        content = "Some content about management"
        current_tags = ["existing"]
        existing_tags = {"tag1", "tag2", "existing"}

        prompt = ai.build_tag_suggestion_prompt(title, content, current_tags, existing_tags)

        assert "Test Note" in prompt
        assert "management" in prompt
        assert "existing" in prompt
        assert "tag1" in prompt or "tag2" in prompt

    def test_filter_link_candidates(self):
        """Should exclude current note and existing links."""
        all_notes = [
            {"id": "note-1", "content": "Content 1"},
            {"id": "note-2", "content": "Content 2"},
            {"id": "note-3", "content": "Content 3"},
            {"id": "note-4"},  # No content
        ]

        candidates = ai.filter_link_candidates(
            all_notes, current_note_id="note-1", existing_links=["note-2"]
        )

        # Should exclude note-1 (current), note-2 (existing link), note-4 (no content)
        assert len(candidates) == 1
        assert candidates[0]["id"] == "note-3"

    def test_build_link_suggestion_prompt(self):
        """Link suggestion prompt should format candidates correctly."""
        current_title = "Current Note"
        current_content = "Current content"
        candidates = [
            {"id": "note-1", "title": "Candidate 1", "content": "Content 1"},
            {"id": "note-2", "title": "Candidate 2", "content": "Content 2"},
        ]

        prompt = ai.build_link_suggestion_prompt(current_title, current_content, candidates)

        assert "Current Note" in prompt
        assert "Candidate 1" in prompt
        assert "note-1" in prompt


class TestMeanVector:
    """Tests for mean_vector (chunk -> whole-document embedding, #192)."""

    def test_single_vector_is_identity(self):
        assert ai.mean_vector([[1.0, 2.0, 3.0]]) == [1.0, 2.0, 3.0]

    def test_mean_of_two_vectors(self):
        result = ai.mean_vector([[1.0, 0.0], [0.0, 1.0]])
        assert result == pytest.approx([0.5, 0.5])

    def test_empty_input(self):
        assert ai.mean_vector([]) == []

    def test_mismatched_lengths_return_empty(self):
        assert ai.mean_vector([[1.0, 2.0], [1.0]]) == []


class TestRankParentsByChunkSimilarity:
    """Tests for chunk-level ranking with max aggregation (#192)."""

    def test_parent_ranks_on_best_chunk(self):
        """One strongly matching section outranks uniformly mediocre documents."""
        query = [1.0, 0.0, 0.0]
        chunks = [
            # doc-a: one great chunk among poor ones
            {"parent_type": "Article", "parent_id": "a", "embedding": [0.0, 1.0, 0.0]},
            {"parent_type": "Article", "parent_id": "a", "embedding": [1.0, 0.0, 0.0]},
            # doc-b: all chunks mediocre
            {"parent_type": "Article", "parent_id": "b", "embedding": [0.7, 0.7, 0.0]},
            {"parent_type": "Article", "parent_id": "b", "embedding": [0.6, 0.8, 0.0]},
        ]

        results = ai.rank_parents_by_chunk_similarity(query, chunks, top_k=5)

        assert [r["id"] for r in results] == ["a", "b"]
        assert results[0]["score"] == pytest.approx(1.0)

    def test_respects_top_k(self):
        query = [1.0, 0.0]
        chunks = [
            {"parent_type": "Note", "parent_id": str(i), "embedding": [1.0, i / 10]}
            for i in range(5)
        ]
        results = ai.rank_parents_by_chunk_similarity(query, chunks, top_k=2)
        assert len(results) == 2

    def test_skips_chunks_without_embedding(self):
        query = [1.0, 0.0]
        chunks = [
            {"parent_type": "Note", "parent_id": "x", "embedding": None},
            {"parent_type": "Note", "parent_id": "y", "embedding": [1.0, 0.0]},
        ]
        results = ai.rank_parents_by_chunk_similarity(query, chunks, top_k=5)
        assert [r["id"] for r in results] == ["y"]

    def test_mixed_types_keep_identity(self):
        query = [1.0, 0.0]
        chunks = [
            {"parent_type": "Article", "parent_id": "1", "embedding": [1.0, 0.0]},
            {"parent_type": "Note", "parent_id": "wise-mountain", "embedding": [0.9, 0.1]},
        ]
        results = ai.rank_parents_by_chunk_similarity(query, chunks, top_k=5)
        assert results[0] == {"id": "1", "type": "Article", "score": pytest.approx(1.0)}
        assert results[1]["type"] == "Note"

    def test_empty_chunks(self):
        assert ai.rank_parents_by_chunk_similarity([1.0], [], top_k=5) == []
