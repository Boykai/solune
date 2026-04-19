"""FastAPI application entry point."""
# pyright: basic
# reason: Legacy top-level module; pending follow-up typing pass.

import asyncio
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import aiosqlite
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_settings, setup_logging
from src.exceptions import AppException, RateLimitError
from src.logging_utils import get_logger
from src.middleware.request_id import request_id_var

logger = get_logger(__name__)


async def _auto_start_copilot_polling() -> bool:
    """Resume Copilot polling after a restart using persisted sessions.

    The copilot polling loop is an in-memory ``asyncio.Task`` that is
    normally started when a user selects a project in the UI.  After a
    container restart the task is lost.  This helper finds **all**
    sessions that have a ``selected_project_id`` and registers each
    project (with its session token) for multi-project monitoring before
    starting the polling loop.

    This ensures that pipelines for *every* project with an active
    session are resumed — not just the most recently selected one.

    **Fallback (no sessions):** When no user sessions exist (e.g. fresh
    container, sessions expired), the system falls back to the
    ``GITHUB_WEBHOOK_TOKEN`` and discovers the ``project_id`` from the
    persisted ``project_settings`` table.  This ensures agent pipelines
    (including Copilot Review) keep running even without an active UI
    session.
    """
    from src.services.copilot_polling import ensure_polling_started, get_polling_status
    from src.services.copilot_polling.state import register_project
    from src.services.database import get_db
    from src.services.pipeline_state_store import get_all_pipeline_states
    from src.services.session_store import get_session
    from src.utils import resolve_repository

    correlation_token = request_id_var.set(f"bg-copilot-{uuid.uuid4().hex[:8]}")
    try:
        polling_status = get_polling_status()
        if polling_status["is_running"]:
            return False

        db = get_db()

        # Collect project_ids that have active (non-complete) pipeline states.
        active_project_ids: set[str] = set()
        for state in get_all_pipeline_states().values():
            pid = getattr(state, "project_id", None)
            if pid and not getattr(state, "is_complete", False):
                active_project_ids.add(pid)

        # ── Strategy 1: Use persisted user sessions ──
        # Query ALL sessions (not just the most recent) so that every
        # project with an active pipeline can be registered for
        # multi-project monitoring with its own access token.
        cursor = await db.execute(
            """
            SELECT session_id, selected_project_id FROM user_sessions
            WHERE selected_project_id IS NOT NULL
            ORDER BY updated_at DESC
            """,
        )
        rows = await cursor.fetchall()

        first_started = False
        for row in rows:
            session = await get_session(db, row["session_id"])
            if not session or not session.selected_project_id:
                continue

            # Only register projects that have active pipeline states so
            # we don't spin up polling for stale/completed projects.
            if active_project_ids and session.selected_project_id not in active_project_ids:
                continue

            try:
                owner, repo = await resolve_repository(
                    session.access_token, session.selected_project_id
                )
            except Exception as e:
                logger.warning(
                    "Could not resolve repo for project %s — skipping: %s",
                    session.selected_project_id,
                    e,
                )
                continue

            # Register this project for multi-project monitoring
            register_project(session.selected_project_id, owner, repo, session.access_token)

            # Start the main polling loop once (it round-robins through
            # all registered projects).
            if not first_started:
                started = await ensure_polling_started(
                    access_token=session.access_token,
                    project_id=session.selected_project_id,
                    owner=owner,
                    repo=repo,
                    caller="lifespan_auto_start",
                )
                if started:
                    logger.info(
                        "Auto-started Copilot polling for project %s (%s/%s)",
                        session.selected_project_id,
                        owner,
                        repo,
                    )
                    first_started = True

        if first_started:
            return True

        # ── Strategy 2: Webhook token + project_settings fallback ──
        # When no UI session exists, use GITHUB_WEBHOOK_TOKEN and discover
        # the project_id from the persisted workflow configuration.
        settings = get_settings()
        token = settings.github_webhook_token
        owner_name = settings.default_repo_owner
        repo_name = settings.default_repo_name

        if not token or not owner_name or not repo_name:
            logger.info(
                "No active session and no GITHUB_WEBHOOK_TOKEN/DEFAULT_REPOSITORY "
                "configured — polling not auto-started"
            )
            return False

        # Prefer explicit DEFAULT_PROJECT_ID if configured.
        project_id: str | None = settings.default_project_id

        if not project_id:
            # Find the most recently updated project_settings row whose
            # workflow_config contains the default repository name.
            import json

            cursor2 = await db.execute(
                """
                SELECT project_id, workflow_config FROM project_settings
                WHERE workflow_config IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT 50
                """,
            )
            owner_only_fallback: str | None = None
            for ps_row in await cursor2.fetchall():
                try:
                    wf = json.loads(ps_row["workflow_config"])
                    wf_repo = wf.get("repository_name", "")
                    wf_owner = wf.get("repository_owner", "")

                    # Exact match: both owner and repo name match
                    if wf_repo == repo_name and (not wf_owner or wf_owner == owner_name):
                        project_id = ps_row["project_id"]
                        break

                    # Owner-only match: repo name is empty/unset but owner matches.
                    # Use as fallback if no exact match is found.
                    if not wf_repo and wf_owner == owner_name and not owner_only_fallback:
                        owner_only_fallback = ps_row["project_id"]
                except (json.JSONDecodeError, TypeError):
                    continue

            if not project_id:
                project_id = owner_only_fallback

        if not project_id:
            logger.info(
                "No project_settings entry found for %s/%s — polling not auto-started",
                owner_name,
                repo_name,
            )
            return False

        started = await ensure_polling_started(
            access_token=token,
            project_id=project_id,
            owner=owner_name,
            repo=repo_name,
            caller="webhook_token_fallback",
        )
        if started:
            logger.info(
                "Auto-started Copilot polling via webhook token for project %s (%s/%s)",
                project_id,
                owner_name,
                repo_name,
            )
        return started
    finally:
        request_id_var.reset(correlation_token)


