# Implementation Plan: Fix Parallel Pipeline Execution Bugs

**Branch**: `001-fix-parallel-pipeline` | **Date**: 2026-03-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-fix-parallel-pipeline/spec.md`

## Summary

Parallel pipeline groups execute agents one-at-a-time instead of simultaneously because the polling loop (`_process_pipeline_completion`) only checks a single `current_agent` per 60-second cycle — and for parallel groups, `current_agent` always returns `agents[0]`. Additionally, sequential group completion (`is_complete`) unconditionally returns `False`, causing pipelines to stall after the last sequential agent finishes. The fix adds a new `current_agents` (plural) list property to `PipelineState`, fixes `is_complete` for sequential groups, updates the polling loop to iterate over all parallel agents per cycle, and fixes the recovery path to re-dispatch all unassigned parallel agents after state reconstruction.

## Technical Context

**Language/Version**: Python ≥3.12 (targets 3.13, runs 3.14-slim in Docker)
**Primary Dependencies**: FastAPI, Pydantic, dataclasses (stdlib)
**Storage**: In-memory `PipelineState` dataclass (pipeline_state_store.py), no DB migration needed
**Testing**: pytest (unit tests in `tests/unit/`, property tests in `tests/property/`)
**Target Platform**: Linux server (Docker container)
**Project Type**: Web application (backend-only changes for this feature)
**Performance Goals**: Polling loop must complete within a single 60-second cycle for groups of up to 10 agents
**Constraints**: No breaking changes to the existing `current_agent` property (used in 20+ call sites); backward-compatible
**Scale/Scope**: 3 files modified (`models.py`, `pipeline.py`), ~40 lines changed, ~80 lines of new tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First Development | ✅ Pass | `spec.md` complete with 3 prioritized user stories, Given-When-Then scenarios, and edge cases |
| II. Template-Driven Workflow | ✅ Pass | All artifacts follow canonical templates |
| III. Agent-Orchestrated Execution | ✅ Pass | Single-purpose plan agent; handoff to `/speckit.tasks` for Phase 2 |
| IV. Test Optionality with Clarity | ✅ Pass | Tests explicitly required by parent issue spec (Phase 3); included in plan |
| V. Simplicity and DRY | ✅ Pass | Additive change (new `current_agents` property) avoids modifying 20+ existing call sites; no new abstractions |

**Post-Phase 1 Re-check**: ✅ All gates still pass. Design adds no new complexity — the data model change is a single list-returning property and the polling loop change is a `for` loop replacement. No constitution violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-fix-parallel-pipeline/
├── plan.md              # This file
├── research.md          # Phase 0 output — design decisions & alternatives
├── data-model.md        # Phase 1 output — PipelineState entity changes
├── quickstart.md        # Phase 1 output — verification guide
├── contracts/           # Phase 1 output — internal API contracts
│   └── pipeline-state-api.md
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   └── services/
│       ├── workflow_orchestrator/
│       │   └── models.py          # PipelineState: add current_agents, fix is_complete
│       └── copilot_polling/
│           └── pipeline.py        # _process_pipeline_completion: parallel-aware loop + recovery fix
└── tests/
    ├── unit/
    │   ├── test_models.py             # New tests for current_agents + sequential is_complete
    │   └── test_copilot_polling.py    # New test for parallel polling loop
    └── property/
        └── test_pipeline_state_machine.py  # Run for regression (no changes)
```

**Structure Decision**: Web application (backend-only). All changes are in `solune/backend/` — no frontend changes needed. The bug is entirely in the backend pipeline execution layer.

## Phases

### Phase 1: Model Layer Fixes (models.py)

**Step 1** — Add `current_agents` property to `PipelineState`

- Location: `solune/backend/src/services/workflow_orchestrator/models.py`, after `current_agent` property (L193)
- Returns `list[str]`: ALL agents in the current group when `execution_mode == "parallel"`, falls back to `[current_agent]` for sequential groups
- Filters out agents already in terminal state (`completed`, `failed`) from the returned list so the polling loop only processes active/pending agents
- Preserves existing `current_agent` property unchanged (20+ call sites depend on it)
- Maps to: FR-001

**Step 2** — Fix `is_complete` for sequential groups

- Location: `solune/backend/src/services/workflow_orchestrator/models.py`, L211
- Current bug: sequential groups unconditionally `return False`
- Fix: check `current_agent_index_in_group >= len(group.agents)` before returning False
- Maps to: FR-004

### Phase 2: Polling Loop Fixes (pipeline.py)

**Step 3** — Fix `_process_pipeline_completion` to check ALL parallel agents (depends on Step 1)

- Location: `solune/backend/src/services/copilot_polling/pipeline.py`, L671-696
- Replace single `current_agent` completion check with a loop over `pipeline.current_agents`
- For each non-completed agent, call `_check_agent_done_on_sub_or_parent`
- If any agent completes, call `_advance_pipeline` for it
- Existing `_advance_pipeline` already handles parallel groups correctly (marks individual agents done, advances group index only when all are terminal)
- Maps to: FR-002, FR-003, FR-008

**Step 4** — Fix "agent never assigned" recovery path (depends on Step 1, parallel with Step 3)

- Location: `solune/backend/src/services/copilot_polling/pipeline.py`, L698-806
- Recovery logic uses `current_agent` (singular) — for parallel groups after reconstruction, ALL unassigned agents need reassignment
- Use `pipeline.current_agents` to iterate over all agents needing recovery
- Maps to: FR-005

### Phase 3: Tests (depends on Steps 1-4)

**Step 5** — Test `current_agents` property: parallel returns all agents, sequential returns single

**Step 6** — Test `is_complete` for sequential group after advancement

**Step 7** — Test `_process_pipeline_completion` checks all parallel agents per cycle

**Step 8** — Run full existing suite for regressions

### Verification Commands

```bash
# Model property fixes
pytest tests/unit/test_models.py -v -k "complete or current_agent"

# Polling loop fix
pytest tests/unit/test_copilot_polling.py -v -k "parallel"

# Property invariants hold
pytest tests/property/test_pipeline_state_machine.py -v

# Full suite — no regressions
pytest tests/unit/ tests/property/
```

## Decisions

| Decision | Rationale |
|----------|-----------|
| Add new `current_agents` list property rather than changing `current_agent` return type | `current_agent` is used in 20+ places for sequential logic; changing its signature would be high-risk |
| Initial launch stagger (`asyncio.sleep(2)`) in `execute_full_workflow` is NOT a bug | Intentional rate-limit protection; out of scope |
| `_advance_pipeline` parallel logic is already correct | Marks individual agents done, advances group index only when all terminal — no changes needed |
| Scope excludes `determine_next_action` in `agent_tracking.py` | Separate lower-priority recovery path |
| Filter terminal agents from `current_agents` return value | Polling loop should only process agents that haven't finished; prevents redundant completion checks |

## Complexity Tracking

> No constitution violations detected. No complexity justifications required.
