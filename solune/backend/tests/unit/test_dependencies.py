from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.exceptions import AppException, AuthorizationError, ValidationError
from src.models.user import UserSession


def _request_with_state(**attrs):
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(**attrs)),
        state=SimpleNamespace(),
    )


def _session(**overrides) -> UserSession:
    defaults = {
        "github_user_id": "12345",
        "github_username": "octocat",
        "access_token": "gho_test_token",
        "selected_project_id": "PVT_123",
    }
    defaults.update(overrides)
    return UserSession(**defaults)


class TestServiceGetters:
    def test_get_github_service_prefers_app_state(self):
        from src.dependencies import get_github_service

        service = object()
        request = _request_with_state(github_service=service)

        assert get_github_service(request) is service

    def test_get_github_service_falls_back_to_global(self):
        from src.dependencies import get_github_service

        request = _request_with_state()
        fallback = object()

        with patch("src.services.github_projects.github_projects_service", fallback):
            assert get_github_service(request) is fallback

    def test_get_connection_manager_prefers_app_state(self):
        from src.dependencies import get_connection_manager

        manager = object()
        request = _request_with_state(connection_manager=manager)

        assert get_connection_manager(request) is manager

    def test_get_connection_manager_falls_back_to_global(self):
        from src.dependencies import get_connection_manager

        request = _request_with_state()
        fallback = object()

        with patch("src.services.websocket.connection_manager", fallback):
            assert get_connection_manager(request) is fallback

    def test_get_database_prefers_app_state(self):
        from src.dependencies import get_database

        db = object()
        request = _request_with_state(db=db)

        assert get_database(request) is db

    def test_get_database_falls_back_to_global(self):
        from src.dependencies import get_database

        request = _request_with_state()
        db = object()

        with patch("src.services.database.get_db", return_value=db):
            assert get_database(request) is db

    def test_get_session_dep_lazy_import_matches_auth_alias(self):
        from src.api.auth import get_session_dep as auth_get_session_dep
        from src.dependencies import _get_session_dep

        assert _get_session_dep() is auth_get_session_dep

    def test_get_chat_agent_service_reads_app_state(self):
        from src.dependencies import get_chat_agent_service

        svc = object()
        request = _request_with_state(chat_agent_service=svc)

        assert get_chat_agent_service(request) is svc

    def test_get_pipeline_run_service_reads_app_state(self):
        from src.dependencies import get_pipeline_run_service

        svc = object()
        request = _request_with_state(pipeline_run_service=svc)

        assert get_pipeline_run_service(request) is svc

    def test_get_github_auth_service_reads_app_state(self):
        from src.dependencies import get_github_auth_service

        svc = object()
        request = _request_with_state(github_auth_service=svc)

        assert get_github_auth_service(request) is svc

    def test_get_alert_dispatcher_reads_app_state(self):
        from src.dependencies import get_alert_dispatcher

        dispatcher = object()
        request = _request_with_state(alert_dispatcher=dispatcher)

        assert get_alert_dispatcher(request) is dispatcher

    # ── new accessors fail fast when app.state attribute is missing ──────

    def test_get_chat_agent_service_raises_when_missing(self):
        """New-style accessors raise a clear startup error."""
        from src.dependencies import get_chat_agent_service

        request = _request_with_state()

        with pytest.raises(RuntimeError, match="ChatAgentService is not initialised"):
            get_chat_agent_service(request)

    def test_get_pipeline_run_service_raises_when_missing(self):
        from src.dependencies import get_pipeline_run_service

        request = _request_with_state()

        with pytest.raises(RuntimeError, match="PipelineRunService is not initialised"):
            get_pipeline_run_service(request)

    def test_get_github_auth_service_raises_when_missing(self):
        from src.dependencies import get_github_auth_service

        request = _request_with_state()

        with pytest.raises(RuntimeError, match="GitHubAuthService is not initialised"):
            get_github_auth_service(request)

    def test_get_alert_dispatcher_raises_when_missing(self):
        from src.dependencies import get_alert_dispatcher

        request = _request_with_state()

        with pytest.raises(RuntimeError, match="AlertDispatcher is not initialised"):
            get_alert_dispatcher(request)

    @pytest.mark.asyncio
    async def test_require_session_honors_fastapi_dependency_overrides(self):
        from src.api.auth import get_session_dep
        from src.dependencies import _require_session

        session = _session()
        request = SimpleNamespace(
            app=SimpleNamespace(dependency_overrides={get_session_dep: lambda: session})
        )

        assert await _require_session(request, None) is session


