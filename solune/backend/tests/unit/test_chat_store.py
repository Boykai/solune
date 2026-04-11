"""Unit tests for chat_store CRUD operations.

Covers:
- save_message / get_messages / count_messages / clear_messages
- save_proposal / get_proposals / get_proposal_by_id / update_proposal_status
- save_recommendation / get_recommendations / update_recommendation_status
- recommendation_status_from_db / _recommendation_status_to_db mappings
- conversation CRUD: save_conversation / get_conversations / get_conversation_by_id
  / update_conversation / delete_conversation
- message filtering by conversation_id
"""

import pytest

from src.services.chat_store import (
    clear_messages,
    count_messages,
    delete_conversation,
    get_conversation_by_id,
    get_conversations,
    get_messages,
    get_proposal_by_id,
    get_proposals,
    get_recommendation_by_id,
    get_recommendations,
    recommendation_status_from_db,
    save_conversation,
    save_message,
    save_proposal,
    save_recommendation,
    update_conversation,
    update_proposal_status,
    update_recommendation_status,
)

# =============================================================================
# Messages
# =============================================================================


class TestSaveAndGetMessages:
    """Round-trip tests for chat message persistence."""

    @pytest.mark.anyio
    async def test_save_and_retrieve_message(self, mock_db):
        await save_message(mock_db, "sess-1", "msg-1", "user", "Hello")
        msgs = await get_messages(mock_db, "sess-1")

        assert len(msgs) == 1
        assert msgs[0]["content"] == "Hello"
        assert msgs[0]["sender_type"] == "user"

    @pytest.mark.anyio
    async def test_get_messages_returns_empty_for_unknown_session(self, mock_db):
        msgs = await get_messages(mock_db, "nonexistent")
        assert msgs == []

    @pytest.mark.anyio
    async def test_count_messages(self, mock_db):
        await save_message(mock_db, "sess-1", "msg-1", "user", "A")
        await save_message(mock_db, "sess-1", "msg-2", "assistant", "B")

        count = await count_messages(mock_db, "sess-1")
        assert count == 2

    @pytest.mark.anyio
    async def test_clear_messages(self, mock_db):
        await save_message(mock_db, "sess-1", "msg-1", "user", "A")
        await clear_messages(mock_db, "sess-1")

        count = await count_messages(mock_db, "sess-1")
        assert count == 0

    @pytest.mark.anyio
    async def test_get_messages_with_limit(self, mock_db):
        for i in range(5):
            await save_message(mock_db, "sess-1", f"msg-{i}", "user", f"msg {i}")

        msgs = await get_messages(mock_db, "sess-1", limit=2)
        assert len(msgs) == 2


# =============================================================================
# Proposals
# =============================================================================


class TestProposals:
    """Tests for proposal persistence."""

    @pytest.mark.anyio
    async def test_save_and_get_proposal(self, mock_db):
        await save_proposal(
            mock_db,
            session_id="sess-1",
            proposal_id="prop-1",
            original_input="fix the bug",
            proposed_title="Fix bug",
            proposed_description="Fixes the bug",
        )
        proposals = await get_proposals(mock_db, "sess-1")
        assert len(proposals) == 1
        assert proposals[0]["proposed_title"] == "Fix bug"

    @pytest.mark.anyio
    async def test_get_proposal_by_id(self, mock_db):
        await save_proposal(
            mock_db,
            session_id="sess-1",
            proposal_id="prop-1",
            original_input="input",
            proposed_title="Title",
            proposed_description="Desc",
        )
        result = await get_proposal_by_id(mock_db, "prop-1")
        assert result is not None
        assert result["proposal_id"] == "prop-1"

    @pytest.mark.anyio
    async def test_get_proposal_by_id_returns_none_for_missing(self, mock_db):
        result = await get_proposal_by_id(mock_db, "nonexistent")
        assert result is None

    @pytest.mark.anyio
    async def test_update_proposal_status(self, mock_db):
        await save_proposal(
            mock_db,
            session_id="sess-1",
            proposal_id="prop-1",
            original_input="input",
            proposed_title="Title",
            proposed_description="Desc",
        )
        await update_proposal_status(mock_db, "prop-1", "confirmed", edited_title="New Title")

        result = await get_proposal_by_id(mock_db, "prop-1")
        assert result["status"] == "confirmed"
        assert result["edited_title"] == "New Title"


