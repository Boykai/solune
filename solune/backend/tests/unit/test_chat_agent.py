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
from src.services.agent_tools import embed_action_payload
from src.services.chat_agent import (
    PLAN_CREATE_DRAFT_MESSAGE,
    AgentSessionMapping,
    ChatAgentService,
)

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
        assert mock_create_agent.call_args.kwargs["tool_runtime_state"] is session.state

    @patch("src.services.chat_agent.create_agent")
    async def test_run_converts_pipeline_launch_action(self, mock_create_agent):
        """Verify _convert_response() correctly maps pipeline_launch action_type."""
        mock_agent = AsyncMock()
        mock_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = json.dumps(
            {
                "content": "Pipeline launched",
                "action_type": "pipeline_launch",
                "action_data": {
                    "pipeline_id": "pipe-1",
                    "preset": "default",
                    "stages": ["In progress"],
                },
            }
        )
        mock_msg.annotations = None
        mock_response.messages = [mock_msg]
        mock_agent.run.return_value = mock_response
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        result = await service.run(
            message="launch the pipeline",
            session_id=uuid4(),
            github_token="test-token",
        )

        assert result.action_type == ActionType.PIPELINE_LAUNCH
        assert result.action_data["pipeline_id"] == "pipe-1"
        assert result.action_data["preset"] == "default"
        assert result.action_data["stages"] == ["In progress"]

    @patch("src.services.chat_agent.create_agent")
    async def test_run_extracts_action_from_function_result_content(self, mock_create_agent):
        """Verify _convert_response() extracts action_type from function_result Content items."""
        mock_agent = AsyncMock()
        mock_response = MagicMock()

        # Simulate an assistant message with text (LLM summarisation)
        assistant_msg = MagicMock()
        assistant_msg.text = "I've created a task proposal."
        assistant_msg.content = None
        assistant_msg.contents = None
        assistant_msg.tool_result = None
        assistant_msg.additional_properties = None
        assistant_msg.annotations = None

        # Simulate the tool-role message containing a function_result Content item.
        # The Agent Framework stores the tool return value in Content.result as
        # a JSON string inside a message with role="tool".
        tool_msg = MagicMock()
        tool_msg.text = None
        tool_msg.content = None
        tool_msg.tool_result = None
        tool_msg.additional_properties = None
        tool_msg.annotations = None

        fn_result_content = MagicMock()
        fn_result_content.type = "function_result"
        fn_result_content.result = json.dumps(
            {
                "content": "Task proposal created",
                "action_type": "task_create",
                "action_data": {
                    "proposed_title": "Add login tests",
                    "proposed_description": "Cover edge cases",
                },
            }
        )
        tool_msg.contents = [fn_result_content]

        mock_response.messages = [tool_msg, assistant_msg]
        mock_agent.run.return_value = mock_response
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        result = await service.run(
            message="Add unit tests for login",
            session_id=uuid4(),
            github_token="test-token",
        )

        assert result.action_type == ActionType.TASK_CREATE
        assert result.action_data["proposed_title"] == "Add login tests"
        assert result.action_data["proposed_description"] == "Cover edge cases"

    @patch("src.services.chat_agent.create_agent")
    async def test_run_plan_create_uses_safe_draft_copy(self, mock_create_agent):
        """Plan drafts should not persist raw model claims about created GitHub work."""
        mock_agent = AsyncMock()
        mock_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = json.dumps(
            {
                "content": "Done! Created the parent issue and launched the pipeline.",
                "action_type": "plan_create",
                "action_data": {"plan_id": "plan-1", "status": "draft"},
            }
        )
        mock_msg.annotations = None
        mock_response.messages = [mock_msg]
        mock_agent.run.return_value = mock_response
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        result = await service.run_plan(
            message="plan a fix",
            session_id=uuid4(),
            github_token="test-token",
            project_name="Roadmap",
            project_id="PVT_1",
            repo_owner="octocat",
            repo_name="hello-world",
        )

        assert result.action_type == ActionType.PLAN_CREATE
        assert result.content == PLAN_CREATE_DRAFT_MESSAGE

    @patch("src.services.chat_agent.create_agent")
    async def test_run_plan_preserves_selected_pipeline_across_refinements(self, mock_create_agent):
        mock_agent = AsyncMock()
        mock_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = json.dumps(
            {
                "content": "Plan drafted.",
                "action_type": "plan_create",
                "action_data": {"plan_id": "plan-1", "status": "draft"},
            }
        )
        mock_msg.annotations = None
        mock_response.messages = [mock_msg]
        mock_agent.run.return_value = mock_response
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        session_id = uuid4()

        await service.run_plan(
            message="plan a fix",
            session_id=session_id,
            github_token="test-token",
            project_name="Roadmap",
            project_id="PVT_1",
            repo_owner="octocat",
            repo_name="hello-world",
            selected_pipeline_id="pipeline-123",
        )

        await service.run_plan(
            message="tighten the rollout",
            session_id=session_id,
            github_token="test-token",
            project_name="Roadmap",
            project_id="PVT_1",
            repo_owner="octocat",
            repo_name="hello-world",
        )

        session = await service._session_mapping.get_or_create(str(session_id))
        assert session.state["selected_pipeline_id"] == "pipeline-123"

    @patch("src.services.chat_agent.create_agent")
    async def test_run_plan_passes_runtime_state_to_agent_factory(self, mock_create_agent):
        mock_agent = AsyncMock()
        mock_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "Plan drafted."
        mock_msg.annotations = None
        mock_response.messages = [mock_msg]
        mock_agent.run.return_value = mock_response
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        session_id = uuid4()

        await service.run_plan(
            message="plan a fix",
            session_id=session_id,
            github_token="test-token",
            project_name="Roadmap",
            project_id="PVT_1",
            repo_owner="octocat",
            repo_name="hello-world",
            selected_pipeline_id="pipeline-123",
            db=object(),
        )

        runtime_state = mock_create_agent.call_args.kwargs["tool_runtime_state"]
        assert runtime_state["session_id"] == str(session_id)
        assert runtime_state["project_id"] == "PVT_1"
        assert runtime_state["repo_owner"] == "octocat"
        assert runtime_state["repo_name"] == "hello-world"
        assert runtime_state["selected_pipeline_id"] == "pipeline-123"

    @patch("src.services.chat_agent.load_mcp_tools", new_callable=AsyncMock)
    @patch("src.services.chat_agent.create_agent")
    async def test_run_loads_mcp_servers_for_project_context(
        self, mock_create_agent, mock_load_mcp_tools
    ):
        """Verify run() loads MCP configs and passes them to the agent factory."""
        mock_agent = AsyncMock()
        mock_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "OK"
        mock_msg.annotations = None
        mock_response.messages = [mock_msg]
        mock_agent.run.return_value = mock_response
        mock_create_agent.return_value = mock_agent
        mock_load_mcp_tools.return_value = {
            "docs": {"endpoint_url": "https://example.com/mcp", "config": {}}
        }

        service = ChatAgentService()
        fake_db = object()

        await service.run(
            message="test",
            session_id=uuid4(),
            github_token="test-token",
            project_id="PVT_1",
            db=fake_db,
        )

        mock_load_mcp_tools.assert_awaited_once_with("PVT_1", fake_db)
        assert mock_create_agent.call_args.kwargs["mcp_servers"] == mock_load_mcp_tools.return_value


