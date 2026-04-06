"""Tests for MCP chat tools — send_chat_message, get_metadata, cleanup_preflight."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.mcp_server.context import McpContext
from src.services.mcp_server.tools.chat import (
    cleanup_preflight,
    get_metadata,
    send_chat_message,
)


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
    "src.services.mcp_server.tools.chat.verify_mcp_project_access",
    new_callable=AsyncMock,
)
@patch("src.services.chat_agent.ChatAgentService")
@patch("src.services.database.get_db")
async def test_send_chat_message_returns_response(
    mock_get_db,
    MockChatAgentService,
    mock_access,
):
    mock_result = MagicMock()
    mock_result.content = "Here is the analysis of your project."
    MockChatAgentService.return_value.run = AsyncMock(return_value=mock_result)

    result = await send_chat_message(_make_ctx(), "PVT_abc", "Analyze my project")

    assert result == {
        "response": "Here is the analysis of your project.",
        "project_id": "PVT_abc",
    }
    mock_access.assert_awaited_once()
    MockChatAgentService.return_value.run.assert_awaited_once()
    mock_get_db.assert_called_once_with()


@pytest.mark.asyncio
@patch("src.services.metadata_service.MetadataService")
async def test_get_metadata_returns_model_dump(MockMetadataService):
    mock_result = MagicMock()
    mock_result.model_dump.return_value = {
        "owner": "octocat",
        "repo": "solune",
        "labels": ["bug", "feature"],
    }
    MockMetadataService.return_value.get_or_fetch = AsyncMock(return_value=mock_result)

    result = await get_metadata(_make_ctx(), "octocat", "solune")

    assert result == {
        "owner": "octocat",
        "repo": "solune",
        "labels": ["bug", "feature"],
    }
    MockMetadataService.return_value.get_or_fetch.assert_awaited_once_with(
        "ghp_testtoken", "octocat", "solune"
    )


@pytest.mark.asyncio
@patch(
    "src.services.mcp_server.tools.chat.verify_mcp_project_access",
    new_callable=AsyncMock,
)
@patch("src.utils.resolve_repository", new_callable=AsyncMock)
@patch("src.services.cleanup_service.preflight", new_callable=AsyncMock)
@patch("src.services.github_projects.GitHubProjectsService")
@patch("src.models.cleanup.CleanupPreflightRequest")
async def test_cleanup_preflight_returns_dry_run_summary(
    MockRequest,
    MockGitHubProjectsService,
    mock_preflight,
    mock_resolve_repository,
    mock_access,
):
    mock_resolve_repository.return_value = ("octocat", "solune")
    preflight_result = MagicMock()
    preflight_result.model_dump.return_value = {
        "stale_branches": 3,
        "stale_prs": 1,
    }
    mock_preflight.return_value = preflight_result

    result = await cleanup_preflight(_make_ctx(), "PVT_abc")

    assert result == {"stale_branches": 3, "stale_prs": 1}
    mock_access.assert_awaited_once()
    mock_resolve_repository.assert_awaited_once_with("ghp_testtoken", "PVT_abc")
    mock_preflight.assert_awaited_once()
