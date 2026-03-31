"""Tests for MCP agent tools — list_agents and create_agent."""

from unittest.mock import AsyncMock, MagicMock, patch

from src.services.mcp_server.context import McpContext
from src.services.mcp_server.tools.agents import create_agent, list_agents


def _make_ctx(mcp_ctx: McpContext | None = None) -> MagicMock:
    ctx = MagicMock()
    if mcp_ctx is None:
        mcp_ctx = McpContext(
            github_token="ghp_testtoken", github_user_id=42, github_login="testuser"
        )
    ctx.request_context.lifespan_context = {"mcp_context": mcp_ctx}
    return ctx


class TestListAgents:
    @patch(
        "src.services.mcp_server.tools.agents.verify_mcp_project_access",
        new_callable=AsyncMock,
    )
    @patch("src.utils.resolve_repository", new_callable=AsyncMock)
    @patch("src.services.agents.service.AgentsService")
    @patch("src.services.database.get_db")
    async def test_returns_agents_for_resolved_repository(
        self,
        mock_get_db,
        MockAgentsService,
        mock_resolve_repository,
        mock_access,
    ):
        mock_resolve_repository.return_value = ("octocat", "solune")
        mock_agent = MagicMock()
        mock_agent.model_dump.return_value = {"id": "agent-1", "name": "Reviewer"}
        MockAgentsService.return_value.list_agents = AsyncMock(return_value=[mock_agent])

        result = await list_agents(_make_ctx(), "PVT_abc")

        assert result == {
            "project_id": "PVT_abc",
            "agents": [{"id": "agent-1", "name": "Reviewer"}],
        }
        mock_access.assert_awaited_once()
        mock_resolve_repository.assert_awaited_once_with("ghp_testtoken", "PVT_abc")
        MockAgentsService.return_value.list_agents.assert_awaited_once_with(
            project_id="PVT_abc",
            owner="octocat",
            repo="solune",
            access_token="ghp_testtoken",
        )
        mock_get_db.assert_called_once_with()


class TestCreateAgent:
    @patch(
        "src.services.mcp_server.tools.agents.verify_mcp_project_access",
        new_callable=AsyncMock,
    )
    @patch("src.utils.resolve_repository", new_callable=AsyncMock)
    @patch("src.services.agents.service.AgentsService")
    @patch("src.services.database.get_db")
    async def test_passes_model_through_to_agent_create_payload(
        self,
        mock_get_db,
        MockAgentsService,
        mock_resolve_repository,
        mock_access,
    ):
        mock_resolve_repository.return_value = ("octocat", "solune")
        mock_result = MagicMock(agent_id="agent-1", pr_url="https://example.com/pr/1")
        mock_result.model_dump.return_value = {"agent_id": "agent-1"}
        MockAgentsService.return_value.create_agent = AsyncMock(return_value=mock_result)

        result = await create_agent(
            _make_ctx(),
            project_id="PVT_abc",
            name="Reviewer",
            instructions="Review pull requests",
            model="gpt-5",
        )

        assert result == {
            "agent_id": "agent-1",
            "pr_url": "https://example.com/pr/1",
            "result": {"agent_id": "agent-1"},
        }
        mock_access.assert_awaited_once()
        mock_resolve_repository.assert_awaited_once_with("ghp_testtoken", "PVT_abc")
        call_args = MockAgentsService.return_value.create_agent.await_args
        body = call_args.kwargs["body"]
        assert body.name == "Reviewer"
        assert body.system_prompt == "Review pull requests"
        assert body.default_model_id == "gpt-5"
        assert body.default_model_name == "gpt-5"
        assert call_args.kwargs["access_token"] == "ghp_testtoken"
        assert call_args.kwargs["github_user_id"] == "42"
        mock_get_db.assert_called_once_with()
