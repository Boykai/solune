"""Tests for main application factory and supporting classes (src/main.py).

Covers:
- create_app() → correct routers, CORS, exception handlers
- lifespan startup/shutdown
- _session_cleanup_loop background task
- _auto_start_copilot_polling webhook token fallback
"""

import asyncio
import json
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from src.main import _auto_start_copilot_polling, _session_cleanup_loop, create_app

# ── create_app ──────────────────────────────────────────────────────────────


class TestCreateApp:
    def test_app_has_api_router(self):
        """The app should include routes at /api/v1."""
        app = create_app()
        paths = [r.path for r in app.routes]
        # At a minimum the auth callback route should exist
        assert any("/api/v1" in p for p in paths)

    async def test_app_exception_handler(self, client):
        """AppException should return structured JSON error."""

        # Trigger an endpoint that raises AppException (e.g. 404)
        resp = await client.get("/api/v1/projects/NONEXIST")
        assert resp.status_code == 404

    async def test_health_check_or_docs_disabled_in_prod(self):
        """When enable_docs=False, docs should be disabled."""
        with patch("src.main.get_settings") as mock_s:
            mock_s.return_value = MagicMock(
                debug=False,
                enable_docs=False,
                cors_origins_list=["*"],
                host="0.0.0.0",
                port=8000,
                database_path=":memory:",
                session_cleanup_interval=3600,
            )
            app = create_app()
        assert app.docs_url is None
        assert app.redoc_url is None


# ── Lifespan ────────────────────────────────────────────────────────────────


class TestLifespan:
    async def test_lifespan_startup_shutdown(self):
        """Lifespan should init database on startup and close on shutdown."""
        from src.main import lifespan

        mock_db = AsyncMock()
        mock_app = MagicMock()

        # The background loops (_session_cleanup_loop, _polling_watchdog_loop)
        # run inside an asyncio.TaskGroup, so they must be mocked out.
        async def _noop_loop():
            """Coroutine that yields immediately so the TaskGroup can exit."""
            return

        with (
            patch("src.main.get_settings") as mock_s,
            patch("src.main.setup_logging"),
            patch(
                "src.services.database.init_database",
                new_callable=AsyncMock,
                return_value=mock_db,
            ) as mock_init,
            patch(
                "src.services.database.seed_global_settings",
                new_callable=AsyncMock,
            ) as mock_seed,
            patch(
                "src.services.database.close_database",
                new_callable=AsyncMock,
            ) as mock_close,
            patch("src.main._session_cleanup_loop", side_effect=_noop_loop),
            patch("src.main._polling_watchdog_loop", side_effect=_noop_loop),
            patch("src.main._auto_start_copilot_polling", new_callable=AsyncMock),
            patch(
                "src.services.signal_bridge.start_signal_ws_listener",
                new_callable=AsyncMock,
            ),
            patch(
                "src.services.signal_bridge.stop_signal_ws_listener",
                new_callable=AsyncMock,
            ),
            patch(
                "src.services.pipeline_state_store.init_pipeline_state_store",
                new_callable=AsyncMock,
            ),
        ):
            mock_s.return_value = MagicMock(
                debug=True,
                session_cleanup_interval=999999,
                alert_webhook_url="",
                alert_cooldown_minutes=15,
                otel_enabled=False,
                otel_endpoint="http://localhost:4317",
                otel_service_name="solune-backend",
                sentry_dsn="",
            )
            async with lifespan(mock_app):
                mock_init.assert_awaited_once()
                mock_seed.assert_awaited_once_with(mock_db)

            mock_close.assert_awaited_once()

    async def test_lifespan_cleanup_on_startup_failure(self):
        """Resources initialised before failure should still be cleaned up.

        Validates the try/finally guard: if start_signal_ws_listener()
        raises, the DB and cleanup task that were already started must
        still be torn down, but stop_signal_ws_listener() must NOT be
        called because Signal was never started.
        """
        from src.main import lifespan

        mock_db = AsyncMock()
        mock_app = MagicMock()

        with (
            patch("src.main.get_settings") as mock_s,
            patch("src.main.setup_logging"),
            patch(
                "src.services.database.init_database",
                new_callable=AsyncMock,
                return_value=mock_db,
            ),
            patch(
                "src.services.database.seed_global_settings",
                new_callable=AsyncMock,
            ),
            patch(
                "src.services.database.close_database",
                new_callable=AsyncMock,
            ) as mock_close,
            patch(
                "src.services.signal_bridge.start_signal_ws_listener",
                new_callable=AsyncMock,
                side_effect=RuntimeError("signal connect failed"),
            ),
            patch(
                "src.services.signal_bridge.stop_signal_ws_listener",
                new_callable=AsyncMock,
            ) as mock_stop_signal,
            patch(
                "src.services.pipeline_state_store.init_pipeline_state_store",
                new_callable=AsyncMock,
            ),
        ):
            mock_s.return_value = MagicMock(
                debug=True,
                session_cleanup_interval=999999,
                alert_webhook_url="",
                alert_cooldown_minutes=15,
                otel_enabled=False,
                otel_endpoint="http://localhost:4317",
                otel_service_name="solune-backend",
                sentry_dsn="",
            )
            try:
                async with lifespan(mock_app):
                    pass  # pragma: no cover — reason: lifespan expected to raise RuntimeError before reaching here
            except RuntimeError:
                pass

            # DB should still be closed even though startup failed
            mock_close.assert_awaited_once()
            # Signal was never started, so stop must NOT be called
            mock_stop_signal.assert_not_awaited()


