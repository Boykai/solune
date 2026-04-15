"""Tests for MCP catalog service (src/services/tools/catalog.py).

Covers:
- _slugify() — slug generation
- _normalize_server() — upstream Glama payload parsing
- build_import_config() — install config → McpToolConfigCreate mapping
- _map_catalog_fetch_error() — upstream error translation
- validate_upstream_url() — SSRF protection
- list_catalog_servers() — cached browse with already_installed detection
- browse/import API endpoints
"""

import json
from typing import Any
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
    _map_catalog_fetch_error,
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


# ── Unit Tests: _slugify ──────────────────────────────────────────────────


class TestSlugify:
    def test_basic_slugify(self):
        assert _slugify("GitHub MCP") == "github-mcp"

    def test_special_characters_stripped(self):
        assert _slugify("My Tool (v2.0)!") == "my-tool-v2-0"

    def test_leading_trailing_hyphens_stripped(self):
        assert _slugify("--test--") == "test"

    def test_empty_string(self):
        assert _slugify("") == ""

    def test_whitespace_becomes_hyphens(self):
        assert _slugify("hello   world") == "hello-world"

    def test_consecutive_special_chars_collapse(self):
        assert _slugify("a@#$b") == "a-b"


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
        server = _normalize_server(
            {
                "id": "test",
                "name": "Test",
                "install_config": {"url": "https://example.com/mcp"},
            }
        )
        assert server is not None
        assert server.install_config.transport == "http"

    def test_infers_transport_from_command(self):
        server = _normalize_server(
            {
                "id": "test",
                "name": "Test",
                "install_config": {"command": "npx", "args": ["-y", "some-pkg"]},
            }
        )
        assert server is not None
        assert server.install_config.transport == "stdio"

    def test_quality_score_converted_to_string(self):
        server = _normalize_server(
            {
                "id": "test",
                "name": "Test",
                "quality_score": 95,
                "install_config": {"transport": "http", "url": "https://example.com"},
            }
        )
        assert server is not None
        assert server.quality_score == "95"

    def test_title_field_used_as_name(self):
        server = _normalize_server(
            {
                "id": "test",
                "title": "Title Based",
                "install_config": {"transport": "http", "url": "https://example.com"},
            }
        )
        assert server is not None
        assert server.name == "Title Based"

    def test_summary_field_used_as_description(self):
        server = _normalize_server(
            {
                "id": "test",
                "name": "Test",
                "summary": "A summary field",
                "install_config": {"transport": "http", "url": "https://example.com"},
            }
        )
        assert server is not None
        assert server.description == "A summary field"

    def test_description_defaults_to_name(self):
        server = _normalize_server(
            {
                "id": "test",
                "name": "Fallback Name",
                "install_config": {"transport": "http", "url": "https://example.com"},
            }
        )
        assert server is not None
        assert server.description == "Fallback Name"

    def test_repository_field_used_as_repo_url(self):
        server = _normalize_server(
            {
                "id": "test",
                "name": "Test",
                "repository": "https://github.com/test/repo",
                "install_config": {"transport": "http", "url": "https://example.com"},
            }
        )
        assert server is not None
        assert server.repo_url == "https://github.com/test/repo"

    def test_github_url_field_used_as_repo_url(self):
        server = _normalize_server(
            {
                "id": "test",
                "name": "Test",
                "github_url": "https://github.com/test/repo2",
                "install_config": {"transport": "http", "url": "https://example.com"},
            }
        )
        assert server is not None
        assert server.repo_url == "https://github.com/test/repo2"

    def test_non_https_repo_url_is_dropped(self):
        server = _normalize_server(
            {
                "id": "test",
                "name": "Test",
                "repo_url": "javascript:alert(1)",
                "install_config": {"transport": "http", "url": "https://example.com"},
            }
        )
        assert server is not None
        assert server.repo_url is None

    def test_tags_fallback_for_category(self):
        server = _normalize_server(
            {
                "id": "test",
                "name": "Test",
                "tags": ["AI", "Search"],
                "install_config": {"transport": "http", "url": "https://example.com"},
            }
        )
        assert server is not None
        assert server.category == "AI"

    def test_category_preferred_over_tags(self):
        server = _normalize_server(
            {
                "id": "test",
                "name": "Test",
                "category": "Developer Tools",
                "tags": ["AI", "Search"],
                "install_config": {"transport": "http", "url": "https://example.com"},
            }
        )
        assert server is not None
        assert server.category == "Developer Tools"

    def test_json_string_install_config(self):
        server = _normalize_server(
            {
                "id": "test",
                "name": "Test",
                "install_config": '{"transport": "http", "url": "https://example.com/mcp"}',
            }
        )
        assert server is not None
        assert server.install_config.transport == "http"
        assert server.install_config.url == "https://example.com/mcp"

    def test_invalid_json_string_config_defaults_to_unknown_transport(self):
        server = _normalize_server(
            {
                "id": "test",
                "name": "Test",
                "install_config": "not valid json",
            }
        )
        assert server is not None
        assert server.install_config.transport == "unknown"

    def test_config_field_alias(self):
        """Upstream may use 'config' instead of 'install_config'."""
        server = _normalize_server(
            {
                "id": "test",
                "name": "Test",
                "config": {"transport": "sse", "url": "https://example.com/sse"},
            }
        )
        assert server is not None
        assert server.install_config.transport == "sse"

    def test_type_field_alias_for_transport(self):
        """Upstream may use 'type' instead of 'transport' in config."""
        server = _normalize_server(
            {
                "id": "test",
                "name": "Test",
                "install_config": {"type": "http", "url": "https://example.com"},
            }
        )
        assert server is not None
        assert server.install_config.transport == "http"

    def test_unsupported_transport_maps_to_remote_server_type(self):
        server = _normalize_server(
            {
                "id": "test",
                "name": "Test",
                "install_config": {"transport": "grpc", "url": "https://example.com"},
            }
        )
        assert server is not None
        assert server.server_type == "remote"

    def test_no_install_config_at_all(self):
        server = _normalize_server(
            {
                "id": "test",
                "name": "Test",
            }
        )
        assert server is not None
        assert server.install_config.transport == "unknown"
        assert server.server_type == "remote"

    def test_id_generated_from_name_if_missing(self):
        server = _normalize_server(
            {
                "name": "My Cool Server",
                "install_config": {"transport": "http", "url": "https://example.com"},
            }
        )
        assert server is not None
        assert server.id == "my-cool-server"

    def test_non_list_args_treated_as_empty(self):
        server = _normalize_server(
            {
                "id": "test",
                "name": "Test",
                "install_config": {"transport": "stdio", "command": "npx", "args": "invalid"},
            }
        )
        assert server is not None
        assert server.install_config.args == []

    def test_non_dict_env_treated_as_empty(self):
        server = _normalize_server(
            {
                "id": "test",
                "name": "Test",
                "install_config": {"transport": "http", "url": "https://x.com", "env": "invalid"},
            }
        )
        assert server is not None
        assert server.install_config.env == {}


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
        server_config = next(iter(parsed["mcpServers"].values()))
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
        server_config = next(iter(parsed["mcpServers"].values()))
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
        server_config = next(iter(parsed["mcpServers"].values()))
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

    def test_http_with_headers_and_tools(self):
        server = CatalogMcpServer(
            id="test",
            name="Rich HTTP",
            description="HTTP with extras",
            server_type="http",
            install_config=CatalogInstallConfig(
                transport="http",
                url="https://example.com/mcp",
                headers={"Authorization": "Bearer $TOKEN"},
                tools=["tool1", "tool2"],
                env={"API_KEY": "xxx"},
            ),
        )
        result = build_import_config(server)
        parsed = json.loads(result.config_content)
        server_config = next(iter(parsed["mcpServers"].values()))
        assert server_config["headers"] == {"Authorization": "Bearer $TOKEN"}
        assert server_config["tools"] == ["tool1", "tool2"]
        assert server_config["env"] == {"API_KEY": "xxx"}

    def test_stdio_with_env_and_tools(self):
        server = CatalogMcpServer(
            id="test",
            name="Rich Stdio",
            description="Stdio with extras",
            server_type="stdio",
            install_config=CatalogInstallConfig(
                transport="stdio",
                command="npx",
                args=["-y", "pkg"],
                env={"HOME": "/tmp"},
                tools=["mytool"],
            ),
        )
        result = build_import_config(server)
        parsed = json.loads(result.config_content)
        server_config = next(iter(parsed["mcpServers"].values()))
        assert server_config["args"] == ["-y", "pkg"]
        assert server_config["env"] == {"HOME": "/tmp"}
        assert server_config["tools"] == ["mytool"]

    def test_local_transport(self):
        server = CatalogMcpServer(
            id="test",
            name="Local Server",
            description="Local transport server",
            server_type="local",
            install_config=CatalogInstallConfig(
                transport="local",
                command="/usr/local/bin/server",
            ),
        )
        result = build_import_config(server)
        parsed = json.loads(result.config_content)
        server_config = next(iter(parsed["mcpServers"].values()))
        assert server_config["type"] == "local"
        assert server_config["command"] == "/usr/local/bin/server"

    def test_server_name_slug_in_config_content(self):
        server = CatalogMcpServer(
            id="test",
            name="My Cool Server",
            description="Test",
            server_type="http",
            install_config=CatalogInstallConfig(
                transport="http",
                url="https://example.com/mcp",
            ),
        )
        result = build_import_config(server)
        parsed = json.loads(result.config_content)
        assert "my-cool-server" in parsed["mcpServers"]

    def test_github_repo_target_is_empty_string(self):
        server = CatalogMcpServer(
            id="test",
            name="Test",
            description="Test",
            server_type="http",
            install_config=CatalogInstallConfig(
                transport="http",
                url="https://example.com/mcp",
            ),
        )
        result = build_import_config(server)
        assert result.github_repo_target == ""


