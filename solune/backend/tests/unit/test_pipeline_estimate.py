"""Unit tests for the pipeline estimate heuristic module.

Tests cover:
- size_from_hours: boundary conditions for all size categories
- estimate_from_agent_count: agent counts 0, 1, 2, 3, 4, 5, 8, 9, 16, 17, 20
- Date calculation: start_date = today, target_date = today + ceil(hours/8)
- Edge case: agent_count = 0 treated as 1
"""

from __future__ import annotations

from datetime import date

import pytest

from src.models.recommendation import IssuePriority, IssueSize
from src.services.pipeline_estimate import (
    estimate_from_agent_count,
    size_from_hours,
)

# ── size_from_hours ─────────────────────────────────────────────────────────


class TestSizeFromHours:
    """Boundary tests for the hours-to-size mapping."""

    @pytest.mark.parametrize(
        ("hours", "expected"),
        [
            (0.25, IssueSize.XS),
            (0.5, IssueSize.XS),  # boundary: exactly 0.5
            (0.51, IssueSize.S),
            (1.0, IssueSize.S),  # boundary: exactly 1.0
            (1.01, IssueSize.M),
            (2.0, IssueSize.M),  # boundary: exactly 2.0
            (2.01, IssueSize.L),
            (4.0, IssueSize.L),  # boundary: exactly 4.0
            (4.01, IssueSize.XL),
            (8.0, IssueSize.XL),
        ],
    )
    def test_thresholds(self, hours: float, expected: IssueSize):
        assert size_from_hours(hours) == expected


# ── estimate_from_agent_count ───────────────────────────────────────────────


class TestEstimateFromAgentCount:
    """Tests for the composite heuristic function."""

    FIXED_TODAY = date(2026, 4, 4)

    @pytest.mark.parametrize(
        ("agent_count", "expected_hours", "expected_size"),
        [
            (0, 0.5, IssueSize.XS),  # invalid → clamped to 1 → 0.25 → clamped to 0.5
            (1, 0.5, IssueSize.XS),  # 1 * 0.25 = 0.25 → clamped to 0.5
            (2, 0.5, IssueSize.XS),  # 2 * 0.25 = 0.5
            (3, 0.75, IssueSize.S),  # 3 * 0.25 = 0.75
            (4, 1.0, IssueSize.S),  # 4 * 0.25 = 1.0
            (5, 1.25, IssueSize.M),  # 5 * 0.25 = 1.25
            (8, 2.0, IssueSize.M),  # 8 * 0.25 = 2.0
            (9, 2.25, IssueSize.L),  # 9 * 0.25 = 2.25
            (16, 4.0, IssueSize.L),  # 16 * 0.25 = 4.0
            (17, 4.25, IssueSize.XL),  # 17 * 0.25 = 4.25
            (20, 5.0, IssueSize.XL),  # 20 * 0.25 = 5.0 (clamped to 8.0? no, 5.0 < 8)
        ],
    )
    def test_agent_counts(self, agent_count: int, expected_hours: float, expected_size: IssueSize):
        meta = estimate_from_agent_count(agent_count, today=self.FIXED_TODAY)
        assert meta.estimate_hours == expected_hours
        assert meta.size == expected_size

    def test_priority_is_p2(self):
        meta = estimate_from_agent_count(3, today=self.FIXED_TODAY)
        assert meta.priority == IssuePriority.P2

    def test_start_date_is_today(self):
        meta = estimate_from_agent_count(3, today=self.FIXED_TODAY)
        assert meta.start_date == "2026-04-04"

    def test_target_date_one_day_minimum(self):
        """Even for small estimates (< 8h) the minimum target is today + 1 day."""
        meta = estimate_from_agent_count(1, today=self.FIXED_TODAY)
        assert meta.target_date == "2026-04-05"

    def test_target_date_multi_day(self):
        """32 agents → 8h → ceil(8/8)=1 day → today + 1."""
        meta = estimate_from_agent_count(32, today=self.FIXED_TODAY)
        assert meta.estimate_hours == 8.0  # clamped
        assert meta.target_date == "2026-04-05"

    def test_target_date_large_estimate(self):
        """100 agents → clamped to 8h → ceil(8/8) = 1 day."""
        meta = estimate_from_agent_count(100, today=self.FIXED_TODAY)
        assert meta.estimate_hours == 8.0
        assert meta.target_date == "2026-04-05"

    def test_agent_count_zero_defaults_to_one(self):
        """agent_count=0 is treated as 1 (with a warning)."""
        meta = estimate_from_agent_count(0, today=self.FIXED_TODAY)
        assert meta.estimate_hours == 0.5
        assert meta.size == IssueSize.XS

    def test_negative_agent_count_defaults_to_one(self):
        """Negative agent counts are treated as 1."""
        meta = estimate_from_agent_count(-5, today=self.FIXED_TODAY)
        assert meta.estimate_hours == 0.5
