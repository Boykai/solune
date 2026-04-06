"""Unit tests for plan_parser — parse_plan(), group_into_waves(), and edge cases."""

from __future__ import annotations

import pytest

from src.services.plan_parser import PlanPhase, group_into_waves, parse_plan

# ── Sample plan.md content ──────────────────────────────────────────────


VALID_PLAN_MD = """\
# Implementation Plan: Test App

## Summary

This is a test plan.

## Implementation Phases

### Phase 1 — Foundation Setup

**Depends on**: Nothing (foundation phase)

**Step 1.1**: Create database schema

New file `backend/src/migrations/001_schema.sql`.

**Step 1.2**: Create data models

New file `backend/src/models/user.py`.

### Phase 2 — Core Backend

**Depends on**: Phase 1

**Step 2.1**: Implement user service

**Step 2.2**: Implement auth service

### Phase 3 — Frontend

**Depends on**: Phase 1

Frontend work running alongside backend.

**Step 3.1**: Create React components

### Phase 4 — Integration

**Depends on**: Phase 2, Phase 3

**Step 4.1**: Wire frontend to backend

## Verification

Some verification steps here.
"""

SINGLE_PHASE_PLAN = """\
## Implementation Phases

### Phase 1 — Only Phase

The sole implementation phase.

**Step 1.1**: Do everything
"""

PARALLEL_PLAN = """\
## Implementation Phases

### Phase 1 — Task A

No dependencies.

### Phase 2 — Task B

This phase is parallel with Phase 1.

### Phase 3 — Combined

**Depends on**: Phase 1, Phase 2
"""

NO_PHASES_PLAN = """\
## Implementation Phases

Just some text with no phase headings.
"""

CIRCULAR_DEPS_PLAN = """\
## Implementation Phases

### Phase 1 — First

**Depends on**: Phase 2

### Phase 2 — Second

**Depends on**: Phase 1
"""


# ── Tests for parse_plan() ──────────────────────────────────────────────


class TestParsePlan:
    """Tests for the parse_plan function."""

    def test_valid_plan_extracts_all_phases(self) -> None:
        phases = parse_plan(VALID_PLAN_MD)
        assert len(phases) == 4

    def test_phase_indices_are_correct(self) -> None:
        phases = parse_plan(VALID_PLAN_MD)
        assert [p.index for p in phases] == [1, 2, 3, 4]

    def test_phase_titles_are_correct(self) -> None:
        phases = parse_plan(VALID_PLAN_MD)
        assert phases[0].title == "Foundation Setup"
        assert phases[1].title == "Core Backend"
        assert phases[2].title == "Frontend"
        assert phases[3].title == "Integration"

    def test_dependency_detection(self) -> None:
        phases = parse_plan(VALID_PLAN_MD)
        assert phases[0].depends_on_phases == []  # No deps
        assert phases[1].depends_on_phases == [1]  # Depends on Phase 1
        assert phases[2].depends_on_phases == [1]  # Depends on Phase 1
        assert sorted(phases[3].depends_on_phases) == [2, 3]  # Depends on Phase 2, 3

    def test_steps_extracted(self) -> None:
        phases = parse_plan(VALID_PLAN_MD)
        # Phase 1 should have steps
        assert len(phases[0].steps) >= 2

    def test_description_extracted(self) -> None:
        phases = parse_plan(VALID_PLAN_MD)
        # Phase 3 has a description line
        assert "frontend" in phases[2].description.lower() or len(phases[2].steps) > 0

    def test_parallel_detection(self) -> None:
        phases = parse_plan(PARALLEL_PLAN)
        # Phase 2 mentions "parallel with Phase 1"
        assert phases[1].execution_mode == "parallel"

    def test_single_phase(self) -> None:
        phases = parse_plan(SINGLE_PHASE_PLAN)
        assert len(phases) == 1
        assert phases[0].index == 1
        assert phases[0].title == "Only Phase"
        assert phases[0].depends_on_phases == []

    def test_no_phases_raises_error(self) -> None:
        with pytest.raises(ValueError, match="No implementation phases found"):
            parse_plan(NO_PHASES_PLAN)

    def test_empty_content_raises_error(self) -> None:
        with pytest.raises(ValueError, match="No implementation phases found"):
            parse_plan("")

    def test_circular_dependency_raises_error(self) -> None:
        with pytest.raises(ValueError, match="Circular dependency detected"):
            parse_plan(CIRCULAR_DEPS_PLAN)

    def test_invalid_dependency_reference_raises_error(self) -> None:
        plan = """\
## Implementation Phases

### Phase 1 — First

**Depends on**: Phase 99
"""
        with pytest.raises(ValueError, match="depends on non-existent Phase 99"):
            parse_plan(plan)

    def test_em_dash_in_heading(self) -> None:
        """Phase headings with em dash (—) should be parsed."""
        plan = """\
## Implementation Phases

### Phase 1 \u2014 Em Dash Title

Some description.
"""
        phases = parse_plan(plan)
        assert len(phases) == 1
        assert phases[0].title == "Em Dash Title"

    def test_en_dash_in_heading(self) -> None:
        """Phase headings with en dash (–) should be parsed."""
        plan = """\
## Implementation Phases

### Phase 1 \u2013 En Dash Title

Some description.
"""
        phases = parse_plan(plan)
        assert len(phases) == 1
        assert phases[0].title == "En Dash Title"

    def test_hyphen_in_heading(self) -> None:
        """Phase headings with regular hyphen (-) should be parsed."""
        plan = """\
## Implementation Phases

### Phase 1 - Hyphen Title

Some description.
"""
        phases = parse_plan(plan)
        assert len(phases) == 1
        assert phases[0].title == "Hyphen Title"


