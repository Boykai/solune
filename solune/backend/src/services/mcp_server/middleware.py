"""ASGI middleware that authenticates MCP requests via GitHub PAT.

Wraps the MCP Starlette app so every incoming HTTP request has its
``Authorization: Bearer <token>`` header verified before reaching the
MCP SDK's tool/resource handlers.  The resolved ``McpContext`` is stored
in a ``contextvars.ContextVar`` so that ``get_mcp_context()`` in the tool
helpers can retrieve it without depending on the MCP lifespan dict.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.logging_utils import get_logger
from src.services.mcp_server.context import set_current_mcp_context

if TYPE_CHECKING:
    from src.services.mcp_server.auth import GitHubTokenVerifier

logger = get_logger(__name__)


class McpAuthMiddleware:
    """ASGI middleware that verifies GitHub PAT on every MCP request."""

    def __init__(self, app: Any, verifier: GitHubTokenVerifier) -> None:
        self.app = app
        self.verifier = verifier

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Extract Authorization header
        headers = dict(scope.get("headers", []))
        auth_value = headers.get(b"authorization", b"").decode()

        mcp_ctx = None
        if auth_value.lower().startswith("bearer "):
            token = auth_value[7:]
            access_token = await self.verifier.verify_token(token)
            if access_token:
                mcp_ctx = self.verifier.get_context_for_token(token)

        set_current_mcp_context(mcp_ctx)
        try:
            await self.app(scope, receive, send)
        finally:
            set_current_mcp_context(None)
