# Feature Specification: Increase Test Coverage with Meaningful Tests

**Feature Branch**: `003-test-coverage-meaningful`  
**Created**: 2026-04-05  
**Status**: Draft  
**Input**: User description: "Increase Test Coverage with Meaningful Tests"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Backend API Error Path Testing and Bug Fixes (Priority: P1)

A developer runs the backend test suite against the existing low-coverage API modules (`chat.py`, `board.py`, `apps.py`, `utils.py`). The new tests exercise previously untested error handling paths — expired proposals, transient vs permanent retry failures, path traversal attacks, file upload validation, rate-limit classification, name normalization edge cases, and URL parsing quirks. Where these tests expose existing bugs (missing `None` guards, absent validation whitelists, unchecked file sizes, hash computation ordering), the bugs are fixed inline alongside the test additions. After this work, the developer has high confidence that the most critical backend API endpoints handle error conditions correctly and that known defects are resolved.

**Why this priority**: These four modules are the highest-impact backend targets — they already have partial test coverage (50–68%) but contain known bugs and untested error paths. Fixing bugs here directly improves production reliability. Testing error paths prevents regressions in the most user-facing API surface.

**Independent Test**: Run the backend tests for chat, board, apps, and utils modules with coverage reporting and verify each module's line coverage reaches its target threshold (chat ≥80%, board ≥85%, apps branch ≥75%, utils ≥85%). Confirm all known bugs are covered by at least one failing-then-passing test.

**Acceptance Scenarios**:

1. **Given** `api/chat.py` has a proposal with `expires_at` set to `None`, **When** the proposal expiry check runs, **Then** the system handles the `None` value gracefully without raising an unhandled exception
2. **Given** `api/chat.py` receives a file upload, **When** the file exceeds the size limit or has a disallowed type, **Then** the system rejects the request with an appropriate error before processing
3. **Given** `api/chat.py` receives a transcript read request with path traversal characters, **When** the path is resolved, **Then** the system rejects the request and does not access files outside the allowed directory
4. **Given** `api/board.py` encounters an authentication error, **When** the error is classified, **Then** it is correctly distinguished from a rate-limit error and handled with the appropriate retry strategy
5. **Given** `api/apps.py` processes a name consisting entirely of special characters, **When** the name normalization function strips all characters, **Then** the system handles the resulting empty string without creating an invalid resource
6. **Given** `utils.py` receives a URL with enterprise domain, HTTPS scheme, or `.git` suffix variations, **When** the URL is parsed, **Then** the correct repository owner and name are extracted in all cases

---

### User Story 2 - Backend Untested Endpoint Coverage (Priority: P1)

A developer creates test suites for five backend modules that currently have zero test coverage: settings, onboarding, templates, pipeline estimation, and completion providers. Each new test file covers the module's primary operations, permission boundaries, validation rules, and error handling. Where tests expose bugs (such as activity logging on no-op updates), the bugs are fixed. After this work, these previously untested modules have documented behavioral contracts that prevent future regressions.

**Why this priority**: Modules with 0% coverage represent the highest-risk areas — any change could introduce undetected regressions. Testing these modules establishes a safety net for ongoing development. The settings and onboarding endpoints are user-facing and security-sensitive (permission enforcement).

**Independent Test**: Run the backend tests for settings, onboarding, templates, pipeline estimate, and completion provider modules with coverage reporting and verify each module reaches its coverage target (settings ≥80%, onboarding ≥90%, templates ≥90%, pipeline estimate ≥95%, completion providers ≥75%).

**Acceptance Scenarios**:

1. **Given** a non-admin user, **When** they attempt to update global settings, **Then** the system returns a 403 Forbidden response
2. **Given** an admin user submits an empty settings update, **When** the update is processed, **Then** the system treats it as a no-op and does not log an activity event
3. **Given** a new user begins onboarding, **When** the initial state is retrieved, **Then** all default values are populated correctly and progress is preserved across sessions
4. **Given** an onboarding step value exceeds the valid boundary (greater than 13), **When** the step is submitted, **Then** the system returns a 422 validation error
5. **Given** a template request with an invalid category, **When** the registry is queried, **Then** the system returns a 400 error with a descriptive message
6. **Given** a pipeline estimation request with a specific agent count, **When** the estimate is computed, **Then** the hour threshold boundaries (0.5, 1.0, 2.0, 4.0) produce consistent and deterministic results
7. **Given** a completion provider client pool, **When** multiple requests arrive concurrently, **Then** the pool handles access without deadlocks or resource leaks

