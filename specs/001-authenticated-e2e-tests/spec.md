# Feature Specification: Add Authenticated E2E Tests for Core Application

**Feature Branch**: `001-authenticated-e2e-tests`  
**Created**: 2026-03-30  
**Status**: Draft  
**Input**: User description: "Add Authenticated E2E Tests for Core Application"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Authenticated Session Lifecycle Verification (Priority: P1)

As a developer, I need end-to-end tests that verify the full authentication lifecycle — login, session persistence across multiple requests, and logout — so that I can confidently ship auth-related changes without manually verifying session cookie handling, token management, and session invalidation.

**Why this priority**: Authentication is the gateway to all protected functionality. Every other authenticated flow depends on a working session lifecycle. Without verified session bootstrapping and cookie reuse, no downstream E2E test can function. This is the foundation that all other test suites build upon.

**Independent Test**: Can be fully tested by exercising the dev-login endpoint, verifying cookie issuance, making authenticated requests to the user-info endpoint, logging out, and confirming the session is invalidated. Delivers confidence that the cookie-based auth flow works end-to-end.

**Acceptance Scenarios**:

1. **Given** a running application with authentication enabled, **When** a user logs in via the dev-login endpoint with valid credentials, **Then** a session cookie is issued and the user-info endpoint returns the authenticated user's details.
2. **Given** an authenticated session with a valid cookie, **When** the user logs out, **Then** the session is invalidated and subsequent requests to protected endpoints return a 401 Unauthorized response.
3. **Given** an expired session, **When** a request is made with the expired session cookie, **Then** the system returns a 401 Unauthorized response.
4. **Given** a request with an invalid or tampered session cookie, **When** the request reaches a protected endpoint, **Then** the system returns a 401 Unauthorized response.

---

### User Story 2 - Authenticated Project Operations Verification (Priority: P2)

As a developer, I need end-to-end tests that verify project listing, selection, detail retrieval, and task creation under an authenticated session, so that I can ensure the core project management CRUD operations work correctly when accessed by a real authenticated user with session state preserved across requests.

**Why this priority**: Project operations are the primary interaction surface for users. Selecting a project updates session state, and all downstream features (tasks, chat, pipelines, boards) depend on a selected project. Verifying this flow catches regressions in session-state propagation and project access control.

**Independent Test**: Can be fully tested by authenticating, listing available projects, selecting a project, verifying the session reflects the selection, retrieving project details, listing tasks, and creating a new task. Delivers confidence that the project CRUD flow works with real session state.

**Acceptance Scenarios**:

1. **Given** an authenticated user with access to projects, **When** the user lists projects, **Then** the system returns the user's accessible projects.
2. **Given** an authenticated user, **When** the user selects a project, **Then** the session is updated to reflect the selected project and subsequent requests use that project context.
3. **Given** an authenticated user with a selected project, **When** the user retrieves project details, **Then** the system returns the correct project information.
4. **Given** an authenticated user with a selected project, **When** the user lists tasks for that project, **Then** the system returns the project's tasks.
5. **Given** an authenticated user with a selected project, **When** the user creates a new task, **Then** the task is persisted and appears in subsequent task listings.

---

### User Story 3 - Authenticated Chat Flow Verification (Priority: P3)

As a developer, I need end-to-end tests that verify chat message sending, history retrieval, and project-selection validation within an authenticated session, so that I can ensure the chat feature correctly enforces project context requirements and persists conversation history.

**Why this priority**: Chat is a core user interaction that depends on both authentication and project selection. Testing it E2E validates that the require-selected-project guard works correctly and that message persistence functions across multiple requests within the same session.

**Independent Test**: Can be fully tested by authenticating, selecting a project, sending a chat message, retrieving chat history, and verifying that sending a message without a selected project is rejected. Delivers confidence that chat operations enforce project context and persist data correctly.

**Acceptance Scenarios**:

