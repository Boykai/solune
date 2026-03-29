from unittest.mock import AsyncMock, patch

from src.models.tools import (
    McpToolConfigListResponse,
    McpToolConfigResponse,
    RepoMcpConfigResponse,
    RepoMcpServerConfig,
)


class TestToolsPresetsApi:
    async def test_list_presets_returns_catalog(self, client):
        resp = await client.get("/api/v1/tools/presets")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        preset_ids = {preset["id"] for preset in data["presets"]}
        assert "github-readonly" in preset_ids
        assert "context7" in preset_ids
        assert "codegraphcontext" in preset_ids
        github_preset = next(p for p in data["presets"] if p["id"] == "github-readonly")
        assert "api.githubcopilot.com/mcp/readonly" in github_preset["config_content"]

    async def test_context7_preset_has_correct_config(self, client):
        resp = await client.get("/api/v1/tools/presets")
        assert resp.status_code == 200
        data = resp.json()
        preset = next(p for p in data["presets"] if p["id"] == "context7")
        assert preset["name"] == "Context7"
        assert preset["category"] == "Documentation"
        assert "mcp.context7.com/mcp" in preset["config_content"]

    async def test_codegraphcontext_preset_has_correct_config(self, client):
        resp = await client.get("/api/v1/tools/presets")
        assert resp.status_code == 200
        data = resp.json()
        preset = next(p for p in data["presets"] if p["id"] == "codegraphcontext")
        assert preset["name"] == "Code Graph Context"
        assert preset["category"] == "Code Analysis"
        assert "codegraphcontext" in preset["config_content"]


