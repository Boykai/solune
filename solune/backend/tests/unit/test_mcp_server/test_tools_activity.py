"""Tests for MCP activity tools — get_activity and update_item_status."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.mcp_server.context import McpContext
from src.services.mcp_server.tools.activity import get_activity, update_item_status


def _make_ctx(mcp_ctx: McpContext | None = None) -> MagicMock:
    ctx = MagicMock()
    if mcp_ctx is None:
        mcp_ctx = McpContext(
            github_token="ghp_testtoken", github_user_id=42, github_login="testuser"
        )
    ctx.request_context.lifespan_context = {"mcp_context": mcp_ctx}
    return ctx


@pytest.mark.asyncio
@patch(
    "src.services.mcp_server.tools.activity.verify_mcp_project_access",
    new_callable=AsyncMock,
)
@patch("src.services.activity_service.query_events", new_callable=AsyncMock)
@patch("src.services.database.get_db")
async def test_get_activity_returns_events(
    mock_get_db,
    mock_query_events,
    mock_access,
):
    mock_query_events.return_value = {
        "events": [{"type": "issue_created", "id": "evt-1"}],
        "total": 1,
    }

    result = await get_activity(_make_ctx(), "PVT_abc", limit=20)

    assert result == {
        "project_id": "PVT_abc",
        "events": [{"type": "issue_created", "id": "evt-1"}],
        "total": 1,
    }
    mock_access.assert_awaited_once()
    mock_query_events.assert_awaited_once_with(
        mock_get_db.return_value, project_id="PVT_abc", limit=20
    )
    mock_get_db.assert_called_once_with()


@pytest.mark.asyncio
@patch(
    "src.services.mcp_server.tools.activity.verify_mcp_project_access",
    new_callable=AsyncMock,
)
@patch("src.services.activity_service.query_events", new_callable=AsyncMock)
@patch("src.services.database.get_db")
async def test_get_activity_clamps_limit_to_valid_range(
    mock_get_db,
    mock_query_events,
    mock_access,
):
    mock_query_events.return_value = {"events": [], "total": 0}

    # limit=0 should be clamped to 1
    await get_activity(_make_ctx(), "PVT_abc", limit=0)
    mock_query_events.assert_awaited_with(mock_get_db.return_value, project_id="PVT_abc", limit=1)

    mock_query_events.reset_mock()

    # limit=200 should be clamped to 100
    await get_activity(_make_ctx(), "PVT_abc", limit=200)
    mock_query_events.assert_awaited_with(mock_get_db.return_value, project_id="PVT_abc", limit=100)


@pytest.mark.asyncio
@patch(
    "src.services.mcp_server.tools.activity.verify_mcp_project_access",
    new_callable=AsyncMock,
)
@patch("src.services.github_projects.GitHubProjectsService")
async def test_update_item_status_returns_success(
    MockGitHubProjectsService,
    mock_access,
):
    MockGitHubProjectsService.return_value.update_item_status_by_name = AsyncMock(return_value=True)

    result = await update_item_status(_make_ctx(), "PVT_abc", "PVTI_item1", "Done")

    assert result == {
        "success": True,
        "project_id": "PVT_abc",
        "item_id": "PVTI_item1",
        "new_status": "Done",
    }
    mock_access.assert_awaited_once()
    MockGitHubProjectsService.return_value.update_item_status_by_name.assert_awaited_once_with(
        "ghp_testtoken", "PVT_abc", "PVTI_item1", "Done"
    )
