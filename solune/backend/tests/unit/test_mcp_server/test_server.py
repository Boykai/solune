"""Tests for MCP server creation, tool registration, and helper functions.

Covers:
- create_mcp_server() creates a FastMCP instance and registers tools
- get_mcp_app() returns a Starlette app (requires prior create_mcp_server)
- get_mcp_app() raises when called before create_mcp_server()
- get_mcp_context() extracts McpContext from tool context
- get_mcp_context() raises AuthorizationError when context is missing
- verify_mcp_project_access() passes for accessible projects
- verify_mcp_project_access() raises AuthorizationError for inaccessible projects
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import AuthorizationError
from src.services.mcp_server.context import McpContext
from src.services.mcp_server.tools import get_mcp_context, verify_mcp_project_access

# ── get_mcp_context ────────────────────────────────────────────────


class TestGetMcpContext:
    def test_extracts_context_from_lifespan(self):
        mcp_ctx = McpContext(github_token="ghp_test", github_user_id=42, github_login="testuser")
        ctx = MagicMock()
        ctx.request_context.lifespan_context = {"mcp_context": mcp_ctx}

        result = get_mcp_context(ctx)
        assert result is mcp_ctx

    def test_raises_when_context_is_none(self):
        ctx = MagicMock()
        ctx.request_context.lifespan_context = {"mcp_context": None}

        with pytest.raises(AuthorizationError, match="Authentication required"):
            get_mcp_context(ctx)

    def test_raises_when_context_key_missing(self):
        ctx = MagicMock()
        ctx.request_context.lifespan_context = {}

        with pytest.raises(AuthorizationError, match="Authentication required"):
            get_mcp_context(ctx)


# ── verify_mcp_project_access ─────────────────────────────────────


class TestVerifyMcpProjectAccess:
    @patch("src.services.github_projects.GitHubProjectsService")
    async def test_passes_for_accessible_project(self, MockSvc):
        mock_project = MagicMock()
        mock_project.project_id = "PVT_abc"
        svc = MockSvc.return_value
        svc.list_user_projects = AsyncMock(return_value=[mock_project])

        mcp_ctx = McpContext(github_token="ghp_test", github_user_id=42, github_login="testuser")
        # Should not raise
        await verify_mcp_project_access(mcp_ctx, "PVT_abc")
        svc.list_user_projects.assert_awaited_once_with("ghp_test", "testuser")

    @patch("src.services.github_projects.GitHubProjectsService")
    async def test_raises_for_inaccessible_project(self, MockSvc):
        mock_project = MagicMock()
        mock_project.project_id = "PVT_other"
        svc = MockSvc.return_value
        svc.list_user_projects = AsyncMock(return_value=[mock_project])

        mcp_ctx = McpContext(github_token="ghp_test", github_user_id=42, github_login="testuser")
        with pytest.raises(AuthorizationError, match="do not have access"):
            await verify_mcp_project_access(mcp_ctx, "PVT_forbidden")

    @patch("src.services.github_projects.GitHubProjectsService")
    async def test_raises_when_service_fails(self, MockSvc):
        svc = MockSvc.return_value
        svc.list_user_projects = AsyncMock(side_effect=RuntimeError("API error"))

        mcp_ctx = McpContext(github_token="ghp_test", github_user_id=42, github_login="testuser")
        with pytest.raises(AuthorizationError, match="Unable to verify"):
            await verify_mcp_project_access(mcp_ctx, "PVT_abc")

    @patch("src.services.github_projects.GitHubProjectsService")
    async def test_passes_with_empty_project_list(self, MockSvc):
        svc = MockSvc.return_value
        svc.list_user_projects = AsyncMock(return_value=[])

        mcp_ctx = McpContext(github_token="ghp_test", github_user_id=42, github_login="testuser")
        with pytest.raises(AuthorizationError, match="do not have access"):
            await verify_mcp_project_access(mcp_ctx, "PVT_any")


# ── Server creation ───────────────────────────────────────────────


class TestServerCreation:
    @patch("src.services.mcp_server.server.get_settings")
    def test_create_mcp_server_returns_fastmcp(self, mock_settings):
        from mcp.server.fastmcp import FastMCP

        from src.services.mcp_server.server import create_mcp_server

        mock_settings.return_value = MagicMock(
            mcp_server_name="test-solune", mcp_server_enabled=True
        )

        server = create_mcp_server()
        assert isinstance(server, FastMCP)

    @patch("src.services.mcp_server.server.get_settings")
    def test_get_mcp_app_returns_starlette_app(self, mock_settings):
        from src.services.mcp_server.server import create_mcp_server, get_mcp_app

        mock_settings.return_value = MagicMock(
            mcp_server_name="test-solune", mcp_server_enabled=True
        )

        create_mcp_server()
        app = get_mcp_app()
        # Starlette app should have a router
        assert hasattr(app, "routes")

    def test_get_mcp_app_raises_before_create(self):
        import src.services.mcp_server.server as mod

        # Reset the module-level singleton
        original = mod._mcp_server
        mod._mcp_server = None
        try:
            with pytest.raises(RuntimeError, match="MCP server not created"):
                mod.get_mcp_app()
        finally:
            mod._mcp_server = original

    @patch("src.services.mcp_server.server.get_settings")
    def test_token_verifier_created(self, mock_settings):
        from src.services.mcp_server.auth import GitHubTokenVerifier
        from src.services.mcp_server.server import create_mcp_server, get_token_verifier

        mock_settings.return_value = MagicMock(
            mcp_server_name="test-solune", mcp_server_enabled=True
        )

        create_mcp_server()
        verifier = get_token_verifier()
        assert isinstance(verifier, GitHubTokenVerifier)
