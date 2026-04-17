# Tasks: Bug Basher

**Input**: Design documents from `/specs/001-bug-basher/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md, contracts/

**Tests**: Tests are **required** — FR-003 mandates at least one regression test per bug fix.

**Organization**: Tasks are grouped by user story (bug category) to enable independent, prioritized execution of each audit phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/frontend/src/`
- **Backend tests**: `solune/backend/tests/`
- **Frontend tests**: `solune/frontend/src/__tests__/`, co-located `*.test.ts(x)` files
- **Scripts**: `solune/scripts/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish baseline state — run all existing tools and capture current pass/fail status before making any changes

- [ ] T001 Run `uv sync --locked --extra dev` in solune/backend/ to ensure all backend dependencies are installed
- [ ] T002 Run `npm ci` in solune/frontend/ to ensure all frontend dependencies are installed
- [ ] T003 [P] Run `uv run bandit -r src/ -ll -ii --skip B104` in solune/backend/ and save output as baseline security scan
- [ ] T004 [P] Run `uv run ruff check src tests` in solune/backend/ and save output as baseline lint report
- [ ] T005 [P] Run `uv run pyright src` in solune/backend/ and save output as baseline type-check report
- [ ] T006 [P] Run `uv run pytest --cov=src --cov-report=term-missing --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency` in solune/backend/ and save output as baseline test/coverage report
- [ ] T007 [P] Run `npm run lint` in solune/frontend/ and save output as baseline frontend lint report
- [ ] T008 [P] Run `npm run type-check` in solune/frontend/ and save output as baseline frontend type-check report
- [ ] T009 [P] Run `npm run test` in solune/frontend/ and save output as baseline frontend test report
- [ ] T010 [P] Run `bash solune/scripts/check-suppressions.sh` from repo root and save output as baseline suppression guard report
- [ ] T011 Grep entire repository for hardcoded secrets, API keys, tokens, and passwords; save output as secrets scan baseline

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the audit methodology and reporting structure that ALL user story phases will use

**⚠️ CRITICAL**: No audit work can begin until this phase is complete

- [ ] T012 Review specs/001-bug-basher/contracts/security-checklist.md and internalize all audit areas
- [ ] T013 [P] Review specs/001-bug-basher/contracts/runtime-checklist.md and internalize all audit areas
- [ ] T014 [P] Review specs/001-bug-basher/contracts/logic-checklist.md and internalize all audit areas
- [ ] T015 [P] Review specs/001-bug-basher/contracts/test-quality-checklist.md and internalize all audit areas
- [ ] T016 [P] Review specs/001-bug-basher/contracts/code-quality-checklist.md and internalize all audit areas
- [ ] T017 Review specs/001-bug-basher/research.md for architecture boundary rules (R3) and mock pitfalls (R5) that constrain all fixes

**Checkpoint**: Audit methodology loaded — phase-specific audit work can now begin in priority order

---

## Phase 3: User Story 1 — Security Vulnerability Audit (Priority: P1) 🎯 MVP

**Goal**: Identify and fix all security vulnerabilities across the entire codebase, or flag ambiguous ones with `TODO(bug-bash)` comments

**Independent Test**: Run full backend + frontend test suite plus new regression tests; verify no secrets/tokens in source; verify bandit + ESLint security plugin pass clean

### Automated Security Scanning for US1

- [ ] T018 [US1] Run `uv run bandit -r src/ -ll -ii --skip B104` in solune/backend/ and triage each finding — fix obvious issues, flag ambiguous ones
- [ ] T019 [P] [US1] Run `uv run pip-audit .` in solune/backend/ and triage dependency advisories
- [ ] T020 [P] [US1] Run `npm run lint` in solune/frontend/ focusing on security plugin findings and triage each
- [ ] T021 [P] [US1] Grep entire codebase for hardcoded secrets: API keys, tokens, passwords, private keys in source and config files

### Authentication & Authorization Audit for US1

- [ ] T022 [US1] Audit solune/backend/src/api/auth.py — verify all auth endpoints validate tokens correctly; fix + regression test per finding
- [ ] T023 [P] [US1] Audit solune/backend/src/middleware/admin_guard.py — verify admin-only routes are properly guarded; fix + regression test per finding
- [ ] T024 [P] [US1] Audit solune/backend/src/middleware/csrf.py — verify CSRF protection covers all state-changing routes; fix + regression test per finding
- [ ] T025 [P] [US1] Audit solune/backend/src/services/github_auth.py — verify OAuth flow has no bypasses; fix + regression test per finding
- [ ] T026 [P] [US1] Audit solune/backend/src/services/session_store.py — verify session tokens are properly validated and expired; fix + regression test per finding

### Input Validation Audit for US1

- [ ] T027 [US1] Audit all API endpoints in solune/backend/src/api/ — verify request bodies validated via Pydantic models; fix + regression test per finding
- [ ] T028 [P] [US1] Audit solune/backend/src/api/webhooks.py — verify webhook payloads validated before processing; fix + regression test per finding
- [ ] T029 [P] [US1] Audit solune/backend/src/services/chat_agent.py — verify user input sanitized before LLM calls; fix + regression test per finding
- [ ] T030 [P] [US1] Audit solune/backend/src/api/signal.py — verify Signal bridge inputs validated; fix + regression test per finding

### Cryptography & Secrets Audit for US1

- [ ] T031 [US1] Audit solune/backend/src/services/encryption.py — verify secure algorithms and key management; fix + regression test per finding
- [ ] T032 [P] [US1] Audit solune/backend/src/config.py — verify no secrets hardcoded; all use environment variables; fix + regression test per finding

### Network Security Audit for US1

- [ ] T033 [US1] Audit solune/backend/src/middleware/csp.py — verify Content Security Policy is restrictive; fix + regression test per finding
- [ ] T034 [P] [US1] Audit solune/backend/src/middleware/rate_limit.py — verify rate limiting covers sensitive endpoints; fix + regression test per finding
- [ ] T035 [P] [US1] Audit solune/backend/src/services/mcp_server/auth.py — verify MCP server authentication; fix + regression test per finding

### Frontend Security Audit for US1

- [ ] T036 [US1] Audit solune/frontend/src/ for dangerouslySetInnerHTML usage without sanitization; fix + regression test per finding
- [ ] T037 [P] [US1] Audit solune/frontend/src/ for API tokens stored in localStorage (should use httpOnly cookies or memory); fix + regression test per finding
- [ ] T038 [P] [US1] Audit solune/frontend/src/ for user-supplied data not escaped in rendered output; fix + regression test per finding

### US1 Validation

- [ ] T039 [US1] Run full backend validation: `uv run pytest --cov=src --cov-report=term-missing --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency` + `uv run ruff check src tests` + `uv run bandit -r src/ -ll -ii --skip B104` — all must pass
- [ ] T040 [US1] Run full frontend validation: `npm run test` + `npm run lint` + `npm run type-check` — all must pass

**Checkpoint**: All security vulnerabilities fixed or flagged — test suite passes with all new regression tests

---

## Phase 4: User Story 2 — Runtime Error Resolution (Priority: P2)

**Goal**: Identify and fix all runtime errors (unhandled exceptions, race conditions, null references, resource leaks, missing imports) across the entire codebase

**Independent Test**: Exercise affected code paths through unit tests; verify no unhandled exceptions or resource leaks occur

### Automated Runtime Scanning for US2

- [ ] T041 [US2] Run `uv run pyright src` in solune/backend/ and triage all type errors — fix obvious issues, flag ambiguous ones
- [ ] T042 [P] [US2] Run `npm run type-check` in solune/frontend/ and triage all TypeScript errors — fix obvious issues, flag ambiguous ones

### Unhandled Exception Audit for US2

- [ ] T043 [US2] Audit all async handlers in solune/backend/src/api/ — verify try/except covers external calls; fix + regression test per finding
- [ ] T044 [P] [US2] Audit solune/backend/src/services/chat_agent.py — verify LLM streaming errors handled; fix + regression test per finding
- [ ] T045 [P] [US2] Audit solune/backend/src/services/copilot_polling/polling_loop.py — verify polling errors don't crash the service; fix + regression test per finding
- [ ] T046 [P] [US2] Audit solune/backend/src/services/signal_bridge.py — verify WebSocket disconnection handled gracefully; fix + regression test per finding
- [ ] T047 [P] [US2] Audit solune/backend/src/services/github_projects/ (all files) — verify GitHub API errors handled (rate limits, 404s, 500s); fix + regression test per finding

### Resource Leak Audit for US2

- [ ] T048 [US2] Audit solune/backend/src/services/database.py — verify all database connections properly closed; fix + regression test per finding
- [ ] T049 [P] [US2] Audit solune/backend/src/services/cache.py — verify cached resources have TTL or cleanup; fix + regression test per finding
- [ ] T050 [P] [US2] Audit all httpx client usage across solune/backend/src/ — verify clients used as context managers or properly closed; fix + regression test per finding
- [ ] T051 [P] [US2] Audit solune/backend/src/services/websocket.py — verify WebSocket connections cleaned up on disconnect; fix + regression test per finding
- [ ] T052 [P] [US2] Audit all file handle operations across solune/backend/src/ — verify context managers (`with`) used; fix + regression test per finding

### Race Condition Audit for US2

- [ ] T053 [US2] Audit solune/backend/src/services/task_registry.py — verify concurrent task creation is safe; fix + regression test per finding
- [ ] T054 [P] [US2] Audit solune/backend/src/services/copilot_polling/state.py — verify state updates are atomic; fix + regression test per finding
- [ ] T055 [P] [US2] Audit solune/backend/src/services/pipeline_state_store.py — verify pipeline state transitions safe; fix + regression test per finding

### Null/None Reference Audit for US2

- [ ] T056 [US2] Audit solune/backend/src/services/ for optional return values without caller None-checks; fix + regression test per finding
- [ ] T057 [P] [US2] Audit solune/backend/src/ for dictionary access without `.get()` or `in` guards; fix + regression test per finding
- [ ] T058 [P] [US2] Audit solune/frontend/src/ for missing optional chaining (`?.`) on nullable objects; fix + regression test per finding

### Frontend Runtime Audit for US2

- [ ] T059 [US2] Audit solune/frontend/src/hooks/ for stale closure issues in React hooks; fix + regression test per finding
- [ ] T060 [P] [US2] Audit solune/frontend/src/services/api.ts for unhandled promise rejections; fix + regression test per finding

### Missing Import Audit for US2

- [ ] T061 [US2] Verify all type hints in solune/backend/src/ reference imported types; fix + regression test per finding
- [ ] T062 [P] [US2] Verify all service dependencies properly imported at module level in solune/backend/src/; fix + regression test per finding

### US2 Validation

- [ ] T063 [US2] Run full backend validation: `uv run pytest --cov=src --cov-report=term-missing --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency` + `uv run ruff check src tests` + `uv run pyright src` — all must pass
- [ ] T064 [US2] Run full frontend validation: `npm run test` + `npm run lint` + `npm run type-check` — all must pass

**Checkpoint**: All runtime errors fixed or flagged — test suite passes with all new regression tests

---

## Phase 5: User Story 3 — Logic Bug Correction (Priority: P3)

**Goal**: Identify and fix all logic bugs (incorrect state transitions, off-by-one errors, wrong return values, broken control flow) across the entire codebase

**Independent Test**: Targeted unit tests assert correct behavior for specific logic being fixed, including boundary conditions

### State Transition Audit for US3

- [ ] T065 [US3] Audit solune/backend/src/services/workflow_orchestrator/transitions.py — verify all state transitions are valid; fix + regression test per finding
- [ ] T066 [P] [US3] Audit solune/backend/src/services/workflow_orchestrator/orchestrator.py — verify orchestrator state machine correctness; fix + regression test per finding
- [ ] T067 [P] [US3] Audit solune/backend/src/services/copilot_polling/state.py — verify polling state transitions; fix + regression test per finding
- [ ] T068 [P] [US3] Audit solune/backend/src/services/copilot_polling/state_validation.py — verify state validation logic; fix + regression test per finding
- [ ] T069 [P] [US3] Audit solune/backend/src/services/pipelines/ (all files) — verify pipeline stage transitions match preset definitions; fix + regression test per finding

### Off-by-One Error Audit for US3

- [ ] T070 [US3] Audit solune/backend/src/services/pagination.py — verify page calculations (0-indexed vs 1-indexed); fix + regression test per finding
- [ ] T071 [P] [US3] Audit solune/backend/src/ for loops with explicit index manipulation — verify boundary conditions; fix + regression test per finding
- [ ] T072 [P] [US3] Audit solune/frontend/src/ for array index calculations in list rendering; fix + regression test per finding

### API Call Correctness Audit for US3

- [ ] T073 [US3] Audit solune/backend/src/services/github_projects/ — verify GraphQL queries return expected fields; fix + regression test per finding
- [ ] T074 [P] [US3] Audit solune/backend/src/services/copilot_polling/ — verify Copilot API calls use correct parameters; fix + regression test per finding
- [ ] T075 [P] [US3] Audit solune/frontend/src/services/api.ts — verify request/response shapes match backend contracts; fix + regression test per finding

### Data Consistency Audit for US3

- [ ] T076 [US3] Audit solune/backend/src/constants.py — verify constant values are consistent across all usage sites; fix + regression test per finding
- [ ] T077 [P] [US3] Audit pipeline presets in solune/backend/src/services/pipelines/service.py — verify stage labels match between presets and status columns (note: "In progress" vs "In Progress" is intentional per research.md); fix + regression test per finding
- [ ] T078 [P] [US3] Audit solune/frontend/src/ Zustand stores — verify stores stay in sync with API responses; fix + regression test per finding

### Control Flow Audit for US3

- [ ] T079 [US3] Audit solune/backend/src/services/copilot_polling/recovery.py — verify recovery logic handles all failure modes; fix + regression test per finding
- [ ] T080 [P] [US3] Audit solune/backend/src/services/collision_resolver.py — verify collision detection/resolution is correct; fix + regression test per finding
- [ ] T081 [P] [US3] Audit error recovery paths across solune/backend/src/services/ — verify retry logic has proper backoff and termination; fix + regression test per finding

### Return Value Audit for US3

- [ ] T082 [US3] Audit functions returning Optional types in solune/backend/src/services/ — verify all return paths covered; fix + regression test per finding
- [ ] T083 [P] [US3] Audit boolean logic in solune/backend/src/ — verify negation and compound conditions correct; fix + regression test per finding
- [ ] T084 [P] [US3] Audit solune/frontend/src/hooks/ — verify memoization dependencies are complete (useMemo/useCallback dep arrays); fix + regression test per finding

### US3 Validation

- [ ] T085 [US3] Run full backend validation: `uv run pytest --cov=src --cov-report=term-missing --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency` + `uv run ruff check src tests` — all must pass
- [ ] T086 [US3] Run full frontend validation: `npm run test` + `npm run lint` + `npm run type-check` — all must pass

**Checkpoint**: All logic bugs fixed or flagged — test suite passes with all new regression tests

---

## Phase 6: User Story 4 — Test Quality Improvement (Priority: P4)

**Goal**: Fill test gaps and fix low-quality tests so the test suite provides meaningful coverage and catches real regressions

**Independent Test**: Run improved test suite; confirm increased code coverage, meaningful assertions, and no mock leaks into production paths

### Coverage Analysis for US4

- [ ] T087 [US4] Run `uv run pytest --cov=src --cov-report=term-missing --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency` in solune/backend/ — identify files below 80% coverage
- [ ] T088 [P] [US4] Run `npm run test -- --coverage` in solune/frontend/ — identify untested components and hooks

### Tests That Pass for Wrong Reason — US4

- [ ] T089 [US4] Audit solune/backend/tests/unit/ for tests that mock the code under test (instead of its dependencies); fix by replacing over-mocking with real logic execution + regression test
- [ ] T090 [P] [US4] Audit solune/backend/tests/unit/ for tests where mock return value matches expected output coincidentally; fix assertions to be meaningful + regression test
- [ ] T091 [P] [US4] Audit solune/backend/tests/unit/ for tests that assert only on mock call counts instead of behavior; strengthen assertions + regression test

### Mock Leak Audit for US4

- [ ] T092 [US4] Audit solune/backend/tests/ for MagicMock objects used as file paths or database paths (known pitfall per research.md R5); fix mock scoping + regression test
- [ ] T093 [P] [US4] Audit solune/backend/tests/ for unscoped patches (task_registry.create_task mock affecting coalesced_fetch per research.md R5); fix scope + regression test
- [ ] T094 [P] [US4] Audit solune/frontend/src/ test files for mocks that don't clean up after test completion; fix cleanup + regression test

### Weak Assertion Audit for US4

- [ ] T095 [US4] Audit solune/backend/tests/ for `assert True`, `assert 1 == 1`, or always-true assertions; replace with meaningful checks + regression test
- [ ] T096 [P] [US4] Audit solune/backend/tests/ for try/except blocks that catch and ignore assertion errors; fix by removing swallowed assertions + regression test
- [ ] T097 [P] [US4] Audit solune/backend/tests/ for assertions that only check mock was called but not with correct arguments; strengthen assertions + regression test

### Missing Edge Case Coverage for US4

- [ ] T098 [US4] Audit solune/backend/src/services/ for error paths without test coverage — add edge case tests for exception scenarios
- [ ] T099 [P] [US4] Audit solune/backend/src/api/ for untested error responses (400, 404, 500) — add tests for error paths
- [ ] T100 [P] [US4] Audit solune/frontend/src/hooks/ for untested error/loading states — add tests for edge cases
- [ ] T101 [P] [US4] Audit for empty input handling (empty lists, empty strings, None values) without test coverage — add boundary tests

### Test Naming and Organization for US4

- [ ] T102 [US4] Audit solune/backend/tests/ for tests named `test_something` that don't test what the name describes; fix names + regression test
- [ ] T103 [P] [US4] Audit solune/backend/tests/ for duplicate test logic that could be parameterized; consolidate with `@pytest.mark.parametrize`

### US4 Validation

- [ ] T104 [US4] Run full backend validation: `uv run pytest --cov=src --cov-report=term-missing --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency` — verify improved coverage + all tests pass
- [ ] T105 [US4] Run full frontend validation: `npm run test` — verify all tests pass including new edge case tests

**Checkpoint**: Test quality improved — all tests meaningful, no mock leaks, improved coverage, full suite passes

---

## Phase 7: User Story 5 — Code Quality Cleanup (Priority: P5)

**Goal**: Remove dead code, fix silent failures, consolidate duplication, and clean up hardcoded values across the entire codebase

**Independent Test**: Verify removed dead code doesn't break tests; verify previously silent failures now produce error messages

### Dead Code Audit for US5

- [ ] T106 [US5] Audit solune/backend/src/ for unused imports (verify ruff catches them all); fix + verify tests pass
- [ ] T107 [P] [US5] Audit solune/backend/src/ for unused functions or methods not called anywhere; remove + verify tests pass
- [ ] T108 [P] [US5] Audit solune/backend/src/ for unreachable code after return/raise/break/continue; remove + verify tests pass
- [ ] T109 [P] [US5] Audit solune/frontend/src/ for components imported but never rendered; remove + verify tests pass
- [ ] T110 [P] [US5] Audit entire codebase for commented-out code blocks that should be removed; remove + verify tests pass

### Duplicated Logic Audit for US5

- [ ] T111 [US5] Audit solune/backend/src/api/ for similar validation logic repeated across endpoints; consolidate without changing public API + regression test
- [ ] T112 [P] [US5] Audit solune/backend/src/services/ for duplicate error handling patterns; extract shared patterns + regression test
- [ ] T113 [P] [US5] Audit solune/frontend/src/components/ for near-identical logic (candidates for shared hooks); consolidate + regression test
- [ ] T114 [P] [US5] Audit for configuration values defined in multiple places; centralize + regression test

### Hardcoded Values Audit for US5

- [ ] T115 [US5] Audit solune/backend/src/ for magic numbers without named constants; extract to solune/backend/src/constants.py + regression test
- [ ] T116 [P] [US5] Audit solune/backend/src/ for hardcoded URLs or paths that should be configurable; extract to solune/backend/src/config.py + regression test
- [ ] T117 [P] [US5] Audit solune/backend/src/ for hardcoded timeout values; extract to configuration + regression test
- [ ] T118 [P] [US5] Audit solune/frontend/src/ for hardcoded API base URLs; extract to constants + regression test

### Silent Failure Audit for US5

- [ ] T119 [US5] Audit solune/backend/src/ for bare `except:` or `except Exception:` without logging or re-raising; add error reporting + regression test
- [ ] T120 [P] [US5] Audit solune/frontend/src/ for empty catch blocks; add error reporting + regression test
- [ ] T121 [P] [US5] Audit solune/backend/src/ for functions returning None on error without indication; add error reporting + regression test
- [ ] T122 [P] [US5] Audit solune/backend/src/ for missing error messages in exception handlers; add messages + regression test

### Code Clarity Audit for US5

- [ ] T123 [US5] Audit solune/backend/src/ for overly complex conditionals; simplify with early returns + regression test
- [ ] T124 [P] [US5] Audit solune/backend/src/ for missing type hints on public function signatures; add hints + verify pyright passes
- [ ] T125 [P] [US5] Audit solune/frontend/src/ for use of `any` type where a specific type is known; add proper types + verify tsc passes
- [ ] T126 [P] [US5] Audit for `# type: ignore` and `# noqa` without justification comments (per check-suppressions.sh); add reason or fix underlying issue

