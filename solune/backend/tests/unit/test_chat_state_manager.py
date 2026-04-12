"""Unit tests for ChatStateManager.

Covers:
- Instantiation with mocked dependencies
- get_lock returns same lock for same key
- get_messages read-through cache (memory → SQLite)
- add_message write-through (SQLite → cache)
- store_proposal / get_proposal round-trip
- store_recommendation / get_recommendation round-trip
- Multiple independent instances have separate state
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models.chat import ChatMessage, SenderType
from src.models.recommendation import (
    AITaskProposal,
    IssueRecommendation,
    ProposalStatus,
    RecommendationStatus,
)
from src.services.chat_state_manager import ChatStateManager

# Stable UUIDs for deterministic tests
SESSION_UUID = uuid4()
SESSION_ID = str(SESSION_UUID)


# =============================================================================
# Helpers
# =============================================================================


def _make_chat_message(session_id: str = SESSION_ID, content: str = "hello") -> ChatMessage:
    return ChatMessage(
        session_id=session_id,
        sender_type=SenderType.USER,
        content=content,
    )


def _make_proposal(session_id: str = SESSION_ID) -> AITaskProposal:
    return AITaskProposal(
        session_id=session_id,
        original_input="fix the bug",
        proposed_title="Fix Login Bug",
        proposed_description="Resolve the authentication failure.",
    )


def _make_recommendation(session_id: str = SESSION_ID) -> IssueRecommendation:
    return IssueRecommendation(
        session_id=session_id,
        original_input="add CSV export",
        title="Add CSV Export",
        user_story="As a user, I want to export data as CSV.",
        ui_ux_description="Add an Export button in settings.",
        functional_requirements=["System MUST generate CSV"],
    )


def _mock_store() -> MagicMock:
    """Return a mock chat_store module with all required async functions."""
    store = MagicMock()
    store.save_message = AsyncMock()
    store.get_messages = AsyncMock(return_value=[])
    store.clear_messages = AsyncMock()
    store.save_proposal = AsyncMock()
    store.get_proposal_by_id = AsyncMock(return_value=None)
    store.save_recommendation = AsyncMock()
    store.get_recommendation_by_id = AsyncMock(return_value=None)
    store.recommendation_status_from_db = MagicMock(side_effect=lambda s: s)
    return store


def _build_manager(store: MagicMock | None = None) -> ChatStateManager:
    """Create a ChatStateManager with a mocked db and optional store."""
    db = AsyncMock(name="aiosqlite.Connection")
    if store is None:
        store = _mock_store()
    return ChatStateManager(db, store, max_retries=2, base_delay=0.001)


# =============================================================================
# Tests — Instantiation
# =============================================================================


class TestInstantiation:
    def test_creates_with_empty_caches(self):
        mgr = _build_manager()
        assert mgr._messages == {}
        assert mgr._proposals == {}
        assert mgr._recommendations == {}
        assert mgr._locks == {}

    def test_custom_retry_parameters(self):
        db = AsyncMock()
        mgr = ChatStateManager(db, _mock_store(), max_retries=5, base_delay=0.5)
        assert mgr._max_retries == 5
        assert mgr._base_delay == 0.5


# =============================================================================
# Tests — Locks
# =============================================================================


class TestGetLock:
    def test_returns_asyncio_lock(self):
        mgr = _build_manager()
        lock = mgr.get_lock("key-1")
        assert isinstance(lock, asyncio.Lock)

    def test_same_key_returns_same_lock(self):
        mgr = _build_manager()
        lock_a = mgr.get_lock("key-1")
        lock_b = mgr.get_lock("key-1")
        assert lock_a is lock_b

    def test_different_keys_return_different_locks(self):
        mgr = _build_manager()
        lock_a = mgr.get_lock("key-1")
        lock_b = mgr.get_lock("key-2")
        assert lock_a is not lock_b


# =============================================================================
# Tests — Messages
# =============================================================================


class TestGetMessages:
    @pytest.mark.anyio
    async def test_returns_cached_messages(self):
        mgr = _build_manager()
        msg = _make_chat_message()
        mgr._messages[SESSION_ID] = [msg]

        result = await mgr.get_messages(SESSION_ID)
        assert result == [msg]
        # Should NOT call the store since cache was hit
        mgr._store.get_messages.assert_not_called()

    @pytest.mark.anyio
    async def test_read_through_from_sqlite(self):
        store = _mock_store()
        msg_uuid = uuid4()
        store.get_messages.return_value = [
            {
                "message_id": str(msg_uuid),
                "session_id": SESSION_ID,
                "sender_type": "user",
                "content": "from db",
                "action_type": None,
                "action_data": None,
            }
        ]
        mgr = _build_manager(store)

        result = await mgr.get_messages(SESSION_ID)
        assert len(result) == 1
        assert result[0].content == "from db"
        # Cache should now be populated
        assert SESSION_ID in mgr._messages

    @pytest.mark.anyio
    async def test_returns_empty_on_sqlite_error(self):
        store = _mock_store()
        store.get_messages.side_effect = RuntimeError("db error")
        mgr = _build_manager(store)

        result = await mgr.get_messages(SESSION_ID)
        assert result == []


class TestAddMessage:
    @pytest.mark.anyio
    async def test_write_through_persists_then_caches(self):
        store = _mock_store()
        mgr = _build_manager(store)
        msg = _make_chat_message(content="hi there")

        await mgr.add_message(SESSION_ID, msg)

        store.save_message.assert_awaited_once()
        assert SESSION_ID in mgr._messages
        assert mgr._messages[SESSION_ID][-1].content == "hi there"

    @pytest.mark.anyio
    async def test_appends_to_existing_cache(self):
        mgr = _build_manager()
        msg1 = _make_chat_message(content="first")
        msg2 = _make_chat_message(content="second")

        await mgr.add_message(SESSION_ID, msg1)
        await mgr.add_message(SESSION_ID, msg2)

        assert len(mgr._messages[SESSION_ID]) == 2


class TestClearMessages:
    @pytest.mark.anyio
    async def test_clears_cache_and_sqlite(self):
        store = _mock_store()
        mgr = _build_manager(store)
        mgr._messages[SESSION_ID] = [_make_chat_message()]

        await mgr.clear_messages(SESSION_ID)

        store.clear_messages.assert_awaited_once()
        assert SESSION_ID not in mgr._messages


# =============================================================================
# Tests — Proposals
# =============================================================================


class TestProposalRoundTrip:
    @pytest.mark.anyio
    async def test_store_and_get_from_cache(self):
        store = _mock_store()
        mgr = _build_manager(store)
        proposal = _make_proposal()
        pid = str(proposal.proposal_id)

        await mgr.store_proposal(pid, proposal)

        store.save_proposal.assert_awaited_once()
        result = await mgr.get_proposal(pid)
        assert result is proposal
        # get_proposal_by_id should not be called because cache was hit
        store.get_proposal_by_id.assert_not_called()

    @pytest.mark.anyio
    async def test_get_reads_through_from_sqlite(self):
        store = _mock_store()
        proposal = _make_proposal()
        store.get_proposal_by_id.return_value = {
            "proposal_id": str(proposal.proposal_id),
            "session_id": str(proposal.session_id),
            "original_input": proposal.original_input,
            "proposed_title": proposal.proposed_title,
            "proposed_description": proposal.proposed_description,
            "status": "pending",
            "edited_title": None,
            "edited_description": None,
            "file_urls": [],
            "selected_pipeline_id": None,
            "created_at": proposal.created_at.isoformat(),
            "expires_at": proposal.expires_at.isoformat(),
        }
        mgr = _build_manager(store)

        result = await mgr.get_proposal(str(proposal.proposal_id))
        assert result is not None
        assert result.proposed_title == "Fix Login Bug"

    @pytest.mark.anyio
    async def test_get_returns_none_for_missing(self):
        mgr = _build_manager()
        result = await mgr.get_proposal("nonexistent")
        assert result is None


# =============================================================================
# Tests — Recommendations
# =============================================================================


class TestRecommendationRoundTrip:
    @pytest.mark.anyio
    async def test_store_and_get_from_cache(self):
        store = _mock_store()
        mgr = _build_manager(store)
        rec = _make_recommendation()
        rid = str(rec.recommendation_id)

        await mgr.store_recommendation(rid, rec)

        store.save_recommendation.assert_awaited_once()
        result = await mgr.get_recommendation(rid)
        assert result is rec
        store.get_recommendation_by_id.assert_not_called()

    @pytest.mark.anyio
    async def test_get_reads_through_from_sqlite(self):
        store = _mock_store()
        rec = _make_recommendation()
        store.get_recommendation_by_id.return_value = {
            "recommendation_id": str(rec.recommendation_id),
            "session_id": str(rec.session_id),
            "data": rec.model_dump_json(),
            "status": "pending",
            "created_at": rec.created_at.isoformat(),
            "file_urls": [],
        }
        store.recommendation_status_from_db.side_effect = lambda s: s
        mgr = _build_manager(store)

        result = await mgr.get_recommendation(str(rec.recommendation_id))
        assert result is not None
        assert result.title == "Add CSV Export"

    @pytest.mark.anyio
    async def test_get_returns_none_for_missing(self):
        mgr = _build_manager()
        result = await mgr.get_recommendation("nonexistent")
        assert result is None


# =============================================================================
# Tests — Instance isolation
# =============================================================================


class TestInstanceIsolation:
    @pytest.mark.anyio
    async def test_independent_instances_have_separate_state(self):
        mgr_a = _build_manager()
        mgr_b = _build_manager()

        msg = _make_chat_message(content="only in A")
        await mgr_a.add_message(SESSION_ID, msg)

        assert len(mgr_a._messages.get(SESSION_ID, [])) == 1
        assert mgr_b._messages.get(SESSION_ID) is None

    def test_locks_are_not_shared(self):
        mgr_a = _build_manager()
        mgr_b = _build_manager()

        lock_a = mgr_a.get_lock("shared-key")
        lock_b = mgr_b.get_lock("shared-key")
        assert lock_a is not lock_b
