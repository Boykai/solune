"""Shared utilities for chat sub-modules."""

from __future__ import annotations

import asyncio
import json
from uuid import UUID

from src.logging_utils import get_logger
from src.models.chat import ChatMessage, SenderType
from src.models.recommendation import AITaskProposal, IssueRecommendation
from src.models.user import UserSession
from src.services.database import get_db
from src.utils import resolve_repository

from .state import (
    _PERSIST_BASE_DELAY,
    _PERSIST_MAX_RETRIES,
    _locks,
    _messages,
    _proposals,
    _recommendations,
)

logger = get_logger(__name__)


# ── Known safe ValueError messages ───────────────────────────────────────
_SAFE_ERROR_MESSAGES: dict[str, tuple[int, str]] = {
    "Cannot add steps": (409, "Cannot add steps to a non-draft plan."),
    "Cannot change approval": (409, "Cannot change approval status of steps in a non-draft plan."),
    "Cannot delete steps": (409, "Cannot delete steps from a non-draft plan."),
    "Cannot modify steps": (409, "Cannot modify steps in a non-draft plan."),
    "Cannot reorder steps": (409, "Cannot reorder steps in a non-draft plan."),
    "Cannot update steps": (409, "Cannot update steps of a non-draft plan."),
    "DAG validation failed": (400, "DAG validation failed: invalid step dependencies."),
    "Invalid approval_status": (400, "Invalid approval status value."),
    "step_ids must contain exactly the current step IDs": (
        400,
        "step_ids must contain exactly the current step IDs.",
    ),
}


def _get_lock(key: str) -> asyncio.Lock:
    """Return a per-key asyncio lock (lazy-created atomically)."""
    return _locks.setdefault(key, asyncio.Lock())


async def _retry_persist(
    fn,
    *args,
    context: str = "",
    **kwargs,
) -> None:
    """Retry a persistence function with exponential backoff.

    Only *transient* SQLite errors (``OperationalError`` — e.g. database
    locked, busy, I/O) are retried.  Permanent errors (``IntegrityError``,
    ``ProgrammingError``, etc.) are re-raised immediately.

    Raises :class:`PersistenceError` after all retries are exhausted.
    """
    import sqlite3

    from src.exceptions import PersistenceError

    last_exc: Exception | None = None
    for attempt in range(1, _PERSIST_MAX_RETRIES + 1):
        try:
            await fn(*args, **kwargs)
            return
        except sqlite3.OperationalError as exc:
            last_exc = exc
            logger.warning(
                "Persist attempt %d/%d failed (%s): %s",
                attempt,
                _PERSIST_MAX_RETRIES,
                context,
                exc,
            )
            if attempt < _PERSIST_MAX_RETRIES:
                await asyncio.sleep(_PERSIST_BASE_DELAY * (2 ** (attempt - 1)))
        except Exception:
            raise  # Non-transient — fail fast

    raise PersistenceError(
        f"Failed to persist {context} after {_PERSIST_MAX_RETRIES} retries",
        details={"context": context, "last_error": str(last_exc)},
    )


async def _persist_message(session_id: UUID, message: ChatMessage) -> None:
    """Persist a chat message to SQLite with retry."""
    from src.services import chat_store

    db = get_db()
    await _retry_persist(
        chat_store.save_message,
        db,
        session_id=str(session_id),
        message_id=str(message.message_id),
        sender_type=message.sender_type.value,
        content=message.content,
        action_type=message.action_type.value if message.action_type else None,
        action_data=json.dumps(message.action_data) if message.action_data else None,
        conversation_id=str(message.conversation_id) if message.conversation_id else None,
        context=f"message:{message.message_id}",
    )


