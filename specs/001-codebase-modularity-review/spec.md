# Feature Specification: Codebase Modularity Review

**Feature Branch**: `001-codebase-modularity-review`  
**Created**: 2026-04-12  
**Status**: Draft  
**Input**: User description: "Codebase Modularity Review — decompose 6 monolithic hotspots across backend and frontend into domain-scoped modules to improve maintainability, testability, and code-review ergonomics."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Navigates and Edits Backend Chat Endpoints Without Wading Through Thousands of Lines (Priority: P1)

A developer receives a bug report about how chat messages are sent. Today, they must open a single 2,930-line file (`api/chat.py`), scroll through 25 route handlers spanning conversations, messages, proposals, plans, uploads, and streaming to find the relevant code. After the refactoring, they navigate directly to a domain-scoped module (e.g., `api/chat/messages.py`) containing only the message-related routes. They make their change, run the module's tests, and submit a focused pull request that reviewers can assess in minutes rather than having to parse unrelated code.

**Why this priority**: The monolithic `api/chat.py` is the single largest maintainability bottleneck in the codebase. Every backend feature that touches chat — the core product surface — forces developers into a 2,930-line file. Splitting it is the highest-leverage improvement identified in the review.

**Independent Test**: A developer can open any one of the new chat sub-modules (conversations, messages, proposals, plans, streaming), make an isolated change, and verify it compiles and passes tests without touching other chat sub-modules.

**Acceptance Scenarios**:

1. **Given** a developer needs to modify message-sending behavior, **When** they navigate to the chat API code, **Then** they find a dedicated `messages` module containing only message-related endpoints (no proposal, plan, or streaming code).
2. **Given** the chat API package exists with sub-modules, **When** a developer imports from the chat API using existing import paths, **Then** all imports resolve correctly without modification to consuming code.
3. **Given** the backend test suite runs after the split, **When** all existing tests execute, **Then** every test passes with identical behavior to the pre-split state (zero functional regressions).

---

### User Story 2 - Developer Tests Proposal Confirmation Logic in Isolation (Priority: P1)

A developer needs to debug or extend the proposal confirmation flow — a critical workflow that spans GitHub issue creation, agent assignment, polling start, and WebSocket broadcasting. Today, this logic lives inside a single ~350-line function (`confirm_proposal()`) embedded in the monolithic chat file, making it impossible to unit-test individual phases. After the refactoring, each phase (validation, GitHub API interaction, workflow setup, agent assignment, status broadcasting) is an independently testable method on a `ProposalOrchestrator` service class. The developer writes a focused unit test for just the failing phase without mocking the other six.

**Why this priority**: The `confirm_proposal()` function is the highest-risk code path in the backend — it orchestrates 7 external service integrations in a single untestable block. Any regression here breaks the core product workflow. Making it testable in isolation directly reduces defect risk.

**Independent Test**: A developer can instantiate `ProposalOrchestrator` with mocked dependencies and invoke any single orchestration phase, verifying its behavior without exercising the other phases.

**Acceptance Scenarios**:

1. **Given** a `ProposalOrchestrator` class exists, **When** a developer creates an instance with mocked dependencies, **Then** each orchestration phase (validation, GitHub API, workflow setup, agent assignment, broadcasting) can be tested independently.
2. **Given** the proposal endpoint calls the orchestrator, **When** a user confirms a proposal through the UI, **Then** the behavior is identical to the pre-extraction flow (same HTTP responses, same side effects, same error handling).

---

### User Story 3 - Developer Modifies a Single Domain's API Client Without Reviewing 1,800 Lines (Priority: P2)

A frontend developer needs to update how the board API handles pagination. Today, they must open the 1,876-line `services/api.ts` file and locate the `boardApi` namespace among 17 other namespace objects. After the refactoring, they navigate directly to `services/api/board.ts`, make the change, and submit a review-friendly pull request. The 63+ files that import from `@/services/api` continue working without changes because a barrel `index.ts` re-exports all namespaces.

