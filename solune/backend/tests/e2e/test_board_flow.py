"""Board operations E2E tests (User Story 5).

Verifies: list board projects, get board data, update item status.
"""

from __future__ import annotations

import pytest

from src.models.board import (
    BoardColumn,
    BoardDataResponse,
    BoardItem,
    BoardProject,
    StatusColor,
    StatusField,
    StatusOption,
)
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


def _make_board_project() -> BoardProject:
    return BoardProject(
        project_id="PVT_test123",
        name="Test Project",
        url=f"https://github.com/users/{TEST_GITHUB_USERNAME}/projects/1",
        owner_login=TEST_GITHUB_USERNAME,
        status_field=StatusField(
            field_id="PVTSSF_f1",
            options=[
                StatusOption(option_id="opt1", name="Backlog", color=StatusColor.GRAY),
                StatusOption(option_id="opt2", name="In Progress", color=StatusColor.YELLOW),
                StatusOption(option_id="opt3", name="Done", color=StatusColor.GREEN),
            ],
        ),
    )


def _make_board_data() -> BoardDataResponse:
    board_project = _make_board_project()
    return BoardDataResponse(
        project=board_project,
        columns=[
            BoardColumn(
                status=StatusOption(option_id="opt1", name="Backlog", color=StatusColor.GRAY),
                items=[
                    BoardItem(
                        item_id="PVTI_item1",
                        content_type="issue",
                        title="Test Task",
                        number=1,
                        status="Backlog",
                        status_option_id="opt1",
                    ),
                ],
                item_count=1,
            ),
            BoardColumn(
                status=StatusOption(option_id="opt2", name="In Progress", color=StatusColor.YELLOW),
                items=[],
                item_count=0,
            ),
            BoardColumn(
                status=StatusOption(option_id="opt3", name="Done", color=StatusColor.GREEN),
                items=[],
                item_count=0,
            ),
        ],
    )


class TestBoardOperations:
    """Authenticated board operations with mocked GitHub API."""

    @pytest.mark.asyncio
    async def test_get_board_projects(self, auth_client, mock_github_projects_service):
        """GET /board/projects returns the board project list."""
        mock_github_projects_service.list_board_projects.return_value = [_make_board_project()]

        response = await auth_client.get("/api/v1/board/projects")
        assert response.status_code == 200
        data = response.json()
        assert len(data["projects"]) == 1
        assert data["projects"][0]["project_id"] == "PVT_test123"

    @pytest.mark.asyncio
    async def test_get_board_data_with_columns(self, auth_client, mock_github_projects_service):
        """GET /board/projects/{id} returns board data with columns and items."""
        mock_github_projects_service.get_board_data.return_value = _make_board_data()

        response = await auth_client.get("/api/v1/board/projects/PVT_test123")
        assert response.status_code == 200
        data = response.json()
        assert "columns" in data
        assert len(data["columns"]) == 3

        # Verify the first column has an item
        backlog = data["columns"][0]
        assert backlog["status"]["name"] == "Backlog"
        assert len(backlog["items"]) == 1
        assert backlog["items"][0]["title"] == "Test Task"

    @pytest.mark.asyncio
    async def test_move_task_between_columns(self, auth_client, mock_github_projects_service):
        """PATCH /board/projects/{id}/items/{item_id}/status updates the status."""
        mock_github_projects_service.update_item_status_by_name.return_value = True

        response = await auth_client.patch(
            "/api/v1/board/projects/PVT_test123/items/PVTI_item1/status",
            json={"status": "In Progress"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_board_operations_require_auth(self, unauthenticated_client):
        """Board endpoints return 401 without authentication."""
        response = await unauthenticated_client.get("/api/v1/board/projects")
        assert response.status_code == 401

