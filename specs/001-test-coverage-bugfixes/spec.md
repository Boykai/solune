# Feature Specification: Increase Test Coverage & Fix Discovered Bugs

**Feature Branch**: `001-test-coverage-bugfixes`  
**Created**: 2026-04-06  
**Status**: Draft  
**Input**: User description: "Increase Test Coverage & Fix Discovered Bugs"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Close Backend Security Gap in MCP Resource Handlers (Priority: P1)

As a project owner, I need the MCP server to enforce project-level access control on all resource endpoints so that unauthenticated or unauthorized requests cannot read project data.

**Why this priority**: This is a security vulnerability. Resource handlers currently skip access verification, meaning any caller who knows a project ID can read data without authorization. Fixing this is the highest-priority item because it protects user data.

**Independent Test**: Can be fully tested by sending requests to each MCP resource endpoint with (a) no credentials, (b) credentials for a different project, and (c) valid credentials. Unauthorized requests must be rejected; authorized requests must succeed.

**Acceptance Scenarios**:

1. **Given** a resource endpoint is called without authentication credentials, **When** the request is processed, **Then** the system rejects the request and returns an unauthorized error.
2. **Given** a resource endpoint is called with valid credentials for a different project, **When** the request is processed, **Then** the system rejects the request and returns a forbidden/unauthorized error.
3. **Given** a resource endpoint is called with valid credentials matching the requested project, **When** the request is processed, **Then** the system returns the requested project data.
4. **Given** all three MCP resource handlers, **When** access control is reviewed, **Then** every handler follows the same authentication and authorization pattern used by tool handlers.

---

### User Story 2 — Fix Backend Middleware Silent Authentication Bypass (Priority: P1)

As a system administrator, I need the authentication middleware to block requests when token verification fails, instead of silently passing them through, so that unauthenticated requests cannot reach protected endpoints.

**Why this priority**: A failed token verification currently sets context to null and still forwards the request, which defeats the purpose of authentication middleware. This is a security-critical fix.

**Independent Test**: Can be tested by sending requests with invalid, missing, or malformed tokens and verifying that a 401 response is returned before the request reaches any handler.

**Acceptance Scenarios**:

1. **Given** a request with a missing authorization header, **When** processed by the middleware, **Then** the system returns a 401 unauthorized response.
2. **Given** a request with a malformed bearer token, **When** processed by the middleware, **Then** the system returns a 401 unauthorized response.
3. **Given** a request with an expired or invalid token, **When** processed by the middleware, **Then** the system returns a 401 unauthorized response.
4. **Given** a request with a valid token, **When** processed by the middleware, **Then** the request passes through to the handler.
5. **Given** a non-HTTP connection scope (e.g., WebSocket lifespan), **When** processed by the middleware, **Then** it passes through without authentication checks.

---

### User Story 3 — Fix Backend Auth Cache Off-by-One Error (Priority: P2)

As a developer, I need the authentication token cache to respect its configured maximum size exactly, so that memory usage remains predictable and bounded.

**Why this priority**: The cache can grow one entry beyond the configured maximum because eviction uses a strict greater-than comparison instead of greater-than-or-equal. While not a security vulnerability, it is a correctness bug that affects memory predictability.

**Independent Test**: Can be tested by configuring a cache with a small maximum size, filling it to capacity, and verifying that adding one more entry triggers eviction before insertion (keeping total entries at or below the limit).

**Acceptance Scenarios**:

1. **Given** the token cache is at its maximum configured size, **When** a new entry is added, **Then** the oldest entry is evicted before insertion, keeping total entries at or below the maximum.
2. **Given** the token cache has fewer entries than the maximum, **When** a new entry is added, **Then** no eviction occurs and the new entry is stored.

---

### User Story 4 — Add Graceful Degradation for Observability Setup (Priority: P2)

As a platform operator, I need the application to start successfully even when the observability/telemetry endpoint is unreachable, so that a telemetry infrastructure outage does not block application startup.

**Why this priority**: Currently, an unreachable telemetry endpoint causes a crash on startup, which means a monitoring infrastructure failure cascades into an application outage — the opposite of graceful degradation.

**Independent Test**: Can be tested by starting the application with a non-existent telemetry endpoint and verifying the app starts normally with telemetry disabled.

**Acceptance Scenarios**:

1. **Given** the telemetry endpoint is unreachable, **When** the application starts, **Then** it starts successfully with telemetry disabled and logs a warning.
2. **Given** the telemetry endpoint is reachable, **When** the application starts, **Then** telemetry initializes normally.

---

### User Story 5 — Fix Frontend Render-Time State Mutations (Priority: P2)

As a user interacting with modals and selectors, I need form state to be preserved correctly so that typing in a search field or interacting with form controls does not unexpectedly reset my input.

**Why this priority**: Two components (AddAgentModal, ToolSelectorModal) clear or reset state during render, which violates framework rules and causes user-visible bugs: error messages flash and disappear, search input resets unexpectedly.

**Independent Test**: Can be tested by opening each affected modal, interacting with form fields (triggering validation errors, typing in search), and verifying the state persists across re-renders.

