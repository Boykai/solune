"""Heuristic pipeline estimate derived from the number of configured agents.

Provides two pure functions:

* :func:`size_from_hours` — maps estimated hours to an :class:`IssueSize` enum.
* :func:`estimate_from_agent_count` — computes :class:`IssueMetadata` from the
  agent count using the formula ``max(0.5, min(8.0, agent_count * 0.25))``.

All functions are deterministic and side-effect-free (dates are parameterised
for testing).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from math import ceil

from src.logging_utils import get_logger
from src.models.recommendation import IssueMetadata, IssuePriority, IssueSize

logger = get_logger(__name__)

# ── Constants ───────────────────────────────────────────────────────────────

#: Working hours per day — used to convert estimate hours into calendar days.
HOURS_PER_DAY: float = 8.0

#: Default priority assigned when the AI classifier does not detect urgency.
DEFAULT_PRIORITY: IssuePriority = IssuePriority.P2


# ── Pure functions ──────────────────────────────────────────────────────────


def size_from_hours(hours: float) -> IssueSize:
    """Map estimated hours to an :class:`IssueSize` category.

    Thresholds (from the feature specification):

    * ``≤ 0.5``  → **XS**
    * ``0.51-1.0`` → **S**
    * ``1.01-2.0`` → **M**
    * ``2.01-4.0`` → **L**
    * ``> 4.0``  → **XL**
    """
    if hours <= 0.5:
        return IssueSize.XS
    if hours <= 1.0:
        return IssueSize.S
    if hours <= 2.0:
        return IssueSize.M
    if hours <= 4.0:
        return IssueSize.L
    return IssueSize.XL


def estimate_from_agent_count(
    agent_count: int,
    *,
    today: date | None = None,
) -> IssueMetadata:
    """Compute pipeline estimate metadata from the number of configured agents.

    Args:
        agent_count: Number of agents in the pipeline.  Must be ``≥ 1``.
            A count of ``0`` is treated as ``1`` with a warning log.
        today: Override the current date (for deterministic tests).
            Defaults to ``date.today()`` (UTC).

    Returns:
        :class:`IssueMetadata` populated with the heuristic estimate.
    """
    if agent_count < 1:
        logger.warning(
            "agent_count=%d is invalid (< 1); defaulting to 1",
            agent_count,
        )
        agent_count = 1

    estimate_hours = max(0.5, min(8.0, agent_count * 0.25))
    size = size_from_hours(estimate_hours)
    _today = today or datetime.now(UTC).date()
    start_date = _today.isoformat()
    days = max(1, ceil(estimate_hours / HOURS_PER_DAY))
    target_date = (_today + timedelta(days=days)).isoformat()

    logger.info(
        "Pipeline estimate: agents=%d, hours=%.2f, size=%s, priority=%s, start=%s, target=%s",
        agent_count,
        estimate_hours,
        size.value,
        DEFAULT_PRIORITY.value,
        start_date,
        target_date,
    )

    return IssueMetadata(
        priority=DEFAULT_PRIORITY,
        size=size,
        estimate_hours=estimate_hours,
        start_date=start_date,
        target_date=target_date,
    )
