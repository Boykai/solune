# Feature Specification: Full Coverage Push + Bug Fixes

**Feature Branch**: `002-coverage-push-bugfixes`  
**Created**: 2026-04-06  
**Status**: Draft  
**Input**: User description: "Increase test coverage across frontend and backend while fixing 4 discovered bugs: 2 concurrency race conditions in copilot polling, stale polling test mocks, and a missing agent preview regression test. 5 phases ordered by risk/impact."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Eliminate Copilot Polling Race Conditions (Priority: P1)

As a user interacting with the copilot feature, I expect polling to operate reliably without data corruption or duplicate background tasks, so that my copilot sessions produce consistent, correct results every time.

Two concurrency bugs have been identified in the copilot polling subsystem:

1. **Stale-write race**: Multiple concurrent operations can overwrite polling state fields without coordination, causing the system to lose track of the current polling status and producing inconsistent or incorrect results for users.
2. **Duplicate-task race**: The startup sequence that creates polling tasks can be triggered concurrently, resulting in multiple polling tasks running simultaneously for the same session, wasting resources and potentially returning conflicting data to the user.

**Why this priority**: These are active production bugs. Race conditions are non-deterministic and can silently corrupt state, leading to unpredictable user experiences. Fixing them is a prerequisite for reliable copilot functionality and must be done before any coverage work that touches the same code paths.

**Independent Test**: Can be fully tested by running the concurrency test suite and verifying that both previously-expected-to-fail tests now pass without flakiness across multiple runs.

**Acceptance Scenarios**:

1. **Given** two concurrent polling operations attempt to update the same polling state, **When** both execute simultaneously, **Then** all state mutations are serialized and the final state is consistent (no lost updates).
2. **Given** multiple callers invoke the polling startup sequence at the same time, **When** the startup check runs concurrently, **Then** exactly one polling task is created (no duplicates).
3. **Given** the concurrency test suite is run, **When** previously-expected-to-fail tests execute, **Then** all tests pass without the expected-failure marker.

---

### User Story 2 — Update Stale Test Mocks to Match Current Code (Priority: P1)

As a developer maintaining the project, I need the test suite to mock the actual functions that the production code calls, so that tests remain meaningful and do not silently pass while testing outdated code paths.

The project API tests currently mock deprecated internal functions that are no longer called by the production code. This means the tests pass but do not actually validate the current behavior, creating a false sense of security.

**Why this priority**: Stale mocks mask real bugs. If production code changes and tests still pass against deprecated mocks, the team has no safety net. This is equally critical to the race condition fixes because it undermines the value of the entire test suite.

**Independent Test**: Can be verified by confirming that the affected tests mock only the current production functions and that removing the deprecated function signatures from the codebase does not break any test.

**Acceptance Scenarios**:

1. **Given** the API project tests currently mock deprecated internal functions, **When** the mocks are updated to target current production functions, **Then** all affected tests continue to pass.
2. **Given** the updated test file, **When** searching for references to the deprecated function names, **Then** zero references remain.

---

### User Story 3 — Add Regression Test for Agent Preview Edge Case (Priority: P2)

As a developer, I need a regression test covering the scenario where the agent preview extraction receives malformed input data, so that the existing guard logic is validated and future regressions are caught automatically.

A defensive guard exists in the agent service that returns a safe fallback when the agent tools configuration is malformed. However, no test exercises this path, meaning a future code change could remove the guard without anyone noticing.

**Why this priority**: While the bug itself is already guarded in production, the lack of a test means regressions can be introduced silently. This is lower priority than the active race conditions but still important for long-term reliability.

**Independent Test**: Can be tested independently by invoking the agent preview extraction with a malformed tools configuration and asserting it returns the expected fallback value.

**Acceptance Scenarios**:

1. **Given** an agent configuration with a malformed tools entry (e.g., a bare string instead of a structured object), **When** the agent preview extraction is invoked, **Then** the function returns a safe fallback (None/null) rather than crashing.

---

### User Story 4 — Increase Backend Test Coverage for MCP Server Components (Priority: P2)

As a development team, we need comprehensive test coverage for the MCP (Model Context Protocol) server components — including authentication middleware, tool endpoints, resource handlers, and template routes — so that changes to these critical backend services are caught by the test suite before reaching production.

Current coverage for these components ranges from 20% to 65%, with branch coverage at 0% for several modules. This means large portions of the server logic — including error handling, edge cases, and authentication flows — are untested.

