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
    data = result.model_dump() if hasattr(result, "model_dump") else result
    response: dict[str, Any] = {"project_id": project_id}
    if isinstance(data, dict):
        response.update(data)
    else:
        response["pipelines"] = data
    return response


async def launch_pipeline(
    ctx: Context, project_id: str, pipeline_id: str, issue_description: str
) -> dict[str, Any]:
    """Launch a development pipeline for a project.

    Creates a parent issue, sub-issues for each pipeline agent, and starts
    the first agent.  Delegates to ``execute_pipeline_launch()``.

    Args:
        project_id: The GitHub Project V2 node ID.
        pipeline_id: Pipeline configuration ID (e.g. ``"github"``, ``"default"``).
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

    Clears the error state and dedup guards, then re-drives agent
    assignment for the current pipeline stage.

    Args:
        project_id: The GitHub Project V2 node ID.
        issue_number: The GitHub issue number of the pipeline's parent issue.
    """
    from src.services.pipeline_state_store import get_pipeline_state, set_pipeline_state

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    state = get_pipeline_state(issue_number)
    if state is None:
        return {"error": f"No pipeline state found for issue #{issue_number}"}

    if getattr(state, "project_id", None) != project_id:
        return {"error": f"No pipeline state found for issue #{issue_number}"}

    if getattr(state, "is_complete", False):
        return {"message": "Pipeline already complete", "issue_number": issue_number}

    current_agent = getattr(state, "current_agent", None)
    if not current_agent:
        return {"message": "No pending agent to retry", "issue_number": issue_number}

    # Clear the error state so retry proceeds
    state.error = None
    await set_pipeline_state(issue_number, state)

    # Clear any pending assignment dedup guards for this agent
    try:
        from src.services.copilot_polling import _pending_agent_assignments

        pending_key = f"{issue_number}:{current_agent}"
        _pending_agent_assignments.pop(pending_key, None)
    except ImportError:
        pass

    # Retry the assignment
    from src.services.workflow_orchestrator.config import get_workflow_config
    from src.services.workflow_orchestrator.models import WorkflowContext
    from src.services.workflow_orchestrator.orchestrator import get_workflow_orchestrator
    from src.utils import resolve_repository

    config = await get_workflow_config(project_id)
    if not config:
        return {"error": "No workflow configuration found for this project"}

    owner, repo = await resolve_repository(mcp_ctx.github_token, project_id)

    wf_ctx = WorkflowContext(
        session_id="mcp",
        project_id=project_id,
        access_token=mcp_ctx.github_token,
        repository_owner=owner,
        repository_name=repo,
        config=config,
        user_chat_model="",
        user_agent_model="",
    )

    # Fetch issue context for the orchestrator
    from src.services.github_projects import GitHubProjectsService

    svc = GitHubProjectsService()
    try:
        issue_data = await svc.get_issue_with_comments(
            access_token=mcp_ctx.github_token,
            owner=owner,
            repo=repo,
            issue_number=issue_number,
        )
        wf_ctx.issue_id = issue_data.get("node_id", "")
        wf_ctx.issue_number = issue_number
        wf_ctx.issue_url = issue_data.get("html_url", "")
    except Exception:
        return {
            "success": False,
            "issue_number": issue_number,
            "message": f"Could not fetch issue #{issue_number} for retry",
        }

    orchestrator = get_workflow_orchestrator()
    agent_index = getattr(state, "current_agent_index", 0) or 0
    success = await orchestrator.assign_agent_for_status(
        wf_ctx, state.status, agent_index=agent_index
    )

    return {
        "success": success,
        "issue_number": issue_number,
        "project_id": project_id,
        "agent": current_agent,
        "message": (
            f"Successfully retried agent '{current_agent}' on issue #{issue_number}"
            if success
            else f"Retry failed for agent '{current_agent}' on issue #{issue_number}"
        ),
    }
