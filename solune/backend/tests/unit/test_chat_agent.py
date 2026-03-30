"""Tests for ChatAgentService (src/services/chat_agent.py).

Covers:
- ChatAgentService.run() response conversion
- AgentSessionMapping (session creation, TTL eviction, max sessions)
- ChatAgentService.run_stream() async iterator
- Provider factory integration (mocked)
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.chat import ActionType, ChatMessage, SenderType
from src.services.chat_agent import AgentSessionMapping, ChatAgentService

# ── AgentSessionMapping tests ───────────────────────────────────────────


class TestAgentSessionMapping:
    async def test_creates_session_on_first_access(self):
        mapping = AgentSessionMapping(ttl_seconds=3600, max_sessions=10)
        session = await mapping.get_or_create("session-1")
        assert session is not None
        assert mapping.session_count == 1

    async def test_returns_same_session_on_repeat_access(self):
        mapping = AgentSessionMapping(ttl_seconds=3600, max_sessions=10)
        s1 = await mapping.get_or_create("session-1")
        s2 = await mapping.get_or_create("session-1")
        assert s1 is s2
        assert mapping.session_count == 1

    async def test_creates_separate_sessions_for_different_ids(self):
        mapping = AgentSessionMapping(ttl_seconds=3600, max_sessions=10)
        await mapping.get_or_create("session-1")
        await mapping.get_or_create("session-2")
        assert mapping.session_count == 2

    async def test_evicts_expired_sessions(self):
        mapping = AgentSessionMapping(ttl_seconds=0, max_sessions=10)
        await mapping.get_or_create("session-1")
        # TTL=0 means everything expires immediately
        # Force some time to pass
        await asyncio.sleep(0.01)
        # Creating a new session should trigger eviction
        await mapping.get_or_create("session-2")
        # session-1 should be evicted (expired)
        assert mapping.session_count == 1

    async def test_evicts_oldest_when_at_capacity(self):
        mapping = AgentSessionMapping(ttl_seconds=3600, max_sessions=2)
        await mapping.get_or_create("session-1")
        await mapping.get_or_create("session-2")
        assert mapping.session_count == 2
        # Adding a third should evict the oldest
        await mapping.get_or_create("session-3")
        assert mapping.session_count == 2

    async def test_touch_updates_last_accessed(self):
        mapping = AgentSessionMapping(ttl_seconds=3600, max_sessions=10)
        await mapping.get_or_create("session-1")
        entry = mapping._sessions["session-1"]
        old_time = entry.last_accessed
        await asyncio.sleep(0.01)
        await mapping.get_or_create("session-1")
        assert entry.last_accessed > old_time


# ── ChatAgentService.run() tests ────────────────────────────────────────


class TestChatAgentServiceRun:
    @patch("src.services.chat_agent.create_agent")
    async def test_run_returns_chat_message(self, mock_create_agent):
        """Verify run() returns a ChatMessage from the agent response."""
        # Set up mock agent
        mock_agent = AsyncMock()
        mock_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "I'll help you with that."
        mock_msg.annotations = None
        mock_response.messages = [mock_msg]
        mock_agent.run.return_value = mock_response
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        session_id = uuid4()

        result = await service.run(
            message="Create a task to fix the login bug",
            session_id=session_id,
            github_token="test-token",
            project_name="Test Project",
        )

        assert isinstance(result, ChatMessage)
        assert result.session_id == session_id
        assert result.sender_type == SenderType.ASSISTANT
        assert "help" in result.content.lower()

    @patch("src.services.chat_agent.create_agent")
    async def test_run_handles_agent_error(self, mock_create_agent):
        """Verify run() returns error ChatMessage when agent fails."""
        mock_agent = AsyncMock()
        mock_agent.run.side_effect = RuntimeError("Agent down")
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        session_id = uuid4()

        result = await service.run(
            message="test",
            session_id=session_id,
            github_token="test-token",
        )

        assert isinstance(result, ChatMessage)
        assert "error" in result.content.lower()

    @patch("src.services.chat_agent.create_agent")
    async def test_run_extracts_tool_result_from_json(self, mock_create_agent):
        """When agent returns a JSON tool result, extract action_type and action_data."""

        mock_agent = AsyncMock()
        mock_response = MagicMock()
        mock_msg = MagicMock()
        # Simulate a tool result returned as JSON in message content
        mock_msg.content = json.dumps(
            {
                "content": "Task proposal created",
                "action_type": "task_create",
                "action_data": {"proposed_title": "Fix bug", "proposed_description": "desc"},
            }
        )
        mock_msg.annotations = None
        mock_response.messages = [mock_msg]
        mock_agent.run.return_value = mock_response
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        result = await service.run(
            message="fix the bug",
            session_id=uuid4(),
            github_token="test-token",
        )

        assert result.action_type == ActionType.TASK_CREATE
        assert result.action_data["proposed_title"] == "Fix bug"

    @patch("src.services.chat_agent.create_agent")
    async def test_run_passes_context_via_session_state(self, mock_create_agent):
        """Verify runtime context is injected into AgentSession.state."""
        mock_agent = AsyncMock()
        mock_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "OK"
        mock_msg.annotations = None
        mock_response.messages = [mock_msg]
        mock_agent.run.return_value = mock_response
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        await service.run(
            message="test",
            session_id=uuid4(),
            github_token="test-token",
            project_name="My Project",
            project_id="PVT_1",
            available_statuses=["Todo", "Done"],
        )

        # Verify the agent was called with a session containing state
        call_kwargs = mock_agent.run.call_args.kwargs
        session = call_kwargs["session"]
        assert session.state["project_name"] == "My Project"
        assert session.state["project_id"] == "PVT_1"
        assert "Todo" in session.state["available_statuses"]


# ── ChatAgentService.run_stream() tests ─────────────────────────────────


class TestChatAgentServiceRunStream:
    @patch("src.services.chat_agent.create_agent")
    async def test_stream_yields_events(self, mock_create_agent):
        """Verify run_stream() yields SSE-compatible events."""
        mock_agent = AsyncMock()

        # Create an async iterator for streaming
        async def mock_stream(*args, **kwargs):
            update1 = MagicMock(spec=["text"])
            update1.text = "Hello "
            yield update1
            update2 = MagicMock(spec=["text"])
            update2.text = "World"
            yield update2

        mock_agent.run = MagicMock(return_value=mock_stream())
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        events = [
            event
            async for event in service.run_stream(
                message="test",
                session_id=uuid4(),
                github_token="test-token",
            )
        ]

        # Should have token events + done event
        token_events = [e for e in events if e["event"] == "token"]
        done_events = [e for e in events if e["event"] == "done"]
        assert len(token_events) == 2
        assert len(done_events) == 1

    @patch("src.services.chat_agent.create_agent")
    async def test_stream_done_event_contains_accumulated_text(self, mock_create_agent):
        """Verify the done event's ChatMessage contains all accumulated text."""

        mock_agent = AsyncMock()

        async def mock_stream(*args, **kwargs):
            update1 = MagicMock(spec=["text"])
            update1.text = "Hello "
            yield update1
            update2 = MagicMock(spec=["text"])
            update2.text = "World"
            yield update2

        mock_agent.run = MagicMock(return_value=mock_stream())
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        events = [
            event
            async for event in service.run_stream(
                message="test",
                session_id=uuid4(),
                github_token="test-token",
            )
        ]

        done_event = next(e for e in events if e["event"] == "done")
        done_data = json.loads(done_event["data"])
        assert done_data["content"] == "Hello World"

    @patch("src.services.chat_agent.create_agent")
    async def test_stream_extracts_tool_result(self, mock_create_agent):
        """Verify run_stream() extracts action_type/action_data from tool_result updates."""

        mock_agent = AsyncMock()

        async def mock_stream(*args, **kwargs):
            # Text update
            text_update = MagicMock(spec=["text"])
            text_update.text = "Task proposal created"
            yield text_update
            # Tool result update
            tool_update = MagicMock(spec=["text", "tool_result"])
            tool_update.text = None
            tool_update.tool_result = {
                "action_type": "task_create",
                "action_data": {"proposed_title": "Fix bug"},
            }
            yield tool_update

        mock_agent.run = MagicMock(return_value=mock_stream())
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        events = [
            event
            async for event in service.run_stream(
                message="fix the bug",
                session_id=uuid4(),
                github_token="test-token",
            )
        ]

        # Should have tool_result event
        tool_events = [e for e in events if e["event"] == "tool_result"]
        assert len(tool_events) == 1
        tool_data = json.loads(tool_events[0]["data"])
        assert tool_data["action_type"] == "task_create"

        # Done event should include action_type
        done_event = next(e for e in events if e["event"] == "done")
        done_data = json.loads(done_event["data"])
        assert done_data["action_type"] == "task_create"
        assert done_data["action_data"]["proposed_title"] == "Fix bug"

    @patch("src.services.chat_agent.create_agent")
    async def test_stream_extracts_action_from_json_text(self, mock_create_agent):
        """Verify run_stream() falls back to JSON extraction from accumulated text."""

        mock_agent = AsyncMock()
        tool_json = json.dumps(
            {
                "content": "Task proposal created",
                "action_type": "task_create",
                "action_data": {"proposed_title": "Fix bug"},
            }
        )

        async def mock_stream(*args, **kwargs):
            update = MagicMock(spec=["text"])
            update.text = tool_json
            yield update

        mock_agent.run = MagicMock(return_value=mock_stream())
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        events = [
            event
            async for event in service.run_stream(
                message="fix the bug",
                session_id=uuid4(),
                github_token="test-token",
            )
        ]

        done_event = next(e for e in events if e["event"] == "done")
        done_data = json.loads(done_event["data"])
        assert done_data["action_type"] == "task_create"
        assert done_data["action_data"]["proposed_title"] == "Fix bug"
        assert done_data["content"] == "Task proposal created"

    @patch("src.services.chat_agent.create_agent")
    async def test_stream_yields_error_on_failure(self, mock_create_agent):
        """Verify run_stream() yields error event on agent failure."""
        mock_agent = AsyncMock()

        async def failing_stream(*args, **kwargs):
            raise RuntimeError("Stream failed")
            yield  # pragma: no cover — makes this function an async generator

        mock_agent.run = MagicMock(return_value=failing_stream())
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        events = [
            event
            async for event in service.run_stream(
                message="test",
                session_id=uuid4(),
                github_token="test-token",
            )
        ]

        error_events = [e for e in events if e["event"] == "error"]
        assert len(error_events) == 1


# ── Provider factory tests ──────────────────────────────────────────────


class TestProviderFactory:
    @patch("src.services.agent_provider.get_settings")
    async def test_copilot_provider_requires_token(self, mock_settings):
        from src.services.agent_provider import create_agent

        mock_settings.return_value = MagicMock(ai_provider="copilot", copilot_model="gpt-4o")
        with pytest.raises(ValueError, match="GitHub OAuth token required"):
            create_agent(instructions="test", github_token=None)

    @patch("src.services.agent_provider.get_settings")
    async def test_azure_provider_requires_credentials(self, mock_settings):
        from src.services.agent_provider import create_agent

        mock_settings.return_value = MagicMock(
            ai_provider="azure_openai",
            azure_openai_endpoint=None,
            azure_openai_key=None,
        )
        with pytest.raises(ValueError, match="Azure OpenAI credentials"):
            create_agent(instructions="test")

    @patch("src.services.agent_provider.get_settings")
    async def test_unknown_provider_raises(self, mock_settings):
        from src.services.agent_provider import create_agent

        mock_settings.return_value = MagicMock(ai_provider="unknown_provider")
        with pytest.raises(ValueError, match="Unknown AI_PROVIDER"):
            create_agent(instructions="test")
