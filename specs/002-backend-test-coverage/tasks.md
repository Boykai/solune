# Tasks: Increase Backend Test Coverage & Fix Bugs

**Input**: Design documents from `/specs/002-backend-test-coverage/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/test-contracts.yaml

**Tests**: Tests ARE the primary deliverable of this feature. All tasks produce test code. Tests follow existing patterns (pytest-asyncio auto mode, MagicMock for aiosqlite, patch at import location).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. Phase 1 (US1) is already completed and included for traceability only.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app monorepo**: `solune/backend/src/`, `solune/backend/tests/unit/`
- **Source files under test**: NO changes — test-only feature
- **Test files**: Extend existing test modules with new test functions

---

## Phase 1: Setup (Shared Infrastructure) — ALREADY COMPLETED ✅

**Purpose**: Verify green baseline — all existing tests pass before new test work begins

- [x] T001 Verify existing test suite passes with `cd solune/backend && uv run pytest tests/unit/ -q` (0 failures)
- [x] T002 Record baseline coverage for 4 target files: projects.py (37.7%), agent_creator.py (39.4%), agents/service.py (47.4%), chores/service.py (51.3%)

---

## Phase 2: User Story 1 — Fix Broken Tests to Restore Green Suite (Priority: P1) ✅ COMPLETED

**Goal**: Convert 9 sync tests → async in test_agent_provider.py, add 2 new passthrough tests

**Independent Test**: `cd solune/backend && uv run pytest tests/unit/test_agent_provider.py -v` — zero failures

> **NOTE**: This phase was completed before task generation. Included for traceability.

- [x] T003 [US1] Convert 9 sync tests to async with `await` in solune/backend/tests/unit/test_agent_provider.py
- [x] T004 [US1] Mock `get_copilot_client_pool` at `src.services.completion_providers` in solune/backend/tests/unit/test_agent_provider.py
- [x] T005 [P] [US1] Add timeout passthrough test verifying `agent_copilot_timeout_seconds` is forwarded in solune/backend/tests/unit/test_agent_provider.py
- [x] T006 [P] [US1] Add mcp_servers passthrough test verifying MCP config forwarding in solune/backend/tests/unit/test_agent_provider.py
- [x] T007 [US1] Run full suite to confirm 0 failures, 4071+ passed

**Checkpoint**: ✅ Green suite restored — all subsequent phases can proceed

---

## Phase 3: User Story 2 — Increase Project Management Coverage (Priority: P2)

**Goal**: Increase `src/api/projects.py` coverage from 37.7% → ~70% by adding ~30 new test functions

**Independent Test**: `cd solune/backend && uv run pytest tests/unit/test_api_projects.py -v --cov=src.api.projects --cov-report=term-missing`

### Rate Limit Detection Tests

- [ ] T008 [P] [US2] Add test for 403 + `X-RateLimit-Remaining: "0"` triggering rate limit detection in solune/backend/tests/unit/test_api_projects.py (TC-PROJ-001)
- [ ] T009 [P] [US2] Add test for 403 with empty rate limit dict NOT triggering rate limit path in solune/backend/tests/unit/test_api_projects.py (TC-PROJ-002)

### Task Fallback Tests

- [ ] T010 [P] [US2] Add test for `get_project_tasks` exception fallback to `get_done_items()` returning cached Task models in solune/backend/tests/unit/test_api_projects.py (TC-PROJ-003)
- [ ] T011 [P] [US2] Add test for `get_project_tasks` exception fallback when DB cache is also empty in solune/backend/tests/unit/test_api_projects.py (TC-PROJ-004)

### Project List Cache Tests

- [ ] T012 [P] [US2] Add test for `list_projects` with cache returning empty list `[]` (not cache miss) in solune/backend/tests/unit/test_api_projects.py (TC-PROJ-005)
- [ ] T013 [P] [US2] Add test for `list_projects` with cache returning `None` (unpopulated, triggers API call) in solune/backend/tests/unit/test_api_projects.py (TC-PROJ-006)
- [ ] T014 [P] [US2] Add test for `list_projects` with non-rate-limit error fallback in solune/backend/tests/unit/test_api_projects.py (TC-PROJ-007)

### Get Project Cache Edge Cases

- [ ] T015 [P] [US2] Add test for `get_project` when project ID is not in cached list in solune/backend/tests/unit/test_api_projects.py (TC-PROJ-008)
- [ ] T016 [P] [US2] Add test for `get_project` with `refresh=True` but API returns error in solune/backend/tests/unit/test_api_projects.py (TC-PROJ-009)

### WebSocket Subscription Tests

- [ ] T017 [US2] Add test for `websocket_subscribe` receiving data change via hash diffing in solune/backend/tests/unit/test_api_projects.py (TC-PROJ-010)
- [ ] T018 [US2] Add test for `websocket_subscribe` stale revalidation counter triggering refresh in solune/backend/tests/unit/test_api_projects.py (TC-PROJ-011)
- [ ] T019 [US2] Add test for `websocket_subscribe` client disconnect cleanup (WebSocketDisconnect handling) in solune/backend/tests/unit/test_api_projects.py (TC-PROJ-012)

### Verification

- [ ] T020 [US2] Run `uv run pytest tests/unit/test_api_projects.py -v --cov=src.api.projects --cov-report=term-missing` and verify coverage ≥ 70%

**Checkpoint**: Project management module at ~70% coverage — independently testable

---

## Phase 4: User Story 3 — Increase Agent Creator Coverage (Priority: P3)

**Goal**: Increase `src/services/agent_creator.py` coverage from 39.4% → ~65% by adding ~25 new test functions

**Independent Test**: `cd solune/backend && uv run pytest tests/unit/test_agent_creator.py -v --cov=src.services.agent_creator --cov-report=term-missing`

### Admin Auth Edge Case Tests

- [ ] T021 [P] [US3] Add test for debug auto-promote via CAS (`UPDATE WHERE admin_github_user_id IS NULL`, rowcount=1) in solune/backend/tests/unit/test_agent_creator.py (TC-AC-001)
- [ ] T022 [P] [US3] Add test for `ADMIN_GITHUB_USER_ID` env var recognizing configured user as admin in solune/backend/tests/unit/test_agent_creator.py (TC-AC-002)
- [ ] T023 [P] [US3] Add test for database exception during admin auth check (graceful failure, no internal details) in solune/backend/tests/unit/test_agent_creator.py (TC-AC-003)

### Status Resolution Tests

- [ ] T024 [P] [US3] Add test for fuzzy empty input status resolution (empty string handled without crash) in solune/backend/tests/unit/test_agent_creator.py (TC-AC-004)
- [ ] T025 [P] [US3] Add test for normalized case-insensitive status matching in solune/backend/tests/unit/test_agent_creator.py (TC-AC-005)
- [ ] T026 [P] [US3] Add test for out-of-range numeric selection (e.g., "99") rejection in solune/backend/tests/unit/test_agent_creator.py (TC-AC-006)
- [ ] T027 [P] [US3] Add test for new column creation during status resolution via API in solune/backend/tests/unit/test_agent_creator.py (TC-AC-007)

### Creation Pipeline Tests (Steps 3–7)

- [ ] T028 [US3] Add test for duplicate agent name detection halting pipeline in solune/backend/tests/unit/test_agent_creator.py (TC-AC-008)
- [ ] T029 [US3] Add test for issue creation failure (Step 5) logged as warning, pipeline continues in solune/backend/tests/unit/test_agent_creator.py (TC-AC-009)
- [ ] T030 [US3] Add test for PR creation failure (Step 7) after issue created, with cleanup attempt in solune/backend/tests/unit/test_agent_creator.py (TC-AC-010)

### AI Service Failure Tests

- [ ] T031 [P] [US3] Add test for `generate_agent_config()` exception → user-facing error, session cleanup in solune/backend/tests/unit/test_agent_creator.py (TC-AC-011)
- [ ] T032 [P] [US3] Add test for `edit_agent_config()` failure on retry → error message, preview preserved in solune/backend/tests/unit/test_agent_creator.py (TC-AC-012)
- [ ] T033 [P] [US3] Add test for AI returning string instead of list for tools → graceful coercion/default in solune/backend/tests/unit/test_agent_creator.py (TC-AC-013)

### Verification

- [ ] T034 [US3] Run `uv run pytest tests/unit/test_agent_creator.py -v --cov=src.services.agent_creator --cov-report=term-missing` and verify coverage ≥ 65%

**Checkpoint**: Agent creator module at ~65% coverage — independently testable

---

## Phase 5: User Story 4 — Increase Agent Service Coverage (Priority: P4) ⚡ Parallel with Phase 4

**Goal**: Increase `src/services/agents/service.py` coverage from 47.4% → ~70% by adding ~35 new test functions

**Independent Test**: `cd solune/backend && uv run pytest tests/unit/test_agents_service.py -v --cov=src.services.agents.service --cov-report=term-missing`

### Cache & Stale Data Tests

- [ ] T035 [P] [US4] Add test for `list_agents()` with cached agent list + user preference overlay (model_id, model_name, icon_name merged) in solune/backend/tests/unit/test_agents_service.py (TC-AS-001)
- [ ] T036 [P] [US4] Add test for stale cache fallback when API fails (expired cache returns last known data) in solune/backend/tests/unit/test_agents_service.py (TC-AS-002)
- [ ] T037 [P] [US4] Add test for session pruning removing stale sessions while preserving active ones in solune/backend/tests/unit/test_agents_service.py (TC-AS-003)

### Agent Source Mixing Tests

- [ ] T038 [P] [US4] Add test for `bulk_update_models()` with both REPO and LOCAL agent sources in solune/backend/tests/unit/test_agents_service.py (TC-AS-004)
- [ ] T039 [P] [US4] Add test for partial failure during bulk update (successful updates applied, failures reported) in solune/backend/tests/unit/test_agents_service.py (TC-AS-005)
- [ ] T040 [P] [US4] Add test for tombstoned agents (PENDING_DELETION) excluded from `list_agents()` results in solune/backend/tests/unit/test_agents_service.py (TC-AS-006)

### YAML Frontmatter Tests

- [ ] T041 [P] [US4] Add test for agent file with missing YAML frontmatter fields → default values used in solune/backend/tests/unit/test_agents_service.py (TC-AS-007)
- [ ] T042 [P] [US4] Add test for agent file with YAML parse errors → fallback to basic agent without crashing in solune/backend/tests/unit/test_agents_service.py (TC-AS-008)
- [ ] T043 [P] [US4] Add test for agent file with no YAML frontmatter (plain markdown) → handled gracefully in solune/backend/tests/unit/test_agents_service.py (TC-AS-009)

### Tool Resolution Tests

- [ ] T044 [P] [US4] Add test for MCP server config normalization to standard GitHub agent YAML shape in solune/backend/tests/unit/test_agents_service.py (TC-AS-010)
- [ ] T045 [P] [US4] Add test for wildcard tool pattern expansion vs explicit tool IDs with deduplication in solune/backend/tests/unit/test_agents_service.py (TC-AS-011)
- [ ] T046 [P] [US4] Add test for invalid MCP configuration (missing required fields) skipped with warning in solune/backend/tests/unit/test_agents_service.py (TC-AS-012)

### Create Agent Tests

- [ ] T047 [P] [US4] Add test for slug generation from special characters (emojis, unicode) → valid sanitized slug in solune/backend/tests/unit/test_agents_service.py (TC-AS-013)
- [ ] T048 [P] [US4] Add test for AI enhancement failure during creation → fallback to raw user input in solune/backend/tests/unit/test_agents_service.py (TC-AS-014)
- [ ] T049 [P] [US4] Add test for raw mode creation (skip AI enhancement) → agent created with user input as-is in solune/backend/tests/unit/test_agents_service.py (TC-AS-015)

### Verification

- [ ] T050 [US4] Run `uv run pytest tests/unit/test_agents_service.py -v --cov=src.services.agents.service --cov-report=term-missing` and verify coverage ≥ 70%

**Checkpoint**: Agent service module at ~70% coverage — independently testable

---

## Phase 6: User Story 5 — Increase Chores Service Coverage (Priority: P5) ⚡ Parallel with Phase 5

**Goal**: Increase `src/services/chores/service.py` coverage from 51.3% → ~75% by adding ~30 new test functions

**Independent Test**: `cd solune/backend && uv run pytest tests/unit/test_chores_service.py -v --cov=src.services.chores.service --cov-report=term-missing`

### Preset Seeding Tests

- [ ] T051 [P] [US5] Add test for idempotent re-seed (`seed_presets()` called when presets already exist → no duplicates) in solune/backend/tests/unit/test_chores_service.py (TC-CS-001)
- [ ] T052 [P] [US5] Add test for preset file read failure (`Path.read_text` raises `FileNotFoundError` → graceful handling) in solune/backend/tests/unit/test_chores_service.py (TC-CS-002)
- [ ] T053 [P] [US5] Add test for fresh seed of all 3 presets with unique IDs in solune/backend/tests/unit/test_chores_service.py (TC-CS-003)

### Update Validation Tests

- [ ] T054 [P] [US5] Add test for inconsistent schedule parameters (schedule_type without schedule_value → validation error) in solune/backend/tests/unit/test_chores_service.py (TC-CS-004)
- [ ] T055 [P] [US5] Add test for boolean `True` → integer `1` conversion for `enabled` field in solune/backend/tests/unit/test_chores_service.py (TC-CS-005)
- [ ] T056 [P] [US5] Add test for column name with SQL injection payload rejected before `db.execute` in solune/backend/tests/unit/test_chores_service.py (TC-CS-006)
- [ ] T057 [P] [US5] Add test for boolean `False` → integer `0` conversion for `auto_merge` field in solune/backend/tests/unit/test_chores_service.py (TC-CS-007)

### Trigger State CAS Tests

- [ ] T058 [US5] Add test for first CAS trigger with `last_triggered_at = NULL` → CAS succeeds, new timestamp recorded in solune/backend/tests/unit/test_chores_service.py (TC-CS-008)
- [ ] T059 [US5] Add test for CAS trigger with matching old value → CAS succeeds, timestamp updated in solune/backend/tests/unit/test_chores_service.py (TC-CS-009)
- [ ] T060 [US5] Add test for CAS trigger with mismatched old value → CAS fails (rowcount=0), double-fire prevented in solune/backend/tests/unit/test_chores_service.py (TC-CS-010)
- [ ] T061 [US5] Add test for `clear_current_issue()` setting `current_issue_number` and `current_issue_node_id` to NULL in solune/backend/tests/unit/test_chores_service.py (TC-CS-011)

### Verification

- [ ] T062 [US5] Run `uv run pytest tests/unit/test_chores_service.py -v --cov=src.services.chores.service --cov-report=term-missing` and verify coverage ≥ 75%

**Checkpoint**: Chores service module at ~75% coverage — independently testable

---

## Phase 7: User Story 6 — Verify Full Suite and Coverage Targets (Priority: P6)

**Goal**: Confirm all new tests integrate cleanly and per-file coverage targets are met

**Independent Test**: Full backend suite + per-file coverage report

- [ ] T063 Run full backend test suite `cd solune/backend && uv run pytest tests/unit/ --tb=short -q` and confirm 0 failures
- [ ] T064 Generate targeted per-file coverage report: `uv run pytest tests/unit/ --cov=src.api.projects --cov=src.services.agent_creator --cov=src.services.agents.service --cov=src.services.chores.service --cov-report=term-missing -q`
- [ ] T065 Compare per-file coverage deltas against baselines: projects.py (37.7% → ≥70%), agent_creator.py (39.4% → ≥65%), agents/service.py (47.4% → ≥70%), chores/service.py (51.3% → ≥75%)
- [ ] T066 Verify overall backend coverage trending toward ~85% (baseline: 78.3%)

**Checkpoint**: All coverage targets met, zero regressions — ready to merge

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: ✅ COMPLETED — green baseline confirmed
- **Phase 2 (US1 — Fix Broken Tests)**: ✅ COMPLETED — depends on Phase 1
- **Phase 3 (US2 — projects.py)**: Depends on Phase 1/2 completion only
- **Phase 4 (US3 — agent_creator.py)**: Depends on Phase 1/2 completion only
- **Phase 5 (US4 — agents/service.py)**: Depends on Phase 1/2 completion only — ⚡ parallel with Phase 4
- **Phase 6 (US5 — chores/service.py)**: Depends on Phase 1/2 completion only — ⚡ parallel with Phase 5
- **Phase 7 (US6 — Verification)**: Depends on ALL prior phases (3–6) completion

### User Story Dependencies

- **US1 (P1)**: ✅ COMPLETED — no dependencies
- **US2 (P2)**: No dependencies on other stories — can start immediately
- **US3 (P3)**: No dependencies on other stories — can start immediately
- **US4 (P4)**: No dependencies on other stories — ⚡ parallel with US3
- **US5 (P5)**: No dependencies on other stories — ⚡ parallel with US4
- **US6 (P6)**: Depends on US2 + US3 + US4 + US5 all complete

### Within Each User Story

- All tasks marked [P] within a story can run in parallel (they target independent test scenarios in the same file)
- Non-[P] tasks (e.g., WebSocket tests, pipeline tests) have implicit ordering due to shared setup complexity
- Verification task at the end of each phase must run after all story tasks complete

### Parallel Opportunities

- **Maximum parallelism**: US2 + US3 + US4 + US5 can ALL start simultaneously (they modify different test files)
- **Within US2**: T008–T016 are all [P] (independent scenarios); T017–T019 are sequential (WebSocket lifecycle)
- **Within US3**: T021–T027 are all [P] (independent admin/status scenarios); T028–T030 are sequential (pipeline steps); T031–T033 are [P] (independent AI failures)
- **Within US4**: All T035–T049 are [P] (independent scenarios across different test groups)
- **Within US5**: T051–T057 are all [P] (independent seeding/validation); T058–T061 are sequential (CAS state machine)

---

## Parallel Example: User Story 2 (projects.py)

```bash
# Launch all parallelizable rate-limit + cache tests at once:
Task T008: "Rate limit detection: 403 + X-RateLimit-Remaining: 0"
Task T009: "Rate limit: empty dict, NOT rate limited"
Task T010: "Task fallback: exception → get_done_items()"
Task T011: "Task fallback: exception + empty DB cache"
Task T012: "List projects: cache returns empty list []"
Task T013: "List projects: cache returns None"
Task T014: "List projects: non-rate-limit error"
Task T015: "Get project: not in cached list"
Task T016: "Get project: refresh=True + API error"

