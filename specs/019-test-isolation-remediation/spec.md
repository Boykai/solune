# Feature Specification: Test Isolation & State-Leak Remediation

**Feature Branch**: `019-test-isolation-remediation`  
**Created**: 2026-04-07  
**Status**: Draft  
**Input**: User description: "The backend _clear_test_caches autouse fixture only clears 3 of 20+ module-level mutable globals, creating widespread cross-test state leaks. The frontend has a fake-timer leak and ordering-dependent UUID counter. Fix by expanding the central autouse fixture, adding pytest-randomly, and fixing frontend cleanup gaps."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Backend Tests Pass in Any Order (Priority: P1)

As a backend developer, I need every unit test to produce the same result regardless of execution order, so that test failures reliably indicate real bugs — not hidden dependencies on which tests ran before.

**Why this priority**: Cross-test state leaks are the root cause of flaky tests, false positives, and false negatives across the entire backend test suite. Fixing this unlocks trustworthy CI and unblocks all other development.

**Independent Test**: Can be fully tested by running the full backend test suite with three different random seed values and confirming all tests pass every time.

**Acceptance Scenarios**:

1. **Given** the expanded autouse fixture clears all 20+ module-level mutable globals, **When** the backend test suite is run with `--randomly-seed=12345`, **Then** all tests pass.
2. **Given** the expanded autouse fixture clears all 20+ module-level mutable globals, **When** the backend test suite is run with `--randomly-seed=99999`, **Then** all tests pass.
3. **Given** the expanded autouse fixture clears all 20+ module-level mutable globals, **When** the backend test suite is run with `--randomly-seed=42`, **Then** all tests pass.
4. **Given** a test modifies `_project_launch_locks` (the confirmed bug), **When** the next test reads `_project_launch_locks`, **Then** it sees an empty dictionary — the bug is fixed.
5. **Given** a test creates an `asyncio.Lock` in one event loop, **When** the next test runs in a fresh event loop, **Then** lazy-init locks have been reset to `None` and are recreated correctly.

---

### User Story 2 - Random Test Ordering Catches Future Regressions (Priority: P2)

As a backend developer, I need test execution order to be randomized by default, so that any new test-ordering dependency is surfaced immediately — before it reaches main.

**Why this priority**: Expanding the fixture fixes existing leaks, but without randomized ordering future leaks will go undetected until they cause a hard-to-diagnose CI failure.

**Independent Test**: Can be tested by verifying `pytest-randomly` is installed, active by default, and prints its seed at the start of every test run.

**Acceptance Scenarios**:

1. **Given** `pytest-randomly` is added to dev dependencies, **When** a developer runs `pytest`, **Then** tests execute in a random order and the seed is printed in the output.
2. **Given** a test failure due to ordering, **When** the developer re-runs with `pytest --randomly-seed=<printed-seed>`, **Then** the failure is exactly reproduced.
3. **Given** a developer needs deterministic ordering temporarily, **When** they run `pytest -p no:randomly`, **Then** tests execute in the standard order.

---

### User Story 3 - Frontend Tests Produce Deterministic Results (Priority: P2)

As a frontend developer, I need each test to start with a clean timer, UUID counter, and mock state, so that test assertions are deterministic and unaffected by which tests ran previously.

**Why this priority**: The frontend timer leak, UUID ordering dependency, and spy leaks cause intermittent failures that erode confidence in the test suite and waste developer time debugging phantom failures.

**Independent Test**: Can be tested by running `npx vitest run --reporter=verbose` and confirming no regressions, plus verifying that UUID-dependent assertions produce consistent values regardless of test execution order.

**Acceptance Scenarios**:

1. **Given** `useFileUpload.test.ts` uses fake timers, **When** the test file completes, **Then** real timers are restored and subsequent tests use real timer functions.
2. **Given** a test generates a UUID via the stub, **When** a different test generates a UUID in a separate run order, **Then** both tests produce the same UUID value (counter resets to 0 before each test).
3. **Given** `TopBar.test.tsx` uses `vi.spyOn()`, **When** the test file completes, **Then** the original implementations are restored and no spy wrappers leak to subsequent tests.
4. **Given** `useAuth.test.tsx` spies on `window.history.replaceState`, **When** the test file completes, **Then** the original `replaceState` is restored.

---

### User Story 4 - Existing Integration Tests Continue Working (Priority: P3)

As a developer, I need the existing integration test fixtures to remain intact as a defense-in-depth layer, so that expanding the central fixture does not inadvertently break integration-specific setup or teardown.

**Why this priority**: The integration conftest's `_reset_integration_state` provides additional safety for integration tests. Removing or conflicting with it could regress integration coverage.

**Independent Test**: Can be tested by running the full integration test suite and confirming all tests pass with the expanded central fixture layered underneath.

**Acceptance Scenarios**:

1. **Given** the central autouse fixture clears all globals, **When** integration tests run, **Then** the integration conftest's `_reset_integration_state` still executes as defense-in-depth.
2. **Given** the expanded fixture and the integration fixture both clear overlapping state, **When** both run for an integration test, **Then** no errors occur from double-clearing.

---

### Edge Cases

