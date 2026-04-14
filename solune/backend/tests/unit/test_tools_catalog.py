"""Tests for MCP catalog service (src/services/tools/catalog.py).

Covers:
- _normalize_server() — upstream Glama payload parsing
- build_import_config() — install config → McpToolConfigCreate mapping
- list_catalog_servers() — cached browse with already_installed detection
- browse/import API endpoints
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.exceptions import CatalogUnavailableError, ValidationError
from src.models.tools import (
    CatalogInstallConfig,
    CatalogMcpServer,
    CatalogMcpServerListResponse,
    McpToolConfigResponse,
)
from src.services.cache import InMemoryCache
from src.services.tools.catalog import (
    CATALOG_CACHE_KEY,
    _normalize_server,
    _slugify,
    build_import_config,
    list_catalog_servers,
    validate_upstream_url,
)


# ── Helper fixtures ──────────────────────────────────────────────────────

SAMPLE_GLAMA_SERVER = {
    "id": "github-mcp",
    "name": "GitHub MCP",
    "description": "GitHub integration for Copilot",
    "repo_url": "https://github.com/github/github-mcp-server",
    "category": "Developer Tools",
    "quality_score": "A",
    "install_config": {
        "transport": "http",
        "url": "https://api.githubcopilot.com/mcp",
    },
}

SAMPLE_STDIO_SERVER = {
    "id": "context7-mcp",
    "name": "Context7",
    "description": "Documentation search",
    "category": "Documentation",
    "quality_score": "B",
    "install_config": {
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@context7/mcp-server"],
    },
}


# ── Unit Tests: _normalize_server ────────────────────────────────────────


class TestNormalizeServer:
    def test_http_server(self):
        server = _normalize_server(SAMPLE_GLAMA_SERVER)
        assert server is not None
        assert server.id == "github-mcp"
        assert server.name == "GitHub MCP"
        assert server.server_type == "http"
        assert server.install_config.transport == "http"
        assert server.install_config.url == "https://api.githubcopilot.com/mcp"

    def test_stdio_server(self):
        server = _normalize_server(SAMPLE_STDIO_SERVER)
        assert server is not None
        assert server.server_type == "stdio"
        assert server.install_config.command == "npx"
        assert server.install_config.args == ["-y", "@context7/mcp-server"]

    def test_missing_name_returns_none(self):
        assert _normalize_server({}) is None
        assert _normalize_server({"description": "no name"}) is None

    def test_infers_transport_from_url(self):
        server = _normalize_server({
            "id": "test",
            "name": "Test",
            "install_config": {"url": "https://example.com/mcp"},
        })
        assert server is not None
        assert server.install_config.transport == "http"

    def test_infers_transport_from_command(self):
        server = _normalize_server({
            "id": "test",
            "name": "Test",
            "install_config": {"command": "npx", "args": ["-y", "some-pkg"]},
        })
        assert server is not None
        assert server.install_config.transport == "stdio"

    def test_quality_score_converted_to_string(self):
        server = _normalize_server({
            "id": "test",
            "name": "Test",
            "quality_score": 95,
            "install_config": {"transport": "http", "url": "https://example.com"},
        })
        assert server is not None
        assert server.quality_score == "95"


# ── Unit Tests: build_import_config ──────────────────────────────────────


class TestBuildImportConfig:
    def test_http_transport(self):
        server = CatalogMcpServer(
            id="test",
            name="Test HTTP",
            description="A test server",
            server_type="http",
            install_config=CatalogInstallConfig(
                transport="http",
                url="https://example.com/mcp",
            ),
        )
        result = build_import_config(server)
        assert result.name == "Test HTTP"
        parsed = json.loads(result.config_content)
        assert "mcpServers" in parsed
        server_config = list(parsed["mcpServers"].values())[0]
        assert server_config["type"] == "http"
        assert server_config["url"] == "https://example.com/mcp"

    def test_sse_transport(self):
        server = CatalogMcpServer(
            id="test",
            name="Test SSE",
            description="SSE server",
            server_type="sse",
            install_config=CatalogInstallConfig(
                transport="sse",
                url="https://example.com/sse",
            ),
        )
        result = build_import_config(server)
        parsed = json.loads(result.config_content)
        server_config = list(parsed["mcpServers"].values())[0]
        assert server_config["type"] == "sse"
        assert server_config["url"] == "https://example.com/sse"

    def test_stdio_transport(self):
        server = CatalogMcpServer(
            id="test",
            name="Test Stdio",
            description="Stdio server",
            server_type="stdio",
            install_config=CatalogInstallConfig(
                transport="stdio",
                command="npx",
                args=["-y", "test-pkg"],
            ),
        )
        result = build_import_config(server)
        parsed = json.loads(result.config_content)
        server_config = list(parsed["mcpServers"].values())[0]
        assert server_config["type"] == "stdio"
        assert server_config["command"] == "npx"
        assert server_config["args"] == ["-y", "test-pkg"]

    def test_http_without_url_raises(self):
        server = CatalogMcpServer(
            id="test",
            name="Bad HTTP",
            description="No URL",
            server_type="http",
            install_config=CatalogInstallConfig(transport="http"),
        )
        with pytest.raises(ValidationError):
            build_import_config(server)

    def test_stdio_without_command_raises(self):
        server = CatalogMcpServer(
            id="test",
            name="Bad Stdio",
            description="No command",
            server_type="stdio",
            install_config=CatalogInstallConfig(transport="stdio"),
        )
        with pytest.raises(ValidationError):
            build_import_config(server)

    def test_unsupported_transport_raises(self):
        server = CatalogMcpServer(
            id="test",
            name="Bad",
            description="Unsupported",
            server_type="unknown",
            install_config=CatalogInstallConfig(transport="grpc"),
        )
        with pytest.raises(ValidationError, match="Unsupported transport"):
            build_import_config(server)


# ── Unit Tests: validate_upstream_url ────────────────────────────────────


class TestValidateUpstreamUrl:
    def test_valid_glama_url(self):
        validate_upstream_url("https://glama.ai/api/mcp/v1/servers")

    def test_http_rejected(self):
        with pytest.raises(ValueError, match="HTTPS"):
            validate_upstream_url("http://glama.ai/api/mcp/v1/servers")

    def test_non_allowed_host_rejected(self):
        with pytest.raises(ValueError, match="not in the allowed list"):
            validate_upstream_url("https://evil.example.com/api")


# ── Integration: list_catalog_servers ────────────────────────────────────


class TestListCatalogServers:
    async def test_returns_normalized_servers(self):
        mock_cache = InMemoryCache()

        with patch(
            "src.services.tools.catalog._fetch_glama_servers",
            new_callable=AsyncMock,
            return_value=[SAMPLE_GLAMA_SERVER, SAMPLE_STDIO_SERVER],
        ):
            result = await list_catalog_servers(
                "proj-1",
                set(),
                cache_instance=mock_cache,
            )

        assert result.count == 2
        assert result.servers[0].name == "GitHub MCP"
        assert result.servers[1].name == "Context7"

    async def test_marks_already_installed(self):
        mock_cache = InMemoryCache()

        with patch(
            "src.services.tools.catalog._fetch_glama_servers",
            new_callable=AsyncMock,
            return_value=[SAMPLE_GLAMA_SERVER],
        ):
            result = await list_catalog_servers(
                "proj-1",
                {"GitHub MCP"},
                cache_instance=mock_cache,
            )

        assert result.servers[0].already_installed is True

    async def test_stale_fallback_on_error(self):
        mock_cache = InMemoryCache()

        # Populate cache
        with patch(
            "src.services.tools.catalog._fetch_glama_servers",
            new_callable=AsyncMock,
            return_value=[SAMPLE_GLAMA_SERVER],
        ):
            await list_catalog_servers("proj-1", set(), cache_instance=mock_cache)

        # Second call fails but uses stale data
        with patch(
            "src.services.tools.catalog._fetch_glama_servers",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("down"),
        ):
            # Expire the cache entry
            for entry in mock_cache._cache.values():
                from datetime import timedelta
                entry.expires_at = entry.expires_at - timedelta(hours=2)

            result = await list_catalog_servers(
                "proj-1",
                set(),
                cache_instance=mock_cache,
            )
            assert result.count == 1

    async def test_upstream_error_without_cache_raises(self):
        mock_cache = InMemoryCache()

        with (
            patch(
                "src.services.tools.catalog._fetch_glama_servers",
                new_callable=AsyncMock,
                side_effect=httpx.ConnectError("down"),
            ),
            pytest.raises(CatalogUnavailableError),
        ):
            await list_catalog_servers("proj-1", set(), cache_instance=mock_cache)

    async def test_query_filtering(self):
        mock_cache = InMemoryCache()

        with patch(
            "src.services.tools.catalog._fetch_glama_servers",
            new_callable=AsyncMock,
            return_value=[SAMPLE_GLAMA_SERVER],
        ) as mock_fetch:
            result = await list_catalog_servers(
                "proj-1",
                set(),
                query="github",
                cache_instance=mock_cache,
            )
            mock_fetch.assert_called_once_with(query="github", category="")

        assert result.query == "github"


# ── API endpoint tests ───────────────────────────────────────────────────


class TestBrowseCatalogApi:
    async def test_browse_catalog_success(self, client):
        mock_servers = CatalogMcpServerListResponse(
            servers=[
                CatalogMcpServer(
                    id="test-mcp",
                    name="Test MCP",
                    description="A test MCP server",
                    server_type="http",
                    install_config=CatalogInstallConfig(
                        transport="http",
                        url="https://example.com/mcp",
                    ),
                ),
            ],
            count=1,
            query=None,
            category=None,
        )

        with (
            patch(
                "src.api.tools._get_service",
                return_value=MagicMock(
                    list_tools=AsyncMock(
                        return_value=MagicMock(tools=[])
                    ),
                ),
            ),
            patch(
                "src.services.tools.catalog.list_catalog_servers",
                new_callable=AsyncMock,
                return_value=mock_servers,
            ),
        ):
            resp = await client.get("/api/v1/tools/proj-1/catalog")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["servers"][0]["name"] == "Test MCP"

    async def test_browse_catalog_with_query(self, client):
        mock_servers = CatalogMcpServerListResponse(
            servers=[], count=0, query="github", category=None,
        )

        with (
            patch(
                "src.api.tools._get_service",
                return_value=MagicMock(
                    list_tools=AsyncMock(
                        return_value=MagicMock(tools=[])
                    ),
                ),
            ),
            patch(
                "src.services.tools.catalog.list_catalog_servers",
                new_callable=AsyncMock,
                return_value=mock_servers,
            ),
        ):
            resp = await client.get("/api/v1/tools/proj-1/catalog?query=github")

        assert resp.status_code == 200
        assert resp.json()["query"] == "github"

    async def test_browse_catalog_upstream_error(self, client):
        with (
            patch(
                "src.api.tools._get_service",
                return_value=MagicMock(
                    list_tools=AsyncMock(
                        return_value=MagicMock(tools=[])
                    ),
                ),
            ),
            patch(
                "src.services.tools.catalog.list_catalog_servers",
                new_callable=AsyncMock,
                side_effect=CatalogUnavailableError(
                    status_code=503,
                    details={"reason": "unavailable"},
                ),
            ),
        ):
            resp = await client.get("/api/v1/tools/proj-1/catalog")

        assert resp.status_code == 503


class TestImportFromCatalogApi:
    async def test_import_success(self, client, mock_github_service):
        mock_github_service.get_project_repository.return_value = ("octo", "widgets")
        mock_servers = CatalogMcpServerListResponse(
            servers=[
                CatalogMcpServer(
                    id="test-mcp",
                    name="Test MCP",
                    description="A test server",
                    server_type="http",
                    install_config=CatalogInstallConfig(
                        transport="http",
                        url="https://example.com/mcp",
                    ),
                    already_installed=False,
                ),
            ],
            count=1,
        )

        mock_tool_response = McpToolConfigResponse(
            id="tool-abc",
            name="Test MCP",
            description="A test server",
            endpoint_url="https://example.com/mcp",
            config_content='{"mcpServers":{"test-mcp":{"type":"http","url":"https://example.com/mcp"}}}',
            sync_status="pending",
            sync_error="",
            synced_at=None,
            github_repo_target="",
            is_active=True,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )

        with (
            patch(
                "src.api.tools._get_service",
                return_value=MagicMock(
                    list_tools=AsyncMock(return_value=MagicMock(tools=[])),
                    create_tool=AsyncMock(return_value=mock_tool_response),
                ),
            ),
            patch(
                "src.services.tools.catalog.list_catalog_servers",
                new_callable=AsyncMock,
                return_value=mock_servers,
            ),
        ):
            resp = await client.post(
                "/api/v1/tools/proj-1/catalog/import",
                json={"catalog_server_id": "test-mcp"},
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test MCP"

    async def test_import_not_found(self, client, mock_github_service):
        mock_github_service.get_project_repository.return_value = ("octo", "widgets")
        mock_servers = CatalogMcpServerListResponse(servers=[], count=0)

        with (
            patch(
                "src.api.tools._get_service",
                return_value=MagicMock(
                    list_tools=AsyncMock(return_value=MagicMock(tools=[])),
                ),
            ),
            patch(
                "src.services.tools.catalog.list_catalog_servers",
                new_callable=AsyncMock,
                return_value=mock_servers,
            ),
        ):
            resp = await client.post(
                "/api/v1/tools/proj-1/catalog/import",
                json={"catalog_server_id": "nonexistent"},
            )

        assert resp.status_code == 404

    async def test_import_already_installed(self, client, mock_github_service):
        mock_github_service.get_project_repository.return_value = ("octo", "widgets")
        mock_servers = CatalogMcpServerListResponse(
            servers=[
                CatalogMcpServer(
                    id="test-mcp",
                    name="Test MCP",
                    description="A test server",
                    server_type="http",
                    install_config=CatalogInstallConfig(
                        transport="http",
                        url="https://example.com/mcp",
                    ),
                    already_installed=True,
                ),
            ],
            count=1,
        )

        with (
            patch(
                "src.api.tools._get_service",
                return_value=MagicMock(
                    list_tools=AsyncMock(return_value=MagicMock(tools=[])),
                ),
            ),
            patch(
                "src.services.tools.catalog.list_catalog_servers",
                new_callable=AsyncMock,
                return_value=mock_servers,
            ),
        ):
            resp = await client.post(
                "/api/v1/tools/proj-1/catalog/import",
                json={"catalog_server_id": "test-mcp"},
            )

        assert resp.status_code == 409
