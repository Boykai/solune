# Feature Specification: Increase Test Coverage with Meaningful Tests

**Feature Branch**: `003-increase-test-coverage`  
**Created**: 2026-04-05  
**Status**: Draft  
**Input**: User description: "Increase Test Coverage with Meaningful Tests"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Backend Bug Discovery Through Test Coverage (Priority: P1)

A developer working on the Solune backend discovers and fixes latent bugs in low-coverage API endpoints (chat, board, apps) by writing targeted tests that exercise untested error paths and boundary conditions. Each bug fix is accompanied by a regression test to prevent reintroduction.

**Why this priority**: Bug-catching tests deliver immediate production safety. Known bugs in `api/chat.py` (expires_at None guard), `api/board.py` (hash computed before rate_limit), and `api/apps.py` (empty string from name normalization) currently risk runtime failures. Fixing these while adding tests provides the highest return on effort.

**Independent Test**: Can be fully tested by running `pytest tests/unit/test_api_chat.py tests/unit/test_api_board.py tests/unit/test_api_apps.py --cov=src/api -q` and verifying that all new tests pass, known bugs are resolved, and line coverage for these files increases (chat 65%→~80%, board 68%→~85%, apps 50% branch→~75%).

**Acceptance Scenarios**:

1. **Given** the `api/chat.py` module has an `expires_at` value of `None`, **When** the proposal expiry boundary logic executes, **Then** the system handles the `None` case gracefully without raising an unhandled exception.
2. **Given** the `api/chat.py` module receives an unrecognized `action_type` during post-processing, **When** the action is evaluated, **Then** the system rejects it with an appropriate error rather than silently proceeding.
3. **Given** a transcript file read request with a path traversal attempt (e.g., `../../etc/passwd`), **When** the file path is validated, **Then** the system blocks the request and returns an error.
4. **Given** the `api/board.py` module computes a data hash, **When** the hash is generated before the rate_limit field is set, **Then** the bug is fixed so hash computation occurs after all fields are populated.
5. **Given** an app name that normalizes to an empty string via `re.sub(r"[_.]", "-", ...).strip("-")`, **When** the name normalization runs in `api/apps.py`, **Then** the system returns a validation error instead of producing an empty string.
6. **Given** a file upload to the chat endpoint, **When** the file exceeds size limits or has an invalid type, **Then** the system rejects the upload with a clear error message.

---

### User Story 2 - Backend Coverage for Untested Endpoints (Priority: P2)

A developer creates test suites for backend endpoints that currently have zero test coverage (settings, onboarding, templates, pipeline_estimate, completion_providers), ensuring each module's primary workflows, error handling, and edge cases are validated.

**Why this priority**: Zero-coverage endpoints represent blind spots where any change could introduce regressions undetected. Covering these modules brings the overall backend from 82.8% to approximately 90% line coverage and establishes a safety net for future development.

**Independent Test**: Can be fully tested by running `pytest tests/unit/test_api_settings.py tests/unit/test_api_onboarding.py tests/unit/test_api_templates.py tests/unit/test_pipeline_estimate.py tests/unit/test_completion_providers.py --cov -q` and verifying new test files exist, all tests pass, and each module reaches its target coverage.

**Acceptance Scenarios**:

1. **Given** a non-admin user attempts a `PUT /global` settings request, **When** the request is processed, **Then** the system returns a 403 Forbidden response.
2. **Given** an empty update is sent to the settings endpoint, **When** the update is processed, **Then** no activity log entry is created (fixing the existing no-op update bug).
3. **Given** a new user begins the onboarding flow, **When** they reach the initial state, **Then** all defaults are correctly populated and progress is preserved across sessions.
4. **Given** a step value greater than 13 is submitted to the onboarding endpoint, **When** the request is validated, **Then** the system returns a 422 error.
5. **Given** an empty template registry, **When** the templates list is requested, **Then** the system returns an empty collection without error.
6. **Given** an invalid category is requested from the templates endpoint, **When** the request is processed, **Then** the system returns a 400 error.
7. **Given** agent count values at threshold boundaries (0.5, 1.0, 2.0, 4.0 hours), **When** the pipeline estimate is computed, **Then** the size classification and date computation are deterministic and correct.
8. **Given** concurrent access to the completion provider client pool, **When** multiple requests access the pool simultaneously, **Then** the system handles concurrency without corruption or deadlock.