# ── ChatAgentService.run_stream() tests ─────────────────────────────────


class TestChatAgentServiceRunStream:
    @patch("src.services.chat_agent.load_mcp_tools", new_callable=AsyncMock)
    @patch("src.services.chat_agent.create_agent")
    async def test_stream_yields_events(self, mock_create_agent, mock_load_mcp_tools):
        """Verify run_stream() yields SSE-compatible events."""
        mock_agent = AsyncMock()
        mock_load_mcp_tools.return_value = {}

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

    @patch("src.services.chat_agent.load_mcp_tools", new_callable=AsyncMock)
    @patch("src.services.chat_agent.create_agent")
    async def test_stream_loads_mcp_servers_for_project_context(
        self, mock_create_agent, mock_load_mcp_tools
    ):
        """Verify run_stream() loads MCP configs and passes them to the agent factory."""
        mock_agent = AsyncMock()
        mock_load_mcp_tools.return_value = {
            "docs": {"endpoint_url": "https://example.com/mcp", "config": {}}
        }

        async def mock_stream(*args, **kwargs):
            update = MagicMock(spec=["text"])
            update.text = "Hello"
            yield update

        mock_agent.run = MagicMock(return_value=mock_stream())
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        fake_db = object()
        events = [
            event
            async for event in service.run_stream(
                message="test",
                session_id=uuid4(),
                github_token="test-token",
                project_id="PVT_1",
                db=fake_db,
            )
        ]

        assert next(e for e in events if e["event"] == "done")
        mock_load_mcp_tools.assert_awaited_once_with("PVT_1", fake_db)
        assert mock_create_agent.call_args.kwargs["mcp_servers"] == mock_load_mcp_tools.return_value

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
            yield  # pragma: no cover — reason: unreachable yield makes function an async generator; required for type signature

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


