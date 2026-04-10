# Tasks: Harden Phase 1 — Critical Bug Fixes

**Input**: Design documents from `/specs/001-harden-phase1-bugfixes/`
**Prerequisites**: spec.md (required)

**Tests**: Tests are included — all three bugs require regression tests to prevent recurrence.

**Organization**: Tasks are grouped by user story (one per bug fix) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/backend/tests/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify existing utilities and identify code locations for all three bug fixes

- [ ] T001 Verify `BoundedDict` class exists with `touch()`, eviction, and `maxlen` in `solune/backend/src/utils.py`
- [ ] T002 Verify `AgentStatus.PENDING_PR` enum value exists in `solune/backend/src/models/agents.py`
- [ ] T003 Verify `_extract_agent_preview()` static method exists in `solune/backend/src/services/agents/service.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Ensure shared utilities support the fix requirements before modifying call sites

**⚠️ CRITICAL**: No bug fix work can begin until this phase is complete

- [ ] T004 Confirm `BoundedDict.__setitem__` evicts oldest entry when at capacity and `touch()` refreshes LRU order in `solune/backend/src/utils.py`
- [ ] T005 [P] Confirm `BoundedDict` unit tests cover eviction, `touch()`, `clear()`, and `on_evict` callback in `solune/backend/tests/unit/test_utils.py` and `solune/backend/tests/unit/test_bounded_eviction_callback.py`

**Checkpoint**: Foundation ready — bug fix implementation can now begin in parallel

---

## Phase 3: User Story 1 — Bounded Lock Dictionary Prevents Memory Leak (Priority: P1) 🎯 MVP

**Goal**: Replace the unbounded `dict[str, asyncio.Lock]` for per-project launch locks with a `BoundedDict` capped at 10,000 entries, using LRU eviction so active projects keep their locks while idle ones are reclaimed.

**Independent Test**: Create locks for more unique project IDs than the configured maximum and verify the dictionary size never exceeds that maximum. Confirm that recently-used entries survive eviction while idle entries are removed first.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T006 [P] [US1] Add regression test `test_lock_dict_is_bounded` asserting `_project_launch_locks` is a `BoundedDict` instance in `solune/backend/tests/unit/test_pipeline_state_store.py`
- [ ] T007 [P] [US1] Add regression test `test_lock_count_stays_bounded` creating locks for `maxlen + 100` projects and asserting `len(_project_launch_locks) <= maxlen` in `solune/backend/tests/unit/test_pipeline_state_store.py`
- [ ] T008 [P] [US1] Add regression test `test_returns_same_lock_for_same_project` verifying repeated calls return the identical `asyncio.Lock` instance in `solune/backend/tests/unit/test_pipeline_state_store.py`
- [ ] T009 [P] [US1] Add regression test `test_eviction_does_not_corrupt_remaining_locks` verifying remaining locks are valid `asyncio.Lock` instances after eviction in `solune/backend/tests/unit/test_pipeline_state_store.py`
- [ ] T010 [P] [US1] Add regression test `test_touch_refreshes_active_lock` verifying that accessing an existing lock moves it to the end of the eviction order (LRU refresh) in `solune/backend/tests/unit/test_pipeline_state_store.py`

### Implementation for User Story 1

- [ ] T011 [US1] Replace `_project_launch_locks: dict[str, asyncio.Lock] = {}` with `_project_launch_locks: BoundedDict[str, asyncio.Lock] = BoundedDict(maxlen=10_000)` in `solune/backend/src/services/pipeline_state_store.py` (line ~40), importing `BoundedDict` from `src.utils`
- [ ] T012 [US1] Refactor `get_project_launch_lock()` to use `BoundedDict` API — on cache miss call `__setitem__`, on cache hit call `touch()` for LRU refresh in `solune/backend/src/services/pipeline_state_store.py` (lines ~54–71)
- [ ] T013 [US1] Verify existing conftest cleanup `_project_launch_locks.clear()` still works with `BoundedDict` in `solune/backend/tests/conftest.py`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently — `_project_launch_locks` stays bounded at 10,000

---

## Phase 4: User Story 2 — Updated Local Agents Show Correct Lifecycle Status (Priority: P1)

**Goal**: Ensure all SQL paths in `update_agent()` set `lifecycle_status = PENDING_PR` when a PR is opened, so updated agents are not incorrectly shown as "active".

**Independent Test**: Update an existing local agent's configuration, verify the returned agent object has `status == AgentStatus.PENDING_PR`, and confirm the persisted database row reflects the same status along with the new PR number and branch name.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T014 [P] [US2] Add test `test_update_agent_marks_existing_local_agent_pending_pr` — insert an agent with `lifecycle_status=active`, update it, assert `result.agent.status == PENDING_PR` and DB row has `lifecycle_status=pending_pr` in `solune/backend/tests/unit/test_agents_service.py`
- [ ] T015 [P] [US2] Add test `test_update_repo_agent_inserts_local_row_with_pending_pr` — update a `repo:`-prefixed agent, assert new local row is inserted with `lifecycle_status=pending_pr`, correct `github_pr_number`, and `branch_name` in `solune/backend/tests/unit/test_agents_service.py`
- [ ] T016 [P] [US2] Add test `test_update_agent_rejects_pending_deletion` — attempt update on an agent with `lifecycle_status=pending_deletion`, assert `ValueError` is raised in `solune/backend/tests/unit/test_agents_service.py`
- [ ] T017 [P] [US2] Add test `test_runtime_preference_update_no_pr_no_status_change` — update only `icon_name` or `default_model_id`, assert no PR is opened and lifecycle status remains unchanged in `solune/backend/tests/unit/test_agents_service.py`

### Implementation for User Story 2

- [ ] T018 [US2] Ensure the UPDATE SQL path for existing local agents (non-`repo:` ID) sets `lifecycle_status = ?` to `AgentStatus.PENDING_PR.value` in `solune/backend/src/services/agents/service.py` (line ~1246)
- [ ] T019 [US2] Ensure the UPDATE SQL path for existing local agents with a prior local record (`existing_local_agent` branch) sets `lifecycle_status = ?` to `AgentStatus.PENDING_PR.value` in `solune/backend/src/services/agents/service.py` (line ~1279)
- [ ] T020 [US2] Ensure the INSERT SQL path for first-time repo-sourced agents includes `lifecycle_status = ?` set to `AgentStatus.PENDING_PR.value` in `solune/backend/src/services/agents/service.py` (line ~1311)
- [ ] T021 [US2] Ensure the returned `Agent` object has `status=AgentStatus.PENDING_PR` in the `AgentCreateResult` in `solune/backend/src/services/agents/service.py` (line ~1326)

**Checkpoint**: At this point, User Story 2 should be fully functional and testable independently — all agent update paths correctly set pending_pr

---

## Phase 5: User Story 3 — Malformed Agent Configs Are Rejected During Chat Refinement (Priority: P1)

**Goal**: Harden `_extract_agent_preview()` to reject malformed-but-parseable configs (e.g., `tools: "read"`, `tools: [123, null, {}]`, missing name) by returning `None` instead of passing invalid data downstream.

**Independent Test**: Supply various malformed config payloads and verify each one returns `None` from `_extract_agent_preview()` without raising exceptions.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T022 [P] [US3] Add test `test_non_list_tools_returns_none` — `tools: "read"` (string instead of list) → returns `None` in `solune/backend/tests/unit/test_agents_service.py`
- [ ] T023 [P] [US3] Add test `test_non_string_tools_elements_returns_none` — `tools: [123, null, {}]` (list with non-string elements) → returns `None` in `solune/backend/tests/unit/test_agents_service.py`
- [ ] T024 [P] [US3] Add test `test_mixed_valid_invalid_tools_returns_none` — `tools: ["read", 123, "write"]` (mixed valid and invalid) → returns `None` in `solune/backend/tests/unit/test_agents_service.py`
- [ ] T025 [P] [US3] Add test `test_empty_string_tool_returns_none` — `tools: ["read", "", "write"]` (empty string element) → returns `None` in `solune/backend/tests/unit/test_agents_service.py`
- [ ] T026 [P] [US3] Add test `test_empty_name_returns_none` — `name: ""` → returns `None` in `solune/backend/tests/unit/test_agents_service.py`
- [ ] T027 [P] [US3] Add test `test_missing_name_key_returns_none` — no `name` field → returns `None` in `solune/backend/tests/unit/test_agents_service.py`
- [ ] T028 [P] [US3] Add test `test_non_dict_top_level_returns_none` — top-level JSON is a list, not a dict → returns `None` in `solune/backend/tests/unit/test_agents_service.py`
- [ ] T029 [P] [US3] Add test `test_valid_config_returns_preview` — valid config with correct types → returns populated `AgentPreview` in `solune/backend/tests/unit/test_agents_service.py`

### Implementation for User Story 3

- [ ] T030 [US3] Add guard after `isinstance(tools, list)` check to validate every element is a non-empty string: `if not all(isinstance(t, str) and t for t in tools): return None` in `solune/backend/src/services/agents/service.py` (line ~1473)
- [ ] T031 [US3] Ensure `name` emptiness check rejects whitespace-only names (e.g., `name: "   "`) by using `if not name or not name.strip()` in `solune/backend/src/services/agents/service.py` (line ~1469)

**Checkpoint**: All three user stories should now be independently functional — malformed configs are rejected without exceptions

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, and regression prevention

- [ ] T032 [P] Run full backend test suite to confirm no regressions: `cd solune/backend && python -m pytest`
- [ ] T033 [P] Run type checker to confirm no type errors: `cd solune/backend && pyright`
- [ ] T034 [P] Run linter to confirm code style: `cd solune/backend && ruff check`
- [ ] T035 Verify memory stability: review that `_project_launch_locks` maxlen of 10,000 is appropriate for production workloads and document the choice in a code comment in `solune/backend/src/services/pipeline_state_store.py`
- [ ] T036 Review T008 test results to confirm edge case: concurrent lock creation for the same project ID returns the same lock instance
- [ ] T037 Verify edge case: multiple `agent-config` code blocks — only the first match is processed (already handled by `pattern.search()` in `solune/backend/src/services/agents/service.py`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3–5)**: All depend on Foundational phase completion
  - User stories can then proceed **in parallel** (different files, no cross-dependencies)
  - Or sequentially in priority order (all are P1 so order is flexible)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2 — modifies `pipeline_state_store.py` and `utils.py` only
- **User Story 2 (P1)**: Can start after Phase 2 — modifies `agents/service.py` (update_agent method)
- **User Story 3 (P1)**: Can start after Phase 2 — modifies `agents/service.py` (_extract_agent_preview method)
- **US2 and US3** touch the same file but **different methods** — can run in parallel with care

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Implementation fixes the specific code path
- Re-run tests to confirm they PASS after implementation
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1**: All setup verification tasks (T001–T003) can run in parallel
- **Phase 2**: Foundation verification tasks (T004–T005) can run in parallel
- **Phase 3–5**: All three user stories can start in parallel after Phase 2
  - US1 tests (T006–T010) can all run in parallel
  - US2 tests (T014–T017) can all run in parallel
  - US3 tests (T022–T029) can all run in parallel
- **Phase 6**: Polish tasks T032–T034 can run in parallel

---

## Parallel Example: All Three Bug Fixes

```bash
# After Phase 2 completes, launch all three stories in parallel:

# Developer A: User Story 1 (pipeline_state_store.py)
Task: T006–T010 (write tests) → T011–T013 (implement fix)

# Developer B: User Story 2 (agents/service.py — update_agent)
Task: T014–T017 (write tests) → T018–T021 (implement fix)

# Developer C: User Story 3 (agents/service.py — _extract_agent_preview)
Task: T022–T029 (write tests) → T030–T031 (implement fix)
```

---

## Implementation Strategy

### MVP First (Any Single Bug Fix)

1. Complete Phase 1: Setup verification
2. Complete Phase 2: Foundation verification
3. Complete Phase 3: User Story 1 (memory leak fix)
4. **STOP and VALIDATE**: Run bounded-lock regression tests independently
5. Deploy if ready — memory leak is the highest-impact fix

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (memory leak) → Test independently → Ship
3. Add User Story 2 (lifecycle status) → Test independently → Ship
4. Add User Story 3 (config validation) → Test independently → Ship
5. Each bug fix adds reliability without breaking previous fixes

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundation together
2. Once Foundation is verified:
   - Developer A: User Story 1 (`pipeline_state_store.py`)
   - Developer B: User Story 2 (`agents/service.py` — `update_agent`)
   - Developer C: User Story 3 (`agents/service.py` — `_extract_agent_preview`)
3. Bug fixes complete and integrate independently — no cross-story dependencies

---

## Summary

| Metric | Value |
|---|---|
| **Total tasks** | 37 |
| **US1 tasks** (memory leak) | 8 (T006–T013) |
| **US2 tasks** (lifecycle status) | 8 (T014–T021) |
| **US3 tasks** (config validation) | 10 (T022–T031) |
| **Setup + Foundation tasks** | 5 (T001–T005) |
| **Polish tasks** | 6 (T032–T037) |
| **Parallel opportunities** | 28 tasks marked [P] |
| **Suggested MVP** | User Story 1 (memory leak — highest production impact) |

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- All three bugs are P1 priority — order is flexible based on team capacity
- US2 and US3 modify the same file (`agents/service.py`) but different methods — parallelizable with merge coordination
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