**Why this priority**: The MCP server is a core backend component. Low coverage means regressions in authentication, data operations, and resource handling go undetected. This work can proceed in parallel with the regression test (Story 3).

**Independent Test**: Each new test file can be run independently against mocked service dependencies, verifying specific scenarios for each component.

**Acceptance Scenarios**:

1. **Given** the authentication middleware, **When** tested with valid tokens, missing headers, and malformed tokens, **Then** each scenario produces the correct authorization outcome and context is properly cleaned up.
2. **Given** the tool endpoints for chores, chat, and activity, **When** tested with CRUD operations, error conditions, boundary limits, and session handling, **Then** each scenario produces the expected result or error response.
3. **Given** the resource and prompt handlers, **When** tested across resource type branches and prompt template selection paths, **Then** all branches are exercised and return correct data.
4. **Given** the template routes, **When** tested with category filtering, missing resources, and pagination, **Then** correct responses and error codes are returned.

---

### User Story 5 — Increase Frontend Test Coverage for Scroll Behavior (Priority: P3)

As a user navigating between pages, I expect the page to scroll to the top on each navigation and for scroll locking to work correctly during overlay interactions, so that I always see the top of the new page and modals behave as expected.

These scroll behaviors were introduced in a prior PR but have zero test coverage. Without tests, regressions in scroll-to-top behavior or scroll locking could ship undetected.

**Why this priority**: Scroll behavior is a user-experience concern. While less severe than data bugs, broken scroll behavior causes visible user frustration. This can proceed in parallel with backend coverage work.

**Independent Test**: Can be tested by simulating route changes and asserting scroll position resets, verifying scroll lock activation on component mount, and confirming section anchor IDs render in the DOM.

**Acceptance Scenarios**:

1. **Given** a user navigates to a new page, **When** the route changes, **Then** the main content area scrolls to the top.
2. **Given** the main content element does not exist, **When** a route change occurs, **Then** no error is thrown (null guard works).
3. **Given** a cleanup summary overlay mounts, **When** the component renders, **Then** scroll locking is activated.
4. **Given** a catalog page renders, **When** inspecting the DOM, **Then** the expected section anchor IDs are present for deep linking.

---

### User Story 6 — Increase Frontend Test Coverage for Board Components (Priority: P3)

As a user interacting with the board view (agent pipeline management), I expect the cleanup workflow, pipeline stage management, and agent selection to function correctly. Tests should cover these interactive components so that regressions are caught before release.

Board component coverage sits at 42%. Key interactive components like the cleanup button, pipeline stages section, and agent popover have no dedicated tests.

**Why this priority**: The board is a central interactive surface but its components are lower risk than server-side bugs. Smoke and accessibility tests for lower-priority overlay and drag components provide baseline coverage without over-investing.

**Independent Test**: Each component test can be run independently with mocked props and context providers.

**Acceptance Scenarios**:

1. **Given** the cleanup button component, **When** the user initiates the cleanup workflow, **Then** the full orchestration sequence executes (confirmation, processing, completion).
2. **Given** the pipeline stages section, **When** stages are displayed with agent dropdowns, **Then** the correct stages and agent options render.
3. **Given** the add-agent popover, **When** triggered, **Then** agent options load asynchronously and display correctly.
4. **Given** drag overlay and cell components, **When** rendered, **Then** they produce valid accessible markup without errors.

---

### Edge Cases

