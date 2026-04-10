"""Pipeline CRUD E2E tests (User Story 4).

Verifies: list pipelines, create pipeline, assignment operations.
"""

from __future__ import annotations

import pytest

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


async def _select_project(client, mock_github_projects_service) -> None:
    """Select the test project so project-scoped endpoints succeed."""
    mock_github_projects_service.list_user_projects.return_value = [_make_test_project()]
    resp = await client.post("/api/v1/projects/PVT_test123/select")
    assert resp.status_code == 200


class TestPipelineCRUD:
    """Authenticated pipeline operations backed by real SQLite."""

    @pytest.mark.asyncio
    async def test_list_pipelines(self, auth_client, mock_github_projects_service):
        """GET /pipelines/{project_id} returns pipeline list (initially empty)."""
        await _select_project(auth_client, mock_github_projects_service)

        response = await auth_client.get("/api/v1/pipelines/PVT_test123")
        assert response.status_code == 200
        data = response.json()
        assert data["pipelines"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_create_pipeline(self, auth_client, mock_github_projects_service):
        """POST /pipelines/{project_id} creates a new pipeline config."""
        await _select_project(auth_client, mock_github_projects_service)

        create_resp = await auth_client.post(
            "/api/v1/pipelines/PVT_test123",
            json={
                "name": "Test Pipeline",
                "description": "A pipeline for E2E testing",
                "stages": [],
            },
        )
        assert create_resp.status_code == 201
        pipeline = create_resp.json()
        assert pipeline["name"] == "Test Pipeline"
        assert pipeline["project_id"] == "PVT_test123"

        # Verify it appears in the list
        list_resp = await auth_client.get("/api/v1/pipelines/PVT_test123")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_assign_pipeline_to_project(self, auth_client, mock_github_projects_service):
        """PUT /pipelines/{project_id}/assignment sets the pipeline assignment."""
        await _select_project(auth_client, mock_github_projects_service)

        # Create a pipeline first
        create_resp = await auth_client.post(
            "/api/v1/pipelines/PVT_test123",
            json={"name": "Assigned Pipeline", "stages": []},
        )
        assert create_resp.status_code == 201
        pipeline_id = create_resp.json()["id"]

        # Assign pipeline to project
        assign_resp = await auth_client.put(
            "/api/v1/pipelines/PVT_test123/assignment",
            json={"pipeline_id": pipeline_id},
        )
        assert assign_resp.status_code == 200
        assert assign_resp.json()["pipeline_id"] == pipeline_id

        # Verify assignment persists
        get_resp = await auth_client.get("/api/v1/pipelines/PVT_test123/assignment")
        assert get_resp.status_code == 200
        assert get_resp.json()["pipeline_id"] == pipeline_id

    @pytest.mark.asyncio
    async def test_pipeline_operations_require_auth(self, unauthenticated_client):
        """Pipeline endpoints return 401 without authentication."""
        response = await unauthenticated_client.get("/api/v1/pipelines/PVT_test123")
        assert response.status_code == 401
