"""MCP tool modules for Solune.

Provides shared helpers used across all tool modules.
"""

from __future__ import annotations

from typing import Any

from src.exceptions import AuthorizationError
from src.logging_utils import get_logger
from src.services.mcp_server.context import McpContext

logger = get_logger(__name__)


def get_mcp_context(ctx: Any) -> McpContext:
    """Extract the ``McpContext`` from the MCP tool context.

    Checks the lifespan context first, then falls back to the
    ``contextvars.ContextVar`` set by the ASGI auth middleware.
    """
    lifespan_ctx = ctx.request_context.lifespan_context
    mcp_ctx: McpContext | None = lifespan_ctx.get("mcp_context")
    if mcp_ctx is None:
        from src.services.mcp_server.context import get_current_mcp_context

        mcp_ctx = get_current_mcp_context()
    if mcp_ctx is None:
        raise AuthorizationError("Authentication required")  # noqa: TRY003 — reason: domain exception with descriptive message
    return mcp_ctx


async def verify_mcp_project_access(mcp_ctx: McpContext, project_id: str) -> None:
    """Verify that the authenticated MCP user has access to *project_id*.

    Re-uses the same pattern as ``dependencies.verify_project_access``
    but operates with the MCP context instead of a FastAPI request.
    """
    from src.services.github_projects import GitHubProjectsService

    svc = GitHubProjectsService()
    try:
        projects = await svc.list_user_projects(mcp_ctx.github_token, mcp_ctx.github_login)
        if any(p.project_id == project_id for p in projects):
            return
    except Exception as exc:
        logger.warning(
            "Failed to verify MCP project access for user=%s project=%s: %s",
            mcp_ctx.github_login,
            project_id,
            exc,
            exc_info=True,
        )
        raise AuthorizationError("Unable to verify project access") from exc  # noqa: TRY003 — reason: domain exception with descriptive message

    raise AuthorizationError("You do not have access to this project")  # noqa: TRY003 — reason: domain exception with descriptive message
