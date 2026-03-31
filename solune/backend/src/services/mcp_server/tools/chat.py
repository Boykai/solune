"""MCP tools for chat, metadata, and cleanup.

Tier 2 tools (FR-026 - FR-028):
- send_chat_message, get_metadata, cleanup_preflight
"""

from __future__ import annotations

import uuid
from typing import Any

from mcp.server.fastmcp import Context

from src.services.mcp_server.tools import get_mcp_context, verify_mcp_project_access


async def send_chat_message(ctx: Context, project_id: str, message: str) -> dict[str, Any]:
    """Send a natural language message to Solune's AI agent.

    The agent can analyze issues, suggest solutions, and perform actions
    on the project board using its internal tool set.

    Args:
        project_id: The GitHub Project V2 node ID.
        message: The natural language message to send.
    """
    from src.services.chat_agent import ChatAgentService
    from src.services.database import get_db

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    agent = ChatAgentService()
    db = get_db()
    result = await agent.run(
        message=message,
        session_id=uuid.uuid4(),
        github_token=mcp_ctx.github_token,
        project_id=project_id,
        db=db,
    )
    return {
        "response": result.content if hasattr(result, "content") else str(result),
        "project_id": project_id,
    }


async def get_metadata(ctx: Context, owner: str, repo: str) -> dict[str, Any]:
    """Get repository context: labels, branches, milestones, collaborators.

    Args:
        owner: GitHub repository owner (user or org).
        repo: GitHub repository name.
    """
    from src.services.metadata_service import MetadataService

    mcp_ctx = get_mcp_context(ctx)

    metadata_svc = MetadataService()
    result = await metadata_svc.get_or_fetch(mcp_ctx.github_token, owner, repo)

    return (
        result.model_dump()
        if hasattr(result, "model_dump")
        else {
            "owner": owner,
            "repo": repo,
            "metadata": str(result),
        }
    )


async def cleanup_preflight(ctx: Context, project_id: str) -> dict[str, Any]:
    """Preview stale branches and pull requests that can be cleaned up.

    Returns a dry-run summary without actually deleting anything.

    Args:
        project_id: The GitHub Project V2 node ID.
    """
    from src.services.cleanup_service import preflight as _preflight
    from src.services.github_projects import GitHubProjectsService
    from src.utils import resolve_repository

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    owner, repo = await resolve_repository(mcp_ctx.github_token, project_id)
    svc = GitHubProjectsService()

    from src.models.cleanup import CleanupPreflightRequest

    request = CleanupPreflightRequest(owner=owner, repo=repo, project_id=project_id)
    result = await _preflight(
        svc,
        mcp_ctx.github_token,
        mcp_ctx.github_login,
        request,
    )
    return (
        result.model_dump()
        if hasattr(result, "model_dump")
        else {"project_id": project_id, "preview": str(result)}
    )
