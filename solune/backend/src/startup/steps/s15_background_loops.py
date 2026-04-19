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
        get_monitored_projects,
        get_polling_status,
        unregister_project,
    )
    from src.services.pipeline_state_store import (
        count_active_pipelines_for_project,
        get_queued_pipelines_for_project,
    )
    from src.startup.steps.s11_copilot_polling import (
        auto_start_copilot_polling,
    )
    from src.startup.steps.s12_multi_project import (
        discover_and_register_active_projects,
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
                    from src.config import get_settings

                    await auto_start_copilot_polling(get_settings())
                    if get_polling_status()["is_running"]:
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
            try:
                from src.config import get_settings

                _registered = await discover_and_register_active_projects(get_settings())
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
            except Exception as e:  # noqa: BLE001 — reason: polling resilience; failure logged, polling loop continues
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
