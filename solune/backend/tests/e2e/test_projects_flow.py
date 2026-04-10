"""Project operations E2E tests (User Story 2).

Verifies: list projects, select project (session update), get details, list tasks.
"""

from __future__ import annotations

import pytest

from src.models.project import GitHubProject, StatusColumn
from tests.conftest import TEST_GITHUB_USERNAME


def _make_test_project(project_id: str = "PVT_test123") -> GitHubProject:
    """Create a minimal GitHubProject fixture."""
    return GitHubProject(
        project_id=project_id,
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


class TestProjectOperations:
    """Authenticated project CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_projects(self, auth_client, mock_github_projects_service):
        """GET /projects returns the mock project list."""
        project = _make_test_project()
        mock_github_projects_service.list_user_projects.return_value = [project]

        response = await auth_client.get("/api/v1/projects")
        assert response.status_code == 200
        data = response.json()
        assert len(data["projects"]) == 1
        assert data["projects"][0]["project_id"] == "PVT_test123"
        assert data["projects"][0]["name"] == "Test Project"

    @pytest.mark.asyncio
    async def test_select_project_updates_session(self, auth_client, mock_github_projects_service):
        """POST /projects/{id}/select updates selected_project_id in the session."""
        project = _make_test_project()
        mock_github_projects_service.list_user_projects.return_value = [project]

        # Select the project
        response = await auth_client.post("/api/v1/projects/PVT_test123/select")
        assert response.status_code == 200
        data = response.json()
        assert data["selected_project_id"] == "PVT_test123"

        # Verify the session was updated
        me = await auth_client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["selected_project_id"] == "PVT_test123"

    @pytest.mark.asyncio
    async def test_get_project_details(self, auth_client, mock_github_projects_service):
        """GET /projects/{id} returns project details after selection."""
        project = _make_test_project()
        mock_github_projects_service.list_user_projects.return_value = [project]

        response = await auth_client.get("/api/v1/projects/PVT_test123")
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == "PVT_test123"
        assert data["name"] == "Test Project"

    @pytest.mark.asyncio
    async def test_list_project_tasks(self, auth_client, mock_github_projects_service):
        """GET /projects/{id}/tasks returns task list for the selected project."""
        project = _make_test_project()
        mock_github_projects_service.list_user_projects.return_value = [project]

        # Mock get_project_items to return an empty task list
        mock_github_projects_service.get_project_items.return_value = []

        response = await auth_client.get("/api/v1/projects/PVT_test123/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert isinstance(data["tasks"], list)

    @pytest.mark.asyncio
    async def test_project_operations_require_auth(self, unauthenticated_client):
        """Project endpoints return 401 without authentication."""
        response = await unauthenticated_client.get("/api/v1/projects")
        assert response.status_code == 401