---

### User Story 3 - Frontend Critical Component Testing (Priority: P2)

A developer creates test suites for the highest-impact frontend components: the Agents panel (list, search, sort, delete, undo), the Add Agent modal (validation, create vs edit modes), the Agent Chat Flow (message handling, keyboard interactions), and the Pipeline components (execution groups, model dropdowns, run history). Each test suite covers user interactions, state transitions, accessibility, and error/loading states using behavior-driven testing patterns. After this work, the most complex interactive components have automated tests that verify their user-facing behavior.

**Why this priority**: Frontend coverage is significantly lower (57.8%) than backend. These components represent the most complex interactive surfaces — they handle user input, state management, and async operations. Behavioral tests here catch regressions that are expensive to find manually. The Agents panel and Pipeline components are used in every pipeline workflow.

**Independent Test**: Run the frontend test suite with coverage reporting and verify statement coverage reaches ≥63%. Confirm each new test file passes independently.

**Acceptance Scenarios**:

1. **Given** the Agents panel renders with no agents configured, **When** the panel loads, **Then** an empty state message is displayed guiding the user to create their first agent
2. **Given** the Agents panel has multiple agents, **When** the user types in the search filter, **Then** the displayed agent list updates to show only matching agents
3. **Given** the user deletes an agent from the panel, **When** the deletion completes, **Then** an undo option is presented allowing the user to restore the agent within a time window
4. **Given** the Add Agent modal is open in create mode, **When** the user enters a name that fails validation (empty, too long, or containing invalid characters), **Then** an inline error message is shown and the create button is disabled
5. **Given** the Agent Chat Flow is active and a message is pending, **When** the user attempts to send another message, **Then** the input is disabled until the pending response completes
6. **Given** a Pipeline run history entry, **When** the user expands the entry, **Then** the duration is formatted in human-readable units and status badges reflect the correct run state

---

### User Story 4 - Frontend Utility and Context Testing (Priority: P3)

A developer creates tests for frontend utility functions and context providers: route suggestion matching (Levenshtein distance calculations, threshold filtering), the command registry (register/unregister/get/filter commands, argument parsing), and the Sync Status context (provider state management, transition logic, equality deduplication). These are pure-function and context-provider tests that verify the correctness of foundational logic used across the application.

**Why this priority**: While lower priority than component tests, these utilities underpin many features. Route suggestions affect navigation UX, the command registry powers the slash-command system, and the Sync Status context manages real-time state. Bugs in these utilities have cascading effects across the application.

**Independent Test**: Run the frontend tests for route-suggestions, registry, and SyncStatusContext files and verify all tests pass with full branch coverage of the targeted functions.

**Acceptance Scenarios**:

1. **Given** a route suggestion input, **When** the Levenshtein distance is calculated against available routes, **Then** the results are correctly filtered by the threshold and empty inputs return no suggestions
2. **Given** a command registered in the registry, **When** the registry is queried with a filter, **Then** only matching commands are returned and argument parsing produces the correct tokens
3. **Given** the Sync Status context provider is active, **When** multiple rapid state transitions occur with equivalent values, **Then** duplicate transitions are deduplicated and downstream consumers do not re-render unnecessarily

---

### Edge Cases

