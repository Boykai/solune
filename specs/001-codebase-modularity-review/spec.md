# Feature Specification: Codebase Modularity Review

**Feature Branch**: `001-codebase-modularity-review`  
**Created**: 2026-04-12  
**Status**: Draft  
**Input**: User description: "Codebase Modularity Review — decompose monolithic backend endpoints, extract dedicated service classes, split the frontend API client and type definitions by domain, consolidate backend global state, and standardise frontend project conventions"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Backend Endpoint Files Are Decomposed into Focused Modules (Priority: P1)

A developer working on backend chat or webhook functionality can navigate directly to the relevant sub-module (e.g., message handling, proposal management, streaming, pull-request webhooks) without scrolling through thousands of lines in a single file. Each sub-module is small enough to read in one sitting, can be reviewed in a pull request without excessive context, and can be tested independently.

**Why this priority**: The backend chat endpoint file (~2 900 lines) and webhook endpoint file (~1 000 lines) are the two largest monolithic hotspots in the codebase. They combine unrelated concerns — message persistence, proposal orchestration, streaming, dispatch, webhook signature verification, pull-request handling, and check-run handling — into single files. This makes navigation difficult, code reviews slow, and unit tests hard to isolate. Splitting them is the single highest-impact maintainability improvement.

**Independent Test**: Open the backend codebase and confirm that no single endpoint file exceeds a manageable size. Verify that every public endpoint is still reachable and returns the same responses as before the decomposition. Run the existing backend test suite and confirm all tests pass without modification to test assertions.

**Acceptance Scenarios**:

1. **Given** the backend chat endpoint file currently contains ~2 900 lines, **When** the decomposition is complete, **Then** no individual sub-module exceeds 600 lines and each sub-module has a single, clearly defined responsibility.
2. **Given** the backend webhook endpoint file currently contains ~1 000 lines, **When** the decomposition is complete, **Then** no individual sub-module exceeds 400 lines and each sub-module has a single, clearly defined responsibility.
3. **Given** the existing backend endpoint integration and unit tests, **When** the decomposition is complete, **Then** all existing tests pass without changes to their assertions (import paths may be updated but behaviour is identical).
4. **Given** external callers of the chat and webhook endpoints, **When** the decomposition is complete, **Then** all public endpoint URLs, request/response shapes, and status codes remain unchanged.

---

### User Story 2 — Critical Business Logic Is Extracted into Testable Service Classes (Priority: P1)

A developer can unit-test proposal confirmation logic — which coordinates external service calls, workflow setup, agent assignment, polling initiation, and real-time broadcast — in complete isolation without standing up the full API stack. The extracted service class encapsulates the multi-step orchestration so that each step can be verified independently and new steps can be added without modifying endpoint code.

**Why this priority**: The proposal confirmation function (~450 lines) is the most complex single function in the codebase. It interleaves external service calls with workflow configuration, agent assignment, and real-time broadcast in a way that makes isolated testing impossible. Extracting it into a dedicated service class is the second-highest-impact refactoring because it unblocks reliable test coverage for a business-critical flow.

**Independent Test**: Instantiate the extracted service class with mock dependencies. Call the orchestration method and verify that each step (configuration retrieval, agent resolution, polling initiation, broadcast) is invoked in the correct order with the correct arguments. Confirm that failures at any step are handled gracefully without leaving partial state.

**Acceptance Scenarios**:

1. **Given** the proposal confirmation logic is currently embedded in a single ~450-line endpoint function, **When** extraction is complete, **Then** a dedicated service class exists that encapsulates the full orchestration flow and can be instantiated with injected dependencies.
2. **Given** the extracted service class, **When** a unit test provides mock dependencies, **Then** each orchestration step (configuration, agent resolution, polling, broadcast) can be verified independently.
3. **Given** a failure occurs at any step during proposal confirmation, **When** the service handles the failure, **Then** no partial state persists and a meaningful error is returned to the caller.
4. **Given** the existing end-to-end proposal confirmation tests, **When** extraction is complete, **Then** all existing tests pass without changes to their assertions.

