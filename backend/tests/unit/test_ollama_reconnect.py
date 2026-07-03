"""Unit tests for OllamaClient lazy reconnection (issue #194)."""

import time

import pytest

from ollama_client import RECONNECT_COOLDOWN_SECONDS, OllamaClient


def _make_disconnected_client() -> OllamaClient:
    """Build an OllamaClient in the 'failed initial connect' state without I/O."""
    client = OllamaClient.__new__(OllamaClient)
    client.enabled = True
    client.client = None
    client._last_connect_attempt = time.monotonic()
    return client


class TestLazyReconnect:
    def test_disabled_client_never_connects(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_disconnected_client()
        client.enabled = False
        monkeypatch.setattr(client, "_try_connect", lambda: pytest.fail("must not attempt connect"))
        assert client.is_available() is False

    def test_no_retry_within_cooldown(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_disconnected_client()
        monkeypatch.setattr(
            client, "_try_connect", lambda: pytest.fail("must not retry within cooldown")
        )
        assert client.is_available() is False

    def test_retries_after_cooldown(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_disconnected_client()
        client._last_connect_attempt = time.monotonic() - RECONNECT_COOLDOWN_SECONDS - 1
        attempts: list[int] = []

        def fake_connect() -> bool:
            attempts.append(1)
            client.client = object()  # simulate successful connection
            return True

        monkeypatch.setattr(client, "_try_connect", fake_connect)
        assert client.is_available() is True
        assert attempts == [1]
        # Once connected, no further reconnect attempts
        assert client.is_available() is True
        assert attempts == [1]

    def test_failed_retry_stays_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_disconnected_client()
        client._last_connect_attempt = time.monotonic() - RECONNECT_COOLDOWN_SECONDS - 1

        def fake_connect() -> bool:
            client._last_connect_attempt = time.monotonic()
            return False

        monkeypatch.setattr(client, "_try_connect", fake_connect)
        assert client.is_available() is False

    def test_try_connect_failure_does_not_disable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A failed connection must not flip enabled=False (the old behavior)."""
        client = _make_disconnected_client()
        client.host = "http://localhost:1"  # nothing listening

        assert client._try_connect() is False
        assert client.enabled is True
        assert client.client is None

    def test_embeddings_available_mirrors_is_available(self) -> None:
        client = _make_disconnected_client()
        assert client.embeddings_available() is False
        client.client = object()
        assert client.embeddings_available() is True
