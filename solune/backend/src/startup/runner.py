"""Startup/shutdown runner — iterates step lists with timing, logging, and error handling."""

from __future__ import annotations

import time
from collections.abc import Sequence

from src.logging_utils import get_logger
from src.middleware.request_id import request_id_var
from src.startup.protocol import StartupContext, Step, StepOutcome

logger = get_logger(__name__)


async def run_startup(
    steps: Sequence[Step],
    ctx: StartupContext,
) -> list[StepOutcome]:
    """Execute *steps* sequentially, returning recorded outcomes.

    For each step:
    1. Evaluate ``skip_if`` — if true, record ``skipped`` and continue.
    2. Set ``request_id_var`` to ``startup-{step.name}`` for correlated logs.
    3. Measure wall-clock time around ``await step.run(ctx)``.
    4. On success: log info with step name and duration.
    5. On exception:
       - If ``fatal=True``: log exception and re-raise.
       - If ``fatal=False``: log warning with exc_info, record and continue.

    The outcome list is returned for introspection (e.g. stash on
    ``app.state.startup_report``).
    """
    outcomes: list[StepOutcome] = []
    for step in steps:
        # Optional skip_if predicate
        skip_fn = getattr(step, "skip_if", None)
        if callable(skip_fn) and skip_fn(ctx):
            outcome = StepOutcome(name=step.name, status="skipped", duration_ms=0.0)
            outcomes.append(outcome)
            logger.info(
                "startup step skipped",
                extra={"step": step.name, "status": "skipped"},
            )
            continue

        token = request_id_var.set(f"startup-{step.name}")
        t0 = time.perf_counter()
        try:
            await step.run(ctx)
            duration_ms = (time.perf_counter() - t0) * 1000
            outcome = StepOutcome(name=step.name, status="ok", duration_ms=duration_ms)
            outcomes.append(outcome)
            logger.info(
                "startup step ok",
                extra={"step": step.name, "status": "ok", "duration_ms": round(duration_ms, 2)},
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000
            outcome = StepOutcome(
                name=step.name,
                status="error",
                duration_ms=duration_ms,
                error=str(exc),
            )
            outcomes.append(outcome)
            if step.fatal:
                logger.exception(
                    "startup step FATAL error",
                    extra={
                        "step": step.name,
                        "status": "error",
                        "duration_ms": round(duration_ms, 2),
                    },
                )
                raise
            logger.warning(
                "startup step error (non-fatal): %s",
                exc,
                exc_info=True,
                extra={"step": step.name, "status": "error", "duration_ms": round(duration_ms, 2)},
            )
        finally:
            request_id_var.reset(token)
    return outcomes


async def run_shutdown(
    hooks: Sequence[Step],
    ctx: StartupContext,
) -> list[StepOutcome]:
    """Execute shutdown *hooks* in order (typically LIFO of registration).

    All hooks are treated as ``fatal=False`` — failures are logged but
    never abort the remaining hooks.  Returns outcome list.
    """
    outcomes: list[StepOutcome] = []
    for hook in hooks:
        token = request_id_var.set(f"shutdown-{hook.name}")
        t0 = time.perf_counter()
        try:
            await hook.run(ctx)
            duration_ms = (time.perf_counter() - t0) * 1000
            outcome = StepOutcome(name=hook.name, status="ok", duration_ms=duration_ms)
            outcomes.append(outcome)
            logger.info(
                "shutdown step ok",
                extra={"step": hook.name, "status": "ok", "duration_ms": round(duration_ms, 2)},
            )
        except Exception as exc:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
            duration_ms = (time.perf_counter() - t0) * 1000
            outcome = StepOutcome(
                name=hook.name,
                status="error",
                duration_ms=duration_ms,
                error=str(exc),
            )
            outcomes.append(outcome)
            logger.warning(
                "shutdown step error (non-fatal): %s",
                exc,
                exc_info=True,
                extra={"step": hook.name, "status": "error", "duration_ms": round(duration_ms, 2)},
            )
        finally:
            request_id_var.reset(token)
    return outcomes