- What happens when the polling state lock is contended under high concurrency? The system should serialize access without deadlock, and performance should not degrade noticeably for the expected low-contention workload.
- What happens when the deprecated mock functions are completely removed from the codebase? All tests should still pass, confirming the stale mocks have been fully replaced.
- What happens when the agent preview extraction receives an empty configuration object (not just malformed)? The guard should handle this gracefully, returning the safe fallback.
- What happens when the MCP middleware receives an expired token versus a malformed token? Each should produce a distinct, appropriate error response.
- What happens when a page transition animation class is applied but the main content element is null? The null guard should prevent errors without visible side effects.
- What happens when a board drag overlay component receives missing or undefined props? It should render safely or show a graceful fallback.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST serialize all concurrent mutations to the polling state so that no field update is lost due to a race condition.
- **FR-002**: System MUST ensure that the polling startup sequence creates at most one polling task per session, even when invoked concurrently by multiple callers.
- **FR-003**: The concurrency tests that were previously marked as expected failures MUST pass reliably without that marker.
- **FR-004**: All test mocks in the API project test suite MUST target the currently-used production functions, not deprecated ones.
- **FR-005**: After updating stale mocks, zero references to the deprecated function names MUST remain in the affected test file.
- **FR-006**: A regression test MUST exist that validates the agent preview extraction returns a safe fallback when given malformed tools configuration input.
- **FR-007**: The MCP authentication middleware MUST have tests covering valid tokens, missing authorization headers, malformed tokens, and context cleanup.
- **FR-008**: The MCP tool endpoints MUST have tests covering CRUD operations, error dictionary responses, boundary/limit conditions, and session handling.
- **FR-009**: The MCP resource and prompt handlers MUST have tests covering all resource type branches and prompt template selection paths.
- **FR-010**: The template routes MUST have tests covering category enum filtering, 404 responses, and pagination.
- **FR-011**: A page transition test MUST exist that verifies scroll-to-top behavior on route change, null element guard, and animation class application.
- **FR-012**: The cleanup summary test MUST verify that scroll locking is activated with the correct parameter on component mount.
- **FR-013**: Page-level tests MUST verify that expected section anchor IDs render in the DOM for all catalog pages.
- **FR-014**: The board cleanup button component MUST have a test covering the full cleanup orchestration workflow.
- **FR-015**: The pipeline stages section MUST have a test covering stage rendering and agent dropdown display.
- **FR-016**: The add-agent popover MUST have a test covering asynchronous agent option loading.
- **FR-017**: Drag overlay and supporting board cell/config/preset components MUST have at minimum smoke and accessibility tests.

### Key Entities

- **Polling State**: Represents the current status of a copilot polling session, including fields that track progress, results, and completion. Mutations to this state must be coordinated to prevent corruption.
- **Polling Task**: A background process that periodically checks for copilot completion. Exactly one task should exist per active session.
- **Agent Preview**: A summary representation of an agent, extracted from its tools configuration. Must handle malformed input gracefully.
- **MCP Server Components**: The set of middleware, tool handlers, resource providers, and prompt templates that constitute the Model Context Protocol server layer.
- **Board Components**: Frontend interactive components for managing the agent pipeline, including cleanup workflows, stage management, agent selection, and drag-and-drop overlays.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Both previously-expected-to-fail concurrency tests pass reliably across 10 consecutive test runs with zero flakiness.
- **SC-002**: Backend unit test coverage rises from 79% to 81% or higher.
- **SC-003**: Frontend overall test coverage rises from 42% to 55% or higher for board components.
- **SC-004**: Zero references to deprecated mock function names remain in the API project test file.
- **SC-005**: All new backend test files (middleware, tools, resources, templates) achieve at least 80% line coverage for their target modules.
- **SC-006**: All new frontend test files pass without warnings or errors.
- **SC-007**: No new type errors are introduced (both backend and frontend type checking passes cleanly).
- **SC-008**: The full test suite (backend and frontend) passes end-to-end with no regressions.

## Assumptions

- The concurrency bugs are caused by uncoordinated concurrent access and can be resolved with standard mutual exclusion, which is appropriate given the low-contention nature of these code paths.
- The deprecated mock targets are fully unused in production code and can be safely removed from the test suite without losing meaningful coverage.
- MCP server tests will use unit-level mocking of service dependencies rather than integration-level testing, as full integration testing is planned for a future phase.
- Frontend drag-and-drop interaction testing (complex multi-step DnD sequences) is explicitly excluded from this scope and deferred to a follow-up effort.
- The `otel_setup` module (infrastructure/observability setup) is excluded from coverage targets as it provides marginal test value.
- Backend API branch coverage for chat, pipelines, and MCP routes remains a known gap to be addressed in a follow-up error-path testing initiative.

## Dependencies

- This work depends on the existing concurrency test infrastructure (test files for interleaving and polling races must already exist with expected-failure markers).
- Frontend scroll behavior tests depend on the scroll-to-top and scroll-lock implementations already being merged in the codebase.
- Board component tests depend on the current board component implementations and their existing prop/context interfaces.

## Scope Exclusions

- Deep drag-and-drop interaction testing (multi-step DnD sequences) is deferred.
- `otel_setup.py` coverage is excluded (infrastructure-only, marginal test value).
- Backend API branch coverage improvements for chat, pipelines, and MCP routes beyond the specific modules listed are deferred to a follow-up.
- Activity component coverage verification is deferred to post-implementation analysis.
