# Tasks: Fix Parallel Pipeline Execution Bugs

**Input**: Design documents from `/specs/002-fix-parallel-pipeline-bugs/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — explicitly requested in the feature specification (spec.md Phase 3, Constitution Check IV).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Project type**: Web application (backend + frontend monorepo under `solune/`)
- **Backend source**: `solune/backend/src/`
- **Backend tests**: `solune/backend/tests/`
- **Modified source files**: `solune/backend/src/services/workflow_orchestrator/models.py`, `solune/backend/src/services/copilot_polling/pipeline.py`
- **Extended test files**: `solune/backend/tests/unit/test_models.py`, `solune/backend/tests/unit/test_copilot_polling.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No project initialization or new dependencies needed — this is a surgical fix to an existing codebase (2 source files modified, 0 new files, 2 test files extended).

> **SKIP**: All infrastructure exists. Proceed directly to Phase 2.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add the `current_agents` (plural) property to `PipelineState` — the new parallel-aware interface that the polling loop (US1) and recovery path (US3) both depend on.

**⚠️ CRITICAL**: US1 and US3 cannot begin until `current_agents` property is implemented and tested.

- [ ] T001 Add `current_agents` property to `PipelineState` class in `solune/backend/src/services/workflow_orchestrator/models.py`. Insert after existing `current_agent` property (~line 193). For grouped pipelines with `execution_mode == "parallel"`: return all agents in the current group. For `execution_mode == "sequential"`: return single-element list with the agent at `current_agent_index_in_group`. Skip empty groups (while-loop advancing `idx`). For non-grouped pipelines (no `self.groups`): fall back to `[self.current_agent]` if not None, else `[]`. Return type: `list[str]`. See `contracts/pipeline-state.yaml` for full behavioral contract and `quickstart.md` Change A for reference implementation.
- [ ] T002 [P] Add test `test_current_agents_parallel_returns_all` in `solune/backend/tests/unit/test_models.py`. Create a `PipelineState` with a parallel group containing 3 agents (`["linter", "archivist", "judge"]`). Assert `current_agents` returns all 3 agents. Place near existing group tests (~line 348-450).
- [ ] T003 [P] Add test `test_current_agents_sequential_returns_single` in `solune/backend/tests/unit/test_models.py`. Create a `PipelineState` with a sequential group containing 3 agents and `current_agent_index_in_group = 1`. Assert `current_agents` returns `["plan"]` (single-element list with agent at index 1).
- [ ] T004 [P] Add test `test_current_agents_empty_group_skipped` in `solune/backend/tests/unit/test_models.py`. Create a `PipelineState` where the current group has an empty agents list, followed by a non-empty group. Assert `current_agents` skips the empty group and returns agents from the next non-empty group.
- [ ] T005 [P] Add test `test_current_agents_flat_fallback` in `solune/backend/tests/unit/test_models.py`. Create a `PipelineState` with no groups configured (flat agent list). Assert `current_agents` returns `[current_agent]` as a single-element list.

**Checkpoint**: `current_agents` property ready — `pytest tests/unit/test_models.py -v -k "current_agents"` passes. US1 and US3 can now proceed.

---

## Phase 3: User Story 1 — Parallel Agents Execute Simultaneously (Priority: P1) 🎯 MVP

**Goal**: Fix the polling loop so that ALL agents in a parallel group are checked for completion during each 60-second poll cycle, not just agent[0]. This is the core defect — parallel groups currently behave identically to sequential groups.

**Independent Test**: Trigger a pipeline with a 3-agent parallel group and verify all 3 agents are checked for completion in the same polling cycle. Each completed agent is advanced individually; the group advances only when all agents reach a terminal state.

### Tests for User Story 1

- [ ] T006 [US1] Add test `test_process_pipeline_completion_checks_all_parallel_agents` in `solune/backend/tests/unit/test_copilot_polling.py`. Create a pipeline with a parallel group of 3 agents. Mock `_check_agent_done_on_sub_or_parent` to return `True` for agent 2 only. Verify that the mock is called once for each of the 3 non-completed agents in a single polling cycle. Verify `_advance_pipeline` is called exactly once (for agent 2 only). Place near existing parallel tests (~line 3187-3449).

### Implementation for User Story 1

- [ ] T007 [US1] Fix `_process_pipeline_completion` polling loop in `solune/backend/src/services/copilot_polling/pipeline.py` (~line 680). Replace the single `current_agent` completion check with a `for agent in pipeline.current_agents:` loop. For each agent not in `completed_agents` or `failed_agents`, call `_check_agent_done_on_sub_or_parent`. If any agent completes, call `_advance_pipeline` for it. The existing `_advance_pipeline` already handles parallel groups correctly (marks individual agents done, advances group index only when all are terminal). See `quickstart.md` Change C for before/after reference.