---

### User Story 3 — Frontend API Client Is Split by Domain (Priority: P2)

A frontend developer working on a specific domain (e.g., chat, board, pipeline, authentication) can locate, modify, and test the relevant API client module without touching an unrelated monolithic file. Each domain module can be code-split independently, reducing initial bundle size for pages that use only a subset of API calls.

**Why this priority**: The monolithic frontend API client file (~1 900 lines with 17 namespace objects) combines every domain's API calls into a single file. This prevents effective code-splitting, makes pull-request reviews noisy (any domain change touches the same file), and increases merge-conflict risk. Splitting by domain improves developer velocity and enables page-level code-splitting.

**Independent Test**: Open the frontend codebase and confirm that no single API client module exceeds a manageable size. Verify that every existing API call is still accessible through the same public interface. Run the existing frontend test suite and confirm all tests pass.

**Acceptance Scenarios**:

1. **Given** the frontend API client currently contains ~1 900 lines in a single file, **When** the split is complete, **Then** each domain module contains only the API calls relevant to that domain and no single module exceeds 400 lines.
2. **Given** the existing frontend API client tests, **When** the split is complete, **Then** all existing tests pass without changes to their assertions.
3. **Given** consuming components that import API functions, **When** the split is complete, **Then** all import paths resolve correctly and no runtime errors occur.
4. **Given** the application build process, **When** the split is complete, **Then** the build succeeds with no increase in total bundle size.

---

### User Story 4 — Frontend Types Are Organised by Domain (Priority: P2)

A frontend developer working on a specific domain can find all related type definitions in a dedicated file rather than searching through a single ~1 500-line barrel file. Cross-domain type dependencies are explicit, making it clear which domains share types and which are fully independent.

**Why this priority**: The monolithic types file (~1 500 lines) mixes definitions from every domain. Developers must scan the entire file to find relevant types, and any change triggers merge conflicts across unrelated work. Domain-scoped type files improve discoverability and reduce coupling.

**Independent Test**: Open the frontend codebase and confirm that each domain has its own type file. Verify the build compiles without errors and all existing tests pass. Confirm that no circular dependencies exist between domain type files.

**Acceptance Scenarios**:

1. **Given** the frontend types are currently in a single ~1 500-line file, **When** the reorganisation is complete, **Then** each domain has a dedicated type file and no single type file exceeds 300 lines.
2. **Given** the existing frontend tests that use imported types, **When** the reorganisation is complete, **Then** all existing tests pass without changes to their assertions.
3. **Given** the domain type files, **When** the build is run, **Then** no circular dependency warnings or errors are produced.
4. **Given** a developer modifying types for one domain, **When** they edit the domain's type file, **Then** no other domain's type file needs modification (unless a shared type is genuinely cross-cutting).

---

### User Story 5 — Backend Global State Has Lifecycle Management (Priority: P3)

A platform operator can rely on backend state (message caches, proposal stores, per-project locks) being properly initialised at startup and cleaned up at shutdown. Concurrent access to shared state does not risk race conditions because state is encapsulated in a managed class rather than scattered across module-level globals.

**Why this priority**: Module-level dictionaries for messages, proposals, and locks lack lifecycle management. They are never cleaned up during shutdown, and their scattered locations make it difficult to reason about concurrent access. Consolidating them into a state manager eliminates this class of risk. This is lower priority than the structural splits because the current code functions correctly under normal load.

**Independent Test**: Start the backend, exercise state-dependent operations (sending messages, creating proposals, acquiring locks), shut down the backend, and verify that all state is released. Under concurrent load, verify that no race conditions cause lost updates or stale reads.

**Acceptance Scenarios**:

1. **Given** backend state is currently held in module-level globals, **When** consolidation is complete, **Then** all chat-related state (messages, proposals, locks) is encapsulated in a single managed class with explicit initialisation and cleanup methods.
2. **Given** the managed state class, **When** the backend shuts down, **Then** all state is cleaned up and no resources are leaked.
3. **Given** concurrent requests accessing shared state, **When** the managed state class is used, **Then** no race conditions occur (verified by concurrent test scenarios).
4. **Given** the existing backend tests, **When** consolidation is complete, **Then** all existing tests pass without changes to their assertions.

---

### User Story 6 — Backend Bootstrap Logic Is Separated from Application Lifecycle (Priority: P3)

A developer modifying startup behaviour (auto-discovery, polling watchdogs, agent synchronisation, session cleanup) can find and change the relevant bootstrap logic without navigating an 850-line application entry point. Each bootstrap concern is isolated so it can be tested, disabled, or reordered independently.

**Why this priority**: The backend entry point (~850 lines) mixes application factory logic with startup procedures (auto-discovery, polling watchdog, session cleanup, agent sync). This makes it hard to test startup sequences independently and increases risk when modifying bootstrap behaviour. Separating bootstrap from application lifecycle improves testability and reduces the blast radius of startup changes.

**Independent Test**: Import the bootstrap module independently and call each startup function with mock dependencies. Verify that each function performs its expected setup without requiring the full application to be running. Confirm the full application starts and shuts down correctly after the separation.

**Acceptance Scenarios**:

1. **Given** the backend entry point currently contains ~850 lines mixing bootstrap and lifecycle, **When** separation is complete, **Then** the entry point contains only application factory and lifecycle management, with all bootstrap procedures in dedicated modules.
2. **Given** the separated bootstrap functions, **When** called with mock dependencies, **Then** each function can be tested independently without starting the full application.
3. **Given** the full application, **When** started after the separation, **Then** all startup procedures execute in the same order and produce the same result as before.
4. **Given** the existing backend tests, **When** separation is complete, **Then** all existing tests pass without changes to their assertions.

---

### Edge Cases

- What happens when the decomposed backend modules need to share helper functions? Shared utilities must be placed in a common sub-module within the package rather than duplicated across sub-modules.
- What happens when a frontend domain type is genuinely used by multiple domains? Shared types must be placed in a dedicated shared types file with explicit exports, not duplicated in each domain file.
- What happens when an existing import path changes after decomposition? A re-export layer at the original package level must maintain backward compatibility so that external consumers and tests can migrate incrementally.
- What happens when the backend state manager fails during initialisation? The application must fail to start with a clear error rather than silently falling back to uninitialised state.
- What happens when two developers simultaneously modify different sub-modules that were previously in the same monolithic file? Merge conflicts should be eliminated — this is a primary goal of the decomposition.
- What happens when a frontend domain API module imports a type from another domain's type file? The dependency must be explicit and unidirectional; circular dependencies between domain modules are not permitted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backend chat endpoint file MUST be decomposed into a package of sub-modules, each with a single clearly defined responsibility, with no sub-module exceeding 600 lines.
- **FR-002**: The backend webhook endpoint file MUST be decomposed into a package of sub-modules, each with a single clearly defined responsibility, with no sub-module exceeding 400 lines.
- **FR-003**: All existing public endpoint URLs, request/response shapes, and status codes MUST remain unchanged after backend decomposition.
- **FR-004**: A dedicated service class MUST be extracted to encapsulate the proposal confirmation orchestration flow, accepting dependencies through injection so it can be instantiated with mocks for testing.
- **FR-005**: The extracted proposal service MUST handle failures at any orchestration step gracefully, returning meaningful errors and leaving no partial state.
- **FR-006**: The frontend API client file MUST be split into domain-scoped modules with no single module exceeding 400 lines.
- **FR-007**: All existing frontend API call sites MUST continue to resolve correctly after the split, with no runtime import errors.
- **FR-008**: The frontend types file MUST be reorganised into domain-scoped type files with no single type file exceeding 300 lines.
- **FR-009**: No circular dependencies MUST exist between frontend domain type files after reorganisation.
- **FR-010**: All chat-related backend global state (messages, proposals, locks) MUST be consolidated into a managed class with explicit initialisation and cleanup lifecycle methods.
- **FR-011**: The managed state class MUST clean up all held resources when the backend shuts down.
- **FR-012**: Backend bootstrap logic (auto-discovery, polling, agent sync, session cleanup) MUST be separated from the application entry point into dedicated modules that can be tested independently.
- **FR-013**: Each decomposed module (backend and frontend) MUST provide a re-export layer at the package level to maintain backward compatibility during incremental migration.
- **FR-014**: All existing backend and frontend tests MUST pass after all refactoring changes, with no modifications to test assertions (import path updates are permitted).