**Why this priority**: The monolithic API client is the frontend equivalent of `api/chat.py` — a single file that every domain touches. Splitting it improves code-review efficiency, enables domain-scoped code-splitting, and reduces merge conflicts when multiple developers work on different API domains simultaneously.

**Independent Test**: A developer can modify a single domain API file (e.g., `api/board.ts`), verify the TypeScript compiler finds no errors, and confirm that all existing imports resolve correctly via the barrel re-export.

**Acceptance Scenarios**:

1. **Given** the API client is split into domain files, **When** a developer imports `boardApi` from `@/services/api`, **Then** the import resolves correctly through the barrel re-export.
2. **Given** the frontend test suite runs after the split, **When** all existing tests execute, **Then** every test passes with identical behavior to the pre-split state.
3. **Given** 63+ consumer files import from `@/services/api`, **When** the split is complete, **Then** zero consumer files require import path changes.

---

### User Story 4 - Developer Finds and Updates Domain Types Without Scanning 1,500 Lines (Priority: P2)

A frontend developer needs to add a field to the `ChatMessage` type. Today, they open the 1,525-line `types/index.ts` and search among 199 exported types across 25+ domain sections. After the refactoring, they navigate to `types/chat.ts`, find `ChatMessage` immediately among only chat-related types, and make the change. The 202 files that import from `@/types` continue working without changes.

**Why this priority**: The monolithic types file is the second most-imported file in the frontend. Domain-scoping types reduces cognitive load and merge conflicts while preserving backward compatibility through barrel re-exports.

**Independent Test**: A developer can modify a domain types file (e.g., `types/chat.ts`), verify the TypeScript compiler finds no errors, and confirm that all existing imports resolve correctly.

**Acceptance Scenarios**:

1. **Given** types are split into domain files, **When** a developer imports `ChatMessage` from `@/types`, **Then** the import resolves correctly through the barrel re-export.
2. **Given** 202 consumer files import from `@/types`, **When** the split is complete, **Then** zero consumer files require import path changes.

---

### User Story 5 - Developer Manages Chat State Through a Structured Interface (Priority: P3)

A developer investigating a race condition in the chat message cache encounters module-level dictionary globals (`_messages`, `_proposals`, `_locks`) with no lifecycle management. Today, there is no way to reset state between tests or inspect cache contents during debugging. After the refactoring, these globals are consolidated into a `ChatStateManager` class with explicit methods for state access, lifecycle management (clear on shutdown), and constructor-based dependency injection for testing.

**Why this priority**: The module-level globals create race condition risks and make integration testing fragile. While the risk hasn't caused production incidents yet, consolidation into a managed class is a low-cost change that eliminates a category of potential bugs.

**Independent Test**: A developer can instantiate `ChatStateManager` in a test, perform cache operations, and verify behavior without any module-level side effects.

**Acceptance Scenarios**:

1. **Given** a `ChatStateManager` instance, **When** messages are stored and retrieved, **Then** the cache behaves identically to the module-level dictionaries (same read-through cache semantics, same persistence).
2. **Given** the application shuts down, **When** the lifespan cleanup runs, **Then** all cached state is explicitly cleared through the `ChatStateManager` interface.

---

### User Story 6 - Developer Reviews Webhook Handlers by Event Type (Priority: P3)

A developer debugging a failing GitHub pull request webhook must today scan the 1,033-line `api/webhooks.py` to find the PR-specific handler among check-run, check-suite, and general dispatch logic. After the refactoring, they navigate to `api/webhooks/pull_requests.py` for PR handling or `api/webhooks/ci.py` for CI-related events.

**Why this priority**: Webhook handling is event-driven and naturally segments by event type. The split aligns file structure with how developers reason about webhook debugging (by event type, not by shared infrastructure).

**Independent Test**: A developer can modify a webhook sub-module (e.g., `pull_requests.py`) and verify its behavior through the existing webhook integration tests.

**Acceptance Scenarios**:

1. **Given** webhooks are split by event type, **When** a PR webhook arrives, **Then** it is dispatched to the `pull_requests` module and processed identically to the pre-split behavior.
2. **Given** the webhook test suite runs after the split, **When** all webhook integration tests execute, **Then** every test passes with identical behavior.

---

### User Story 7 - Developer Reads and Tests Bootstrap Logic Independently from Application Factory (Priority: P3)

A developer investigating a startup failure in the background service initialization must today scan the 859-line `main.py` to separate application factory code, middleware registration, route mounting, and lifespan bootstrap logic. After the refactoring, bootstrap-specific functions (database init, service registration, background task startup, shutdown) live in a dedicated `services/bootstrap.py` module, testable in isolation.

**Why this priority**: While `main.py` is less frequently edited than `chat.py`, its mixed responsibilities make startup debugging harder than necessary. Extracting bootstrap functions improves testability with minimal risk.

**Independent Test**: A developer can import and test individual bootstrap functions (e.g., `start_background_services()`) with mocked dependencies.

**Acceptance Scenarios**:

1. **Given** bootstrap functions are extracted, **When** the application starts, **Then** the lifespan delegates to bootstrap functions and all startup behavior is identical to the pre-extraction state.
2. **Given** bootstrap functions exist in a separate module, **When** a developer writes a unit test for `start_background_services()`, **Then** they can mock all dependencies without loading the full application.

---

### Edge Cases

- What happens when a circular import is introduced between the new sub-modules (e.g., `messages.py` importing from `proposals.py`)? Sub-modules must only import from shared utilities or the `ChatStateManager`, never from sibling sub-modules. Import validation should flag violations.
- How does the system handle if a barrel re-export is accidentally removed from `index.ts`? The TypeScript compiler will immediately fail for any consumer that depends on the removed export, providing a clear error message. CI builds catch this.
- What happens when `ChatStateManager` is not initialized before a request arrives during startup? FastAPI's lifespan ensures the manager is set on `app.state` before routes become available. Requests arriving before lifespan completion receive a 503 Service Unavailable from the framework.
- What if a webhook event type is added in the future that doesn't fit `pull_requests.py` or `ci.py`? The `handlers.py` dispatcher remains the single entry point and can route to new sub-modules without changing the dispatch pattern.
- How are test patch paths affected after the splits? Tests that patch at the module level (e.g., `src.api.chat.get_settings`) must be updated to patch at the sub-module level (e.g., `src.api.chat.messages.get_settings`). Barrel re-exports in `__init__.py` do not affect patch resolution.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST split the monolithic `api/chat.py` (2,930 lines, 25 routes) into a package with domain-scoped sub-modules: conversations, messages, proposals, plans, and streaming.
- **FR-002**: The system MUST extract the `confirm_proposal()` function (~350 lines, 7 orchestration phases) into a `ProposalOrchestrator` service class with independently testable methods per phase.
- **FR-003**: The system MUST split the monolithic `services/api.ts` (1,876 lines, 17+ namespace objects) into domain-scoped files within a `services/api/` directory with a barrel `index.ts` for backward compatibility.
- **FR-004**: The system MUST split the monolithic `types/index.ts` (1,525 lines, 199 exports) into domain-scoped type files within the `types/` directory with a barrel `index.ts` for backward compatibility.
- **FR-005**: The system MUST consolidate module-level global state dictionaries (`_messages`, `_proposals`, `_recommendations`, `_locks`) into a `ChatStateManager` class with explicit lifecycle management.
- **FR-006**: The system MUST split the monolithic `api/webhooks.py` (1,033 lines) into a package with sub-modules organized by event type: handlers (dispatcher + security), pull requests, and CI events.
- **FR-007**: The system MUST extract startup/shutdown bootstrap logic from `main.py` into a `services/bootstrap.py` module, with the lifespan function delegating to named bootstrap functions.
- **FR-008**: All existing import paths MUST continue to resolve correctly after each split — achieved through `__init__.py` re-exports (Python) and barrel `index.ts` re-exports (TypeScript). Zero consumer file changes required.
- **FR-009**: All existing backend tests (pytest) and frontend tests (Vitest) MUST pass without modifying test assertions after the refactoring is complete. Only test patch paths may change.
- **FR-010**: The `ProposalOrchestrator` class MUST be injectable via FastAPI's `Depends()` mechanism, receiving all service dependencies through constructor injection.
- **FR-011**: The `ChatStateManager` class MUST be instantiated during FastAPI lifespan, stored on `app.state`, and accessible via a `Depends()` factory.
- **FR-012**: The refactoring MUST introduce zero functional changes — all user-facing behavior, API responses, error handling, and side effects must remain identical.

