"""MCP tools for project and board operations.

Tier 1 tools (FR-011 - FR-014):
- list_projects, get_project, get_board, get_project_tasks
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from src.services.mcp_server.tools import get_mcp_context, verify_mcp_project_access


async def list_projects(ctx: Context) -> dict[str, Any]:
    """List all GitHub Projects accessible to the authenticated user.

    Returns a list of projects with their IDs, names, and URLs.
    No project_id is required — this tool discovers available projects.
    """
    from src.services.github_projects import GitHubProjectsService

    mcp_ctx = get_mcp_context(ctx)
    svc = GitHubProjectsService()
    projects = await svc.list_user_projects(mcp_ctx.github_token, mcp_ctx.github_login)
    return {
        "projects": [
            {
                "project_id": p.project_id,
                "name": p.name,
                "url": p.url,
            }
            for p in projects
        ]
    }


async def get_project(ctx: Context, project_id: str) -> dict[str, Any]:
    """Get details of a specific GitHub Project including its status columns.

    Args:
        project_id: The GitHub Project V2 node ID (e.g. ``PVT_...``).
    """
    from src.services.github_projects import GitHubProjectsService

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    svc = GitHubProjectsService()
    fields = await svc.get_project_fields(mcp_ctx.github_token, project_id)
    repo_info = await svc.get_project_repository(mcp_ctx.github_token, project_id)
    return {
        "project_id": project_id,
        "fields": fields,
        "repository": {"owner": repo_info[0], "repo": repo_info[1]} if repo_info else None,
    }


async def get_board(ctx: Context, project_id: str) -> dict[str, Any]:
    """Get the full kanban board state for a GitHub Project.

    Returns all columns and items with their current status, type, and labels.

    Args:
        project_id: The GitHub Project V2 node ID.
    """
    from src.services.github_projects import GitHubProjectsService

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    svc = GitHubProjectsService()
    board_data = await svc.get_board_data(mcp_ctx.github_token, project_id)
    return {"project_id": project_id, "board": board_data}


async def get_project_tasks(ctx: Context, project_id: str) -> dict[str, Any]:
    """Get all items and issues in a GitHub Project.

    Returns every item on the project board with status, type, and labels.

    Args:
        project_id: The GitHub Project V2 node ID.
    """
    from src.services.github_projects import GitHubProjectsService

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    svc = GitHubProjectsService()
    items = await svc.get_project_items(mcp_ctx.github_token, project_id)
    return {
        "project_id": project_id,
        "items": [item.model_dump() if hasattr(item, "model_dump") else item for item in items],
    }
