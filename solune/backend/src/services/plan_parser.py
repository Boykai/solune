"""Plan.md parser — extracts implementation phases from plan documents.

Parses ``## Implementation Phases`` sections into structured ``PlanPhase``
objects and groups them into dependency-ordered execution waves.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class PlanPhase:
    """A single implementation phase parsed from a plan.md document."""

    index: int
    title: str
    description: str = ""
    steps: list[str] = field(default_factory=list)
    depends_on_phases: list[int] = field(default_factory=list)
    execution_mode: str = "sequential"  # "sequential" or "parallel"


# Regex patterns
_PHASE_HEADING_RE = re.compile(r"###\s+Phase\s+(\d+)\s*[—–\-]\s*(.+)", re.IGNORECASE)
_DEPENDS_ON_RE = re.compile(r"depends?\s+on\s+phase\s+(\d+)", re.IGNORECASE)
_PARALLEL_WITH_RE = re.compile(r"parallel\s+with\s+phase\s+(\d+)", re.IGNORECASE)
_STEP_PATTERN_RE = re.compile(r"^\*\*Step\s+\d+", re.IGNORECASE)
_NUMBERED_STEP_RE = re.compile(r"^\d+\.\s+")


def parse_plan(plan_md_content: str) -> list[PlanPhase]:
    """Parse a plan.md document and extract implementation phases.

    Locates the ``## Implementation Phases`` section (or falls back to the
    first ``### Phase N`` heading) and extracts each ``### Phase N — Title``
    block into a :class:`PlanPhase`.

    Raises:
        ValueError: If no phases are found or a circular dependency is detected.
    """
    lines = plan_md_content.split("\n")

    # Find the start of the Implementation Phases section
    start_idx = 0
    for i, line in enumerate(lines):
        if re.match(r"^##\s+Implementation\s+Phases", line, re.IGNORECASE):
            start_idx = i + 1
            break

    # Extract phase blocks
    phases: list[PlanPhase] = []
    current_phase: PlanPhase | None = None
    block_lines: list[str] = []

    for line in lines[start_idx:]:
        # Stop at the next top-level section (## but not ###)
        if re.match(r"^##\s+[^#]", line) and not re.match(r"^###", line):
            if current_phase is not None:
                _finalize_phase(current_phase, block_lines)
                phases.append(current_phase)
            break

        match = _PHASE_HEADING_RE.match(line)
        if match:
            # Save previous phase
            if current_phase is not None:
                _finalize_phase(current_phase, block_lines)
                phases.append(current_phase)

            phase_index = int(match.group(1))
            phase_title = match.group(2).strip()
            current_phase = PlanPhase(index=phase_index, title=phase_title)
            block_lines = []
        elif current_phase is not None:
            block_lines.append(line)

    # Don't forget the last phase
    if current_phase is not None and current_phase not in phases:
        _finalize_phase(current_phase, block_lines)
        phases.append(current_phase)

    if not phases:
        msg = "No implementation phases found in plan.md content"
        raise ValueError(msg)

    # Validate dependencies
    phase_indices = {p.index for p in phases}
    for phase in phases:
        for dep in phase.depends_on_phases:
            if dep not in phase_indices:
                msg = f"Phase {phase.index} depends on non-existent Phase {dep}"
                raise ValueError(msg)

    # Check for circular dependencies
    _detect_circular_dependencies(phases)

    logger.info("Parsed %d phases from plan.md", len(phases))
    return phases


def _finalize_phase(phase: PlanPhase, block_lines: list[str]) -> None:
    """Extract description, steps, dependencies, and execution mode from block lines."""
    description_parts: list[str] = []
    steps: list[str] = []
    in_description = True

    for line in block_lines:
        stripped = line.strip()
        if not stripped:
            if in_description and description_parts:
                in_description = False
            continue

        # Check for dependency markers
        for dep_match in _DEPENDS_ON_RE.finditer(stripped):
            dep_idx = int(dep_match.group(1))
            if dep_idx not in phase.depends_on_phases:
                phase.depends_on_phases.append(dep_idx)

        # Check for parallel markers
        if _PARALLEL_WITH_RE.search(stripped):
            phase.execution_mode = "parallel"

        # Check for step patterns
        if _STEP_PATTERN_RE.match(stripped) or (
            _NUMBERED_STEP_RE.match(stripped) and not in_description
        ):
            steps.append(stripped)
            in_description = False
        elif stripped.startswith("**Depends on**:") or stripped.startswith("**Depends on:**"):
            # Parse "**Depends on**: Phase 1, Phase 2" or "Nothing"
            dep_text = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            for dep_match in re.finditer(r"Phase\s+(\d+)", dep_text, re.IGNORECASE):
                dep_idx = int(dep_match.group(1))
                if dep_idx not in phase.depends_on_phases:
                    phase.depends_on_phases.append(dep_idx)
            in_description = False
        elif stripped.startswith("- ") or stripped.startswith("* "):
            steps.append(stripped)
            in_description = False
        elif in_description:
            description_parts.append(stripped)

    phase.description = " ".join(description_parts).strip()
    phase.steps = steps


def _detect_circular_dependencies(phases: list[PlanPhase]) -> None:
    """Detect circular dependencies among phases using DFS.

    Raises:
        ValueError: If a cycle is found, with details about the cycle.
    """
    phase_map = {p.index: p for p in phases}
    visited: set[int] = set()
    in_stack: set[int] = set()
    path: list[int] = []

    def dfs(idx: int) -> None:
        if idx in in_stack:
            cycle_start = path.index(idx)
            cycle = path[cycle_start:] + [idx]
            cycle_str = " → ".join(f"Phase {i}" for i in cycle)
            msg = f"Circular dependency detected: {cycle_str}"
            raise ValueError(msg)
        if idx in visited:
            return

        visited.add(idx)
        in_stack.add(idx)
        path.append(idx)

        phase = phase_map.get(idx)
        if phase:
            for dep in phase.depends_on_phases:
                dfs(dep)

        path.pop()
        in_stack.discard(idx)

    for phase in phases:
        dfs(phase.index)


def group_into_waves(phases: list[PlanPhase]) -> list[list[PlanPhase]]:
    """Group phases into execution waves based on dependencies.

    Wave 1 contains phases with no dependencies. Wave N contains phases
    whose dependencies are all satisfied by Waves 1..N-1.

    Returns:
        List of waves, where each wave is a list of phases that can
        execute in parallel.

    Raises:
        ValueError: If phases cannot be fully resolved (circular deps or
            missing references).
    """
    if not phases:
        return []

    phase_map = {p.index: p for p in phases}
    resolved: set[int] = set()
    remaining = list(phases)
    waves: list[list[PlanPhase]] = []

    while remaining:
        wave: list[PlanPhase] = []
        for phase in remaining:
            deps_met = all(d in resolved for d in phase.depends_on_phases)
            if deps_met:
                wave.append(phase)

        if not wave:
            unresolved = [f"Phase {p.index}" for p in remaining]
            msg = f"Cannot resolve wave ordering for: {', '.join(unresolved)}"
            raise ValueError(msg)

        waves.append(wave)
        for phase in wave:
            resolved.add(phase.index)
        remaining = [p for p in remaining if p.index not in resolved]

    logger.info("Grouped %d phases into %d waves", len(phases), len(waves))
    return waves
