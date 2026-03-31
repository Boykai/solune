# Tasks: Bug Basher — Full Codebase Review & Fix

**Input**: Design documents from `/specs/002-bug-basher/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Regression tests are REQUIRED per FR-003. Each fixed bug must have at least one regression test added. Tests are embedded within each review task (fix → update existing tests → add regression test → validate).

**Organization**: Tasks are grouped by user story / bug category to enable independent review and validation of each category. Categories follow priority order from the spec: Security (P1) → Runtime (P2) → Logic (P3) → Test Quality (P4) → Code Quality (P5) → Reporting (P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/frontend/src/`
- **Backend tests**: `solune/backend/tests/` (unit/, integration/, property/, concurrency/, fuzz/, chaos/, e2e/, performance/, architecture/)
- **Frontend tests**: `solune/frontend/src/` (co-located `*.test.ts(x)` files)

---

## Phase 1: Setup (Establish Baseline)

**Purpose**: Verify the codebase is in a known-good state before making any changes. Document any pre-existing failures as out-of-scope.

- [ ] T001 Establish backend baseline by running lint, format, and type checks in solune/backend/ (`uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run pyright src`)
- [ ] T002 [P] Establish backend test baseline by running unit tests in solune/backend/ (`uv run pytest tests/unit/ -x --timeout=120`)
- [ ] T003 [P] Establish frontend baseline by running lint, typecheck, test, and build in solune/frontend/ (`npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`)
- [ ] T004 [P] Run static security analysis baseline in solune/backend/ (`uv run bandit -r src -f json -o /tmp/bandit-report.json`)
- [ ] T005 Document any pre-existing failures as out-of-scope in a baseline report at /tmp/bug-bash-baseline.md

---

## Phase 2: Foundational (Static Analysis & Finding Identification)

**Purpose**: Use existing tooling to generate initial findings that inform the manual review phases. MUST complete before manual review begins.

**⚠️ CRITICAL**: No manual review tasks can begin until static analysis results are collected.

- [ ] T006 Analyze bandit security scan results from /tmp/bandit-report.json and triage findings by severity (High/Medium/Low) for solune/backend/src/
- [ ] T007 [P] Run ruff extended rule check (`uv run ruff check src --select=ALL`) in solune/backend/ and catalog findings by category (security, bugbear, complexity)
- [ ] T008 [P] Search for weak test patterns in solune/backend/tests/ — scan for `assert True`, `assert mock_*.called` without `assert_called_with()`, `MagicMock()` used as file paths, bare `except:`, tests with no assertions
- [ ] T009 [P] Search for potential security patterns in solune/backend/src/ — scan for hardcoded secrets, `eval()`, `exec()`, unvalidated redirects, `subprocess.call` with `shell=True`, unsanitized SQL
- [ ] T010 [P] Search for dead code patterns in solune/backend/src/ — scan for unused imports (F401), unreachable code after return/raise, commented-out code blocks, empty except/pass blocks
- [ ] T011 Compile triage list of all static analysis findings categorized by user story (Security/Runtime/Logic/Test Quality/Code Quality) to guide manual review phases

**Checkpoint**: Static analysis complete — manual review can now proceed by category

---

## Phase 3: User Story 1 — Security Vulnerability Remediation (Priority: P1) 🎯 MVP

**Goal**: Identify and fix all security vulnerabilities in the codebase — auth bypasses, injection risks, exposed secrets, insecure defaults, improper input validation.

**Independent Test**: Run the full backend test suite after all security fixes. Each fix has at least one regression test. Verify no security-related test failures. Run `bandit -r src` and confirm zero High/Medium findings.

### Backend Security Review

