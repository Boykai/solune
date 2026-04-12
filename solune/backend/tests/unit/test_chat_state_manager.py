"""Unit tests for ChatStateManager.

Covers:
- Instantiation with mocked deps
- get_lock() returns same lock for same key
- get_messages() read-through cache (cache hit + SQLite fallback)
- add_message() write-through
- store_proposal() / get_proposal() round-trip
- store_recommendation() / get_recommendation() round-trip
- clear_messages()
- Multiple instances have separate state
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.chat_state_manager import ChatStateManager


@pytest.fixture
def mock_chat_store():
    """Mock chat_store module with async persistence methods."""
    store = MagicMock()
    store.save_message = AsyncMock()
    store.get_messages = AsyncMock(return_value=[])
    store.clear_messages = AsyncMock()
    store.save_proposal = AsyncMock()
    store.get_proposal_by_id = AsyncMock(return_value=None)
    store.save_recommendation = AsyncMock()
    store.get_recommendation_by_id = AsyncMock(return_value=None)
    store.recommendation_status_from_db = MagicMock(return_value="pending")
    return store


@pytest.fixture
def mock_state_db():
    """Mock aiosqlite connection."""
    return AsyncMock()


@pytest.fixture
def manager(mock_state_db, mock_chat_store):
    """A ChatStateManager wired to mocked deps."""
    return ChatStateManager(mock_state_db, mock_chat_store, max_retries=3, base_delay=0.001)


class TestInstantiation:
    def test_creates_empty_state(self, manager):
        """Fresh manager should have empty internal dicts."""
        assert manager._messages == {}
        assert manager._proposals == {}
        assert manager._recommendations == {}
        assert manager._locks == {}

    def test_stores_db_and_chat_store(self, mock_state_db, mock_chat_store):
        mgr = ChatStateManager(mock_state_db, mock_chat_store)
        assert mgr._db is mock_state_db
        assert mgr._chat_store is mock_chat_store

    def test_default_retry_params(self, mock_state_db, mock_chat_store):
        mgr = ChatStateManager(mock_state_db, mock_chat_store)
        assert mgr._max_retries == 3
        assert mgr._base_delay == 0.1

    def test_custom_retry_params(self, mock_state_db, mock_chat_store):
        mgr = ChatStateManager(mock_state_db, mock_chat_store, max_retries=5, base_delay=0.5)
        assert mgr._max_retries == 5
        assert mgr._base_delay == 0.5


class TestGetLock:
    def test_returns_lock(self, manager):
        lock = manager.get_lock("key1")
        assert isinstance(lock, asyncio.Lock)

    def test_same_key_returns_same_lock(self, manager):
        lock1 = manager.get_lock("key1")
        lock2 = manager.get_lock("key1")
        assert lock1 is lock2

    def test_different_keys_return_different_locks(self, manager):
        lock1 = manager.get_lock("key1")
        lock2 = manager.get_lock("key2")
        assert lock1 is not lock2


class TestGetMessages:
    async def test_cache_hit(self, manager):
        """When messages are in memory, SQLite should not be queried."""
        expected = [{"content": "hello"}]
        manager._messages["sid1"] = expected

        result = await manager.get_messages("sid1")

        assert result is expected
        manager._chat_store.get_messages.assert_not_awaited()

    async def test_sqlite_fallback(self, manager, mock_chat_store):
        """On cache miss, messages should be loaded from SQLite and cached."""
        db_rows = [{"content": "from db"}]
        mock_chat_store.get_messages.return_value = db_rows

        result = await manager.get_messages("sid2")

        assert result == db_rows
        mock_chat_store.get_messages.assert_awaited_once_with(manager._db, "sid2")
        # Verify cache was populated
        assert manager._messages["sid2"] is db_rows

    async def test_sqlite_error_returns_empty(self, manager, mock_chat_store):
        """If SQLite fails, return empty list and don't crash."""
        mock_chat_store.get_messages.side_effect = RuntimeError("DB locked")

        result = await manager.get_messages("sid_err")

        assert result == []
        assert "sid_err" not in manager._messages


class TestAddMessage:
    async def test_write_through(self, manager, mock_chat_store):
        """add_message should persist to SQLite first, then update cache."""
        msg = MagicMock()
        msg.message_id = "msg1"
        msg.sender_type = "user"
        msg.content = "hello"
        msg.action_type = None
        msg.action_data = None

        await manager.add_message("sid1", msg)

        mock_chat_store.save_message.assert_awaited_once()
        assert manager._messages["sid1"] == [msg]

    async def test_appends_to_existing(self, manager, mock_chat_store):
        """Messages should accumulate in the cache."""
        msg1 = MagicMock(
            message_id="m1", sender_type="user", content="a", action_type=None, action_data=None
        )
        msg2 = MagicMock(
            message_id="m2",
            sender_type="assistant",
            content="b",
            action_type=None,
            action_data=None,
        )

        await manager.add_message("sid1", msg1)
        await manager.add_message("sid1", msg2)

        assert manager._messages["sid1"] == [msg1, msg2]


