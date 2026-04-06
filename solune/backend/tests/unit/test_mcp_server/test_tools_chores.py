"""Tests for MCP chore tools — list_chores and trigger_chore."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.mcp_server.context import McpContext
from src.services.mcp_server.tools.chores import list_chores, trigger_chore


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
    "src.services.mcp_server.tools.chores.verify_mcp_project_access",
    new_callable=AsyncMock,
)
@patch("src.services.chores.service.ChoresService")
@patch("src.services.database.get_db")
async def test_list_chores_returns_serialized_chores(
    mock_get_db,
    MockChoresService,
    mock_access,
):
    chore1 = MagicMock()
    chore1.model_dump.return_value = {"id": "chore-1", "name": "Stale branch cleanup"}
    chore2 = MagicMock()
    chore2.model_dump.return_value = {"id": "chore-2", "name": "Dependency update"}
    MockChoresService.return_value.list_chores = AsyncMock(return_value=[chore1, chore2])

    result = await list_chores(_make_ctx(), "PVT_abc")

    assert result == {
        "project_id": "PVT_abc",
        "chores": [
            {"id": "chore-1", "name": "Stale branch cleanup"},
            {"id": "chore-2", "name": "Dependency update"},
        ],
    }
    mock_access.assert_awaited_once()
    MockChoresService.return_value.list_chores.assert_awaited_once_with("PVT_abc")
    mock_get_db.assert_called_once_with()


@pytest.mark.asyncio
@patch(
    "src.services.mcp_server.tools.chores.verify_mcp_project_access",
    new_callable=AsyncMock,
)
@patch("src.utils.resolve_repository", new_callable=AsyncMock)
@patch("src.services.github_projects.GitHubProjectsService")
@patch("src.services.chores.service.ChoresService")
@patch("src.services.database.get_db")
async def test_trigger_chore_returns_result(
    mock_get_db,
    MockChoresService,
    MockGitHubProjectsService,
    mock_resolve_repository,
    mock_access,
):
    mock_resolve_repository.return_value = ("octocat", "solune")
    chore = MagicMock()
    chore.id = "chore-1"
    MockChoresService.return_value.list_chores = AsyncMock(return_value=[chore])

    trigger_result = MagicMock()
    trigger_result.model_dump.return_value = {"status": "triggered"}
    MockChoresService.return_value.trigger_chore = AsyncMock(return_value=trigger_result)

    result = await trigger_chore(_make_ctx(), "PVT_abc", "chore-1")

    assert result == {
        "chore_id": "chore-1",
        "project_id": "PVT_abc",
        "result": {"status": "triggered"},
    }
    mock_access.assert_awaited_once()
    mock_resolve_repository.assert_awaited_once_with("ghp_testtoken", "PVT_abc")
    MockChoresService.return_value.trigger_chore.assert_awaited_once()
    mock_get_db.assert_called_once_with()


@pytest.mark.asyncio
@patch(
    "src.services.mcp_server.tools.chores.verify_mcp_project_access",
    new_callable=AsyncMock,
)
@patch("src.services.chores.service.ChoresService")
@patch("src.services.database.get_db")
async def test_trigger_chore_returns_error_dict_when_chore_not_found(
    mock_get_db,
    MockChoresService,
    mock_access,
):
    chore = MagicMock()
    chore.id = "chore-1"
    MockChoresService.return_value.list_chores = AsyncMock(return_value=[chore])

    result = await trigger_chore(_make_ctx(), "PVT_abc", "nonexistent")

    assert result == {
        "error": "Chore 'nonexistent' not found in project PVT_abc",
    }
    mock_access.assert_awaited_once()
