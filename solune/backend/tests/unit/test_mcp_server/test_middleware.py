from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.mcp_server.context import McpContext, get_current_mcp_context
from src.services.mcp_server.middleware import McpAuthMiddleware


def _http_scope(auth_header: bytes | None = None) -> dict:
    headers = []
    if auth_header is not None:
        headers.append((b"authorization", auth_header))
    return {"type": "http", "headers": headers}


@pytest.mark.asyncio
async def test_allows_valid_http_requests_and_sets_context() -> None:
    captured: dict[str, object] = {"called": False}
    mcp_ctx = McpContext(github_token="ghp_valid", github_user_id=1, github_login="octocat")

    async def app(scope, receive, send) -> None:
        captured["called"] = True
        captured["context"] = get_current_mcp_context()
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    verifier = MagicMock()
    verifier.verify_token = AsyncMock(return_value=SimpleNamespace(token="ghp_valid"))
    verifier.get_context_for_token.return_value = mcp_ctx

    messages: list[dict] = []

    async def send(message) -> None:
        messages.append(message)

    middleware = McpAuthMiddleware(app, verifier)
    await middleware(_http_scope(b"Bearer ghp_valid"), AsyncMock(), send)

    assert captured["called"] is True
    assert captured["context"] == mcp_ctx
    assert get_current_mcp_context() is None
    assert messages[0]["status"] == 204


@pytest.mark.parametrize(
    "header",
    [
        None,
        b"Basic abc123",
        b"Bearer ",
    ],
)
@pytest.mark.asyncio
async def test_rejects_missing_or_malformed_http_auth(header: bytes | None) -> None:
    app = AsyncMock()
    verifier = MagicMock()
    verifier.verify_token = AsyncMock(return_value=None)
    verifier.get_context_for_token.return_value = None

    messages: list[dict] = []

    async def send(message) -> None:
        messages.append(message)

    middleware = McpAuthMiddleware(app, verifier)
    await middleware(_http_scope(header), AsyncMock(), send)

    assert app.await_count == 0
    assert messages[0]["status"] == 401
    assert messages[1]["body"] == b'{"error": "Unauthorized"}'


@pytest.mark.asyncio
async def test_rejects_invalid_token_when_verifier_returns_none() -> None:
    app = AsyncMock()
    verifier = MagicMock()
    verifier.verify_token = AsyncMock(return_value=None)
    verifier.get_context_for_token.return_value = None

    messages: list[dict] = []

    async def send(message) -> None:
        messages.append(message)

    middleware = McpAuthMiddleware(app, verifier)
    await middleware(_http_scope(b"Bearer ghp_invalid"), AsyncMock(), send)

    verifier.verify_token.assert_awaited_once_with("ghp_invalid")
    assert app.await_count == 0
    assert messages[0]["status"] == 401


@pytest.mark.asyncio
async def test_rejects_http_request_when_verification_raises() -> None:
    app = AsyncMock()
    verifier = MagicMock()
    verifier.verify_token = AsyncMock(side_effect=RuntimeError("boom"))
    verifier.get_context_for_token.return_value = None

    messages: list[dict] = []

    async def send(message) -> None:
        messages.append(message)

    middleware = McpAuthMiddleware(app, verifier)
    await middleware(_http_scope(b"Bearer ghp_boom"), AsyncMock(), send)

    assert app.await_count == 0
    assert messages[0]["status"] == 401


@pytest.mark.asyncio
async def test_non_http_scopes_pass_through_without_auth() -> None:
    app = AsyncMock()
    verifier = MagicMock()
    verifier.verify_token = AsyncMock()

    middleware = McpAuthMiddleware(app, verifier)
    await middleware({"type": "websocket", "headers": []}, AsyncMock(), AsyncMock())

    assert app.await_count == 1
    verifier.verify_token.assert_not_awaited()


@pytest.mark.asyncio
async def test_context_is_cleared_even_when_app_raises() -> None:
    """Ensure set_current_mcp_context(None) runs in the finally block."""
    mcp_ctx = McpContext(github_token="ghp_valid", github_user_id=1, github_login="octocat")

    async def failing_app(scope, receive, send) -> None:
        raise RuntimeError("app crash")

    verifier = MagicMock()
    verifier.verify_token = AsyncMock(return_value=SimpleNamespace(token="ghp_valid"))
    verifier.get_context_for_token.return_value = mcp_ctx

    middleware = McpAuthMiddleware(failing_app, verifier)

    with pytest.raises(RuntimeError, match="app crash"):
        await middleware(_http_scope(b"Bearer ghp_valid"), AsyncMock(), AsyncMock())

    assert get_current_mcp_context() is None


@pytest.mark.asyncio
async def test_unauthorized_response_includes_www_authenticate_header() -> None:
    """Verify the 401 response includes WWW-Authenticate: Bearer."""
    app = AsyncMock()
    verifier = MagicMock()
    verifier.verify_token = AsyncMock(return_value=None)
    verifier.get_context_for_token.return_value = None

    messages: list[dict] = []

    async def send(message) -> None:
        messages.append(message)

    middleware = McpAuthMiddleware(app, verifier)
    await middleware(_http_scope(None), AsyncMock(), send)

    start_msg = messages[0]
    assert start_msg["status"] == 401
    header_names = [h[0] for h in start_msg["headers"]]
    assert b"www-authenticate" in header_names