async def _persist_proposal(proposal: AITaskProposal) -> None:
    """Persist a proposal to SQLite with retry."""
    from src.services import chat_store

    db = get_db()
    await _retry_persist(
        chat_store.save_proposal,
        db,
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


async def _persist_recommendation(recommendation: IssueRecommendation) -> None:
    """Persist a recommendation to SQLite with retry."""
    from src.services import chat_store

    db = get_db()
    await _retry_persist(
        chat_store.save_recommendation,
        db,
        session_id=str(recommendation.session_id),
        recommendation_id=str(recommendation.recommendation_id),
        data=json.dumps(recommendation.model_dump(mode="json")),
        status=recommendation.status.value,
        file_urls=recommendation.file_urls or None,
        context=f"recommendation:{recommendation.recommendation_id}",
    )


async def store_proposal(proposal: AITaskProposal) -> None:
    """Persist a proposal to SQLite, then update cache."""
    await _persist_proposal(proposal)
    _proposals[str(proposal.proposal_id)] = proposal


async def store_recommendation(recommendation: IssueRecommendation) -> None:
    """Persist a recommendation to SQLite, then update cache."""
    await _persist_recommendation(recommendation)
    _recommendations[str(recommendation.recommendation_id)] = recommendation


async def get_proposal(proposal_id: str) -> AITaskProposal | None:
    """Get a proposal by ID from cache or SQLite."""
    from src.models.recommendation import ProposalStatus

    # Fast path: in-memory cache
    proposal = _proposals.get(proposal_id)
    if proposal is not None:
        return proposal

    # Slow path: load from SQLite
    try:
        from src.services import chat_store

        db = get_db()
        row = await chat_store.get_proposal_by_id(db, proposal_id)
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
        _proposals[proposal_id] = proposal
        return proposal
    except Exception:
        logger.warning("Failed to load proposal from SQLite", exc_info=True)
        return None


async def get_recommendation(recommendation_id: str) -> IssueRecommendation | None:
    """Get a recommendation by ID from cache or SQLite."""
    from src.models.recommendation import RecommendationStatus

    # Fast path: in-memory cache
    rec = _recommendations.get(recommendation_id)
    if rec is not None:
        return rec

    # Slow path: load from SQLite
    try:
        from src.services import chat_store

        db = get_db()
        row = await chat_store.get_recommendation_by_id(db, recommendation_id)
        if row is None:
            return None
        data = json.loads(row["data"]) if isinstance(row["data"], str) else row["data"]
        rec = IssueRecommendation.model_validate(data)
        rec.status = RecommendationStatus(chat_store.recommendation_status_from_db(row["status"]))
        _recommendations[str(rec.recommendation_id)] = rec
        return rec
    except Exception:
        logger.warning("Failed to load recommendation from SQLite", exc_info=True)
        return None


def _default_expires_at(created_at_str: str) -> str:
    """Compute a fallback expires_at when the stored value is NULL."""
    from datetime import datetime, timedelta

    try:
        created = datetime.fromisoformat(created_at_str)
        return (created + timedelta(minutes=10)).isoformat()
    except (ValueError, TypeError):
        return created_at_str


async def _resolve_repository(session: UserSession) -> tuple[str, str]:
    """Resolve repository owner and name for issue creation."""
    from src.dependencies import require_selected_project

    project_id = require_selected_project(session)
    return await resolve_repository(session.access_token, project_id)


def _trigger_signal_delivery(
    session: UserSession,
    message: ChatMessage,
    project_name: str | None = None,
) -> None:
    """Fire-and-forget Signal delivery for assistant/system messages.

    Only delivers for non-user messages when the user has an active Signal connection.
    """
    if message.sender_type == SenderType.USER:
        return

    async def _deliver() -> None:
        try:
            from src.services.signal_delivery import deliver_chat_message_via_signal

            await deliver_chat_message_via_signal(
                github_user_id=session.github_user_id,
                message=message,
                project_name=project_name,
                project_id=session.selected_project_id,
            )
        except Exception as e:
            logger.debug("Signal delivery trigger failed (non-fatal): %s", e)

    try:
        from src.services.task_registry import task_registry

        task_registry.create_task(_deliver(), name="signal-delivery")
    except RuntimeError:
        pass  # No running event loop — skip silently


async def get_session_messages(session_id: UUID) -> list[ChatMessage]:
    """Get messages for a session from cache or SQLite."""
    from src.models.chat import ActionType, SenderType

    key = str(session_id)
    cached = _messages.get(key)
    if cached is not None:
        return cached

    # Load from SQLite on cache miss
    try:
        from src.services import chat_store

        db = get_db()
        rows = await chat_store.get_messages(db, key)
        messages = []
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
                    action_type=ActionType(row["action_type"]) if row.get("action_type") else None,
                    action_data=action_data,
                )
            )
        _messages[key] = messages
        return messages
    except Exception:
        logger.warning("Failed to load messages from SQLite", exc_info=True)
        return []


async def add_message(session_id: UUID, message: ChatMessage) -> None:
    """Persist a message to SQLite, then update cache."""
    key = str(session_id)
    await _persist_message(session_id, message)
    async with _get_lock(key):
        if key not in _messages:
            _messages[key] = []
        _messages[key].append(message)


def _safe_validation_detail(exc: ValueError) -> tuple[int, str]:
    """Return a (status_code, detail) pair for a domain ValueError.

    Returns 409 for non-draft plan conflicts, 400 for validation errors,
    and a generic 400 when the exception doesn't match a known prefix.
    Uses hardcoded messages only (never ``str(exc)``) to avoid leaking internals.
    """
    msg = str(exc)  # Used only for prefix matching; never returned to clients.
    for prefix, response in _SAFE_ERROR_MESSAGES.items():
        if msg.startswith(prefix):
            return response
    return 400, "Invalid request: validation failed."
