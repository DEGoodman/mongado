"""Unit tests for pure API-token logic (core/api_tokens.py, #300)."""

import pytest

from core.api_tokens import (
    ADMIN_WILDCARD,
    KNOWN_SCOPES,
    TOKEN_PREFIX,
    hash_token,
    is_expired,
    looks_like_api_token,
    scopes_satisfy,
    token_display_prefix,
    validate_scopes,
)


class TestHashToken:
    def test_deterministic(self) -> None:
        assert hash_token("mgd_abc") == hash_token("mgd_abc")

    def test_distinct_inputs_distinct_hashes(self) -> None:
        assert hash_token("mgd_abc") != hash_token("mgd_abd")

    def test_is_hex_sha256(self) -> None:
        digest = hash_token("mgd_abc")
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)


class TestDisplayPrefix:
    def test_reveals_prefix_and_a_few_chars(self) -> None:
        prefix = token_display_prefix("mgd_abcdefghijklmnop", chars=4)
        assert prefix == "mgd_abcd…"

    def test_short_token_not_truncated(self) -> None:
        assert token_display_prefix("mgd_ab", chars=8) == "mgd_ab"


class TestLooksLikeApiToken:
    def test_true_for_prefixed(self) -> None:
        assert looks_like_api_token(f"{TOKEN_PREFIX}whatever")

    def test_false_for_session_shaped(self) -> None:
        assert not looks_like_api_token("payload.signature")

    def test_false_for_static_token(self) -> None:
        assert not looks_like_api_token("some-static-admin-token")


class TestScopesSatisfy:
    def test_exact_match(self) -> None:
        assert scopes_satisfy({"notes:write"}, "notes:write")

    def test_missing_scope(self) -> None:
        assert not scopes_satisfy({"notes:write"}, "library:write")

    def test_admin_wildcard_satisfies_anything(self) -> None:
        assert scopes_satisfy({ADMIN_WILDCARD}, "library:write")
        assert scopes_satisfy({ADMIN_WILDCARD}, "feature_flags:write")

    def test_empty_grant_satisfies_nothing(self) -> None:
        assert not scopes_satisfy(set(), "notes:write")


class TestIsExpired:
    def test_none_never_expires(self) -> None:
        assert not is_expired(None, now=10_000_000_000.0)

    def test_future_expiry_not_expired(self) -> None:
        assert not is_expired(1000.0, now=999.0)

    def test_past_expiry_expired(self) -> None:
        assert is_expired(1000.0, now=1001.0)

    def test_exact_boundary_is_expired(self) -> None:
        assert is_expired(1000.0, now=1000.0)


class TestValidateScopes:
    def test_accepts_known_scopes(self) -> None:
        assert validate_scopes(["notes:write", "library:write"]) == [
            "notes:write",
            "library:write",
        ]

    def test_deduplicates_preserving_order(self) -> None:
        assert validate_scopes(["ai:use", "ai:use", "notes:write"]) == ["ai:use", "notes:write"]

    def test_strips_whitespace(self) -> None:
        assert validate_scopes([" notes:write "]) == ["notes:write"]

    def test_rejects_unknown_scope(self) -> None:
        with pytest.raises(ValueError, match="Unknown scope"):
            validate_scopes(["notes:destroy"])

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="At least one scope"):
            validate_scopes([])

    def test_all_known_scopes_validate(self) -> None:
        # Guards against KNOWN_SCOPES and validate_scopes drifting apart
        assert set(validate_scopes(sorted(KNOWN_SCOPES))) == set(KNOWN_SCOPES)
