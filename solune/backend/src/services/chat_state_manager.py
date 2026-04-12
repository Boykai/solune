"""ChatStateManager — encapsulated chat state with read/write-through caching.

Replaces the module-level global dicts (``_messages``, ``_proposals``,
``_recommendations``, ``_locks``) in ``api/chat.py`` with instance-level
state backed by SQLite via :mod:`src.services.chat_store`.

Write operations persist to SQLite first, then update the in-memory cache.
Read operations check the cache first, falling back to SQLite on a miss.
Transient SQLite errors are retried with exponential backoff.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from typing import TYPE_CHECKING

from src.exceptions import PersistenceError
from src.logging_utils import get_logger
from src.models.chat import ActionType, ChatMessage, SenderType
from src.models.recommendation import (
    AITaskProposal,
    IssueRecommendation,
    ProposalStatus,
    RecommendationStatus,
)
from src.services import chat_store

if TYPE_CHECKING:
    import aiosqlite

logger = get_logger(__name__)


def _default_expires_at(created_at_str: str) -> str:
    """Compute a fallback ``expires_at`` when the stored value is NULL."""
    from datetime import datetime, timedelta

    try:
        created = datetime.fromisoformat(created_at_str)
        return (created + timedelta(minutes=10)).isoformat()
    except (ValueError, TypeError):
        return created_at_str


class ChatStateManager:
    """In-memory cache backed by SQLite for chat messages, proposals, and recommendations.

    Each instance maintains its own cache dicts and lock registry, making it
    safe to run multiple independent instances (e.g. in tests).
    """

    def __init__(
        self,
        db: aiosqlite.Connection,
        chat_store_module: object = chat_store,
        *,
        max_retries: int = 3,
        base_delay: float = 0.1,
    ) -> None:
        self._db = db
        self._store = chat_store_module
        self._max_retries = max_retries
        self._base_delay = base_delay

        # Per-instance caches
        self._messages: dict[str, list[ChatMessage]] = {}
        self._proposals: dict[str, AITaskProposal] = {}
        self._recommendations: dict[str, IssueRecommendation] = {}
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
        fn,
        *args,
        context: str = "",
        **kwargs,
    ) -> None:
        """Retry a persistence function with exponential backoff.

        Only *transient* SQLite errors (``OperationalError``) are retried.
        Permanent errors are re-raised immediately.
        """
        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                await fn(*args, **kwargs)
                return
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

    async def get_messages(self, session_id: str) -> list[ChatMessage]:
        """Get messages for a session from cache or SQLite."""
        cached = self._messages.get(session_id)
        if cached is not None:
            return cached

        try:
            rows = await self._store.get_messages(self._db, session_id)
            messages: list[ChatMessage] = []
            for row in rows:
                action_data = None
                if row.get("action_data"):
                    try:
                        action_data = json.loads(row["action_data"])
                    except (json.JSONDecodeError, TypeError):
                        action_data = None
                messages.append(
                    ChatMessage(
                        message_id=row["message_id"],
                        session_id=row["session_id"],
                        sender_type=SenderType(row["sender_type"]),
                        content=row["content"],
                        action_type=(
                            ActionType(row["action_type"]) if row.get("action_type") else None
                        ),
                        action_data=action_data,
                    )
                )
            self._messages[session_id] = messages
            return messages
        except Exception:
            logger.warning("Failed to load messages from SQLite", exc_info=True)
            return []

    async def add_message(self, session_id: str, message: ChatMessage) -> None:
        """Persist a message to SQLite, then update cache."""
        await self._retry_persist(
            self._store.save_message,
            self._db,
            session_id=session_id,
            message_id=str(message.message_id),
            sender_type=message.sender_type.value,
            content=message.content,
            action_type=message.action_type.value if message.action_type else None,
            action_data=json.dumps(message.action_data) if message.action_data else None,
            conversation_id=str(message.conversation_id) if message.conversation_id else None,
            context=f"message:{message.message_id}",
        )
        async with self.get_lock(session_id):
            if session_id not in self._messages:
                self._messages[session_id] = []
            self._messages[session_id].append(message)

    async def clear_messages(self, session_id: str) -> None:
        """Clear messages for a session from cache and SQLite."""
        await self._store.clear_messages(self._db, session_id)
        self._messages.pop(session_id, None)

    # ── Proposals ────────────────────────────────────────────────────

    async def store_proposal(self, proposal_id: str, proposal: AITaskProposal) -> None:
        """Persist a proposal to SQLite, then update cache."""
        await self._retry_persist(
            self._store.save_proposal,
            self._db,
            session_id=str(proposal.session_id),
            proposal_id=str(proposal.proposal_id),
            original_input=proposal.original_input,
            proposed_title=proposal.proposed_title,
            proposed_description=proposal.proposed_description,
            status=proposal.status.value,
            edited_title=proposal.edited_title,
            edited_description=proposal.edited_description,
            created_at=proposal.created_at.isoformat(),
            expires_at=proposal.expires_at.isoformat(),
            file_urls=proposal.file_urls or None,
            selected_pipeline_id=proposal.selected_pipeline_id,
            context=f"proposal:{proposal.proposal_id}",
        )
        self._proposals[proposal_id] = proposal

    async def get_proposal(self, proposal_id: str) -> AITaskProposal | None:
        """Get a proposal by ID from cache or SQLite."""
        proposal = self._proposals.get(proposal_id)
        if proposal is not None:
            return proposal

        try:
            row = await self._store.get_proposal_by_id(self._db, proposal_id)
            if row is None:
                return None
            from datetime import datetime as _dt

            raw_expires = row["expires_at"] or _default_expires_at(row["created_at"])
            parsed_expires = (
                _dt.fromisoformat(raw_expires) if isinstance(raw_expires, str) else raw_expires
            )

            proposal = AITaskProposal(
                proposal_id=row["proposal_id"],
                session_id=row["session_id"],
                original_input=row["original_input"],
                proposed_title=row["proposed_title"],
                proposed_description=row["proposed_description"],
                status=ProposalStatus(row["status"]),
                edited_title=row.get("edited_title"),
                edited_description=row.get("edited_description"),
                file_urls=row.get("file_urls", []),
                selected_pipeline_id=row.get("selected_pipeline_id"),
                created_at=row["created_at"],
                expires_at=parsed_expires,
            )
            self._proposals[proposal_id] = proposal
            return proposal
        except Exception:
            logger.warning("Failed to load proposal from SQLite", exc_info=True)
            return None

    # ── Recommendations ──────────────────────────────────────────────

    async def store_recommendation(
        self, recommendation_id: str, recommendation: IssueRecommendation
    ) -> None:
        """Persist a recommendation to SQLite, then update cache."""
        await self._retry_persist(
            self._store.save_recommendation,
            self._db,
            session_id=str(recommendation.session_id),
            recommendation_id=str(recommendation.recommendation_id),
            data=json.dumps(recommendation.model_dump(mode="json")),
            status=recommendation.status.value,
            file_urls=recommendation.file_urls or None,
            context=f"recommendation:{recommendation.recommendation_id}",
        )
        self._recommendations[recommendation_id] = recommendation

    async def get_recommendation(
        self, recommendation_id: str
    ) -> IssueRecommendation | None:
        """Get a recommendation by ID from cache or SQLite."""
        rec = self._recommendations.get(recommendation_id)
        if rec is not None:
            return rec

        try:
            row = await self._store.get_recommendation_by_id(self._db, recommendation_id)
            if row is None:
                return None
            data = json.loads(row["data"]) if isinstance(row["data"], str) else row["data"]
            rec = IssueRecommendation.model_validate(data)
            rec.status = RecommendationStatus(
                chat_store.recommendation_status_from_db(row["status"])
            )
            self._recommendations[str(rec.recommendation_id)] = rec
            return rec
        except Exception:
            logger.warning("Failed to load recommendation from SQLite", exc_info=True)
            return None