# Then sequential WebSocket tests:
Task T017: "WebSocket: hash diffing detects data change"
Task T018: "WebSocket: stale revalidation counter triggers refresh"
Task T019: "WebSocket: client disconnect cleanup"
```

## Parallel Example: User Story 4 (agents/service.py)

```bash
# All 15 tasks can run in parallel (independent scenarios):
Task T035–T037: Cache & stale data tests (3 tests)
Task T038–T040: Agent source mixing tests (3 tests)
Task T041–T043: YAML frontmatter tests (3 tests)
Task T044–T046: Tool resolution tests (3 tests)
Task T047–T049: Create agent tests (3 tests)
```

---

## Implementation Strategy

### MVP First (User Story 2 Only — projects.py)

1. ✅ Phase 1 + Phase 2: Already completed (green suite)
2. Complete Phase 3: User Story 2 (projects.py — lowest coverage, highest impact)
3. **STOP and VALIDATE**: Run `uv run pytest tests/unit/test_api_projects.py -v --cov=src.api.projects --cov-report=term-missing`
4. Confirm ~70% coverage reached for projects.py

### Incremental Delivery

1. ✅ US1 complete → green suite
2. Add US2 (projects.py) → Test independently → 37.7% → ~70%
3. Add US3 (agent_creator.py) → Test independently → 39.4% → ~65%
4. Add US4 (agents/service.py) → Test independently → 47.4% → ~70%
5. Add US5 (chores/service.py) → Test independently → 51.3% → ~75%
6. US6 verification → full suite green + coverage targets met

### Parallel Team Strategy

With multiple developers after US1 is complete:

1. **Developer A**: US2 (projects.py) — Phase 3
2. **Developer B**: US3 (agent_creator.py) — Phase 4
3. **Developer C**: US4 (agents/service.py) — Phase 5
4. **Developer D**: US5 (chores/service.py) — Phase 6
5. All developers converge for Phase 7 (verification)

---

## Notes

- [P] tasks = independent test scenarios in the same file, no shared mocking state
- [Story] label maps task to specific user story for traceability
- Each user story targets an independent source file and test file — no cross-file conflicts
- All tests follow existing patterns: `pytest-asyncio` auto mode, `MagicMock` for aiosqlite, `AsyncMock` for async services, `@patch` at import location
- Contract IDs (TC-PROJ-001, TC-AC-001, etc.) trace back to `contracts/test-contracts.yaml`
- No production source code is modified — this is a test-only feature
- Decisions from `research.md`: R1 (async auto mode), R2 (MagicMock for aiosqlite), R3 (TestClient WebSocket), R4 (CAS semantics), R5 (SQL injection defense), R6 (AI failure mocking), R7 (parallel execution), R8 (pytest-cov per-file)