async def _discover_and_register_active_projects() -> int:
    """Discover all projects with active pipeline states and register them.

    Reads distinct ``project_id`` values from the in-memory pipeline state
    cache, resolves each project's owner/repo from
    ``project_settings.workflow_config``, and registers them for
    multi-project monitoring.

    Returns the number of newly registered projects.
    """
    from src.services.copilot_polling import register_project
    from src.services.database import get_db
    from src.services.pipeline_state_store import get_all_pipeline_states, set_pipeline_state
    from src.utils import resolve_repository

    # Collect distinct project_ids from in-memory pipeline state cache
    active_project_ids: set[str] = set()
    # Build a lookup from pipeline state's embedded repo info (primary source)
    state_repo_map: dict[str, tuple[str, str]] = {}
    for state in get_all_pipeline_states().values():
        pid = getattr(state, "project_id", None)
        if pid:
            active_project_ids.add(pid)
            owner = getattr(state, "repository_owner", "") or ""
            repo = getattr(state, "repository_name", "") or ""
            if owner and repo and pid not in state_repo_map:
                state_repo_map[pid] = (owner, repo)

    if not active_project_ids:
        return 0

    # Resolve owner/repo and access_token for each project
    db = get_db()
    import json

    from src.config import get_settings

    settings = get_settings()
    fallback_token = settings.github_webhook_token or ""

    # Also try the most recent session token
    session_token: str | None = None
    try:
        cursor = await db.execute(
            "SELECT access_token FROM user_sessions "
            "WHERE selected_project_id IS NOT NULL "
            "ORDER BY updated_at DESC LIMIT 1",
        )
        row = await cursor.fetchone()
        if row:
            session_token = row["access_token"]
    except Exception:
        logger.debug("Could not fetch recent session token for polling", exc_info=True)

    token = session_token or fallback_token
    if not token:
        return 0

    # Build a lookup of project_id → (owner, repo) from project_settings
    project_repo_map: dict[str, tuple[str, str]] = {}
    try:
        cursor = await db.execute(
            "SELECT project_id, workflow_config FROM project_settings "
            "WHERE workflow_config IS NOT NULL",
        )
        for ps_row in await cursor.fetchall():
            try:
                wf = json.loads(ps_row["workflow_config"])
                wf_owner = wf.get("repository_owner", "")
                wf_repo = wf.get("repository_name", "")
                if wf_owner and wf_repo:
                    project_repo_map[ps_row["project_id"]] = (wf_owner, wf_repo)
            except (json.JSONDecodeError, TypeError):
                continue
    except Exception:
        logger.debug("Could not load project repo map from project_settings", exc_info=True)

    # Fallback: default repo from settings
    default_owner = settings.default_repo_owner or ""
    default_repo = settings.default_repo_name or ""

    registered_count = 0
    for pid in active_project_ids:
        # Prefer repo info embedded in pipeline state (survives restarts
        # for cross-repo pipelines), then fall back to project_settings.
        owner, repo = state_repo_map.get(pid, project_repo_map.get(pid, ("", "")))

        # If both local sources are empty, resolve via GitHub API.
        if not owner or not repo:
            try:
                owner, repo = await resolve_repository(token, pid)
                logger.info(
                    "Resolved project %s via GitHub API → %s/%s",
                    pid,
                    owner,
                    repo,
                )
                # Self-healing backfill: persist repo info so future
                # restarts skip the API call.
                for state in get_all_pipeline_states().values():
                    if getattr(state, "project_id", None) == pid:
                        if not (
                            getattr(state, "repository_owner", "")
                            and getattr(state, "repository_name", "")
                        ):
                            state.repository_owner = owner
                            state.repository_name = repo
                            await set_pipeline_state(state.issue_number, state)
            except Exception:
                logger.warning(
                    "Could not resolve repository for project %s via API, "
                    "falling back to default repo",
                    pid,
                )
                owner, repo = default_owner, default_repo

        if not owner or not repo:
            continue
        if register_project(pid, owner, repo, token):
            registered_count += 1

    if registered_count:
        logger.info(
            "Multi-project discovery: registered %d project(s) with active pipelines",
            registered_count,
        )
    return registered_count