**Checkpoint**: Parallel polling fixed — `pytest tests/unit/test_copilot_polling.py -v -k "parallel"` passes. A parallel group of N agents now achieves ~1x slowest agent duration instead of N× sequential sum.

---

## Phase 4: User Story 2 — Sequential Group Completion Detection (Priority: P1)

**Goal**: Fix the `is_complete` property so sequential groups correctly report completion when all agents have been processed, instead of unconditionally returning `False`.

**Independent Test**: Create a pipeline with a sequential group of 2 agents, advance `current_agent_index_in_group` past both agents, and verify `is_complete` returns `True`. Verify it returns `False` when agents remain.

### Tests for User Story 2

- [ ] T008 [P] [US2] Add test `test_is_complete_sequential_group_done` in `solune/backend/tests/unit/test_models.py`. Create a `PipelineState` with a sequential group of 2 agents and set `current_agent_index_in_group = 2` (past end). Assert `is_complete` returns `True`.
- [ ] T009 [P] [US2] Add test `test_is_complete_sequential_group_not_done` in `solune/backend/tests/unit/test_models.py`. Create a `PipelineState` with a sequential group of 3 agents and set `current_agent_index_in_group = 1` (agents remain). Assert `is_complete` returns `False`.

### Implementation for User Story 2

- [ ] T010 [US2] Fix `is_complete` property in `PipelineState` in `solune/backend/src/services/workflow_orchestrator/models.py` (~line 217). In the sequential group branch, replace the unconditional `return False` with `return self.current_agent_index_in_group >= len(group.agents)`. This checks whether the agent index has advanced past all agents in the group. See `quickstart.md` Change B for before/after reference.

**Checkpoint**: Sequential completion fixed — `pytest tests/unit/test_models.py -v -k "complete"` passes. Sequential groups correctly signal completion, preventing pipeline stalls at group boundaries.

---

## Phase 5: User Story 3 — Parallel Agent Recovery After Restart (Priority: P2)

**Goal**: Fix the recovery path so that ALL unassigned agents in a parallel group are reassigned after state reconstruction (e.g., after a service restart), not just agent[0].

**Independent Test**: Simulate a pipeline with a 3-agent parallel group where none have been assigned. Verify the recovery path reassigns all 3 agents. Verify that already-active agents are left untouched while only unassigned agents are reassigned.

### Tests for User Story 3

- [ ] T011 [US3] Add test `test_recovery_reassigns_all_unassigned_parallel_agents` in `solune/backend/tests/unit/test_copilot_polling.py`. Create a pipeline with a parallel group of 3 agents where none appear in the tracking table or pending cache. Mock `assign_agent_for_status`. Verify the recovery path calls the assignment function for all 3 agents. Also test the partial case: agent 1 is Active (in tracking table), agents 2 and 3 are unassigned — verify only agents 2 and 3 are reassigned.

### Implementation for User Story 3

- [ ] T012 [US3] Fix recovery path in `_process_pipeline_completion` in `solune/backend/src/services/copilot_polling/pipeline.py` (~line 710). Replace the single `current_agent` reassignment check with a `for agent in pipeline.current_agents:` loop. For each agent not in `completed_agents` or `failed_agents`: check if Active in tracking table → skip (`continue`); check if in pending assignments cache → skip (`continue`); otherwise → reassign via `assign_agent_for_status` using the agent's flat index from `pipeline.agents.index(agent)`. See `quickstart.md` Change D for before/after reference.

**Checkpoint**: Recovery path fixed — `pytest tests/unit/test_copilot_polling.py -v -k "recovery"` passes. After service restart, all parallel agents are recovered within a single recovery cycle.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate no regressions across the full test suite, verify property invariants hold, and run linting/type checks on modified files.

- [ ] T013 [P] Run property invariant test suite: `cd solune/backend && uv run pytest tests/property/test_pipeline_state_machine.py -v` — verify all existing property-based invariants still hold with the new `current_agents` property and fixed `is_complete`.
- [ ] T014 [P] Run lint and type checks on modified source files: `cd solune/backend && .venv/bin/ruff check src/services/workflow_orchestrator/models.py src/services/copilot_polling/pipeline.py && .venv/bin/ruff format --check src/services/workflow_orchestrator/models.py src/services/copilot_polling/pipeline.py && uv run pyright src/services/workflow_orchestrator/models.py`
- [ ] T015 Run full regression test suite: `cd solune/backend && uv run pytest tests/unit/ tests/property/ -v --tb=short` — zero regressions expected. Sequential pipeline behavior must be unchanged (FR-008). Existing parallel tests must still pass (SC-005).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Skipped — no new infrastructure needed
- **Foundational (Phase 2)**: No dependencies — can start immediately. BLOCKS US1 (Phase 3) and US3 (Phase 5)
- **US1 (Phase 3)**: Depends on Phase 2 (`current_agents` property)
- **US2 (Phase 4)**: No dependencies on Phase 2 — can run in parallel with Phases 2 and 3
- **US3 (Phase 5)**: Depends on Phase 2 (`current_agents` property). Can run in parallel with US1 (Phase 3)
- **Polish (Phase 6)**: Depends on all user stories being complete (Phases 3-5)

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational `current_agents` property (T001). No dependencies on other stories.
- **User Story 2 (P1)**: Independent — no dependencies on `current_agents` or other stories. Can start immediately.
- **User Story 3 (P2)**: Depends on Foundational `current_agents` property (T001). No dependencies on other stories.

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Model changes before service/polling changes
- Core implementation before integration
- Story complete before moving to next priority

