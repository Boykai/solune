"""MCP tools for activity feed and item status updates.

Tier 1 tools (FR-021, FR-022):
- get_activity, update_item_status
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from src.services.mcp_server.tools import get_mcp_context, verify_mcp_project_access


async def get_activity(ctx: Context, project_id: str, limit: int = 20) -> dict[str, Any]:
    """Get a paginated activity feed for a project.

    Args:
        project_id: The GitHub Project V2 node ID.
        limit: Maximum number of events to return (default 20, max 100).
    """
    from src.services.activity_service import query_events
    from src.services.database import get_db

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    db = get_db()
    limit = min(max(limit, 1), 100)
    result = await query_events(db, project_id=project_id, limit=limit)
    return {"project_id": project_id, **result}


async def update_item_status(
    ctx: Context, project_id: str, item_id: str, status: str
) -> dict[str, Any]:
    """Update the status of an item on the project board.

    Moves an item to a different column by updating its status field.

    Args:
        project_id: The GitHub Project V2 node ID.
        item_id: The project item node ID (``PVTI_...``).
        status: The target status name (e.g. ``"In Progress"``, ``"Done"``).
    """
    from src.services.github_projects import GitHubProjectsService

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    svc = GitHubProjectsService()
    success = await svc.update_item_status_by_name(
        mcp_ctx.github_token, project_id, item_id, status
    )
    return {
        "success": success,
        "project_id": project_id,
        "item_id": item_id,
        "new_status": status,
    }