- [ ] T012 [P] [US1] Audit authentication middleware for bypass vulnerabilities in solune/backend/src/middleware/admin_guard.py — check role validation, session verification, header spoofing risks. Fix and add regression tests.
- [ ] T013 [P] [US1] Audit CSRF middleware for token validation weaknesses in solune/backend/src/middleware/csrf.py — check token generation, validation bypass, same-site cookie settings. Fix and add regression tests.
- [ ] T014 [P] [US1] Audit CSP middleware for header injection or misconfiguration in solune/backend/src/middleware/csp.py — check directive completeness, nonce handling, unsafe-inline risks. Fix and add regression tests.
- [ ] T015 [P] [US1] Audit rate limiting middleware for bypass vulnerabilities in solune/backend/src/middleware/rate_limit.py — check IP spoofing via headers, counter reset logic, exempt path handling. Fix and add regression tests.
- [ ] T016 [P] [US1] Audit request ID middleware for header injection in solune/backend/src/middleware/request_id.py — check user-supplied request ID validation, log injection risks. Fix and add regression tests.
- [ ] T017 [P] [US1] Audit encryption service for cryptographic weaknesses in solune/backend/src/services/encryption.py — check key management, Fernet usage, error handling on decrypt failure, key rotation. Fix and add regression tests.
- [ ] T018 [P] [US1] Audit GitHub OAuth flow for token exposure and redirect vulnerabilities in solune/backend/src/services/github_auth.py — check redirect URI validation, token exchange security, state parameter verification. Fix and add regression tests.
- [ ] T019 [P] [US1] Audit session store for session fixation and token exposure in solune/backend/src/services/session_store.py — check session persistence, token encryption at rest, session invalidation, cookie security flags. Fix and add regression tests.
- [ ] T020 [P] [US1] Audit auth API endpoints for authentication bypass in solune/backend/src/api/auth.py — check token endpoints, session creation, logout handling, error message information leakage. Fix and add regression tests.
- [ ] T021 [P] [US1] Audit MCP server authentication and rate limiting in solune/backend/src/services/mcp_server/auth.py — check token validation, rate limit enforcement, privilege escalation risks. Fix and add regression tests.
- [ ] T022 [P] [US1] Audit webhook endpoint for signature verification bypass in solune/backend/src/api/webhooks.py — check HMAC validation, timing attack resistance, payload sanitization. Fix and add regression tests.
- [ ] T023 [P] [US1] Audit application configuration for insecure defaults in solune/backend/src/config.py — check secret validation on startup, environment-specific settings, debug mode guards, default passwords. Fix and add regression tests.
- [ ] T024 [P] [US1] Audit logging utilities for sensitive data exposure in solune/backend/src/logging_utils.py — check token/secret redaction coverage, PII filtering, error message sanitization. Fix and add regression tests.
- [ ] T025 [P] [US1] Audit exception handlers and middleware ordering in solune/backend/src/main.py — check error responses for internal detail leakage, middleware stack order correctness, debug endpoint exposure. Fix and add regression tests.
- [ ] T026 [P] [US1] Audit dependency injection for session/auth bypass in solune/backend/src/dependencies.py — check session resolution, auth dependency chains, optional vs required auth. Fix and add regression tests.
- [ ] T027 [P] [US1] Audit input validation across all API endpoints in solune/backend/src/api/ — check Pydantic model validation completeness, path parameter injection, query parameter sanitization. Fix and add regression tests.
- [ ] T028 [P] [US1] Audit app template renderer for path traversal in solune/backend/src/services/template_files.py — check `os.path.realpath()` boundary enforcement, template file access controls. Fix and add regression tests.

### Frontend Security Review

- [ ] T029 [P] [US1] Audit frontend for XSS via `dangerouslySetInnerHTML` or unescaped rendering in solune/frontend/src/components/ — search all components for unsafe HTML rendering. Fix and add regression tests.
- [ ] T030 [P] [US1] Audit frontend API client services for unvalidated responses and credential exposure in solune/frontend/src/services/ — check response validation, token storage, CORS handling. Fix and add regression tests.
- [ ] T031 [P] [US1] Audit frontend route guards for authentication state bypass in solune/frontend/src/pages/ — check auth redirects, protected route enforcement, session expiry handling. Fix and add regression tests.

### Security Validation

- [ ] T032 [US1] Run full security validation after all US1 fixes — `uv run bandit -r src`, `uv run pytest tests/unit/ -x`, `uv run ruff check src tests` in solune/backend/. Iterate until all pass.

