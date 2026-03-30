"""
Authenticated E2E test fixtures.

Provides ``auth_client`` and ``unauthenticated_client`` fixtures that exercise
the full FastAPI request pipeline (middleware → routing → auth → handler) with
a real in-memory SQLite database and session store, mocking only external
network-dependent services (GitHub API, AI agents, WebSocket manager).
"""

from __future__ import annotations

import contextlib
from unittest.mock import AsyncMock, patch

import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient

from src.constants import SESSION_COOKIE_NAME
from src.main import create_app
from tests.conftest import (
    TEST_ACCESS_TOKEN,
    TEST_GITHUB_USER_ID,
    TEST_GITHUB_USERNAME,
    _apply_migrations,
    make_mock_github_service,
    make_mock_websocket_manager,
)

# ── Test constants ────────────────────────────────────────────────────────────

TEST_AVATAR_URL = f"https://avatars.githubusercontent.com/u/{TEST_GITHUB_USER_ID}"

# Mock GitHub user data returned by the patched ``get_github_user`` call
# inside ``create_session_from_token``.  Matches the shape returned by
# the real GitHub ``GET /user`` endpoint.
_MOCK_GITHUB_USER = {
    "id": int(TEST_GITHUB_USER_ID),
    "login": TEST_GITHUB_USERNAME,
    "avatar_url": TEST_AVATAR_URL,
}


# ── Database ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def test_db():
    """Fresh in-memory SQLite database with all migrations applied."""
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await _apply_migrations(db)
    yield db
    await db.close()


# ── Service mocks ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_github_projects_service():
    """Pre-configured GitHubProjectsService mock."""
    return make_mock_github_service()


@pytest.fixture
def mock_chat_agent_service():
    """AsyncMock with ChatAgentService spec."""
    from src.services.chat_agent import ChatAgentService

    return AsyncMock(name="ChatAgentService", spec=ChatAgentService)


@pytest.fixture
def mock_ai_agent_service():
    """AsyncMock with AIAgentService spec."""
    from src.services.ai_agent import AIAgentService

    return AsyncMock(name="AIAgentService", spec=AIAgentService)


@pytest.fixture
def mock_connection_manager():
    """Pre-configured ConnectionManager mock."""
    return make_mock_websocket_manager()


# ── Application ───────────────────────────────────────────────────────────────


@pytest.fixture
async def e2e_app(
    test_db: aiosqlite.Connection,
    mock_github_projects_service: AsyncMock,
    mock_chat_agent_service: AsyncMock,
    mock_ai_agent_service: AsyncMock,
    mock_connection_manager: AsyncMock,
):
    """Fully-wired FastAPI application for authenticated E2E testing.

    External services are mocked; the session store and database are real
    (in-memory SQLite).  Only ``get_github_user`` is patched on
    ``github_auth_service`` so that ``create_session_from_token`` runs its
    real code (saving the session to the test DB) without calling the
    GitHub API.
    """
    from src.dependencies import get_connection_manager, get_database, get_github_service

    app = create_app()

    # FastAPI dependency overrides — these apply to all Depends() calls
    app.dependency_overrides[get_database] = lambda: test_db
    app.dependency_overrides[get_github_service] = lambda: mock_github_projects_service
    app.dependency_overrides[get_connection_manager] = lambda: mock_connection_manager

    patches = [
        # ── Database ──
        # Patch get_db() everywhere it is imported so that all code paths
        # (Depends-injected *and* direct calls) use the test DB.
        patch("src.services.database.get_db", return_value=test_db),
        patch("src.services.database._connection", test_db),
        # github_auth_service internally calls get_db() for session CRUD
        patch("src.services.github_auth.get_db", return_value=test_db),
        # API modules that call get_db() directly
        patch("src.api.settings.get_db", return_value=test_db),
        patch("src.api.mcp.get_db", return_value=test_db),
        patch("src.api.tools.get_db", return_value=test_db),
        patch("src.api.onboarding.get_db", return_value=test_db),
        # ── GitHub Projects service singletons ──
        patch("src.api.board.github_projects_service", mock_github_projects_service),
        patch("src.api.projects.github_projects_service", mock_github_projects_service),
        patch("src.api.tasks.github_projects_service", mock_github_projects_service),
        patch("src.api.workflow.github_projects_service", mock_github_projects_service),
        patch("src.api.chores.github_projects_service", mock_github_projects_service),
        patch(
            "src.services.github_projects.github_projects_service",
            mock_github_projects_service,
        ),
        # ── Auth: mock only the GitHub API call inside create_session_from_token ──
        # The real method body still runs (creates UserSession, saves to DB,
        # sets cookie), only the network call is stubbed.
        patch(
            "src.services.github_auth.GitHubAuthService.get_github_user",
            new_callable=AsyncMock,
            return_value=_MOCK_GITHUB_USER,
        ),
        # ── AI / chat agent services ──
        patch("src.api.chat.get_ai_agent_service", return_value=mock_ai_agent_service),
        patch("src.api.chat.get_chat_agent_service", return_value=mock_chat_agent_service),
        # ── WebSocket connection_manager ──
        patch("src.api.projects.connection_manager", mock_connection_manager),
        patch("src.api.tasks.connection_manager", mock_connection_manager),
        patch("src.api.workflow.connection_manager", mock_connection_manager),
        # ── Copilot polling: prevent background task leaks ──
        # select_project triggers ensure_polling_started() which spawns
        # long-lived background tasks.  Stub it to a no-op for E2E tests.
        patch("src.api.projects._start_copilot_polling", new_callable=AsyncMock),
    ]

    with contextlib.ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        yield app

    app.dependency_overrides.clear()


# ── Clients ───────────────────────────────────────────────────────────────────


@pytest.fixture
async def auth_client(e2e_app):
    """Authenticated ``httpx.AsyncClient`` with a valid session cookie.

    Performs a real ``POST /api/v1/auth/dev-login`` against the E2E app so
    that the session cookie is issued by the real auth middleware.
    """
    transport = ASGITransport(app=e2e_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Perform dev-login to obtain a real session cookie
        response = await client.post(
            "/api/v1/auth/dev-login",
            json={"github_token": TEST_ACCESS_TOKEN},
        )
        assert response.status_code == 200, f"dev-login failed: {response.text}"
        assert SESSION_COOKIE_NAME in response.cookies or any(
            SESSION_COOKIE_NAME in str(h) for h in response.headers.raw
        ), "Session cookie not set after dev-login"
        yield client


@pytest.fixture
async def unauthenticated_client(e2e_app):
    """``httpx.AsyncClient`` without a session cookie."""
    transport = ASGITransport(app=e2e_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