# ── Tests for group_into_waves() ────────────────────────────────────────


class TestGroupIntoWaves:
    """Tests for the group_into_waves function."""

    def test_basic_wave_grouping(self) -> None:
        phases = parse_plan(VALID_PLAN_MD)
        waves = group_into_waves(phases)

        # Wave 1: Phase 1 (no deps)
        # Wave 2: Phase 2, Phase 3 (both depend on Phase 1)
        # Wave 3: Phase 4 (depends on Phase 2, Phase 3)
        assert len(waves) == 3
        assert [p.index for p in waves[0]] == [1]
        assert sorted(p.index for p in waves[1]) == [2, 3]
        assert [p.index for p in waves[2]] == [4]

    def test_single_wave_no_deps(self) -> None:
        """All phases with no dependencies should be in a single wave."""
        phases = [
            PlanPhase(index=1, title="A"),
            PlanPhase(index=2, title="B"),
            PlanPhase(index=3, title="C"),
        ]
        waves = group_into_waves(phases)
        assert len(waves) == 1
        assert len(waves[0]) == 3

    def test_sequential_phases(self) -> None:
        """Chain of dependencies produces one phase per wave."""
        phases = [
            PlanPhase(index=1, title="A"),
            PlanPhase(index=2, title="B", depends_on_phases=[1]),
            PlanPhase(index=3, title="C", depends_on_phases=[2]),
        ]
        waves = group_into_waves(phases)
        assert len(waves) == 3
        assert waves[0][0].index == 1
        assert waves[1][0].index == 2
        assert waves[2][0].index == 3

    def test_empty_phases(self) -> None:
        waves = group_into_waves([])
        assert waves == []

    def test_complex_dependency_graph(self) -> None:
        """Test a diamond dependency pattern."""
        phases = [
            PlanPhase(index=1, title="Root"),
            PlanPhase(index=2, title="Left", depends_on_phases=[1]),
            PlanPhase(index=3, title="Right", depends_on_phases=[1]),
            PlanPhase(index=4, title="Join", depends_on_phases=[2, 3]),
            PlanPhase(index=5, title="Final", depends_on_phases=[4]),
        ]
        waves = group_into_waves(phases)
        assert len(waves) == 4
        assert [p.index for p in waves[0]] == [1]
        assert sorted(p.index for p in waves[1]) == [2, 3]
        assert [p.index for p in waves[2]] == [4]
        assert [p.index for p in waves[3]] == [5]


# ── Tests for PlanPhase dataclass ───────────────────────────────────────


class TestPlanPhase:
    """Tests for the PlanPhase dataclass."""

    def test_default_values(self) -> None:
        phase = PlanPhase(index=1, title="Test")
        assert phase.description == ""
        assert phase.steps == []
        assert phase.depends_on_phases == []
        assert phase.execution_mode == "sequential"

    def test_with_all_fields(self) -> None:
        phase = PlanPhase(
            index=2,
            title="Core",
            description="Core implementation",
            steps=["Step 1", "Step 2"],
            depends_on_phases=[1],
            execution_mode="parallel",
        )
        assert phase.index == 2
        assert phase.title == "Core"
        assert phase.description == "Core implementation"
        assert len(phase.steps) == 2
        assert phase.depends_on_phases == [1]
        assert phase.execution_mode == "parallel"


# ── Additional edge cases for parse_plan() ──────────────────────────────


BULLET_LIST_STEPS_PLAN = """\
## Implementation Phases

### Phase 1 — Setup

Base setup phase.

- Install dependencies
- Configure database
- Set up CI pipeline

### Phase 2 — Feature

**Depends on**: Phase 1

- Implement feature A
- Implement feature B
"""