class TestChatAgentServiceRunPlanStream:
    @patch("src.services.chat_agent.on_post_tool_use_hook", new_callable=AsyncMock)
    @patch("src.services.chat_agent.on_pre_tool_use_hook", new_callable=AsyncMock)
    @patch("src.services.chat_agent._recover_saved_plan_action", new_callable=AsyncMock)
    @patch("src.services.chat_agent.create_agent")
    async def test_plan_stream_normalizes_plan_create_done_copy(
        self,
        mock_create_agent,
        mock_recover_saved_plan_action,
        mock_pre_tool_use_hook,
        mock_post_tool_use_hook,
    ):
        """Streaming plan drafts should emit safe final copy even if token text is misleading."""
        mock_agent = AsyncMock()
        mock_pre_tool_use_hook.return_value = None
        mock_post_tool_use_hook.return_value = None
        mock_recover_saved_plan_action.return_value = (None, None)

        async def mock_stream(*args, **kwargs):
            text_update = MagicMock(spec=["text"])
            text_update.text = "Done! Parent issue created."
            yield text_update

            tool_update = MagicMock(spec=["text", "tool_result"])
            tool_update.text = None
            tool_update.tool_result = {
                "action_type": "plan_create",
                "action_data": {"plan_id": "plan-1", "status": "draft"},
            }
            yield tool_update

        mock_agent.run = MagicMock(return_value=mock_stream())
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        events = [
            event
            async for event in service.run_plan_stream(
                message="plan a fix",
                session_id=uuid4(),
                github_token="test-token",
                project_name="Roadmap",
                project_id="PVT_1",
                repo_owner="octocat",
                repo_name="hello-world",
            )
        ]

        done_event = next(e for e in events if e["event"] == "done")
        done_data = json.loads(done_event["data"])
        assert done_data["action_type"] == "plan_create"
        assert done_data["content"] == PLAN_CREATE_DRAFT_MESSAGE

    @patch("src.services.chat_agent.on_post_tool_use_hook", new_callable=AsyncMock)
    @patch("src.services.chat_agent.on_pre_tool_use_hook", new_callable=AsyncMock)
    @patch("src.services.chat_agent._recover_saved_plan_action", new_callable=AsyncMock)
    @patch("src.services.chat_agent.create_agent")
    async def test_plan_stream_extracts_embedded_payload_from_function_result(
        self,
        mock_create_agent,
        mock_recover_saved_plan_action,
        mock_pre_tool_use_hook,
        mock_post_tool_use_hook,
    ):
        """Plan streams should recover embedded action payloads from Copilot-flattened tool results."""
        mock_agent = AsyncMock()
        mock_pre_tool_use_hook.return_value = None
        mock_post_tool_use_hook.return_value = None
        mock_recover_saved_plan_action.return_value = (None, None)

        async def mock_stream(*args, **kwargs):
            text_update = MagicMock(spec=["text"])
            text_update.text = "The save_plan tool failed due to missing session context."
            yield text_update

            tool_update = MagicMock()
            tool_update.text = None
            tool_update.content = None
            tool_update.tool_result = None
            tool_update.additional_properties = None
            tool_update.annotations = None

            fn_result_content = MagicMock()
            fn_result_content.type = "function_result"
            fn_result_content.result = embed_action_payload(
                "Plan saved: **Parity test** with 2 steps.",
                "plan_create",
                {
                    "plan_id": "plan-1",
                    "status": "draft",
                    "steps": [],
                },
            )
            tool_update.contents = [fn_result_content]
            yield tool_update

        mock_agent.run = MagicMock(return_value=mock_stream())
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        events = [
            event
            async for event in service.run_plan_stream(
                message="plan a fix",
                session_id=uuid4(),
                github_token="test-token",
                project_name="Roadmap",
                project_id="PVT_1",
                repo_owner="octocat",
                repo_name="hello-world",
            )
        ]

        tool_event = next(e for e in events if e["event"] == "tool_result")
        tool_data = json.loads(tool_event["data"])
        assert tool_data["action_type"] == "plan_create"
        assert tool_data["action_data"]["plan_id"] == "plan-1"

        done_event = next(e for e in events if e["event"] == "done")
        done_data = json.loads(done_event["data"])
        assert done_data["action_type"] == "plan_create"
        assert done_data["content"] == PLAN_CREATE_DRAFT_MESSAGE
        assert done_data["action_data"]["plan_id"] == "plan-1"

    @patch("src.services.chat_agent.on_post_tool_use_hook", new_callable=AsyncMock)
    @patch("src.services.chat_agent.on_pre_tool_use_hook", new_callable=AsyncMock)
    @patch("src.services.chat_agent._recover_saved_plan_action", new_callable=AsyncMock)
    @patch("src.services.chat_agent.create_agent")
    async def test_plan_stream_uses_final_response_when_updates_omit_tool_payload(
        self,
        mock_create_agent,
        mock_recover_saved_plan_action,
        mock_pre_tool_use_hook,
        mock_post_tool_use_hook,
    ):
        """Plan streams should recover actions from get_final_response() when only text deltas were streamed."""
        mock_agent = AsyncMock()
        mock_pre_tool_use_hook.return_value = None
        mock_post_tool_use_hook.return_value = None
        mock_recover_saved_plan_action.return_value = (None, None)

        text_update = MagicMock(spec=["text"])
        text_update.text = "save_plan reported a session error."

        tool_msg = MagicMock()
        tool_msg.text = None
        tool_msg.content = None
        tool_msg.tool_result = None
        tool_msg.additional_properties = None
        tool_msg.annotations = None

        fn_result_content = MagicMock()
        fn_result_content.type = "function_result"
        fn_result_content.result = embed_action_payload(
            "Plan saved: **Parity test** with 2 steps.",
            "plan_create",
            {
                "plan_id": "plan-final",
                "status": "draft",
                "steps": [],
            },
        )
        tool_msg.contents = [fn_result_content]

        assistant_msg = MagicMock()
        assistant_msg.text = "Here is the structured smoke-test plan."
        assistant_msg.content = None
        assistant_msg.contents = None
        assistant_msg.tool_result = None
        assistant_msg.additional_properties = None
        assistant_msg.annotations = None

        final_response = MagicMock()
        final_response.text = assistant_msg.text
        final_response.messages = [tool_msg, assistant_msg]

        class MockStream:
            def __init__(self, updates, response):
                self._updates = iter(updates)
                self.get_final_response = AsyncMock(return_value=response)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    return next(self._updates)
                except StopIteration as exc:
                    raise StopAsyncIteration from exc

        stream = MockStream([text_update], final_response)
        mock_agent.run = MagicMock(return_value=stream)
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        events = [
            event
            async for event in service.run_plan_stream(
                message="plan a fix",
                session_id=uuid4(),
                github_token="test-token",
                project_name="Roadmap",
                project_id="PVT_1",
                repo_owner="octocat",
                repo_name="hello-world",
            )
        ]

        done_event = next(e for e in events if e["event"] == "done")
        done_data = json.loads(done_event["data"])
        assert done_data["action_type"] == "plan_create"
        assert done_data["content"] == PLAN_CREATE_DRAFT_MESSAGE
        assert done_data["action_data"]["plan_id"] == "plan-final"

    @patch("src.services.chat_agent.on_post_tool_use_hook", new_callable=AsyncMock)
    @patch("src.services.chat_agent.on_pre_tool_use_hook", new_callable=AsyncMock)
    @patch("src.services.chat_agent._recover_saved_plan_action", new_callable=AsyncMock)
    @patch("src.services.chat_agent.create_agent")
    async def test_plan_stream_uses_session_tool_action_when_transport_drops_metadata(
        self,
        mock_create_agent,
        mock_recover_saved_plan_action,
        mock_pre_tool_use_hook,
        mock_post_tool_use_hook,
    ):
        """Plan streams should fall back to the session-side tool action when Copilot drops metadata."""
        mock_agent = AsyncMock()
        mock_pre_tool_use_hook.return_value = None
        mock_post_tool_use_hook.return_value = None
        mock_recover_saved_plan_action.return_value = (None, None)

        text_update = MagicMock(spec=["text"])
        text_update.text = "save_plan reported a session error."

        final_response = MagicMock()
        final_response.text = "Here is the structured smoke-test plan."
        final_response.messages = []

        class MockStream:
            def __init__(self, updates, response):
                self._updates = iter(updates)
                self.get_final_response = AsyncMock(return_value=response)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    return next(self._updates)
                except StopIteration as exc:
                    raise StopAsyncIteration from exc

        def run_side_effect(*args, **kwargs):
            session = kwargs["session"]
            session.state["_last_tool_action"] = {
                "action_type": "plan_create",
                "action_data": {
                    "plan_id": "plan-session",
                    "status": "draft",
                    "steps": [],
                },
            }
            return MockStream([text_update], final_response)

        mock_agent.run = MagicMock(side_effect=run_side_effect)
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        events = [
            event
            async for event in service.run_plan_stream(
                message="plan a fix",
                session_id=uuid4(),
                github_token="test-token",
                project_name="Roadmap",
                project_id="PVT_1",
                repo_owner="octocat",
                repo_name="hello-world",
            )
        ]

        done_event = next(e for e in events if e["event"] == "done")
        done_data = json.loads(done_event["data"])
        assert done_data["action_type"] == "plan_create"
        assert done_data["content"] == PLAN_CREATE_DRAFT_MESSAGE
        assert done_data["action_data"]["plan_id"] == "plan-session"

    @patch("src.services.chat_agent.on_post_tool_use_hook", new_callable=AsyncMock)
    @patch("src.services.chat_agent.on_pre_tool_use_hook", new_callable=AsyncMock)
    @patch("src.services.chat_agent._recover_saved_plan_action", new_callable=AsyncMock)
    @patch("src.services.chat_agent.create_agent")
    async def test_plan_stream_recovers_saved_plan_from_db_when_transport_drops_metadata(
        self,
        mock_create_agent,
        mock_recover_saved_plan_action,
        mock_pre_tool_use_hook,
        mock_post_tool_use_hook,
    ):
        """Plan streams should fall back to the saved draft plan when Copilot drops all action metadata."""
        mock_agent = AsyncMock()
        mock_pre_tool_use_hook.return_value = None
        mock_post_tool_use_hook.return_value = None
        mock_recover_saved_plan_action.return_value = (
            "plan_create",
            {
                "plan_id": "plan-db",
                "status": "draft",
                "title": "Recovered plan",
                "summary": "Recovered from persistence",
                "project_id": "PVT_1",
                "project_name": "Roadmap",
                "repo_owner": "octocat",
                "repo_name": "hello-world",
                "steps": [],
            },
        )

        text_update = MagicMock(spec=["text"])
        text_update.text = "save_plan reported a session error."

        class MockStream:
            def __init__(self, updates, response):
                self._updates = iter(updates)
                self.get_final_response = AsyncMock(return_value=response)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    return next(self._updates)
                except StopIteration as exc:
                    raise StopAsyncIteration from exc

        stream = MockStream(
            [text_update],
            MagicMock(text="Assistant summary", messages=[]),
        )
        mock_agent.run = MagicMock(return_value=stream)
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        events = [
            event
            async for event in service.run_plan_stream(
                message="plan a fix",
                session_id=uuid4(),
                github_token="test-token",
                project_name="Roadmap",
                project_id="PVT_1",
                repo_owner="octocat",
                repo_name="hello-world",
                db=object(),
            )
        ]

        done_event = next(e for e in events if e["event"] == "done")
        done_data = json.loads(done_event["data"])
        assert done_data["action_type"] == "plan_create"
        assert done_data["content"] == PLAN_CREATE_DRAFT_MESSAGE
        assert done_data["action_data"]["plan_id"] == "plan-db"


