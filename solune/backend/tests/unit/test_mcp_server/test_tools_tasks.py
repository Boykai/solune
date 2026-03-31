"""Tests for MCP task tools — create_task, create_issue.

Covers:
- Service delegation (correct methods called with correct arguments)
- Structured return data format
- Project access validation (rejects unauthorized users)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import AuthorizationError
from src.services.mcp_server.context import McpContext
from src.services.mcp_server.tools.tasks import create_issue, create_task


def _make_ctx(mcp_ctx: McpContext | None = None) -> MagicMock:
    """Create a mock MCP tool Context with an McpContext in lifespan."""
    ctx = MagicMock()
    if mcp_ctx is None:
        mcp_ctx = McpContext(
            github_token="ghp_testtoken", github_user_id=42, github_login="testuser"
        )
    ctx.request_context.lifespan_context = {"mcp_context": mcp_ctx}
    return ctx


# ── create_task ─────────────────────────────────────────────────────


class TestCreateTask:
    @patch("src.utils.resolve_repository", new_callable=AsyncMock)
    @patch("src.services.github_projects.GitHubProjectsService")
    @patch(
        "src.services.mcp_server.tools.tasks.verify_mcp_project_access",
        new_callable=AsyncMock,
    )
    async def test_creates_issue_and_adds_to_project(self, mock_access, MockSvc, mock_resolve_repo):
        mock_resolve_repo.return_value = ("octocat", "hello-world")
        svc = MockSvc.return_value
        svc.create_issue = AsyncMock(
            return_value={
                "number": 1,
                "html_url": "https://github.com/octocat/hello-world/issues/1",
                "node_id": "I_abc",
                "id": 100,
            }
        )
        svc.add_issue_to_project = AsyncMock(return_value="PVTI_xyz")

        ctx = _make_ctx()
        result = await create_task(ctx, "PVT_abc", "My Task", "Task description")

        assert result["issue_number"] == 1
        assert result["project_item_id"] == "PVTI_xyz"
        assert result["project_id"] == "PVT_abc"
        svc.create_issue.assert_awaited_once_with(
            "ghp_testtoken", "octocat", "hello-world", "My Task", "Task description"
        )
        svc.add_issue_to_project.assert_awaited_once_with("ghp_testtoken", "PVT_abc", "I_abc", 100)

    @patch(
        "src.services.mcp_server.tools.tasks.verify_mcp_project_access",
        new_callable=AsyncMock,
    )
    async def test_rejects_unauthorized_user(self, mock_access):
        mock_access.side_effect = AuthorizationError("You do not have access to this project")

        ctx = _make_ctx()
        with pytest.raises(AuthorizationError):
            await create_task(ctx, "PVT_noaccess", "Title", "Body")

    async def test_rejects_unauthenticated(self):
        ctx = MagicMock()
        ctx.request_context.lifespan_context = {}

        with pytest.raises(AuthorizationError):
            await create_task(ctx, "PVT_abc", "Title", "Body")


# ── create_issue ────────────────────────────────────────────────────


class TestCreateIssue:
    @patch("src.utils.resolve_repository", new_callable=AsyncMock)
    @patch("src.services.github_projects.GitHubProjectsService")
    @patch(
        "src.services.mcp_server.tools.tasks.verify_mcp_project_access",
        new_callable=AsyncMock,
    )
    async def test_creates_issue_with_labels(self, mock_access, MockSvc, mock_resolve_repo):
        mock_resolve_repo.return_value = ("octocat", "hello-world")
        svc = MockSvc.return_value
        svc.create_issue = AsyncMock(
            return_value={
                "number": 2,
                "html_url": "https://github.com/octocat/hello-world/issues/2",
                "node_id": "I_def",
                "id": 200,
            }
        )
        svc.add_issue_to_project = AsyncMock(return_value="PVTI_uvw")

        ctx = _make_ctx()
        result = await create_issue(
            ctx, "PVT_abc", "Bug Report", "Something broke", labels=["bug", "urgent"]
        )

        assert result["issue_number"] == 2
        assert result["node_id"] == "I_def"
        assert result["project_item_id"] == "PVTI_uvw"
        svc.create_issue.assert_awaited_once_with(
            "ghp_testtoken",
            "octocat",
            "hello-world",
            "Bug Report",
            "Something broke",
            labels=["bug", "urgent"],
        )

    @patch("src.utils.resolve_repository", new_callable=AsyncMock)
    @patch("src.services.github_projects.GitHubProjectsService")
    @patch(
        "src.services.mcp_server.tools.tasks.verify_mcp_project_access",
        new_callable=AsyncMock,
    )
    async def test_creates_issue_without_labels(self, mock_access, MockSvc, mock_resolve_repo):
        mock_resolve_repo.return_value = ("octocat", "hello-world")
        svc = MockSvc.return_value
        svc.create_issue = AsyncMock(
            return_value={
                "number": 3,
                "html_url": "https://github.com/octocat/hello-world/issues/3",
                "node_id": "I_ghi",
                "id": 300,
            }
        )
        svc.add_issue_to_project = AsyncMock(return_value="PVTI_rst")

        ctx = _make_ctx()
        result = await create_issue(ctx, "PVT_abc", "Feature", "New feature")

        assert result["issue_number"] == 3
        svc.create_issue.assert_awaited_once_with(
            "ghp_testtoken",
            "octocat",
            "hello-world",
            "Feature",
            "New feature",
            labels=None,
        )