async def _restore_app_pipeline_polling() -> int:
    """Restore scoped app-pipeline polling tasks after a container restart.

    Scans in-memory pipeline states for new-repo / external-repo app
    pipelines (where the pipeline's repo differs from the default repo)
    and restarts scoped polling for each.

    Returns the number of restored polling tasks.
    """
    from src.services.copilot_polling import ensure_app_pipeline_polling
    from src.services.database import get_db
    from src.services.pipeline_state_store import get_all_pipeline_states, set_pipeline_state
    from src.utils import resolve_repository

    settings = get_settings()
    default_owner = (settings.default_repo_owner or "").lower()
    default_repo = (settings.default_repo_name or "").lower()

    db = get_db()
    token: str | None = None
    try:
        from src.services.session_store import get_session

        cursor = await db.execute(
            "SELECT session_id FROM user_sessions "
            "WHERE selected_project_id IS NOT NULL "
            "ORDER BY updated_at DESC LIMIT 1",
        )
        row = await cursor.fetchone()
        if row:
            session = await get_session(db, row["session_id"])
            if session:
                token = session.access_token
    except Exception:
        logger.debug("Could not fetch session token for app pipeline polling", exc_info=True)

    if not token:
        token = settings.github_webhook_token
    if not token:
        return 0

    import json

    project_repo_map: dict[str, tuple[str, str]] = {}
    try:
        cursor = await db.execute(
            "SELECT project_id, workflow_config FROM project_settings "
            "WHERE workflow_config IS NOT NULL",
        )
        for ps_row in await cursor.fetchall():
            try:
                wf = json.loads(ps_row["workflow_config"])
                wf_owner = wf.get("repository_owner", "")
                wf_repo = wf.get("repository_name", "")
                if wf_owner and wf_repo:
                    project_repo_map[ps_row["project_id"]] = (wf_owner, wf_repo)
            except (json.JSONDecodeError, TypeError):
                continue
    except Exception:
        logger.debug("Could not load project repo map for app pipeline polling", exc_info=True)

    restored = 0
    for issue_number, state in get_all_pipeline_states().items():
        pid = getattr(state, "project_id", None)
        if not pid:
            continue
        if getattr(state, "is_complete", False):
            continue

        # Prefer repo info embedded in pipeline state (primary source for
        # cross-repo pipelines), then fall back to project_settings lookup.
        state_owner = getattr(state, "repository_owner", "") or ""
        state_repo = getattr(state, "repository_name", "") or ""
        if state_owner and state_repo:
            owner, repo = state_owner, state_repo
        else:
            owner, repo = project_repo_map.get(pid, ("", ""))

        # If both local sources are empty, resolve via GitHub API.
        if not owner or not repo:
            try:
                owner, repo = await resolve_repository(token, pid)
                logger.info(
                    "Resolved project %s via GitHub API for app-pipeline → %s/%s",
                    pid,
                    owner,
                    repo,
                )
                # Self-healing backfill
                if not (state_owner and state_repo):
                    state.repository_owner = owner
                    state.repository_name = repo
                    await set_pipeline_state(issue_number, state)
            except Exception:
                logger.warning(
                    "Could not resolve repository for project %s via API, "
                    "falling back to default repo",
                    pid,
                )
                owner, repo = default_owner, default_repo

        if not owner or not repo:
            continue

        # If the pipeline's repo matches the default repo, it is handled
        # by the main polling loop — no scoped task needed.
        if owner.lower() == default_owner and repo.lower() == default_repo:
            continue

        started = await ensure_app_pipeline_polling(
            access_token=token,
            project_id=pid,
            owner=owner,
            repo=repo,
            parent_issue_number=issue_number,
        )
        if started:
            restored += 1
            logger.info(
                "Restored scoped app-pipeline polling for issue #%d on %s/%s",
                issue_number,
                owner,
                repo,
            )

    if restored:
        logger.info(
            "Restored %d scoped app-pipeline polling task(s) after restart",
            restored,
        )
    return restored