**Checkpoint**: All security vulnerabilities addressed. Backend test suite and security scans pass.

---

## Phase 4: User Story 2 — Runtime Error Elimination (Priority: P2)

**Goal**: Identify and fix all runtime errors — unhandled exceptions, race conditions, null references, missing imports, type errors, resource leaks.

**Independent Test**: Run the full test suite after all runtime fixes. Each fix has a regression test confirming the previously-failing code path now handles errors gracefully.

### Backend Runtime Review

- [ ] T033 [P] [US2] Audit database service for connection leaks and migration errors in solune/backend/src/services/database.py — check connection lifecycle, `async with` usage, migration exception handling, connection pool exhaustion. Fix and add regression tests.
- [ ] T034 [P] [US2] Audit cache service for TTL bugs and bounded collection overflow in solune/backend/src/services/cache.py — check TTL expiry edge cases, BoundedDict overflow handling, thread safety. Fix and add regression tests.
- [ ] T035 [P] [US2] Audit copilot polling loop for retry and timeout failures in solune/backend/src/services/copilot_polling/polling_loop.py — check retry logic, timeout handling, external API failure recovery. Fix and add regression tests.
- [ ] T036 [P] [US2] Audit copilot pipeline for race conditions and state corruption in solune/backend/src/services/copilot_polling/pipeline.py — check concurrent state updates, agent completion loop, `CancelledError` handling. Fix and add regression tests.
- [ ] T037 [P] [US2] Audit copilot recovery and state validation for error handling in solune/backend/src/services/copilot_polling/recovery.py and solune/backend/src/services/copilot_polling/state_validation.py — check recovery paths, grace period logic, state consistency. Fix and add regression tests.
- [ ] T038 [P] [US2] Audit copilot completion and helpers for null reference and type errors in solune/backend/src/services/copilot_polling/completion.py and solune/backend/src/services/copilot_polling/helpers.py — check None propagation, type coercions, optional field access. Fix and add regression tests.
- [ ] T039 [P] [US2] Audit workflow orchestrator for concurrent state update bugs in solune/backend/src/services/workflow_orchestrator/orchestrator.py — check state transitions, concurrent group updates, lock usage. Fix and add regression tests.
- [ ] T040 [P] [US2] Audit workflow orchestrator models for state machine edge cases in solune/backend/src/services/workflow_orchestrator/models.py — check `current_agent` skip logic, empty group handling, index bounds. Fix and add regression tests.
- [ ] T041 [P] [US2] Audit workflow orchestrator transitions for invalid state handling in solune/backend/src/services/workflow_orchestrator/transitions.py — check transition validation, error states, rollback on failure. Fix and add regression tests.
- [ ] T042 [P] [US2] Audit WebSocket service for connection cleanup on disconnect in solune/backend/src/services/websocket.py — check `finally` block cleanup, stale connection detection, concurrent send safety. Fix and add regression tests.
- [ ] T043 [P] [US2] Audit agent service for lifecycle management errors in solune/backend/src/services/agents/service.py — check agent creation/destruction, resource cleanup, exception propagation. Fix and add regression tests.
- [ ] T044 [P] [US2] Audit all httpx usage across solune/backend/src/services/ — check timeout configuration, response body consumption, connection pool cleanup, error handling on network failures. Fix and add regression tests.
- [ ] T045 [P] [US2] Audit remaining top-level services for unhandled exceptions in solune/backend/src/services/ — check activity_logger.py, alert_dispatcher.py, app_service.py, cleanup_service.py, chat_store.py, and other service files for missing try/except, None dereferences, missing awaits. Fix and add regression tests.
- [ ] T046 [P] [US2] Audit GitHub Projects integration services for API error handling in solune/backend/src/services/github_projects/ — check GraphQL error responses, pagination edge cases, null field handling. Fix and add regression tests.
- [ ] T047 [P] [US2] Audit MCP server for request handling errors in solune/backend/src/services/mcp_server/ (server.py, context.py, middleware.py, tools/) — check tool execution error handling, context propagation, middleware exception safety. Fix and add regression tests.