### Critical Path

```text
T001 (current_agents) → T007 (polling loop fix) → T012 (recovery fix) → T015 (full regression)
```

### Parallel Opportunities

- T002, T003, T004, T005 can all run in parallel (different test functions in same file)
- T008, T009 can run in parallel (different test functions)
- US2 (Phase 4) can run entirely in parallel with US1 (Phase 3) — different properties, no shared dependencies
- US1 (Phase 3) and US3 (Phase 5) can run in parallel — different sections of `pipeline.py` (polling loop vs recovery path)
- T013 and T014 can run in parallel (different verification commands)

---

## Parallel Example: Foundational Phase

```bash
# Launch all current_agents tests together (after T001):
Task: "Add test test_current_agents_parallel_returns_all in solune/backend/tests/unit/test_models.py"
Task: "Add test test_current_agents_sequential_returns_single in solune/backend/tests/unit/test_models.py"
Task: "Add test test_current_agents_empty_group_skipped in solune/backend/tests/unit/test_models.py"
Task: "Add test test_current_agents_flat_fallback in solune/backend/tests/unit/test_models.py"
```

## Parallel Example: US1 + US2 Together

```bash
# US2 has no dependency on current_agents — launch alongside US1:
Task: "[US1] Fix polling loop in pipeline.py"     # Requires T001
Task: "[US2] Fix is_complete in models.py"          # Independent — no T001 dependency
```

## Parallel Example: US1 + US3 Together

```bash
# Both depend on T001 but modify different sections of pipeline.py:
Task: "[US1] Fix polling loop (~line 680)"          # Polling section
Task: "[US3] Fix recovery path (~line 710)"         # Recovery section
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (`current_agents` property + tests)
2. Complete Phase 3: User Story 1 (polling loop fix + test)
3. **STOP and VALIDATE**: `pytest tests/unit/test_models.py tests/unit/test_copilot_polling.py -v -k "current_agents or parallel"` — MVP functional
4. Deploy/demo if ready — parallel groups now check all agents per cycle

### Incremental Delivery

1. Add `current_agents` property → Foundation ready
2. Add US1 (polling loop fix) → Test independently → **MVP! Parallel groups work** 🎯
3. Add US2 (sequential completion fix) → Test independently → Sequential groups report completion correctly
4. Add US3 (recovery path fix) → Test independently → Parallel recovery after restart works
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. **Developer A**: Phase 2 (T001) → Phase 3 (US1: T006-T007) → Phase 5 (US3: T011-T012)
2. **Developer B**: Phase 4 (US2: T008-T010) — fully independent, can start immediately
3. Stories complete and integrate independently

---

## Verification Commands

```bash
cd solune/backend

# Phase 2: Model property tests
uv run pytest tests/unit/test_models.py -v -k "current_agents"

# Phase 3 (US1): Polling loop fix
uv run pytest tests/unit/test_copilot_polling.py -v -k "parallel"

# Phase 4 (US2): Sequential completion fix
uv run pytest tests/unit/test_models.py -v -k "complete"

# Phase 5 (US3): Recovery path fix
uv run pytest tests/unit/test_copilot_polling.py -v -k "recovery"

# Phase 6: Property invariants
uv run pytest tests/property/test_pipeline_state_machine.py -v

# Phase 6: Full regression
uv run pytest tests/unit/ tests/property/ -v --tb=short

# Phase 6: Lint + type checks
.venv/bin/ruff check src/services/workflow_orchestrator/models.py src/services/copilot_polling/pipeline.py
.venv/bin/ruff format --check src/services/workflow_orchestrator/models.py src/services/copilot_polling/pipeline.py
uv run pyright src/services/workflow_orchestrator/models.py
```

---

## Notes

- [P] tasks = different files or functions, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing (TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- `_advance_pipeline` requires NO changes — its parallel logic is already correct (RT-005)
- Initial launch stagger in `orchestrator.py` is intentional rate-limit protection — NOT a bug (RT-006)
- Scope excludes `determine_next_action` in `agent_tracking.py` (separate lower-priority recovery path)
- Python 3.13 with PEP 695 type parameter syntax enforced by ruff (UP046/UP047)