async def _startup_agent_mcp_sync(db: aiosqlite.Connection) -> None:
    """Run agent MCP sync on startup to reconcile drift (FR-009).

    Uses the most recent user session to obtain credentials and project
    context.  If no session is available, the sync is silently skipped.
    """
    from src.services.agents.agent_mcp_sync import sync_agent_mcps
    from src.services.session_store import get_session
    from src.utils import resolve_repository

    cursor = await db.execute(
        """
        SELECT session_id FROM user_sessions
        WHERE selected_project_id IS NOT NULL
        ORDER BY updated_at DESC
        LIMIT 1
        """,
    )
    row = await cursor.fetchone()
    if row is None:
        logger.debug("No user session found — skipping startup agent MCP sync")
        return

    session = await get_session(db, row["session_id"])
    if not session or not session.selected_project_id:
        return

    try:
        owner, repo = await resolve_repository(session.access_token, session.selected_project_id)
    except Exception as e:
        logger.debug("Could not resolve repo for startup MCP sync: %s", e)
        return

    await sync_agent_mcps(
        owner=owner,
        repo=repo,
        project_id=session.selected_project_id,
        access_token=session.access_token,
        trigger="startup",
        db=db,
    )
    logger.info(
        "Startup agent MCP sync completed for %s/%s",
        owner,
        repo,
    )