### Frontend Runtime Review

- [ ] T048 [P] [US2] Audit frontend hooks for stale closure bugs and missing cleanup in solune/frontend/src/hooks/ — check `useEffect` dependency arrays, cleanup functions, unhandled promise rejections. Fix and add regression tests.
- [ ] T049 [P] [US2] Audit frontend WebSocket integration for reconnection failures in solune/frontend/src/ — check reconnection logic, message parsing errors, connection state management. Fix and add regression tests.
- [ ] T050 [P] [US2] Audit frontend error boundaries and loading states in solune/frontend/src/components/ and solune/frontend/src/pages/ — check error boundary coverage, missing loading/error states, unhandled async errors. Fix and add regression tests.

### Runtime Validation

- [ ] T051 [US2] Run full runtime validation after all US2 fixes — `uv run pytest tests/unit/ -x`, `uv run pyright src`, `uv run ruff check src tests` in solune/backend/. Frontend: `npm run lint`, `npm run test`, `npm run build` in solune/frontend/. Iterate until all pass.

**Checkpoint**: All runtime errors addressed. Full test suite passes.

---

## Phase 5: User Story 3 — Logic Bug Correction (Priority: P3)

**Goal**: Identify and fix all logic bugs — incorrect state transitions, wrong API calls, off-by-one errors, data inconsistencies, broken control flow, incorrect return values.

**Independent Test**: Run the full test suite after all logic fixes. Each fix has a regression test that exercises the corrected logic path and verifies expected outputs.

### Backend Logic Review

- [ ] T052 [P] [US3] Audit workflow orchestrator state machine for incorrect transitions in solune/backend/src/services/workflow_orchestrator/models.py and solune/backend/src/services/workflow_orchestrator/transitions.py — check state transition sequences, guard conditions, terminal state handling. Fix and add regression tests.
- [ ] T053 [P] [US3] Audit copilot pipeline agent completion logic for off-by-one and ordering bugs in solune/backend/src/services/copilot_polling/pipeline.py — check `current_agents` iteration, grace period logic, `continue` vs `return None` semantics. Fix and add regression tests.
- [ ] T054 [P] [US3] Audit copilot agent output processing for incorrect parsing in solune/backend/src/services/copilot_polling/agent_output.py — check output extraction, status determination, edge case handling for empty/malformed output. Fix and add regression tests.
- [ ] T055 [P] [US3] Audit copilot auto-merge and label manager for incorrect API calls in solune/backend/src/services/copilot_polling/auto_merge.py and solune/backend/src/services/copilot_polling/label_manager.py — check merge conditions, label application logic, error handling. Fix and add regression tests.
- [ ] T056 [P] [US3] Audit copilot pipeline state service for data inconsistencies in solune/backend/src/services/copilot_polling/pipeline_state_service.py — check state persistence, read/write consistency, concurrent access handling. Fix and add regression tests.
- [ ] T057 [P] [US3] Audit agent service for incorrect lifecycle management logic in solune/backend/src/services/agents/service.py — check agent creation validation, state tracking, cleanup ordering. Fix and add regression tests.
- [ ] T058 [P] [US3] Audit pipeline service for CRUD operation logic errors in solune/backend/src/services/pipelines/service.py — check create/update/delete flows, validation, cascading operations. Fix and add regression tests.
- [ ] T059 [P] [US3] Audit workflow orchestrator configuration for incorrect defaults in solune/backend/src/services/workflow_orchestrator/config.py — check timeout values, retry counts, parallelism settings. Fix and add regression tests.
- [ ] T060 [P] [US3] Audit model definitions for incorrect validation and data coercion in solune/backend/src/models/ — check Pydantic validators, field defaults, enum handling, optional field semantics across all 27 model files. Fix and add regression tests.
- [ ] T061 [P] [US3] Audit remaining services for logic bugs in solune/backend/src/services/ — check collision_resolver.py, completion_providers.py, signal_bridge.py, signal_delivery.py, plan_issue_service.py, guard_service.py, pagination.py for control flow and return value errors. Fix and add regression tests.
- [ ] T062 [P] [US3] Audit chore services for scheduling and execution logic in solune/backend/src/services/chores/ — check scheduler timing, chat chore execution, counter logic, template builder output. Fix and add regression tests.
- [ ] T063 [P] [US3] Audit database migration files for schema inconsistencies in solune/backend/src/migrations/ — check migration ordering, column types, foreign key constraints, default values. Fix and add regression tests.

