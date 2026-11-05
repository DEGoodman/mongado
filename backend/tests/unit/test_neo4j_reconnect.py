"""Neo4jAdapter recovers when Neo4j comes up after the backend (#314).

After a droplet reboot every container starts at once, so the adapter's first
connect can fail. It must retry later instead of staying unavailable forever.
"""

from unittest.mock import MagicMock, patch

from neo4j.exceptions import ServiceUnavailable

from adapters.neo4j import Neo4jAdapter


def _working_driver() -> MagicMock:
    return MagicMock()


def _failing_driver() -> MagicMock:
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value.run.side_effect = ServiceUnavailable(
        "bolt not ready"
    )
    return driver


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _adapter(drivers: list[MagicMock], clock: _Clock) -> tuple[Neo4jAdapter, MagicMock]:
    factory = MagicMock(side_effect=drivers)
    with (
        patch("adapters.neo4j.GraphDatabase.driver", factory),
        patch("adapters.neo4j.time.monotonic", clock),
    ):
        adapter = Neo4jAdapter()
    return adapter, factory


def test_reconnects_after_cooldown() -> None:
    clock = _Clock()
    first, second = _failing_driver(), _working_driver()
    adapter, factory = _adapter([first, second], clock)
    assert adapter._available is False

    clock.now += Neo4jAdapter.RECONNECT_COOLDOWN_SECONDS
    with (
        patch("adapters.neo4j.GraphDatabase.driver", factory),
        patch("adapters.neo4j.time.monotonic", clock),
    ):
        assert adapter.is_available() is True

    assert factory.call_count == 2
    first.close.assert_called_once()  # failed driver's pool released
    assert adapter.driver is second


def test_no_retry_within_cooldown() -> None:
    clock = _Clock()
    adapter, factory = _adapter([_failing_driver(), _working_driver()], clock)

    clock.now += Neo4jAdapter.RECONNECT_COOLDOWN_SECONDS / 2
    with (
        patch("adapters.neo4j.GraphDatabase.driver", factory),
        patch("adapters.neo4j.time.monotonic", clock),
    ):
        assert adapter.is_available() is False

    assert factory.call_count == 1


def test_available_adapter_does_not_reconnect() -> None:
    clock = _Clock()
    adapter, factory = _adapter([_working_driver()], clock)

    clock.now += Neo4jAdapter.RECONNECT_COOLDOWN_SECONDS * 10
    with (
        patch("adapters.neo4j.GraphDatabase.driver", factory),
        patch("adapters.neo4j.time.monotonic", clock),
    ):
        assert adapter.is_available() is True

    assert factory.call_count == 1


def test_data_methods_trigger_reconnect() -> None:
    """Methods gate on is_available(), so a list call after Neo4j comes up works."""
    clock = _Clock()
    second = _working_driver()
    adapter, factory = _adapter([_failing_driver(), second], clock)

    clock.now += Neo4jAdapter.RECONNECT_COOLDOWN_SECONDS
    with (
        patch("adapters.neo4j.GraphDatabase.driver", factory),
        patch("adapters.neo4j.time.monotonic", clock),
    ):
        adapter.get_note_count()

    assert adapter.driver is second