async def _polling_watchdog_loop() -> None:
    """Watchdog task: restart the Copilot polling loop if it stops unexpectedly.

    Runs every 30 seconds and calls ``_auto_start_copilot_polling()`` whenever
    ``is_running`` is False.  Also discovers orphaned projects with active
    pipelines and registers them for multi-project monitoring.

    Uses a short fixed interval (30 s) so issues blocked by a stopped polling
    loop are unblocked within at most one minute.
    """
    from src.services.copilot_polling import get_polling_status

    consecutive_failures = 0

    while True:
        token = request_id_var.set(f"bg-polling-{uuid.uuid4().hex[:8]}")
        try:
            await asyncio.sleep(30)

            status = get_polling_status()
            if not status["is_running"]:
                logger.warning(
                    "Polling watchdog: polling loop is stopped "
                    "(errors=%d, last_error=%r) — attempting restart",
                    status.get("errors_count", 0),
                    status.get("last_error"),
                )
                try:
                    restarted = await _auto_start_copilot_polling()
                    if restarted:
                        logger.info("Polling watchdog: polling loop restarted successfully")
                    consecutive_failures = 0
                except Exception as e:
                    consecutive_failures += 1
                    logger.exception(
                        "Polling watchdog: restart attempt #%d failed: %s",
                        consecutive_failures,
                        e,
                    )

            # ── Multi-project discovery ──
            # Register any projects with active pipelines that aren't yet
            # monitored, and unregister projects with no remaining pipelines.
            try:
                await _discover_and_register_active_projects()

                # Auto-unregister projects whose pipelines have all completed
                from src.services.copilot_polling import get_monitored_projects, unregister_project
                from src.services.pipeline_state_store import (
                    count_active_pipelines_for_project,
                    get_queued_pipelines_for_project,
                )
                from src.utils import utcnow as _utcnow

                _now = _utcnow()
                for mp in get_monitored_projects():
                    # Grace period: don't unregister projects registered
                    # less than 60s ago to avoid a race between
                    # set_pipeline_state() and register_project() in
                    # execute_pipeline_launch().
                    age_seconds = (_now - mp.registered_at).total_seconds()
                    if age_seconds < 60:
                        continue
                    if (
                        count_active_pipelines_for_project(mp.project_id) == 0
                        and len(get_queued_pipelines_for_project(mp.project_id)) == 0
                    ):
                        unregister_project(mp.project_id)
            except Exception as e:
                logger.debug("Watchdog multi-project sync failed: %s", e)
        except asyncio.CancelledError:
            logger.debug("Polling watchdog task cancelled")
            break
        except Exception as e:
            logger.exception("Unexpected error in polling watchdog: %s", e)
        finally:
            request_id_var.reset(token)


