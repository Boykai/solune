# Tasks: Uplift Solune Testing — Remove Skips, Fix Bugs, Apply Modern Best Practices

**Input**: Design documents from `/specs/020-uplift-solune-testing/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅, contracts/ ✅

**Tests**: This feature IS about testing — tests are the primary deliverable. Test tasks are included throughout.

**Organization**: Tasks are grouped by user story (6 stories from spec.md) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/` (Python/FastAPI), `solune/frontend/` (TypeScript/React)
- Tests: `solune/backend/tests/`, `solune/frontend/src/**/*.test.{ts,tsx}`, `solune/frontend/e2e/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Audit all skip markers and commit the inventory — prerequisite for all subsequent phases

- [x] T001 Search backend tests for all skip markers (`pytest.mark.skip`, `pytest.mark.xfail`, `skipIf`, `unittest.skip`, `pytest.skip`) in `solune/backend/tests/` and record file, line, marker, and reason
- [x] T002 Search frontend source and E2E tests for all skip markers (`test.skip`, `it.skip`, `describe.skip`, `.todo`, `xit`, `xdescribe`) in `solune/frontend/src/` and `solune/frontend/e2e/` and record file, line, marker, and reason
- [x] T003 Classify each marker as unconditional (removable) or conditional infrastructure guard (acceptable) per contracts in `specs/020-uplift-solune-testing/contracts/backend-testing.md` and `specs/020-uplift-solune-testing/contracts/frontend-testing.md`
- [x] T004 Commit the skip inventory to `.specify/memory/test-skip-inventory.md` with a table of all 16 markers (10 backend + 6 frontend E2E), their classification, and verdicts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infrastructure and configuration changes that MUST be complete before user story work begins

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Verify `asyncio_mode = "auto"` and `asyncio_default_fixture_loop_scope = "function"` are set in `solune/backend/pyproject.toml` under `[tool.pytest.ini_options]` — confirm no changes needed
- [x] T006 Verify `filterwarnings` in `solune/backend/pyproject.toml` only suppresses intentional deprecation warnings — confirm no changes needed
- [x] T007 Verify no deprecated `loop` parameter usage in `solune/backend/tests/helpers/` conftest fixtures — confirm modern patterns in use
- [x] T008 Verify `solune/frontend/vitest.config.ts` has `globals: true`, `environment: 'happy-dom'`, `setupFiles: ['./src/test/setup.ts']`, `coverage.provider: 'v8'`, and correct `thresholds` — confirm no changes needed
- [x] T009 Verify `solune/frontend/src/test/setup.ts` configures jest-dom matchers — confirm no changes needed
- [x] T010 Verify `test.exclude` in `solune/frontend/vitest.config.ts` does not accidentally exclude unit test files — confirm no changes needed
- [x] T011 Verify `jest-axe` is available in `solune/frontend/package.json` devDependencies; if missing, install with `npm install --save-dev jest-axe @types/jest-axe`

**Checkpoint**: Infrastructure verified — user story implementation can now begin

---

## Phase 3: User Story 1 — Remove All Backend Test Skips (Priority: P1) 🎯 MVP

**Goal**: Verify every backend skip marker is a conditional infrastructure guard and confirm zero unconditional `@pytest.mark.skip` or `@pytest.mark.xfail` markers remain

**Independent Test**: Run `pytest tests/ -v` in `solune/backend/` and confirm zero `SKIPPED` results from unconditional markers

### Implementation for User Story 1

- [x] T012 [US1] Verify `solune/backend/tests/unit/test_run_mutmut_shard.py:138` uses `@pytest.mark.skipif` with CI workflow YAML condition — confirm conditional infrastructure guard, no removal needed
- [x] T013 [US1] Verify `solune/backend/tests/architecture/test_import_rules.py` lines 54, 93, and 116 each use `pytest.skip()` with directory-existence conditions — confirm conditional infrastructure guards, no removal needed
- [x] T014 [US1] Verify `solune/backend/tests/performance/test_board_load_time.py:40-71` uses `pytest.skip()` with env-var and HTTP-health conditions — confirm conditional infrastructure guards, no removal needed
- [x] T015 [US1] Verify `solune/backend/tests/integration/test_custom_agent_assignment.py:45` uses `pytest.skip()` with `GITHUB_TOKEN` env-var condition — confirm conditional infrastructure guard, no removal needed
- [x] T016 [US1] Run `uv run pytest tests/ -x -q` from `solune/backend/` and confirm all tests pass (skipped tests skip only due to missing infrastructure)
- [x] T017 [US1] Run `grep -rn "pytest.mark.skip\b" solune/backend/tests/` (without `if`) and confirm zero unconditional `@pytest.mark.skip(reason=...)` markers exist
- [x] T018 [US1] Run `grep -rn "pytest.mark.xfail" solune/backend/tests/` and confirm zero `@pytest.mark.xfail` markers exist

**Checkpoint**: US1 complete — zero unconditional backend skip markers confirmed

---

## Phase 4: User Story 2 — Fix Backend pytest Infrastructure (Priority: P1)

**Goal**: Confirm the existing backend coverage enforcement threshold remains at 75% (which already exceeds issue #1149's 70% minimum) and verify pytest runs with zero asyncio deprecation warnings

**Independent Test**: Run `uv run pytest tests/ --cov=src --cov-fail-under=75 -q --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency` from `solune/backend/` and confirm coverage >= 75% is enforced

### Implementation for User Story 2

- [ ] T019 [US2] Verify `[tool.coverage.report] fail_under = 75` remains in `solune/backend/pyproject.toml`, noting that it already satisfies and exceeds issue #1149's 70% minimum
- [ ] T020 [US2] Run `uv run pytest tests/ --cov=src --cov-fail-under=75 -q --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency` from `solune/backend/` and confirm coverage threshold is enforced
- [ ] T021 [US2] Run `uv run pytest tests/ -W error::DeprecationWarning -x -q` from `solune/backend/` and confirm zero asyncio deprecation warnings

**Checkpoint**: US2 complete — existing 75% backend coverage enforcement preserved, zero deprecation warnings

---

## Phase 5: User Story 3 — Fix Frontend Vitest Infrastructure (Priority: P1)

**Goal**: Confirm Vitest configuration is correct and jest-axe matchers are available for per-test import

**Independent Test**: Run `npm run test` from `solune/frontend/` with zero configuration warnings

### Implementation for User Story 3

- [ ] T022 [US3] Run `npx vitest run --reporter=verbose` from `solune/frontend/` and confirm zero configuration warnings
- [ ] T023 [US3] Verify jest-axe can be imported in a test file by checking `solune/frontend/package.json` for `jest-axe` dependency or adding it if missing (per-test import pattern, not global setup)

**Checkpoint**: US3 complete — Vitest infrastructure verified, jest-axe available

---

## Phase 6: User Story 4 — Resolve Frontend Skipped E2E Tests (Priority: P2)

**Goal**: Verify all frontend E2E skips are conditional infrastructure guards and confirm useAuth.test.tsx stability in parallel modes

**Independent Test**: With infrastructure running, `npx playwright test` executes all tests; without infrastructure, tests skip gracefully

### Implementation for User Story 4

- [x] T024 [US4] Verify `solune/frontend/e2e/integration.spec.ts:62,73` uses `test.skip()` inside catch blocks for unreachable backend — confirm conditional infrastructure guards, no removal needed
- [x] T025 [US4] Verify `solune/frontend/e2e/project-load-performance.spec.ts:47,50,65,114` uses `test.skip()` for missing auth state, env vars, and unreachable frontend — confirm conditional infrastructure guards, no removal needed
- [x] T026 [US4] Run `grep -rn "\.skip\|\.todo\|xit\b\|xdescribe" solune/frontend/src/` and confirm zero unconditional skip markers in unit tests
- [ ] T027 [US4] Run `npx vitest run src/hooks/useAuth.test.tsx` from `solune/frontend/` and confirm all 18 tests pass
- [ ] T028 [US4] Run `npx vitest run --pool=forks src/hooks/useAuth.test.tsx` from `solune/frontend/` and confirm all 18 tests pass in process isolation mode
- [ ] T029 [US4] Run `npx vitest run --pool=threads src/hooks/useAuth.test.tsx` from `solune/frontend/` and confirm all 18 tests pass in thread isolation mode

**Checkpoint**: US4 complete — zero unconditional frontend skips, useAuth.test.tsx stable in all pool modes

---

## Phase 7: User Story 5 — Add Net-New Coverage for Critical Untested Paths (Priority: P2)

**Goal**: Add meaningful tests for high-risk backend and frontend code paths with zero or partial coverage, increasing coverage >= 10 percentage points in targeted modules

**Independent Test**: Run coverage reports and confirm >= 10 percentage-point increase from baseline in targeted modules; zero new `.skip` markers

### Tests for User Story 5

> **NOTE: Write tests that assert behavior, not implementation. Cover happy path plus at least one error/edge case. Use existing helpers from `tests/helpers/`.**

- [ ] T030 [P] [US5] Create `solune/backend/tests/unit/test_resolve_repository.py` — test `resolve_repository()` from `solune/backend/src/utils.py`: cache hit returns cached value, GraphQL fallback when cache misses, REST fallback when GraphQL fails, error handling for all fallbacks (minimum 4 tests)
- [ ] T031 [P] [US5] Create or extend `solune/backend/tests/unit/test_webhooks.py` — test HMAC signature validation from `solune/backend/src/api/webhooks.py`: valid signature passes, invalid signature returns 401/403, missing `X-Hub-Signature-256` header handled, replay protection via `_processed_delivery_ids` (minimum 3 tests)
- [ ] T032 [P] [US5] Create `solune/backend/tests/unit/test_presets.py` — test preset catalog from `solune/backend/src/services/tools/presets.py`: `_PRESETS` tuple iteration and `McpPresetResponse` field validation, filtering by name or category (minimum 2 tests)
- [ ] T033 [P] [US5] Create or extend `solune/backend/tests/unit/test_encryption.py` — test Fernet encryption from `solune/backend/src/services/encryption.py`: encrypt-then-decrypt roundtrip preserves plaintext, invalid key raises appropriate error (minimum 2 tests)
- [ ] T034 [P] [US5] Create `solune/backend/tests/unit/test_pipeline_state_store.py` — test restart survivability from `solune/backend/src/services/pipeline_state_store.py`: SQLite persistence across simulated restart, state recovery, lock re-initialization (minimum 2 tests)

### Frontend Tests for User Story 5

- [ ] T035 [P] [US5] Extend `solune/frontend/src/services/api.test.ts` — test authenticated request helper: correct `Authorization` header attached, retry on 401 response, retry on network error (minimum 3 tests)
- [ ] T036 [P] [US5] Add axe accessibility assertion to at least one page-level component test in `solune/frontend/src/pages/` — import `jest-axe`, render component, assert `expect(await axe(container)).toHaveNoViolations()` (minimum 1 test per page component)
- [ ] T037 [US5] Identify hooks in `solune/frontend/src/hooks/` with zero test coverage and add basic happy-path plus error-case tests for at least one uncovered hook (minimum 2 tests per hook)

### Verification for User Story 5

- [ ] T038 [US5] Run `uv run pytest tests/ --cov=src --cov-report=term-missing -q --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency` from `solune/backend/` and compare coverage to baseline — confirm >= 10pp increase in targeted modules
- [ ] T039 [US5] Run `npx vitest run --coverage` from `solune/frontend/` and confirm coverage thresholds still met with new tests
- [ ] T040 [US5] Run `grep -rn "\.skip\|\.todo\|xfail\|xit\b\|xdescribe" solune/backend/tests/ solune/frontend/src/` and confirm zero new unconditional skip markers introduced

**Checkpoint**: US5 complete — net-new coverage added, coverage increase verified, zero new skips

---

## Phase 8: User Story 6 — Validate Full Suite and CI Green (Priority: P3)

**Goal**: Run all quality gates end-to-end and confirm CI passes with zero unconditional skip markers remaining

**Independent Test**: Push to CI and confirm all jobs exit 0

### Implementation for User Story 6

- [ ] T041 [US6] Run `uv run ruff check src/ tests/` from `solune/backend/` and confirm zero lint errors
- [ ] T042 [US6] Run `uv run ruff format --check src/ tests/` from `solune/backend/` and confirm zero format violations
- [ ] T043 [US6] Run `uv run pyright src/` from `solune/backend/` and confirm zero type errors
- [ ] T044 [US6] Run `uv run pytest tests/ --cov=src --cov-fail-under=75 -q --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency` from `solune/backend/` and confirm all pass with coverage >= 75%
- [ ] T045 [P] [US6] Run `npm run lint` from `solune/frontend/` and confirm zero lint errors
- [ ] T046 [P] [US6] Run `npm run type-check` from `solune/frontend/` and confirm zero type errors
- [ ] T047 [US6] Run `npm run test -- --pool=forks` from `solune/frontend/` and confirm all tests pass
- [ ] T048 [US6] Run `npm run build` from `solune/frontend/` and confirm build succeeds
- [ ] T049 [US6] Run `npx playwright test --project=chromium` from `solune/frontend/` — E2E tests pass (with continue-on-error for missing infrastructure)
- [ ] T050 [US6] Update `solune/CHANGELOG.md` under `[Unreleased]` with `Fixed` entries for any production bugs discovered and fixed during the uplift
- [ ] T051 [US6] Push all changes and verify CI pipeline is green — all jobs exit 0

**Checkpoint**: US6 complete — full validation passed, CI green, zero unconditional skip markers

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final documentation and cleanup

- [ ] T052 [P] Verify `specs/020-uplift-solune-testing/data-model.md` skip inventory tables match final state of codebase
- [ ] T053 [P] Verify `.specify/memory/test-skip-inventory.md` is accurate and committed
- [ ] T054 Run `specs/020-uplift-solune-testing/quickstart.md` validation commands end-to-end to confirm the developer guide is accurate

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (audit informs what infrastructure changes are needed) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — backend skip verification
- **US2 (Phase 4)**: Depends on Phase 2 — backend infrastructure change (`fail_under`)
- **US3 (Phase 5)**: Depends on Phase 2 — frontend infrastructure verification
- **US4 (Phase 6)**: Depends on Phase 2 — frontend skip verification and useAuth stability
- **US5 (Phase 7)**: Depends on US1, US2, US3, US4 — all skips verified and infrastructure stable before adding net-new tests
- **US6 (Phase 8)**: Depends on US5 — all changes complete before full validation
- **Polish (Phase 9)**: Depends on US6 — documentation updated after all changes verified

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **US2 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **US3 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **US4 (P2)**: Can start after Foundational (Phase 2) — No dependencies on P1 stories
- **US5 (P2)**: Depends on US1–US4 completion (infrastructure must be stable and skips verified before adding tests)
- **US6 (P3)**: Depends on US5 completion (all changes must be complete before final validation)

### Within Each User Story

- Verification tasks before code changes (confirm existing state)
- Configuration changes before test runs
- Tests validate each change immediately
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1**: T001 and T002 can run in parallel (backend vs. frontend audits)
- **Phase 2**: T005–T011 can all run in parallel (independent infrastructure verifications)
- **Phase 3–6**: US1, US2, US3, US4 can all start in parallel after Phase 2 (independent stories)
- **Phase 7**: T030–T037 (all new test file creations) are marked [P] and can run in parallel (different files, no dependencies)
- **Phase 8**: T041–T043 and T045–T046 can run in parallel (backend lint/format/type vs. frontend lint/type)
- **Phase 9**: T052–T053 can run in parallel (different documentation files)

---

## Parallel Example: User Story 5 (Net-New Coverage)

```bash
# Launch all backend test creations together (different files, no dependencies):
Task: "T030 [P] [US5] Create test_resolve_repository.py"
Task: "T031 [P] [US5] Create/extend test_webhooks.py"
Task: "T032 [P] [US5] Create test_presets.py"
Task: "T033 [P] [US5] Create/extend test_encryption.py"
Task: "T034 [P] [US5] Create test_pipeline_state_store.py"