- What happens when a test exposes a bug in code that is also changed by another in-flight PR? The bug fix is applied to the current branch and the test documents the expected behavior; merge conflicts are resolved during integration.
- What happens when a backend module's internal structure changes, invalidating mock setups? Tests use the thinnest possible mocking layer (patching at the boundary, not deep internals) so that internal refactors do not break the test contract.
- What happens when test coverage metrics fluctuate due to code changes in other branches? Verification uses relative improvement targets (delta from baseline) in addition to absolute thresholds.
- What happens when a frontend component's async behavior causes test flakiness? Tests use deterministic state management (explicit wait-for patterns, controlled timers) rather than arbitrary delays.
- What happens when a discovered bug requires a breaking API change to fix? The bug is documented in the test as a known issue with a skip marker and a linked follow-up ticket, rather than making breaking changes in a test-focused effort.
- What happens when multiple test files import the same fixture or mock? Shared test utilities are extracted to existing shared fixture locations (backend conftest, frontend test-utils) following established conventions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Test suite MUST add error-path tests for `api/chat.py` covering proposal expiry boundary, retry persistence (transient vs permanent), transcript path traversal prevention, file upload size/type validation, unrecognized action types, and streaming errors with missing action data
- **FR-002**: Test suite MUST fix the `expires_at None` guard bug in `api/chat.py` and include a regression test that fails without the fix
- **FR-003**: Test suite MUST fix the missing `action_type` validation whitelist in `api/chat.py` and include a regression test
- **FR-004**: Test suite MUST fix the missing size check before transcript file read in `api/chat.py` and include a regression test
- **FR-005**: Test suite MUST add tests for `api/board.py` covering auth error vs rate-limit distinction, `_retry_after_seconds()` edge cases, stale cache fallback, manual refresh cache deletion, and data hash stability
- **FR-006**: Test suite MUST fix the hash-computed-before-rate-limit-set bug in `api/board.py` and include a regression test
- **FR-007**: Test suite MUST add tests for `api/apps.py` covering name normalization edge cases (including empty-after-strip), pipeline launch failure warnings, duplicate repo import via URL normalization, and force-delete partial failure
- **FR-008**: Test suite MUST fix the empty string produced by name normalization in `api/apps.py` and include a regression test
- **FR-009**: Test suite MUST add tests for `utils.py` covering BoundedDict eviction callback and move-to-end, URL parsing edge cases (HTTPS, enterprise, .git suffix), resolve_repository full fallback chain, REST repo extraction with malformed URLs, and cached_fetch refresh bypass
- **FR-010**: Test suite MUST create `test_api_settings.py` with tests for non-admin permission enforcement (403), empty update no-op behavior, project settings workflow sync, cache invalidation, and model fetcher with missing token
- **FR-011**: Test suite MUST fix the activity log called on no-op update bug in `api/settings.py` and include a regression test
- **FR-012**: Test suite MUST create `test_api_onboarding.py` with tests for initial state defaults, progress preservation, completion timestamp, dismiss vs completion flow, and step boundary validation (step >13 returns 422)
- **FR-013**: Test suite MUST create `test_api_templates.py` with tests for empty registry, invalid category (400), summary vs detail field filtering, and not-found (404) responses
- **FR-014**: Test suite MUST create `test_pipeline_estimate.py` with tests for hour threshold boundaries (0.5, 1.0, 2.0, 4.0), agent count validation with logging, and date computation determinism
- **FR-015**: Test suite MUST create `test_completion_providers.py` with tests for client pool concurrent access, cleanup on remove, session timeout empty string fallback, Azure config validation, and factory dispatch
- **FR-016**: Test suite MUST create `AgentsPanel.test.tsx` with tests for empty state, search filter, sort toggle, modal open/close, delete with undo, infinite scroll, and error/loading states
- **FR-017**: Test suite MUST create `AddAgentModal.test.tsx` with tests for name validation, prompt length limit, character counter, create vs edit mode switching, and AI enhance toggle
- **FR-018**: Test suite MUST create `AgentChatFlow.test.tsx` with tests for initial message auto-send, Enter/Shift+Enter handling, disable while pending, and error display
- **FR-019**: Test suite MUST create Pipeline component tests: `ExecutionGroupCard.test.tsx` (agents in group, execution mode toggle, remove agent), `PipelineModelDropdown.test.tsx` (open/close, model selection, click outside), `PipelineRunHistory.test.tsx` (collapsible, duration formatting, status badges, lazy query)
- **FR-020**: Test suite MUST create `route-suggestions.test.ts` with tests for Levenshtein distance accuracy, threshold filtering, and empty input handling
- **FR-021**: Test suite MUST create `commands/registry.test.ts` with tests for register/unregister/get/filter operations and argument parsing
- **FR-022**: Test suite MUST create `SyncStatusContext.test.tsx` with tests for provider state management, transitions, and equality deduplication
- **FR-023**: All new tests MUST follow existing project conventions — behavior-driven testing for frontend components, async client patterns for backend endpoints
- **FR-024**: All existing tests MUST continue to pass after changes (no regressions in the existing test suite)
- **FR-025**: Bug fixes MUST be made inline alongside the tests that expose them, not as separate changes
- **FR-026**: Tests MUST target behavior and error paths, not line-coverage padding — each test must verify a meaningful behavioral contract