async def _session_cleanup_loop() -> None:
    """Periodic background task to purge expired sessions.

    Uses exponential backoff on consecutive failures so transient DB
    errors don't spin-loop, while preserving the configured base
    interval on the success path.  The backoff cap is never lower than
    the base interval itself.
    """
    from src.services.database import get_db
    from src.services.session_store import purge_expired_sessions

    settings = get_settings()
    interval = settings.session_cleanup_interval
    consecutive_failures = 0

    while True:
        token = request_id_var.set(f"bg-cleanup-{uuid.uuid4().hex[:8]}")
        try:
            # On the success path keep the configured cadence; only apply
            # capped exponential backoff when there have been failures.
            if consecutive_failures == 0:
                sleep_time = interval
            else:
                backoff = interval * (2**consecutive_failures)
                cap = max(interval, 300)
                sleep_time = min(backoff, cap)

            await asyncio.sleep(sleep_time)
            db = get_db()
            count = await purge_expired_sessions(db)
            if count > 0:
                logger.info("Periodic cleanup: purged %d expired sessions", count)
            consecutive_failures = 0
        except asyncio.CancelledError:
            logger.debug("Session cleanup task cancelled")
            break
        except Exception as e:
            consecutive_failures += 1
            logger.exception(
                "Error in session cleanup task (consecutive_failures=%d): %s",
                consecutive_failures,
                e,
            )
        finally:
            request_id_var.reset(token)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan handler.

    Uses :class:`asyncio.TaskGroup` for background tasks so they are
    automatically cancelled and awaited on shutdown.  Fire-and-forget
    tasks go through :data:`task_registry` and are drained before the
    database is closed.
    """
    settings = get_settings()
    setup_logging(settings.debug, structured=not settings.debug)
    logger.info("Starting Solune API")

    from src.services.database import close_database, init_database, seed_global_settings
    from src.services.signal_bridge import start_signal_ws_listener, stop_signal_ws_listener
    from src.services.task_registry import task_registry

    db = None
    signal_started = False

    try:
        # Install a global asyncio exception handler so unhandled async
        # errors are logged with context instead of silently swallowed.
        loop = asyncio.get_running_loop()

        def _asyncio_exception_handler(_loop: asyncio.AbstractEventLoop, context: dict) -> None:
            exc = context.get("exception")
            msg = context.get("message", "Unhandled async exception")
            logger.error(
                "Async exception: %s — %s",
                msg,
                exc,
                exc_info=(
                    (type(exc), exc, getattr(exc, "__traceback__", None))
                    if exc is not None
                    else None
                ),
            )

        loop.set_exception_handler(_asyncio_exception_handler)

        # Initialize SQLite database, run migrations, seed global settings
        db = await init_database()
        await seed_global_settings(db)
        _app.state.db = db

        # Load persisted pipeline state from SQLite into L1 caches
        from src.services.pipeline_state_store import init_pipeline_state_store

        await init_pipeline_state_store(db)

        # Initialise Done-items DB cache for cold-start optimisation
        from src.services.done_items_store import init_done_items_store

        await init_done_items_store(db)

        # Register singleton services on app.state for DI (see dependencies.py)
        from src.services.github_projects import github_projects_service
        from src.services.websocket import connection_manager

        _app.state.github_service = github_projects_service
        _app.state.connection_manager = connection_manager

        # ── Services migrated from module-level lazy singletons ──
        from src.services.chat_agent import ChatAgentService
        from src.services.github_auth import github_auth_service

        try:
            _app.state.chat_agent_service = ChatAgentService()
        except Exception:  # noqa: BLE001 — reason: fail-fast startup; logged before re-raise
            logger.critical("Failed to initialise ChatAgentService", exc_info=True)
            raise

        _app.state.github_auth_service = github_auth_service

        from src.services.copilot_polling.pipeline_state_service import PipelineRunService

        try:
            _app.state.pipeline_run_service = PipelineRunService(db)
        except Exception:  # noqa: BLE001 — reason: fail-fast startup; logged before re-raise
            logger.critical("Failed to initialise PipelineRunService", exc_info=True)
            raise

        # ── Observability: Alert dispatcher (Phase 5) ──
        from src.services.alert_dispatcher import AlertDispatcher, set_dispatcher

        _alert_dispatcher = AlertDispatcher(
            webhook_url=settings.alert_webhook_url,
            cooldown_minutes=settings.alert_cooldown_minutes,
        )
        _app.state.alert_dispatcher = _alert_dispatcher
        set_dispatcher(_alert_dispatcher)

        # ── Observability: OpenTelemetry (Phase 5) ──
        if settings.otel_enabled:
            from src.services.otel_setup import init_otel

            tracer, meter = init_otel(settings.otel_service_name, settings.otel_endpoint)
            _app.state.otel_tracer = tracer
            _app.state.otel_meter = meter
        else:
            _app.state.otel_tracer = None
            _app.state.otel_meter = None

        # ── Observability: Sentry (Phase 5) ──
        if settings.sentry_dsn:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                traces_sample_rate=0,  # avoid double-tracing when OTel is also active
                integrations=[FastApiIntegration()],
            )
            logger.info("Sentry SDK initialised")

        # Start Signal WebSocket listener for inbound messages
        await start_signal_ws_listener()
        signal_started = True

        # Auto-resume Copilot polling so agent pipelines survive restarts
        try:
            await _auto_start_copilot_polling()
        except Exception as e:
            logger.exception("Failed to auto-start Copilot polling (non-fatal): %s", e)

        # Discover all projects with active pipelines and register them
        # for multi-project monitoring (survives container restarts).
        try:
            await _discover_and_register_active_projects()
        except Exception as e:
            logger.warning("Multi-project discovery failed (non-fatal): %s", e)

        # Restore scoped app-pipeline polling for new-repo / external-repo
        # apps whose polling tasks were lost during the restart.
        try:
            await _restore_app_pipeline_polling()
        except Exception as e:
            logger.warning("App-pipeline polling restore failed (non-fatal): %s", e)

        # Agent MCP sync — fire-and-forget via TaskRegistry
        async def _run_startup_agent_mcp_sync_background() -> None:
            try:
                await _startup_agent_mcp_sync(db)
            except Exception as e:
                logger.warning("Startup agent MCP sync failed (non-fatal): %s", e)

        task_registry.create_task(_run_startup_agent_mcp_sync_background(), name="startup-mcp-sync")

        # Use TaskGroup for long-running background loops — automatic
        # cancellation and awaiting on exit.
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(_session_cleanup_loop())
                tg.create_task(_polling_watchdog_loop())
                yield
        except* Exception as eg:
            for exc in eg.exceptions:
                logger.error("Background task failed during lifespan: %s", exc, exc_info=exc)
    finally:
        # Stop known long-lived tasks first so they don't block the drain.
        if signal_started:
            await stop_signal_ws_listener()

        # Drain remaining fire-and-forget tasks tracked by the registry
        # before tearing down the database connection.
        await task_registry.drain(drain_timeout=30.0)

        # Stop Copilot polling if it was auto-started or started via the UI
        try:
            from src.services.copilot_polling import get_polling_status, stop_polling

            if get_polling_status()["is_running"]:
                await stop_polling()
        except Exception as e:
            logger.warning("Error stopping Copilot polling during shutdown: %s", e, exc_info=True)

        if db is not None:
            await close_database()
        logger.info("Shutting down Solune API")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Solune API",
        description="REST API for Solune",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.enable_docs else None,
        redoc_url="/api/redoc" if settings.enable_docs else None,
    )

    # CORS middleware — explicit methods and headers reduce attack surface.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "X-Request-ID",
            "X-Requested-With",
            "X-CSRF-Token",
        ],
    )

    # Request-ID middleware (must be added after CORS — Starlette LIFO order)
    from src.middleware.request_id import RequestIDMiddleware

    app.add_middleware(RequestIDMiddleware)

    # Content Security Policy middleware
    from src.middleware.csp import CSPMiddleware

    app.add_middleware(CSPMiddleware)

    # CSRF protection — double-submit cookie for state-changing requests
    from src.middleware.csrf import CSRFMiddleware

    app.add_middleware(CSRFMiddleware)

    # Rate limiting — slowapi state + exception handler
    from typing import cast

    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from starlette.types import ExceptionHandler

    from src.middleware.rate_limit import RateLimitKeyMiddleware, limiter

    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        cast(ExceptionHandler, _rate_limit_exceeded_handler),
    )
    app.add_middleware(RateLimitKeyMiddleware)

    # Exception handlers
    @app.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
        headers: dict[str, str] = {}
        if isinstance(exc, RateLimitError):
            headers["Retry-After"] = str(exc.retry_after)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "details": exc.details,
            },
            headers=headers or None,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        from src.middleware.request_id import request_id_var

        rid = request_id_var.get("")
        logger.exception(
            "Unhandled exception: %s | request_id=%s method=%s path=%s",
            type(exc).__name__,
            rid,
            _request.method,
            _request.url.path,
        )

        # ── Sentry capture (Phase 5) ──
        try:
            import sentry_sdk

            if sentry_sdk.is_initialized():
                with sentry_sdk.new_scope() as scope:
                    scope.set_tag("request_id", rid)
                    scope.set_context(
                        "request",
                        {"path": _request.url.path, "method": _request.method},
                    )
                    sentry_sdk.capture_exception(exc)
        except Exception:
            pass  # Sentry capture is best-effort

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error"},
        )

    # Include API routes (imported here to avoid circular import)
    from src.api import router as api_router

    app.include_router(api_router, prefix="/api/v1")

    # MCP server configuration discovery endpoint (FR-037)
    # Registered BEFORE the MCP mount so Starlette's router matches
    # the explicit route before the catch-all mount prefix.
    # Available regardless of mcp_server_enabled so clients can check.
    @app.get("/api/v1/mcp/config")
    async def mcp_server_config() -> dict:
        """Return MCP server connection details for external agents."""
        return {
            "server_name": settings.mcp_server_name,
            "enabled": settings.mcp_server_enabled,
            "url": "/api/v1/mcp",
            "transport": "streamable-http",
            "auth": {
                "type": "bearer",
                "description": "Provide a GitHub Personal Access Token (PAT) as a Bearer token.",
            },
        }

    # ── MCP Server (v0.4.0) — mount when enabled ──
    if settings.mcp_server_enabled:
        from src.services.mcp_server import create_mcp_server, get_mcp_app
        from src.services.mcp_server.middleware import McpAuthMiddleware
        from src.services.mcp_server.server import get_token_verifier

        create_mcp_server()
        mcp_app = get_mcp_app()
        verifier = get_token_verifier()
        if verifier is not None:
            mcp_app = McpAuthMiddleware(mcp_app, verifier)
        app.mount("/api/v1/mcp", mcp_app)
        logger.info("MCP server mounted at /api/v1/mcp")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
