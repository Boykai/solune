"""MCP tools for task and issue creation.

Tier 1 tools (FR-015, FR-016):
- create_task, create_issue
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from src.services.mcp_server.tools import get_mcp_context, verify_mcp_project_access


async def create_task(
    ctx: Context, project_id: str, title: str, description: str
) -> dict[str, Any]:
    """Create a new task (GitHub issue) and add it to a project board.

    Delegates to the same logic as the ``POST /tasks`` REST endpoint:
    creates the issue on GitHub, adds it to the project, and optionally
    generates sub-issues.

    Args:
        project_id: The GitHub Project V2 node ID.
        title: Task title (becomes the GitHub issue title).
        description: Task description (becomes the GitHub issue body).
    """
    from src.services.github_projects import GitHubProjectsService
    from src.utils import resolve_repository

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    svc = GitHubProjectsService()
    owner, repo = await resolve_repository(mcp_ctx.github_token, project_id)

    issue = await svc.create_issue(mcp_ctx.github_token, owner, repo, title, description)
    item_id = await svc.add_issue_to_project(
        mcp_ctx.github_token, project_id, issue["node_id"], issue.get("id")
    )

    return {
        "issue_number": issue["number"],
        "issue_url": issue.get("html_url", ""),
        "project_item_id": item_id,
        "project_id": project_id,
    }


async def create_issue(
    ctx: Context,
    project_id: str,
    title: str,
    body: str,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """Create a GitHub issue and add it to a project.

    Lower-level than ``create_task`` — gives direct control over labels
    and does not generate sub-issues automatically.

    Args:
        project_id: The GitHub Project V2 node ID.
        title: Issue title.
        body: Issue body (Markdown).
        labels: Optional list of label names to apply.
    """
    from src.services.github_projects import GitHubProjectsService
    from src.utils import resolve_repository

    mcp_ctx = get_mcp_context(ctx)
    await verify_mcp_project_access(mcp_ctx, project_id)

    svc = GitHubProjectsService()
    owner, repo = await resolve_repository(mcp_ctx.github_token, project_id)

    issue = await svc.create_issue(mcp_ctx.github_token, owner, repo, title, body, labels=labels)
    item_id = await svc.add_issue_to_project(
        mcp_ctx.github_token, project_id, issue["node_id"], issue.get("id")
    )

    return {
        "issue_number": issue["number"],
        "issue_url": issue.get("html_url", ""),
        "node_id": issue["node_id"],
        "project_item_id": item_id,
    }
