import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.exceptions import AuthorizationError
from src.services.mcp_server.context import McpContext
from src.services.mcp_server.resources import register_resources


class _FakePipelineState:
    def __init__(self, project_id: str, status: str) -> None:
        self.project_id = project_id
        self.status = status

    def model_dump(self) -> dict[str, str]:
        return {"project_id": self.project_id, "status": self.status}


class _FakeMCP:
    def __init__(self) -> None:
        self.resources: dict[str, object] = {}

    def resource(self, uri: str):
        def decorator(fn):
            self.resources[uri] = fn
            return fn

        return decorator


def _ctx(mcp_ctx: McpContext | None) -> SimpleNamespace:
    return SimpleNamespace(
        request_context=SimpleNamespace(lifespan_context={"mcp_context": mcp_ctx})
    )


@pytest.fixture
def registered_resources() -> dict[str, object]:
    mcp = _FakeMCP()
    register_resources(mcp)
    return mcp.resources


@pytest.mark.asyncio
async def test_pipelines_resource_requires_access_and_serializes_matching_state(
    registered_resources,
) -> None:
    handler = registered_resources["solune://projects/{project_id}/pipelines"]
    mcp_ctx = McpContext(github_token="ghp_valid", github_user_id=1, github_login="octocat")
    states = {
        "pipe-1": _FakePipelineState("proj-1", "running"),
        "pipe-2": _FakePipelineState("proj-2", "queued"),
    }

    with (
        patch(
            "src.services.mcp_server.resources.verify_mcp_project_access",
            new=AsyncMock(),
        ) as mock_verify,
        patch(
            "src.services.pipeline_state_store.get_all_pipeline_states",
            return_value=states,
        ),
    ):
        result = await handler(_ctx(mcp_ctx), "proj-1")

    assert json.loads(result) == {
        "project_id": "proj-1",
        "pipeline_states": {"pipe-1": {"project_id": "proj-1", "status": "running"}},
    }
    mock_verify.assert_awaited_once_with(mcp_ctx, "proj-1")


@pytest.mark.asyncio
async def test_board_resource_requires_authenticated_context(registered_resources) -> None:
    handler = registered_resources["solune://projects/{project_id}/board"]

    with pytest.raises(AuthorizationError, match="Authentication required"):
        await handler(_ctx(None), "proj-1")


@pytest.mark.asyncio
async def test_board_resource_rejects_unauthorized_projects(registered_resources) -> None:
    handler = registered_resources["solune://projects/{project_id}/board"]
    mcp_ctx = McpContext(github_token="ghp_valid", github_user_id=1, github_login="octocat")

    with patch(
        "src.services.mcp_server.resources.verify_mcp_project_access",
        new=AsyncMock(side_effect=AuthorizationError("forbidden")),
    ):
        with pytest.raises(AuthorizationError, match="forbidden"):
            await handler(_ctx(mcp_ctx), "proj-2")


@pytest.mark.asyncio
async def test_activity_resource_serializes_events_with_default_string_conversion(
    registered_resources,
) -> None:
    handler = registered_resources["solune://projects/{project_id}/activity"]
    mcp_ctx = McpContext(github_token="ghp_valid", github_user_id=1, github_login="octocat")
    now = datetime(2026, 4, 6, tzinfo=UTC)

    with (
        patch(
            "src.services.mcp_server.resources.verify_mcp_project_access",
            new=AsyncMock(),
        ) as mock_verify,
        patch("src.services.database.get_db", return_value=object()),
        patch(
            "src.services.activity_service.query_events",
            new=AsyncMock(return_value={"events": [{"created_at": now}], "count": 1}),
        ),
    ):
        result = await handler(_ctx(mcp_ctx), "proj-1")

    payload = json.loads(result)
    assert payload["project_id"] == "proj-1"
    assert payload["count"] == 1
    assert payload["events"][0]["created_at"] == str(now)
    mock_verify.assert_awaited_once_with(mcp_ctx, "proj-1")


@pytest.mark.asyncio
async def test_activity_resource_propagates_service_errors_after_auth(registered_resources) -> None:
    handler = registered_resources["solune://projects/{project_id}/activity"]
    mcp_ctx = McpContext(github_token="ghp_valid", github_user_id=1, github_login="octocat")

    with (
        patch(
            "src.services.mcp_server.resources.verify_mcp_project_access",
            new=AsyncMock(),
        ),
        patch("src.services.database.get_db", return_value=object()),
        patch(
            "src.services.activity_service.query_events",
            new=AsyncMock(side_effect=RuntimeError("db down")),
        ),
    ):
        with pytest.raises(RuntimeError, match="db down"):
            await handler(_ctx(mcp_ctx), "proj-1")
