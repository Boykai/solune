# Feature Specification: Increase Test Coverage

**Feature Branch**: `001-increase-test-coverage`
**Created**: 2026-04-09
**Status**: Draft
**Input**: User description: "Increase test coverage with meaningful test, using modern best practices. Resolve any discovered bugs/issues."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Close Critical Frontend Test Gaps (Priority: P1)

A developer opens a pull request that modifies chores, tools, or hooks code. The CI pipeline runs the test suite and catches regressions before the change is merged, because meaningful tests now exist for these previously untested areas.

**Why this priority**: Frontend chores (13 components, 0% tested), hooks (44 of 58 untested), and tools (8 of 9 untested) represent the largest and most business-critical coverage gaps. Without tests, any change to these areas risks shipping regressions to users undetected.

**Independent Test**: Can be fully tested by running `npm run test:coverage` in the frontend project and verifying that the chores, tools, and hooks directories show meaningful coverage improvements. Delivers immediate regression-detection value for the most-changed frontend code paths.

**Acceptance Scenarios**:

1. **Given** a frontend project with untested chores components, **When** the new tests are run, **Then** every chores component has at least one test file exercising its primary rendering and interaction behavior.
2. **Given** a frontend project with 14 of 58 hooks tested, **When** the new hook tests are run, **Then** at least 80% of hooks have dedicated test files validating their core behavior, including state transitions, error handling, and cleanup.
3. **Given** a frontend project with 1 of 9 tools components tested, **When** the new tests are run, **Then** every tools component has at least one test file covering its primary user interaction flow.
4. **Given** an existing passing test suite, **When** the new tests are added, **Then** all previously passing tests continue to pass without modification.

---

### User Story 2 - Close Backend Test Gaps (Priority: P2)

A developer changes a prompt template or a backend service that previously had no tests. The CI pipeline catches the regression because new backend tests cover these modules.

**Why this priority**: Backend coverage is generally strong (75%+ enforced) but specific modules — 3 prompt files and the observability setup — lack dedicated tests. These are lower-risk than frontend gaps but still represent blind spots. (Note: `encryption.py` already has dedicated tests in `test_token_encryption.py` and `test_encryption_helpers.py`.)

**Independent Test**: Can be tested by running `pytest --cov=src` in the backend project and verifying that the newly tested modules appear in the coverage report with meaningful line coverage.

**Acceptance Scenarios**:

1. **Given** untested prompt modules (`agent_instructions.py`, `issue_generation.py`, `task_generation.py`), **When** dedicated tests are written, **Then** each prompt module has tests verifying prompt output structure, variable substitution, and edge cases (empty inputs, special characters).
2. **Given** an untested `otel_setup.py` service, **When** tests are added, **Then** the tests verify setup initialization, no-op fallback behavior, and cleanup.

---

### User Story 3 - Fix Discovered Bugs (Priority: P2)

A production deployment runs for weeks handling thousands of project launches. The system remains stable because the unbounded lock dictionary in `pipeline_state_store.py` has been fixed with a bounded data structure, preventing memory growth.

**Why this priority**: The `_project_launch_locks` memory leak is a known production stability risk. While it manifests only at scale, the fix is straightforward and directly discovered through coverage analysis. Fixing it alongside test coverage work keeps the codebase healthy.

**Independent Test**: Can be tested by writing a unit test that creates locks for more entries than the maximum capacity and verifies that the dictionary does not grow beyond its bound.

**Acceptance Scenarios**:

1. **Given** a `pipeline_state_store` module with an unbounded `_project_launch_locks` dictionary, **When** the fix is applied, **Then** the lock dictionary uses a bounded data structure consistent with other dictionaries in the same file.
2. **Given** a bounded lock dictionary with a configured maximum size, **When** more than the maximum number of unique project IDs request locks, **Then** the oldest entries are evicted and memory usage remains stable.
3. **Given** an existing test suite for `pipeline_state_store`, **When** the fix is applied, **Then** all existing tests continue to pass and new tests validate the bounded behavior.

---

### User Story 4 - Raise Coverage Thresholds (Priority: P3)

After the new tests are added, the team raises CI coverage thresholds to prevent future coverage regressions. Developers receive clear feedback when a pull request would drop coverage below the new minimum.

**Why this priority**: Thresholds codify the coverage gains and prevent regression. This is lower priority because it only matters after the tests from P1 and P2 are in place.

**Independent Test**: Can be tested by temporarily lowering a coverage value below the new threshold and verifying that the CI job fails with a clear error message indicating which threshold was violated.

**Acceptance Scenarios**:

1. **Given** the current frontend coverage thresholds (50% lines, 44% branches, 41% functions), **When** coverage improvements are in place, **Then** thresholds are raised to reflect the new baseline (target: 65%+ lines, 55%+ branches, 55%+ functions).
2. **Given** the current backend coverage threshold (75%), **When** coverage improvements are in place, **Then** the threshold remains at 75% or is raised if overall coverage now exceeds 80%.
3. **Given** a developer submits a PR that reduces line coverage below the threshold, **When** CI runs, **Then** the test job fails and the output identifies the coverage shortfall.

---

### Edge Cases

- What happens when a component under test depends on complex global state (authentication, routing, stores)? Tests must use appropriate mocking and setup utilities already present in the test infrastructure.
- How does the system handle tests for components with asynchronous data fetching? Tests must use established async patterns (e.g., `waitFor` in React Testing Library, `pytest-asyncio` for backend).
- What happens when a hook depends on other hooks or context providers? Tests must wrap components in the necessary providers, consistent with existing test patterns in the repository.
- What happens when the bounded lock dictionary evicts an entry that is still in active use? The implementation must ensure active locks are not evicted or that eviction is safe (lock is re-created on next access).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every frontend component directory with 0% test coverage MUST have at least one test file per component covering primary rendering and user interaction.
- **FR-002**: Every frontend custom hook MUST have a dedicated test file validating its core state management, side effects, error handling, and cleanup behavior.
- **FR-003**: Every untested backend prompt module MUST have tests verifying output structure, template variable substitution, and edge-case inputs.
- **FR-004**: ~~The `encryption.py` service MUST have tests verifying encrypt/decrypt round-trips, key management, and error handling for malformed inputs.~~ *(Already covered: `test_token_encryption.py` and `test_encryption_helpers.py` exist.)*
- **FR-005**: The `otel_setup.py` service MUST have tests verifying initialization, no-op fallback, and teardown behavior.
- **FR-006**: The `_project_launch_locks` dictionary in `pipeline_state_store.py` MUST use a bounded data structure to prevent unbounded memory growth.
- **FR-007**: All new tests MUST follow existing test patterns and conventions in the repository (e.g., file naming, directory structure, assertion style).
- **FR-008**: All new tests MUST be meaningful — they MUST test actual behavior, not merely assert that a module can be imported or a component renders without crashing.
- **FR-009**: Frontend coverage thresholds MUST be raised after new tests are added to reflect the improved baseline.
- **FR-010**: All pre-existing tests MUST continue to pass after changes are applied.

### Key Entities

- **Test File**: A source file containing one or more test cases, colocated or in a parallel test directory, following the repository's naming convention (`.test.tsx` for frontend, `test_*.py` for backend).
- **Coverage Threshold**: A numeric percentage configured in the test runner (Vitest or pytest) that causes CI to fail when overall coverage drops below the value.
- **Bounded Dictionary**: A dictionary data structure with a configurable maximum size that evicts the oldest entries when capacity is reached, already available as `BoundedDict` in the backend utilities.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Frontend component test coverage increases from the current baseline to at least 65% line coverage across all component directories.
- **SC-002**: At least 80% of frontend custom hooks (47 of 58) have dedicated test files with meaningful assertions.
- **SC-003**: All 13 chores components, all 9 tools components, and the command-palette component have at least one test file each.
- **SC-004**: All 3 untested backend prompt modules (`agent_instructions.py`, `issue_generation.py`, `task_generation.py`) have dedicated test files.
- **SC-005**: Backend service `otel_setup.py` has at least one dedicated test file. (`encryption.py` is already covered by existing tests `test_token_encryption.py` and `test_encryption_helpers.py`.)
- **SC-006**: The `_project_launch_locks` memory leak is fixed and validated by a test that confirms bounded behavior.
- **SC-007**: Backend coverage remains at or above 75%; frontend coverage thresholds are raised to at least 65% lines, 55% branches, 55% functions.
- **SC-008**: Zero pre-existing test failures are introduced by the changes.
- **SC-009**: All new test files follow the established naming conventions and directory structure of the repository.

## Assumptions

- The existing test infrastructure (Vitest + React Testing Library for frontend; pytest + pytest-asyncio for backend) is sufficient and does not need replacement or major reconfiguration.
- The `BoundedDict` utility already present in `backend/src/utils.py` is suitable for replacing the unbounded `_project_launch_locks` dictionary.
- Coverage percentage targets (65% frontend lines, 75% backend) are reasonable starting points; exact final numbers will be calibrated after tests are written.
- Property-based testing (Hypothesis for backend, fast-check for frontend) should be used where it adds value (e.g., encryption round-trip testing, input fuzzing for prompts) but is not required for every new test.
- Existing skip markers and conditional test guards remain as-is; they are infrastructure-appropriate and not considered coverage gaps.

