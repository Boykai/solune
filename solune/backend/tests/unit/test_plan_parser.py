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
        """Phase headings with en dash should be parsed."""
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


# ── Additional parse_plan edge cases ────────────────────────────────────


class TestParsePlanEdgeCases:
    """Additional edge cases for parse_plan."""

    def test_comma_separated_dependencies(self) -> None:
        """Phases with multiple comma-separated dependencies are parsed."""
        plan = """\
## Implementation Phases

### Phase 1 — Base

Foundation work.

### Phase 2 — Mid

Build on base.

### Phase 3 — Final

**Depends on**: Phase 1, Phase 2
"""
        phases = parse_plan(plan)
        assert len(phases) == 3
        assert sorted(phases[2].depends_on_phases) == [1, 2]

    def test_bullet_list_steps(self) -> None:
        """Steps as bullet list items (- or *) are extracted."""
        plan = """\
## Implementation Phases

### Phase 1 — Bullet Steps

Some description.

- Create the database schema
- Implement the API endpoints
* Deploy the service
"""
        phases = parse_plan(plan)
        assert len(phases[0].steps) == 3

    def test_phase_with_only_description(self) -> None:
        """Phase with a description but no explicit steps."""
        plan = """\
## Implementation Phases

### Phase 1 — Simple

This phase just has a description with no step markers.
"""
        phases = parse_plan(plan)
        assert len(phases) == 1
        assert "description" in phases[0].description.lower()
        assert phases[0].steps == []

    def test_self_dependency_raises_circular_error(self) -> None:
        """Phase that depends on itself should raise circular dependency."""
        plan = """\
## Implementation Phases

### Phase 1 — Self Ref

**Depends on**: Phase 1
"""
        with pytest.raises(ValueError, match="Circular dependency detected"):
            parse_plan(plan)

    def test_five_phase_deep_dependency_chain(self) -> None:
        """Linear chain of 5 phases with increasing dependencies."""
        plan = """\
## Implementation Phases

### Phase 1 — A
Base.

### Phase 2 — B
**Depends on**: Phase 1

### Phase 3 — C
**Depends on**: Phase 2

### Phase 4 — D
**Depends on**: Phase 3

### Phase 5 — E
**Depends on**: Phase 4
"""
        phases = parse_plan(plan)
        assert len(phases) == 5
        waves = group_into_waves(phases)
        assert len(waves) == 5
        for i, wave in enumerate(waves):
            assert len(wave) == 1
            assert wave[0].index == i + 1

    def test_phases_without_implementation_header_still_parse(self) -> None:
        """Phases can be parsed even when they appear before ## Implementation Phases."""
        plan = """\
### Phase 1 — Direct

No header above this phase.

**Step 1.1**: Do it
"""
        phases = parse_plan(plan)
        assert len(phases) == 1
        assert phases[0].title == "Direct"

    def test_verification_section_stops_phase_parsing(self) -> None:
        """Parsing stops at ## Verification section."""
        plan = """\
## Implementation Phases

### Phase 1 — Before

**Step 1.1**: Do something

## Verification

### Phase 2 — After Verification

This should NOT be parsed as a phase.
"""
        phases = parse_plan(plan)
        assert len(phases) == 1
        assert phases[0].title == "Before"


# ── Additional group_into_waves edge cases ──────────────────────────────


class TestGroupIntoWavesEdgeCases:
    """Additional edge cases for group_into_waves."""

    def test_unresolvable_phases_raises_error(self) -> None:
        """Phases with unresolvable (non-existent) deps in waves raise error."""
        phases = [
            PlanPhase(index=1, title="A", depends_on_phases=[99]),
        ]
        with pytest.raises(ValueError, match="Cannot resolve wave ordering"):
            group_into_waves(phases)

    def test_large_parallel_wave(self) -> None:
        """Many independent phases all land in wave 1."""
        phases = [PlanPhase(index=i, title=f"P{i}") for i in range(1, 11)]
        waves = group_into_waves(phases)
        assert len(waves) == 1
        assert len(waves[0]) == 10
