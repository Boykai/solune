from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from src.services.github_projects import GitHubProjectsService


async def _login(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/dev-login",
        json={"github_token": "ghp_test_token"},
    )
    assert response.status_code == 200


async def _select_project(client: AsyncClient, project_id: str) -> None:
    response = await client.post(f"/api/v1/projects/{project_id}/select")
    assert response.status_code == 200


def _stage(agent_slug: str, display_name: str, *, config: dict | None = None) -> dict:
    return {
        "id": f"stage-{agent_slug}",
        "name": "Backlog",
        "order": 0,
        "execution_mode": "sequential",
        "groups": [
            {
                "id": f"group-{agent_slug}",
                "order": 0,
                "execution_mode": "sequential",
                "agents": [
                    {
                        "id": f"agent-{agent_slug}",
                        "agent_slug": agent_slug,
                        "agent_display_name": display_name,
                        "model_id": "",
                        "model_name": "",
                        "tool_ids": [],
                        "tool_count": 0,
                        "config": config or {},
                    }
                ],
            }
        ],
        "agents": [
            {
                "id": f"agent-{agent_slug}",
                "agent_slug": agent_slug,
                "agent_display_name": display_name,
                "model_id": "",
                "model_name": "",
                "tool_ids": [],
                "tool_count": 0,
                "config": config or {},
            }
        ],
    }


async def _create_pipeline(
    client: AsyncClient,
    project_id: str,
    *,
    name: str,
    stage: dict,
) -> str:
    response = await client.post(
        f"/api/v1/pipelines/{project_id}",
        json={
            "name": name,
            "description": name,
            "stages": [stage],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_pipeline_launch_records_fleet_dispatch_metadata(
    thin_mock_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.api.pipelines as pipelines_api

    project_id = "PVT_integration"
    await _login(thin_mock_client)
    await _select_project(thin_mock_client, project_id)

    capture: dict[str, str] = {}
    real_service = GitHubProjectsService()
    orchestrator = pipelines_api.get_workflow_orchestrator()
    github_stub = orchestrator.github

    async def _assign_copilot_to_issue(**kwargs):
        capture.update(
            {
                "custom_agent": kwargs["custom_agent"],
                "custom_instructions": kwargs["custom_instructions"],
            }
        )
        return True

    monkeypatch.setattr(
        github_stub,
        "format_issue_context_as_prompt",
        real_service.format_issue_context_as_prompt,
        raising=False,
    )
    monkeypatch.setattr(
        github_stub,
        "assign_copilot_to_issue",
        AsyncMock(side_effect=_assign_copilot_to_issue),
        raising=False,
    )
    monkeypatch.setattr(
        github_stub,
        "list_agent_tasks",
        AsyncMock(
            return_value=[
                {
                    "id": "task-123",
                    "name": "[speckit.specify] Launch human review",
                    "createdAt": "2026-04-12T10:00:00Z",
                }
            ]
        ),
        raising=False,
    )

    pipeline_id = await _create_pipeline(
        thin_mock_client,
        project_id,
        name="Fleet Dispatch Pipeline",
        stage=_stage("speckit.specify", "Spec Kit Specify"),
    )

    launch_response = await thin_mock_client.post(
        f"/api/v1/pipelines/{project_id}/launch",
        json={
            "issue_description": "Launch the fleet-backed spec pipeline.",
            "pipeline_id": pipeline_id,
        },
    )

    assert launch_response.status_code == 200
    body = launch_response.json()
    assert body["success"] is True
    assert body["issue_number"] == 101

    state_response = await thin_mock_client.get("/api/v1/workflow/pipeline-states/101")
    assert state_response.status_code == 200
    state = state_response.json()
    assert state["dispatch_backend"] == "fleet"
    assert state["agent_task_ids"] == {"speckit.specify": "task-123"}
    assert state["agent_statuses"]["speckit.specify"] == "active"
    assert capture["custom_agent"] == "speckit.specify"
    assert "Launch human review" in capture["custom_instructions"]
    assert "Parent issue body" in capture["custom_instructions"]


@pytest.mark.asyncio
async def test_pipeline_launch_with_human_agent_stays_classic(
    thin_mock_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.api.pipelines as pipelines_api

    project_id = "PVT_integration"
    await _login(thin_mock_client)
    await _select_project(thin_mock_client, project_id)
    orchestrator = pipelines_api.get_workflow_orchestrator()

    monkeypatch.setattr(
        orchestrator.github,
        "assign_copilot_to_issue",
        AsyncMock(side_effect=AssertionError("human launches must not dispatch Copilot")),
        raising=False,
    )

    pipeline_id = await _create_pipeline(
        thin_mock_client,
        project_id,
        name="Human Review Pipeline",
        stage=_stage("human", "Human"),
    )

    launch_response = await thin_mock_client.post(
        f"/api/v1/pipelines/{project_id}/launch",
        json={
            "issue_description": "Launch the human review pipeline.",
            "pipeline_id": pipeline_id,
        },
    )

    assert launch_response.status_code == 200
    body = launch_response.json()
    assert body["success"] is True
    assert body["issue_number"] == 101

    state_response = await thin_mock_client.get("/api/v1/workflow/pipeline-states/101")
    assert state_response.status_code == 200
    state = state_response.json()
    assert state["dispatch_backend"] == "classic"
    assert state["agent_task_ids"] == {}
    assert state["current_agent"] == "human"