MULTIPLE_DEPS_PLAN = """\
## Implementation Phases

### Phase 1 — DB Layer

Step 1: Create schema

### Phase 2 — API Layer

**Depends on**: Phase 1

Step 2: Build API

### Phase 3 — UI Layer

**Depends on**: Phase 1

Step 3: Build UI

### Phase 4 — Integration

**Depends on**: Phase 2, Phase 3

Step 4: Wire up

### Phase 5 — Polish

**Depends on**: Phase 4

Step 5: Final polish
"""

COLON_VARIANT_DEPS_PLAN = """\
## Implementation Phases

### Phase 1 — First

Starting phase.

### Phase 2 — Second

**Depends on:** Phase 1

Follow-up phase.
"""


class TestParsePlanEdgeCases:
    """Additional edge cases for parse_plan."""

    def test_bullet_list_steps_extracted(self) -> None:
        """Bullet list items (- foo) should be collected as steps."""
        phases = parse_plan(BULLET_LIST_STEPS_PLAN)
        assert len(phases) == 2
        assert len(phases[0].steps) == 3
        assert any("dependencies" in s.lower() for s in phases[0].steps)

    def test_multiple_dependencies_chain(self) -> None:
        """Five-phase chain with fan-out and fan-in dependencies."""
        phases = parse_plan(MULTIPLE_DEPS_PLAN)
        assert len(phases) == 5
        assert phases[0].depends_on_phases == []
        assert phases[1].depends_on_phases == [1]
        assert phases[2].depends_on_phases == [1]
        assert sorted(phases[3].depends_on_phases) == [2, 3]
        assert phases[4].depends_on_phases == [4]

    def test_multiple_deps_wave_grouping(self) -> None:
        """Five-phase fan-out/fan-in produces 4 waves."""
        phases = parse_plan(MULTIPLE_DEPS_PLAN)
        waves = group_into_waves(phases)
        assert len(waves) == 4
        # Wave 1: Phase 1
        assert [p.index for p in waves[0]] == [1]
        # Wave 2: Phase 2, 3 (both depend only on Phase 1)
        assert sorted(p.index for p in waves[1]) == [2, 3]
        # Wave 3: Phase 4 (depends on Phase 2, 3)
        assert [p.index for p in waves[2]] == [4]
        # Wave 4: Phase 5 (depends on Phase 4)
        assert [p.index for p in waves[3]] == [5]

    def test_depends_on_with_colon_variant(self) -> None:
        """'**Depends on:** Phase 1' (colon before closing **) should be parsed."""
        phases = parse_plan(COLON_VARIANT_DEPS_PLAN)
        assert len(phases) == 2
        assert phases[1].depends_on_phases == [1]

    def test_whitespace_only_content_raises(self) -> None:
        """Whitespace-only content has no phases."""
        with pytest.raises(ValueError, match="No implementation phases found"):
            parse_plan("   \n\n  \n")

    def test_phase_without_steps_has_empty_list(self) -> None:
        """A phase with only a description and no steps should have an empty steps list."""
        plan = """\
## Implementation Phases

### Phase 1 — Setup

Just a description with no step patterns.
Another line of description.
"""
        phases = parse_plan(plan)
        assert len(phases) == 1
        assert phases[0].steps == []
        assert "description" in phases[0].description.lower()

    def test_non_sequential_phase_indices(self) -> None:
        """Phase indices don't have to be 1,2,3 — parser preserves original indices."""
        plan = """\
## Implementation Phases

### Phase 3 — Third

First phase listed.

### Phase 7 — Seventh

**Depends on**: Phase 3

Second phase listed.
"""
        phases = parse_plan(plan)
        assert len(phases) == 2
        assert phases[0].index == 3
        assert phases[1].index == 7
        assert phases[1].depends_on_phases == [3]

    def test_self_dependency_is_circular(self) -> None:
        """A phase that depends on itself is a circular dependency."""
        plan = """\
## Implementation Phases

### Phase 1 — Self

**Depends on**: Phase 1
"""
        with pytest.raises(ValueError, match="Circular dependency detected"):
            parse_plan(plan)

    def test_three_phase_circular_dependency(self) -> None:
        """Three-phase cycle: 1→2→3→1."""
        plan = """\
## Implementation Phases

### Phase 1 — A

**Depends on**: Phase 3

### Phase 2 — B

**Depends on**: Phase 1

### Phase 3 — C

**Depends on**: Phase 2
"""
        with pytest.raises(ValueError, match="Circular dependency detected"):
            parse_plan(plan)
