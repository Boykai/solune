"""run_startup and run_shutdown implementations."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence

from src.logging_utils import get_logger
from src.middleware.request_id import request_id_var
from src.startup.protocol import StartupContext, StartupError, Step, StepOutcome

logger = get_logger(__name__)


async def run_startup(
    steps: Sequence[Step],
    ctx: StartupContext,
) -> list[StepOutcome]:
    """Execute startup steps in order, returning one StepOutcome per step.

    Raises StartupError (with __cause__) when a fatal step fails.
    On fatal failure, partial outcomes are stored on ctx.app.state.startup_report
    before raising.
    """
    # Validate unique names
    names = [s.name for s in steps]
    if len(names) != len(set(names)):
        seen: set[str] = set()
        dupes: list[str] = []
        for n in names:
            if n in seen:
                dupes.append(n)
            seen.add(n)
        raise ValueError(f"Duplicate step names: {dupes}")

    results: list[StepOutcome] = []

    for step in steps:
        token = request_id_var.set(f"startup-{step.name}")
        start = time.perf_counter()
        outcome: StepOutcome
        try:
            if hasattr(step, "skip_if") and step.skip_if(ctx):  # type: ignore[union-attr] — reason: guarded by hasattr; Protocol does not mandate skip_if
                duration_ms = (time.perf_counter() - start) * 1000
                outcome = StepOutcome(step.name, "skipped", duration_ms, None)
                logger.info(
                    "Startup step skipped",
                    extra={"step": step.name, "status": "skipped", "duration_ms": duration_ms},
                )
            else:
                await step.run(ctx)
                duration_ms = (time.perf_counter() - start) * 1000
                outcome = StepOutcome(step.name, "ok", duration_ms, None)
                logger.info(
                    "Startup step ok",
                    extra={"step": step.name, "status": "ok", "duration_ms": duration_ms},
                )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            outcome = StepOutcome(step.name, "failed", duration_ms, str(exc))
            if step.fatal:
                logger.error(
                    "Fatal startup step failed: %s",
                    step.name,
                    exc_info=True,
                    extra={"step": step.name, "status": "failed", "duration_ms": duration_ms},
                )
                results.append(outcome)
                ctx.app.state.startup_report = results
                raise StartupError(step.name) from exc
            else:
                logger.warning(
                    "Non-fatal startup step failed: %s",
                    step.name,
                    exc_info=True,
                    extra={"step": step.name, "status": "failed", "duration_ms": duration_ms},
                )
        finally:
            request_id_var.reset(token)

        results.append(outcome)

    ctx.app.state.startup_report = results
    return results


async def run_shutdown(
    ctx: StartupContext,
    *,
    shutdown_timeout: float = 30.0,
) -> list[StepOutcome]:
    """Execute shutdown hooks in LIFO order then run built-in trailing hooks.

    Never raises — all exceptions are caught and logged.
    """
    results: list[StepOutcome] = []

    # User-registered hooks in LIFO order
    for i, hook in enumerate(reversed(ctx.shutdown_hooks)):
        hook_name = f"shutdown-{len(ctx.shutdown_hooks) - 1 - i}"
        start = time.perf_counter()
        try:
            await asyncio.wait_for(hook(), timeout=shutdown_timeout)
            duration_ms = (time.perf_counter() - start) * 1000
            outcome = StepOutcome(hook_name, "ok", duration_ms, None)
            logger.info(
                "Shutdown hook ok",
                extra={"step": hook_name, "status": "ok", "duration_ms": duration_ms},
            )
        except (TimeoutError, asyncio.CancelledError, Exception) as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            error_message = (
                f"timed out after {shutdown_timeout}s"
                if isinstance(exc, TimeoutError)
                else str(exc)
            )
            outcome = StepOutcome(hook_name, "failed", duration_ms, error_message)
            logger.warning(
                "Shutdown hook failed: %s — %s",
                hook_name,
                error_message,
                exc_info=True,
                extra={"step": hook_name, "status": "failed", "duration_ms": duration_ms},
            )
        results.append(outcome)

    # ── Trailing hooks (always run) ──

    # 1. Drain task registry
    start = time.perf_counter()
    try:
        await ctx.task_registry.drain(drain_timeout=shutdown_timeout)
        duration_ms = (time.perf_counter() - start) * 1000
        results.append(StepOutcome("shutdown-drain", "ok", duration_ms, None))
    except (asyncio.CancelledError, Exception) as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        results.append(StepOutcome("shutdown-drain", "failed", duration_ms, str(exc)))
        logger.warning("shutdown-drain failed: %s", exc, exc_info=True)

    # 2. Stop Copilot polling if running
    start = time.perf_counter()
    try:
        from src.services.copilot_polling import get_polling_status, stop_polling

        if get_polling_status()["is_running"]:
            await stop_polling()
        duration_ms = (time.perf_counter() - start) * 1000
        results.append(StepOutcome("shutdown-stop-polling", "ok", duration_ms, None))
    except (asyncio.CancelledError, Exception) as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        results.append(StepOutcome("shutdown-stop-polling", "failed", duration_ms, str(exc)))
        logger.warning("shutdown-stop-polling failed: %s", exc, exc_info=True)

    # 3. Close database (unconditional — close_database() is a no-op when
    #    _connection is None, and gating on ctx.db can miss the module-level
    #    connection when init_database() succeeded but the step failed before
    #    assigning ctx.db)
    start = time.perf_counter()
    try:
        from src.services.database import close_database

        await close_database()
        duration_ms = (time.perf_counter() - start) * 1000
        results.append(StepOutcome("shutdown-close-db", "ok", duration_ms, None))
    except (asyncio.CancelledError, Exception) as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        results.append(StepOutcome("shutdown-close-db", "failed", duration_ms, str(exc)))
        logger.warning("shutdown-close-db failed: %s", exc, exc_info=True)

    return results