### Key Entities

- **Test Case**: A single test function that verifies one specific behavior or error path. Key attributes: target module, tested scenario, expected outcome, priority (bug-regression vs coverage-gap)
- **Bug Fix**: An inline code correction discovered through test writing. Key attributes: affected module, line reference, root cause, regression test reference
- **Coverage Metric**: A measurement of test coverage for a specific module. Key attributes: module path, line coverage percentage, branch coverage percentage, baseline value, target value

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Backend overall line coverage reaches ≥87% (up from 82.8% baseline), as measured by the backend coverage reporting tool
- **SC-002**: Backend overall branch coverage reaches ≥78%, as measured by the same coverage tool
- **SC-003**: Frontend statement coverage reaches ≥63% (up from 57.8% baseline), as measured by the frontend coverage reporting tool
- **SC-004**: All six identified backend bugs are fixed, each verified by at least one test that would fail without the fix
- **SC-005**: All existing test suites remain green — zero test regressions introduced by the changes
- **SC-006**: Lint, type-check, and build smoke tests pass on both backend and frontend after all changes
- **SC-007**: Every new test file follows the established project test conventions and does not introduce new test dependencies
- **SC-008**: Each new backend test module covers ≥80% of its target module's lines, with the specific targets being: chat ≥80%, board ≥85%, apps branch ≥75%, utils ≥85%, settings ≥80%, onboarding ≥90%, templates ≥90%, pipeline estimate ≥95%, completion providers ≥75%
- **SC-009**: Each new frontend test file includes tests for primary user flows, error states, and at least two edge cases per component
- **SC-010**: No end-to-end tests, integration tests, property tests, or fuzz tests are included — scope remains strictly unit and behavioral tests

## Assumptions

- Current backend line coverage baseline is 82.8% and frontend statement coverage baseline is 57.8%, as stated in the parent issue. These baselines may shift slightly due to concurrent development on other branches.
- The existing test infrastructure is stable and sufficient — no new test frameworks or tools are needed.
- Bug line references in the parent issue (e.g., `api/chat.py` ~line 1077, `api/board.py` ~line 395, `api/settings.py` ~line 94) are approximate and may have shifted due to recent code changes; the bugs are identified by behavior, not exact line number.
- Shared test fixtures and mocks follow existing patterns in backend conftest files and frontend test utility files — new shared utilities are added to these existing locations.
- The six identified bugs are fixable without breaking API contracts or requiring database migrations.
- Frontend components under test may use mocked API calls and context providers consistent with existing test patterns in the repository.
- Coverage metrics are measured at the module level for target tracking but reported at the project level for success criteria verification.

## Dependencies

- **Parent Issue #890**: This specification is tracked under the parent issue for test coverage improvement
- **Existing test infrastructure**: Backend and frontend test runners, coverage tools, and assertion libraries must be available and configured
- **Current test suites**: All existing tests must pass before new tests are added (clean baseline)
- **CI pipeline**: Lint, type-check, build, and test steps must be functional for verification

## Out of Scope

- End-to-end tests, integration tests, property-based tests, chaos tests, and fuzz tests
- Refactoring global state to dependency injection patterns
- Prompt snapshot tests for AI-generated content
- Trivial re-export files and purely decorative components
- Mobile-specific or accessibility-specific test coverage (unless directly related to component behavior)
- Test infrastructure upgrades or new testing tool adoption
- Coverage improvements to modules not listed in the parent issue's phased plan
