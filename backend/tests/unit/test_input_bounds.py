"""Request-size bounds on public endpoints.

Unbounded strings on public AI/search endpoints let one request inflate a
hosted-LLM prompt (cost, provider 413s - see #279) or burn CPU in fuzzy
matching. Pydantic rejects oversized input with 422 before any work happens.
"""

from fastapi.testclient import TestClient


class TestSearchBounds:
    def test_oversized_query_rejected(self, client: TestClient) -> None:
        response = client.post("/api/search", json={"query": "x" * 501})
        assert response.status_code == 422

    def test_top_k_upper_bound(self, client: TestClient) -> None:
        response = client.post("/api/search", json={"query": "sre", "top_k": 10_000})
        assert response.status_code == 422

    def test_top_k_lower_bound(self, client: TestClient) -> None:
        response = client.post("/api/search", json={"query": "sre", "top_k": 0})
        assert response.status_code == 422

    def test_normal_query_accepted(self, client: TestClient) -> None:
        response = client.post("/api/search", json={"query": "sre", "top_k": 5})
        assert response.status_code == 200


class TestAiBounds:
    def test_oversized_question_rejected(self, client: TestClient) -> None:
        response = client.post("/api/ask", json={"question": "x" * 2001})
        assert response.status_code == 422

    def test_empty_question_rejected(self, client: TestClient) -> None:
        response = client.post("/api/ask", json={"question": ""})
        assert response.status_code == 422

    def test_oversized_synthesis_query_rejected(self, client: TestClient) -> None:
        response = client.post("/api/synthesize", json={"query": "x" * 1001})
        assert response.status_code == 422