### US5 Validation

- [ ] T127 [US5] Run full backend validation: `uv run ruff check src tests` + `uv run ruff format --check src tests` + `uv run pyright src` + `uv run pytest --cov=src --cov-report=term-missing --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency` — all must pass
- [ ] T128 [US5] Run full frontend validation: `npm run lint` + `npm run type-check` + `npm run test` — all must pass

**Checkpoint**: Code quality improved — no dead code, no silent failures, reduced duplication, full suite passes

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all phases and summary report generation

- [ ] T129 Run full backend test suite with coverage: `uv run pytest --cov=src --cov-report=term-missing --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency` in solune/backend/
- [ ] T130 [P] Run full frontend test suite: `npm run test` in solune/frontend/
- [ ] T131 [P] Run all backend linters: `uv run ruff check src tests && uv run ruff format --check src tests` in solune/backend/
- [ ] T132 [P] Run backend security scan: `uv run bandit -r src/ -ll -ii --skip B104` in solune/backend/
- [ ] T133 [P] Run backend type check: `uv run pyright src` in solune/backend/
- [ ] T134 [P] Run frontend lint: `npm run lint` in solune/frontend/
- [ ] T135 [P] Run frontend type check: `npm run type-check` in solune/frontend/
- [ ] T136 Run suppression guard: `bash solune/scripts/check-suppressions.sh` from repo root
- [ ] T137 Produce final summary table per FR-011 format: sequential #, File, Line(s), Category, Description, Status (✅ Fixed or ⚠️ Flagged)
- [ ] T138 Verify summary table excludes files with no bugs per FR-012
- [ ] T139 Verify every fix has at least one regression test per FR-003
- [ ] T140 Verify no new dependencies added per FR-008
- [ ] T141 Verify no public API surface changes per constraint
- [ ] T142 Run quickstart.md validation: execute the final validation steps from specs/001-bug-basher/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all audit phases
- **US1: Security (Phase 3)**: Depends on Foundational — MUST complete before US2 (per research.md R2: security fixes first to avoid reintroducing vulnerabilities)
- **US2: Runtime (Phase 4)**: Depends on US1 completion (security fixes may resolve related runtime errors)
- **US3: Logic (Phase 5)**: Depends on US2 completion (runtime fixes may affect logic evaluation)
- **US4: Test Quality (Phase 6)**: Depends on US3 completion (all source fixes must be done before improving tests)
- **US5: Code Quality (Phase 7)**: Depends on US4 completion (test improvements must be done before removing code)
- **Polish (Phase 8)**: Depends on ALL user story phases being complete