# ── Provider factory tests ──────────────────────────────────────────────


class TestProviderFactory:
    @patch("src.services.agent_provider.get_settings")
    async def test_copilot_provider_requires_token(self, mock_settings):
        from src.services.agent_provider import create_agent

        mock_settings.return_value = MagicMock(ai_provider="copilot", copilot_model="gpt-4o")
        with pytest.raises(ValueError, match="GitHub OAuth token required"):
            await create_agent(instructions="test", github_token=None)

    @patch("src.services.agent_provider.get_settings")
    async def test_azure_provider_requires_credentials(self, mock_settings):
        from src.services.agent_provider import create_agent

        mock_settings.return_value = MagicMock(
            ai_provider="azure_openai",
            azure_openai_endpoint=None,
            azure_openai_key=None,
        )
        with pytest.raises(ValueError, match="Azure OpenAI endpoint not configured"):
            await create_agent(instructions="test")

    @patch("src.services.agent_provider.get_settings")
    async def test_unknown_provider_raises(self, mock_settings):
        from src.services.agent_provider import create_agent

        mock_settings.return_value = MagicMock(ai_provider="unknown_provider")
        with pytest.raises(ValueError, match="Unknown AI_PROVIDER"):
            await create_agent(instructions="test")


# ── Agent key isolation tests ───────────────────────────────────────────


