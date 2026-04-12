"""Bootstrap and background tasks extracted from main.py.

Contains startup routines (auto-polling, project discovery, MCP sync)
and long-running background loops (watchdog, session cleanup).
"""

import asyncio
import uuid

import aiosqlite

from src.config import get_settings
from src.logging_utils import get_logger
from src.middleware.request_id import request_id_var

logger = get_logger(__name__)


async def auto_start_copilot_polling() -> bool:
    """Resume Copilot polling after a restart using a persisted session.

    The copilot polling loop is an in-memory ``asyncio.Task`` that is
    normally started when a user selects a project in the UI.  After a
    container restart the task is lost.  This helper finds the most
    recently updated session that already has a ``selected_project_id``
    and automatically re-starts the polling loop so agent pipelines
    continue without manual intervention.

    **Fallback (no sessions):** When no user sessions exist (e.g. fresh
    container, sessions expired), the system falls back to the
    ``GITHUB_WEBHOOK_TOKEN`` and discovers the ``project_id`` from the
    persisted ``project_settings`` table.  This ensures agent pipelines
    (including Copilot Review) keep running even without an active UI
    session.
    """
    from src.services.copilot_polling import ensure_polling_started, get_polling_status
    from src.services.database import get_db
    from src.services.session_store import get_session
    from src.utils import resolve_repository

    correlation_token = request_id_var.set(f"bg-copilot-{uuid.uuid4().hex[:8]}")
    try:
        polling_status = get_polling_status()
        if polling_status["is_running"]:
            return False

        db = get_db()

        # ── Strategy 1: Use a persisted user session ──
        cursor = await db.execute(
            """
            SELECT session_id FROM user_sessions
            WHERE selected_project_id IS NOT NULL
            ORDER BY updated_at DESC
            LIMIT 1
            """,
        )
        row = await cursor.fetchone()

        if row is not None:
            session = await get_session(db, row["session_id"])
            if session and session.selected_project_id:
                try:
                    owner, repo = await resolve_repository(
                        session.access_token, session.selected_project_id
                    )
                except Exception as e:
                    logger.warning(
                        "Could not resolve repo for project %s — trying webhook token fallback: %s",
                        session.selected_project_id,
                        e,
                    )
                else:
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
                    return started

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


async def discover_and_register_active_projects() -> int:
    """Discover all projects with active pipeline states and register them.

    Reads distinct ``project_id`` values from the in-memory pipeline state
    cache, resolves each project's owner/repo from
    ``project_settings.workflow_config``, and registers them for
    multi-project monitoring.

    Returns the number of newly registered projects.
    """
    from src.services.copilot_polling import register_project
    from src.services.database import get_db
    from src.services.pipeline_state_store import get_all_pipeline_states

    # Collect distinct project_ids from in-memory pipeline state cache
    active_project_ids: set[str] = set()
    for state in get_all_pipeline_states().values():
        pid = getattr(state, "project_id", None)
        if pid:
            active_project_ids.add(pid)

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
        pass

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
        pass

    # Fallback: default repo from settings
    default_owner = settings.default_repo_owner or ""
    default_repo = settings.default_repo_name or ""

    registered_count = 0
    for pid in active_project_ids:
        owner, repo = project_repo_map.get(pid, (default_owner, default_repo))
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


async def restore_app_pipeline_polling() -> int:
    """Restore scoped app-pipeline polling tasks after a container restart.

    Scans in-memory pipeline states for new-repo / external-repo app
    pipelines (where the pipeline's repo differs from the default repo)
    and restarts scoped polling for each.

    Returns the number of restored polling tasks.
    """
    from src.services.copilot_polling import ensure_app_pipeline_polling
    from src.services.database import get_db
    from src.services.pipeline_state_store import get_all_pipeline_states

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
        pass

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
        pass

    restored = 0
    for issue_number, state in get_all_pipeline_states().items():
        pid = getattr(state, "project_id", None)
        if not pid:
            continue
        if getattr(state, "is_complete", False):
            continue

        owner, repo = project_repo_map.get(pid, (default_owner, default_repo))
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


async def startup_agent_mcp_sync(db: aiosqlite.Connection) -> None:
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


async def polling_watchdog_loop() -> None:
    """Watchdog task: restart the Copilot polling loop if it stops unexpectedly.

    Runs every 30 seconds and calls ``auto_start_copilot_polling()`` whenever
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
                    restarted = await auto_start_copilot_polling()
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
                await discover_and_register_active_projects()

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


async def session_cleanup_loop() -> None:
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