### User Story Dependencies

- **US1 Security (P1)**: Start after Foundational (Phase 2) — must complete before US2 begins
- **US2 Runtime (P2)**: Start after US1 completes — security fixes may resolve runtime issues
- **US3 Logic (P3)**: Start after US2 completes — runtime fixes may affect logic paths
- **US4 Test Quality (P4)**: Start after US3 completes — all source code fixes finalized before test review
- **US5 Code Quality (P5)**: Start after US4 completes — test improvements finalized before dead code removal

> **Note**: Unlike typical feature development where user stories run in parallel, the bug bash phases are **sequential by design** (per research.md R2). Fixes in earlier categories can affect later categories, so strict priority ordering prevents rework.

### Within Each User Story

- Automated scanning tasks FIRST to identify findings
- Manual audit tasks SECOND, organized by sub-category
- Each finding: fix source code + add regression test (or add TODO(bug-bash) flag)
- Validation LAST: full test suite + linter pass required before proceeding

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T003–T011)
- All Foundational tasks marked [P] can run in parallel (T013–T016)
- Within each User Story phase, tasks auditing different files/directories marked [P] can run in parallel
- All Polish validation tasks marked [P] can run in parallel (T130–T135)

---

## Parallel Example: User Story 1 (Security)

```bash
# Launch automated scans in parallel:
Task T019: "Run pip-audit in solune/backend/"
Task T020: "Run ESLint security in solune/frontend/"
Task T021: "Grep for hardcoded secrets across codebase"

# Launch independent file audits in parallel:
Task T023: "Audit admin_guard.py"
Task T024: "Audit csrf.py"
Task T025: "Audit github_auth.py"
Task T026: "Audit session_store.py"
```