class TestRepoMcpConfigApi:
    async def test_repo_config_returns_service_payload(self, client, mock_github_service):
        mock_github_service.get_project_repository.return_value = ("octo", "widgets")
        response_model = RepoMcpConfigResponse(
            paths_checked=[".copilot/mcp.json", ".vscode/mcp.json"],
            available_paths=[".copilot/mcp.json", ".vscode/mcp.json"],
            primary_path=".copilot/mcp.json",
            servers=[
                RepoMcpServerConfig(
                    name="github",
                    config={"type": "http", "url": "https://api.githubcopilot.com/mcp/readonly"},
                    source_paths=[".copilot/mcp.json", ".vscode/mcp.json"],
                )
            ],
        )

        with patch(
            "src.api.tools.ToolsService.get_repo_mcp_config",
            AsyncMock(return_value=response_model),
        ) as repo_config_mock:
            resp = await client.get("/api/v1/tools/PVT_123/repo-config")

        assert resp.status_code == 200
        data = resp.json()
        assert data["primary_path"] == ".copilot/mcp.json"
        assert data["available_paths"] == [".copilot/mcp.json", ".vscode/mcp.json"]
        assert data["servers"][0]["name"] == "github"
        repo_config_mock.assert_awaited_once_with(
            owner="octo",
            repo="widgets",
            access_token="test-token",
        )

    async def test_repo_config_returns_400_when_repository_cannot_be_resolved(
        self,
        client,
    ):
        with patch(
            "src.api.tools.resolve_repository",
            AsyncMock(side_effect=RuntimeError("resolution failed")),
        ):
            resp = await client.get("/api/v1/tools/PVT_123/repo-config")

        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data
        assert "Cannot resolve repository" in data["detail"]

    async def test_repo_config_returns_502_when_service_fetch_fails(
        self,
        client,
        mock_github_service,
    ):
        mock_github_service.get_project_repository.return_value = ("octo", "widgets")

        with patch(
            "src.api.tools.ToolsService.get_repo_mcp_config",
            AsyncMock(side_effect=RuntimeError("GitHub API error: 500 boom")),
        ):
            resp = await client.get("/api/v1/tools/PVT_123/repo-config")

        assert resp.status_code == 502
        data = resp.json()
        assert data["error"] == "Failed to fetch repository MCP config"

    async def test_update_repo_server_returns_updated_payload(self, client, mock_github_service):
        mock_github_service.get_project_repository.return_value = ("octo", "widgets")
        response_model = RepoMcpServerConfig(
            name="github",
            config={"type": "http", "url": "https://api.githubcopilot.com/mcp/full"},
            source_paths=[".copilot/mcp.json"],
        )

        with patch(
            "src.api.tools.ToolsService.update_repo_mcp_server",
            AsyncMock(return_value=response_model),
        ) as update_mock:
            resp = await client.put(
                "/api/v1/tools/PVT_123/repo-config/github",
                json={
                    "name": "github",
                    "config_content": '{"mcpServers":{"github":{"type":"http","url":"https://api.githubcopilot.com/mcp/full"}}}',
                },
            )

        assert resp.status_code == 200
        assert resp.json()["name"] == "github"
        update_mock.assert_awaited_once()

    async def test_delete_repo_server_returns_deleted_payload(self, client, mock_github_service):
        mock_github_service.get_project_repository.return_value = ("octo", "widgets")
        response_model = RepoMcpServerConfig(
            name="github",
            config={"type": "http", "url": "https://api.githubcopilot.com/mcp/readonly"},
            source_paths=[".copilot/mcp.json", ".vscode/mcp.json"],
        )

        with patch(
            "src.api.tools.ToolsService.delete_repo_mcp_server",
            AsyncMock(return_value=response_model),
        ) as delete_mock:
            resp = await client.delete("/api/v1/tools/PVT_123/repo-config/github")

        assert resp.status_code == 200
        assert resp.json()["source_paths"] == [".copilot/mcp.json", ".vscode/mcp.json"]
        delete_mock.assert_awaited_once_with(
            owner="octo",
            repo="widgets",
            access_token="test-token",
            server_name="github",
        )

    async def test_update_repo_server_returns_422_for_invalid_repo_json(
        self, client, mock_github_service
    ):
        mock_github_service.get_project_repository.return_value = ("octo", "widgets")

        with patch(
            "src.api.tools.ToolsService.update_repo_mcp_server",
            AsyncMock(
                side_effect=ValueError(
                    "Invalid JSON in repository MCP config file at .copilot/mcp.json: boom"
                )
            ),
        ):
            resp = await client.put(
                "/api/v1/tools/PVT_123/repo-config/github",
                json={
                    "name": "github",
                    "config_content": '{"mcpServers":{"github":{"type":"http","url":"https://api.githubcopilot.com/mcp/full"}}}',
                },
            )

        assert resp.status_code == 422
        assert "Invalid JSON" in resp.json()["error"]

    async def test_update_repo_server_returns_502_when_service_write_fails(
        self, client, mock_github_service
    ):
        mock_github_service.get_project_repository.return_value = ("octo", "widgets")

        with patch(
            "src.api.tools.ToolsService.update_repo_mcp_server",
            AsyncMock(side_effect=RuntimeError("GitHub API write error")),
        ):
            resp = await client.put(
                "/api/v1/tools/PVT_123/repo-config/github",
                json={
                    "name": "github",
                    "config_content": '{"mcpServers":{"github":{"type":"http","url":"https://api.githubcopilot.com/mcp/full"}}}',
                },
            )

        assert resp.status_code == 502
        assert resp.json()["error"] == "Failed to update repository MCP server"

    async def test_delete_repo_server_returns_422_for_invalid_repo_json(
        self, client, mock_github_service
    ):
        mock_github_service.get_project_repository.return_value = ("octo", "widgets")

        with patch(
            "src.api.tools.ToolsService.delete_repo_mcp_server",
            AsyncMock(
                side_effect=ValueError(
                    "Invalid JSON in repository MCP config file at .copilot/mcp.json: boom"
                )
            ),
        ):
            resp = await client.delete("/api/v1/tools/PVT_123/repo-config/github")

        assert resp.status_code == 422
        assert "Invalid JSON" in resp.json()["error"]

    async def test_delete_repo_server_returns_502_when_service_write_fails(
        self, client, mock_github_service
    ):
        mock_github_service.get_project_repository.return_value = ("octo", "widgets")

        with patch(
            "src.api.tools.ToolsService.delete_repo_mcp_server",
            AsyncMock(side_effect=RuntimeError("GitHub API write error")),
        ):
            resp = await client.delete("/api/v1/tools/PVT_123/repo-config/github")

        assert resp.status_code == 502
        assert resp.json()["error"] == "Failed to delete repository MCP server"