# ── Unit Tests: _map_catalog_fetch_error ─────────────────────────────────


class TestMapCatalogFetchError:
    def test_http_status_error_returns_502(self):
        response = httpx.Response(500, request=httpx.Request("GET", "https://glama.ai/api"))
        exc = httpx.HTTPStatusError("Server Error", request=response.request, response=response)
        result = _map_catalog_fetch_error(exc)
        assert isinstance(result, CatalogUnavailableError)
        assert result.message == "MCP catalog is temporarily unavailable."
        assert result.status_code == 502
        assert result.details["upstream_status"] == 500

    def test_http_404_gives_specific_message(self):
        response = httpx.Response(404, request=httpx.Request("GET", "https://glama.ai/api"))
        exc = httpx.HTTPStatusError("Not Found", request=response.request, response=response)
        result = _map_catalog_fetch_error(exc)
        assert "could not be found" in result.details["reason"]

    def test_timeout_returns_503(self):
        exc = httpx.ReadTimeout("timed out")
        result = _map_catalog_fetch_error(exc)
        assert isinstance(result, CatalogUnavailableError)
        assert result.status_code == 503
        assert "timed out" in result.details["reason"]

    def test_connect_error_returns_503(self):
        exc = httpx.ConnectError("connection refused")
        result = _map_catalog_fetch_error(exc)
        assert result.status_code == 503
        assert "could not be reached" in result.details["reason"]

    def test_request_error_returns_503(self):
        exc = httpx.RequestError("request failed")
        result = _map_catalog_fetch_error(exc)
        assert result.status_code == 503
        assert "request failed" in result.details["reason"]

    def test_generic_exception_returns_503(self):
        exc = RuntimeError("something unexpected")
        result = _map_catalog_fetch_error(exc)
        assert result.status_code == 503
        assert "could not be loaded" in result.details["reason"]