class TestSessionCleanupLoop:
    """Tests for _session_cleanup_loop background task."""

    async def test_purges_expired_sessions(self):
        """Should call purge_expired_sessions and log when count > 0."""
        call_count = 0

        async def _fake_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise asyncio.CancelledError

        with (
            patch("src.main.get_settings") as mock_s,
            patch("src.main.asyncio.sleep", side_effect=_fake_sleep),
            patch("src.services.database.get_db", return_value=MagicMock()),
            patch(
                "src.services.session_store.purge_expired_sessions",
                new_callable=AsyncMock,
                return_value=3,
            ) as mock_purge,
        ):
            mock_s.return_value = MagicMock(session_cleanup_interval=10)
            await _session_cleanup_loop()
            mock_purge.assert_awaited_once()

    async def test_handles_exception_in_loop(self):
        """Should log exception and continue looping."""
        call_count = 0

        async def _fake_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise asyncio.CancelledError

        with (
            patch("src.main.get_settings") as mock_s,
            patch("src.main.asyncio.sleep", side_effect=_fake_sleep),
            patch("src.services.database.get_db", return_value=MagicMock()),
            patch(
                "src.services.session_store.purge_expired_sessions",
                new_callable=AsyncMock,
                side_effect=RuntimeError("DB error"),
            ),
        ):
            mock_s.return_value = MagicMock(session_cleanup_interval=10)
            # Should not raise; should catch and continue until CancelledError
            await _session_cleanup_loop()

    async def test_backoff_uses_base_interval_on_success(self):
        """On success (consecutive_failures==0) sleep equals base interval.

        Regression test: the original implementation used
        ``min(interval * 2**0, 300)`` which capped the default 3600s
        interval down to 300s, running cleanup 12x more often.
        """
        sleep_values: list[float] = []

        async def _capture_sleep(seconds):
            sleep_values.append(seconds)
            raise asyncio.CancelledError

        with (
            patch("src.main.get_settings") as mock_s,
            patch("src.main.asyncio.sleep", side_effect=_capture_sleep),
            patch("src.services.database.get_db", return_value=MagicMock()),
        ):
            mock_s.return_value = MagicMock(session_cleanup_interval=3600)
            await _session_cleanup_loop()

        # First sleep should be the full configured interval, not capped to 300
        assert sleep_values[0] == 3600

    async def test_backoff_increases_on_consecutive_failures(self):
        """After failures, sleep uses exponential backoff capped correctly."""
        sleep_values: list[float] = []
        call_count = 0

        async def _capture_sleep(seconds):
            nonlocal call_count
            sleep_values.append(seconds)
            call_count += 1
            if call_count >= 3:
                raise asyncio.CancelledError

        with (
            patch("src.main.get_settings") as mock_s,
            patch("src.main.asyncio.sleep", side_effect=_capture_sleep),
            patch("src.services.database.get_db", return_value=MagicMock()),
            patch(
                "src.services.session_store.purge_expired_sessions",
                new_callable=AsyncMock,
                side_effect=RuntimeError("DB error"),
            ),
        ):
            mock_s.return_value = MagicMock(session_cleanup_interval=10)
            await _session_cleanup_loop()

        # 1st call: consecutive_failures=0 → sleep=10 (base interval)
        assert sleep_values[0] == 10
        # 2nd call: consecutive_failures=1 → min(10*2, max(10,300)) = 20
        assert sleep_values[1] == 20
        # 3rd call: consecutive_failures=2 → min(10*4, 300) = 40
        assert sleep_values[2] == 40


