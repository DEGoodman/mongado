"""Runtime feature flags backed by Neo4j.

Flags are toggled at runtime via the admin API (/api/admin/feature-flags)
and persisted as FeatureFlag nodes in Neo4j. Environment settings only
provide the default when a flag has never been set.
"""

import logging
from dataclasses import dataclass

from fastapi import HTTPException

from adapters.neo4j import Neo4jAdapter, get_neo4j_adapter
from config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FlagDefinition:
    """A known feature flag with its metadata and default value."""

    name: str
    description: str
    default: bool


def _flag_definitions() -> dict[str, FlagDefinition]:
    """Build the registry of known flags (defaults come from settings)."""
    settings = get_settings()
    definitions = [
        FlagDefinition(
            name="llm_features",
            description="AI/LLM features: semantic search, Q&A, summaries, link suggestions",
            default=settings.llm_features_enabled,
        ),
    ]
    return {d.name: d for d in definitions}


class FeatureFlagService:
    """Read/write feature flags with an in-memory cache over Neo4j.

    The cache is loaded lazily on first read and kept authoritative for the
    process lifetime (only the admin API mutates flags, and this is a
    single-process app).
    """

    def __init__(self, neo4j: Neo4jAdapter) -> None:
        self.neo4j = neo4j
        self.definitions = _flag_definitions()
        self._cache: dict[str, bool] | None = None

    def _load(self) -> dict[str, bool]:
        """Load flags: persisted values override defaults."""
        if self._cache is None:
            flags = {name: d.default for name, d in self.definitions.items()}
            try:
                persisted = self.neo4j.get_feature_flags()
            except Exception as e:
                logger.warning("Failed to load feature flags from Neo4j: %s", e)
                persisted = {}
            for name, enabled in persisted.items():
                if name in flags:
                    flags[name] = enabled
            self._cache = flags
        return self._cache

    def is_enabled(self, name: str) -> bool:
        """Check whether a flag is enabled (defaults win if never persisted)."""
        return self._load().get(name, False)

    def all_flags(self) -> dict[str, bool]:
        """Get all known flags and their current values."""
        return dict(self._load())

    def set_flag(self, name: str, enabled: bool) -> bool:
        """Set a flag value, persisting to Neo4j.

        Args:
            name: Flag name (must be a known flag)
            enabled: New value

        Returns:
            True if persisted to Neo4j, False if only set in memory
            (Neo4j unavailable - value is lost on restart)

        Raises:
            KeyError: If the flag name is not a known flag
        """
        if name not in self.definitions:
            raise KeyError(name)
        persisted = self.neo4j.set_feature_flag(name, enabled)
        self._load()[name] = enabled
        if not persisted:
            logger.warning(
                "Feature flag '%s' set in memory only - Neo4j unavailable, "
                "value will reset on restart",
                name,
            )
        return persisted

    def reset_cache(self) -> None:
        """Clear the in-memory cache (reloads from Neo4j on next read)."""
        self._cache = None


_service: FeatureFlagService | None = None


def get_feature_flags() -> FeatureFlagService:
    """Get the global feature flag service (dependency-injectable in tests)."""
    global _service
    if _service is None:
        _service = FeatureFlagService(get_neo4j_adapter())
    return _service


def require_llm_features() -> None:
    """FastAPI dependency: reject the request when LLM features are disabled."""
    if not get_feature_flags().is_enabled("llm_features"):
        raise HTTPException(
            status_code=503,
            detail="LLM features are disabled. An admin can enable them at /api/admin/feature-flags.",
        )
