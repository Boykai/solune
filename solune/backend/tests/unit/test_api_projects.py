"""Tests for projects API routes (src/api/projects.py).

Covers:
- GET  /api/v1/projects                     → list_projects
- GET  /api/v1/projects/{id}                → get_project
- GET  /api/v1/projects/{id}/tasks           → get_project_tasks
- POST /api/v1/projects/{id}/select         → select_project
- _start_copilot_polling helper
- _is_github_rate_limit_error helper
- WebSocket subscribe (send_tasks / disconnect)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from githubkit.exception import PrimaryRateLimitExceeded, RequestFailed

from src.api.projects import _is_github_rate_limit_error, _start_copilot_polling
from src.models.project import GitHubProject, StatusColumn
from src.models.task import Task

# ── Helpers ─────────────────────────────────────────────────────────────────


def _project(**kw) -> GitHubProject:
    defaults = {
        "project_id": "PVT_abc",
        "owner_id": "O_123",
        "owner_login": "testuser",
        "name": "Test Project",
        "type": "user",
        "url": "https://github.com/users/testuser/projects/1",
        "status_columns": [
            StatusColumn(field_id="SF_1", name="Todo", option_id="opt1"),
            StatusColumn(field_id="SF_1", name="Done", option_id="opt2"),
        ],
    }
    defaults.update(kw)
    return GitHubProject(**defaults)


def _task(**kw) -> Task:
    defaults = {
        "project_id": "PVT_abc",
        "github_item_id": "PVTI_1",
        "title": "Sample task",
        "status": "Todo",
        "status_option_id": "opt1",
    }
    defaults.update(kw)
    return Task(**defaults)


# ── GET /projects ───────────────────────────────────────────────────────────


class TestListProjects:
    async def test_returns_projects(self, client, mock_github_service):
        p = _project()
        mock_github_service.list_user_projects.return_value = [p]
        resp = await client.get("/api/v1/projects", params={"refresh": True})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["projects"]) == 1
        assert data["projects"][0]["name"] == "Test Project"

    async def test_returns_empty_list(self, client, mock_github_service):
        mock_github_service.list_user_projects.return_value = []
        resp = await client.get("/api/v1/projects", params={"refresh": True})
        assert resp.status_code == 200
        assert resp.json()["projects"] == []

    async def test_rate_limit_uses_cached_headers_for_generic_errors(
        self, client, mock_github_service
    ):
        mock_github_service.list_user_projects.side_effect = RuntimeError("network")
        mock_github_service.get_last_rate_limit.return_value = {
            "limit": 5000,
            "remaining": 0,
            "reset_at": 1_700_000_000,
            "used": 5000,
        }

        resp = await client.get("/api/v1/projects", params={"refresh": True})

        assert resp.status_code == 429
        body = resp.json()
        assert body["error"] == "GitHub API rate limit exceeded"
        assert body["details"]["rate_limit"]["limit"] == 5000


# ── GET /projects/{id} ─────────────────────────────────────────────────────


class TestGetProject:
    async def test_get_existing_project(self, client, mock_github_service):
        p = _project()
        mock_github_service.list_user_projects.return_value = [p]
        resp = await client.get("/api/v1/projects/PVT_abc", params={"refresh": True})
        assert resp.status_code == 200
        assert resp.json()["project_id"] == "PVT_abc"

    async def test_project_not_found(self, client, mock_github_service):
        mock_github_service.list_user_projects.return_value = []
        with patch("src.api.projects.cache") as mock_cache:
            mock_cache.get.return_value = None
            resp = await client.get("/api/v1/projects/PVT_missing")
        assert resp.status_code == 404


# ── GET /projects/{id}/tasks ───────────────────────────────────────────────


class TestGetProjectTasks:
    async def test_returns_tasks(self, client, mock_github_service):
        t = _task()
        mock_github_service.get_project_items.return_value = [t]
        resp = await client.get("/api/v1/projects/PVT_abc/tasks", params={"refresh": True})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["title"] == "Sample task"

    async def test_returns_empty_tasks(self, client, mock_github_service):
        mock_github_service.get_project_items.return_value = []
        resp = await client.get("/api/v1/projects/PVT_abc/tasks", params={"refresh": True})
        assert resp.status_code == 200
        assert resp.json()["tasks"] == []


# ── POST /projects/{id}/select ─────────────────────────────────────────────


class TestSelectProject:
    async def test_select_project(
        self, client, mock_session, mock_github_service, mock_github_auth_service
    ):
        p = _project()
        mock_github_service.list_user_projects.return_value = [p]
        mock_github_auth_service.update_session.return_value = None

        # Patch out copilot polling startup
        with (
            patch("src.api.projects._start_copilot_polling", new_callable=AsyncMock),
            patch("src.api.projects.cache") as mock_cache,
            patch("src.api.projects.log_event", new_callable=AsyncMock) as mock_log_event,
        ):
            mock_cache.get.return_value = None
            resp = await client.post("/api/v1/projects/PVT_abc/select")
        assert resp.status_code == 200
        data = resp.json()
        assert data["selected_project_id"] == "PVT_abc"
        mock_log_event.assert_awaited_once()
        assert mock_log_event.await_args.kwargs["action"] == "selected"
        assert mock_log_event.await_args.kwargs["detail"] == {"project_name": "Test Project"}

    async def test_select_nonexistent_project(self, client, mock_github_service):
        mock_github_service.list_user_projects.return_value = []
        with patch("src.api.projects.cache") as mock_cache:
            mock_cache.get.return_value = None
            resp = await client.post("/api/v1/projects/PVT_missing/select")
        assert resp.status_code == 404


class TestCreateProject:
    async def test_create_project_logs_activity(self, client):
        with (
            patch(
                "src.api.projects.create_standalone_project",
                new_callable=AsyncMock,
                return_value={
                    "project_id": "PVT_NEW",
                    "project_number": 12,
                    "project_url": "https://github.com/users/testuser/projects/12",
                },
            ),
            patch("src.api.projects.log_event", new_callable=AsyncMock) as mock_log_event,
        ):
            resp = await client.post(
                "/api/v1/projects/create",
                json={"title": "Fresh Project", "owner": "testuser"},
            )

        assert resp.status_code == 201
        assert resp.json()["project_id"] == "PVT_NEW"
        mock_log_event.assert_awaited_once()
        assert mock_log_event.await_args.kwargs["action"] == "created"
        assert mock_log_event.await_args.kwargs["detail"] == {
            "project_name": "Fresh Project",
            "owner": "testuser",
        }

    async def test_create_project_requires_title_and_owner(self, client):
        with patch("src.api.projects.create_standalone_project", new_callable=AsyncMock) as create:
            resp = await client.post(
                "/api/v1/projects/create",
                json={"title": "Fresh Project"},
            )

        assert resp.status_code == 422
        assert resp.json()["error"] == "Both 'title' and 'owner' are required."
        create.assert_not_awaited()


# ── Cache Hit Paths ────────────────────────────────────────────────────────


class TestCacheHitPaths:
    async def test_list_projects_cache_hit(self, client, mock_github_service):
        """Cache hit returns cached projects without calling GitHub."""
        p = _project()
        with patch("src.api.projects.cache") as mock_cache:
            mock_cache.get.return_value = [p]
            resp = await client.get("/api/v1/projects")
        assert resp.status_code == 200
        assert len(resp.json()["projects"]) == 1
        mock_github_service.list_user_projects.assert_not_called()

    async def test_get_project_cache_hit(self, client, mock_github_service):
        """get_project returns project from cached list."""
        p = _project()
        with patch("src.api.projects.cache") as mock_cache:
            mock_cache.get.return_value = [p]
            resp = await client.get("/api/v1/projects/PVT_abc")
        assert resp.status_code == 200
        assert resp.json()["project_id"] == "PVT_abc"

    async def test_get_project_tasks_cache_hit(self, client, mock_github_service):
        """get_project_tasks returns cached tasks."""
        t = _task()
        with patch("src.api.projects.cache") as mock_cache:
            mock_cache.get.return_value = [t]
            resp = await client.get("/api/v1/projects/PVT_abc/tasks")
        assert resp.status_code == 200
        assert len(resp.json()["tasks"]) == 1
        mock_github_service.get_project_items.assert_not_called()


# ── _start_copilot_polling ─────────────────────────────────────────────────

PROJ = "src.api.projects"


class TestStartCopilotPolling:
    @pytest.fixture
    def session(self, mock_session):
        mock_session.access_token = "tok"
        return mock_session

    @pytest.mark.asyncio
    async def test_starts_polling_with_resolved_repo(self, session):
        """Happy path: resolve_repository returns repo info, polling starts."""
        with (
            patch(
                "src.services.copilot_polling.get_polling_status",
                return_value={"is_running": False},
            ),
            patch(
                "src.api.projects.resolve_repository",
                new=AsyncMock(return_value=("owner", "repo")),
            ),
            patch(
                "src.services.copilot_polling.ensure_polling_started",
                new_callable=AsyncMock,
            ) as mock_ensure,
        ):
            await _start_copilot_polling(session, "proj-1")

        mock_ensure.assert_awaited_once_with(
            access_token="tok",
            project_id="proj-1",
            owner="owner",
            repo="repo",
            caller="select_project",
        )

    @pytest.mark.asyncio
    async def test_stops_existing_polling_first(self, session):
        """If polling is already running, stops it before restarting."""
        with (
            patch(
                "src.services.copilot_polling.get_polling_status",
                return_value={"is_running": True},
            ),
            patch("src.services.copilot_polling.stop_polling") as mock_stop,
            patch(
                "src.api.projects.resolve_repository",
                new=AsyncMock(return_value=("o", "r")),
            ),
            patch(
                "src.services.copilot_polling.ensure_polling_started",
                new_callable=AsyncMock,
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await _start_copilot_polling(session, "proj-1")
            mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_repository_failure_skips_start(self, session):
        """When resolve_repository raises, polling is not started."""
        with (
            patch(
                "src.services.copilot_polling.get_polling_status",
                return_value={"is_running": False},
            ),
            patch(
                "src.api.projects.resolve_repository",
                new=AsyncMock(side_effect=RuntimeError("boom")),
            ),
            patch(
                "src.services.copilot_polling.ensure_polling_started",
                new_callable=AsyncMock,
            ) as ensure_polling_started,
        ):
            await _start_copilot_polling(session, "proj-1")

        ensure_polling_started.assert_not_awaited()


# ── Helpers for rate-limit mocks ───────────────────────────────────────────


def _make_request_failed(status_code: int, headers: dict | None = None):
    """Build a real ``RequestFailed`` instance with a mocked response."""
    exc = RequestFailed.__new__(RequestFailed)
    exc.response = MagicMock()
    exc.response.status_code = status_code
    exc.response.headers = headers or {}
    return exc


# ── _is_github_rate_limit_error ────────────────────────────────────────────


class TestRateLimitDetection:
    """T008-T009: direct tests for _is_github_rate_limit_error."""

    def test_primary_rate_limit_exceeded(self):
        exc = PrimaryRateLimitExceeded.__new__(PrimaryRateLimitExceeded)
        with patch("src.api.projects.github_projects_service") as svc:
            svc.get_last_rate_limit.return_value = None
            assert _is_github_rate_limit_error(exc) is True

    def test_request_failed_429(self):
        exc = _make_request_failed(429)
        with patch("src.api.projects.github_projects_service") as svc:
            svc.get_last_rate_limit.return_value = None
            assert _is_github_rate_limit_error(exc) is True

    def test_403_with_rate_limit_remaining_zero(self):
        """T008: 403 + X-RateLimit-Remaining: '0' → True."""
        exc = _make_request_failed(403, {"X-RateLimit-Remaining": "0"})
        with patch("src.api.projects.github_projects_service") as svc:
            svc.get_last_rate_limit.return_value = None
            assert _is_github_rate_limit_error(exc) is True

    def test_403_with_empty_rate_limit_dict(self):
        """T009: 403 with no remaining header and empty rl dict → False."""
        exc = _make_request_failed(403, {})
        with patch("src.api.projects.github_projects_service") as svc:
            svc.get_last_rate_limit.return_value = {}
            assert _is_github_rate_limit_error(exc) is False

    def test_403_with_nonzero_remaining(self):
        exc = _make_request_failed(403, {"X-RateLimit-Remaining": "100"})
        with patch("src.api.projects.github_projects_service") as svc:
            svc.get_last_rate_limit.return_value = None
            assert _is_github_rate_limit_error(exc) is False

    def test_generic_error_with_rate_limit_remaining_zero_in_dict(self):
        """Falls back to get_last_rate_limit() → remaining == 0 → True."""
        exc = RuntimeError("network")
        with patch("src.api.projects.github_projects_service") as svc:
            svc.get_last_rate_limit.return_value = {"remaining": 0}
            assert _is_github_rate_limit_error(exc) is True

    def test_generic_error_with_no_rate_limit_info(self):
        exc = RuntimeError("network")
        with patch("src.api.projects.github_projects_service") as svc:
            svc.get_last_rate_limit.return_value = None
            assert _is_github_rate_limit_error(exc) is False


# ── GET /projects/{id}/tasks - fallback paths ─────────────────────────────


class TestGetProjectTasksFallback:
    """T010-T011: API failure falls back to get_done_items()."""

    async def test_api_failure_returns_done_items_from_db(self, client, mock_github_service):
        """T010: cached_fetch raises → get_done_items() returns cached Task models."""
        cached_done = [
            {
                "project_id": "PVT_abc",
                "github_item_id": "PVTI_done1",
                "title": "Done task",
                "status": "Done",
                "status_option_id": "opt2",
            }
        ]
        with (
            patch(
                "src.api.projects.cached_fetch",
                new_callable=AsyncMock,
                side_effect=RuntimeError("API down"),
            ),
            patch(
                "src.api.projects.get_done_items",
                new_callable=AsyncMock,
                return_value=cached_done,
            ),
        ):
            resp = await client.get("/api/v1/projects/PVT_abc/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["title"] == "Done task"

    async def test_api_failure_and_empty_done_items_reraises(self, client, mock_github_service):
        """T011: cached_fetch raises + get_done_items() returns [] → re-raises."""
        with (
            patch(
                "src.api.projects.cached_fetch",
                new_callable=AsyncMock,
                side_effect=RuntimeError("API down"),
            ),
            patch(
                "src.api.projects.get_done_items",
                new_callable=AsyncMock,
                return_value=[],
            ),
            pytest.raises(RuntimeError, match="API down"),
        ):
            await client.get("/api/v1/projects/PVT_abc/tasks")


# ── GET /projects - cache edge cases ──────────────────────────────────────


class TestListProjectsCacheEdgeCases:
    """T012-T014: edge cases around cache truthiness and stale fallback."""

    async def test_empty_list_is_falsy_triggers_api_call(self, client, mock_github_service):
        """T012: cache returns [] (falsy) → API call triggered."""
        p = _project()
        mock_github_service.list_user_projects.return_value = [p]
        with patch("src.api.projects.cache") as mock_cache:
            mock_cache.get.return_value = []  # falsy
            resp = await client.get("/api/v1/projects", params={"refresh": False})
        # empty list is falsy → falls through to API
        assert resp.status_code == 200
        mock_github_service.list_user_projects.assert_called_once()

    async def test_cache_returns_none_triggers_api_call(self, client, mock_github_service):
        """T013: cache returns None → API call triggered."""
        mock_github_service.list_user_projects.return_value = []
        with patch("src.api.projects.cache") as mock_cache:
            mock_cache.get.return_value = None
            resp = await client.get("/api/v1/projects")
        assert resp.status_code == 200
        mock_github_service.list_user_projects.assert_called_once()

    async def test_non_rate_limit_error_with_stale_fallback(self, client, mock_github_service):
        """T014: Non-rate-limit error with stale cache available → stale served."""
        p = _project(name="Stale Project")
        mock_github_service.list_user_projects.side_effect = RuntimeError("network")
        mock_github_service.get_last_rate_limit.return_value = None  # not a rate limit
        with patch("src.api.projects.cache") as mock_cache:
            mock_cache.get.return_value = None  # no fresh cache
            mock_cache.get_stale.return_value = [p]
            resp = await client.get("/api/v1/projects")
        assert resp.status_code == 200
        assert resp.json()["projects"][0]["name"] == "Stale Project"

    async def test_non_rate_limit_error_no_stale_raises(self, client, mock_github_service):
        """Non-rate-limit error + no stale cache → raises GitHubAPIError."""
        mock_github_service.list_user_projects.side_effect = RuntimeError("network")
        mock_github_service.get_last_rate_limit.return_value = None
        with patch("src.api.projects.cache") as mock_cache:
            mock_cache.get.return_value = None
            mock_cache.get_stale.return_value = None
            resp = await client.get("/api/v1/projects")
        assert resp.status_code == 502


# ── GET /projects/{id} - cache edge cases ─────────────────────────────────


class TestGetProjectCacheEdgeCases:
    """T015-T016: get_project when project not in cached list."""

    async def test_project_not_found_after_refresh(self, client, mock_github_service):
        """T015: project not in cached list → refresh triggers → still not found → 404."""
        other = _project(project_id="PVT_other", name="Other")
        mock_github_service.list_user_projects.return_value = [other]
        with patch("src.api.projects.cache") as mock_cache:
            mock_cache.get.return_value = None  # nothing cached
            resp = await client.get("/api/v1/projects/PVT_missing")
        assert resp.status_code == 404

    async def test_api_error_propagated_through_get_project(self, client, mock_github_service):
        """T016: refresh=True via get_project but API error → error propagated."""
        mock_github_service.list_user_projects.side_effect = RuntimeError("boom")
        mock_github_service.get_last_rate_limit.return_value = None
        with patch("src.api.projects.cache") as mock_cache:
            mock_cache.get.return_value = None
            mock_cache.get_stale.return_value = None
            resp = await client.get("/api/v1/projects/PVT_abc")
        assert resp.status_code == 502


# ── WebSocket subscribe ───────────────────────────────────────────────────


class TestWebSocketSubscribe:
    """T017-T019: WebSocket endpoint internal logic."""

    async def test_auth_failure_closes_socket(self, mock_websocket_manager):
        from src.api.projects import websocket_subscribe

        mock_ws = AsyncMock()
        mock_ws.cookies = {}
        mock_ws.close = AsyncMock()

        with (
            patch(
                "src.api.projects.get_current_session",
                new_callable=AsyncMock,
                side_effect=RuntimeError("invalid session"),
            ),
            patch("src.api.projects.connection_manager", mock_websocket_manager),
        ):
            await websocket_subscribe(mock_ws, "PVT_abc")

        mock_ws.close.assert_awaited_once_with(code=1008, reason="Authentication required")
        mock_websocket_manager.connect.assert_not_called()

    async def test_access_denied_closes_before_connect(
        self, mock_session, mock_github_service, mock_websocket_manager
    ):
        from src.api.projects import websocket_subscribe
        from src.constants import SESSION_COOKIE_NAME

        mock_ws = AsyncMock()
        mock_ws.cookies = {SESSION_COOKIE_NAME: "test-session-id"}
        mock_ws.close = AsyncMock()

        with (
            patch(
                "src.api.projects.get_current_session",
                new_callable=AsyncMock,
                return_value=mock_session,
            ),
            patch("src.api.projects.cache") as mock_cache,
            patch("src.api.projects.github_projects_service", mock_github_service),
            patch("src.api.projects.connection_manager", mock_websocket_manager),
        ):
            mock_cache.get.return_value = [_project(project_id="PVT_other", name="Other")]

            await websocket_subscribe(mock_ws, "PVT_abc")

        mock_ws.close.assert_awaited_once_with(code=4403, reason="Project access denied")
        mock_websocket_manager.connect.assert_not_called()

    async def test_hash_diffing_detects_data_changes(self, client, mock_github_service):
        """T017: compute_data_hash produces different hashes for changed task data,
        driving the hash-based change detection in the WebSocket refresh loop."""
        from src.services.cache import compute_data_hash

        t1 = _task(title="v1")
        t2 = _task(title="v2")
        payload1 = [t1.model_dump(mode="json")]
        payload2 = [t2.model_dump(mode="json")]

        hash1 = compute_data_hash(payload1)
        hash2 = compute_data_hash(payload2)
        assert hash1 != hash2, "Different task data must produce different hashes"

        # Same data must produce the same hash (idempotent)
        assert compute_data_hash(payload1) == hash1

    async def test_websocket_disconnect_triggers_cleanup(
        self, mock_session, mock_github_service, mock_websocket_manager
    ):
        """T019: WebSocketDisconnect → connection_manager.disconnect called."""
        from fastapi import WebSocketDisconnect

        from src.api.projects import websocket_subscribe
        from src.constants import SESSION_COOKIE_NAME

        mock_ws = AsyncMock()
        mock_ws.cookies = {SESSION_COOKIE_NAME: "test-session-id"}
        # After connect + initial send, the receive loop raises disconnect
        mock_ws.receive_json = AsyncMock(side_effect=WebSocketDisconnect())
        mock_ws.send_json = AsyncMock()

        p = _project()
        t = _task()

        with (
            patch(
                "src.api.projects.get_current_session",
                new_callable=AsyncMock,
                return_value=mock_session,
            ),
            patch("src.api.projects.cache") as mock_cache,
            patch("src.api.projects.github_projects_service", mock_github_service),
            patch("src.api.projects.connection_manager", mock_websocket_manager),
        ):
            mock_cache.get.return_value = [p]  # project access check
            mock_github_service.get_project_items = AsyncMock(return_value=[t])
            mock_cache.get_entry.return_value = None

            await websocket_subscribe(mock_ws, "PVT_abc")

        mock_websocket_manager.disconnect.assert_called_once_with(mock_ws)

    async def test_stale_revalidation_counter_reaches_limit(
        self, mock_session, mock_github_service, mock_websocket_manager
    ):
        """T018: WebSocket subscribe handles a timeout cycle followed by
        disconnection, calling get_project_items for the initial fetch."""
        from fastapi import WebSocketDisconnect

        from src.api.projects import websocket_subscribe
        from src.constants import SESSION_COOKIE_NAME

        p = _project()
        t = _task()

        mock_ws = AsyncMock()
        mock_ws.cookies = {SESSION_COOKIE_NAME: "test-session-id"}
        mock_ws.send_json = AsyncMock()

        # First receive_json call triggers TimeoutError (simulating timeout),
        # then on next iteration we disconnect.
        receive_calls = 0

        async def mock_receive(*_a, **_kw):
            nonlocal receive_calls
            receive_calls += 1
            if receive_calls <= 1:
                raise TimeoutError()
            raise WebSocketDisconnect()

        mock_ws.receive_json = mock_receive

        with (
            patch(
                "src.api.projects.get_current_session",
                new_callable=AsyncMock,
                return_value=mock_session,
            ),
            patch("src.api.projects.cache") as mock_cache,
            patch("src.api.projects.github_projects_service", mock_github_service),
            patch("src.api.projects.connection_manager", mock_websocket_manager),
        ):
            mock_cache.get.side_effect = [
                [p],  # project access check (list of projects)
                None,  # send_tasks initial force_refresh → cache miss
                None,  # periodic send_tasks → cache miss
            ]
            mock_cache.get_stale.return_value = None
            mock_cache.get_entry.return_value = None
            mock_github_service.get_project_items = AsyncMock(return_value=[t])

            await websocket_subscribe(mock_ws, "PVT_abc")

        # The endpoint should have called get_project_items for the initial
        # force_refresh and been invoked in send_tasks
        mock_github_service.get_project_items.assert_called()


# ── New coverage tests ──────────────────────────────────────────────────────


class TestRetryAfterSeconds:
    """Cover _retry_after_seconds() — lines 52-66."""

    def test_timedelta_retry_after(self):
        from datetime import timedelta

        from src.api.projects import _retry_after_seconds

        exc = Exception("rate limit")
        exc.retry_after = timedelta(seconds=30)
        assert _retry_after_seconds(exc) == 30

    def test_timedelta_zero_returns_min_1(self):
        from datetime import timedelta

        from src.api.projects import _retry_after_seconds

        exc = Exception("rate limit")
        exc.retry_after = timedelta(seconds=0)
        assert _retry_after_seconds(exc) == 1

    def test_int_retry_after(self):
        from src.api.projects import _retry_after_seconds

        exc = Exception("rate limit")
        exc.retry_after = 45
        assert _retry_after_seconds(exc) == 45

    def test_int_zero_returns_min_1(self):
        from src.api.projects import _retry_after_seconds

        exc = Exception("rate limit")
        exc.retry_after = 0
        assert _retry_after_seconds(exc) == 1

    def test_args_fallback(self):
        from src.api.projects import _retry_after_seconds

        exc = Exception("msg", 120)
        assert _retry_after_seconds(exc) == 120

    def test_no_retry_after_returns_default(self):
        from src.api.projects import _retry_after_seconds

        exc = Exception("generic error")
        assert _retry_after_seconds(exc) == 60


class TestRateLimitDetails:
    """Cover _rate_limit_details() — lines 69-84."""

    def test_valid_dict(self):
        from src.api.projects import _rate_limit_details

        rl = {"limit": 5000, "remaining": 100, "reset_at": "2025-01-01T00:00:00Z", "used": 4900}
        with patch("src.api.projects.github_projects_service") as mock_gps:
            mock_gps.get_last_rate_limit.return_value = rl
            result = _rate_limit_details()
        assert result == {"rate_limit": rl}

    def test_non_dict_returns_empty(self):
        from src.api.projects import _rate_limit_details

        with patch("src.api.projects.github_projects_service") as mock_gps:
            mock_gps.get_last_rate_limit.return_value = None
            assert _rate_limit_details() == {}

    def test_missing_keys_returns_empty(self):
        from src.api.projects import _rate_limit_details

        with patch("src.api.projects.github_projects_service") as mock_gps:
            mock_gps.get_last_rate_limit.return_value = {"limit": 5000}
            assert _rate_limit_details() == {}


class TestListProjectsStaleCacheOnRateLimit:
    """Cover lines 146-154: rate limit + stale cache path (non-refresh)."""

    @pytest.mark.asyncio
    async def test_stale_cache_returned_on_rate_limit(self):
        from src.api.projects import list_projects

        stale_projects = [_project()]
        rate_exc = PrimaryRateLimitExceeded.__new__(PrimaryRateLimitExceeded)
        rate_exc.retry_after = 60

        mock_session = MagicMock()
        mock_session.github_user_id = "U_1"
        mock_session.github_username = "testuser"
        mock_session.access_token = "tok"

        with (
            patch("src.api.projects.github_projects_service") as mock_gps,
            patch("src.api.projects.cache") as mock_cache,
        ):
            mock_cache.get.return_value = None  # no fresh cache
            mock_gps.list_user_projects = AsyncMock(side_effect=rate_exc)
            mock_cache.get_stale.return_value = stale_projects
            mock_gps.get_last_rate_limit.return_value = None

            result = await list_projects(session=mock_session, refresh=False)

        assert result.projects == stale_projects