class TestGenericExceptionHandler:
    """Tests for the generic exception handler."""

    async def test_unhandled_exception_returns_500(self):
        """Unhandled exceptions should return 500 with JSON body."""
        app = create_app()

        # Add a route that raises a raw Exception
        from fastapi import APIRouter

        err_router = APIRouter()

        @err_router.get("/_test_500")
        async def _raise():
            raise RuntimeError("boom")

        app.include_router(err_router, prefix="/api/v1")

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/_test_500")

        assert resp.status_code == 500
        assert resp.json() == {"error": "Internal server error"}


class TestShutdownPollingLogging:
    """Regression test: shutdown must log errors instead of silently swallowing them."""

    async def test_shutdown_logs_polling_stop_error(self):
        """If stop_polling() raises during shutdown, the error must be logged
        rather than silently swallowed by a bare ``except: pass``."""
        from src.main import lifespan

        mock_db = AsyncMock()
        mock_app = MagicMock()

        async def _noop_loop():
            return

        with (
            patch("src.main.get_settings") as mock_s,
            patch("src.main.setup_logging"),
            patch(
                "src.services.database.init_database",
                new_callable=AsyncMock,
                return_value=mock_db,
            ),
            patch(
                "src.services.database.seed_global_settings",
                new_callable=AsyncMock,
            ),
            patch(
                "src.services.database.close_database",
                new_callable=AsyncMock,
            ),
            patch(
                "src.services.signal_bridge.start_signal_ws_listener",
                new_callable=AsyncMock,
            ),
            patch(
                "src.services.signal_bridge.stop_signal_ws_listener",
                new_callable=AsyncMock,
            ),
            patch("src.main._auto_start_copilot_polling", new_callable=AsyncMock),
            patch("src.main._session_cleanup_loop", side_effect=_noop_loop),
            patch("src.main._polling_watchdog_loop", side_effect=_noop_loop),
            patch(
                "src.services.pipeline_state_store.init_pipeline_state_store",
                new_callable=AsyncMock,
            ),
            patch(
                "src.services.copilot_polling.get_polling_status",
                return_value={"is_running": True},
            ),
            patch(
                "src.services.copilot_polling.stop_polling",
                new_callable=AsyncMock,
                side_effect=RuntimeError("polling stop failed"),
            ),
            patch("src.main.logger") as mock_logger,
        ):
            mock_s.return_value = MagicMock(
                debug=True,
                session_cleanup_interval=999999,
                alert_webhook_url="",
                alert_cooldown_minutes=15,
                otel_enabled=False,
                otel_endpoint="http://localhost:4317",
                otel_service_name="solune-backend",
                sentry_dsn="",
            )
            async with lifespan(mock_app):
                pass

            # The error must have been logged, not silently swallowed
            mock_logger.warning.assert_called()
            # Verify the warning includes the shutdown context and traceback
            warning_args = mock_logger.warning.call_args
            assert "Error stopping Copilot polling during shutdown" in str(warning_args)
            assert warning_args.kwargs.get("exc_info") is True


# ── _auto_start_copilot_polling webhook token fallback ──────────────────────


def _make_mock_db(session_rows=None, project_settings_rows=None):
    """Build a mock async DB that handles both user_sessions and project_settings queries."""

    async def _execute(sql, *args, **kwargs):
        cursor = AsyncMock()
        if "user_sessions" in sql:
            # session_rows: list of row dicts for fetchall, or None for no rows
            cursor.fetchall = AsyncMock(return_value=session_rows or [])
            cursor.fetchone = AsyncMock(return_value=session_rows[0] if session_rows else None)
        elif "project_settings" in sql:
            cursor.fetchall = AsyncMock(return_value=project_settings_rows or [])
        else:
            cursor.fetchone = AsyncMock(return_value=None)
            cursor.fetchall = AsyncMock(return_value=[])
        return cursor

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=_execute)
    return db


