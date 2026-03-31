"""MCP tools for agent management.

Tier 2 tools (FR-023):
- list_agents, create_agent
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from src.services.mcp_server.tools import get_mcp_context, verify_mcp_project_access


async def list_agents(ctx: Context, project_id: str) -> dict[str, Any]:
    """List custom GitHub Copilot agents configured for a project.

    Args:
        project_id: The GitHub Project V2 node ID.
    """
    from src.services.agents.service import AgentsService
    from src.services.database import get_db
    from src.utils import resolve_repository

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    owner, repo = await resolve_repository(mcp_ctx.github_token, project_id)
    db = get_db()
    agents_svc = AgentsService(db)
    agents = await agents_svc.list_agents(
        project_id=project_id,
        owner=owner,
        repo=repo,
        access_token=mcp_ctx.github_token,
    )
    return {
        "project_id": project_id,
        "agents": [a.model_dump() if hasattr(a, "model_dump") else a for a in agents],
    }


async def create_agent(
    ctx: Context,
    project_id: str,
    name: str,
    instructions: str,
    model: str | None = None,
) -> dict[str, Any]:
    """Create a new custom GitHub Copilot agent.

    Creates a branch, commits the agent definition, and opens a pull request.

    Args:
        project_id: The GitHub Project V2 node ID.
        name: Agent name (used as filename).
        instructions: Agent instructions/system prompt.
        model: Optional model override (e.g. ``"gpt-4o"``).
    """
    from src.models.agents import AgentCreate
    from src.services.agents.service import AgentsService
    from src.services.database import get_db
    from src.utils import resolve_repository

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    owner, repo = await resolve_repository(mcp_ctx.github_token, project_id)
    db = get_db()
    agents_svc = AgentsService(db)

    body = AgentCreate(
        name=name,
        system_prompt=instructions,
        default_model_id=model or "",
        default_model_name=model or "",
    )
    result = await agents_svc.create_agent(
        project_id=project_id,
        owner=owner,
        repo=repo,
        body=body,
        access_token=mcp_ctx.github_token,
        github_user_id=str(mcp_ctx.github_user_id),
    )
    return {
        "agent_id": getattr(result, "agent_id", None),
        "pr_url": getattr(result, "pr_url", None),
        "result": result.model_dump() if hasattr(result, "model_dump") else str(result),
    }