### Frontend Logic Review

- [ ] T064 [P] [US3] Audit frontend API client services for incorrect request construction in solune/frontend/src/services/ — check URL construction, parameter encoding, response mapping, error code handling. Fix and add regression tests.
- [ ] T065 [P] [US3] Audit frontend state management hooks for stale state bugs in solune/frontend/src/hooks/ — check TanStack Query cache keys, mutation invalidation, optimistic update rollback. Fix and add regression tests.
- [ ] T066 [P] [US3] Audit frontend form handling for validation bypass in solune/frontend/src/components/ — check Zod schema validation, form submission edge cases, error display logic. Fix and add regression tests.

### Logic Validation

- [ ] T067 [US3] Run full logic validation after all US3 fixes — `uv run pytest tests/unit/ -x`, `uv run ruff check src tests` in solune/backend/. Frontend: `npm run lint`, `npm run test` in solune/frontend/. Iterate until all pass.

**Checkpoint**: All logic bugs addressed. Full test suite passes.

---

## Phase 6: User Story 4 — Test Quality Improvement (Priority: P4)

**Goal**: Identify and fix test gaps, false-positive tests, mock leaks, and weak assertions so the test suite provides reliable coverage.

**Independent Test**: Review coverage reports. Verify that previously untested code paths now have meaningful assertions. Confirm mock objects are properly scoped. Run full test suite green.

### Backend Test Quality Review

- [ ] T068 [P] [US4] Fix weak assertions across solune/backend/tests/ — find and replace `assert True`, `assert mock.called` without call arg verification, and empty assertion tests with meaningful assertions
- [ ] T069 [P] [US4] Fix mock leaks in solune/backend/tests/ — find `MagicMock()` objects used as file paths, database paths, or URLs that could leak into production-like code paths; ensure proper mock scoping with `patch` decorators
- [ ] T070 [P] [US4] Fix overly broad exception handling in solune/backend/tests/ — find `try/except Exception` blocks in tests that swallow real failures; replace with specific exception types or remove
- [ ] T071 [P] [US4] Fix tests with no assertions or trivial assertions in solune/backend/tests/ — find test functions that have no `assert` statements or only `assert True`; add meaningful assertions or remove if redundant
- [ ] T072 [P] [US4] Audit unit tests for workflow orchestrator coverage gaps in solune/backend/tests/unit/ — identify untested state transitions, error paths, and edge cases in workflow_orchestrator tests; add missing tests
- [ ] T073 [P] [US4] Audit unit tests for copilot polling coverage gaps in solune/backend/tests/unit/ — identify untested retry paths, timeout handling, and error recovery in copilot polling tests; add missing tests
- [ ] T074 [P] [US4] Audit unit tests for agent service coverage gaps in solune/backend/tests/unit/ — identify untested lifecycle paths, error handling, and edge cases in agent service tests; add missing tests
- [ ] T075 [P] [US4] Audit unit tests for security-critical modules coverage gaps in solune/backend/tests/unit/ — check tests for encryption, auth, session store, middleware have complete path coverage; add missing tests
- [ ] T076 [P] [US4] Audit integration tests for end-to-end flow coverage in solune/backend/tests/integration/ — identify missing integration scenarios, incomplete multi-component flows; add missing tests
- [ ] T077 [P] [US4] Review `@pytest.mark.skip` and `@pytest.mark.xfail` usage in solune/backend/tests/ — verify each has a documented justification; remove skips that are no longer valid; fix xfail tests that should now pass

### Frontend Test Quality Review

