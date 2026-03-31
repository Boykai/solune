"""GitHub PAT token verification for the MCP server.

Implements the MCP SDK ``TokenVerifier`` protocol by calling the GitHub
API (``GET /user``) with the provided PAT.  Includes short-TTL caching
(60 s) to avoid redundant GitHub API calls and sliding-window rate
limiting (10 attempts per 60 s per token hash) to prevent abuse.
"""

from __future__ import annotations

import hashlib
import time
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import httpx

from src.logging_utils import get_logger
from src.services.mcp_server.context import McpContext

if TYPE_CHECKING:
    from mcp.server.auth.provider import AccessToken

logger = get_logger(__name__)

_CACHE_TTL_SECONDS: float = 60.0
_RATE_LIMIT_WINDOW: float = 60.0
_RATE_LIMIT_MAX_ATTEMPTS: int = 10
_MAX_CACHE_SIZE: int = 1024
_MAX_RATE_LIMIT_ENTRIES: int = 4096
_GITHUB_API_USER_URL = "https://api.github.com/user"


def _hash_token(token: str) -> str:
    """Return a SHA-256 hex digest of *token* for cache/rate-limit keys."""
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass
class TokenCacheEntry:
    """Cached result of a successful token verification."""

    access_token: AccessToken
    mcp_context: McpContext
    expires_at: float


@dataclass
class RateLimitEntry:
    """Sliding-window rate limit tracker for a single token hash."""

    attempts: deque[float] = field(default_factory=deque)


class GitHubTokenVerifier:
    """Verify GitHub PAT tokens and manage per-token caching/rate limiting.

    Implements the MCP SDK ``TokenVerifier`` protocol::

        async def verify_token(self, token: str) -> AccessToken | None
    """

    def __init__(
        self,
        *,
        cache_ttl: float = _CACHE_TTL_SECONDS,
        rate_limit_window: float = _RATE_LIMIT_WINDOW,
        rate_limit_max: int = _RATE_LIMIT_MAX_ATTEMPTS,
        max_cache_size: int = _MAX_CACHE_SIZE,
        max_rate_limit_entries: int = _MAX_RATE_LIMIT_ENTRIES,
    ) -> None:
        self._cache: dict[str, TokenCacheEntry] = {}
        self._rate_limits: dict[str, RateLimitEntry] = {}
        self._cache_ttl = cache_ttl
        self._rate_limit_window = rate_limit_window
        self._rate_limit_max = rate_limit_max
        self._max_cache_size = max_cache_size
        self._max_rate_limit_entries = max_rate_limit_entries

    # ------------------------------------------------------------------
    # Public API (MCP SDK TokenVerifier protocol)
    # ------------------------------------------------------------------

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify a GitHub PAT and return an ``AccessToken`` or ``None``."""
        from mcp.server.auth.provider import AccessToken as McpAccessToken

        # Early guard: ignore empty or whitespace-only tokens to avoid
        # unnecessary rate limiting/cache entries and external API calls.
        if not token or not token.strip():
            return None

        token_hash = _hash_token(token)
        now = time.monotonic()

        # 1. Cache hit — fast path, does not affect rate limiting
        cached = self._cache.get(token_hash)
        if cached is not None and cached.expires_at > now:
            return cached.access_token

        # 2. Rate limiting — only for GitHub API calls
        if self._is_rate_limited(token_hash, now):
            logger.warning("Rate-limited token verification for hash=%s…", token_hash[:12])
            return None

        self._record_attempt(token_hash, now)

        # 3. Call GitHub API
        user_info = await self._fetch_github_user(token)
        if user_info is None:
            # Invalidate cache if token was previously valid
            self._cache.pop(token_hash, None)
            return None

        github_user_id: int = user_info["id"]
        github_login: str = user_info["login"]

        access_token = McpAccessToken(
            token=token,
            client_id=str(github_user_id),
            scopes=[],
        )
        mcp_ctx = McpContext(
            github_token=token,
            github_user_id=github_user_id,
            github_login=github_login,
        )

        self._evict_expired_cache(now)
        self._cache[token_hash] = TokenCacheEntry(
            access_token=access_token,
            mcp_context=mcp_ctx,
            expires_at=now + self._cache_ttl,
        )

        return access_token

    def get_context_for_token(self, token: str) -> McpContext | None:
        """Return the cached ``McpContext`` for *token*, or ``None``."""
        token_hash = _hash_token(token)
        cached = self._cache.get(token_hash)
        if cached is not None and cached.expires_at > time.monotonic():
            return cached.mcp_context
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_rate_limited(self, token_hash: str, now: float) -> bool:
        entry = self._rate_limits.get(token_hash)
        if entry is None:
            return False
        # Prune expired timestamps
        cutoff = now - self._rate_limit_window
        while entry.attempts and entry.attempts[0] < cutoff:
            entry.attempts.popleft()
        return len(entry.attempts) >= self._rate_limit_max

    def _record_attempt(self, token_hash: str, now: float) -> None:
        self._evict_stale_rate_limits(now)
        entry = self._rate_limits.setdefault(token_hash, RateLimitEntry())
        entry.attempts.append(now)

    def _evict_expired_cache(self, now: float) -> None:
        """Remove expired cache entries and enforce max cache size."""
        expired = [k for k, v in self._cache.items() if v.expires_at <= now]
        for k in expired:
            del self._cache[k]
        # If still over limit, remove oldest entries
        while len(self._cache) >= self._max_cache_size:
            oldest_key = min(self._cache, key=lambda k: self._cache[k].expires_at)
            del self._cache[oldest_key]

    def _evict_stale_rate_limits(self, now: float) -> None:
        """Remove rate-limit entries with no recent attempts."""
        if len(self._rate_limits) <= self._max_rate_limit_entries:
            return
        cutoff = now - self._rate_limit_window
        stale = [
            k for k, v in self._rate_limits.items() if not v.attempts or v.attempts[-1] < cutoff
        ]
        for k in stale:
            del self._rate_limits[k]

    async def _fetch_github_user(self, token: str) -> dict | None:
        """Call ``GET /user`` on the GitHub API with the given PAT."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    _GITHUB_API_USER_URL,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                )
            if resp.status_code == 200:
                data = resp.json()
                if "id" in data and "login" in data:
                    return data
                logger.warning("GitHub /user response missing id or login")
                return None
            logger.info("GitHub /user returned status %d", resp.status_code)
            return None
        except httpx.HTTPError as exc:
            logger.warning("GitHub API unreachable during token verification: %s", exc)
            return None