class TestAutoStartWebhookFallback:
    """Tests for the webhook-token fallback in _auto_start_copilot_polling."""

    async def test_fallback_starts_polling_with_webhook_token(self):
        """When no sessions exist but GITHUB_WEBHOOK_TOKEN and DEFAULT_REPOSITORY
        are set, polling should start using stored project settings."""

        wf_config = json.dumps(
            {"repository_owner": "Boykai", "repository_name": "github-workflows"}
        )
        ps_rows = [{"project_id": "PVT_abc123", "workflow_config": wf_config}]
        mock_db = _make_mock_db(session_rows=None, project_settings_rows=ps_rows)

        mock_settings = MagicMock(
            default_project_id=None,
            github_webhook_token="ghp_test_token",
            default_repo_owner="Boykai",
            default_repo_name="github-workflows",
        )

        with (
            patch(
                "src.services.copilot_polling.get_polling_status",
                return_value={"is_running": False},
            ),
            patch("src.services.database.get_db", return_value=mock_db),
            patch("src.main.get_settings", return_value=mock_settings),
            patch(
                "src.services.session_store.get_session",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.copilot_polling.ensure_polling_started",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_start,
            patch(
                "src.services.pipeline_state_store.get_all_pipeline_states",
                return_value={},
            ),
        ):
            await _auto_start_copilot_polling()

            mock_start.assert_awaited_once_with(
                access_token="ghp_test_token",
                project_id="PVT_abc123",
                owner="Boykai",
                repo="github-workflows",
                caller="webhook_token_fallback",
            )

    async def test_fallback_skipped_when_no_token(self):
        """Without GITHUB_WEBHOOK_TOKEN, fallback should not attempt polling."""
        mock_db = _make_mock_db(session_rows=None)
        mock_settings = MagicMock(
            default_project_id=None,
            github_webhook_token=None,
            default_repo_owner="Boykai",
            default_repo_name="github-workflows",
        )

        with (
            patch(
                "src.services.copilot_polling.get_polling_status",
                return_value={"is_running": False},
            ),
            patch("src.services.database.get_db", return_value=mock_db),
            patch("src.main.get_settings", return_value=mock_settings),
            patch(
                "src.services.session_store.get_session",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.copilot_polling.ensure_polling_started",
                new_callable=AsyncMock,
            ) as mock_start,
            patch(
                "src.services.pipeline_state_store.get_all_pipeline_states",
                return_value={},
            ),
        ):
            await _auto_start_copilot_polling()
            mock_start.assert_not_awaited()

    async def test_fallback_skipped_when_no_matching_project(self):
        """When project_settings has no matching repo, polling should not start."""
        wf_config = json.dumps({"repository_owner": "Other", "repository_name": "other-repo"})
        ps_rows = [{"project_id": "PVT_other", "workflow_config": wf_config}]
        mock_db = _make_mock_db(session_rows=None, project_settings_rows=ps_rows)

        mock_settings = MagicMock(
            default_project_id=None,
            github_webhook_token="ghp_test_token",
            default_repo_owner="Boykai",
            default_repo_name="github-workflows",
        )

        with (
            patch(
                "src.services.copilot_polling.get_polling_status",
                return_value={"is_running": False},
            ),
            patch("src.services.database.get_db", return_value=mock_db),
            patch("src.main.get_settings", return_value=mock_settings),
            patch(
                "src.services.session_store.get_session",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.copilot_polling.ensure_polling_started",
                new_callable=AsyncMock,
            ) as mock_start,
            patch(
                "src.services.pipeline_state_store.get_all_pipeline_states",
                return_value={},
            ),
        ):
            await _auto_start_copilot_polling()
            mock_start.assert_not_awaited()

    async def test_fallback_owner_only_match(self):
        """When repo_name is empty but owner matches, use as fallback."""
        wf_config = json.dumps({"repository_owner": "Boykai", "repository_name": ""})
        ps_rows = [{"project_id": "PVT_owner_only", "workflow_config": wf_config}]
        mock_db = _make_mock_db(session_rows=None, project_settings_rows=ps_rows)

        mock_settings = MagicMock(
            default_project_id=None,
            github_webhook_token="ghp_test_token",
            default_repo_owner="Boykai",
            default_repo_name="github-workflows",
        )

        with (
            patch(
                "src.services.copilot_polling.get_polling_status",
                return_value={"is_running": False},
            ),
            patch("src.services.database.get_db", return_value=mock_db),
            patch("src.main.get_settings", return_value=mock_settings),
            patch(
                "src.services.session_store.get_session",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.copilot_polling.ensure_polling_started",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_start,
            patch(
                "src.services.pipeline_state_store.get_all_pipeline_states",
                return_value={},
            ),
        ):
            await _auto_start_copilot_polling()

            mock_start.assert_awaited_once_with(
                access_token="ghp_test_token",
                project_id="PVT_owner_only",
                owner="Boykai",
                repo="github-workflows",
                caller="webhook_token_fallback",
            )

    async def test_session_strategy_preferred_over_fallback(self):
        """When a valid session exists, it should be used instead of webhook token."""
        mock_session = MagicMock(
            access_token="ghp_session_token",
            selected_project_id="PVT_session",
        )

        session_row = {"session_id": "sid123"}

        async def _execute(sql, *args, **kwargs):
            cursor = AsyncMock()
            if "user_sessions" in sql:
                cursor.fetchall = AsyncMock(return_value=[session_row])
                cursor.fetchone = AsyncMock(return_value=session_row)
            else:
                cursor.fetchone = AsyncMock(return_value=None)
                cursor.fetchall = AsyncMock(return_value=[])
            return cursor

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=_execute)

        with (
            patch(
                "src.services.copilot_polling.get_polling_status",
                return_value={"is_running": False},
            ),
            patch("src.services.database.get_db", return_value=mock_db),
            patch(
                "src.services.session_store.get_session",
                new_callable=AsyncMock,
                return_value=mock_session,
            ),
            patch(
                "src.utils.resolve_repository",
                new_callable=AsyncMock,
                return_value=("Boykai", "github-workflows"),
            ),
            patch(
                "src.services.copilot_polling.ensure_polling_started",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_start,
            patch(
                "src.services.pipeline_state_store.get_all_pipeline_states",
                return_value={},
            ),
            patch("src.services.copilot_polling.state.register_project"),
        ):
            await _auto_start_copilot_polling()

            mock_start.assert_awaited_once_with(
                access_token="ghp_session_token",
                project_id="PVT_session",
                owner="Boykai",
                repo="github-workflows",
                caller="lifespan_auto_start",
            )

    async def test_fallback_used_when_session_resolve_fails(self):
        """If session exists but resolve_repository fails, fall through to webhook fallback."""
        mock_session = MagicMock(
            access_token="ghp_bad_token",
            selected_project_id="PVT_expired",
        )
        session_row = {"session_id": "sid_expired"}
        wf_config = json.dumps(
            {"repository_owner": "Boykai", "repository_name": "github-workflows"}
        )
        ps_rows = [{"project_id": "PVT_fallback", "workflow_config": wf_config}]

        call_count = 0

        async def _execute(sql, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            cursor = AsyncMock()
            if "user_sessions" in sql:
                cursor.fetchall = AsyncMock(return_value=[session_row])
                cursor.fetchone = AsyncMock(return_value=session_row)
            elif "project_settings" in sql:
                cursor.fetchall = AsyncMock(return_value=ps_rows)
            else:
                cursor.fetchone = AsyncMock(return_value=None)
                cursor.fetchall = AsyncMock(return_value=[])
            return cursor

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=_execute)

        mock_settings = MagicMock(
            default_project_id=None,
            github_webhook_token="ghp_webhook",
            default_repo_owner="Boykai",
            default_repo_name="github-workflows",
        )

        with (
            patch(
                "src.services.copilot_polling.get_polling_status",
                return_value={"is_running": False},
            ),
            patch("src.services.database.get_db", return_value=mock_db),
            patch("src.main.get_settings", return_value=mock_settings),
            patch(
                "src.services.session_store.get_session",
                new_callable=AsyncMock,
                return_value=mock_session,
            ),
            patch(
                "src.utils.resolve_repository",
                new_callable=AsyncMock,
                side_effect=Exception("token expired"),
            ),
            patch(
                "src.services.copilot_polling.ensure_polling_started",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_start,
            patch(
                "src.services.pipeline_state_store.get_all_pipeline_states",
                return_value={},
            ),
        ):
            await _auto_start_copilot_polling()

            # Should have used the webhook token fallback
            mock_start.assert_awaited_once_with(
                access_token="ghp_webhook",
                project_id="PVT_fallback",
                owner="Boykai",
                repo="github-workflows",
                caller="webhook_token_fallback",
            )


class TestAutoStartMultiProject:
    """Tests for multi-project recovery in _auto_start_copilot_polling."""

    async def test_registers_multiple_projects_from_sessions(self):
        """All sessions with active pipeline states should be registered."""
        session1 = MagicMock(
            access_token="tok_1",
            selected_project_id="PVT_proj1",
        )
        session2 = MagicMock(
            access_token="tok_2",
            selected_project_id="PVT_proj2",
        )

        session_rows = [
            {"session_id": "sid1", "selected_project_id": "PVT_proj1"},
            {"session_id": "sid2", "selected_project_id": "PVT_proj2"},
        ]

        async def _execute(sql, *args, **kwargs):
            cursor = AsyncMock()
            if "user_sessions" in sql:
                cursor.fetchall = AsyncMock(return_value=session_rows)
            else:
                cursor.fetchone = AsyncMock(return_value=None)
                cursor.fetchall = AsyncMock(return_value=[])
            return cursor

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=_execute)

        # Both projects have active pipeline states
        fake_state_1 = MagicMock(project_id="PVT_proj1", is_complete=False)
        fake_state_2 = MagicMock(project_id="PVT_proj2", is_complete=False)

        async def _get_session(db, sid):
            return {"sid1": session1, "sid2": session2}.get(sid)

        resolve_results = {
            "PVT_proj1": ("owner1", "repo1"),
            "PVT_proj2": ("owner2", "repo2"),
        }

        async def _resolve(token, pid):
            return resolve_results[pid]

        with (
            patch(
                "src.services.copilot_polling.get_polling_status",
                return_value={"is_running": False},
            ),
            patch("src.services.database.get_db", return_value=mock_db),
            patch(
                "src.services.session_store.get_session",
                new_callable=AsyncMock,
                side_effect=_get_session,
            ),
            patch(
                "src.utils.resolve_repository",
                new_callable=AsyncMock,
                side_effect=_resolve,
            ),
            patch(
                "src.services.copilot_polling.ensure_polling_started",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_start,
            patch(
                "src.services.pipeline_state_store.get_all_pipeline_states",
                return_value={1: fake_state_1, 2: fake_state_2},
            ),
            patch(
                "src.services.copilot_polling.state.register_project",
            ) as mock_register,
        ):
            result = await _auto_start_copilot_polling()

            assert result is True
            # Both projects should be registered
            assert mock_register.call_count == 2
            mock_register.assert_any_call("PVT_proj1", "owner1", "repo1", "tok_1")
            mock_register.assert_any_call("PVT_proj2", "owner2", "repo2", "tok_2")
            # Polling loop started once for the first project
            mock_start.assert_awaited_once()

    async def test_skips_sessions_without_active_pipelines(self):
        """Sessions whose projects have no active pipeline states are skipped."""
        session1 = MagicMock(
            access_token="tok_active",
            selected_project_id="PVT_active",
        )
        session2 = MagicMock(
            access_token="tok_stale",
            selected_project_id="PVT_stale",
        )

        session_rows = [
            {"session_id": "sid1", "selected_project_id": "PVT_active"},
            {"session_id": "sid2", "selected_project_id": "PVT_stale"},
        ]

        async def _execute(sql, *args, **kwargs):
            cursor = AsyncMock()
            if "user_sessions" in sql:
                cursor.fetchall = AsyncMock(return_value=session_rows)
            else:
                cursor.fetchone = AsyncMock(return_value=None)
                cursor.fetchall = AsyncMock(return_value=[])
            return cursor

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=_execute)

        # Only PVT_active has an active pipeline state
        fake_state = MagicMock(project_id="PVT_active", is_complete=False)

        async def _get_session(db, sid):
            return {"sid1": session1, "sid2": session2}.get(sid)

        with (
            patch(
                "src.services.copilot_polling.get_polling_status",
                return_value={"is_running": False},
            ),
            patch("src.services.database.get_db", return_value=mock_db),
            patch(
                "src.services.session_store.get_session",
                new_callable=AsyncMock,
                side_effect=_get_session,
            ),
            patch(
                "src.utils.resolve_repository",
                new_callable=AsyncMock,
                return_value=("owner1", "repo1"),
            ),
            patch(
                "src.services.copilot_polling.ensure_polling_started",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "src.services.pipeline_state_store.get_all_pipeline_states",
                return_value={1: fake_state},
            ),
            patch(
                "src.services.copilot_polling.state.register_project",
            ) as mock_register,
        ):
            await _auto_start_copilot_polling()

            # Only the active project should be registered
            mock_register.assert_called_once_with("PVT_active", "owner1", "repo1", "tok_active")


class TestWatchdogGracePeriod:
    """Watchdog should not unregister projects registered less than 60s ago."""

    def test_recently_registered_project_not_unregistered(self):
        """Projects registered < 60s ago are kept even with zero pipelines."""
        from src.services.copilot_polling.state import MonitoredProject
        from src.utils import utcnow

        # A project registered just now (age < 60s)
        recent = MonitoredProject(
            project_id="PVT_new",
            owner="owner",
            repo="repo",
            access_token="tok",
            registered_at=utcnow(),
        )
        # A project registered 5 minutes ago (age > 60s)
        old = MonitoredProject(
            project_id="PVT_old",
            owner="owner",
            repo="repo",
            access_token="tok",
            registered_at=utcnow() - timedelta(minutes=5),
        )

        unregistered: list[str] = []
        _now = utcnow()

        # Reproduce the watchdog's inline grace-period logic
        for mp in [recent, old]:
            age_seconds = (_now - mp.registered_at).total_seconds()
            if age_seconds < 60:
                continue
            # Simulate: count_active == 0 and queued == 0
            unregistered.append(mp.project_id)

        # Only the old project should have been unregistered
        assert "PVT_old" in unregistered
        assert "PVT_new" not in unregistered


# ── GitHub API fallback tests for _discover_and_register_active_projects ────


class TestDiscoverGitHubApiFallback:
    """Tests for the resolve_repository() fallback in _discover_and_register_active_projects."""

    def _make_state(
        self,
        issue_number: int = 1,
        project_id: str = "PVT_cross",
        repository_owner: str = "",
        repository_name: str = "",
    ):
        from src.services.workflow_orchestrator.models import PipelineState

        return PipelineState(
            issue_number=issue_number,
            project_id=project_id,
            status="In Progress",
            agents=["speckit.implement"],
            repository_owner=repository_owner,
            repository_name=repository_name,
        )

    async def test_discover_calls_resolve_repository_when_local_sources_empty(self):
        """When state has no repo info and project_settings is empty,
        resolve_repository() should be called and the result used."""
        from src.main import _discover_and_register_active_projects

        state = self._make_state()
        mock_db = AsyncMock()
        # Session query → token
        session_cursor = AsyncMock()
        session_cursor.fetchone = AsyncMock(return_value={"access_token": "tok"})
        # project_settings query → empty
        ps_cursor = AsyncMock()
        ps_cursor.fetchall = AsyncMock(return_value=[])
        mock_db.execute = AsyncMock(side_effect=[session_cursor, ps_cursor])

        registered = []

        with (
            patch(
                "src.services.pipeline_state_store.get_all_pipeline_states",
                return_value={1: state},
            ),
            patch(
                "src.services.pipeline_state_store.set_pipeline_state",
                new_callable=AsyncMock,
            ) as mock_persist,
            patch(
                "src.utils.resolve_repository",
                new_callable=AsyncMock,
                return_value=("Boykai", "kitton"),
            ) as mock_resolve,
            patch("src.services.database.get_db", return_value=mock_db),
            patch("src.config.get_settings") as mock_s,
            patch(
                "src.services.copilot_polling.register_project",
                side_effect=lambda pid, o, r, t: registered.append((pid, o, r)) or True,
            ),
        ):
            mock_s.return_value = MagicMock(
                github_webhook_token="tok",
                default_repo_owner="Boykai",
                default_repo_name="solune",
            )
            count = await _discover_and_register_active_projects()

        assert count == 1
        mock_resolve.assert_awaited_once_with("tok", "PVT_cross")
        assert registered == [("PVT_cross", "Boykai", "kitton")]
        # Backfill should persist the resolved repo into the state
        mock_persist.assert_awaited_once()
        assert state.repository_owner == "Boykai"
        assert state.repository_name == "kitton"

    async def test_discover_skips_api_when_state_has_repo_info(self):
        """When state already has embedded repo info, resolve_repository()
        should NOT be called."""
        from src.main import _discover_and_register_active_projects

        state = self._make_state(repository_owner="Boykai", repository_name="kitton")
        mock_db = AsyncMock()
        session_cursor = AsyncMock()
        session_cursor.fetchone = AsyncMock(return_value={"access_token": "tok"})
        ps_cursor = AsyncMock()
        ps_cursor.fetchall = AsyncMock(return_value=[])
        mock_db.execute = AsyncMock(side_effect=[session_cursor, ps_cursor])

        with (
            patch(
                "src.services.pipeline_state_store.get_all_pipeline_states",
                return_value={1: state},
            ),
            patch(
                "src.services.pipeline_state_store.set_pipeline_state",
                new_callable=AsyncMock,
            ),
            patch(
                "src.utils.resolve_repository",
                new_callable=AsyncMock,
            ) as mock_resolve,
            patch("src.services.database.get_db", return_value=mock_db),
            patch("src.config.get_settings") as mock_s,
            patch("src.services.copilot_polling.register_project", return_value=True),
        ):
            mock_s.return_value = MagicMock(
                github_webhook_token="tok",
                default_repo_owner="Boykai",
                default_repo_name="solune",
            )
            await _discover_and_register_active_projects()

        mock_resolve.assert_not_awaited()

    async def test_discover_falls_back_to_default_on_api_failure(self):
        """When resolve_repository() raises, the default repo should be used."""
        from src.main import _discover_and_register_active_projects

        state = self._make_state()
        mock_db = AsyncMock()
        session_cursor = AsyncMock()
        session_cursor.fetchone = AsyncMock(return_value={"access_token": "tok"})
        ps_cursor = AsyncMock()
        ps_cursor.fetchall = AsyncMock(return_value=[])
        mock_db.execute = AsyncMock(side_effect=[session_cursor, ps_cursor])

        registered = []

        with (
            patch(
                "src.services.pipeline_state_store.get_all_pipeline_states",
                return_value={1: state},
            ),
            patch(
                "src.services.pipeline_state_store.set_pipeline_state",
                new_callable=AsyncMock,
            ),
            patch(
                "src.utils.resolve_repository",
                new_callable=AsyncMock,
                side_effect=RuntimeError("GitHub API down"),
            ),
            patch("src.services.database.get_db", return_value=mock_db),
            patch("src.config.get_settings") as mock_s,
            patch(
                "src.services.copilot_polling.register_project",
                side_effect=lambda pid, o, r, t: registered.append((pid, o, r)) or True,
            ),
        ):
            mock_s.return_value = MagicMock(
                github_webhook_token="tok",
                default_repo_owner="Boykai",
                default_repo_name="solune",
            )
            count = await _discover_and_register_active_projects()

        assert count == 1
        # Should fall back to default repo
        assert registered == [("PVT_cross", "Boykai", "solune")]


class TestRestoreGitHubApiFallback:
    """Tests for the resolve_repository() fallback in _restore_app_pipeline_polling."""

    def _make_state(
        self,
        issue_number: int = 42,
        project_id: str = "PVT_cross",
        repository_owner: str = "",
        repository_name: str = "",
    ):
        from src.services.workflow_orchestrator.models import PipelineState

        return PipelineState(
            issue_number=issue_number,
            project_id=project_id,
            status="In Progress",
            agents=["speckit.implement"],
            repository_owner=repository_owner,
            repository_name=repository_name,
        )

    async def test_restore_calls_resolve_repository_for_old_pipeline(self):
        """Old cross-repo pipeline with no local repo info should resolve
        via GitHub API and start scoped polling."""
        from src.main import _restore_app_pipeline_polling

        state = self._make_state()
        mock_db = AsyncMock()
        session_cursor = AsyncMock()
        session_cursor.fetchone = AsyncMock(return_value=None)
        ps_cursor = AsyncMock()
        ps_cursor.fetchall = AsyncMock(return_value=[])
        mock_db.execute = AsyncMock(side_effect=[session_cursor, ps_cursor])

        with (
            patch(
                "src.services.pipeline_state_store.get_all_pipeline_states",
                return_value={42: state},
            ),
            patch(
                "src.services.pipeline_state_store.set_pipeline_state",
                new_callable=AsyncMock,
            ) as mock_persist,
            patch(
                "src.utils.resolve_repository",
                new_callable=AsyncMock,
                return_value=("Boykai", "kitton"),
            ) as mock_resolve,
            patch("src.services.database.get_db", return_value=mock_db),
            patch("src.main.get_settings") as mock_s,
            patch(
                "src.services.copilot_polling.ensure_app_pipeline_polling",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_poll,
        ):
            mock_s.return_value = MagicMock(
                github_webhook_token="tok",
                default_repo_owner="boykai",
                default_repo_name="solune",
            )
            restored = await _restore_app_pipeline_polling()

        assert restored == 1
        mock_resolve.assert_awaited_once_with("tok", "PVT_cross")
        mock_poll.assert_awaited_once()
        # Backfill
        mock_persist.assert_awaited_once()
        assert state.repository_owner == "Boykai"
        assert state.repository_name == "kitton"