- [ ] T078 [P] [US4] Audit frontend test quality in solune/frontend/src/ — find tests with weak assertions, missing error state testing, incomplete user interaction coverage; fix and add missing tests
- [ ] T079 [P] [US4] Audit frontend mock quality in solune/frontend/src/ — check that `vi.fn()` mocks are properly scoped and verified, API mocking is consistent, no mock leaks into production paths

### Test Quality Validation

- [ ] T080 [US4] Run full test quality validation after all US4 fixes — `uv run pytest tests/unit/ -x --timeout=120` and `uv run pytest --cov=src --cov-report=term-missing --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency` in solune/backend/. Frontend: `npm run test` in solune/frontend/. Iterate until all pass.

**Checkpoint**: Test suite quality improved. All tests pass with meaningful assertions.

---

## Phase 7: User Story 5 — Code Quality Cleanup (Priority: P5)

**Goal**: Remove dead code, unreachable branches, duplicated logic, hardcoded values, and silent failures to improve maintainability.

**Independent Test**: Run lint checks and full test suite after cleanup. Confirm removed code does not break any existing functionality.

### Backend Code Quality Review

- [ ] T081 [P] [US5] Remove dead code and unused imports across solune/backend/src/ — use ruff F401 findings and manual review to identify and remove unused imports, unreachable code after return/raise/break
- [ ] T082 [P] [US5] Fix silent failures across solune/backend/src/ — find bare `except: pass`, empty `except` blocks, swallowed exceptions without logging; add appropriate error reporting or re-raise
- [ ] T083 [P] [US5] Fix hardcoded values that should be configurable in solune/backend/src/ — identify magic numbers, hardcoded timeouts, inline URLs, feature flags that belong in solune/backend/src/config.py or constants.py
- [ ] T084 [P] [US5] Identify and flag duplicated logic across solune/backend/src/services/ — find repeated code patterns across service files; consolidate if minimal fix or flag with `# TODO(bug-bash):` if consolidation requires architectural change
- [ ] T085 [P] [US5] Fix missing error messages across solune/backend/src/ — find `raise Exception()` without messages, empty `HTTPException` details, log statements missing context; add descriptive error messages
- [ ] T086 [P] [US5] Remove commented-out code blocks across solune/backend/src/ — find and remove blocks of commented-out code that serve no documentation purpose

### Frontend Code Quality Review

- [ ] T087 [P] [US5] Remove dead code and unused imports across solune/frontend/src/ — use ESLint findings to identify and remove unused imports, unreachable branches, dead components
- [ ] T088 [P] [US5] Fix hardcoded values and silent failures in solune/frontend/src/ — identify inline magic values, empty catch blocks, missing error handling in async operations

### Code Quality Validation

- [ ] T089 [US5] Run full code quality validation after all US5 fixes — `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run pyright src` in solune/backend/. Frontend: `npm run lint`, `npm run typecheck`, `npm run build` in solune/frontend/. Iterate until all pass.

**Checkpoint**: Code quality improved. All lint and format checks pass.

---

## Phase 8: User Story 6 — Ambiguity Flagging & Summary Reporting (Priority: P3)

**Goal**: Ensure all ambiguous issues from phases 3–7 are properly flagged with `TODO(bug-bash)` comments, and produce a comprehensive summary report of all findings.

**Independent Test**: Verify every "Flagged" entry in the summary has a corresponding `TODO(bug-bash)` comment in source code. Verify every "Fixed" entry has a passing regression test.

### TODO Flag Verification

- [ ] T090 [P] [US6] Verify all `# TODO(bug-bash):` comments in solune/backend/src/ follow the required format — each must describe: (1) the issue, (2) available options, (3) why human judgment is needed. Example: `# TODO(bug-bash): Session timeout is 24h which may be too long for admin sessions. Options: reduce to 1h for admins, keep 24h for all. Needs human decision on UX trade-off.`
- [ ] T091 [P] [US6] Verify all `// TODO(bug-bash):` comments in solune/frontend/src/ follow the required format — same three-part structure: issue description, options, reason for human decision

### Summary Report Generation

