"""Chat flow E2E tests (User Story 3).

Verifies: project-selection requirement, send message, get history.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.models.chat import ChatMessage, SenderType
from src.models.project import GitHubProject, StatusColumn
from tests.conftest import TEST_GITHUB_USERNAME


def _make_test_project() -> GitHubProject:
    return GitHubProject(
        project_id="PVT_test123",
        owner_id="O_owner123",
        owner_login=TEST_GITHUB_USERNAME,
        name="Test Project",
        type="user",
        url=f"https://github.com/users/{TEST_GITHUB_USERNAME}/projects/1",
        status_columns=[
            StatusColumn(field_id="PVTSSF_f1", name="Todo", option_id="opt1"),
            StatusColumn(field_id="PVTSSF_f1", name="In Progress", option_id="opt2"),
            StatusColumn(field_id="PVTSSF_f1", name="Done", option_id="opt3"),
        ],
    )


def _make_assistant_message(session_id) -> ChatMessage:
    """Create a realistic assistant ChatMessage for mock responses."""
    return ChatMessage(
        message_id=uuid4(),
        session_id=session_id,
        sender_type=SenderType.ASSISTANT,
        content="I can help you with that! Here's what I found.",
    )


class TestChatFlow:
    """Authenticated chat operations."""

    @pytest.mark.asyncio
    async def test_send_message_requires_selected_project(self, auth_client):
        """POST /chat/messages without selecting a project first returns an error."""
        response = await auth_client.post(
            "/api/v1/chat/messages",
            json={"content": "Hello"},
        )
        # Should fail because no project is selected
        assert response.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_send_message_with_selected_project(
        self, auth_client, mock_github_projects_service, mock_chat_agent_service
    ):
        """POST /chat/messages succeeds after selecting a project."""
        project = _make_test_project()
        mock_github_projects_service.list_user_projects.return_value = [project]

        # Select a project first
        select_resp = await auth_client.post("/api/v1/projects/PVT_test123/select")
        assert select_resp.status_code == 200

        # Configure the mock chat agent to return a proper ChatMessage
        session_id = uuid4()  # Placeholder — the endpoint creates its own ChatMessage
        mock_chat_agent_service.run.return_value = _make_assistant_message(session_id)

        response = await auth_client.post(
            "/api/v1/chat/messages",
            json={"content": "Test message for chat flow"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data

    @pytest.mark.asyncio
    async def test_get_chat_history(
        self, auth_client, mock_github_projects_service, mock_chat_agent_service
    ):
        """GET /chat/messages returns chat history after sending a message."""
        project = _make_test_project()
        mock_github_projects_service.list_user_projects.return_value = [project]

        # Select project
        await auth_client.post("/api/v1/projects/PVT_test123/select")

        # Configure mock to return a proper ChatMessage
        session_id = uuid4()
        mock_chat_agent_service.run.return_value = _make_assistant_message(session_id)

        # Send a message
        await auth_client.post(
            "/api/v1/chat/messages",
            json={"content": "Hello chat history test"},
        )

        # Retrieve history
        response = await auth_client.get("/api/v1/chat/messages")
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)
        # Should have at least the user message and the assistant response
        assert len(data["messages"]) >= 1

    @pytest.mark.asyncio
    async def test_chat_requires_auth(self, unauthenticated_client):
        """Chat endpoints return 401 without authentication."""
        response = await unauthenticated_client.post(
            "/api/v1/chat/messages",
            json={"content": "Hello"},
        )
        assert response.status_code == 401