**Acceptance Scenarios**:

1. **Given** the AddAgentModal is open and displays a validation error, **When** the component re-renders, **Then** the error message remains visible until the user corrects the input.
2. **Given** the ToolSelectorModal is open and the user has typed a search query, **When** the component re-renders, **Then** the search query and results are preserved.

---

### User Story 6 — Fix Frontend Event Listener and Animation Cleanup (Priority: P2)

As a user navigating between views, I need UI components to properly clean up event listeners and animation frames when they unmount, so that I do not experience ghost interactions or memory leaks.

**Why this priority**: Two components have cleanup bugs — AddChoreModal's Escape key listener is torn down and re-added on every render (causing potential missed keypresses), and ChoreCard's animation frame can fire after unmount (causing potential errors or stale UI updates).

**Independent Test**: Can be tested by mounting and unmounting each component and verifying no residual listeners or animation callbacks persist.

**Acceptance Scenarios**:

1. **Given** the AddChoreModal is open, **When** the user presses Escape, **Then** the modal closes reliably regardless of how many re-renders have occurred.
2. **Given** a ChoreCard with an active pipeline menu animation, **When** the card unmounts, **Then** the pending animation frame is cancelled and no callback fires.

---

### User Story 7 — Fix Frontend CommandPalette Tab Focus Trap (Priority: P3)

As a keyboard-navigation user, I need the CommandPalette to handle Tab key behavior correctly even when no focusable elements are present, so that pressing Tab does not cause the focus to escape the palette unexpectedly.

**Why this priority**: When no focusable elements exist inside the CommandPalette, the Tab handler returns early without preventing default behavior, allowing focus to leave the component.

**Independent Test**: Can be tested by opening the CommandPalette with an empty result set and pressing Tab — focus should remain within the palette.

**Acceptance Scenarios**:

1. **Given** the CommandPalette is open with no focusable elements, **When** the user presses Tab, **Then** focus remains within the CommandPalette (default Tab behavior is prevented).
2. **Given** the CommandPalette is open with focusable elements, **When** the user presses Tab, **Then** focus cycles through the elements as expected.

---

### User Story 8 — Achieve Backend Test Coverage Targets (Priority: P2)

As a development team, we need comprehensive test suites for the middleware, resource handlers, authentication edge cases, and observability setup so that all bug fixes (Stories 1–4) are regression-protected and backend coverage reaches ≥ 75%.

**Why this priority**: Tests are essential to confirm the security fixes work and to prevent regressions. They also ensure the CI coverage gate passes.

**Independent Test**: Can be tested by running the backend test suite and confirming coverage ≥ 75% with all tests passing.

**Acceptance Scenarios**:

1. **Given** the middleware test suite, **When** run, **Then** it covers valid token flow, missing header, malformed bearer, empty token, exception propagation, non-HTTP scope, and 401 on failed auth (target ≥ 90% middleware coverage).
2. **Given** the resource handler test suite, **When** run, **Then** it covers valid project access, invalid project ID, unauthorized project, service exceptions, and serialization (target ≥ 80% resource handler coverage).
3. **Given** the auth edge-case test suite, **When** run, **Then** it covers cache eviction at limit, rate limit cleanup, HTTP timeout, and API error responses.
4. **Given** the observability test suite, **When** run, **Then** it covers initialization with an unreachable endpoint, request ID span processing, and graceful degradation.

---

### User Story 9 — Achieve Frontend Test Coverage Targets (Priority: P2)

As a development team, we need test suites for hooks, modals, and key UI components so that all frontend bug fixes (Stories 5–7) are regression-protected and frontend coverage meets CI thresholds (≥ 50% statements, ≥ 44% branches).

**Why this priority**: Frontend coverage is currently estimated at 45–48% statements, below the 50% CI gate. New tests for hooks, modals, and grid components push coverage above the threshold.

**Independent Test**: Can be tested by running the frontend test suite with coverage reporting and confirming thresholds are met.

**Acceptance Scenarios**:

1. **Given** the useCountdown hook test suite, **When** run, **Then** it covers countdown decrement, expiration at zero, prop change reset, interval cleanup, and format edge cases.
2. **Given** the useFirstErrorFocus hook test suite, **When** run, **Then** it covers first-field focus, key ordering, no-op on null ref, and no-op without errors.
3. **Given** the modal test suites (AddAgentModal, AddChoreModal, ConfirmChoreModal), **When** run, **Then** they cover create/edit flows, validation, dirty-state detection, escape handling, and templates.
4. **Given** the component test suites (ChoresGrid, ChoreScheduleConfig, InstallConfirmDialog, ToolSelectorModal, CommandPalette), **When** run, **Then** they cover primary interaction flows, edge cases, and accessibility scenarios.
5. **Given** the full frontend test suite with coverage, **When** run, **Then** statement coverage ≥ 50%, branch coverage ≥ 44%, function coverage ≥ 41%, and line coverage ≥ 50%.

---

### Edge Cases