class TestToolsCrud:
    """Tests for tool CRUD endpoints (create, get, update, list with pagination)."""

    def _make_tool_response(self, **overrides):
        defaults = {
            "id": "tool-1",
            "name": "test-tool",
            "description": "A test tool",
            "endpoint_url": "https://example.com/mcp",
            "config_content": '{"mcpServers":{}}',
            "sync_status": "synced",
            "sync_error": "",
            "synced_at": "2024-01-01T00:00:00Z",
            "github_repo_target": "octo/widgets",
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        defaults.update(overrides)
        return McpToolConfigResponse(**defaults)

    async def test_create_tool_success(self, client, mock_github_service):
        mock_github_service.get_project_repository.return_value = ("octo", "widgets")
        tool_resp = self._make_tool_response()

        with (
            patch("src.api.tools.ToolsService.create_tool", AsyncMock(return_value=tool_resp)),
            patch("src.api.tools.log_event", new_callable=AsyncMock) as mock_log,
        ):
            resp = await client.post(
                "/api/v1/tools/PVT_123",
                json={
                    "name": "test-tool",
                    "config_content": '{"mcpServers":{}}',
                },
            )

        assert resp.status_code == 201
        assert resp.json()["name"] == "test-tool"
        mock_log.assert_awaited_once()

    async def test_create_tool_duplicate_name_returns_409(self, client, mock_github_service):
        from src.services.tools.service import DuplicateToolNameError

        mock_github_service.get_project_repository.return_value = ("octo", "widgets")

        with patch(
            "src.api.tools.ToolsService.create_tool",
            AsyncMock(side_effect=DuplicateToolNameError("test-tool")),
        ):
            resp = await client.post(
                "/api/v1/tools/PVT_123",
                json={
                    "name": "test-tool",
                    "config_content": '{"mcpServers":{}}',
                },
            )

        assert resp.status_code == 409

    async def test_create_tool_resolve_failure(self, client):
        with patch(
            "src.api.tools.resolve_repository",
            AsyncMock(side_effect=RuntimeError("cannot resolve")),
        ):
            resp = await client.post(
                "/api/v1/tools/PVT_123",
                json={
                    "name": "test-tool",
                    "config_content": '{"mcpServers":{}}',
                },
            )
        assert resp.status_code == 422

    async def test_get_tool_found(self, client):
        tool_resp = self._make_tool_response()
        with patch("src.api.tools.ToolsService.get_tool", AsyncMock(return_value=tool_resp)):
            resp = await client.get("/api/v1/tools/PVT_123/tool-1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "tool-1"

    async def test_get_tool_not_found(self, client):
        with patch("src.api.tools.ToolsService.get_tool", AsyncMock(return_value=None)):
            resp = await client.get("/api/v1/tools/PVT_123/nonexistent")
        assert resp.status_code == 404

    async def test_update_tool_success(self, client, mock_github_service):
        mock_github_service.get_project_repository.return_value = ("octo", "widgets")
        tool_resp = self._make_tool_response(name="updated-tool")

        with (
            patch("src.api.tools.ToolsService.update_tool", AsyncMock(return_value=tool_resp)),
            patch("src.api.tools.log_event", new_callable=AsyncMock),
        ):
            resp = await client.put(
                "/api/v1/tools/PVT_123/tool-1",
                json={"name": "updated-tool"},
            )
        assert resp.status_code == 200
        assert resp.json()["name"] == "updated-tool"

    async def test_update_tool_not_found(self, client, mock_github_service):
        mock_github_service.get_project_repository.return_value = ("octo", "widgets")

        with patch(
            "src.api.tools.ToolsService.update_tool",
            AsyncMock(side_effect=LookupError("not found")),
        ):
            resp = await client.put(
                "/api/v1/tools/PVT_123/tool-1",
                json={"name": "updated-tool"},
            )
        assert resp.status_code == 404

    async def test_update_tool_duplicate_name(self, client, mock_github_service):
        from src.services.tools.service import DuplicateToolNameError

        mock_github_service.get_project_repository.return_value = ("octo", "widgets")

        with patch(
            "src.api.tools.ToolsService.update_tool",
            AsyncMock(side_effect=DuplicateToolNameError("dupe")),
        ):
            resp = await client.put(
                "/api/v1/tools/PVT_123/tool-1",
                json={"name": "dupe"},
            )
        assert resp.status_code == 409

    async def test_list_tools_returns_result(self, client):
        list_resp = McpToolConfigListResponse(
            tools=[self._make_tool_response()],
            count=1,
        )
        with patch("src.api.tools.ToolsService.list_tools", AsyncMock(return_value=list_resp)):
            resp = await client.get("/api/v1/tools/PVT_123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1

    async def test_list_tools_with_pagination(self, client):
        tools = [self._make_tool_response(id=f"tool-{i}") for i in range(3)]
        list_resp = McpToolConfigListResponse(tools=tools, count=3)
        with patch("src.api.tools.ToolsService.list_tools", AsyncMock(return_value=list_resp)):
            resp = await client.get("/api/v1/tools/PVT_123", params={"limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tools"]) == 2
        assert data["count"] == 3
