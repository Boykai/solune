"""ChatStateManager — encapsulates in-memory chat state with SQLite persistence.

Wraps the module-level global dicts from ``api/chat.py`` into a proper class
with read-through cache (check memory → SQLite fallback) and write-through
(persist to SQLite first → update memory on success) semantics.

This is a parallel structure introduced in Phase 1 of the modularity
refactoring.  The original globals in ``api/chat.py`` continue to work
until Phase 3 migrates the routes.
"""

from __future__ import annotations

import asyncio
import sqlite3
from typing import Any

from src.logging_utils import get_logger

logger = get_logger(__name__)


class ChatStateManager:
    """Manages in-memory chat state backed by SQLite persistence.

    Parameters:
        db: An ``aiosqlite.Connection`` (or compatible async DB handle).
        chat_store: The ``src.services.chat_store`` module (or duck-typed
            object exposing ``save_message``, ``get_messages``,
            ``clear_messages``, ``save_proposal``, ``get_proposal_by_id``,
            ``save_recommendation``, ``get_recommendation_by_id``,
            ``recommendation_status_from_db``).
        max_retries: Maximum retry attempts for transient SQLite errors.
        base_delay: Base delay in seconds for exponential backoff.
    """

    def __init__(
        self,
        db: Any,
        chat_store: Any,
        *,
        max_retries: int = 3,
        base_delay: float = 0.1,
    ) -> None:
        self._db = db
        self._chat_store = chat_store
        self._max_retries = max_retries
        self._base_delay = base_delay

        self._messages: dict[str, list[Any]] = {}
        self._proposals: dict[str, Any] = {}
        self._recommendations: dict[str, Any] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    # ── Lock management ──────────────────────────────────────────────

    def get_lock(self, key: str) -> asyncio.Lock:
        """Return a per-key asyncio lock (lazy-created)."""
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    # ── Retry helper ─────────────────────────────────────────────────

    async def _retry_persist(
        self,
        fn: Any,
        *args: Any,
        context: str = "",
        **kwargs: Any,
    ) -> Any:
        """Retry a persistence function with exponential backoff.

        Only transient SQLite errors (``OperationalError``) are retried.
        Returns the result of *fn* on success.
        """
        from src.exceptions import PersistenceError

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return await fn(*args, **kwargs)
            except sqlite3.OperationalError as exc:
                last_exc = exc
                logger.warning(
                    "Persist attempt %d/%d failed (%s): %s",
                    attempt,
                    self._max_retries,
                    context,
                    exc,
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(self._base_delay * (2 ** (attempt - 1)))
            except Exception:
                raise  # Non-transient — fail fast

        raise PersistenceError(
            f"Failed to persist {context} after {self._max_retries} retries",
            details={"context": context, "last_error": str(last_exc)},
        )

    # ── Messages ─────────────────────────────────────────────────────

    async def get_messages(self, session_id: str) -> list[Any]:
        """Get messages for a session (read-through cache)."""
        cached = self._messages.get(session_id)
        if cached is not None:
            return cached

        # SQLite fallback
        try:
            rows = await self._chat_store.get_messages(self._db, session_id)
            self._messages[session_id] = rows
            return rows
        except Exception:
            logger.warning("Failed to load messages from SQLite", exc_info=True)
            return []

    async def add_message(self, session_id: str, message: Any) -> None:
        """Persist a message to SQLite, then update the cache."""
        async with self.get_lock(session_id):
            await self._retry_persist(
                self._chat_store.save_message,
                self._db,
                session_id=session_id,
                message_id=str(getattr(message, "message_id", "")),
                sender_type=getattr(message, "sender_type", ""),
                content=getattr(message, "content", ""),
                action_type=getattr(message, "action_type", None),
                action_data=getattr(message, "action_data", None),
                context=f"message:{getattr(message, 'message_id', '')}",
            )
            if session_id not in self._messages:
                self._messages[session_id] = []
            self._messages[session_id].append(message)

    async def clear_messages(self, session_id: str) -> None:
        """Clear all messages for a session from cache and SQLite."""
        self._messages.pop(session_id, None)
        try:
            await self._chat_store.clear_messages(self._db, session_id)
        except Exception:
            logger.warning("Failed to clear messages from SQLite", exc_info=True)

    # ── Proposals ────────────────────────────────────────────────────

    async def get_proposal(self, proposal_id: str) -> Any | None:
        """Get a proposal by ID (read-through cache)."""
        cached = self._proposals.get(proposal_id)
        if cached is not None:
            return cached

        # SQLite fallback
        try:
            row = await self._chat_store.get_proposal_by_id(self._db, proposal_id)
            if row is None:
                return None
            self._proposals[proposal_id] = row
            return row
        except Exception:
            logger.warning("Failed to load proposal from SQLite", exc_info=True)
            return None

    async def store_proposal(self, proposal_id: str, proposal: Any) -> None:
        """Persist a proposal to SQLite, then update the cache."""
        await self._retry_persist(
            self._chat_store.save_proposal,
            self._db,
            proposal_id=proposal_id,
            proposal=proposal,
            context=f"proposal:{proposal_id}",
        )
        self._proposals[proposal_id] = proposal

    # ── Recommendations ──────────────────────────────────────────────

    async def get_recommendation(self, rec_id: str) -> Any | None:
        """Get a recommendation by ID (read-through cache)."""
        cached = self._recommendations.get(rec_id)
        if cached is not None:
            return cached

        # SQLite fallback
        try:
            row = await self._chat_store.get_recommendation_by_id(self._db, rec_id)
            if row is None:
                return None
            self._recommendations[rec_id] = row
            return row
        except Exception:
            logger.warning("Failed to load recommendation from SQLite", exc_info=True)
            return None

    async def store_recommendation(self, rec_id: str, rec: Any) -> None:
        """Persist a recommendation to SQLite, then update the cache."""
        await self._retry_persist(
            self._chat_store.save_recommendation,
            self._db,
            rec_id=rec_id,
            rec=rec,
            context=f"recommendation:{rec_id}",
        )
        self._recommendations[rec_id] = rec