- [ ] T092 [US6] Compile the final summary report as a markdown table listing every finding — columns: #, File, Line(s), Category, Description, Status (✅ Fixed / ⚠️ Flagged). Include counts: total fixed, total flagged, total files audited.
- [ ] T093 [US6] Cross-reference summary report against source code — verify every "Fixed" entry has a corresponding regression test that passes, and every "Flagged" entry has a corresponding `TODO(bug-bash)` comment in the source

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, and cross-cutting quality assurance

- [ ] T094 [P] Run complete backend CI validation in solune/backend/ — `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run pyright src`, `uv run bandit -r src`, `uv run pytest --cov=src --cov-report=term-missing --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency`
- [ ] T095 [P] Run complete frontend CI validation in solune/frontend/ — `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`
- [ ] T096 Verify no new dependencies were introduced — check solune/backend/pyproject.toml and solune/frontend/package.json against baseline for unexpected additions
- [ ] T097 Verify no architecture or public API surface changes — diff solune/backend/src/api/__init__.py router registrations, middleware ordering in solune/backend/src/main.py, and frontend route definitions
- [ ] T098 Run quickstart.md validation checklist from specs/002-bug-basher/quickstart.md — confirm all items pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all manual review phases
- **US1: Security (Phase 3)**: Depends on Foundational — highest priority, review first
- **US2: Runtime (Phase 4)**: Depends on Foundational — can start after or in parallel with US1 (different files)
- **US3: Logic (Phase 5)**: Depends on Foundational — can start after or in parallel with US1/US2 (different files)
- **US4: Test Quality (Phase 6)**: Depends on US1, US2, US3 — reviews tests AFTER source fixes to avoid rework
- **US5: Code Quality (Phase 7)**: Depends on US1, US2, US3 — cleanup AFTER bug fixes to avoid conflicts
- **US6: Reporting (Phase 8)**: Depends on all review phases (US1–US5) — compiles final summary
- **Polish (Phase 9)**: Depends on all user stories being complete — final validation gate

### User Story Dependencies