# Launch frontend test additions in parallel (different files):
Task: "T035 [P] [US5] Extend api.test.ts"
Task: "T036 [P] [US5] Add axe assertions to page tests"

# After all tests created, run verification sequentially:
Task: "T038 [US5] Backend coverage comparison"
Task: "T039 [US5] Frontend coverage verification"
Task: "T040 [US5] Skip marker audit"
```

---

## Implementation Strategy

### MVP First (User Stories 1–3 Only)

1. Complete Phase 1: Setup (audit skip markers)
2. Complete Phase 2: Foundational (verify infrastructure)
3. Complete Phase 3: US1 — Verify backend skips are all conditional
4. Complete Phase 4: US2 — Add `fail_under = 70` coverage enforcement
5. Complete Phase 5: US3 — Verify frontend Vitest infrastructure
6. **STOP and VALIDATE**: All P1 stories independently verified

### Incremental Delivery

1. Complete Setup + Foundational → Infrastructure verified
2. Add US1 + US2 + US3 → Backend and frontend infrastructure hardened → Validate (MVP!)
3. Add US4 → Frontend E2E and useAuth verified → Validate
4. Add US5 → Net-new coverage added → Validate coverage increase
5. Add US6 → Full suite validation → CI green → Deploy/Merge
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (backend skips) + US2 (backend infrastructure)
   - Developer B: US3 (frontend infrastructure) + US4 (frontend skips)
3. Once US1–US4 complete:
   - Developer A: US5 backend tests (T030–T034)
   - Developer B: US5 frontend tests (T035–T037)
4. Developer A or B: US6 full validation

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 54 |
| **Phase 1 (Setup)** | 4 tasks |
| **Phase 2 (Foundational)** | 7 tasks |
| **US1 — Backend Skips (P1)** | 7 tasks |
| **US2 — Backend Infrastructure (P1)** | 3 tasks |
| **US3 — Frontend Infrastructure (P1)** | 2 tasks |
| **US4 — Frontend E2E + useAuth (P2)** | 6 tasks |
| **US5 — Net-New Coverage (P2)** | 11 tasks |
| **US6 — Full Validation (P3)** | 11 tasks |
| **Phase 9 (Polish)** | 3 tasks |
| **Parallel Opportunities** | 14 tasks marked [P] |
| **Suggested MVP Scope** | Setup + Foundational + US1 + US2 + US3 (23 tasks) |

---

## Notes

- [P] tasks = different files, no dependencies — safe to run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and verifiable
- All conditional `pytest.skip()` / `test.skip()` infrastructure guards are intentionally kept per research.md findings
- Commit after each task or logical group
- Stop at any checkpoint to validate the story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