class TestAgentKey:
    """Tests for ChatAgentService._agent_key() composite key generation."""

    def test_agent_key_with_conversation_id(self):
        sid = uuid4()
        key = ChatAgentService._agent_key(sid, "conv-123")
        assert key == f"{sid}:conv-123"

    def test_agent_key_without_conversation_id(self):
        sid = uuid4()
        key = ChatAgentService._agent_key(sid, None)
        assert key == f"{sid}:_"

    def test_agent_key_default_conversation_id(self):
        sid = uuid4()
        key = ChatAgentService._agent_key(sid)
        assert key == f"{sid}:_"

    def test_different_conversations_produce_different_keys(self):
        sid = uuid4()
        key_a = ChatAgentService._agent_key(sid, "conv-a")
        key_b = ChatAgentService._agent_key(sid, "conv-b")
        assert key_a != key_b

    def test_none_conversation_uses_sentinel(self):
        sid = uuid4()
        key_none = ChatAgentService._agent_key(sid, None)
        key_conv = ChatAgentService._agent_key(sid, "conv-1")
        assert key_none != key_conv

    def test_empty_string_conversation_uses_sentinel(self):
        """Empty string conversation_id falls back to '_' sentinel like None."""
        sid = uuid4()
        key_empty = ChatAgentService._agent_key(sid, "")
        key_none = ChatAgentService._agent_key(sid, None)
        assert key_empty == key_none


