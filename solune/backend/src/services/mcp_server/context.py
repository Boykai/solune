"""Per-request MCP authentication context.

``McpContext`` is a dataclass that holds the resolved GitHub identity from
token verification.  It is created by ``GitHubTokenVerifier`` and made
available to all MCP tool handlers through the ``FastMCP`` lifespan context.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass

# ── Contextvar for per-request MCP context ──────────────────────────
# Used by the ASGI auth middleware to pass the resolved context into
# the MCP tool handler without relying solely on the lifespan dict.
_current_mcp_context: contextvars.ContextVar[McpContext | None] = contextvars.ContextVar(
    "_current_mcp_context", default=None
)


def set_current_mcp_context(ctx: McpContext | None) -> None:
    """Set the per-request ``McpContext`` contextvar."""
    _current_mcp_context.set(ctx)


def get_current_mcp_context() -> McpContext | None:
    """Return the per-request ``McpContext``, or ``None``."""
    return _current_mcp_context.get()


@dataclass(frozen=True, slots=True)
class McpContext:
    """Authentication context for a single MCP request.

    Attributes:
        github_token: Raw GitHub PAT provided by the MCP client.
        github_user_id: Numeric GitHub user ID resolved from ``GET /user``.
        github_login: GitHub username (login) resolved from ``GET /user``.
    """

    github_token: str
    github_user_id: int
    github_login: str

    def __post_init__(self) -> None:
        if not self.github_token:
            raise ValueError("github_token must be non-empty")  # noqa: TRY003 — reason: domain exception with descriptive message
        if self.github_user_id <= 0:
            raise ValueError("github_user_id must be a positive integer")  # noqa: TRY003 — reason: domain exception with descriptive message
        if not self.github_login:
            raise ValueError("github_login must be non-empty")  # noqa: TRY003 — reason: domain exception with descriptive message