class TestClearMessages:
    async def test_clears_cache_and_sqlite(self, manager, mock_chat_store):
        """clear_messages should remove from memory and call SQLite delete."""
        manager._messages["sid1"] = [{"content": "old"}]

        await manager.clear_messages("sid1")

        assert "sid1" not in manager._messages
        mock_chat_store.clear_messages.assert_awaited_once_with(manager._db, "sid1")

    async def test_sqlite_failure_still_clears_cache(self, manager, mock_chat_store):
        """Cache should be cleared even if SQLite fails."""
        manager._messages["sid1"] = [{"content": "old"}]
        mock_chat_store.clear_messages.side_effect = RuntimeError("DB error")

        await manager.clear_messages("sid1")

        assert "sid1" not in manager._messages


class TestProposalRoundTrip:
    async def test_store_and_get(self, manager, mock_chat_store):
        """store_proposal then get_proposal should return the same object."""
        proposal = {"title": "Do stuff", "id": "p1"}

        await manager.store_proposal("p1", proposal)

        mock_chat_store.save_proposal.assert_awaited_once()
        result = await manager.get_proposal("p1")
        assert result is proposal
        # Should not have hit SQLite on the get (cache hit)
        mock_chat_store.get_proposal_by_id.assert_not_awaited()

    async def test_get_from_sqlite(self, manager, mock_chat_store):
        """Cache miss should load from SQLite and cache it."""
        db_row = {"proposal_id": "p2", "title": "From DB"}
        mock_chat_store.get_proposal_by_id.return_value = db_row

        result = await manager.get_proposal("p2")

        assert result == db_row
        mock_chat_store.get_proposal_by_id.assert_awaited_once()
        assert manager._proposals["p2"] is db_row

    async def test_get_returns_none_when_not_found(self, manager, mock_chat_store):
        """Should return None when proposal doesn't exist anywhere."""
        mock_chat_store.get_proposal_by_id.return_value = None

        result = await manager.get_proposal("nonexistent")

        assert result is None

    async def test_get_sqlite_error_returns_none(self, manager, mock_chat_store):
        """SQLite errors should return None, not crash."""
        mock_chat_store.get_proposal_by_id.side_effect = RuntimeError("DB error")

        result = await manager.get_proposal("p_err")

        assert result is None


class TestRecommendationRoundTrip:
    async def test_store_and_get(self, manager, mock_chat_store):
        """store_recommendation then get_recommendation should return same object."""
        rec = {"title": "Fix bug", "id": "r1"}

        await manager.store_recommendation("r1", rec)

        mock_chat_store.save_recommendation.assert_awaited_once()
        result = await manager.get_recommendation("r1")
        assert result is rec
        mock_chat_store.get_recommendation_by_id.assert_not_awaited()

    async def test_get_from_sqlite(self, manager, mock_chat_store):
        """Cache miss should load from SQLite."""
        db_row = {"recommendation_id": "r2", "title": "From DB"}
        mock_chat_store.get_recommendation_by_id.return_value = db_row

        result = await manager.get_recommendation("r2")

        assert result == db_row
        mock_chat_store.get_recommendation_by_id.assert_awaited_once()
        assert manager._recommendations["r2"] is db_row

    async def test_get_returns_none_when_not_found(self, manager, mock_chat_store):
        mock_chat_store.get_recommendation_by_id.return_value = None

        result = await manager.get_recommendation("nonexistent")

        assert result is None

    async def test_get_sqlite_error_returns_none(self, manager, mock_chat_store):
        mock_chat_store.get_recommendation_by_id.side_effect = RuntimeError("DB error")

        result = await manager.get_recommendation("r_err")

        assert result is None


class TestSeparateInstances:
    def test_instances_have_independent_state(self, mock_state_db, mock_chat_store):
        """Two ChatStateManager instances should not share mutable state."""
        mgr1 = ChatStateManager(mock_state_db, mock_chat_store)
        mgr2 = ChatStateManager(mock_state_db, mock_chat_store)

        mgr1._messages["key"] = ["msg"]
        mgr1._proposals["p1"] = {"title": "A"}
        mgr1._recommendations["r1"] = {"title": "B"}
        mgr1.get_lock("k1")

        assert "key" not in mgr2._messages
        assert "p1" not in mgr2._proposals
        assert "r1" not in mgr2._recommendations
        assert "k1" not in mgr2._locks