class TestAgentKeySessionIsolation:
    """Verify that run() and run_stream() use _agent_key to isolate conversations."""

    @patch("src.services.chat_agent.create_agent")
    async def test_run_uses_composite_key_for_session(self, mock_create_agent):
        """run() passes session_id:conversation_id to session mapping."""
        mock_agent = AsyncMock()
        mock_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "Response"
        mock_msg.annotations = None
        mock_response.messages = [mock_msg]
        mock_agent.run.return_value = mock_response
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        service._session_mapping = AsyncMock(spec=AgentSessionMapping)
        mock_session = MagicMock()
        mock_session.state = {}
        mock_session.conversation_history = []
        service._session_mapping.get_or_create.return_value = mock_session

        session_id = uuid4()
        await service.run(
            message="Hello",
            session_id=session_id,
            conversation_id="conv-abc",
        )

        expected_key = f"{session_id}:conv-abc"
        service._session_mapping.get_or_create.assert_called_once_with(expected_key)

    @patch("src.services.chat_agent.create_agent")
    async def test_run_without_conversation_id_uses_sentinel_key(self, mock_create_agent):
        """run() without conversation_id uses session_id:_ as key."""
        mock_agent = AsyncMock()
        mock_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "Response"
        mock_msg.annotations = None
        mock_response.messages = [mock_msg]
        mock_agent.run.return_value = mock_response
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        service._session_mapping = AsyncMock(spec=AgentSessionMapping)
        mock_session = MagicMock()
        mock_session.state = {}
        mock_session.conversation_history = []
        service._session_mapping.get_or_create.return_value = mock_session

        session_id = uuid4()
        await service.run(
            message="Hello",
            session_id=session_id,
        )

        expected_key = f"{session_id}:_"
        service._session_mapping.get_or_create.assert_called_once_with(expected_key)

    @patch("src.services.chat_agent.load_mcp_tools", new_callable=AsyncMock)
    @patch("src.services.chat_agent.create_agent")
    async def test_run_stream_uses_composite_key(self, mock_create_agent, mock_load_mcp_tools):
        """run_stream() passes session_id:conversation_id to session mapping."""
        mock_load_mcp_tools.return_value = []

        # Create a minimal async iterator for the agent
        async def mock_run_stream(*args, **kwargs):
            yield MagicMock(text="token")

        mock_agent = AsyncMock()
        mock_agent.run_stream = mock_run_stream
        mock_create_agent.return_value = mock_agent

        service = ChatAgentService()
        service._session_mapping = AsyncMock(spec=AgentSessionMapping)
        mock_session = MagicMock()
        mock_session.state = {}
        mock_session.conversation_history = []
        service._session_mapping.get_or_create.return_value = mock_session

        session_id = uuid4()
        _events = [
            event
            async for event in service.run_stream(
                message="Hello",
                session_id=session_id,
                conversation_id="conv-xyz",
            )
        ]

        expected_key = f"{session_id}:conv-xyz"
        service._session_mapping.get_or_create.assert_called_once_with(expected_key)

    async def test_different_conversations_get_different_agent_sessions(self):
        """Verify the session mapping creates separate entries for different conversations."""
        mapping = AgentSessionMapping(ttl_seconds=3600, max_sessions=10)
        sid = uuid4()

        # Two conversations under the same session
        key_a = ChatAgentService._agent_key(sid, "conv-a")
        key_b = ChatAgentService._agent_key(sid, "conv-b")

        session_a = await mapping.get_or_create(key_a)
        session_b = await mapping.get_or_create(key_b)

        assert session_a is not session_b
        assert mapping.session_count == 2