class TestFetchGlamaServers:
    async def test_invalid_json_returns_502_catalog_error(self):
        mock_cache = InMemoryCache()
        request = httpx.Request("GET", "https://glama.ai/api/mcp/v1/servers")
        response = httpx.Response(200, request=request, text="not json")

        class MockClient:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get(self, url, params=None):
                return response

        with patch("src.services.tools.catalog.httpx.AsyncClient", MockClient):
            with pytest.raises(CatalogUnavailableError) as exc_info:
                await list_catalog_servers("proj-1", set(), cache_instance=mock_cache)

        assert exc_info.value.status_code == 502
        assert exc_info.value.message == "MCP catalog upstream returned an invalid response."

    async def test_fetch_disables_redirects(self):
        mock_cache = InMemoryCache()
        request = httpx.Request("GET", "https://glama.ai/api/mcp/v1/servers")
        response = httpx.Response(200, request=request, json=[])
        captured_kwargs: dict[str, Any] = {}

        class MockClient:
            def __init__(self, **kwargs):
                captured_kwargs.update(kwargs)

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get(self, url, params=None):
                return response

        with patch("src.services.tools.catalog.httpx.AsyncClient", MockClient):
            result = await list_catalog_servers(
                "proj-1",
                set(),
                query="github",
                cache_instance=mock_cache,
            )

        assert result.count == 0
        assert captured_kwargs["follow_redirects"] is False


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

    def test_empty_string_rejected(self):
        with pytest.raises(ValueError):
            validate_upstream_url("")

    def test_localhost_rejected(self):
        with pytest.raises(ValueError, match="not in the allowed list"):
            validate_upstream_url("https://localhost/api")

    def test_private_ip_rejected(self):
        with pytest.raises(ValueError, match="not in the allowed list"):
            validate_upstream_url("https://192.168.1.1/api")


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
            entry = mock_cache.get_entry(f"{CATALOG_CACHE_KEY}::")
            assert entry is not None
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

    async def test_case_insensitive_already_installed(self):
        """Matching should be case-insensitive: 'github mcp' matches 'GitHub MCP'."""
        mock_cache = InMemoryCache()

        with patch(
            "src.services.tools.catalog._fetch_glama_servers",
            new_callable=AsyncMock,
            return_value=[SAMPLE_GLAMA_SERVER],
        ):
            result = await list_catalog_servers(
                "proj-1",
                {"github mcp"},  # lowercase
                cache_instance=mock_cache,
            )

        assert result.servers[0].already_installed is True

    async def test_skips_servers_without_name(self):
        mock_cache = InMemoryCache()

        with patch(
            "src.services.tools.catalog._fetch_glama_servers",
            new_callable=AsyncMock,
            return_value=[
                {"id": "no-name", "install_config": {"transport": "http", "url": "https://x.com"}},
                SAMPLE_GLAMA_SERVER,
            ],
        ):
            result = await list_catalog_servers(
                "proj-1",
                set(),
                cache_instance=mock_cache,
            )

        assert result.count == 1
        assert result.servers[0].name == "GitHub MCP"

    async def test_category_passed_to_response(self):
        mock_cache = InMemoryCache()

        with patch(
            "src.services.tools.catalog._fetch_glama_servers",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await list_catalog_servers(
                "proj-1",
                set(),
                category="Developer Tools",
                cache_instance=mock_cache,
            )

        assert result.category == "Developer Tools"

    async def test_empty_query_returns_none_in_response(self):
        mock_cache = InMemoryCache()

        with patch(
            "src.services.tools.catalog._fetch_glama_servers",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await list_catalog_servers(
                "proj-1",
                set(),
                cache_instance=mock_cache,
            )

        assert result.query is None
        assert result.category is None


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
                    list_tools=AsyncMock(return_value=MagicMock(tools=[])),
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
            servers=[],
            count=0,
            query="github",
            category=None,
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
            resp = await client.get("/api/v1/tools/proj-1/catalog?query=github")

        assert resp.status_code == 200
        assert resp.json()["query"] == "github"

    async def test_browse_catalog_upstream_error(self, client):
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

    async def test_import_uses_catalog_server_from_request_when_provided(
        self, client, mock_github_service
    ):
        mock_github_service.get_project_repository.return_value = ("octo", "widgets")
        request_server = {
            "id": "test-mcp",
            "name": "Test MCP",
            "description": "A test server",
            "server_type": "http",
            "install_config": {
                "transport": "http",
                "url": "https://example.com/mcp",
            },
            "already_installed": False,
        }
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
            ) as list_catalog_servers_mock,
        ):
            resp = await client.post(
                "/api/v1/tools/proj-1/catalog/import",
                json={
                    "catalog_server_id": "test-mcp",
                    "catalog_server": request_server,
                },
            )

        assert resp.status_code == 201
        assert resp.json()["name"] == "Test MCP"
        list_catalog_servers_mock.assert_not_awaited()

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
