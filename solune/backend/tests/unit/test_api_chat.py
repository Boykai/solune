"""Tests for chat API routes (src/api/chat.py).

Covers:
- GET    /api/v1/chat/messages                     → get_messages
- DELETE /api/v1/chat/messages                     → clear_messages
- POST   /api/v1/chat/messages                     → send_message (branches)
- POST   /api/v1/chat/proposals/{id}/confirm       → confirm_proposal
- DELETE /api/v1/chat/proposals/{id}               → cancel_proposal
- _resolve_repository                              → all fallback branches
"""

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import UploadFile
from fastapi.responses import JSONResponse

from src.models.chat import (
    AITaskProposal,
    IssueRecommendation,
    ProposalStatus,
)
from src.models.user import UserSession

TEST_MAX_FILE_SIZE_BYTES = 4

# ── Helpers ─────────────────────────────────────────────────────────────────


def _recommendation(session_id, **kw) -> IssueRecommendation:
    defaults = {
        "session_id": session_id,
        "original_input": "add dark mode",
        "title": "Add dark mode",
        "user_story": "As a user I want dark mode",
        "ui_ux_description": "Toggle in header",
        "functional_requirements": ["Must toggle theme"],
    }
    defaults.update(kw)
    return IssueRecommendation(**defaults)


def _proposal(session_id, **kw) -> AITaskProposal:
    defaults = {
        "session_id": session_id,
        "original_input": "fix login bug",
        "proposed_title": "Fix login bug",
        "proposed_description": "Fix the login flow",
    }
    defaults.update(kw)
    return AITaskProposal(**defaults)


def _make_upload_file(
    filename: str | None, content: bytes, content_type: str | None = "text/plain"
) -> UploadFile:
    import io

    from starlette.datastructures import Headers

    headers = Headers({"content-type": content_type}) if content_type is not None else Headers()
    return UploadFile(filename=filename, file=io.BytesIO(content), headers=headers)


async def _save_plan(mock_db, session_id: str, **kw) -> dict:
    from src.models.plan import Plan, PlanStatus, PlanStep
    from src.services.chat_store import get_plan, save_plan

    plan_id = kw.pop("plan_id", "plan-1")
    steps = kw.pop(
        "steps",
        [
            PlanStep(
                step_id=f"{plan_id}-step-1",
                plan_id=plan_id,
                position=0,
                title="Investigate planning mode",
                description="Review how /plan mode should behave.",
            )
        ],
    )
    plan = Plan(
        plan_id=plan_id,
        session_id=session_id,
        title=kw.pop("title", "Planning Mode"),
        summary=kw.pop("summary", "Create a plan for persistent planning mode."),
        status=kw.pop("status", PlanStatus.DRAFT),
        project_id=kw.pop("project_id", "PVT_1"),
        project_name=kw.pop("project_name", "Roadmap"),
        repo_owner=kw.pop("repo_owner", "octocat"),
        repo_name=kw.pop("repo_name", "hello-world"),
        steps=steps,
        **kw,
    )
    await save_plan(mock_db, plan)
    saved = await get_plan(mock_db, plan_id)
    assert saved is not None
    return saved


def _parse_sse_events(payload: str) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    normalized = payload.replace("\r\n", "\n").strip()
    for chunk in normalized.split("\n\n"):
        event_name = None
        data_parts: list[str] = []
        for line in chunk.splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ").strip()
            elif line.startswith("data: "):
                data_parts.append(line.removeprefix("data: "))

        if event_name is not None:
            events.append({"event": event_name, "data": "\n".join(data_parts)})

    return events


# ── GET /chat/messages ──────────────────────────────────────────────────────


class TestGetMessages:
    async def test_empty_messages(self, client):
        resp = await client.get("/api/v1/chat/messages")
        assert resp.status_code == 200
        assert resp.json()["messages"] == []


# ── DELETE /chat/messages ───────────────────────────────────────────────────


class TestClearMessages:
    async def test_clear_messages(self, client):
        resp = await client.delete("/api/v1/chat/messages")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Chat history cleared"


# ── POST /chat/messages — feature request path ─────────────────────────────


