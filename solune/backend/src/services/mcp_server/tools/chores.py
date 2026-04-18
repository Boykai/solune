"""MCP tools for recurring chore management.

Tier 2 tools (FR-025):
- list_chores, trigger_chore
"""
# pyright: basic
# reason: MCP tool wrappers forward heterogeneous payloads; typed once tools/ catalog stabilises.

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from src.services.mcp_server.tools import get_mcp_context, verify_mcp_project_access


async def list_chores(ctx: Context, project_id: str) -> dict[str, Any]:
    """List recurring maintenance chores for a project.

    Args:
        project_id: The GitHub Project V2 node ID.
    """
    from src.services.chores.service import ChoresService
    from src.services.database import get_db

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    db = get_db()
    chore_svc = ChoresService(db)
    chores = await chore_svc.list_chores(project_id)
    return {
        "project_id": project_id,
        "chores": [c.model_dump() if hasattr(c, "model_dump") else c for c in chores],
    }


async def trigger_chore(ctx: Context, project_id: str, chore_id: str) -> dict[str, Any]:
    """Manually trigger a recurring chore.

    Args:
        project_id: The GitHub Project V2 node ID.
        chore_id: The chore identifier.
    """
    from src.services.chores.service import ChoresService
    from src.services.database import get_db
    from src.services.github_projects import GitHubProjectsService
    from src.utils import resolve_repository

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    db = get_db()
    chore_svc = ChoresService(db)
    chores = await chore_svc.list_chores(project_id)
    chore = next((c for c in chores if getattr(c, "id", None) == chore_id), None)
    if chore is None:
        return {"error": f"Chore '{chore_id}' not found in project {project_id}"}

    owner, repo = await resolve_repository(mcp_ctx.github_token, project_id)
    svc = GitHubProjectsService()
    result = await chore_svc.trigger_chore(
        chore,
        github_service=svc,
        access_token=mcp_ctx.github_token,
        owner=owner,
        repo=repo,
        project_id=project_id,
    )
    return {
        "chore_id": chore_id,
        "project_id": project_id,
        "result": result.model_dump() if hasattr(result, "model_dump") else str(result),
    }