# =============================================================================
# Recommendations
# =============================================================================


class TestRecommendations:
    """Tests for recommendation persistence."""

    @pytest.mark.anyio
    async def test_save_and_get_recommendation(self, mock_db):
        await save_recommendation(
            mock_db,
            session_id="sess-1",
            recommendation_id="rec-1",
            data='{"title":"Fix something"}',
        )
        recs = await get_recommendations(mock_db, "sess-1")
        assert len(recs) == 1
        assert recs[0]["recommendation_id"] == "rec-1"

    @pytest.mark.anyio
    async def test_get_recommendation_by_id(self, mock_db):
        await save_recommendation(
            mock_db,
            session_id="sess-1",
            recommendation_id="rec-1",
            data="{}",
        )
        result = await get_recommendation_by_id(mock_db, "rec-1")
        assert result is not None
        assert result["recommendation_id"] == "rec-1"

    @pytest.mark.anyio
    async def test_update_recommendation_status(self, mock_db):
        await save_recommendation(
            mock_db,
            session_id="sess-1",
            recommendation_id="rec-1",
            data="{}",
        )
        await update_recommendation_status(mock_db, "rec-1", "confirmed")

        result = await get_recommendation_by_id(mock_db, "rec-1")
        # "confirmed" maps to "accepted" in the DB
        assert result["status"] == "accepted"


# =============================================================================
# Status mapping helpers
# =============================================================================


class TestStatusMapping:
    """Tests for recommendation status conversion helpers."""

    def test_recommendation_status_from_db_accepted(self):
        assert recommendation_status_from_db("accepted") == "confirmed"

    def test_recommendation_status_from_db_pending(self):
        assert recommendation_status_from_db("pending") == "pending"

    def test_recommendation_status_from_db_rejected(self):
        assert recommendation_status_from_db("rejected") == "rejected"


# =============================================================================
# Conversations
# =============================================================================


class TestConversationCRUD:
    """Tests for conversation CRUD operations."""

    @pytest.mark.anyio
    async def test_save_and_get_conversation(self, mock_db):
        result = await save_conversation(mock_db, "sess-1", "conv-1", "My Chat")
        assert result["conversation_id"] == "conv-1"
        assert result["session_id"] == "sess-1"
        assert result["title"] == "My Chat"
        assert "created_at" in result
        assert "updated_at" in result

    @pytest.mark.anyio
    async def test_get_conversations_returns_list(self, mock_db):
        await save_conversation(mock_db, "sess-1", "conv-1", "Chat A")
        await save_conversation(mock_db, "sess-1", "conv-2", "Chat B")
        convs = await get_conversations(mock_db, "sess-1")
        assert len(convs) == 2
        titles = {c["title"] for c in convs}
        assert titles == {"Chat A", "Chat B"}

    @pytest.mark.anyio
    async def test_get_conversations_scoped_to_session(self, mock_db):
        await save_conversation(mock_db, "sess-1", "conv-1", "S1 Chat")
        await save_conversation(mock_db, "sess-2", "conv-2", "S2 Chat")
        convs = await get_conversations(mock_db, "sess-1")
        assert len(convs) == 1
        assert convs[0]["title"] == "S1 Chat"

    @pytest.mark.anyio
    async def test_get_conversation_by_id(self, mock_db):
        await save_conversation(mock_db, "sess-1", "conv-1", "Test")
        result = await get_conversation_by_id(mock_db, "conv-1")
        assert result is not None
        assert result["title"] == "Test"

    @pytest.mark.anyio
    async def test_get_conversation_by_id_not_found(self, mock_db):
        result = await get_conversation_by_id(mock_db, "nonexistent")
        assert result is None

    @pytest.mark.anyio
    async def test_update_conversation(self, mock_db):
        await save_conversation(mock_db, "sess-1", "conv-1", "Old Title")
        result = await update_conversation(mock_db, "conv-1", "New Title")
        assert result is not None
        assert result["title"] == "New Title"

    @pytest.mark.anyio
    async def test_update_conversation_not_found(self, mock_db):
        result = await update_conversation(mock_db, "nonexistent", "Title")
        assert result is None

    @pytest.mark.anyio
    async def test_delete_conversation(self, mock_db):
        await save_conversation(mock_db, "sess-1", "conv-1", "To Delete")
        deleted = await delete_conversation(mock_db, "conv-1")
        assert deleted is True
        result = await get_conversation_by_id(mock_db, "conv-1")
        assert result is None

    @pytest.mark.anyio
    async def test_delete_conversation_not_found(self, mock_db):
        deleted = await delete_conversation(mock_db, "nonexistent")
        assert deleted is False