class TestSendMessageFeatureRequest:
    async def test_plan_command_routes_to_plan_mode_handler(
        self, client, mock_session, mock_chat_agent_service
    ):
        import src.api.chat as chat_mod
        from src.models.chat import ActionType, ChatMessage, SenderType
        from src.services.cache import get_user_projects_cache_key

        mock_session.selected_project_id = "PVT_1"

        cached_project = MagicMock()
        cached_project.project_id = "PVT_1"
        cached_project.name = "Roadmap"
        cached_project.status_columns = [MagicMock(name="Backlog")]
        cached_project.status_columns[0].name = "Backlog"
        chat_mod.cache.set(
            get_user_projects_cache_key(mock_session.github_user_id), [cached_project]
        )

        plan_response = ChatMessage(
            session_id=mock_session.session_id,
            sender_type=SenderType.ASSISTANT,
            content="Plan drafted.",
            action_type=ActionType.PLAN_CREATE,
            action_data={"plan_id": "plan-123", "status": "draft"},
        )
        mock_chat_agent_service.run_plan.return_value = plan_response

        with patch(
            "src.api.chat._resolve_repository",
            new=AsyncMock(return_value=("octocat", "hello-world")),
        ):
            resp = await client.post(
                "/api/v1/chat/messages",
                json={"content": "/plan change app title to hello world for Solune"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["action_type"] == "plan_create"
        assert data["action_data"]["plan_id"] == "plan-123"
        mock_chat_agent_service.run.assert_not_called()
        mock_chat_agent_service.run_plan.assert_awaited_once()

        call_kwargs = mock_chat_agent_service.run_plan.call_args.kwargs
        assert call_kwargs["message"] == "change app title to hello world for Solune"
        assert call_kwargs["project_name"] == "Roadmap"
        assert call_kwargs["available_statuses"] == ["Backlog"]
        assert call_kwargs["repo_owner"] == "octocat"
        assert call_kwargs["repo_name"] == "hello-world"

    async def test_no_project_selected(self, client, mock_session):
        mock_session.selected_project_id = None
        resp = await client.post("/api/v1/chat/messages", json={"content": "add dark mode"})
        assert resp.status_code == 422

    async def test_ai_not_configured(self, client, mock_session, mock_ai_agent_service):
        mock_session.selected_project_id = "PVT_1"
        with (
            patch("src.api.chat.get_ai_agent_service", side_effect=ValueError("not configured")),
            patch("src.api.chat.get_chat_agent_service", side_effect=ValueError("not configured")),
        ):
            resp = await client.post("/api/v1/chat/messages", json={"content": "add dark mode"})
        assert resp.status_code == 200
        data = resp.json()
        assert "not configured" in data["content"].lower() or "AI features" in data["content"]

    async def test_feature_request_generates_recommendation(
        self, client, mock_session, mock_chat_agent_service
    ):
        mock_session.selected_project_id = "PVT_1"

        # Configure chat_agent_service.run to return issue_create action
        from src.models.chat import ActionType, ChatMessage, SenderType

        agent_response = ChatMessage(
            session_id=mock_session.session_id,
            sender_type=SenderType.ASSISTANT,
            content="I've generated a GitHub issue recommendation:\n\n**Add dark mode**",
            action_type=ActionType.ISSUE_CREATE,
            action_data={
                "proposed_title": "Add dark mode",
                "user_story": "As a user I want dark mode",
                "ui_ux_description": "Toggle in header",
                "functional_requirements": ["Must toggle theme"],
                "technical_notes": "",
            },
        )
        mock_chat_agent_service.run.return_value = agent_response

        resp = await client.post(
            "/api/v1/chat/messages", json={"content": "I want dark mode support"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action_type"] == "issue_create"
        assert "recommendation_id" in data["action_data"]

    async def test_feature_detection_fails_gracefully(
        self, client, mock_session, mock_chat_agent_service
    ):
        """If agent run fails, returns an error message."""
        mock_session.selected_project_id = "PVT_1"

        from src.models.chat import ChatMessage, SenderType

        error_response = ChatMessage(
            session_id=mock_session.session_id,
            sender_type=SenderType.ASSISTANT,
            content="I encountered an error processing your request (RuntimeError). Please try again.",
        )
        mock_chat_agent_service.run.return_value = error_response

        resp = await client.post("/api/v1/chat/messages", json={"content": "add dark mode"})
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data["content"].lower()


# ── POST /chat/messages — status change path ───────────────────────────────


class TestSendMessageStatusChange:
    async def test_status_change_found(self, client, mock_session, mock_chat_agent_service):
        mock_session.selected_project_id = "PVT_1"

        from src.models.chat import ActionType, ChatMessage, SenderType

        agent_response = ChatMessage(
            session_id=mock_session.session_id,
            sender_type=SenderType.ASSISTANT,
            content="I'll update the status of **Fix login bug** from **In Progress** to **Done**.",
            action_type=ActionType.STATUS_UPDATE,
            action_data={
                "task_id": "PVTI_1",
                "task_title": "Fix login bug",
                "current_status": "In Progress",
                "target_status": "Done",
            },
        )
        mock_chat_agent_service.run.return_value = agent_response

        resp = await client.post(
            "/api/v1/chat/messages",
            json={"content": "move login bug to Done"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action_type"] == "status_update"

    async def test_status_change_task_not_found(
        self, client, mock_session, mock_chat_agent_service
    ):
        mock_session.selected_project_id = "PVT_1"

        from src.models.chat import ChatMessage, SenderType

        agent_response = ChatMessage(
            session_id=mock_session.session_id,
            sender_type=SenderType.ASSISTANT,
            content="I couldn't find a task matching 'nonexistent'. Please try again.",
        )
        mock_chat_agent_service.run.return_value = agent_response

        resp = await client.post(
            "/api/v1/chat/messages",
            json={"content": "move X to Done"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "couldn't find" in data["content"].lower()


# ── POST /chat/messages — task generation path ─────────────────────────────


class TestSendMessageTaskGeneration:
    async def test_generates_task_proposal(self, client, mock_session, mock_chat_agent_service):
        mock_session.selected_project_id = "PVT_1"

        from src.models.chat import ActionType, ChatMessage, SenderType

        agent_response = ChatMessage(
            session_id=mock_session.session_id,
            sender_type=SenderType.ASSISTANT,
            content="I've created a task proposal:\n\n**Fix auth bug**",
            action_type=ActionType.TASK_CREATE,
            action_data={
                "proposed_title": "Fix auth bug",
                "proposed_description": "Fix the authentication flow bug in the login page",
            },
        )
        mock_chat_agent_service.run.return_value = agent_response

        resp = await client.post("/api/v1/chat/messages", json={"content": "fix the auth bug"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["action_type"] == "task_create"
        assert data["action_data"]["proposed_title"] == "Fix auth bug"

    async def test_task_generation_error(self, client, mock_session, mock_chat_agent_service):
        mock_session.selected_project_id = "PVT_1"

        from src.models.chat import ChatMessage, SenderType

        error_response = ChatMessage(
            session_id=mock_session.session_id,
            sender_type=SenderType.ASSISTANT,
            content="I encountered an error processing your request (RuntimeError). Please try again.",
        )
        mock_chat_agent_service.run.return_value = error_response

        resp = await client.post("/api/v1/chat/messages", json={"content": "do something"})
        assert resp.status_code == 200
        assert "error" in resp.json()["content"].lower()

    async def test_ai_enhance_off_uses_raw_input(self, client, mock_session, mock_ai_agent_service):
        """When ai_enhance=False, raw user input is used as description, title is AI-generated."""
        mock_session.selected_project_id = "PVT_1"
        mock_ai_agent_service.detect_feature_request_intent.return_value = False
        mock_ai_agent_service.parse_status_change_request.return_value = None
        mock_ai_agent_service.generate_title_from_description.return_value = "Fix login flow"

        user_input = "The login page has a bug where users can't sign in"
        resp = await client.post(
            "/api/v1/chat/messages",
            json={"content": user_input, "ai_enhance": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action_type"] == "task_create"
        assert data["action_data"]["proposed_title"] == "Fix login flow"
        assert data["action_data"]["proposed_description"] == user_input

    async def test_ai_enhance_off_metadata_error_returns_specific_message(
        self, client, mock_session, mock_ai_agent_service
    ):
        """When the fallback branch fails after title generation, show a specific error."""
        mock_session.selected_project_id = "PVT_1"
        mock_ai_agent_service.detect_feature_request_intent.return_value = False
        mock_ai_agent_service.parse_status_change_request.return_value = None
        mock_ai_agent_service.generate_title_from_description.return_value = "Some task"

        with patch("src.api.chat.AITaskProposal", side_effect=RuntimeError("storage failed")):
            resp = await client.post(
                "/api/v1/chat/messages",
                json={"content": "some task", "ai_enhance": False},
            )
        assert resp.status_code == 200
        content = resp.json()["content"]
        assert "metadata" in content.lower()
        assert "preserved" in content.lower()
        # Must NOT show the generic error
        assert "couldn't generate a task" not in content.lower()

    async def test_ai_enhance_on_uses_full_pipeline(
        self, client, mock_session, mock_chat_agent_service
    ):
        """When ai_enhance=True (default), the agent framework is used."""
        import src.api.chat as chat_mod

        mock_session.selected_project_id = "PVT_1"

        from src.models.chat import ActionType, ChatMessage, SenderType

        agent_response = ChatMessage(
            session_id=mock_session.session_id,
            sender_type=SenderType.ASSISTANT,
            content="I've created a task proposal:\n\n**Enhanced Title**",
            action_type=ActionType.TASK_CREATE,
            action_data={
                "proposed_title": "Enhanced Title",
                "proposed_description": "AI-enhanced description of the task",
            },
        )
        mock_chat_agent_service.run.return_value = agent_response
        expected_db = chat_mod.get_db()

        resp = await client.post(
            "/api/v1/chat/messages",
            json={"content": "do something", "ai_enhance": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action_data"]["proposed_title"] == "Enhanced Title"
        assert mock_chat_agent_service.run.call_args.kwargs["db"] is expected_db

    async def test_ai_enhance_off_without_ai_service_preserves_description(
        self, client, mock_session, mock_chat_agent_service
    ):
        mock_session.selected_project_id = "PVT_1"
        user_input = "Investigate why the login flow gets stuck after redirect"

        with patch("src.api.chat.get_ai_agent_service", side_effect=ValueError("not configured")):
            resp = await client.post(
                "/api/v1/chat/messages",
                json={"content": user_input, "ai_enhance": False},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["action_type"] == "task_create"
        assert data["action_data"]["proposed_title"] == user_input
        assert data["action_data"]["proposed_description"] == user_input
        assert data["action_data"]["status"] == "pending"
        mock_chat_agent_service.run.assert_not_called()

        stored = await client.get("/api/v1/chat/messages")
        messages = stored.json()["messages"]
        assert messages[-1]["action_data"]["proposed_description"] == user_input


# ── POST /chat/messages/stream ───────────────────────────────────────────────


class TestSendMessageStream:
    async def test_stream_plan_command_routes_to_plan_mode_stream(
        self, client, mock_session, mock_chat_agent_service
    ):
        import src.api.chat as chat_mod
        from src.models.chat import ActionType, ChatMessage, SenderType
        from src.services.cache import get_user_projects_cache_key

        mock_session.selected_project_id = "PVT_1"

        cached_project = MagicMock()
        cached_project.project_id = "PVT_1"
        cached_project.name = "Roadmap"
        cached_project.status_columns = [MagicMock(name="Backlog"), MagicMock(name="Done")]
        cached_project.status_columns[0].name = "Backlog"
        cached_project.status_columns[1].name = "Done"
        chat_mod.cache.set(
            get_user_projects_cache_key(mock_session.github_user_id), [cached_project]
        )

        async def stream_events():
            yield {
                "event": "thinking",
                "data": json.dumps({"phase": "planning", "detail": "Drafting implementation plan"}),
            }
            yield {
                "event": "done",
                "data": ChatMessage(
                    session_id=mock_session.session_id,
                    sender_type=SenderType.ASSISTANT,
                    content="Plan drafted.",
                    action_type=ActionType.PLAN_CREATE,
                    action_data={"plan_id": "plan-stream", "status": "draft"},
                ).model_dump_json(),
            }

        mock_chat_agent_service.run_plan_stream = MagicMock(return_value=stream_events())

        with patch(
            "src.api.chat._resolve_repository",
            new=AsyncMock(return_value=("octocat", "hello-world")),
        ):
            resp = await client.post(
                "/api/v1/chat/messages/stream",
                json={"content": "/plan change app title to hello world for Solune"},
            )

        assert resp.status_code == 200
        events = _parse_sse_events(resp.text)
        done_event = next(event for event in events if event["event"] == "done")
        done_data = json.loads(done_event["data"])
        assert done_data["action_type"] == "plan_create"
        assert done_data["action_data"]["plan_id"] == "plan-stream"

        mock_chat_agent_service.run_stream.assert_not_called()
        mock_chat_agent_service.run_plan_stream.assert_called_once()
        call_kwargs = mock_chat_agent_service.run_plan_stream.call_args.kwargs
        assert call_kwargs["message"] == "change app title to hello world for Solune"
        assert call_kwargs["project_name"] == "Roadmap"
        assert call_kwargs["available_statuses"] == ["Backlog", "Done"]
        assert call_kwargs["repo_owner"] == "octocat"
        assert call_kwargs["repo_name"] == "hello-world"

    async def test_stream_persists_post_processed_assistant_message(
        self, client, mock_session, mock_chat_agent_service
    ):
        import src.api.chat as chat_mod
        from src.models.chat import ActionType, ChatMessage, SenderType
        from src.services.cache import (
            get_project_items_cache_key,
            get_user_projects_cache_key,
        )

        mock_session.selected_project_id = "PVT_1"

        cached_project = MagicMock()
        cached_project.project_id = "PVT_1"
        cached_project.name = "Roadmap"
        cached_project.status_columns = [MagicMock(name="Todo"), MagicMock(name="Done")]
        cached_project.status_columns[0].name = "Todo"
        cached_project.status_columns[1].name = "Done"

        cached_task = MagicMock()
        cached_task.title = "Fix login bug"
        cached_task.status = "Todo"
        cached_task.github_item_id = "PVTI_1"

        chat_mod.cache.set(
            get_user_projects_cache_key(mock_session.github_user_id), [cached_project]
        )
        chat_mod.cache.set(get_project_items_cache_key("PVT_1"), [cached_task])

        async def stream_events():
            yield {"event": "token", "data": json.dumps({"content": "Creating proposal..."})}
            final_message = ChatMessage(
                session_id=mock_session.session_id,
                sender_type=SenderType.ASSISTANT,
                content="I've created a task proposal.",
                action_type=ActionType.TASK_CREATE,
                action_data={
                    "proposed_title": "Fix login bug",
                    "proposed_description": "Fix the login bug in the auth flow",
                },
            )
            yield {"event": "done", "data": final_message.model_dump_json()}

        mock_chat_agent_service.run_stream = MagicMock(return_value=stream_events())
        expected_db = chat_mod.get_db()

        resp = await client.post(
            "/api/v1/chat/messages/stream",
            json={"content": "fix the login bug"},
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        events = _parse_sse_events(resp.text)
        done_event = next(event for event in events if event["event"] == "done")
        done_data = json.loads(done_event["data"])
        assert done_data["action_type"] == "task_create"
        assert done_data["action_data"]["proposed_title"] == "Fix login bug"
        assert done_data["action_data"]["status"] == "pending"
        assert "proposal_id" in done_data["action_data"]

        stored = await client.get("/api/v1/chat/messages")
        messages = stored.json()["messages"]
        assert len(messages) == 2
        assert messages[0]["sender_type"] == "user"
        assert messages[1]["sender_type"] == "assistant"
        assert messages[1]["action_data"]["proposed_title"] == "Fix login bug"
        assert "proposal_id" in messages[1]["action_data"]

        call_kwargs = mock_chat_agent_service.run_stream.call_args.kwargs
        assert call_kwargs["project_name"] == "Roadmap"
        assert call_kwargs["project_id"] == "PVT_1"
        assert call_kwargs["available_tasks"] == [cached_task]
        assert call_kwargs["available_statuses"] == ["Todo", "Done"]
        assert call_kwargs["db"] is expected_db

    async def test_stream_returns_503_when_streaming_disabled(
        self, client, mock_session, mock_settings, mock_chat_agent_service
    ):
        mock_session.selected_project_id = "PVT_1"
        mock_settings.agent_streaming_enabled = False

        resp = await client.post(
            "/api/v1/chat/messages/stream",
            json={"content": "fix the login bug"},
        )

        assert resp.status_code == 503
        assert "streaming is disabled" in resp.json()["detail"].lower()
        mock_chat_agent_service.run_stream.assert_not_called()

    async def test_stream_rejects_missing_pipeline_before_agent_run(
        self, client, mock_session, mock_chat_agent_service
    ):
        mock_session.selected_project_id = "PVT_1"

        with patch(
            "src.services.pipelines.service.PipelineService.get_pipeline",
            new=AsyncMock(return_value=None),
        ):
            resp = await client.post(
                "/api/v1/chat/messages/stream",
                json={"content": "fix the login bug", "pipeline_id": "missing-pipeline"},
            )

        assert resp.status_code == 422
        assert resp.json()["error"] == "Pipeline not found: missing-pipeline"
        mock_chat_agent_service.run_stream.assert_not_called()


# ── Plan mode endpoints ───────────────────────────────────────────────────────


class TestPlanModeEndpoints:
    async def test_send_plan_message_uses_project_and_repo_context(
        self, client, mock_session, mock_chat_agent_service
    ):
        import src.api.chat as chat_mod
        from src.models.chat import ActionType, ChatMessage, SenderType
        from src.services.cache import get_user_projects_cache_key

        mock_session.selected_project_id = "PVT_1"

        cached_project = MagicMock()
        cached_project.project_id = "PVT_1"
        cached_project.name = "Roadmap"
        cached_project.status_columns = [MagicMock(name="Backlog"), MagicMock(name="In Progress")]
        cached_project.status_columns[0].name = "Backlog"
        cached_project.status_columns[1].name = "In Progress"
        chat_mod.cache.set(
            get_user_projects_cache_key(mock_session.github_user_id), [cached_project]
        )

        agent_response = ChatMessage(
            session_id=mock_session.session_id,
            sender_type=SenderType.ASSISTANT,
            content="I've drafted a plan for this feature.",
            action_type=ActionType.PLAN_CREATE,
            action_data={"plan_id": "plan-123", "status": "draft"},
        )
        mock_chat_agent_service.run_plan.return_value = agent_response

        with patch(
            "src.api.chat._resolve_repository",
            new=AsyncMock(return_value=("octocat", "hello-world")),
        ):
            expected_db = chat_mod.get_db()
            resp = await client.post(
                "/api/v1/chat/messages/plan",
                json={"content": "/plan Add persistent planning mode"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["action_type"] == "plan_create"
        assert data["action_data"]["plan_id"] == "plan-123"

        call_kwargs = mock_chat_agent_service.run_plan.call_args.kwargs
        assert call_kwargs["message"] == "Add persistent planning mode"
        assert call_kwargs["project_name"] == "Roadmap"
        assert call_kwargs["project_id"] == "PVT_1"
        assert call_kwargs["available_statuses"] == ["Backlog", "In Progress"]
        assert call_kwargs["repo_owner"] == "octocat"
        assert call_kwargs["repo_name"] == "hello-world"
        assert call_kwargs["db"] is expected_db

        stored = await client.get("/api/v1/chat/messages")
        messages = stored.json()["messages"]
        assert [message["sender_type"] for message in messages] == ["user", "assistant"]
        assert messages[1]["action_type"] == "plan_create"

    async def test_send_plan_message_requires_feature_description(
        self, client, mock_session, mock_chat_agent_service
    ):
        mock_session.selected_project_id = "PVT_1"

        resp = await client.post("/api/v1/chat/messages/plan", json={"content": "/plan   "})

        assert resp.status_code == 400
        assert resp.json()["detail"] == "Please provide a feature description after /plan."
        mock_chat_agent_service.run_plan.assert_not_called()

    async def test_send_plan_message_service_unavailable_does_not_persist_user_message(
        self, client, mock_session
    ):
        mock_session.selected_project_id = "PVT_1"

        with (
            patch(
                "src.api.chat._resolve_repository",
                new=AsyncMock(return_value=("octocat", "hello-world")),
            ),
            patch("src.api.chat.get_chat_agent_service", side_effect=RuntimeError("offline")),
        ):
            resp = await client.post(
                "/api/v1/chat/messages/plan",
                json={"content": "/plan Build a roadmap"},
            )

        assert resp.status_code == 503
        assert resp.json()["detail"] == "Plan mode not available."

        stored = await client.get("/api/v1/chat/messages")
        assert stored.json()["messages"] == []

    async def test_send_plan_message_stream_emits_thinking_and_persists_result(
        self, client, mock_session, mock_chat_agent_service
    ):
        import src.api.chat as chat_mod
        from src.models.chat import ActionType, ChatMessage, SenderType
        from src.services.cache import get_user_projects_cache_key

        mock_session.selected_project_id = "PVT_1"

        cached_project = MagicMock()
        cached_project.project_id = "PVT_1"
        cached_project.name = "Roadmap"
        cached_project.status_columns = [MagicMock(name="Backlog"), MagicMock(name="Done")]
        cached_project.status_columns[0].name = "Backlog"
        cached_project.status_columns[1].name = "Done"
        chat_mod.cache.set(
            get_user_projects_cache_key(mock_session.github_user_id), [cached_project]
        )

        async def stream_events():
            yield {
                "event": "thinking",
                "data": json.dumps({"phase": "planning", "detail": "Drafting implementation plan"}),
            }
            yield {
                "event": "done",
                "data": ChatMessage(
                    session_id=mock_session.session_id,
                    sender_type=SenderType.ASSISTANT,
                    content="Here is the updated plan.",
                    action_type=ActionType.PLAN_CREATE,
                    action_data={"plan_id": "plan-123", "status": "draft"},
                ).model_dump_json(),
            }

        mock_chat_agent_service.run_plan_stream = MagicMock(return_value=stream_events())

        with patch(
            "src.api.chat._resolve_repository",
            new=AsyncMock(return_value=("octocat", "hello-world")),
        ):
            resp = await client.post(
                "/api/v1/chat/messages/plan/stream",
                json={"content": "/plan Refine the plan flow"},
            )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        events = _parse_sse_events(resp.text)
        thinking_event = next(event for event in events if event["event"] == "thinking")
        assert json.loads(thinking_event["data"]) == {
            "phase": "planning",
            "detail": "Drafting implementation plan",
        }

        done_event = next(event for event in events if event["event"] == "done")
        done_data = json.loads(done_event["data"])
        assert done_data["action_type"] == "plan_create"
        assert done_data["action_data"]["plan_id"] == "plan-123"

        call_kwargs = mock_chat_agent_service.run_plan_stream.call_args.kwargs
        assert call_kwargs["message"] == "Refine the plan flow"
        assert call_kwargs["available_statuses"] == ["Backlog", "Done"]
        assert call_kwargs["repo_owner"] == "octocat"
        assert call_kwargs["repo_name"] == "hello-world"

        stored = await client.get("/api/v1/chat/messages")
        messages = stored.json()["messages"]
        assert [message["sender_type"] for message in messages] == ["user", "assistant"]
        assert messages[1]["content"] == "Here is the updated plan."

    async def test_send_plan_message_stream_service_unavailable_does_not_persist_user_message(
        self, client, mock_session
    ):
        mock_session.selected_project_id = "PVT_1"

        with (
            patch(
                "src.api.chat._resolve_repository",
                new=AsyncMock(return_value=("octocat", "hello-world")),
            ),
            patch("src.api.chat.get_chat_agent_service", side_effect=RuntimeError("offline")),
        ):
            resp = await client.post(
                "/api/v1/chat/messages/plan/stream",
                json={"content": "/plan Stream a roadmap"},
            )

        assert resp.status_code == 503
        assert resp.json()["detail"] == "Plan mode not available."

        stored = await client.get("/api/v1/chat/messages")
        assert stored.json()["messages"] == []

    async def test_send_plan_message_stream_done_failure_falls_back_to_original_event(
        self, client, mock_session, mock_chat_agent_service
    ):
        import src.api.chat as chat_mod
        from src.models.chat import ActionType, ChatMessage, SenderType
        from src.services.cache import get_user_projects_cache_key

        mock_session.selected_project_id = "PVT_1"

        cached_project = MagicMock()
        cached_project.project_id = "PVT_1"
        cached_project.name = "Roadmap"
        cached_project.status_columns = [MagicMock(name="Backlog")]
        cached_project.status_columns[0].name = "Backlog"
        chat_mod.cache.set(
            get_user_projects_cache_key(mock_session.github_user_id), [cached_project]
        )

        raw_message = ChatMessage(
            session_id=mock_session.session_id,
            sender_type=SenderType.ASSISTANT,
            content="Draft plan ready.",
            action_type=ActionType.PLAN_CREATE,
            action_data={"plan_id": "plan-raw", "status": "draft"},
        )

        async def stream_events():
            yield {"event": "done", "data": raw_message.model_dump_json()}

        mock_chat_agent_service.run_plan_stream = MagicMock(return_value=stream_events())

        with (
            patch(
                "src.api.chat._resolve_repository",
                new=AsyncMock(return_value=("octocat", "hello-world")),
            ),
            patch(
                "src.api.chat.add_message",
                new=AsyncMock(side_effect=[None, RuntimeError("db unavailable")]),
            ),
        ):
            resp = await client.post(
                "/api/v1/chat/messages/plan/stream",
                json={"content": "/plan Handle plan persistence errors"},
            )

        assert resp.status_code == 200
        events = _parse_sse_events(resp.text)
        done_event = next(event for event in events if event["event"] == "done")
        assert json.loads(done_event["data"]) == raw_message.model_dump(mode="json")


class TestTranscriptHelpers:
    async def test_handle_transcript_upload_returns_none_without_files(
        self, mock_session, mock_ai_agent_service
    ):
        from src.api.chat import _handle_transcript_upload

        result = await _handle_transcript_upload(
            mock_session,
            mock_ai_agent_service,
            "Roadmap",
            None,
            None,
        )

        assert result is None
        mock_ai_agent_service.analyze_transcript.assert_not_called()

    async def test_handle_transcript_upload_success_with_metadata_fallback(
        self, mock_session, mock_ai_agent_service
    ):
        from src.api.chat import _handle_transcript_upload

        upload_dir = Path(tempfile.gettempdir()) / "chat-uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4().hex[:8]}-transcript.txt"
        file_path = upload_dir / filename
        file_path.write_text("speaker 1: hello\nspeaker 2: ship it", encoding="utf-8")

        recommendation = _recommendation(
            mock_session.session_id,
            technical_notes="T" * 320,
        )
        mock_ai_agent_service.analyze_transcript.return_value = recommendation
        stored: dict[str, IssueRecommendation] = {}

        async def capture_recommendation(rec: IssueRecommendation) -> None:
            stored["recommendation"] = rec

        try:
            with (
                patch(
                    "src.services.transcript_detector.detect_transcript",
                    return_value=SimpleNamespace(is_transcript=True),
                ),
                patch(
                    "src.api.chat._resolve_repository",
                    new=AsyncMock(side_effect=RuntimeError("no repo")),
                ),
                patch(
                    "src.api.chat.store_recommendation",
                    new=AsyncMock(side_effect=capture_recommendation),
                ),
                patch("src.api.chat.add_message", new_callable=AsyncMock) as add_message,
                patch("src.api.chat._trigger_signal_delivery") as trigger_signal,
            ):
                message = await _handle_transcript_upload(
                    mock_session,
                    mock_ai_agent_service,
                    "Roadmap",
                    "pipe-1",
                    [f"/uploads/{filename}"],
                )
        finally:
            file_path.unlink(missing_ok=True)

        assert message is not None
        assert message.action_data is not None
        assert message.action_data["pipeline_id"] == "pipe-1"
        assert message.action_data["file_urls"] == [f"/uploads/{filename}"]
        assert "Technical Notes:" in message.content
        assert message.action_data["status"] == "pending"
        mock_ai_agent_service.analyze_transcript.assert_awaited_once_with(
            transcript_content="speaker 1: hello\nspeaker 2: ship it",
            project_name="Roadmap",
            session_id=str(mock_session.session_id),
            github_token=mock_session.access_token,
            metadata_context=None,
        )
        assert stored["recommendation"].selected_pipeline_id == "pipe-1"
        assert stored["recommendation"].file_urls == [f"/uploads/{filename}"]
        add_message.assert_awaited_once()
        trigger_signal.assert_called_once()

    async def test_handle_transcript_upload_returns_error_message_when_analysis_fails(
        self, mock_session, mock_ai_agent_service
    ):
        from src.api.chat import _handle_transcript_upload

        upload_dir = Path(tempfile.gettempdir()) / "chat-uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4().hex[:8]}-transcript.txt"
        file_path = upload_dir / filename
        file_path.write_text("speaker 1: hello", encoding="utf-8")
        mock_ai_agent_service.analyze_transcript.side_effect = TimeoutError("upstream timeout")

        try:
            with (
                patch(
                    "src.services.transcript_detector.detect_transcript",
                    return_value=SimpleNamespace(is_transcript=True),
                ),
                patch(
                    "src.api.chat._resolve_repository",
                    new=AsyncMock(return_value=("octocat", "hello-world")),
                ),
                patch(
                    "src.api.chat.store_recommendation", new_callable=AsyncMock
                ) as store_recommendation,
                patch("src.api.chat.add_message", new_callable=AsyncMock) as add_message,
            ):
                message = await _handle_transcript_upload(
                    mock_session,
                    mock_ai_agent_service,
                    "Roadmap",
                    None,
                    [f"/uploads/{filename}"],
                )
        finally:
            file_path.unlink(missing_ok=True)

        assert message is not None
        assert "couldn't extract requirements" in message.content.lower()
        assert "TimeoutError" in message.content
        store_recommendation.assert_not_awaited()
        add_message.assert_awaited_once()

    async def test_handle_transcript_upload_skips_oversized_files(
        self, mock_session, mock_ai_agent_service
    ):
        from src.api.chat import _handle_transcript_upload

        upload_dir = Path(tempfile.gettempdir()) / "chat-uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4().hex[:8]}-transcript.txt"
        file_path = upload_dir / filename
        file_path.write_text("x" * 10, encoding="utf-8")

        try:
            with (
                patch(
                    "src.api.chat.MAX_FILE_SIZE_BYTES",
                    TEST_MAX_FILE_SIZE_BYTES,
                ),
                patch("src.services.transcript_detector.detect_transcript") as detect_transcript,
            ):
                result = await _handle_transcript_upload(
                    mock_session,
                    mock_ai_agent_service,
                    "Roadmap",
                    None,
                    [f"/uploads/{filename}"],
                )
        finally:
            file_path.unlink(missing_ok=True)

        assert result is None
        detect_transcript.assert_not_called()
        mock_ai_agent_service.analyze_transcript.assert_not_called()

    async def test_extract_transcript_content_returns_first_detected_transcript(self):
        from src.api.chat import _extract_transcript_content

        upload_dir = Path(tempfile.gettempdir()) / "chat-uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        non_transcript_name = f"{uuid4().hex[:8]}-notes.txt"
        transcript_name = f"{uuid4().hex[:8]}-meeting.vtt"
        non_transcript_path = upload_dir / non_transcript_name
        transcript_path = upload_dir / transcript_name
        non_transcript_path.write_text("just some notes", encoding="utf-8")
        transcript_path.write_text("WEBVTT\n\n00:00.000 --> 00:01.000\nHello", encoding="utf-8")

        try:
            with patch(
                "src.services.transcript_detector.detect_transcript",
                side_effect=[
                    SimpleNamespace(is_transcript=False),
                    SimpleNamespace(is_transcript=True),
                ],
            ):
                result = await _extract_transcript_content(
                    [
                        "/uploads/missing.txt",
                        f"/uploads/{non_transcript_name}",
                        f"/uploads/{transcript_name}",
                    ]
                )
        finally:
            non_transcript_path.unlink(missing_ok=True)
            transcript_path.unlink(missing_ok=True)

        assert result == "WEBVTT\n\n00:00.000 --> 00:01.000\nHello"

    async def test_extract_transcript_content_skips_oversized_files(self):
        from src.api.chat import _extract_transcript_content

        upload_dir = Path(tempfile.gettempdir()) / "chat-uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4().hex[:8]}-meeting.vtt"
        file_path = upload_dir / filename
        file_path.write_text("x" * 10, encoding="utf-8")

        try:
            with (
                patch(
                    "src.api.chat.MAX_FILE_SIZE_BYTES",
                    TEST_MAX_FILE_SIZE_BYTES,
                ),
                patch("src.services.transcript_detector.detect_transcript") as detect_transcript,
            ):
                result = await _extract_transcript_content([f"/uploads/{filename}"])
        finally:
            file_path.unlink(missing_ok=True)

        assert result is None
        detect_transcript.assert_not_called()

    async def test_get_plan_endpoint_is_scoped_to_current_session(
        self, client, mock_db, mock_session
    ):
        await _save_plan(mock_db, str(mock_session.session_id), plan_id="plan-visible")

        resp = await client.get("/api/v1/chat/plans/plan-visible")

        assert resp.status_code == 200
        data = resp.json()
        assert data["plan_id"] == "plan-visible"
        assert data["project_name"] == "Roadmap"
        assert data["repo_owner"] == "octocat"
        assert data["steps"][0]["title"] == "Investigate planning mode"

        await _save_plan(mock_db, "different-session", plan_id="plan-hidden")
        resp = await client.get("/api/v1/chat/plans/plan-hidden")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Plan not found."

    async def test_update_plan_endpoint_rejects_non_draft_plans(
        self, client, mock_db, mock_session
    ):
        from src.models.plan import PlanStatus

        await _save_plan(
            mock_db,
            str(mock_session.session_id),
            plan_id="plan-completed",
            status=PlanStatus.COMPLETED,
        )

        resp = await client.patch(
            "/api/v1/chat/plans/plan-completed",
            json={"title": "Updated title"},
        )

        assert resp.status_code == 400
        assert resp.json()["detail"] == "Only draft plans can be updated."

    async def test_approve_plan_launches_pipeline_with_rendered_markdown(
        self, client, mock_db, mock_session
    ):
        import src.api.chat as chat_mod
        from src.models.workflow import WorkflowResult

        await _save_plan(
            mock_db,
            str(mock_session.session_id),
            plan_id="plan-launch",
            selected_pipeline_id="pipeline-123",
        )

        with patch(
            "src.api.pipelines.execute_pipeline_launch",
            new=AsyncMock(
                return_value=WorkflowResult(
                    success=True,
                    issue_id="I_node_101",
                    issue_number=101,
                    issue_url="https://github.com/octocat/hello-world/issues/101",
                    project_item_id="PVTI_101",
                    current_status="Backlog",
                    message="Issue #101 created, added to the project, and launched with the selected pipeline.",
                )
            ),
        ) as mock_launch:
            resp = await client.post("/api/v1/chat/plans/plan-launch/approve")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["parent_issue_number"] == 101
        assert data["parent_issue_url"] == "https://github.com/octocat/hello-world/issues/101"

        launch_call = mock_launch.await_args
        assert launch_call is not None
        call_kwargs = launch_call.kwargs
        assert call_kwargs["project_id"] == "PVT_1"
        assert call_kwargs["pipeline_id"] == "pipeline-123"
        assert call_kwargs["session"].access_token == mock_session.access_token
        assert call_kwargs["issue_description"].startswith("# Planning Mode")
        assert "## Implementation Steps" in call_kwargs["issue_description"]
        assert "### Step 1: Investigate planning mode" in call_kwargs["issue_description"]

        messages = await chat_mod.get_session_messages(mock_session.session_id)
        assert messages[-1].sender_type.value == "system"
        assert "GitHub parent issue created for plan" in messages[-1].content
        assert "https://github.com/octocat/hello-world/issues/101" in messages[-1].content

    async def test_approve_plan_marks_plan_failed_when_issue_creation_raises(
        self, client, mock_db, mock_session
    ):
        from src.services.chat_store import get_plan

        await _save_plan(mock_db, str(mock_session.session_id), plan_id="plan-error")

        with patch(
            "src.api.pipelines.execute_pipeline_launch",
            new=AsyncMock(side_effect=RuntimeError("GitHub 500: secret details")),
        ):
            resp = await client.post("/api/v1/chat/plans/plan-error/approve")

        assert resp.status_code == 502
        data = resp.json()
        assert data["error"] == "GitHub issue creation failed"
        assert data["detail"] == "An error occurred while creating GitHub issues. Please try again."

        updated = await get_plan(mock_db, "plan-error")
        assert updated is not None
        assert updated["status"] == "failed"

    async def test_approve_plan_marks_failed_when_pipeline_launch_returns_no_issue(
        self, client, mock_db, mock_session
    ):
        from src.models.workflow import WorkflowResult
        from src.services.chat_store import get_plan

        await _save_plan(mock_db, str(mock_session.session_id), plan_id="plan-no-issue")

        with patch(
            "src.api.pipelines.execute_pipeline_launch",
            new=AsyncMock(
                return_value=WorkflowResult(
                    success=False,
                    issue_id=None,
                    issue_number=None,
                    issue_url=None,
                    project_item_id=None,
                    current_status="error",
                    message="We couldn't launch the pipeline from this issue description. Please try again.",
                )
            ),
        ):
            resp = await client.post("/api/v1/chat/plans/plan-no-issue/approve")

        assert resp.status_code == 502
        data = resp.json()
        assert data["error"] == "GitHub issue creation failed"
        assert (
            data["detail"]
            == "We couldn't launch the pipeline from this issue description. Please try again."
        )

        updated = await get_plan(mock_db, "plan-no-issue")
        assert updated is not None
        assert updated["status"] == "failed"

    async def test_approve_plan_completes_when_parent_issue_exists_but_launch_warns(
        self, client, mock_db, mock_session
    ):
        import src.api.chat as chat_mod
        from src.models.workflow import WorkflowResult
        from src.services.chat_store import get_plan

        await _save_plan(mock_db, str(mock_session.session_id), plan_id="plan-warning")

        with patch(
            "src.api.pipelines.execute_pipeline_launch",
            new=AsyncMock(
                return_value=WorkflowResult(
                    success=False,
                    issue_id="I_node_202",
                    issue_number=202,
                    issue_url="https://github.com/octocat/hello-world/issues/202",
                    project_item_id="PVTI_202",
                    current_status="Backlog",
                    message="The parent issue was created, but the first agent could not be assigned automatically. Open the issue to continue from the board.",
                )
            ),
        ):
            resp = await client.post("/api/v1/chat/plans/plan-warning/approve")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["parent_issue_number"] == 202

        updated = await get_plan(mock_db, "plan-warning")
        assert updated is not None
        assert updated["status"] == "completed"
        assert updated["parent_issue_number"] == 202

        messages = await chat_mod.get_session_messages(mock_session.session_id)
        assert messages[-1].sender_type.value == "system"
        assert "GitHub parent issue created for plan" in messages[-1].content
        assert "could not be assigned automatically" in messages[-1].content

    async def test_exit_plan_mode_calls_chat_agent_service(self, client, mock_db, mock_session):
        await _save_plan(mock_db, str(mock_session.session_id), plan_id="plan-exit")

        resp = await client.post("/api/v1/chat/plans/plan-exit/exit")

        assert resp.status_code == 200
        assert resp.json() == {
            "message": "Plan mode deactivated",
            "plan_id": "plan-exit",
            "plan_status": "draft",
        }


# ── POST /chat/proposals/{id}/confirm ───────────────────────────────────────


class TestConfirmProposal:
    async def test_proposal_not_found(self, client):
        resp = await client.post(
            "/api/v1/chat/proposals/nonexistent/confirm",
            json={},
        )
        assert resp.status_code == 404

    async def test_confirm_creates_issue(
        self, client, mock_session, mock_github_service, mock_websocket_manager
    ):
        mock_session.selected_project_id = "PVT_1"
        proposal = _proposal(mock_session.session_id)

        # Insert into module-level storage
        import src.api.chat as chat_mod

        chat_mod._proposals[str(proposal.proposal_id)] = proposal

        mock_github_service.get_project_repository.return_value = ("owner", "repo")
        mock_github_service.create_issue.return_value = {
            "id": 100010,
            "number": 10,
            "node_id": "I_10",
            "html_url": "https://github.com/owner/repo/issues/10",
        }
        mock_github_service.add_issue_to_project.return_value = "PVTI_10"

        # Patch workflow functions to avoid side effects
        with (
            patch("src.api.chat.get_workflow_config", new_callable=AsyncMock, return_value=None),
            patch("src.api.chat.set_workflow_config", new_callable=AsyncMock),
            patch("src.api.chat.get_workflow_orchestrator") as mock_orch,
            patch("src.api.chat.get_agent_slugs", return_value=[]),
        ):
            mock_orch.return_value.assign_agent_for_status = AsyncMock()
            mock_orch.return_value.create_all_sub_issues = AsyncMock(return_value=[])
            resp = await client.post(
                f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
                json={},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "confirmed"

        # Cleanup
        chat_mod._proposals.pop(str(proposal.proposal_id), None)

    async def test_confirm_wrong_session(self, client, mock_session):
        """Proposal owned by different session → 404."""
        other_session_id = uuid4()
        proposal = _proposal(other_session_id)

        import src.api.chat as chat_mod

        chat_mod._proposals[str(proposal.proposal_id)] = proposal

        resp = await client.post(
            f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
            json={},
        )
        assert resp.status_code == 404

        chat_mod._proposals.pop(str(proposal.proposal_id), None)

    async def test_confirm_already_confirmed(self, client, mock_session):
        proposal = _proposal(mock_session.session_id)
        proposal.status = ProposalStatus.CONFIRMED

        import src.api.chat as chat_mod

        chat_mod._proposals[str(proposal.proposal_id)] = proposal

        mock_session.selected_project_id = "PVT_1"
        resp = await client.post(
            f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
            json={},
        )
        assert resp.status_code == 422

        chat_mod._proposals.pop(str(proposal.proposal_id), None)


# ── DELETE /chat/proposals/{id} ─────────────────────────────────────────────


class TestCancelProposal:
    async def test_cancel_success(self, client, mock_session):
        proposal = _proposal(mock_session.session_id)

        import src.api.chat as chat_mod

        chat_mod._proposals[str(proposal.proposal_id)] = proposal

        resp = await client.delete(f"/api/v1/chat/proposals/{proposal.proposal_id}")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Proposal cancelled"

        chat_mod._proposals.pop(str(proposal.proposal_id), None)

    async def test_cancel_not_found(self, client):
        resp = await client.delete("/api/v1/chat/proposals/nonexistent")
        assert resp.status_code == 404


# ── _resolve_repository (direct unit tests) ────────────────────────────────


class TestResolveRepository:
    """Direct tests for _resolve_repository covering all fallback branches."""

    async def test_no_project_selected_raises(self):
        from src.api.chat import _resolve_repository
        from src.exceptions import ValidationError

        session = UserSession(
            github_user_id="1",
            github_username="u",
            access_token="t",
            selected_project_id=None,
        )
        with pytest.raises(ValidationError, match="No project selected"):
            await _resolve_repository(session)

    async def test_project_repository_found(self):
        from src.api.chat import _resolve_repository

        session = UserSession(
            github_user_id="1",
            github_username="u",
            access_token="t",
            selected_project_id="PVT_1",
        )
        mock_svc = AsyncMock()
        mock_svc.get_project_repository.return_value = ("owner", "repo")
        with patch("src.services.github_projects.github_projects_service", mock_svc):
            result = await _resolve_repository(session)
        assert result == ("owner", "repo")

    async def test_workflow_config_fallback(self):
        from src.api.chat import _resolve_repository

        session = UserSession(
            github_user_id="1",
            github_username="u",
            access_token="t",
            selected_project_id="PVT_1",
        )
        mock_svc = AsyncMock()
        mock_svc.get_project_repository.return_value = None
        mock_config = MagicMock(repository_owner="wf_owner", repository_name="wf_repo")
        with (
            patch("src.services.github_projects.github_projects_service", mock_svc),
            patch(
                "src.services.workflow_orchestrator.get_workflow_config",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
        ):
            result = await _resolve_repository(session)
        assert result == ("wf_owner", "wf_repo")

    async def test_settings_default_fallback(self):
        from src.api.chat import _resolve_repository

        session = UserSession(
            github_user_id="1",
            github_username="u",
            access_token="t",
            selected_project_id="PVT_1",
        )
        mock_svc = AsyncMock()
        mock_svc.get_project_repository.return_value = None
        with (
            patch("src.services.github_projects.github_projects_service", mock_svc),
            patch(
                "src.services.workflow_orchestrator.get_workflow_config",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("src.config.get_settings") as mock_s,
        ):
            mock_s.return_value = MagicMock(
                default_repo_owner="def_owner", default_repo_name="def_repo"
            )
            result = await _resolve_repository(session)
        assert result == ("def_owner", "def_repo")

    async def test_all_fallbacks_fail_raises(self):
        from src.api.chat import _resolve_repository
        from src.exceptions import ValidationError

        session = UserSession(
            github_user_id="1",
            github_username="u",
            access_token="t",
            selected_project_id="PVT_1",
        )
        mock_svc = AsyncMock()
        mock_svc.get_project_repository.return_value = None
        with (
            patch("src.services.github_projects.github_projects_service", mock_svc),
            patch(
                "src.services.workflow_orchestrator.get_workflow_config",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("src.config.get_settings") as mock_s,
        ):
            mock_s.return_value = MagicMock(default_repo_owner=None, default_repo_name=None)
            with pytest.raises(ValidationError, match="No repository found"):
                await _resolve_repository(session)


class TestRetryPersist:
    async def test_retries_transient_operational_errors_then_succeeds(self):
        import sqlite3

        from src.api.chat import _PERSIST_BASE_DELAY, _retry_persist

        persist = AsyncMock(side_effect=[sqlite3.OperationalError("locked"), None])

        with patch("src.api.chat.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await _retry_persist(persist, context="message:test")

        assert persist.await_count == 2
        mock_sleep.assert_awaited_once_with(_PERSIST_BASE_DELAY)

    async def test_non_transient_errors_fail_fast(self):
        from src.api.chat import _retry_persist

        persist = AsyncMock(side_effect=RuntimeError("boom"))

        with patch("src.api.chat.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(RuntimeError, match="boom"):
                await _retry_persist(persist, context="message:test")

        mock_sleep.assert_not_awaited()

    async def test_exhausted_transient_errors_raise_persistence_error(self):
        import sqlite3

        from src.api.chat import _PERSIST_MAX_RETRIES, _retry_persist
        from src.exceptions import PersistenceError

        persist = AsyncMock(side_effect=sqlite3.OperationalError("locked"))

        with patch("src.api.chat.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(PersistenceError, match="Failed to persist message:test"):
                await _retry_persist(persist, context="message:test")

        assert persist.await_count == _PERSIST_MAX_RETRIES
        assert mock_sleep.await_count == _PERSIST_MAX_RETRIES - 1


class TestPostProcessAgentResponse:
    async def test_task_create_uses_user_content_when_description_is_missing(self, mock_session):
        from src.api.chat import _post_process_agent_response
        from src.models.chat import ActionType, ChatMessage, SenderType

        captured: dict[str, AITaskProposal] = {}

        async def capture(proposal: AITaskProposal) -> None:
            captured["proposal"] = proposal

        message = ChatMessage(
            session_id=mock_session.session_id,
            sender_type=SenderType.ASSISTANT,
            content="Drafted a task proposal.",
            action_type=ActionType.TASK_CREATE,
            action_data={"proposed_title": "Fix login redirect loop"},
        )

        with patch("src.api.chat.store_proposal", new=AsyncMock(side_effect=capture)):
            result = await _post_process_agent_response(
                session=mock_session,
                message=message,
                project_name="Roadmap",
                pipeline_id=None,
                file_urls=None,
                cached_projects=None,
                selected_project_id="PVT_1",
                user_content="Investigate why login redirects loop forever",
            )

        assert result.action_data is not None
        assert result.action_data["proposed_description"] == (
            "Investigate why login redirects loop forever"
        )
        assert result.action_data["status"] == ProposalStatus.PENDING.value
        assert captured["proposal"].original_input == "Investigate why login redirects loop forever"
        assert captured["proposal"].proposed_description == (
            "Investigate why login redirects loop forever"
        )


# ── cancel_proposal (direct unit tests) ─────────────────────────────────────


class TestCancelProposalDirect:
    """Direct tests for cancel_proposal covering wrong-session and happy path."""

    async def test_cancel_wrong_session(self, client, mock_session):
        """Proposal owned by different session → 404."""
        import src.api.chat as chat_mod

        other_id = uuid4()
        proposal = _proposal(other_id)
        chat_mod._proposals[str(proposal.proposal_id)] = proposal

        resp = await client.delete(f"/api/v1/chat/proposals/{proposal.proposal_id}")
        assert resp.status_code == 404
        chat_mod._proposals.pop(str(proposal.proposal_id), None)

    async def test_cancel_sets_status_cancelled(self, client, mock_session):
        """Should set proposal status to CANCELLED and add system message."""
        import src.api.chat as chat_mod

        proposal = _proposal(mock_session.session_id)
        await chat_mod.store_proposal(proposal)
        chat_mod._proposals[str(proposal.proposal_id)] = proposal

        resp = await client.delete(f"/api/v1/chat/proposals/{proposal.proposal_id}")
        assert resp.status_code == 200
        assert proposal.status == ProposalStatus.CANCELLED
        chat_mod._proposals.pop(str(proposal.proposal_id), None)
        reloaded = await chat_mod.get_proposal(str(proposal.proposal_id))
        assert reloaded is not None
        assert reloaded.status == ProposalStatus.CANCELLED

    async def test_cancel_succeeds_when_sqlite_update_fails(self, client, mock_session):
        import src.api.chat as chat_mod

        proposal = _proposal(mock_session.session_id)
        chat_mod._proposals[str(proposal.proposal_id)] = proposal

        with patch(
            "src.services.chat_store.update_proposal_status",
            new_callable=AsyncMock,
            side_effect=RuntimeError("sqlite unavailable"),
        ):
            resp = await client.delete(f"/api/v1/chat/proposals/{proposal.proposal_id}")

        assert resp.status_code == 200
        assert proposal.status == ProposalStatus.CANCELLED
        chat_mod._proposals.pop(str(proposal.proposal_id), None)


# ── confirm_proposal edge cases (direct) ─────────────────────────────────


class TestConfirmProposalEdgeCases:
    """Tests for confirm_proposal edge cases: expired, edits."""

    async def test_confirm_expired_proposal(self, client, mock_session):
        """Expired proposal → 422 with expiration message."""
        from datetime import timedelta

        import src.api.chat as chat_mod
        from src.utils import utcnow

        proposal = _proposal(mock_session.session_id)
        # Force expiration by setting expires_at in the past
        proposal.expires_at = utcnow() - timedelta(hours=1)
        chat_mod._proposals[str(proposal.proposal_id)] = proposal

        mock_session.selected_project_id = "PVT_1"
        resp = await client.post(
            f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
            json={},
        )
        assert resp.status_code == 422
        chat_mod._proposals.pop(str(proposal.proposal_id), None)

    async def test_get_proposal_loads_persisted_timestamps_and_edits(self, client, mock_session):
        """SQLite reload should preserve proposal lifecycle fields."""
        from datetime import timedelta

        import src.api.chat as chat_mod
        from src.utils import utcnow

        created_at = utcnow()
        proposal = _proposal(
            mock_session.session_id,
            status=ProposalStatus.EDITED,
            edited_title="Edited title",
            edited_description="Edited description",
            created_at=created_at,
            expires_at=created_at + timedelta(minutes=5),
        )

        await chat_mod.store_proposal(proposal)
        chat_mod._proposals.pop(str(proposal.proposal_id), None)

        loaded = await chat_mod.get_proposal(str(proposal.proposal_id))

        assert loaded is not None
        assert loaded.status == ProposalStatus.EDITED
        assert loaded.edited_title == "Edited title"
        assert loaded.edited_description == "Edited description"
        assert loaded.created_at.isoformat() == proposal.created_at.isoformat()
        assert loaded.expires_at.isoformat() == proposal.expires_at.isoformat()

    async def test_confirm_with_edited_title(
        self, client, mock_session, mock_github_service, mock_websocket_manager
    ):
        """Should apply edited title before creating issue."""
        import src.api.chat as chat_mod

        proposal = _proposal(mock_session.session_id)
        await chat_mod.store_proposal(proposal)
        chat_mod._proposals[str(proposal.proposal_id)] = proposal
        mock_session.selected_project_id = "PVT_1"

        mock_github_service.get_project_repository.return_value = ("owner", "repo")
        mock_github_service.create_issue.return_value = {
            "id": 100020,
            "number": 20,
            "node_id": "I_20",
            "html_url": "https://github.com/owner/repo/issues/20",
        }
        mock_github_service.add_issue_to_project.return_value = "PVTI_20"

        with (
            patch("src.api.chat.get_workflow_config", new_callable=AsyncMock, return_value=None),
            patch("src.api.chat.set_workflow_config", new_callable=AsyncMock),
            patch("src.api.chat.get_workflow_orchestrator") as mock_orch,
            patch("src.api.chat.get_agent_slugs", return_value=[]),
        ):
            mock_orch.return_value.assign_agent_for_status = AsyncMock()
            mock_orch.return_value.create_all_sub_issues = AsyncMock(return_value=[])
            resp = await client.post(
                f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
                json={"edited_title": "Better Title"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("edited", "confirmed")
        assert proposal.edited_title == "Better Title"
        chat_mod._proposals.pop(str(proposal.proposal_id), None)
        reloaded = await chat_mod.get_proposal(str(proposal.proposal_id))
        assert reloaded is not None
        assert reloaded.status == ProposalStatus.CONFIRMED
        assert reloaded.edited_title == "Better Title"
        chat_mod._proposals.pop(str(proposal.proposal_id), None)

    async def test_confirm_with_edited_description(
        self, client, mock_session, mock_github_service, mock_websocket_manager
    ):
        """Should apply edited description before creating issue."""
        import src.api.chat as chat_mod

        proposal = _proposal(mock_session.session_id)
        chat_mod._proposals[str(proposal.proposal_id)] = proposal
        mock_session.selected_project_id = "PVT_1"

        mock_github_service.get_project_repository.return_value = ("owner", "repo")
        mock_github_service.create_issue.return_value = {
            "id": 100021,
            "number": 21,
            "node_id": "I_21",
            "html_url": "https://github.com/owner/repo/issues/21",
        }
        mock_github_service.add_issue_to_project.return_value = "PVTI_21"

        with (
            patch("src.api.chat.get_workflow_config", new_callable=AsyncMock, return_value=None),
            patch("src.api.chat.set_workflow_config", new_callable=AsyncMock),
            patch("src.api.chat.get_workflow_orchestrator") as mock_orch,
            patch("src.api.chat.get_agent_slugs", return_value=[]),
        ):
            mock_orch.return_value.assign_agent_for_status = AsyncMock()
            mock_orch.return_value.create_all_sub_issues = AsyncMock(return_value=[])
            resp = await client.post(
                f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
                json={"edited_description": "Updated description text"},
            )

        assert resp.status_code == 200
        assert proposal.edited_description == "Updated description text"
        chat_mod._proposals.pop(str(proposal.proposal_id), None)

    async def test_confirm_proposal_applies_selected_pipeline_from_chat_mention(
        self, client, mock_session, mock_github_service, mock_websocket_manager
    ):
        """A selected chat pipeline must override project/user/default mappings on confirm."""
        import src.api.chat as chat_mod

        proposal = _proposal(mock_session.session_id, selected_pipeline_id="pipe-easy")
        chat_mod._proposals[str(proposal.proposal_id)] = proposal
        mock_session.selected_project_id = "PVT_1"

        mock_github_service.get_project_repository.return_value = ("owner", "repo")
        mock_github_service.create_issue.return_value = {
            "id": 100022,
            "number": 22,
            "node_id": "I_22",
            "html_url": "https://github.com/owner/repo/issues/22",
        }
        mock_github_service.add_issue_to_project.return_value = "PVTI_22"

        selected_mappings = {
            "Backlog": [
                {
                    "slug": "easy",
                    "display_name": "Easy",
                }
            ]
        }

        with (
            patch("src.api.chat.get_workflow_config", new_callable=AsyncMock, return_value=None),
            patch("src.api.chat.set_workflow_config", new_callable=AsyncMock) as mock_set_config,
            patch("src.api.chat.get_workflow_orchestrator") as mock_orch,
            patch("src.api.chat.get_agent_slugs", return_value=["easy"]),
            patch(
                "src.services.workflow_orchestrator.config.load_pipeline_as_agent_mappings",
                new_callable=AsyncMock,
                return_value=(selected_mappings, "Easy", {}, {}),
            ) as mock_load_selected,
            patch(
                "src.services.workflow_orchestrator.config.resolve_project_pipeline_mappings",
                new_callable=AsyncMock,
            ) as mock_resolve_fallback,
        ):
            mock_orch.return_value.assign_agent_for_status = AsyncMock()
            mock_orch.return_value.create_all_sub_issues = AsyncMock(return_value=[])

            resp = await client.post(
                f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
                json={},
            )

        assert resp.status_code == 200
        mock_load_selected.assert_awaited_once_with(
            "PVT_1",
            "pipe-easy",
            github_user_id=mock_session.github_user_id,
        )
        mock_resolve_fallback.assert_not_called()
        set_config_call = mock_set_config.await_args_list[-1]
        assert set_config_call.args[1].agent_mappings == selected_mappings
        create_subissues_call = mock_orch.return_value.create_all_sub_issues.await_args
        assert create_subissues_call is not None
        create_subissues_ctx = create_subissues_call.args[0]
        assert create_subissues_ctx.selected_pipeline_id == "pipe-easy"
        assert create_subissues_ctx.config.agent_mappings == selected_mappings
        assert proposal.pipeline_name == "Easy"
        assert proposal.pipeline_source == "pipeline"
        chat_mod._proposals.pop(str(proposal.proposal_id), None)

    async def test_feature_request_generation_error(
        self, client, mock_session, mock_chat_agent_service
    ):
        """Feature request recommendation generation failure → error message."""
        mock_session.selected_project_id = "PVT_1"

        from src.models.chat import ChatMessage, SenderType

        error_response = ChatMessage(
            session_id=mock_session.session_id,
            sender_type=SenderType.ASSISTANT,
            content="I couldn't generate a recommendation from your request. Please try again.",
        )
        mock_chat_agent_service.run.return_value = error_response

        resp = await client.post("/api/v1/chat/messages", json={"content": "add dark mode"})
        assert resp.status_code == 200
        assert "couldn't generate" in resp.json()["content"].lower()


# ── Preserve full description tests ─────────────────────────────────────────


class TestConfirmProposalPreservesFullDescription:
    """T006, T010, T016, T018, T021: Verify confirm_proposal passes full descriptions unchanged."""

    async def test_full_description_passed_unchanged(
        self, client, mock_session, mock_github_service, mock_websocket_manager
    ):
        """T006: confirm_proposal passes the full final_description to create_issue(body=...)."""
        import src.api.chat as chat_mod

        long_desc = "A" * 10_000
        proposal = _proposal(mock_session.session_id, proposed_description=long_desc)
        chat_mod._proposals[str(proposal.proposal_id)] = proposal
        mock_session.selected_project_id = "PVT_1"

        mock_github_service.get_project_repository.return_value = ("owner", "repo")
        mock_github_service.create_issue.return_value = {
            "id": 100030,
            "number": 30,
            "node_id": "I_30",
            "html_url": "https://github.com/owner/repo/issues/30",
        }
        mock_github_service.add_issue_to_project.return_value = "PVTI_30"

        with (
            patch("src.api.chat.get_workflow_config", new_callable=AsyncMock, return_value=None),
            patch("src.api.chat.set_workflow_config", new_callable=AsyncMock),
            patch("src.api.chat.get_workflow_orchestrator") as mock_orch,
            patch("src.api.chat.get_agent_slugs", return_value=[]),
        ):
            mock_orch.return_value.assign_agent_for_status = AsyncMock()
            mock_orch.return_value.create_all_sub_issues = AsyncMock(return_value=[])
            resp = await client.post(
                f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
                json={},
            )

        assert resp.status_code == 200
        # Verify the full body was passed to create_issue
        call_kwargs = mock_github_service.create_issue.call_args
        assert call_kwargs.kwargs["body"] == long_desc
        chat_mod._proposals.pop(str(proposal.proposal_id), None)

    @pytest.mark.parametrize("length", [256, 1024, 4096, 32768, 65536])
    async def test_boundary_length_descriptions_preserved(
        self, client, mock_session, mock_github_service, mock_websocket_manager, length
    ):
        """T010: Parametrized boundary-length tests for proposal path."""
        import src.api.chat as chat_mod

        desc = "B" * length
        proposal = _proposal(mock_session.session_id, proposed_description=desc)
        chat_mod._proposals[str(proposal.proposal_id)] = proposal
        mock_session.selected_project_id = "PVT_1"

        mock_github_service.get_project_repository.return_value = ("owner", "repo")
        mock_github_service.create_issue.return_value = {
            "id": 100031,
            "number": 31,
            "node_id": "I_31",
            "html_url": "https://github.com/owner/repo/issues/31",
        }
        mock_github_service.add_issue_to_project.return_value = "PVTI_31"

        with (
            patch("src.api.chat.get_workflow_config", new_callable=AsyncMock, return_value=None),
            patch("src.api.chat.set_workflow_config", new_callable=AsyncMock),
            patch("src.api.chat.get_workflow_orchestrator") as mock_orch,
            patch("src.api.chat.get_agent_slugs", return_value=[]),
        ):
            mock_orch.return_value.assign_agent_for_status = AsyncMock()
            mock_orch.return_value.create_all_sub_issues = AsyncMock(return_value=[])
            resp = await client.post(
                f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
                json={},
            )

        assert resp.status_code == 200
        call_kwargs = mock_github_service.create_issue.call_args
        assert call_kwargs.kwargs["body"] == desc
        assert len(call_kwargs.kwargs["body"]) == length
        chat_mod._proposals.pop(str(proposal.proposal_id), None)

    async def test_oversized_description_returns_422(
        self, client, mock_session, mock_github_service, mock_websocket_manager
    ):
        """T016: confirm_proposal returns HTTP 422 when description exceeds 65,536 chars."""
        import src.api.chat as chat_mod

        oversized_desc = "C" * 65_537
        proposal = _proposal(mock_session.session_id, proposed_description=oversized_desc[:65_536])
        # Bypass Pydantic max_length by setting the field directly
        object.__setattr__(proposal, "proposed_description", oversized_desc)
        chat_mod._proposals[str(proposal.proposal_id)] = proposal
        mock_session.selected_project_id = "PVT_1"

        mock_github_service.get_project_repository.return_value = ("owner", "repo")

        resp = await client.post(
            f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
            json={},
        )
        assert resp.status_code == 422
        resp_json = resp.json()
        assert "exceeds" in resp_json["error"].lower()
        # Verify structured details payload is preserved (not lost by
        # exception re-wrapping) per the issue-creation contract.
        assert resp_json["details"]["body_length"] == 65_537
        assert resp_json["details"]["max_length"] == 65_536
        chat_mod._proposals.pop(str(proposal.proposal_id), None)

    async def test_exactly_65537_chars_fails(
        self, client, mock_session, mock_github_service, mock_websocket_manager
    ):
        """T018: Body at exactly 65,537 chars fails with 422."""
        import src.api.chat as chat_mod

        desc = "D" * 65_537
        proposal = _proposal(mock_session.session_id, proposed_description="short")
        object.__setattr__(proposal, "proposed_description", desc)
        chat_mod._proposals[str(proposal.proposal_id)] = proposal
        mock_session.selected_project_id = "PVT_1"

        mock_github_service.get_project_repository.return_value = ("owner", "repo")

        resp = await client.post(
            f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
            json={},
        )
        assert resp.status_code == 422
        # Verify the 422 response includes the structured details payload.
        resp_json = resp.json()
        assert resp_json["details"]["body_length"] == 65_537
        assert resp_json["details"]["max_length"] == 65_536
        chat_mod._proposals.pop(str(proposal.proposal_id), None)

    async def test_rich_markdown_description_preserved(
        self, client, mock_session, mock_github_service, mock_websocket_manager
    ):
        """T021: Rich markdown description is preserved through proposal path."""
        import src.api.chat as chat_mod

        markdown_desc = (
            "# Feature Request\n\n"
            "## Overview\n\n"
            "- bullet point 1\n"
            "- bullet point 2\n"
            "  - nested bullet\n\n"
            "```python\ndef hello():\n    print('world')\n```\n\n"
            "> blockquote with **bold** and *italic*\n\n"
            "| Header1 | Header2 |\n|---------|----------|\n| cell1 | cell2 |\n\n"
            "[link](https://example.com) and `inline code`\n\n"
            "---\n\n"
            "~~strikethrough~~ and 🚀 emoji\n"
        )
        proposal = _proposal(mock_session.session_id, proposed_description=markdown_desc)
        chat_mod._proposals[str(proposal.proposal_id)] = proposal
        mock_session.selected_project_id = "PVT_1"

        mock_github_service.get_project_repository.return_value = ("owner", "repo")
        mock_github_service.create_issue.return_value = {
            "id": 100032,
            "number": 32,
            "node_id": "I_32",
            "html_url": "https://github.com/owner/repo/issues/32",
        }
        mock_github_service.add_issue_to_project.return_value = "PVTI_32"

        with (
            patch("src.api.chat.get_workflow_config", new_callable=AsyncMock, return_value=None),
            patch("src.api.chat.set_workflow_config", new_callable=AsyncMock),
            patch("src.api.chat.get_workflow_orchestrator") as mock_orch,
            patch("src.api.chat.get_agent_slugs", return_value=[]),
        ):
            mock_orch.return_value.assign_agent_for_status = AsyncMock()
            mock_orch.return_value.create_all_sub_issues = AsyncMock(return_value=[])
            resp = await client.post(
                f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
                json={},
            )

        assert resp.status_code == 200
        call_kwargs = mock_github_service.create_issue.call_args
        assert call_kwargs.kwargs["body"] == markdown_desc
        chat_mod._proposals.pop(str(proposal.proposal_id), None)


class TestConfirmProposalFallbacks:
    async def test_confirm_expired_proposal_ignores_sqlite_update_failure(
        self, client, mock_session
    ):
        from datetime import timedelta

        import src.api.chat as chat_mod
        from src.utils import utcnow

        proposal = _proposal(mock_session.session_id)
        proposal.expires_at = utcnow() - timedelta(hours=1)
        chat_mod._proposals[str(proposal.proposal_id)] = proposal
        mock_session.selected_project_id = "PVT_1"

        with patch(
            "src.services.chat_store.update_proposal_status",
            new_callable=AsyncMock,
            side_effect=RuntimeError("sqlite unavailable"),
        ):
            resp = await client.post(
                f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
                json={},
            )

        assert resp.status_code == 422
        assert proposal.status == ProposalStatus.CANCELLED
        chat_mod._proposals.pop(str(proposal.proposal_id), None)

    async def test_confirm_continues_when_sqlite_status_update_fails(
        self, client, mock_session, mock_github_service, mock_websocket_manager
    ):
        import src.api.chat as chat_mod

        proposal = _proposal(mock_session.session_id)
        chat_mod._proposals[str(proposal.proposal_id)] = proposal
        mock_session.selected_project_id = "PVT_1"

        mock_github_service.get_project_repository.return_value = ("owner", "repo")
        mock_github_service.create_issue.return_value = {
            "id": 100033,
            "number": 33,
            "node_id": "I_33",
            "html_url": "https://github.com/owner/repo/issues/33",
        }
        mock_github_service.add_issue_to_project.return_value = "PVTI_33"

        empty_pipeline_result = SimpleNamespace(
            agent_mappings={},
            source="project",
            pipeline_name=None,
            pipeline_id=None,
            stage_execution_modes={},
            group_mappings={},
        )

        with (
            patch(
                "src.services.chat_store.update_proposal_status",
                new_callable=AsyncMock,
                side_effect=RuntimeError("sqlite unavailable"),
            ) as mock_update_status,
            patch(
                "src.config.get_settings",
                return_value=SimpleNamespace(default_assignee="copilot-swe-agent"),
            ),
            patch("src.api.chat.get_workflow_config", new_callable=AsyncMock, return_value=None),
            patch("src.api.chat.set_workflow_config", new_callable=AsyncMock) as mock_set_config,
            patch("src.api.chat.get_workflow_orchestrator") as mock_orch,
            patch("src.api.chat.get_agent_slugs", return_value=[]),
            patch(
                "src.services.workflow_orchestrator.config.resolve_project_pipeline_mappings",
                new_callable=AsyncMock,
                return_value=empty_pipeline_result,
            ),
            patch(
                "src.services.copilot_polling.ensure_polling_started",
                new_callable=AsyncMock,
            ),
        ):
            mock_orch.return_value.assign_agent_for_status = AsyncMock()
            mock_orch.return_value.create_all_sub_issues = AsyncMock(return_value=[])

            resp = await client.post(
                f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
                json={},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"
        assert proposal.status == ProposalStatus.CONFIRMED
        mock_update_status.assert_awaited_once()
        assert mock_set_config.await_args_list[0].args[1].copilot_assignee == "copilot-swe-agent"
        assert (
            mock_websocket_manager.broadcast_to_project.await_args.args[1]["type"] == "task_created"
        )
        chat_mod._proposals.pop(str(proposal.proposal_id), None)

    async def test_confirm_updates_existing_config_and_precreates_subissues(
        self, client, mock_session, mock_github_service, mock_websocket_manager
    ):
        import src.api.chat as chat_mod

        proposal = _proposal(mock_session.session_id)
        chat_mod._proposals[str(proposal.proposal_id)] = proposal
        mock_session.selected_project_id = "PVT_1"

        mock_github_service.get_project_repository.return_value = ("owner", "repo")
        mock_github_service.create_issue.return_value = {
            "id": 100037,
            "number": 37,
            "node_id": "I_37",
            "html_url": "https://github.com/owner/repo/issues/37",
        }
        mock_github_service.add_issue_to_project.return_value = "PVTI_37"

        existing_config = SimpleNamespace(
            repository_owner="old-owner",
            repository_name="old-repo",
            copilot_assignee="",
            status_backlog="Backlog",
            agent_mappings={},
        )
        pipeline_result = SimpleNamespace(
            agent_mappings={"Backlog": [{"slug": "copilot-swe-agent"}]},
            source="project",
            pipeline_name="Fallback pipeline",
            pipeline_id=None,
            stage_execution_modes={},
            group_mappings={},
        )
        effective_settings = SimpleNamespace(
            ai=SimpleNamespace(
                model="gpt-4.1-mini",
                agent_model="o4-mini",
                reasoning_effort="high",
            )
        )
        agent_sub_issues = [{"slug": "copilot-swe-agent", "issue_number": 3701}]

        with (
            patch(
                "src.config.get_settings",
                return_value=SimpleNamespace(default_assignee="copilot-swe-agent"),
            ),
            patch(
                "src.api.chat.get_workflow_config",
                new_callable=AsyncMock,
                return_value=existing_config,
            ),
            patch("src.api.chat.set_workflow_config", new_callable=AsyncMock) as mock_set_config,
            patch("src.api.chat.get_workflow_orchestrator") as mock_orch,
            patch("src.api.chat.get_agent_slugs", return_value=["copilot-swe-agent"]),
            patch(
                "src.api.chat.get_effective_user_settings",
                new_callable=AsyncMock,
                return_value=effective_settings,
            ),
            patch(
                "src.services.workflow_orchestrator.config.resolve_project_pipeline_mappings",
                new_callable=AsyncMock,
                return_value=pipeline_result,
            ),
            patch(
                "src.services.workflow_orchestrator.set_pipeline_state"
            ) as mock_set_pipeline_state,
            patch(
                "src.services.copilot_polling.ensure_polling_started",
                new_callable=AsyncMock,
            ),
        ):
            mock_orch.return_value.create_all_sub_issues = AsyncMock(return_value=agent_sub_issues)
            mock_orch.return_value.assign_agent_for_status = AsyncMock()

            resp = await client.post(
                f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
                json={},
            )

        assert resp.status_code == 200
        assert existing_config.repository_owner == "owner"
        assert existing_config.repository_name == "repo"
        assert existing_config.copilot_assignee == "copilot-swe-agent"
        assert mock_set_config.await_args.args[1].agent_mappings == pipeline_result.agent_mappings
        create_subissues_call = mock_orch.return_value.create_all_sub_issues.await_args
        assert create_subissues_call is not None
        create_ctx = create_subissues_call.args[0]
        assert create_ctx.user_chat_model == "gpt-4.1-mini"
        assert create_ctx.user_agent_model == "o4-mini"
        assert create_ctx.user_reasoning_effort == "high"
        pipeline_state = mock_set_pipeline_state.call_args.args[1]
        assert pipeline_state.agents == ["copilot-swe-agent"]
        assert pipeline_state.agent_sub_issues == agent_sub_issues
        assert mock_websocket_manager.broadcast_to_project.await_count == 2
        chat_mod._proposals.pop(str(proposal.proposal_id), None)

    async def test_confirm_selected_pipeline_falls_back_when_pipeline_missing(
        self, client, mock_session, mock_github_service
    ):
        import src.api.chat as chat_mod

        proposal = _proposal(mock_session.session_id, selected_pipeline_id="pipe-missing")
        chat_mod._proposals[str(proposal.proposal_id)] = proposal
        mock_session.selected_project_id = "PVT_1"

        mock_github_service.get_project_repository.return_value = ("owner", "repo")
        mock_github_service.create_issue.return_value = {
            "id": 100034,
            "number": 34,
            "node_id": "I_34",
            "html_url": "https://github.com/owner/repo/issues/34",
        }
        mock_github_service.add_issue_to_project.return_value = "PVTI_34"

        fallback_result = SimpleNamespace(
            agent_mappings={"Backlog": [{"slug": "fallback-agent", "display_name": "Fallback"}]},
            source="project",
            pipeline_name="Fallback pipeline",
            pipeline_id=None,
            stage_execution_modes={},
            group_mappings={},
        )

        with (
            patch("src.api.chat.get_workflow_config", new_callable=AsyncMock, return_value=None),
            patch("src.api.chat.set_workflow_config", new_callable=AsyncMock) as mock_set_config,
            patch("src.api.chat.get_workflow_orchestrator") as mock_orch,
            patch("src.api.chat.get_agent_slugs", return_value=[]),
            patch(
                "src.services.workflow_orchestrator.config.load_pipeline_as_agent_mappings",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_load_selected,
            patch(
                "src.services.workflow_orchestrator.config.resolve_project_pipeline_mappings",
                new_callable=AsyncMock,
                return_value=fallback_result,
            ) as mock_resolve_fallback,
            patch(
                "src.services.copilot_polling.ensure_polling_started",
                new_callable=AsyncMock,
            ),
        ):
            mock_orch.return_value.assign_agent_for_status = AsyncMock()
            mock_orch.return_value.create_all_sub_issues = AsyncMock(return_value=[])

            resp = await client.post(
                f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
                json={},
            )

        assert resp.status_code == 200
        mock_load_selected.assert_awaited_once_with(
            "PVT_1",
            "pipe-missing",
            github_user_id=mock_session.github_user_id,
        )
        mock_resolve_fallback.assert_awaited_once_with("PVT_1", mock_session.github_user_id)
        assert (
            mock_set_config.await_args_list[-1].args[1].agent_mappings
            == fallback_result.agent_mappings
        )
        assert proposal.pipeline_name == "Fallback pipeline"
        assert proposal.pipeline_source == "project"
        chat_mod._proposals.pop(str(proposal.proposal_id), None)

    async def test_confirm_broadcasts_agent_assignment_and_starts_polling(
        self, client, mock_session, mock_github_service, mock_websocket_manager
    ):
        import src.api.chat as chat_mod

        proposal = _proposal(mock_session.session_id)
        chat_mod._proposals[str(proposal.proposal_id)] = proposal
        mock_session.selected_project_id = "PVT_1"

        mock_github_service.get_project_repository.return_value = ("owner", "repo")
        mock_github_service.create_issue.return_value = {
            "id": 100035,
            "number": 35,
            "node_id": "I_35",
            "html_url": "https://github.com/owner/repo/issues/35",
        }
        mock_github_service.add_issue_to_project.return_value = "PVTI_35"

        empty_pipeline_result = SimpleNamespace(
            agent_mappings={},
            source="project",
            pipeline_name=None,
            pipeline_id=None,
            stage_execution_modes={},
            group_mappings={},
        )

        with (
            patch("src.api.chat.get_workflow_config", new_callable=AsyncMock, return_value=None),
            patch("src.api.chat.set_workflow_config", new_callable=AsyncMock),
            patch("src.api.chat.get_workflow_orchestrator") as mock_orch,
            patch("src.api.chat.get_agent_slugs", return_value=["copilot-swe-agent"]),
            patch(
                "src.services.workflow_orchestrator.config.resolve_project_pipeline_mappings",
                new_callable=AsyncMock,
                return_value=empty_pipeline_result,
            ),
            patch(
                "src.services.copilot_polling.ensure_polling_started",
                new_callable=AsyncMock,
            ) as mock_polling,
        ):
            mock_orch.return_value.assign_agent_for_status = AsyncMock()
            mock_orch.return_value.create_all_sub_issues = AsyncMock(return_value=[])

            resp = await client.post(
                f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
                json={},
            )

        assert resp.status_code == 200
        assert mock_websocket_manager.broadcast_to_project.await_count == 2
        assert (
            mock_websocket_manager.broadcast_to_project.await_args_list[0].args[1]["type"]
            == "task_created"
        )
        assert mock_websocket_manager.broadcast_to_project.await_args_list[1].args[1] == {
            "type": "agent_assigned",
            "issue_number": 35,
            "agent_name": "copilot-swe-agent",
            "status": "Backlog",
        }
        mock_polling.assert_awaited_once_with(
            access_token=mock_session.access_token,
            project_id="PVT_1",
            owner="owner",
            repo="repo",
            caller="confirm_proposal",
        )
        chat_mod._proposals.pop(str(proposal.proposal_id), None)

    async def test_confirm_returns_success_when_agent_assignment_fails(
        self, client, mock_session, mock_github_service, mock_websocket_manager
    ):
        import src.api.chat as chat_mod

        proposal = _proposal(mock_session.session_id)
        chat_mod._proposals[str(proposal.proposal_id)] = proposal
        mock_session.selected_project_id = "PVT_1"

        mock_github_service.get_project_repository.return_value = ("owner", "repo")
        mock_github_service.create_issue.return_value = {
            "id": 100036,
            "number": 36,
            "node_id": "I_36",
            "html_url": "https://github.com/owner/repo/issues/36",
        }
        mock_github_service.add_issue_to_project.return_value = "PVTI_36"

        empty_pipeline_result = SimpleNamespace(
            agent_mappings={},
            source="project",
            pipeline_name=None,
            pipeline_id=None,
            stage_execution_modes={},
            group_mappings={},
        )

        with (
            patch("src.api.chat.get_workflow_config", new_callable=AsyncMock, return_value=None),
            patch("src.api.chat.set_workflow_config", new_callable=AsyncMock),
            patch("src.api.chat.get_workflow_orchestrator") as mock_orch,
            patch("src.api.chat.get_agent_slugs", return_value=[]),
            patch(
                "src.services.workflow_orchestrator.config.resolve_project_pipeline_mappings",
                new_callable=AsyncMock,
                return_value=empty_pipeline_result,
            ),
            patch(
                "src.services.copilot_polling.ensure_polling_started",
                new_callable=AsyncMock,
            ) as mock_polling,
        ):
            mock_orch.return_value.create_all_sub_issues = AsyncMock(return_value=[])
            mock_orch.return_value.assign_agent_for_status = AsyncMock(
                side_effect=RuntimeError("assignment failed")
            )

            resp = await client.post(
                f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
                json={},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"
        assert mock_websocket_manager.broadcast_to_project.await_count == 1
        assert (
            mock_websocket_manager.broadcast_to_project.await_args_list[0].args[1]["type"]
            == "task_created"
        )
        mock_polling.assert_not_awaited()
        chat_mod._proposals.pop(str(proposal.proposal_id), None)


# ── Regression: error messages MUST NOT leak exception details ──────────────


class TestErrorMessageSanitization:
    """Bug-bash regression: chat error messages must not expose internal
    exception details to the end user (information leakage)."""

    async def test_agent_command_error_does_not_leak_exception(
        self, client, mock_session, mock_ai_agent_service
    ):
        """#agent command errors must not include raw exception text."""
        mock_session.selected_project_id = "PVT_1"
        with patch(
            "src.services.agent_creator.handle_agent_command",
            side_effect=RuntimeError("secret db error"),
        ):
            with patch("src.services.agent_creator.get_active_session", return_value=None):
                resp = await client.post(
                    "/api/v1/chat/messages", json={"content": "#agent create foo"}
                )
        assert resp.status_code == 200
        content = resp.json()["content"]
        assert "secret db error" not in content
        assert "unexpected error" in content.lower() or "Error" in content

    async def test_task_generation_error_does_not_leak_exception(
        self, client, mock_session, mock_chat_agent_service
    ):
        """Task generation failure message must not include raw exception."""
        mock_session.selected_project_id = "PVT_1"

        from src.models.chat import ChatMessage, SenderType

        error_response = ChatMessage(
            session_id=mock_session.session_id,
            sender_type=SenderType.ASSISTANT,
            content="I encountered an error processing your request (RuntimeError). Please try again.",
        )
        mock_chat_agent_service.run.return_value = error_response

        resp = await client.post("/api/v1/chat/messages", json={"content": "do something"})
        assert resp.status_code == 200
        content = resp.json()["content"]
        assert "connection refused" not in content
        assert "ai-backend" not in content

    async def test_recommendation_error_does_not_leak_exception(
        self, client, mock_session, mock_chat_agent_service
    ):
        """Issue recommendation failure message must not include raw exception."""
        mock_session.selected_project_id = "PVT_1"

        from src.models.chat import ChatMessage, SenderType

        error_response = ChatMessage(
            session_id=mock_session.session_id,
            sender_type=SenderType.ASSISTANT,
            content="I encountered an error processing your request (RuntimeError). Please try again.",
        )
        mock_chat_agent_service.run.return_value = error_response

        resp = await client.post("/api/v1/chat/messages", json={"content": "I want a new feature"})
        assert resp.status_code == 200
        content = resp.json()["content"]
        assert "model_endpoint" not in content
        assert "timed out" not in content

    async def test_confirm_proposal_error_does_not_leak_exception(
        self, client, mock_session, mock_github_service
    ):
        """confirm_proposal must not leak internal exception details."""
        import src.api.chat as chat_mod

        mock_session.selected_project_id = "PVT_1"
        proposal = _proposal(mock_session.session_id)
        chat_mod._proposals[str(proposal.proposal_id)] = proposal

        mock_github_service.create_issue.side_effect = RuntimeError(
            "GraphQL error: token expired for user 12345"
        )

        with (
            patch(
                "src.api.chat.resolve_repository", new_callable=AsyncMock, return_value=("o", "r")
            ),
        ):
            resp = await client.post(
                f"/api/v1/chat/proposals/{proposal.proposal_id}/confirm",
                json={},
            )
        assert resp.status_code == 422
        body = resp.json()
        # Must not leak the internal error message
        assert "token expired" not in str(body)
        assert "12345" not in str(body)
        chat_mod._proposals.pop(str(proposal.proposal_id), None)


# ── POST /chat/upload — path-traversal regression ──────────────────────────


class TestUploadFilePathTraversal:
    """Regression tests for path-traversal vulnerability in file upload (bug-bash)."""

    async def test_path_traversal_filename_is_sanitised(self, client):
        """A filename containing '../' should be stripped to its base component."""
        import io

        file_content = b"harmless"
        resp = await client.post(
            "/api/v1/chat/upload",
            files={"file": ("../../etc/passwd.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert resp.status_code == 200
        body = resp.json()
        # The traversal components must not appear in the returned URL
        assert "../" not in body["file_url"]
        assert "passwd.txt" in body["file_url"]

    async def test_normal_filename_accepted(self, client):
        """A simple filename should be accepted without modification."""
        import io

        file_content = b"hello"
        resp = await client.post(
            "/api/v1/chat/upload",
            files={"file": ("report.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "report.txt" in body["file_url"]
        assert body["filename"] == "report.txt"

    async def test_blocked_type_rejected(self, client):
        """Executable file extensions should be rejected."""
        import io

        resp = await client.post(
            "/api/v1/chat/upload",
            files={"file": ("malware.exe", io.BytesIO(b"\x00"), "application/octet-stream")},
        )
        assert resp.status_code == 415
        assert resp.json()["error_code"] == "unsupported_type"


class TestUploadFileValidationDirect:
    async def test_missing_filename_returns_no_file_error(self, mock_session):
        from src.api.chat import upload_file

        resp = await upload_file(file=_make_upload_file(None, b"hello"), session=mock_session)

        assert isinstance(resp, JSONResponse)
        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            "filename": "",
            "error": "No file provided",
            "error_code": "no_file",
        }

    async def test_unknown_extension_is_rejected(self, mock_session):
        from src.api.chat import upload_file

        resp = await upload_file(
            file=_make_upload_file("notes.xyz", b"hello"), session=mock_session
        )

        assert isinstance(resp, JSONResponse)
        assert resp.status_code == 415
        assert json.loads(resp.body)["error_code"] == "unsupported_type"

    async def test_empty_file_is_rejected(self, mock_session):
        from src.api.chat import upload_file

        resp = await upload_file(file=_make_upload_file("notes.txt", b""), session=mock_session)

        assert isinstance(resp, JSONResponse)
        assert resp.status_code == 400
        assert json.loads(resp.body)["error_code"] == "empty_file"

    async def test_oversized_file_is_rejected(self, mock_session):
        from src.api.chat import upload_file

        with patch("src.api.chat.MAX_FILE_SIZE_BYTES", 4):
            resp = await upload_file(
                file=_make_upload_file("notes.txt", b"12345"),
                session=mock_session,
            )

        assert isinstance(resp, JSONResponse)
        assert resp.status_code == 413
        assert json.loads(resp.body)["error_code"] == "file_too_large"

    async def test_missing_content_type_defaults_to_octet_stream(self, mock_session):
        from src.api.chat import upload_file

        resp = await upload_file(
            file=_make_upload_file("notes.txt", b"hello", content_type=None),
            session=mock_session,
        )

        assert not isinstance(resp, JSONResponse)
        assert resp.content_type == "application/octet-stream"
        assert resp.file_size == 5
        stored_path = Path(tempfile.gettempdir()) / "chat-uploads" / Path(resp.file_url).name
        try:
            assert stored_path.read_bytes() == b"hello"
        finally:
            stored_path.unlink(missing_ok=True)

    async def test_invalid_resolved_path_is_rejected(self, mock_session):
        import src.api.chat as chat_mod

        with patch.object(
            chat_mod.Path,
            "resolve",
            autospec=True,
            side_effect=[
                Path(tempfile.gettempdir()) / "outside",
                Path(tempfile.gettempdir()) / "chat-uploads",
            ],
        ):
            resp = await chat_mod.upload_file(
                file=_make_upload_file("report.txt", b"hello"),
                session=mock_session,
            )

        assert isinstance(resp, JSONResponse)
        assert resp.status_code == 400
        assert json.loads(resp.body)["error_code"] == "invalid_filename"


# ── Conversation CRUD API endpoints ─────────────────────────────────────────


class TestConversationAPI:
    """Tests for conversation CRUD endpoints in the chat API."""

    async def test_create_conversation(self, client):
        """POST /chat/conversations creates a new conversation."""
        resp = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "My Chat"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "My Chat"
        assert "conversation_id" in data
        assert "session_id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_conversation_default_title(self, client):
        """POST /chat/conversations with no title uses 'New Chat' default."""
        resp = await client.post(
            "/api/v1/chat/conversations",
            json={},
        )
        assert resp.status_code == 201
        assert resp.json()["title"] == "New Chat"

    async def test_list_conversations_empty(self, client):
        """GET /chat/conversations returns empty list when no conversations exist."""
        resp = await client.get("/api/v1/chat/conversations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["conversations"] == []

    async def test_list_conversations_returns_created(self, client):
        """GET /chat/conversations returns previously created conversations."""
        await client.post("/api/v1/chat/conversations", json={"title": "Chat A"})
        await client.post("/api/v1/chat/conversations", json={"title": "Chat B"})

        resp = await client.get("/api/v1/chat/conversations")
        assert resp.status_code == 200
        conversations = resp.json()["conversations"]
        assert len(conversations) == 2
        titles = {c["title"] for c in conversations}
        assert titles == {"Chat A", "Chat B"}

    async def test_update_conversation_title(self, client):
        """PATCH /chat/conversations/{id} updates the title."""
        create_resp = await client.post("/api/v1/chat/conversations", json={"title": "Old Title"})
        conv_id = create_resp.json()["conversation_id"]

        resp = await client.patch(
            f"/api/v1/chat/conversations/{conv_id}",
            json={"title": "New Title"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    async def test_update_conversation_not_found(self, client):
        """PATCH /chat/conversations/{id} returns 404 for nonexistent conversation."""
        resp = await client.patch(
            "/api/v1/chat/conversations/nonexistent-id",
            json={"title": "New Title"},
        )
        assert resp.status_code == 404

    async def test_delete_conversation(self, client):
        """DELETE /chat/conversations/{id} removes the conversation."""
        create_resp = await client.post("/api/v1/chat/conversations", json={"title": "To Delete"})
        conv_id = create_resp.json()["conversation_id"]

        resp = await client.delete(f"/api/v1/chat/conversations/{conv_id}")
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

        # Verify it's gone
        list_resp = await client.get("/api/v1/chat/conversations")
        assert len(list_resp.json()["conversations"]) == 0

    async def test_delete_conversation_not_found(self, client):
        """DELETE /chat/conversations/{id} returns 404 for nonexistent conversation."""
        resp = await client.delete("/api/v1/chat/conversations/nonexistent-id")
        assert resp.status_code == 404

    async def test_get_messages_with_conversation_filter(self, client):
        """GET /chat/messages?conversation_id=X returns only that conversation's messages."""
        # With no messages, filtering by conversation_id returns empty
        resp_filtered = await client.get(
            "/api/v1/chat/messages",
            params={"conversation_id": "conv-nonexistent"},
        )
        assert resp_filtered.status_code == 200
        assert resp_filtered.json()["total"] == 0
        assert resp_filtered.json()["messages"] == []

        # Without filter, also returns empty (no messages yet)
        resp_all = await client.get("/api/v1/chat/messages")
        assert resp_all.status_code == 200
        assert resp_all.json()["total"] == 0

    async def test_clear_messages_with_conversation_id(self, client):
        """DELETE /chat/messages?conversation_id=X clears only that conversation's messages."""
        resp = await client.delete(
            "/api/v1/chat/messages",
            params={"conversation_id": "conv-1"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Chat history cleared"


class TestConversationOwnership:
    """Tests verifying conversation ownership checks prevent cross-session access."""

    async def test_update_other_sessions_conversation_returns_404(self, client, mock_db):
        """PATCH on another session's conversation returns 404 to prevent enumeration."""
        from src.services import chat_store

        # Create a conversation belonging to a different session
        await chat_store.save_conversation(
            mock_db, "other-session-id", "foreign-conv", "Foreign Chat"
        )

        resp = await client.patch(
            "/api/v1/chat/conversations/foreign-conv",
            json={"title": "Hijacked!"},
        )
        assert resp.status_code == 404

    async def test_delete_other_sessions_conversation_returns_404(self, client, mock_db):
        """DELETE on another session's conversation returns 404 to prevent enumeration."""
        from src.services import chat_store

        await chat_store.save_conversation(
            mock_db, "other-session-id", "foreign-conv", "Foreign Chat"
        )

        resp = await client.delete("/api/v1/chat/conversations/foreign-conv")
        assert resp.status_code == 404

    async def test_send_message_other_sessions_conversation_returns_404(
        self, client, mock_db, mock_session, mock_chat_agent_service
    ):
        """POST /chat/messages rejects conversations owned by a different session."""
        from src.services import chat_store

        mock_session.selected_project_id = "PVT_1"
        foreign_conversation_id = str(uuid4())
        await chat_store.save_conversation(
            mock_db,
            "other-session-id",
            foreign_conversation_id,
            "Foreign Chat",
        )

        resp = await client.post(
            "/api/v1/chat/messages",
            json={"content": "fix the auth bug", "conversation_id": foreign_conversation_id},
        )

        assert resp.status_code == 404
        assert resp.json()["error"] == f"Conversation {foreign_conversation_id} not found"
        mock_chat_agent_service.run.assert_not_called()

    async def test_send_message_stream_other_sessions_conversation_returns_404(
        self, client, mock_db, mock_session, mock_chat_agent_service
    ):
        """POST /chat/messages/stream rejects conversations owned by a different session."""
        from src.services import chat_store

        mock_session.selected_project_id = "PVT_1"
        foreign_conversation_id = str(uuid4())
        await chat_store.save_conversation(
            mock_db,
            "other-session-id",
            foreign_conversation_id,
            "Foreign Chat",
        )

        resp = await client.post(
            "/api/v1/chat/messages/stream",
            json={"content": "fix the auth bug", "conversation_id": foreign_conversation_id},
        )

        assert resp.status_code == 404
        assert resp.json()["error"] == f"Conversation {foreign_conversation_id} not found"
        mock_chat_agent_service.run_stream.assert_not_called()
