"""Tests for MCP project tools — list_projects, get_project, get_board, get_project_tasks.

Covers:
- Service delegation (correct methods called with correct arguments)
- Structured return data format
- Project access validation (rejects unauthorized users)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.mcp_server.context import McpContext
from src.services.mcp_server.tools.projects import (
    get_board,
    get_project,
    get_project_tasks,
    list_projects,
)


def _make_ctx(mcp_ctx: McpContext | None = None) -> MagicMock:
    """Create a mock MCP tool Context with an McpContext in lifespan."""
    ctx = MagicMock()
    if mcp_ctx is None:
        mcp_ctx = McpContext(
            github_token="ghp_testtoken", github_user_id=42, github_login="testuser"
        )
    ctx.request_context.lifespan_context = {"mcp_context": mcp_ctx}
    return ctx


def _mock_project(project_id: str = "PVT_abc", name: str = "Test", url: str = "https://github.com"):
    p = MagicMock()
    p.project_id = project_id
    p.name = name
    p.url = url
    return p


# ── list_projects ───────────────────────────────────────────────────


class TestListProjects:
    @patch("src.services.github_projects.GitHubProjectsService")
    async def test_returns_project_list(self, MockSvc):
        svc = MockSvc.return_value
        svc.list_user_projects = AsyncMock(
            return_value=[
                _mock_project("PVT_1", "Project A", "https://example.com/a"),
                _mock_project("PVT_2", "Project B", "https://example.com/b"),
            ]
        )

        ctx = _make_ctx()
        result = await list_projects(ctx)

        assert len(result["projects"]) == 2
        assert result["projects"][0]["project_id"] == "PVT_1"
        assert result["projects"][0]["name"] == "Project A"
        svc.list_user_projects.assert_awaited_once_with("ghp_testtoken", "testuser")

    @patch("src.services.github_projects.GitHubProjectsService")
    async def test_empty_project_list(self, MockSvc):
        svc = MockSvc.return_value
        svc.list_user_projects = AsyncMock(return_value=[])

        ctx = _make_ctx()
        result = await list_projects(ctx)
        assert result["projects"] == []

    async def test_no_auth_context_raises(self):
        ctx = MagicMock()
        ctx.request_context.lifespan_context = {"mcp_context": None}

        from src.exceptions import AuthorizationError

        with pytest.raises(AuthorizationError):
            await list_projects(ctx)


# ── get_project ────────────────────────────────────────────────────


class TestGetProject:
    @patch(
        "src.services.mcp_server.tools.projects.verify_mcp_project_access",
        new_callable=AsyncMock,
    )
    @patch("src.services.github_projects.GitHubProjectsService")
    async def test_returns_project_details(self, MockSvc, mock_access):
        svc = MockSvc.return_value
        svc.get_project_fields = AsyncMock(return_value={"Status": {"type": "single_select"}})
        svc.get_project_repository = AsyncMock(return_value=("owner", "repo"))

        ctx = _make_ctx()
        result = await get_project(ctx, "PVT_abc")

        assert result["project_id"] == "PVT_abc"
        assert result["fields"] == {"Status": {"type": "single_select"}}
        assert result["repository"] == {"owner": "owner", "repo": "repo"}
        mock_access.assert_awaited_once()

    @patch(
        "src.services.mcp_server.tools.projects.verify_mcp_project_access",
        new_callable=AsyncMock,
    )
    @patch("src.services.github_projects.GitHubProjectsService")
    async def test_no_repository_info(self, MockSvc, mock_access):
        svc = MockSvc.return_value
        svc.get_project_fields = AsyncMock(return_value={})
        svc.get_project_repository = AsyncMock(return_value=None)

        ctx = _make_ctx()
        result = await get_project(ctx, "PVT_xyz")
        assert result["repository"] is None


# ── get_board ──────────────────────────────────────────────────────


class TestGetBoard:
    @patch(
        "src.services.mcp_server.tools.projects.verify_mcp_project_access",
        new_callable=AsyncMock,
    )
    @patch("src.services.github_projects.GitHubProjectsService")
    async def test_returns_board_data(self, MockSvc, mock_access):
        svc = MockSvc.return_value
        board_data = {"columns": [{"name": "Todo", "items": []}]}
        svc.get_board_data = AsyncMock(return_value=board_data)

        ctx = _make_ctx()
        result = await get_board(ctx, "PVT_abc")

        assert result["project_id"] == "PVT_abc"
        assert result["board"] == board_data

    @patch(
        "src.services.mcp_server.tools.projects.verify_mcp_project_access",
        new_callable=AsyncMock,
    )
    async def test_access_denied(self, mock_access):
        from src.exceptions import AuthorizationError

        mock_access.side_effect = AuthorizationError("You do not have access to this project")

        ctx = _make_ctx()
        with pytest.raises(AuthorizationError):
            await get_board(ctx, "PVT_forbidden")


# ── get_project_tasks ──────────────────────────────────────────────


class TestGetProjectTasks:
    @patch(
        "src.services.mcp_server.tools.projects.verify_mcp_project_access",
        new_callable=AsyncMock,
    )
    @patch("src.services.github_projects.GitHubProjectsService")
    async def test_returns_items(self, MockSvc, mock_access):
        svc = MockSvc.return_value
        mock_item = MagicMock()
        mock_item.model_dump.return_value = {"title": "Task 1", "status": "Todo"}
        svc.get_project_items = AsyncMock(return_value=[mock_item])

        ctx = _make_ctx()
        result = await get_project_tasks(ctx, "PVT_abc")

        assert result["project_id"] == "PVT_abc"
        assert len(result["items"]) == 1
        assert result["items"][0]["title"] == "Task 1"