- **US1 Security (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **US2 Runtime (P2)**: Can start after Foundational (Phase 2) — Independent of US1 (reviews different bug category in potentially overlapping files)
- **US3 Logic (P3)**: Can start after Foundational (Phase 2) — Independent of US1/US2
- **US4 Test Quality (P4)**: Should start AFTER US1/US2/US3 — test fixes may conflict with source code changes
- **US5 Code Quality (P5)**: Should start AFTER US1/US2/US3 — dead code removal may conflict with bug fixes
- **US6 Reporting (P3)**: Must start AFTER all other stories — needs complete findings list

### Within Each User Story

- Review high-risk files first (as identified in plan.md)
- Fix → update affected tests → add regression test → validate (per fix)
- Run validation task at end of each story phase
- Story complete when all its tasks pass and checkpoint validation succeeds

### Parallel Opportunities

**Within Phase 2 (Foundational)**:
- T006–T010 can all run in parallel (independent static analysis scans)

**Within Phase 3 (US1 Security)**:
- T012–T031 can all run in parallel (each reviews different files)
- T032 must run after all T012–T031 complete (validation gate)

**Within Phase 4 (US2 Runtime)**:
- T033–T050 can all run in parallel (each reviews different files/areas)
- T051 must run after all T033–T050 complete (validation gate)

**Within Phase 5 (US3 Logic)**:
- T052–T066 can all run in parallel (each reviews different files/areas)
- T067 must run after all T052–T066 complete (validation gate)

**Within Phase 6 (US4 Test Quality)**:
- T068–T079 can all run in parallel (each addresses different test patterns)
- T080 must run after all T068–T079 complete (validation gate)

**Within Phase 7 (US5 Code Quality)**:
- T081–T088 can all run in parallel (each addresses different quality patterns)
- T089 must run after all T081–T088 complete (validation gate)

**Cross-phase parallelism**:
- US1 (Phase 3), US2 (Phase 4), and US3 (Phase 5) can run in parallel with different team members
- Each team member reviews their bug category across all files independently
- Merge conflicts resolved at validation checkpoints

---

## Parallel Example: User Story 1 (Security)

```bash
# Launch all security review tasks in parallel (each reviews different files):
Task T012: "Audit admin_guard.py for auth bypasses"
Task T013: "Audit csrf.py for token validation weaknesses"
Task T014: "Audit csp.py for header injection"
Task T015: "Audit rate_limit.py for bypass vulnerabilities"
Task T016: "Audit request_id.py for header injection"
Task T017: "Audit encryption.py for cryptographic weaknesses"
Task T018: "Audit github_auth.py for OAuth vulnerabilities"
Task T019: "Audit session_store.py for session fixation"
Task T020: "Audit auth.py endpoints for authentication bypass"
Task T021: "Audit mcp_server/auth.py for privilege escalation"
Task T022: "Audit webhooks.py for signature verification bypass"
Task T023: "Audit config.py for insecure defaults"
Task T024: "Audit logging_utils.py for sensitive data exposure"
Task T025: "Audit main.py for error detail leakage"
Task T026: "Audit dependencies.py for session/auth bypass"
Task T027: "Audit all API endpoints for input validation"
Task T028: "Audit template_files.py for path traversal"
Task T029: "Audit frontend for XSS vulnerabilities"
Task T030: "Audit frontend API clients for credential exposure"
Task T031: "Audit frontend route guards for auth bypass"

# After all parallel tasks complete, run validation:
Task T032: "Run full security validation"
```

---

## Parallel Example: User Story 4 (Test Quality)

```bash
# Launch all test quality tasks in parallel:
Task T068: "Fix weak assertions across backend tests"
Task T069: "Fix mock leaks across backend tests"
Task T070: "Fix overly broad exception handling in tests"
Task T071: "Fix tests with no assertions"
Task T072: "Audit workflow orchestrator test coverage"
Task T073: "Audit copilot polling test coverage"
Task T074: "Audit agent service test coverage"
Task T075: "Audit security module test coverage"
Task T076: "Audit integration test coverage"
Task T077: "Review skip/xfail markers"
Task T078: "Audit frontend test quality"
Task T079: "Audit frontend mock quality"

# After all parallel tasks complete, run validation:
Task T080: "Run full test quality validation"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup — establish baseline
2. Complete Phase 2: Foundational — run static analysis
3. Complete Phase 3: US1 Security — fix all security vulnerabilities
4. **STOP and VALIDATE**: Run full security scan + test suite
5. Security fixes are the highest-value deliverable

### Incremental Delivery

1. Complete Setup + Foundational → baseline established
2. Add US1 Security → validate → **MVP delivered** (most critical bugs fixed)
3. Add US2 Runtime → validate → reliability improved
4. Add US3 Logic → validate → correctness improved
5. Add US4 Test Quality → validate → safety net strengthened
6. Add US5 Code Quality → validate → maintainability improved
7. Add US6 Reporting → validate → full summary produced
8. Polish → final validation gate → **complete**

### Parallel Team Strategy

With multiple reviewers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Reviewer A: US1 Security (Phase 3)
   - Reviewer B: US2 Runtime (Phase 4)
   - Reviewer C: US3 Logic (Phase 5)
3. After US1–US3 complete:
   - Reviewer A: US4 Test Quality (Phase 6)
   - Reviewer B: US5 Code Quality (Phase 7)
4. After all reviews:
   - Any reviewer: US6 Reporting (Phase 8)
5. Team validates together: Polish (Phase 9)

---

## Notes

- [P] tasks = different files, no dependencies — safe to parallelize
- [Story] label maps task to specific user story for traceability
- Each user story corresponds to one bug category from the spec
- Regression tests are embedded in each review task (fix + test together)
- Validation tasks at the end of each phase are gates — do not proceed until green
- Commit strategy: one commit per bug or tightly related group of bugs
- Commit message format: `fix(category): Brief description` with What/Why/How/Test sections
- Ambiguous issues get `# TODO(bug-bash):` comments instead of code changes
- Files with no bugs are skipped — not mentioned in the summary report