- What happens when a token verification call throws an unexpected exception in the middleware? The middleware must catch the exception and return a 401 response rather than crashing the server.
- What happens when the auth cache eviction is triggered concurrently? The cache should remain consistent and never exceed its maximum size.
- What happens when a modal is opened and closed rapidly in succession? Event listeners and animation frames should be fully cleaned up with no residual callbacks.
- What happens when the observability endpoint becomes unreachable after initial successful connection? The application should continue running; only startup initialization needs the graceful fallback.
- What happens when a resource handler receives a valid token but the referenced project does not exist? The handler should return an appropriate not-found error after successful authentication.

## Requirements *(mandatory)*

### Functional Requirements

**Phase 1 — Backend Security & Coverage (HIGH PRIORITY)**

- **FR-001**: All MCP resource handlers MUST verify authentication and project-level access before returning data, matching the pattern used by existing tool handlers.
- **FR-002**: The authentication middleware MUST return a 401 response when token verification fails, rather than forwarding the request with null context.
- **FR-003**: The token cache MUST evict the oldest entry when the cache reaches (not exceeds) its maximum configured size.
- **FR-004**: The observability initialization MUST catch connection errors and fall back to a no-op configuration, logging a warning, rather than crashing the application.
- **FR-005**: Middleware tests MUST cover valid token, missing header, malformed bearer, empty token, exception propagation, non-HTTP scope, and 401 on failed auth scenarios (≥ 90% middleware code coverage).
- **FR-006**: Resource handler tests MUST cover valid project, invalid project ID, unauthorized project, service exceptions, and serialization scenarios (≥ 80% resource handler code coverage).
- **FR-007**: Auth edge-case tests MUST cover cache eviction at limit, rate limit cleanup, HTTP timeout, and API error responses.
- **FR-008**: Observability tests MUST cover initialization with an unreachable endpoint, request ID span processing, and graceful degradation.

**Phase 2 — Frontend Bug Fixes & Hook Tests (MEDIUM PRIORITY)**

- **FR-009**: The AddAgentModal MUST NOT mutate state during render; error clearing MUST be moved to an effect.
- **FR-010**: The AddChoreModal MUST NOT re-add the Escape key listener on every render; the close callback MUST be stored in a ref.
- **FR-011**: The ChoreCard MUST cancel any pending animation frame when the component unmounts.
- **FR-012**: The ToolSelectorModal MUST NOT reset user search input during render; initialization MUST be moved to an effect.
- **FR-013**: The CommandPalette MUST prevent default Tab behavior even when no focusable elements are present inside the palette.
- **FR-014**: Hook test suites (useCountdown, useFirstErrorFocus) MUST cover all primary behaviors and edge cases.
- **FR-015**: Modal test suites (AddAgentModal, AddChoreModal) MUST cover create/edit flows, validation, dirty-state, and escape handling.

**Phase 3 — Frontend Coverage Push (CI THRESHOLD)**

- **FR-016**: New component test suites MUST be created for ConfirmChoreModal, ChoresGrid, ChoreScheduleConfig, and InstallConfirmDialog.
- **FR-017**: ToolSelectorModal and CommandPalette test suites MUST cover both the bug fix and standard interaction flows.

### Scope Boundaries

**In scope:**
- 4 backend source fixes (resources auth, middleware auth bypass, cache off-by-one, otel graceful degradation)
- 4 backend test files (middleware, resources, auth edge cases, otel)
- 5 frontend bug fixes (AddAgentModal, AddChoreModal, ChoreCard, ToolSelectorModal, CommandPalette)
- 10 frontend test files (2 hooks, 8 components)

**Excluded from scope:**
- Settings components
- Presentational components (AgentAvatar, AgentCard, ToolCard, etc.)
- Chat skeleton components
- PageTransition component
- Any new features or refactoring beyond the identified bugs

### Assumptions

- The existing tool handler authentication pattern in the MCP server is the correct pattern to replicate for resource handlers.
- Backend test coverage baseline is below 75% and needs the new test suites to reach that threshold.
- Frontend test coverage baseline is approximately 45–48% statements and needs ~15–20% additional coverage from new test files to clear the 50% CI gate.
- The observability fallback only needs to handle startup initialization failures; runtime telemetry failures are out of scope.
- Existing test infrastructure and tooling (backend: pytest + coverage; frontend: vitest + coverage) are sufficient for all new tests.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All backend unit tests pass with ≥ 75% overall code coverage.
- **SC-002**: All frontend unit tests pass with statement coverage ≥ 50%, branch coverage ≥ 44%, function coverage ≥ 41%, and line coverage ≥ 50%.
- **SC-003**: Unauthorized requests to all MCP resource endpoints are rejected (verified by test assertions on each handler).
- **SC-004**: Requests with invalid, missing, or malformed tokens are rejected with a 401 response at the middleware layer.
- **SC-005**: The application starts successfully when the telemetry endpoint is unreachable, with no crash or unhandled exception.
- **SC-006**: 8 identified bugs are fixed and each fix has at least one regression test.
- **SC-007**: All existing linting, type-checking, and build steps continue to pass with zero new errors.
- **SC-008**: ~19 implementation steps are completed across 3 phases (4 backend fixes, 4 backend test files, 5 frontend fixes, 10 frontend test files).
