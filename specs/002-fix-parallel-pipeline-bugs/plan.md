# Implementation Plan: Fix Parallel Pipeline Execution Bugs

**Branch**: `002-fix-parallel-pipeline-bugs` | **Date**: 2026-03-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-fix-parallel-pipeline-bugs/spec.md`

## Summary

Parallel pipeline groups execute agents one-at-a-time instead of simultaneously because `_process_pipeline_completion` only checks a single `current_agent` per 60-second poll cycle — and for parallel groups, `current_agent` always returns agent[0]. This plan adds a `current_agents` (plural) property to `PipelineState` that returns ALL agents in the current group when `execution_mode == "parallel"`, fixes the `is_complete` property for sequential groups, and updates the polling loop and recovery path to iterate over all parallel agents per cycle.

## Technical Context

**Language/Version**: Python 3.13 (PEP 695 type parameter syntax enforced by ruff UP046/UP047)
**Primary Dependencies**: FastAPI, Pydantic, aiosqlite, pytest + pytest-asyncio
**Storage**: SQLite via aiosqlite (no schema changes needed)
**Testing**: pytest + pytest-asyncio (unit tests in `tests/unit/`, property tests in `tests/property/`)
**Target Platform**: Linux server (Docker)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: Parallel group of N agents achieves ~1x slowest agent duration (not N× sequential sum)
**Constraints**: Polling cycle is 60 seconds; initial parallel dispatch uses intentional 2-second stagger for rate-limit protection; recovery path must not re-assign already-active agents
**Scale/Scope**: 2 source files modified (`models.py`, `pipeline.py`); 0 new files; ~30-50 lines changed; 2 test files extended

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | `spec.md` exists with 3 prioritized user stories (P1-P2), Given-When-Then scenarios, edge cases, and clear scope boundaries |
| II. Template-Driven | ✅ PASS | All artifacts follow canonical templates from `.specify/templates/` |
| III. Agent-Orchestrated | ✅ PASS | Single-responsibility: this plan phase produces design artifacts; implementation deferred to `/speckit.tasks` + `/speckit.implement` |
| IV. Test Optionality | ✅ PASS | Tests explicitly called for in `spec.md`; property tests for model invariants; regression suite required |
| V. Simplicity and DRY | ✅ PASS | Adds a new `current_agents` property rather than changing `current_agent` return type (used in 20+ places). Minimal surgical changes — no new abstractions, no new files, no new dependencies |

**Gate Result**: ALL PASS — proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/002-fix-parallel-pipeline-bugs/
├── plan.md              # This file
├── research.md          # Phase 0: Research findings
├── data-model.md        # Phase 1: Entity and data model
├── quickstart.md        # Phase 1: Developer quickstart guide
├── contracts/           # Phase 1: Internal service contracts
│   └── pipeline-state.yaml  # PipelineState property contracts
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   └── services/
│       ├── workflow_orchestrator/
│       │   └── models.py              # MODIFY: Add current_agents property; fix is_complete for sequential groups
│       └── copilot_polling/
│           └── pipeline.py            # MODIFY: Use current_agents in polling loop and recovery path
└── tests/
    ├── unit/
    │   ├── test_models.py             # EXTEND: Tests for current_agents property and sequential is_complete
    │   └── test_copilot_polling.py    # EXTEND: Tests for parallel polling loop and recovery
    └── property/
        └── test_pipeline_state_machine.py  # VERIFY: Existing property invariants hold
```

**Structure Decision**: Web application structure. All changes are backend-only within `solune/backend/`. No new files are created — only existing files are modified or extended. The `orchestrator.py` file (initial parallel dispatch + stagger) requires NO changes.

## Constitution Re-Check (Post-Design)

*Re-evaluation after Phase 1 design artifacts are complete.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | All design artifacts trace back to spec.md requirements (FR-001 through FR-010) |
| II. Template-Driven | ✅ PASS | All generated artifacts follow canonical templates |
| III. Agent-Orchestrated | ✅ PASS | Plan phase complete; handoff to `/speckit.tasks` for task decomposition |
| IV. Test Optionality | ✅ PASS | Tests explicitly mandated by spec — included in plan with concrete verification commands |
| V. Simplicity and DRY | ✅ PASS | No new files, no new abstractions, no new dependencies. `current_agents` is the only new public interface; all other changes are internal to existing methods |

**Gate Result**: ALL PASS — ready for Phase 2 (`/speckit.tasks`).

## Complexity Tracking

> No constitution violations — this section is intentionally empty.
