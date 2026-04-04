"""Pipeline orchestrator — sequences speckit agents via SDK sessions.

Drives speckit pipeline stages (plan → specify → tasks → analyze → implement)
through sub-agent sessions, supporting serial and parallel execution groups.
Emits ``stage_started``, ``stage_completed``, and ``stage_failed`` SSE events
for frontend progress tracking.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from src.logging_utils import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Pipeline stage definition
# ---------------------------------------------------------------------------

# Each group runs serially between groups; agents within a group marked
# ``parallel=True`` run concurrently via asyncio.gather().
PIPELINE_STAGES: list[dict[str, Any]] = [
    # Group 1 — speckit core (serial)
    {"name": "plan", "agent": "solune-plan", "group": 1, "parallel": False},
    {"name": "specify", "agent": "solune-specify", "group": 1, "parallel": False},
    {"name": "tasks", "agent": "solune-tasks", "group": 1, "parallel": False},
    {"name": "analyze", "agent": "solune-analyze", "group": 1, "parallel": False},
    {"name": "implement", "agent": "solune-implement", "group": 1, "parallel": False},
    # Group 2 — quality assurance (parallel)
    {"name": "quality-assurance", "agent": "solune-analyze", "group": 2, "parallel": True},
    {"name": "tester", "agent": "solune-analyze", "group": 2, "parallel": True},
    {"name": "copilot-review", "agent": "solune-analyze", "group": 2, "parallel": True},
    # Group 3 — judgment + linting (parallel)
    {"name": "judge", "agent": "solune-analyze", "group": 3, "parallel": True},
    {"name": "linter", "agent": "solune-analyze", "group": 3, "parallel": True},
    # Group 4 — devops (serial)
    {"name": "devops", "agent": "solune-implement", "group": 4, "parallel": False},
]


class StageResult:
    """Result of a single pipeline stage execution."""

    def __init__(self, name: str, success: bool, output: str = "", error: str = ""):
        self.name = name
        self.success = success
        self.output = output
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# SSE event helpers
# ---------------------------------------------------------------------------


def stage_started_event(stage_name: str) -> dict[str, str]:
    """Build a stage_started SSE event."""
    return {
        "event": "stage_started",
        "data": json.dumps({"stage": stage_name}),
    }


def stage_completed_event(stage_name: str, output: str = "") -> dict[str, str]:
    """Build a stage_completed SSE event."""
    return {
        "event": "stage_completed",
        "data": json.dumps({"stage": stage_name, "output": output}),
    }


def stage_failed_event(stage_name: str, error: str = "") -> dict[str, str]:
    """Build a stage_failed SSE event."""
    return {
        "event": "stage_failed",
        "data": json.dumps({"stage": stage_name, "error": error}),
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def _run_stage(
    stage: dict[str, Any],
    context: dict[str, Any],
) -> StageResult:
    """Execute a single pipeline stage.

    In a production setup this would create a Copilot SDK sub-agent session,
    but for now it delegates to a configurable handler or returns a stub.
    """
    stage_name = stage["name"]
    handler = context.get("stage_handlers", {}).get(stage_name)

    if handler is not None:
        try:
            output = await handler(context)
            return StageResult(name=stage_name, success=True, output=str(output))
        except Exception as exc:
            logger.exception("Stage %s failed", stage_name)
            return StageResult(name=stage_name, success=False, error=str(exc))

    # Default: no-op stub for stages without handlers
    return StageResult(name=stage_name, success=True, output=f"{stage_name} completed (stub)")


async def run_pipeline(
    stages: list[dict[str, Any]] | None = None,
    context: dict[str, Any] | None = None,
    event_callback: Any | None = None,
) -> list[StageResult]:
    """Execute the pipeline stages in group order.

    Serial groups run one stage at a time. Parallel groups use
    ``asyncio.gather()`` for concurrent execution.

    Args:
        stages: Pipeline stage definitions (defaults to PIPELINE_STAGES).
        context: Shared context dict passed to each stage handler.
        event_callback: Optional async callable receiving SSE event dicts.

    Returns:
        List of StageResult objects.
    """
    if stages is None:
        stages = PIPELINE_STAGES
    if context is None:
        context = {}

    # Group stages by group number
    groups: dict[int, list[dict[str, Any]]] = {}
    for stage in stages:
        g = stage.get("group", 1)
        groups.setdefault(g, []).append(stage)

    results: list[StageResult] = []

    for group_num in sorted(groups.keys()):
        group_stages = groups[group_num]
        has_parallel = any(s.get("parallel", False) for s in group_stages)

        if has_parallel:
            # Run parallel stages concurrently
            async def _run_with_events(s: dict[str, Any]) -> StageResult:
                if event_callback:
                    await event_callback(stage_started_event(s["name"]))
                result = await _run_stage(s, context)
                if event_callback:
                    if result.success:
                        await event_callback(stage_completed_event(s["name"], result.output))
                    else:
                        await event_callback(stage_failed_event(s["name"], result.error))
                return result

            group_results = await asyncio.gather(
                *[_run_with_events(s) for s in group_stages],
                return_exceptions=False,
            )
            results.extend(group_results)

            # Check for failures in parallel group (continue, but log)
            for r in group_results:
                if not r.success:
                    logger.warning("Parallel stage %s failed: %s", r.name, r.error)
        else:
            # Run serial stages one at a time
            for s in group_stages:
                if event_callback:
                    await event_callback(stage_started_event(s["name"]))

                result = await _run_stage(s, context)
                results.append(result)

                if event_callback:
                    if result.success:
                        await event_callback(stage_completed_event(s["name"], result.output))
                    else:
                        await event_callback(stage_failed_event(s["name"], result.error))

                # Halt on serial failure
                if not result.success:
                    logger.error("Serial stage %s failed — halting pipeline", result.name)
                    return results

    return results