## Parallel Example: User Story 2 (Runtime)

```bash
# Launch independent audits in parallel:
Task T044: "Audit chat_agent.py for unhandled exceptions"
Task T045: "Audit polling_loop.py for crash-safety"
Task T046: "Audit signal_bridge.py for WebSocket cleanup"
Task T047: "Audit github_projects/ for API error handling"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (install deps, run baselines)
2. Complete Phase 2: Foundational (internalize checklists and constraints)
3. Complete Phase 3: User Story 1 — Security Vulnerability Audit
4. **STOP and VALIDATE**: Full test suite + linters + bandit must pass
5. Security fixes alone represent the highest-value increment

### Incremental Delivery

1. Complete Setup + Foundational → Audit methodology ready
2. Complete US1 Security → Security vulnerabilities resolved (MVP!)
3. Complete US2 Runtime → Application stability improved
4. Complete US3 Logic → Correctness bugs resolved
5. Complete US4 Test Quality → Test suite strengthened
6. Complete US5 Code Quality → Technical debt reduced
7. Complete Polish → Final validation + summary table produced
8. Each phase adds value and validates independently before proceeding

### Sequential Execution (Required)

Per research.md R2, phases MUST execute sequentially in priority order:

1. Security (P1) FIRST — highest impact, may affect all other phases
2. Runtime (P2) SECOND — stability issues second only to security
3. Logic (P3) THIRD — correctness after stability
4. Test Quality (P4) FOURTH — strengthen tests after all source fixes
5. Code Quality (P5) FIFTH — cleanup after all fixes and test improvements

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in same phase
- [USn] label maps task to specific user story for traceability
- Tests are **required** per FR-003 — each bug fix must have at least one regression test
- Ambiguous issues: do NOT fix — add `TODO(bug-bash)` comment per research.md R6
- Architecture boundaries: respect import rules per research.md R3 (API layer must not import *_store modules)
- Mock pitfalls: beware task_registry.create_task affecting coalesced_fetch per research.md R5
- Known intentional inconsistency: "In progress" vs "In Progress" stage label is by design per research.md R3
- Frontend icon convention: import from `@/lib/icons`, not directly from `lucide-react`
- Suppressions must include `reason:` justification per check-suppressions.sh
- Commit messages must explain: what the bug was, why it is a bug, how the fix resolves it (FR-010)
- Avoid: vague tasks, same file conflicts, cross-story dependencies
- Stop at any checkpoint to validate independently