### Key Entities

- **ChatStateManager**: Encapsulates in-memory chat state (message cache, proposal cache, recommendation cache, per-key async locks). Provides explicit lifecycle methods (initialize, clear) and cache access methods (get, store, delete). Replaces 4 module-level dictionary globals.
- **ProposalOrchestrator**: Encapsulates the 7-phase proposal confirmation workflow (validation, user-edit application, repository resolution, GitHub issue creation, status broadcasting, workflow configuration, agent assignment). Receives service dependencies via constructor injection. Replaces a single monolithic function.
- **Bootstrap**: Collection of named startup/shutdown functions (database initialization, service registration, background task startup, shutdown cleanup). Called sequentially by the lifespan function. Replaces inline logic in `main.py`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No single backend module exceeds 600 lines after the refactoring is complete (down from the current 2,930-line maximum).
- **SC-002**: No single frontend file exceeds 400 lines after the refactoring is complete (down from the current 1,876-line maximum).
- **SC-003**: 100% of existing backend tests pass without modifying test assertions (only patch paths may change).
- **SC-004**: 100% of existing frontend tests pass without modifying test assertions or import paths in test files.
- **SC-005**: Each phase of `ProposalOrchestrator` can be unit-tested independently — verified by the presence of at least one test per orchestration phase that mocks all other phases.
- **SC-006**: Zero consumer files require import path changes — all 265+ existing import sites continue to work through barrel re-exports.
- **SC-007**: `ChatStateManager` can be instantiated in tests with no module-level side effects — verified by a test that creates multiple independent instances with different initial state.
- **SC-008**: Developers can locate domain-specific code within 2 directory navigation steps (e.g., `api/chat/` → `messages.py`), measurable by the maximum file count per domain package being under 8 files.
- **SC-009**: Code review time for domain-specific changes is reduced — measured by the average changed-file line count in domain-scoped pull requests being under 500 lines (compared to the current 2,930-line minimum for any chat change).

## Assumptions

- The application runs as a single process, so in-memory caching in `ChatStateManager` is sufficient (no distributed cache needed).
- The existing test suite provides adequate coverage to detect regressions from the refactoring — no new feature tests are needed, only structural tests for extracted classes.
- FastAPI's `include_router()` preserves all existing middleware, dependency injection, and URL prefix behavior when sub-routers are composed in `__init__.py`.
- TypeScript barrel re-exports (`export * from './module'`) are resolved correctly by the existing Vite build configuration without any bundler configuration changes.
- The `generate-diagrams.sh` script already handles both `.py` files and package directories with `__init__.py` for API route discovery, so no diagram script changes are needed.
- All 7 phases of `confirm_proposal()` execute sequentially and synchronously within a single request — no event-driven or saga pattern is needed.
- Test patch paths follow Python's import resolution: patching must target the sub-module where the name is used, not the barrel re-export in `__init__.py`.

## Dependencies

- **No new runtime dependencies**: The refactoring uses only existing language features (Python packages, TypeScript modules) and framework capabilities (FastAPI `APIRouter.include_router()`, TypeScript barrel exports).
- **Existing infrastructure**: FastAPI `Depends()` for dependency injection, Pydantic for models, TanStack Query for frontend server state, Zod for validation schemas.
- **CI pipeline**: Existing pytest and Vitest configurations must work without modification. Only test source files may change (patch path updates).
