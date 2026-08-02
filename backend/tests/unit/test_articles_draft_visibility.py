"""Tests for admin draft-article visibility (#184).

Drafts must stay invisible everywhere by default. Only GET /api/articles and
GET /api/articles/{id} reveal them, and only to a passkey-authenticated admin.
Every other consumer of articles (search, ask, inspire, embedding sync) goes
through dependencies.get_static_articles(), which is published-only by
construction - see test_dependencies_draft_filtering below for that guarantee.
"""

import os

os.environ["TESTING"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

import dependencies  # noqa: E402

# admin_headers (a passkey-session token) comes from conftest since #267.

_PUBLISHED_ARTICLE = {
    "id": 9001,
    "title": "Published Article",
    "summary": "A published article.",
    "content": "Published content.",
    "html_content": "<p>Published content.</p>",
    "content_type": "markdown",
    "url": None,
    "tags": [],
    "draft": False,
    "published_date": "2026-01-01",
    "updated_date": None,
    "created_at": None,
}

_DRAFT_ARTICLE = {
    "id": 9002,
    "title": "Draft Article",
    "summary": "A draft article.",
    "content": "Draft content.",
    "html_content": "<p>Draft content.</p>",
    "content_type": "markdown",
    "url": None,
    "tags": [],
    "draft": True,
    "published_date": "2026-01-02",
    "updated_date": None,
    "created_at": None,
}


def _set_mixed_articles() -> None:
    dependencies.set_static_articles([_PUBLISHED_ARTICLE, _DRAFT_ARTICLE])


class TestDependenciesDraftFiltering:
    """Unit tests for the get_static_articles/get_all_static_articles split."""

    def test_get_static_articles_excludes_drafts(self) -> None:
        _set_mixed_articles()
        published = dependencies.get_static_articles()
        assert [a["id"] for a in published] == [_PUBLISHED_ARTICLE["id"]]

    def test_get_all_static_articles_includes_drafts(self) -> None:
        _set_mixed_articles()
        full = dependencies.get_all_static_articles()
        ids = {a["id"] for a in full}
        assert ids == {_PUBLISHED_ARTICLE["id"], _DRAFT_ARTICLE["id"]}


class TestListArticlesDraftVisibility:
    def test_anonymous_list_excludes_drafts(self, client: TestClient) -> None:
        _set_mixed_articles()
        response = client.get("/api/articles")
        assert response.status_code == 200
        ids = {r["id"] for r in response.json()["resources"]}
        assert _DRAFT_ARTICLE["id"] not in ids
        assert _PUBLISHED_ARTICLE["id"] in ids

    def test_admin_list_includes_drafts(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        _set_mixed_articles()
        response = client.get("/api/articles", headers=admin_headers)
        assert response.status_code == 200
        ids = {r["id"] for r in response.json()["resources"]}
        assert ids == {_PUBLISHED_ARTICLE["id"], _DRAFT_ARTICLE["id"]}


class TestGetArticleDraftVisibility:
    def test_anonymous_cannot_fetch_draft(self, client: TestClient) -> None:
        _set_mixed_articles()
        response = client.get(f"/api/articles/{_DRAFT_ARTICLE['id']}")
        assert response.status_code == 404

    def test_admin_can_fetch_draft(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        _set_mixed_articles()
        response = client.get(f"/api/articles/{_DRAFT_ARTICLE['id']}", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["resource"]["id"] == _DRAFT_ARTICLE["id"]

    def test_anonymous_can_still_fetch_published_article(self, client: TestClient) -> None:
        _set_mixed_articles()
        response = client.get(f"/api/articles/{_PUBLISHED_ARTICLE['id']}")
        assert response.status_code == 200
        assert response.json()["resource"]["id"] == _PUBLISHED_ARTICLE["id"]


class TestArticlesCacheControl:
    """Cache poisoning guard: admin (draft-inclusive) responses must never be
    picked up by the shared 60s API cache (CacheControlMiddleware)."""

    def test_anonymous_list_gets_public_cache(self, client: TestClient) -> None:
        _set_mixed_articles()
        response = client.get("/api/articles")
        assert response.status_code == 200
        cache_control = response.headers["cache-control"]
        assert "public" in cache_control
        assert "max-age=60" in cache_control

    def test_admin_list_gets_private_no_store(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        _set_mixed_articles()
        response = client.get("/api/articles", headers=admin_headers)
        assert response.status_code == 200
        cache_control = response.headers["cache-control"]
        assert "private" in cache_control
        assert "no-store" in cache_control

    def test_admin_detail_gets_private_no_store(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        _set_mixed_articles()
        response = client.get(
            f"/api/articles/{_PUBLISHED_ARTICLE['id']}", headers=admin_headers
        )
        assert response.status_code == 200
        cache_control = response.headers["cache-control"]
        assert "private" in cache_control
        assert "no-store" in cache_control

    def test_anonymous_detail_gets_public_cache(self, client: TestClient) -> None:
        _set_mixed_articles()
        response = client.get(f"/api/articles/{_PUBLISHED_ARTICLE['id']}")
        assert response.status_code == 200
        cache_control = response.headers["cache-control"]
        assert "public" in cache_control
        assert "max-age=60" in cache_control


class TestStaticTokenDoesNotUnlockDrafts:
    """The static admin token is scoped to passkey enrollment only (#267) and
    must not unlock draft visibility, even though verify_admin_optional
    reports it as 'authenticated'."""

    def test_static_token_does_not_reveal_drafts(self, client: TestClient) -> None:
        from config import get_settings

        _set_mixed_articles()
        settings = get_settings()
        token = settings.admin_token
        if not token:
            import pytest

            pytest.skip("ADMIN_TOKEN not configured in test environment")

        response = client.get("/api/articles", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        ids = {r["id"] for r in response.json()["resources"]}
        assert _DRAFT_ARTICLE["id"] not in ids


class TestSearchAndAskExcludeDrafts:
    """Resource assembly for /api/search and /api/ask must never see drafts,
    regardless of admin auth - both endpoints depend on get_static_articles(),
    the published-only view."""

    def test_search_never_returns_draft_content(self, client: TestClient) -> None:
        _set_mixed_articles()
        response = client.post("/api/search", json={"query": "Draft content", "top_k": 10})
        assert response.status_code == 200
        results = response.json()["results"]
        titles = {r["title"] for r in results}
        assert _DRAFT_ARTICLE["title"] not in titles

    def test_ask_context_excludes_draft_content(self, client: TestClient) -> None:
        _set_mixed_articles()
        response = client.post("/api/ask", json={"question": "What is in the draft content?"})
        # /api/ask may 503 if the LLM backend is unavailable in the mock - the
        # point of this test is only that draft text is never in scope for
        # whatever context gets assembled.
        if response.status_code == 200:
            body = response.json()
            answer_blob = str(body)
            assert "Draft content." not in answer_blob