### Key Entities

- **Endpoint Package**: A directory-based module that replaces a monolithic endpoint file, containing sub-modules organised by responsibility and a top-level re-export file for backward compatibility.
- **Proposal Orchestrator**: A service class encapsulating the multi-step proposal confirmation flow (configuration, agent resolution, polling, broadcast) with injected dependencies for testability.
- **State Manager**: A class that consolidates per-session and per-project state (message caches, proposal stores, locks) with explicit lifecycle methods (initialise, cleanup) and thread-safe access.
- **Domain API Module**: A frontend module containing all API client functions for a single domain (e.g., chat, board, pipeline), importable independently for code-splitting.
- **Domain Type File**: A frontend file containing all type definitions for a single domain, with explicit imports of any shared cross-domain types.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No single backend endpoint module exceeds 600 lines, down from the current maximum of ~2 900 lines — verified by line-count analysis of all endpoint files.
- **SC-002**: No single frontend API client module exceeds 400 lines, down from the current ~1 900 lines — verified by line-count analysis.
- **SC-003**: No single frontend type file exceeds 300 lines, down from the current ~1 500 lines — verified by line-count analysis.
- **SC-004**: 100% of existing backend tests pass after all refactoring changes — verified by running the full backend test suite.
- **SC-005**: 100% of existing frontend tests pass after all refactoring changes — verified by running the full frontend test suite.
- **SC-006**: The proposal confirmation orchestration logic can be unit-tested with mock dependencies in under 5 seconds per test — verified by measuring test execution time.
- **SC-007**: The application build succeeds with no increase in total bundle size after frontend splits — verified by comparing build output before and after.
- **SC-008**: No circular dependency warnings or errors are produced after frontend type reorganisation — verified by running the build and any circular-dependency detection tooling.
- **SC-009**: Backend startup and shutdown complete successfully after bootstrap separation — verified by integration test or manual verification.
- **SC-010**: Developers working on different domains do not encounter merge conflicts caused by concurrent edits to the same file — verified by the absence of monolithic files that span multiple domains.

## Assumptions

- The decomposition preserves all existing public interfaces (endpoint URLs, function signatures, type exports) so that no downstream consumers are broken. Internal organisation changes are invisible to callers.
- Re-export layers at the original module paths provide backward compatibility. Teams can migrate import paths incrementally; the re-export layer is a transitional mechanism, not a permanent fixture.
- The line-count thresholds (600 for backend endpoints, 400 for frontend API modules, 300 for frontend type files) are guidelines informed by the current codebase structure. Individual modules may slightly exceed these limits if splitting further would harm cohesion.
- The proposal orchestrator service class follows the same dependency-injection pattern already used elsewhere in the backend so that it integrates naturally with the existing architecture.
- Backend global state consolidation does not change the observable behaviour of message caching, proposal storage, or lock acquisition — it only changes the internal organisation and lifecycle management.
- Frontend domain boundaries align with the existing component folder structure (chat, board, pipeline, agents, chores, etc.) so that API modules and type files map naturally to existing domains.
- The backend entry point separation does not change the order or timing of startup procedures — it only moves them into dedicated modules for independent testability.
