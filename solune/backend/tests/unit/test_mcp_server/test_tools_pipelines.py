"""Tests for MCP pipeline tools — list_pipelines, launch_pipeline, get_pipeline_states, retry_pipeline.

Covers:
- Service delegation (correct methods called)
- Structured return data
- Project access validation
"""

from unittest.mock import AsyncMock, MagicMock, patch

from src.services.mcp_server.context import McpContext
from src.services.mcp_server.tools.pipelines import (
    get_pipeline_states,
    launch_pipeline,
    list_pipelines,
    retry_pipeline,
)


def _make_ctx(mcp_ctx: McpContext | None = None) -> MagicMock:
    ctx = MagicMock()
    if mcp_ctx is None:
        mcp_ctx = McpContext(
            github_token="ghp_testtoken", github_user_id=42, github_login="testuser"
        )
    ctx.request_context.lifespan_context = {"mcp_context": mcp_ctx}
    return ctx


# ── list_pipelines ─────────────────────────────────────────────────


class TestListPipelines:
    @patch(
        "src.services.mcp_server.tools.pipelines.verify_mcp_project_access",
        new_callable=AsyncMock,
    )
    @patch("src.services.pipelines.service.PipelineService")
    @patch("src.services.database.get_db")
    async def test_returns_pipeline_list(self, mock_get_db, MockPipeSvc, mock_access):
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"pipelines": [{"id": "easy", "name": "Easy"}]}
        MockPipeSvc.return_value.list_pipelines = AsyncMock(return_value=mock_result)

        ctx = _make_ctx()
        result = await list_pipelines(ctx, "PVT_abc")

        assert result["project_id"] == "PVT_abc"
        mock_access.assert_awaited_once()


# ── launch_pipeline ────────────────────────────────────────────────


class TestLaunchPipeline:
    @patch(
        "src.services.mcp_server.tools.pipelines.verify_mcp_project_access",
        new_callable=AsyncMock,
    )
    @patch("src.api.pipelines.execute_pipeline_launch")
    async def test_launches_pipeline(self, mock_launch, mock_access):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.issue_number = 42
        mock_result.issue_url = "https://github.com/owner/repo/issues/42"
        mock_result.message = "Pipeline launched"
        mock_launch.return_value = mock_result

        ctx = _make_ctx()
        result = await launch_pipeline(ctx, "PVT_abc", "easy", "Build a widget")

        assert result["success"] is True
        assert result["issue_number"] == 42
        mock_launch.assert_awaited_once()
        # Verify session was constructed correctly
        call_kwargs = mock_launch.call_args.kwargs
        assert call_kwargs["project_id"] == "PVT_abc"
        assert call_kwargs["pipeline_id"] == "easy"
        assert call_kwargs["issue_description"] == "Build a widget"


# ── get_pipeline_states ────────────────────────────────────────────


class TestGetPipelineStates:
    @patch(
        "src.services.mcp_server.tools.pipelines.verify_mcp_project_access",
        new_callable=AsyncMock,
    )
    @patch("src.services.pipeline_state_store.get_all_pipeline_states")
    async def test_returns_filtered_states(self, mock_get_states, mock_access):
        state_1 = MagicMock()
        state_1.project_id = "PVT_abc"
        state_1.model_dump.return_value = {"stage": "running"}

        state_2 = MagicMock()
        state_2.project_id = "PVT_other"

        mock_get_states.return_value = {1: state_1, 2: state_2}

        ctx = _make_ctx()
        result = await get_pipeline_states(ctx, "PVT_abc")

        assert result["project_id"] == "PVT_abc"
        assert "1" in result["pipeline_states"]
        assert "2" not in result["pipeline_states"]

    @patch(
        "src.services.mcp_server.tools.pipelines.verify_mcp_project_access",
        new_callable=AsyncMock,
    )
    @patch("src.services.pipeline_state_store.get_all_pipeline_states")
    async def test_empty_states(self, mock_get_states, mock_access):
        mock_get_states.return_value = {}

        ctx = _make_ctx()
        result = await get_pipeline_states(ctx, "PVT_abc")
        assert result["pipeline_states"] == {}


# ── retry_pipeline ─────────────────────────────────────────────────


class TestRetryPipeline:
    @patch(
        "src.services.mcp_server.tools.pipelines.verify_mcp_project_access",
        new_callable=AsyncMock,
    )
    @patch("src.services.pipeline_state_store.get_pipeline_state")
    async def test_retry_existing_pipeline(self, mock_get_state, mock_access):
        mock_get_state.return_value = MagicMock()

        ctx = _make_ctx()
        result = await retry_pipeline(ctx, "PVT_abc", 42)

        assert result["status"] == "retry_requested"
        assert result["issue_number"] == 42

    @patch(
        "src.services.mcp_server.tools.pipelines.verify_mcp_project_access",
        new_callable=AsyncMock,
    )
    @patch("src.services.pipeline_state_store.get_pipeline_state")
    async def test_retry_nonexistent_pipeline(self, mock_get_state, mock_access):
        mock_get_state.return_value = None

        ctx = _make_ctx()
        result = await retry_pipeline(ctx, "PVT_abc", 999)
        assert "error" in result
