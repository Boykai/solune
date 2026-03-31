"""Per-request MCP authentication context.

``McpContext`` is a dataclass that holds the resolved GitHub identity from
token verification.  It is created by ``GitHubTokenVerifier`` and made
available to all MCP tool handlers through the ``FastMCP`` lifespan context.
"""

from __future__ import annotations

from dataclasses import dataclass


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
            raise ValueError("github_token must be non-empty")
        if self.github_user_id <= 0:
            raise ValueError("github_user_id must be a positive integer")
        if not self.github_login:
            raise ValueError("github_login must be non-empty")