---

### User Story 3 - Frontend Critical Component Tests (Priority: P3)

A developer adds behavior-driven tests for high-impact frontend components (AgentsPanel, AddAgentModal, AgentChatFlow, Pipeline components), ensuring user interactions, state transitions, and error handling are validated using the existing Vitest and React Testing Library setup.

**Why this priority**: Frontend coverage at 57.8% means nearly half of the UI code is untested. The selected components represent the most interactive and error-prone parts of the application. Testing them catches visual and interaction regressions that backend tests cannot detect.

**Independent Test**: Can be fully tested by running `npm run test:coverage` in the frontend directory and verifying that new test files exist, all tests pass, and statement coverage increases toward ~63%.

**Acceptance Scenarios**:

1. **Given** the AgentsPanel is rendered with no agents, **When** the component loads, **Then** an empty state message is displayed.
2. **Given** the AgentsPanel has agents loaded, **When** the user types in the search filter, **Then** only matching agents are displayed.
3. **Given** the AddAgentModal is in create mode, **When** the user enters a name that fails validation, **Then** an error message is shown and the create button is disabled.
4. **Given** the AgentChatFlow component is rendered, **When** the user presses Enter (without Shift), **Then** the message is sent; when Shift+Enter is pressed, a newline is inserted instead.
5. **Given** the AgentChatFlow is waiting for a response, **When** the send action is pending, **Then** the input is disabled to prevent duplicate submissions.
6. **Given** the ExecutionGroupCard displays agents in a group, **When** the user toggles execution mode, **Then** the mode switches correctly and the UI updates.
7. **Given** the PipelineModelDropdown is open, **When** the user clicks outside the dropdown, **Then** the dropdown closes.

---

### User Story 4 - Frontend Utility and Context Tests (Priority: P4)

A developer adds boundary-style tests for frontend utility functions (route-suggestions, command registry) and context providers (SyncStatusContext), validating pure logic and state management independently from component rendering.

**Why this priority**: Utility functions and contexts are foundational building blocks. Bugs in these propagate across the entire frontend. Testing them is low-effort and high-value since they are pure functions or simple state machines.

**Independent Test**: Can be fully tested by running targeted test files (`route-suggestions.test.ts`, `registry.test.ts`, `SyncStatusContext.test.tsx`) and verifying all edge cases pass.

**Acceptance Scenarios**:

1. **Given** the route-suggestions utility receives two strings, **When** the Levenshtein distance is computed, **Then** the result matches the expected edit distance.
2. **Given** the route-suggestions utility receives empty inputs, **When** the function is called, **Then** it returns a sensible default without errors.
3. **Given** a command is registered in the command registry, **When** the registry is queried for that command, **Then** it is found; after unregistering, it is not found.
4. **Given** the SyncStatusContext provider manages state transitions, **When** the same state value is set twice, **Then** the equality deduplication prevents unnecessary re-renders.

---

### Edge Cases

