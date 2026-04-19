"""FastAPI dependency-injection helpers.

Provide singleton services stored on ``app.state`` to endpoint handlers via
``Depends()``. The lifespan in ``main.py`` is responsible for registering
instances on ``app.state`` at startup.

Legacy getters for GitHub, WebSocket, and database access still fall back to
module-level globals during the transition. New singleton accessors are
``app.state``-only and fail fast with a clear error when startup has not run.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

from fastapi import Cookie, Depends, Request

from src.constants import SESSION_COOKIE_NAME
from src.exceptions import AppException, AuthorizationError
from src.logging_utils import get_logger

if TYPE_CHECKING:
    import aiosqlite

    from src.models.user import UserSession
    from src.services.alert_dispatcher import AlertDispatcher
    from src.services.chat_agent import ChatAgentService
    from src.services.copilot_polling.pipeline_state_service import PipelineRunService
    from src.services.github_auth import GitHubAuthService
    from src.services.github_projects import GitHubProjectsService
    from src.services.websocket import ConnectionManager

logger = get_logger(__name__)


def _get_required_app_state_attr(request: Request, attr: str, service_name: str) -> object:
    """Return a required ``app.state`` attribute or raise a clear startup error."""
    try:
        return getattr(request.app.state, attr)
    except AttributeError as exc:
        raise RuntimeError(
            f"{service_name} is not initialised on app.state; "
            "did you forget to run lifespan startup?"
        ) from exc


def get_github_service(request: Request) -> GitHubProjectsService:
    """Return the singleton :class:`GitHubProjectsService`."""
    svc = getattr(request.app.state, "github_service", None)
    if svc is not None:
        return svc
    # Fallback to module-level global during transition
    from src.services.github_projects import github_projects_service

    return github_projects_service


def get_connection_manager(request: Request) -> ConnectionManager:
    """Return the singleton :class:`ConnectionManager`."""
    mgr = getattr(request.app.state, "connection_manager", None)
    if mgr is not None:
        return mgr
    from src.services.websocket import connection_manager

    return connection_manager


def get_database(request: Request) -> aiosqlite.Connection:
    """Return the application database connection."""
    db = getattr(request.app.state, "db", None)
    if db is not None:
        return db
    from src.services.database import get_db

    return get_db()


def get_chat_agent_service(request: Request) -> ChatAgentService:
    """Return the singleton :class:`ChatAgentService` from ``app.state``."""
    return _get_required_app_state_attr(request, "chat_agent_service", "ChatAgentService")  # type: ignore[no-any-return]


def get_pipeline_run_service(request: Request) -> PipelineRunService:
    """Return the singleton :class:`PipelineRunService` from ``app.state``."""
    return _get_required_app_state_attr(request, "pipeline_run_service", "PipelineRunService")  # type: ignore[no-any-return]


def get_github_auth_service(request: Request) -> GitHubAuthService:
    """Return the singleton :class:`GitHubAuthService` from ``app.state``."""
    return _get_required_app_state_attr(request, "github_auth_service", "GitHubAuthService")  # type: ignore[no-any-return]


def get_alert_dispatcher(request: Request) -> AlertDispatcher:
    """Return the singleton :class:`AlertDispatcher` from ``app.state``."""
    return _get_required_app_state_attr(request, "alert_dispatcher", "AlertDispatcher")  # type: ignore[no-any-return]


def _get_session_dep():
    """Lazy import to avoid circular imports with api.auth at module level."""
    from src.api.auth import get_session_dep

    return get_session_dep


async def _require_session(
    request: Request,
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> UserSession:
    """Resolve the current session without importing auth dependencies eagerly."""
    get_session_dep = _get_session_dep()
    # FastAPI overrides are keyed by the original dependency callable
    # (get_session_dep). Because this helper wraps that callable to avoid a
    # circular import, tests that override get_session_dep would otherwise be
    # bypassed and fall back to real cookie resolution.
    dependency_override = request.app.dependency_overrides.get(get_session_dep)
    if dependency_override is not None:
        result = dependency_override()
        if inspect.isawaitable(result):
            return await result
        return result

    return await get_session_dep(session_id)


_session_dependency = Depends(_require_session)


async def require_admin(
    request: Request,
    session: UserSession = _session_dependency,
) -> UserSession:
    """Verify the current session belongs to the admin user.

    Checks ``session.github_user_id`` against the
    ``admin_github_user_id`` column in ``global_settings``.
    If no admin has been set yet (NULL) and ``ADMIN_GITHUB_USER_ID`` is
    configured, only the designated user is allowed and the DB is seeded.
    In debug mode without an explicit admin, the first user is
    auto-promoted. In production without an explicit admin, a 500 is
    raised.

    Returns the session if authorized; raises *403* otherwise.
    """
    db = get_database(request)
    cursor = await db.execute("SELECT admin_github_user_id FROM global_settings WHERE id = 1")
    row = await cursor.fetchone()

    if row is None:
        # The global_settings singleton row is missing; this is a server
        # misconfiguration — seed_global_settings() should have created it.
        logger.error(
            "global_settings row with id=1 is missing when verifying admin user "
            "(GitHub user id: %s)",
            session.github_user_id,
        )
        raise AppException(
            message="Server configuration error: admin settings are missing.",
            status_code=500,
        )

    admin_user_id = row["admin_github_user_id"] if isinstance(row, dict) else row[0]

    if admin_user_id is None:
        from src.config import get_settings

        settings = get_settings()
        if settings.admin_github_user_id:
            # Explicit admin designation via ADMIN_GITHUB_USER_ID env var
            if str(session.github_user_id) != str(settings.admin_github_user_id):
                raise AuthorizationError("Admin access required")
            # Set the configured user as admin in the database
            await db.execute(
                "UPDATE global_settings SET admin_github_user_id = ? WHERE id = 1",
                (settings.admin_github_user_id,),
            )
            await db.commit()
            logger.info(
                "Set configured admin user %s (%s) from ADMIN_GITHUB_USER_ID env var",
                session.github_username,
                session.github_user_id,
            )
            return session
        # No ADMIN_GITHUB_USER_ID configured
        if not settings.debug:
            # Production: refuse to auto-promote — config validator should
            # have caught this at startup, but defend in depth.
            raise AppException(
                message="ADMIN_GITHUB_USER_ID must be set in production mode.",
                status_code=500,
            )
        # Debug mode only: auto-promote first user
        logger.warning(
            "ADMIN_GITHUB_USER_ID not set — auto-promoting first user %s (%s). "
            "This is only allowed in debug mode.",
            session.github_username,
            session.github_user_id,
        )
        # Auto-promote first authenticated user atomically to prevent race conditions
        from src.services.chat_store import transaction

        async with transaction(db):
            cursor = await db.execute(
                "UPDATE global_settings SET admin_github_user_id = ? "
                "WHERE id = 1 AND admin_github_user_id IS NULL",
                (session.github_user_id,),
            )
            promoted = cursor.rowcount > 0

        if promoted:
            logger.info(
                "Auto-promoted user %s (%s) as admin",
                session.github_username,
                session.github_user_id,
            )
            return session
        # Another user was promoted concurrently — re-read to check
        cursor = await db.execute("SELECT admin_github_user_id FROM global_settings WHERE id = 1")
        row = await cursor.fetchone()
        if row is None:
            # The global_settings singleton row is missing — this should
            # never happen since we just read it above.  Surface a clear
            # 500 rather than an opaque AttributeError.
            logger.error(
                "global_settings row with id=1 is missing when verifying "
                "admin user (GitHub user id: %s)",
                session.github_user_id,
            )
            raise AppException(
                message="Server configuration error: admin settings are missing.",
                status_code=500,
            )
        admin_user_id = row["admin_github_user_id"] if isinstance(row, dict) else row[0]

    if str(session.github_user_id) != str(admin_user_id):
        raise AuthorizationError("Admin access required")

    return session


async def verify_project_access(
    request: Request,
    project_id: str,
    session: UserSession = _session_dependency,
) -> None:
    """Verify the authenticated user has access to *project_id*.

    Checks the cross-request user-projects cache first (populated by
    list_projects, select_project, etc.) to avoid a redundant GraphQL call.
    Falls back to a live ``list_user_projects`` query on cache miss.
    Raises HTTP 403 if the user does not own or have access to the project.
    """
    from src.services.cache import cache, get_user_projects_cache_key

    cache_key = get_user_projects_cache_key(session.github_user_id)
    projects = cache.get(cache_key)

    if projects is None:
        svc = get_github_service(request)
        try:
            projects = await svc.list_user_projects(session.access_token, session.github_username)
            cache.set(cache_key, projects)
        except Exception as e:
            logger.warning(
                "Failed to verify project access for user=%s project=%s: %s",
                session.github_username,
                project_id,
                e,
                exc_info=True,
            )
            raise AuthorizationError("Unable to verify project access") from e

    if any(p.project_id == project_id for p in projects):
        # Stash on request state so downstream handlers can reuse without
        # a second GraphQL call (e.g. get_project() during POST /select).
        request.state.verified_projects = projects
        return

    raise AuthorizationError("You do not have access to this project")


def require_selected_project(session: UserSession) -> str:
    """Return the selected project ID or raise :class:`ValidationError`.

    Use this in any endpoint that requires a project to be selected,
    instead of repeating inline ``if not session.selected_project_id``
    guards with inconsistent error messages.

    Returns:
        The non-empty ``selected_project_id`` string.

    Raises:
        src.exceptions.ValidationError: If no project is selected.
    """
    from src.exceptions import ValidationError

    if not session.selected_project_id:
        raise ValidationError("No project selected. Please select a project first.")
    return session.selected_project_id
