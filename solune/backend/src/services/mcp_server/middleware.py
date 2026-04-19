"""ASGI middleware that authenticates MCP requests via GitHub PAT.

Wraps the MCP Starlette app so every incoming HTTP request has its
``Authorization: Bearer <token>`` header verified before reaching the
MCP SDK's tool/resource handlers.  The resolved ``McpContext`` is stored
in a ``contextvars.ContextVar`` so that ``get_mcp_context()`` in the tool
helpers can retrieve it without depending on the MCP lifespan dict.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from starlette.types import ASGIApp, Receive, Scope, Send

from src.logging_utils import get_logger
from src.services.mcp_server.context import set_current_mcp_context

if TYPE_CHECKING:
    from src.services.mcp_server.auth import GitHubTokenVerifier

logger = get_logger(__name__)


class McpAuthMiddleware:
    """ASGI middleware that verifies GitHub PAT on every MCP request."""

    def __init__(self, app: ASGIApp, verifier: GitHubTokenVerifier) -> None:
        self.app = app
        self.verifier = verifier

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract Authorization header
        headers = dict(scope.get("headers", []))
        auth_value = headers.get(b"authorization", b"").decode()

        mcp_ctx = None
        if auth_value.lower().startswith("bearer "):
            token = auth_value[7:].strip()
            if token:
                try:
                    access_token = await self.verifier.verify_token(token)
                except Exception as exc:  # noqa: BLE001 — reason: 3rd-party callback; unbounded input
                    logger.warning("MCP token verification failed: %s", exc, exc_info=True)
                    await self._send_unauthorized(send)
                    return

                if access_token:
                    mcp_ctx = self.verifier.get_context_for_token(token)

        if mcp_ctx is None:
            await self._send_unauthorized(send)
            return

        set_current_mcp_context(mcp_ctx)
        try:
            await self.app(scope, receive, send)
        finally:
            set_current_mcp_context(None)

    async def _send_unauthorized(self, send: Send) -> None:
        body = json.dumps({"error": "Unauthorized"}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"www-authenticate", b"Bearer"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
