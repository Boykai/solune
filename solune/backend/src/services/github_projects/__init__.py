"""GitHub Projects V2 GraphQL service."""

from __future__ import annotations

import asyncio
import hashlib

from githubkit import GitHub, TokenAuthStrategy
from githubkit.retry import RETRY_RATE_LIMIT, RETRY_SERVER_ERROR, RetryChainDecision
from githubkit.throttling import LocalThrottler

from src.logging_utils import get_logger
from src.utils import BoundedDict

logger = get_logger(__name__)


class GitHubClientFactory:
    """Creates and pools authenticated githubkit client instances."""

    def __init__(self, max_pool_size: int = 50) -> None:
        self._pool: BoundedDict[str, GitHub] = BoundedDict(maxlen=max_pool_size)
        self._auto_retry = RetryChainDecision(RETRY_RATE_LIMIT, RETRY_SERVER_ERROR)
        self._lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        """Create the factory lock lazily under an active event loop."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def get_client(self, access_token: str) -> GitHub:
        """Return a pooled or newly created client for the given token."""
        key = hashlib.sha256(access_token.encode()).hexdigest()[:16]
        client = self._pool.get(key)
        if client is not None:
            return client
        async with self._get_lock():
            # Double-check after acquiring lock
            client = self._pool.get(key)
            if client is None:
                client = GitHub(
                    TokenAuthStrategy(access_token),
                    auto_retry=self._auto_retry,
                    http_cache=True,
                    throttler=LocalThrottler(100),
                    timeout=30.0,
                )
                self._pool[key] = client
        return client

    async def close_all(self) -> None:
        """Close all pooled clients. Called on application shutdown."""
        for client in self._pool.values():
            try:
                await client.__aexit__(None, None, None)
            except Exception as e:
                logger.debug("Suppressed error: %s", e)
        self._pool.clear()


from src.services.github_projects.service import GitHubProjectsService  # noqa: E402

# ── Lazy singleton accessor ────────────────────────────────────────────
_github_service: GitHubProjectsService | None = None


def get_github_service() -> GitHubProjectsService:
    """Return the ``GitHubProjectsService`` singleton.

    Creates the instance lazily on first call.  The application lifespan
    in ``main.py`` registers the same instance on ``app.state`` for
    FastAPI ``Depends()`` injection (see ``dependencies.py``).

    Background tasks, signal bridges, orchestrators, and other
    non-request contexts should call this function directly.
    """
    global _github_service
    if _github_service is None:
        _github_service = GitHubProjectsService()
    return _github_service


__all__ = [
    "GitHubClientFactory",
    "GitHubProjectsService",
    "get_github_service",
]