1. **Given** an authenticated user with a selected project, **When** the user sends a chat message, **Then** the message is accepted and stored.
2. **Given** an authenticated user with a selected project who has sent messages, **When** the user retrieves chat history, **Then** all previously sent messages are returned in order.
3. **Given** an authenticated user without a selected project, **When** the user attempts to send a chat message, **Then** the system rejects the request with an appropriate error indicating a project must be selected.

---

### User Story 4 - Authenticated Pipeline CRUD Verification (Priority: P4)

As a developer, I need end-to-end tests that verify pipeline listing, creation, project assignment, and lifecycle operations under an authenticated session, so that I can ensure pipeline management works correctly with real authentication and session state.

**Why this priority**: Pipeline operations involve multi-step workflows (create → assign → run) that span multiple requests. Testing these flows E2E catches state management bugs that unit tests miss, particularly around session-scoped pipeline access and lifecycle transitions.

**Independent Test**: Can be fully tested by authenticating, creating a pipeline, assigning it to a project, triggering lifecycle operations, and verifying state transitions. Delivers confidence that the pipeline CRUD and lifecycle flow works end-to-end.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** the user lists pipelines, **Then** the system returns available pipelines.
2. **Given** an authenticated user, **When** the user creates a new pipeline, **Then** the pipeline is persisted and appears in subsequent listings.
3. **Given** an authenticated user with a pipeline and a selected project, **When** the user assigns the pipeline to the project, **Then** the assignment is persisted.
4. **Given** an authenticated user with an assigned pipeline, **When** the user triggers a pipeline run, **Then** the pipeline transitions through its lifecycle states correctly.

---

### User Story 5 - Authenticated Board Operations Verification (Priority: P5)

As a developer, I need end-to-end tests that verify board column retrieval and task movement between columns under an authenticated session, so that I can ensure the kanban board functionality works correctly with real authentication and project context.

**Why this priority**: Board operations (viewing columns, moving tasks) are the visual workflow management interface. Testing these E2E ensures that column data loads correctly and task state transitions are persisted — catching regressions that mock-heavy unit tests may miss.

**Independent Test**: Can be fully tested by authenticating, selecting a project, retrieving board columns, and moving a task between columns. Delivers confidence that board operations work with real session state and project context.

**Acceptance Scenarios**:

1. **Given** an authenticated user with a selected project, **When** the user retrieves board columns, **Then** the system returns the project's board column configuration.
2. **Given** an authenticated user with a selected project and tasks on the board, **When** the user moves a task from one column to another, **Then** the task's column assignment is updated and reflected in subsequent board retrievals.

---

### User Story 6 - Frontend Authenticated E2E Flows (Priority: P6)

As a developer, I need frontend end-to-end tests that verify authenticated UI flows — dashboard rendering, project selection, kanban board display, and page navigation — with realistic API responses, so that I can ensure the frontend correctly handles authenticated state and renders data from the backend.

**Why this priority**: This is an optional follow-up to the backend E2E suite. The existing frontend E2E tests already cover UI rendering with mocked API calls. Adding authenticated fixtures extends coverage to verify the frontend handles real authenticated API response shapes correctly, but is lower priority since the backend E2E suite provides the primary regression safety net.

**Independent Test**: Can be fully tested by extending the existing frontend E2E fixture pattern to return authenticated user data and realistic API responses, then verifying that the dashboard renders, project selector works, kanban board shows tasks, and navigation between pages functions correctly.

**Acceptance Scenarios**:

1. **Given** the frontend is loaded with an authenticated mock user, **When** the dashboard page renders, **Then** it displays the user's projects and navigation elements.
2. **Given** the frontend is loaded with authenticated mock data, **When** the user selects a project from the project selector, **Then** the UI updates to show the selected project's data.
3. **Given** the frontend is loaded with authenticated mock data for a selected project, **When** the kanban board page loads, **Then** it displays the project's tasks organized in columns.

---

### Edge Cases