class TestRequireAdmin:
    @pytest.mark.asyncio
    async def test_require_admin_errors_when_global_settings_row_missing(self):
        from src.dependencies import require_admin

        cursor = AsyncMock()
        cursor.fetchone.return_value = None

        db = AsyncMock()
        db.execute.return_value = cursor

        with patch("src.dependencies.get_database", return_value=db):
            with pytest.raises(AppException, match="admin settings are missing") as exc_info:
                await require_admin(_request_with_state(), _session())

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_require_admin_seeds_configured_admin_user(self):
        from src.dependencies import require_admin

        cursor = AsyncMock()
        cursor.fetchone.return_value = {"admin_github_user_id": None}

        db = AsyncMock()
        db.execute.side_effect = [cursor, AsyncMock()]

        settings = SimpleNamespace(admin_github_user_id="12345", debug=False)

        with (
            patch("src.dependencies.get_database", return_value=db),
            patch("src.config.get_settings", return_value=settings),
        ):
            session = await require_admin(_request_with_state(), _session())

        assert session.github_user_id == "12345"
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_require_admin_auto_promotes_first_debug_user(self):
        from src.dependencies import require_admin

        select_cursor = AsyncMock()
        select_cursor.fetchone.side_effect = [
            {"admin_github_user_id": None},
            {"admin_github_user_id": "12345"},
        ]
        update_cursor = AsyncMock()
        update_cursor.rowcount = 1

        db = AsyncMock()
        db.execute.side_effect = [select_cursor, update_cursor, select_cursor]

        settings = SimpleNamespace(admin_github_user_id=None, debug=True)

        @asynccontextmanager
        async def _txn(_db):
            yield

        with (
            patch("src.dependencies.get_database", return_value=db),
            patch("src.config.get_settings", return_value=settings),
            patch("src.services.chat_store.transaction", _txn),
        ):
            session = await require_admin(_request_with_state(), _session())

        assert session.github_user_id == "12345"

    @pytest.mark.asyncio
    async def test_require_admin_rejects_production_without_configured_admin(self):
        from src.dependencies import require_admin

        cursor = AsyncMock()
        cursor.fetchone.return_value = {"admin_github_user_id": None}

        db = AsyncMock()
        db.execute.return_value = cursor

        settings = SimpleNamespace(admin_github_user_id=None, debug=False)

        with (
            patch("src.dependencies.get_database", return_value=db),
            patch("src.config.get_settings", return_value=settings),
        ):
            with pytest.raises(AppException, match="ADMIN_GITHUB_USER_ID must be set") as exc_info:
                await require_admin(_request_with_state(), _session())

        assert exc_info.value.status_code == 500


class TestVerifyProjectAccess:
    @pytest.mark.asyncio
    async def test_verify_project_access_allows_owned_project(self):
        from src.dependencies import verify_project_access

        svc = AsyncMock()
        svc.list_user_projects.return_value = [SimpleNamespace(project_id="PVT_123")]

        with patch("src.dependencies.get_github_service", return_value=svc):
            await verify_project_access(_request_with_state(), "PVT_123", _session())

    @pytest.mark.asyncio
    async def test_verify_project_access_rejects_unknown_project(self):
        from src.dependencies import verify_project_access

        svc = AsyncMock()
        svc.list_user_projects.return_value = [SimpleNamespace(project_id="PVT_other")]

        with patch("src.dependencies.get_github_service", return_value=svc):
            with pytest.raises(AuthorizationError, match="do not have access"):
                await verify_project_access(_request_with_state(), "PVT_123", _session())

    @pytest.mark.asyncio
    async def test_verify_project_access_maps_service_errors(self):
        from src.dependencies import verify_project_access

        svc = AsyncMock()
        svc.list_user_projects.side_effect = RuntimeError("GitHub unavailable")

        with patch("src.dependencies.get_github_service", return_value=svc):
            with pytest.raises(AuthorizationError, match="Unable to verify project access"):
                await verify_project_access(_request_with_state(), "PVT_123", _session())

    @pytest.mark.asyncio
    async def test_verify_project_access_chains_original_exception(self):
        """Exception cause is preserved for debugging (not suppressed with 'from None')."""
        from src.dependencies import verify_project_access

        original = RuntimeError("GitHub unavailable")
        svc = AsyncMock()
        svc.list_user_projects.side_effect = original

        with patch("src.dependencies.get_github_service", return_value=svc):
            with pytest.raises(AuthorizationError) as exc_info:
                await verify_project_access(_request_with_state(), "PVT_123", _session())

        assert exc_info.value.__cause__ is original


class TestRequireSelectedProject:
    def test_require_selected_project_returns_selected_value(self):
        from src.dependencies import require_selected_project

        assert require_selected_project(_session(selected_project_id="PVT_456")) == "PVT_456"

    def test_require_selected_project_raises_without_selection(self):
        from src.dependencies import require_selected_project

        with pytest.raises(ValidationError, match="No project selected"):
            require_selected_project(_session(selected_project_id=None))


class TestClientFixtureDependencyOverrides:
    """Verify the client fixture uses dependency_overrides for all new service accessors."""

    @pytest.mark.anyio
    async def test_client_overrides_new_service_accessors(self, client):
        """The client fixture must override all four new service dependency accessors."""
        from src.dependencies import (
            get_alert_dispatcher,
            get_chat_agent_service,
            get_github_auth_service,
            get_pipeline_run_service,
        )

        overrides = client._transport.app.dependency_overrides
        assert get_chat_agent_service in overrides, "get_chat_agent_service not overridden"
        assert get_pipeline_run_service in overrides, "get_pipeline_run_service not overridden"
        assert get_github_auth_service in overrides, "get_github_auth_service not overridden"
        assert get_alert_dispatcher in overrides, "get_alert_dispatcher not overridden"

    @pytest.mark.anyio
    async def test_client_fixture_creates_fresh_app(self, client):
        """The client fixture must use a fresh app so overrides don't bleed."""
        app = client._transport.app
        # Add a custom marker — if the app were shared, a second test
        # would see it.
        app.state._test_marker = "unique"
        assert app.state._test_marker == "unique"

    @pytest.mark.anyio
    async def test_client_fixture_fresh_app_has_no_bleed(self, client):
        """Verify no state from previous test leaked through."""
        app = client._transport.app
        assert not hasattr(app.state, "_test_marker"), (
            "State from a previous test leaked — app is shared"
        )