- What happens when a test file already exists for a previously untested module? New tests are appended or the file is extended, not overwritten.
- How does the system handle flaky tests? Tests must be deterministic; any test relying on timing uses controlled mocks or fixed time references.
- What happens when a bug fix changes the public API contract? The fix is documented, and any dependent tests are updated to reflect the corrected behavior.
- How are concurrent test runs handled? Each test is isolated with its own fixtures and mocks; no shared mutable state between test cases.
- What happens when coverage targets are not met after all planned tests are added? Remaining gaps are documented and prioritized for a follow-up effort.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Tests MUST follow existing conventions: Vitest + React Testing Library for frontend, pytest + AsyncClient for backend.
- **FR-002**: Each new test MUST be independently runnable and not depend on execution order or shared mutable state.
- **FR-003**: Bug fixes discovered through testing MUST include a regression test that fails without the fix and passes with it.
- **FR-004**: Backend line coverage MUST increase from 82.8% to at least 87%, with branch coverage reaching at least 78%.
- **FR-005**: Frontend statement coverage MUST increase from 57.8% to at least 63%.
- **FR-006**: All existing test suites MUST remain green after new tests and bug fixes are added.
- **FR-007**: Tests MUST cover error paths and boundary conditions, not just happy paths.
- **FR-008**: File upload validation tests MUST verify both size limits and file type restrictions.
- **FR-009**: Path traversal prevention tests MUST verify that directory traversal attempts are blocked.
- **FR-010**: Tests for the `api/chat.py` module MUST cover: proposal expiry boundary, `_retry_persist` transient vs permanent error handling, transcript path traversal prevention, file upload size/type validation, unrecognized `action_type` in post-processing, and streaming error with missing `action_data`.
- **FR-011**: Tests for `api/board.py` MUST cover: auth error vs rate-limit distinction, `_retry_after_seconds()` edge cases, stale cache fallback, manual refresh sub-issue cache deletion, and data hash stability.
- **FR-012**: Tests for `api/apps.py` MUST cover: name normalization edge cases (including empty after strip), pipeline launch failure as warning, duplicate repo import via URL normalization, and force delete partial failure.
- **FR-013**: Tests for `utils.py` MUST cover: BoundedDict eviction callback + `move_to_end`, URL parsing edge cases (HTTPS, enterprise, `.git` suffix), `resolve_repository` full fallback chain, REST repo extraction with malformed URLs, and `cached_fetch` refresh bypass.
- **FR-014**: New test files MUST be created for: `api/settings.py`, `api/onboarding.py`, `api/templates.py`, `services/pipeline_estimate.py`, and `services/completion_providers.py`.
- **FR-015**: Frontend component tests MUST validate user-facing behavior (interactions, state transitions, error displays), not implementation details.
- **FR-016**: Lint, type-check, and build smoke MUST pass on both backend and frontend after all changes.
- **FR-017**: Pure functions MUST receive boundary-style tests; components MUST receive behavior-driven tests.
- **FR-018**: Trivial re-export files and purely decorative files MUST be excluded from coverage targets.

### Assumptions

- The existing test infrastructure (pytest, Vitest, React Testing Library) is functional and does not require setup changes.
- Current coverage numbers (backend 82.8%, frontend 57.8%) are accurate baselines measured before work begins.
- The identified bugs (expires_at None guard, hash ordering, empty name normalization, no-op activity log) are reproducible with the current codebase.
- Mocking strategies follow existing patterns in the test suite (e.g., AsyncClient for API tests, mock providers for completion tests).
- No new testing dependencies are needed beyond what is already installed.
- E2E tests, integration tests, property/chaos/fuzz tests, refactoring globals to DI, and prompt snapshot tests are out of scope.

### Key Entities

- **Test Suite**: A collection of test cases organized by module (e.g., `test_api_chat.py`), each independently executable.
- **Coverage Report**: A measurement of code exercised by tests, tracking line coverage, branch coverage, and statement coverage.
- **Bug Fix**: A code change that corrects incorrect behavior, always paired with a regression test.
- **Test Fixture**: Reusable test setup (mock data, mock services, test clients) shared across test cases within a module.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Backend line coverage reaches at least 87% (up from 82.8%), verified by running `pytest tests/unit/ --cov=src --cov-report=term-missing -q`.
- **SC-002**: Backend branch coverage reaches at least 78%, verified by the same coverage report.
- **SC-003**: Frontend statement coverage reaches at least 63% (up from 57.8%), verified by running `npm run test:coverage`.
- **SC-004**: All previously identified bugs (expires_at None guard, hash ordering, empty name normalization, no-op activity log) have corresponding regression tests that fail without the fix and pass with it.
- **SC-005**: 100% of existing test suites pass after all changes are applied, with no test removals or modifications to existing passing tests.
- **SC-006**: Lint and type-check pass cleanly on both backend and frontend with zero new warnings or errors.
- **SC-007**: Each new test file is independently runnable (can execute in isolation without depending on other test files).
- **SC-008**: All security-related tests (path traversal, file upload validation, auth checks) pass without exceptions.
- **SC-009**: No new test takes longer than 5 seconds to execute individually, ensuring the test suite remains fast.
- **SC-010**: Every untested endpoint (settings, onboarding, templates, pipeline_estimate, completion_providers) has a dedicated test file with at least 75% coverage of its module.