- What happens when the session expires mid-flow (e.g., between listing projects and selecting one)?
- How does the system handle concurrent requests with the same session cookie?
- What happens when a user's project access is revoked between session creation and a subsequent project request?
- How does the system behave when the database is unavailable during session lookup?
- What happens when a session cookie references a session that was deleted (e.g., by another logout in a different browser)?
- How does the dev-login endpoint behave when provided with an empty or malformed token?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The test suite MUST provide a shared authenticated client fixture that bootstraps a session via the dev-login endpoint, captures the session cookie, and reuses it across multiple requests within a test
- **FR-002**: The test suite MUST use a real in-memory database with all migrations applied, preserving real data persistence and query behavior
- **FR-003**: The test suite MUST mock external services (third-party API calls, AI agent services, WebSocket manager) to avoid network dependencies while keeping internal application services (session store, database, authentication middleware) unpatched
- **FR-004**: The test suite MUST verify the complete authentication lifecycle: login → session cookie issuance → authenticated request → logout → session invalidation
- **FR-005**: The test suite MUST verify that expired sessions and invalid cookies are correctly rejected with 401 Unauthorized responses
- **FR-006**: The test suite MUST verify multi-request authenticated flows where session state changes (e.g., project selection) persist across subsequent requests
- **FR-007**: The test suite MUST verify project operations: listing projects, selecting a project, retrieving project details, listing tasks, and creating tasks — all under an authenticated session
- **FR-008**: The test suite MUST verify chat operations: sending messages, retrieving history, and enforcing the requirement that a project must be selected before sending messages
- **FR-009**: The test suite MUST verify pipeline operations: listing, creating, assigning to a project, and running lifecycle transitions — all under an authenticated session
- **FR-010**: The test suite MUST verify board operations: retrieving board columns and moving tasks between columns — all under an authenticated session
- **FR-011**: Each test MUST run in isolation with a fresh application instance and database, with no shared state between tests
- **FR-012**: The test suite MUST not regress any existing tests — all pre-existing test suites must continue to pass after the new tests are added
- **FR-013**: The frontend authenticated E2E fixtures MUST extend the existing unauthenticated fixture pattern, returning authenticated user data and realistic API responses for core endpoints

### Key Entities

- **Authenticated Test Client**: A reusable test component that holds a valid session cookie obtained via dev-login, enabling multi-request authenticated flows without per-test authentication setup
- **Test Database**: A fresh in-memory database instance with all migrations applied, providing real data persistence behavior while ensuring test isolation
- **Mock External Services**: Substitutes for network-dependent services (third-party API, AI agents, WebSocket) that return predictable responses, enabling offline test execution

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of core authenticated flows (auth lifecycle, projects, chat, pipelines, boards) are covered by at least one multi-request E2E test that exercises login → action → verification
- **SC-002**: All new E2E tests pass consistently (zero flaky failures) when run in isolation and as part of the full test suite
- **SC-003**: The existing test suite experiences zero regressions — all pre-existing tests continue to pass after the new tests are added
- **SC-004**: Each authenticated E2E test completes within 5 seconds, ensuring the test suite remains fast enough for developer feedback loops
- **SC-005**: Session invalidation scenarios (expired session, invalid cookie, post-logout access) are verified to return appropriate error responses within 1 second
- **SC-006**: Multi-request flows verify that session state changes (e.g., project selection) persist correctly across at least 3 sequential requests within the same test

### Assumptions

- The dev-login endpoint is the appropriate mechanism for session bootstrapping in tests, as it exercises the real cookie/session flow without requiring real third-party credentials
- An in-memory database with migrations applied provides sufficient fidelity for E2E testing — production-specific database behaviors (connection pooling, concurrent writes) are out of scope
- External service mocking is acceptable for E2E tests since the goal is to verify application flow correctness, not third-party service integration
- Phase 1 (backend E2E) is the priority deliverable; Phase 2 (frontend authenticated E2E) is an optional follow-up
- Test isolation via fresh app and database per test is preferred over shared state with cleanup, accepting the performance tradeoff for reliability
- The existing frontend E2E tests provide adequate UI rendering coverage; the frontend authenticated E2E extension focuses on verifying correct handling of authenticated API response shapes