# =============================================================================
# Message filtering by conversation_id
# =============================================================================


class TestMessageConversationFiltering:
    """Tests for message filtering by conversation_id."""

    @pytest.mark.anyio
    async def test_save_message_with_conversation_id(self, mock_db):
        await save_message(
            mock_db, "sess-1", "msg-1", "user", "Hello",
            conversation_id="conv-1",
        )
        msgs = await get_messages(mock_db, "sess-1", conversation_id="conv-1")
        assert len(msgs) == 1
        assert msgs[0]["content"] == "Hello"
        assert msgs[0]["conversation_id"] == "conv-1"

    @pytest.mark.anyio
    async def test_get_messages_filters_by_conversation(self, mock_db):
        await save_message(mock_db, "sess-1", "msg-1", "user", "Conv A", conversation_id="conv-a")
        await save_message(mock_db, "sess-1", "msg-2", "user", "Conv B", conversation_id="conv-b")
        await save_message(mock_db, "sess-1", "msg-3", "user", "No conv")

        msgs_a = await get_messages(mock_db, "sess-1", conversation_id="conv-a")
        assert len(msgs_a) == 1
        assert msgs_a[0]["content"] == "Conv A"

        msgs_b = await get_messages(mock_db, "sess-1", conversation_id="conv-b")
        assert len(msgs_b) == 1
        assert msgs_b[0]["content"] == "Conv B"

    @pytest.mark.anyio
    async def test_get_messages_without_conversation_returns_all(self, mock_db):
        """Backward compatibility: no conversation_id filter returns all messages."""
        await save_message(mock_db, "sess-1", "msg-1", "user", "A", conversation_id="conv-1")
        await save_message(mock_db, "sess-1", "msg-2", "user", "B")

        all_msgs = await get_messages(mock_db, "sess-1")
        assert len(all_msgs) == 2

    @pytest.mark.anyio
    async def test_count_messages_with_conversation(self, mock_db):
        await save_message(mock_db, "sess-1", "msg-1", "user", "A", conversation_id="conv-1")
        await save_message(mock_db, "sess-1", "msg-2", "user", "B", conversation_id="conv-1")
        await save_message(mock_db, "sess-1", "msg-3", "user", "C")

        count_all = await count_messages(mock_db, "sess-1")
        assert count_all == 3

        count_conv = await count_messages(mock_db, "sess-1", conversation_id="conv-1")
        assert count_conv == 2

    @pytest.mark.anyio
    async def test_clear_messages_with_conversation(self, mock_db):
        await save_message(mock_db, "sess-1", "msg-1", "user", "A", conversation_id="conv-1")
        await save_message(mock_db, "sess-1", "msg-2", "user", "B", conversation_id="conv-2")
        await save_message(mock_db, "sess-1", "msg-3", "user", "C")

        await clear_messages(mock_db, "sess-1", conversation_id="conv-1")

        remaining = await get_messages(mock_db, "sess-1")
        assert len(remaining) == 2

    @pytest.mark.anyio
    async def test_backward_compat_messages_without_conversation_id(self, mock_db):
        """Messages saved without conversation_id still work (NULL conversation_id)."""
        await save_message(mock_db, "sess-1", "msg-1", "user", "Legacy message")
        msgs = await get_messages(mock_db, "sess-1")
        assert len(msgs) == 1
        assert msgs[0]["conversation_id"] is None