- What happens when a module-level global is imported but never used in a test? The fixture still clears it — no harm, and it prevents future leaks if usage patterns change.
- How does the system handle asyncio locks that were never lazily initialized? Resetting `None` to `None` is a no-op — safe.
- What if a BoundedDict or BoundedSet is replaced (rebound) rather than cleared? The fixture clears via `.clear()` on the original object; rebinding would require the fixture to also reassign. The existing codebase uses in-place mutation, not rebinding, so `.clear()` is correct.
- What if `pytest-randomly` conflicts with existing pytest plugins? `pytest-randomly` is compatible with `pytest-repeat`, `pytest-timeout`, `pytest-cov`, and `pytest-asyncio` — the plugins already in use.
- What if a frontend test intentionally uses fake timers across its entire lifecycle? The `afterEach` in `useFileUpload.test.ts` is file-local, not global — other test files that manage their own timers are unaffected.
- What happens when the UUID counter reset runs but no UUID is generated in a test? Resetting 0 to 0 is a no-op — safe.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The central autouse fixture MUST clear ALL module-level mutable globals (dictionaries, BoundedDicts, BoundedSets, sets, lists, deques) to their empty/default state before and after every test.
- **FR-002**: The central autouse fixture MUST reset lazy-initialized asyncio locks that use a getter pattern (`_ws_lock`, `_store_lock`) to `None` so they are recreated on demand in the correct event loop. Polling locks that are used directly without a lazy getter (`_polling_state_lock`, `_polling_startup_lock`) MUST be reset to fresh `asyncio.Lock()` instances.
- **FR-003**: The central autouse fixture MUST reset scalar state variables (`_consecutive_idle_polls`, `_adaptive_tier`, `_consecutive_poll_failures`, `_polling_task`) to their default values.
- **FR-004**: The central autouse fixture MUST reset `Optional` singletons (`_orchestrator_instance`, `_cached_files`, `_cached_warnings`, `_cache`, `_db`, `_encryption_service`) to `None`.
- **FR-005**: The fixture MUST clear `_project_launch_locks` — a confirmed bug where this dictionary is never cleared anywhere in the codebase.
- **FR-006**: The integration conftest's `_reset_integration_state` fixture MUST remain unchanged as a defense-in-depth layer.
- **FR-007**: `pytest-randomly` MUST be added to the backend's dev dependencies so test execution order is randomized by default.
- **FR-008**: The `useFileUpload.test.ts` test file MUST restore real timers after each test via `afterEach`.
- **FR-009**: The frontend test setup MUST reset the UUID counter to `0` before each test.
- **FR-010**: Test files that use `vi.spyOn()` without cleanup (`TopBar.test.tsx`, `AuthGate.test.tsx`, `useAuth.test.tsx`) MUST restore all mocks after each test via `afterEach`.
- **FR-011**: All existing tests MUST continue to pass after these changes — zero regressions.
- **FR-012**: Coverage thresholds MUST remain met: 75% for backend, 50% for frontend.

### Key Entities *(include if feature involves data)*

- **Module-Level Mutable Global**: A variable defined at module scope (not inside a function or class) that holds mutable state (dicts, lists, sets, locks, singletons). There are 20+ such globals across 15 backend modules. Each must be inventoried and cleared.
- **Autouse Fixture**: A pytest fixture with `autouse=True` that runs automatically before and after every test without requiring explicit reference. The central `_clear_test_caches` fixture is the single point of global state cleanup.
- **Lazy-Init Lock**: An `asyncio.Lock` variable initialized to `None` and created on first use. These bind to the active event loop at creation time and must be reset to `None` (not to a new lock) between tests to avoid cross-loop errors.
- **UUID Counter Stub**: A global counter in the frontend test setup that increments with each `crypto.randomUUID()` call. Without resetting, UUID values become ordering-dependent across the test suite.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The full backend test suite passes with three different random seed values (12345, 99999, 42) — demonstrating order-independence.
- **SC-002**: The full frontend test suite passes with `npx vitest run --reporter=verbose` — no regressions.
- **SC-003**: Backend code coverage remains at or above 75%.
- **SC-004**: Frontend code coverage remains at or above 50%.
- **SC-005**: The central autouse fixture clears all 20+ discovered module-level mutable globals — verified by comparing the fixture's clear list against the full global state inventory.
- **SC-006**: The confirmed `_project_launch_locks` bug is resolved — the dictionary is cleared between every test.
- **SC-007**: Integration and concurrency tests pass with the expanded fixture layering — the defense-in-depth integration fixture coexists without conflict.
- **SC-008**: Frontend UUID-dependent test assertions produce identical values regardless of test execution order.

## Assumptions

- The existing codebase uses in-place mutation (`.clear()`, assignment to `None`) for module-level globals, not rebinding to new objects. The fixture's clearing strategy relies on this pattern.
- `pytest-randomly>=3.16.0` is compatible with the project's Python >=3.12 and pytest 8+ requirements.
- The `_reset_integration_state` fixture in the integration conftest is safe to layer on top of the expanded central fixture — double-clearing is harmless.
- No production code changes are required. All changes are confined to test infrastructure (fixtures, test files, dev dependencies).
- The scope explicitly excludes: pytest-xdist parallelization, refactoring globals into dependency injection (architectural), and adding new tests beyond verification runs.
- Standard web/mobile performance expectations apply — this feature has no runtime performance impact since all changes are test-only.
- Error handling follows existing patterns — fixture failures surface as test setup errors with clear stack traces.
