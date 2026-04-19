"""Step 15: Enqueue long-running background loop coroutines."""

from __future__ import annotations

import asyncio
import uuid

from src.logging_utils import get_logger
from src.middleware.request_id import request_id_var
from src.startup.protocol import StartupContext

logger = get_logger(__name__)


async def _session_cleanup_loop() -> None:
    """Periodic background task to purge expired sessions."""
    from src.config import get_settings
    from src.services.database import get_db
    from src.services.session_store import purge_expired_sessions

    settings = get_settings()
    interval = settings.session_cleanup_interval
    consecutive_failures = 0

    while True:
        token = request_id_var.set(f"bg-cleanup-{uuid.uuid4().hex[:8]}")
        try:
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


async def _polling_watchdog_loop() -> None:
    """Watchdog task: restart the Copilot polling loop if it stops unexpectedly."""
    from src.services.copilot_polling import (
        ensure_polling_started,
        get_monitored_projects,
        get_polling_status,
        unregister_project,
    )
    from src.services.pipeline_state_store import (
        count_active_pipelines_for_project,
        get_all_pipeline_states,
        get_queued_pipelines_for_project,
    )
    from src.utils import utcnow as _utcnow

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
                    # Inline auto-start logic (can't import from other step modules)
                    from src.services.copilot_polling import ensure_polling_started
                    from src.services.copilot_polling.state import register_project
                    from src.services.database import get_db
                    from src.services.session_store import get_session
                    from src.utils import resolve_repository

                    db = get_db()

                    active_project_ids: set[str] = set()
                    for st in get_all_pipeline_states().values():
                        pid = getattr(st, "project_id", None)
                        if pid and not getattr(st, "is_complete", False):
                            active_project_ids.add(pid)

                    cursor = await db.execute(
                        "SELECT session_id, selected_project_id FROM user_sessions "
                        "WHERE selected_project_id IS NOT NULL ORDER BY updated_at DESC",
                    )
                    rows = await cursor.fetchall()

                    first_started = False
                    for row in rows:
                        session = await get_session(db, row["session_id"])
                        if not session or not session.selected_project_id:
                            continue
                        if (
                            active_project_ids
                            and session.selected_project_id not in active_project_ids
                        ):
                            continue
                        try:
                            owner, repo = await resolve_repository(
                                session.access_token, session.selected_project_id
                            )
                        except Exception:
                            continue
                        register_project(
                            session.selected_project_id, owner, repo, session.access_token
                        )
                        if not first_started:
                            restarted = await ensure_polling_started(
                                access_token=session.access_token,
                                project_id=session.selected_project_id,
                                owner=owner,
                                repo=repo,
                                caller="watchdog_restart",
                            )
                            if restarted:
                                logger.info("Polling watchdog: polling loop restarted successfully")
                                first_started = True

                    consecutive_failures = 0
                except Exception as e:
                    consecutive_failures += 1
                    logger.exception(
                        "Polling watchdog: restart attempt #%d failed: %s",
                        consecutive_failures,
                        e,
                    )

            # ── Multi-project discovery ──
            try:
                from src.config import get_settings as _get_settings
                from src.services.copilot_polling import register_project as _reg_proj
                from src.services.database import get_db as _get_db

                _settings = _get_settings()
                _db = _get_db()
                _fallback_token = _settings.github_webhook_token or ""

                _session_tok: str | None = None
                try:
                    _cur = await _db.execute(
                        "SELECT access_token FROM user_sessions "
                        "WHERE selected_project_id IS NOT NULL "
                        "ORDER BY updated_at DESC LIMIT 1",
                    )
                    _row = await _cur.fetchone()
                    if _row:
                        _session_tok = _row["access_token"]
                except Exception:
                    pass

                _token = _session_tok or _fallback_token

                if _token:
                    import json as _json

                    _proj_repo_map: dict[str, tuple[str, str]] = {}
                    try:
                        _c2 = await _db.execute(
                            "SELECT project_id, workflow_config FROM project_settings "
                            "WHERE workflow_config IS NOT NULL",
                        )
                        for _ps in await _c2.fetchall():
                            try:
                                _wf = _json.loads(_ps["workflow_config"])
                                _wo = _wf.get("repository_owner", "")
                                _wr = _wf.get("repository_name", "")
                                if _wo and _wr:
                                    _proj_repo_map[_ps["project_id"]] = (_wo, _wr)
                            except (ValueError, TypeError):
                                continue
                    except Exception:
                        pass

                    _all_states = get_all_pipeline_states()
                    _active_pids: set[str] = set()
                    _state_repo_map: dict[str, tuple[str, str]] = {}
                    for _st in _all_states.values():
                        _pid = getattr(_st, "project_id", None)
                        if _pid:
                            _active_pids.add(_pid)
                            _so = getattr(_st, "repository_owner", "") or ""
                            _sr = getattr(_st, "repository_name", "") or ""
                            if _so and _sr:
                                _state_repo_map[_pid] = (_so, _sr)

                    from src.utils import resolve_repository as _resolve_repo

                    _registered = 0
                    for _pid in _active_pids:
                        _o, _r = _state_repo_map.get(_pid, _proj_repo_map.get(_pid, ("", "")))
                        if not _o or not _r:
                            try:
                                _o, _r = await _resolve_repo(_token, _pid)
                            except Exception:
                                _o, _r = (
                                    (_settings.default_repo_owner or ""),
                                    (_settings.default_repo_name or ""),
                                )
                        if _o and _r:
                            if _reg_proj(_pid, _o, _r, _token):
                                _registered += 1

                    if _registered:
                        logger.debug(
                            "Watchdog multi-project sync: registered %d project(s)",
                            _registered,
                        )

                # Auto-unregister projects whose pipelines have all completed
                _now = _utcnow()
                for mp in get_monitored_projects():
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


class BackgroundLoopsStep:
    name = "background_loops"
    fatal = True

    async def run(self, ctx: StartupContext) -> None:
        """Enqueue long-running background loop coroutines."""
        ctx.background.append(_session_cleanup_loop())
        ctx.background.append(_polling_watchdog_loop())
