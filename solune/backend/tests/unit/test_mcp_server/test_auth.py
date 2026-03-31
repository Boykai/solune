"""Tests for GitHubTokenVerifier — token verification, caching, and rate limiting.

Covers:
- Valid token returns AccessToken
- Invalid token returns None
- Cache hit avoids GitHub API call
- Expired cache entry triggers re-verification
- Rate limiting blocks after max attempts
- Revoked token invalidates cache
- GitHub API unreachability returns None (no cache of failures)
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.services.mcp_server.auth import GitHubTokenVerifier, _hash_token
from src.services.mcp_server.context import McpContext

# ── McpContext Tests ────────────────────────────────────────────────


class TestMcpContext:
    def test_valid_context(self):
        ctx = McpContext(github_token="ghp_abc123", github_user_id=42, github_login="testuser")
        assert ctx.github_token == "ghp_abc123"
        assert ctx.github_user_id == 42
        assert ctx.github_login == "testuser"

    def test_empty_token_raises(self):
        with pytest.raises(ValueError, match="github_token must be non-empty"):
            McpContext(github_token="", github_user_id=42, github_login="testuser")

    def test_zero_user_id_raises(self):
        with pytest.raises(ValueError, match="github_user_id must be a positive integer"):
            McpContext(github_token="ghp_abc", github_user_id=0, github_login="testuser")

    def test_negative_user_id_raises(self):
        with pytest.raises(ValueError, match="github_user_id must be a positive integer"):
            McpContext(github_token="ghp_abc", github_user_id=-1, github_login="testuser")

    def test_empty_login_raises(self):
        with pytest.raises(ValueError, match="github_login must be non-empty"):
            McpContext(github_token="ghp_abc", github_user_id=42, github_login="")


# ── Token Hashing ──────────────────────────────────────────────────


class TestTokenHashing:
    def test_hash_is_deterministic(self):
        assert _hash_token("ghp_abc123") == _hash_token("ghp_abc123")

    def test_different_tokens_different_hashes(self):
        assert _hash_token("ghp_abc123") != _hash_token("ghp_xyz789")


# ── GitHubTokenVerifier ────────────────────────────────────────────


class TestVerifyToken:
    async def test_valid_token_returns_access_token(self):
        verifier = GitHubTokenVerifier()

        with patch.object(verifier, "_fetch_github_user", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"id": 42, "login": "testuser"}
            result = await verifier.verify_token("ghp_validtoken")

        assert result is not None
        assert result.client_id == "42"
        assert result.token == "ghp_validtoken"
        assert result.scopes == []

    async def test_invalid_token_returns_none(self):
        verifier = GitHubTokenVerifier()

        with patch.object(verifier, "_fetch_github_user", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None
            result = await verifier.verify_token("ghp_badtoken")

        assert result is None

    async def test_cache_hit_avoids_api_call(self):
        verifier = GitHubTokenVerifier()

        with patch.object(verifier, "_fetch_github_user", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"id": 42, "login": "testuser"}

            # First call — hits API
            result1 = await verifier.verify_token("ghp_cached")
            assert result1 is not None
            assert mock_fetch.call_count == 1

            # Second call — should use cache
            result2 = await verifier.verify_token("ghp_cached")
            assert result2 is not None
            assert result2.client_id == result1.client_id
            # No additional API call
            assert mock_fetch.call_count == 1

    async def test_expired_cache_triggers_reverification(self):
        verifier = GitHubTokenVerifier(cache_ttl=0)  # Immediate expiry

        with patch.object(verifier, "_fetch_github_user", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"id": 42, "login": "testuser"}

            await verifier.verify_token("ghp_expire")
            await verifier.verify_token("ghp_expire")

            # Both calls should hit the API (cache expired immediately)
            assert mock_fetch.call_count == 2

    async def test_rate_limiting_blocks_after_max_attempts(self):
        verifier = GitHubTokenVerifier(rate_limit_max=3, rate_limit_window=60)

        with patch.object(verifier, "_fetch_github_user", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None  # Invalid token

            # Exhaust rate limit
            for _ in range(3):
                await verifier.verify_token("ghp_rateme")

            assert mock_fetch.call_count == 3

            # Next attempt should be blocked without hitting API
            result = await verifier.verify_token("ghp_rateme")
            assert result is None
            assert mock_fetch.call_count == 3  # No additional call

    async def test_revoked_token_invalidates_cache(self):
        verifier = GitHubTokenVerifier()

        with patch.object(verifier, "_fetch_github_user", new_callable=AsyncMock) as mock_fetch:
            # First call: valid
            mock_fetch.return_value = {"id": 42, "login": "testuser"}
            result1 = await verifier.verify_token("ghp_revoke")
            assert result1 is not None

            # Expire cache to force re-verification
            token_hash = _hash_token("ghp_revoke")
            verifier._cache[token_hash].expires_at = 0

            # Second call: token revoked
            mock_fetch.return_value = None
            result2 = await verifier.verify_token("ghp_revoke")
            assert result2 is None
            # Cache should be invalidated
            assert token_hash not in verifier._cache

    async def test_github_api_unreachable_returns_none(self):
        verifier = GitHubTokenVerifier()

        with patch.object(verifier, "_fetch_github_user", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None
            result = await verifier.verify_token("ghp_unreachable")
            assert result is None

    async def test_get_context_for_valid_cached_token(self):
        verifier = GitHubTokenVerifier()

        with patch.object(verifier, "_fetch_github_user", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"id": 42, "login": "testuser"}
            await verifier.verify_token("ghp_ctx")

        ctx = verifier.get_context_for_token("ghp_ctx")
        assert ctx is not None
        assert ctx.github_user_id == 42
        assert ctx.github_login == "testuser"

    async def test_get_context_for_unknown_token_returns_none(self):
        verifier = GitHubTokenVerifier()
        ctx = verifier.get_context_for_token("ghp_unknown")
        assert ctx is None
