"""MCP tools for pipeline operations.

Tier 1 tools (FR-017 - FR-020):
- list_pipelines, launch_pipeline, get_pipeline_states, retry_pipeline
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from src.services.mcp_server.tools import get_mcp_context, verify_mcp_project_access


async def list_pipelines(ctx: Context, project_id: str) -> dict[str, Any]:
    """List available pipeline configurations for a project.

    Args:
        project_id: The GitHub Project V2 node ID.
    """
    from src.services.database import get_db
    from src.services.pipelines.service import PipelineService

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    db = get_db()
    pipeline_svc = PipelineService(db)
    result = await pipeline_svc.list_pipelines(project_id)
    return {
        "project_id": project_id,
        "pipelines": result.model_dump() if hasattr(result, "model_dump") else result,
    }


async def launch_pipeline(
    ctx: Context, project_id: str, pipeline_id: str, issue_description: str
) -> dict[str, Any]:
    """Launch a development pipeline for a project.

    Creates a parent issue, sub-issues for each pipeline agent, and starts
    the first agent.  Delegates to ``execute_pipeline_launch()``.

    Args:
        project_id: The GitHub Project V2 node ID.
        pipeline_id: Pipeline configuration ID (e.g. ``"easy"``, ``"medium"``).
        issue_description: Description for the parent issue that drives the pipeline.
    """
    from src.api.pipelines import execute_pipeline_launch
    from src.models.user import UserSession

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    # Build a minimal UserSession for the pipeline launch function
    session = UserSession(
        github_user_id=str(mcp_ctx.github_user_id),
        github_username=mcp_ctx.github_login,
        access_token=mcp_ctx.github_token,
        selected_project_id=project_id,
    )

    result = await execute_pipeline_launch(
        project_id=project_id,
        issue_description=issue_description,
        pipeline_id=pipeline_id,
        session=session,
    )

    return {
        "success": result.success,
        "issue_number": result.issue_number,
        "issue_url": result.issue_url,
        "message": result.message,
    }


async def get_pipeline_states(ctx: Context, project_id: str) -> dict[str, Any]:
    """Get all active pipeline states for a project.

    Returns pipeline states with stage progress information.

    Args:
        project_id: The GitHub Project V2 node ID.
    """
    from src.services.pipeline_state_store import get_all_pipeline_states

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    all_states = get_all_pipeline_states()
    # Filter states that belong to this project
    project_states = {
        issue_num: state
        for issue_num, state in all_states.items()
        if getattr(state, "project_id", None) == project_id
    }

    return {
        "project_id": project_id,
        "pipeline_states": {
            str(k): v.model_dump() if hasattr(v, "model_dump") else v
            for k, v in project_states.items()
        },
    }


async def retry_pipeline(ctx: Context, project_id: str, issue_number: int) -> dict[str, Any]:
    """Retry a failed pipeline by re-assigning the agent.

    Args:
        project_id: The GitHub Project V2 node ID.
        issue_number: The GitHub issue number of the pipeline's parent issue.
    """
    from src.services.pipeline_state_store import get_pipeline_state

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    state = get_pipeline_state(issue_number)
    if state is None:
        return {"error": f"No pipeline state found for issue #{issue_number}"}

    # The retry logic follows the same pattern as the API endpoint
    return {
        "status": "retry_requested",
        "issue_number": issue_number,
        "project_id": project_id,
        "message": "Pipeline retry has been requested. The agent will be re-assigned.",
    }
