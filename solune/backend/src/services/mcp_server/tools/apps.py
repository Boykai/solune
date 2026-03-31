"""MCP tools for application management.

Tier 2 tools (FR-024):
- list_apps, get_app_status, create_app
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from src.services.mcp_server.tools import get_mcp_context


async def list_apps(ctx: Context) -> dict[str, Any]:
    """List all managed applications with their current status."""
    from src.services.app_service import list_apps as _list_apps
    from src.services.database import get_db

    get_mcp_context(ctx)  # Require authentication

    db = get_db()
    apps = await _list_apps(db)
    return {"apps": [a.model_dump() if hasattr(a, "model_dump") else a for a in apps]}


async def get_app_status(ctx: Context, app_name: str) -> dict[str, Any]:
    """Get the health status of a managed application.

    Args:
        app_name: Application name.
    """
    from src.services.app_service import get_app_status as _get_app_status
    from src.services.database import get_db

    get_mcp_context(ctx)  # Require authentication

    db = get_db()
    status = await _get_app_status(db, app_name)
    return (
        status.model_dump()
        if hasattr(status, "model_dump")
        else {"name": app_name, "status": str(status)}
    )


async def create_app(
    ctx: Context,
    name: str,
    owner: str,
    template: str | None = None,
    pipeline_id: str | None = None,
) -> dict[str, Any]:
    """Scaffold a new managed application with optional pipeline launch.

    Args:
        name: Application name.
        owner: GitHub owner (user or org) for the new repository.
        template: Optional template repository to clone from.
        pipeline_id: Optional pipeline to launch after app creation.
    """
    from src.models.app import AppCreate, RepoType
    from src.services.app_service import create_app as _create_app
    from src.services.database import get_db
    from src.services.github_projects import GitHubProjectsService

    mcp_ctx = get_mcp_context(ctx)

    db = get_db()
    svc = GitHubProjectsService()
    payload = AppCreate(
        name=name,
        display_name=name,
        pipeline_id=pipeline_id,
        repo_type=RepoType.NEW_REPO,
        repo_owner=owner,
    )
    result = await _create_app(db, payload, access_token=mcp_ctx.github_token, github_service=svc)
    return (
        result.model_dump()
        if hasattr(result, "model_dump")
        else {"name": name, "status": "created"}
    )
