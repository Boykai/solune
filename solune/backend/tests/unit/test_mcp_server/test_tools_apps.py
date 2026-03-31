"""Tests for MCP app tools — list_apps, get_app_status, create_app."""

from unittest.mock import MagicMock, patch

from src.services.mcp_server.context import McpContext
from src.services.mcp_server.tools.apps import create_app, get_app_status, list_apps


def _make_ctx(mcp_ctx: McpContext | None = None) -> MagicMock:
    ctx = MagicMock()
    if mcp_ctx is None:
        mcp_ctx = McpContext(
            github_token="ghp_testtoken", github_user_id=42, github_login="testuser"
        )
    ctx.request_context.lifespan_context = {"mcp_context": mcp_ctx}
    return ctx


class TestListApps:
    @patch("src.services.app_service.list_apps")
    @patch("src.services.database.get_db")
    async def test_returns_app_list(self, mock_get_db, mock_list_apps):
        mock_app = MagicMock()
        mock_app.model_dump.return_value = {"name": "demo", "status": "active"}
        mock_list_apps.return_value = [mock_app]

        result = await list_apps(_make_ctx())

        assert result == {"apps": [{"name": "demo", "status": "active"}]}
        mock_list_apps.assert_awaited_once_with(mock_get_db.return_value)


class TestGetAppStatus:
    @patch("src.services.app_service.get_app_status")
    @patch("src.services.database.get_db")
    async def test_returns_serialized_status(self, mock_get_db, mock_get_status):
        mock_status = MagicMock()
        mock_status.model_dump.return_value = {"name": "demo", "status": "active"}
        mock_get_status.return_value = mock_status

        result = await get_app_status(_make_ctx(), "demo")

        assert result == {"name": "demo", "status": "active"}
        mock_get_status.assert_awaited_once_with(mock_get_db.return_value, "demo")


class TestCreateApp:
    @patch("src.services.app_service.create_app")
    @patch("src.services.github_projects.GitHubProjectsService")
    @patch("src.services.database.get_db")
    async def test_uses_new_repo_payload_with_owner_and_pipeline(
        self, mock_get_db, MockGitHubProjectsService, mock_create_app
    ):
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"name": "demo", "status": "created"}
        mock_create_app.return_value = mock_result

        result = await create_app(
            _make_ctx(),
            name="demo",
            owner="octocat",
            template="starter",
            pipeline_id="easy",
        )

        assert result == {"name": "demo", "status": "created"}
        mock_create_app.assert_awaited_once()
        call_args = mock_create_app.await_args
        payload = call_args.args[1]
        assert payload.name == "demo"
        assert payload.display_name == "demo"
        assert payload.repo_type == "new-repo"
        assert payload.repo_owner == "octocat"
        assert payload.pipeline_id == "easy"
        assert call_args.kwargs["access_token"] == "ghp_testtoken"
        assert call_args.kwargs["github_service"] is MockGitHubProjectsService.return_value
        assert call_args.args[0] is mock_get_db.return_value
