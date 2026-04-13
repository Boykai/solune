# Feature Specification: Codebase Modularity Review

**Feature Branch**: `002-codebase-modularity-review`  
**Created**: 2026-04-13  
**Status**: Draft  
**Input**: User description: "Codebase Modularity Review"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Split Monolithic Backend Chat Endpoint (Priority: P1)

A backend developer needs to modify, debug, or add tests to the chat functionality. Today the entire chat domain — messages, proposals, plans, dispatch, and streaming — lives in a single ~2900-line file. The developer must scroll through unrelated logic, risks merge conflicts with teammates working on different chat features, and cannot run targeted test suites for individual chat concerns. After this refactoring, each chat sub-domain resides in its own module, and the developer can navigate, edit, and test each concern independently without touching unrelated code.

**Why this priority**: The monolithic chat endpoint is the single largest maintainability bottleneck in the backend. Splitting it unblocks faster iteration, safer code reviews, and independent testing of the most active backend area.

**Independent Test**: Can be fully tested by verifying that every existing chat endpoint returns identical responses before and after the split, that all existing chat-related tests continue to pass, and that each new module can be tested in isolation.

**Acceptance Scenarios**:

1. **Given** the current monolithic chat endpoint file, **When** the refactoring is complete, **Then** messages, proposals, plans, dispatch, and streaming logic each reside in separate modules within a chat sub-package.
2. **Given** the split is complete, **When** any existing chat-related test is run, **Then** it produces the same pass/fail result as before the split with no behavior changes.
3. **Given** the split modules, **When** a developer edits only the proposals module, **Then** the change does not require modifications in the messages, plans, dispatch, or streaming modules.
4. **Given** the split modules, **When** a contributor opens a pull request for a single chat concern, **Then** the diff is scoped to one module and does not create merge conflicts with concurrent changes to other chat concerns.

---

### User Story 2 - Extract Proposal Orchestration into a Dedicated Service (Priority: P1)

A developer needs to test or extend the proposal confirmation workflow — which currently spans GitHub operations, workflow setup, agent assignment, polling initiation, and real-time broadcast — all inside a single ~450-line function. Changes are risky because the function cannot be tested in isolation and has multiple interleaved responsibilities. After extraction, each responsibility is a testable method on a dedicated service, and the developer can mock any dependency to verify one behavior at a time.

**Why this priority**: The `confirm_proposal` god function is the highest-risk code path in the backend. Extracting it into a service with testable methods directly reduces production incident risk and unblocks reliable test coverage for the proposal workflow.

**Independent Test**: Can be fully tested by writing unit tests for each extracted method (GitHub operations, workflow setup, agent assignment, polling start, broadcast) using mocked dependencies, and verifying the end-to-end flow still works via integration tests.

**Acceptance Scenarios**:

1. **Given** the current ~450-line proposal confirmation function, **When** the extraction is complete, **Then** a dedicated service class exists with separate methods for each responsibility (GitHub operations, workflow setup, agent assignment, polling start, broadcast).
2. **Given** the extracted service, **When** a unit test targets the agent assignment method, **Then** it can run without invoking GitHub operations, polling, or broadcast logic.
3. **Given** the extracted service, **When** the full proposal confirmation flow is triggered via the existing endpoint, **Then** the end-to-end behavior is identical to the pre-extraction behavior.
4. **Given** the extracted service, **When** a new step needs to be added to the proposal workflow, **Then** the developer adds a single method to the service without modifying unrelated methods.

---

### User Story 3 - Split Monolithic Frontend API Client (Priority: P1)

A frontend developer needs to update the API integration for a single domain (e.g., chat, board, auth). Today all API calls live in a single ~1900-line file with 17+ namespace objects. The developer must load and parse the entire file, risks merge conflicts, and the application cannot code-split API logic per domain for bundle optimization. After the split, each domain has its own API module, and the developer edits only the relevant domain file.

**Why this priority**: The monolithic API client is the frontend equivalent of the backend chat file — it touches every domain and creates merge conflicts, review burden, and bundle-size issues. Splitting it is the highest-impact frontend maintainability improvement.

**Independent Test**: Can be fully tested by verifying that every API call produces the same request/response as before the split, that all existing frontend tests pass, and that each domain API module can be imported independently.

**Acceptance Scenarios**:

1. **Given** the current monolithic API client file, **When** the split is complete, **Then** each domain (auth, chat, board, pipeline, agents, chores, etc.) has its own API module.
2. **Given** the split modules, **When** a frontend test that calls a chat API function is run, **Then** only the chat API module is imported, not the entire API surface.
3. **Given** the split modules, **When** a developer modifies the board API module, **Then** no changes are required in the chat, auth, or pipeline API modules.
4. **Given** the split modules, **When** the application is built, **Then** each page-level code bundle includes only the API modules for the domains it uses.

---

### User Story 4 - Domain-Scoped Frontend Types (Priority: P2)

A frontend developer needs to add or modify a type definition for the pipeline domain. Today all types are in a single ~1500-line file, making it hard to find relevant types and causing unrelated imports across domains. After the refactoring, types are organized by domain, and the developer edits only the relevant domain types file.

**Why this priority**: Domain-scoped types improve code navigation, reduce accidental cross-domain coupling, and make type changes more reviewable. It is a prerequisite for fully decoupled domain modules.

**Independent Test**: Can be fully tested by verifying that all existing type references resolve correctly after the split, that the build succeeds with no type errors, and that each domain types file can be imported independently.

**Acceptance Scenarios**:

1. **Given** the current monolithic types file, **When** the split is complete, **Then** each domain (chat, board, pipeline, agents, chores, etc.) has its own types file.
2. **Given** the split type files, **When** the full frontend build is run, **Then** there are zero type errors.
3. **Given** the split type files, **When** a developer adds a new pipeline type, **Then** the change is isolated to the pipeline types file and does not modify other domain type files.
4. **Given** the split type files, **When** shared types are needed across domains, **Then** they reside in a dedicated shared types file that each domain can import.

---

### User Story 5 - Consolidate Backend Global State into a Managed Class (Priority: P2)

A backend developer encounters intermittent race conditions or needs to understand the lifecycle of in-memory chat state (messages, proposals, locks). Today these are module-level global dictionaries with no lifecycle management or thread-safety guarantees. After consolidation, all mutable state is encapsulated in a state manager class with explicit initialization, cleanup, and concurrency controls.

**Why this priority**: Module-level global state creates race conditions, makes testing unreliable, and prevents proper lifecycle management during application startup/shutdown. Consolidating it eliminates a class of hard-to-reproduce production bugs.

**Independent Test**: Can be fully tested by instantiating the state manager in a test, verifying that concurrent operations do not corrupt state, and confirming that cleanup properly releases resources.

**Acceptance Scenarios**:

1. **Given** the current module-level global dictionaries, **When** the consolidation is complete, **Then** all mutable chat state (messages, proposals, locks) is encapsulated in a single state manager class.
2. **Given** the state manager, **When** concurrent requests access the same session's state, **Then** operations are serialized by the state manager's concurrency controls with no data corruption.
3. **Given** the state manager, **When** the application shuts down, **Then** the state manager's cleanup method is invoked and all resources are released.
4. **Given** the state manager, **When** a test creates its own instance, **Then** the test is fully isolated from other tests and from production state.

---

### User Story 6 - Split Backend Webhooks Endpoint (Priority: P2)

A backend developer needs to modify the handling logic for a specific webhook event type (e.g., pull request events vs. check run events). Today all webhook handlers are in a single ~1000-line file. After the split, each event type has its own handler module, and the developer can modify and test one event type without touching others.

**Why this priority**: Webhook handling is a critical integration point. Splitting by event type improves testability, reduces review scope, and makes it easier to add new webhook event handlers without risking regressions in existing ones.

**Independent Test**: Can be fully tested by sending test webhook payloads for each event type and verifying that the correct handler module processes each event with identical behavior to the pre-split implementation.

**Acceptance Scenarios**:

1. **Given** the current monolithic webhooks file, **When** the split is complete, **Then** each webhook event type (pull requests, check runs, etc.) has its own handler module within a webhooks sub-package.
2. **Given** the split handler modules, **When** a pull request webhook is received, **Then** only the pull request handler module processes it.
3. **Given** the split handler modules, **When** a developer adds handling for a new webhook event type, **Then** they create a new handler module without modifying existing handlers.
4. **Given** the split handler modules, **When** existing webhook-related tests are run, **Then** they produce the same pass/fail results as before the split.

---

### User Story 7 - Standardize Frontend Test Layout (Priority: P3)

A frontend contributor needs to find and run tests for a specific component or hook. Today some domains use `__tests__/` subdirectories while others co-locate `.test.tsx` files alongside source files. The inconsistency makes test discovery unreliable and complicates CI configuration. After standardization, all frontend tests follow a single, documented convention.

**Why this priority**: While not a functional change, inconsistent test layout slows onboarding, makes grep-based test discovery unreliable, and creates friction during code review. Standardizing it is low-risk and improves developer experience across all future work.

**Independent Test**: Can be fully tested by verifying that all existing tests are discoverable by the test runner after the reorganization, that all tests pass, and that the chosen convention is documented.

**Acceptance Scenarios**:

1. **Given** the current inconsistent test layout, **When** the standardization is complete, **Then** all frontend tests follow a single documented convention (either `__tests__/` subdirectories or co-located `.test.tsx` files — not a mix).
2. **Given** the standardized layout, **When** the test runner is invoked, **Then** it discovers and runs all tests with zero configuration changes.
3. **Given** the standardized layout, **When** a new contributor looks for tests for a given component, **Then** they find them in the expected location on the first attempt.
4. **Given** the standardized layout, **When** a developer creates a new component, **Then** the contributing guide specifies exactly where to place the test file.

---

### Edge Cases

- What happens when a split module needs to import a symbol that was previously file-private in the monolithic file? The refactoring must explicitly decide which symbols become public module exports and which remain internal, documenting the decision.
- What happens when circular dependencies arise between split modules (e.g., proposals importing from messages and vice versa)? A shared types or utilities module must be created to break the cycle, and the dependency graph must remain acyclic.
- How does the system handle existing third-party integrations or scripts that import directly from the old monolithic file paths? Public re-exports from the original file path must be maintained during a deprecation period, or all import sites must be updated atomically.
- What happens when a split module's tests rely on shared fixtures or mocks that were previously scoped to the monolithic file's test? Shared test utilities must be extracted to a common test fixtures module.
- How does the refactoring handle in-flight pull requests that target the same files being split? A migration guide must be provided, and the refactoring should be merged as a single coordinated change to minimize rebase conflicts.
- What happens when the state manager class is instantiated multiple times in the same process? The design must enforce a singleton pattern or explicitly support multiple instances for testing.
- How does the system handle partial completion — e.g., only some modules are split while others remain monolithic? Each split must be independently deployable, and the system must function correctly with any combination of split and unsplit modules during the transition.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backend chat endpoint file MUST be split into separate modules for messages, proposals, plans, dispatch, and streaming, organized within a chat sub-package.
- **FR-002**: The proposal confirmation workflow MUST be extracted into a dedicated service class with individually testable methods for each responsibility (GitHub operations, workflow setup, agent assignment, polling start, broadcast).
- **FR-003**: The frontend API client file MUST be split into domain-scoped modules (auth, chat, board, pipeline, agents, chores, etc.) that can be imported independently.
- **FR-004**: The frontend types file MUST be split into domain-scoped type files with a shared types file for cross-domain definitions.
- **FR-005**: All backend mutable global state (messages, proposals, locks dictionaries) MUST be consolidated into a state manager class with explicit initialization, cleanup, and concurrency controls.
- **FR-006**: The backend webhooks file MUST be split into event-type-specific handler modules within a webhooks sub-package.
- **FR-007**: All existing tests MUST continue to pass after each refactoring step with no behavior changes to user-facing functionality.
- **FR-008**: Each split module MUST be independently importable and testable without requiring the import of unrelated modules.
- **FR-009**: The dependency graph between split modules MUST remain acyclic — no circular imports.
- **FR-010**: Frontend test file placement MUST follow a single, documented convention consistently across all domains.
- **FR-011**: Each refactoring target MUST be implementable and deployable independently of the others, allowing incremental adoption.
- **FR-012**: Public entry points (endpoint URLs, exported API functions, type names) MUST remain unchanged — refactoring is internal only.
- **FR-013**: The backend application bootstrap and lifecycle management logic MUST be separated from the main entry point file into a dedicated bootstrap module.
- **FR-014**: The extracted proposal orchestration service MUST support dependency injection for all external dependencies (GitHub client, workflow manager, polling service, broadcast service) to enable isolated unit testing.

### Key Entities

- **Chat Sub-Package**: A collection of backend modules (messages, proposals, plans, dispatch, streaming) that together provide all chat endpoint functionality, replacing the current single-file implementation.
- **Proposal Orchestrator Service**: A dedicated service class encapsulating the full proposal confirmation workflow, with separate methods for each responsibility and injected dependencies for testability.
- **Chat State Manager**: A class encapsulating all mutable in-memory chat state (messages, proposals, locks) with lifecycle management, concurrency controls, and cleanup capabilities.
- **Domain API Module**: A frontend module containing all API client functions for a single domain (e.g., chat, board, auth), independently importable and code-splittable.
- **Domain Types File**: A frontend type definition file scoped to a single domain, with a separate shared types file for cross-domain definitions.
- **Webhook Handler Module**: A backend module handling a specific webhook event type (e.g., pull requests, check runs), organized within a webhooks sub-package.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No single backend source file in the chat domain exceeds 600 lines (down from ~2900 lines).
- **SC-002**: No single frontend source file in the API client or types domains exceeds 400 lines (down from ~1900 and ~1500 lines respectively).
- **SC-003**: The proposal confirmation workflow is covered by unit tests that each execute in under 1 second without requiring external service connections.
- **SC-004**: 100% of existing automated tests pass after each refactoring step with zero behavior changes.
- **SC-005**: Average pull request diff for chat-domain changes decreases by at least 50% (measured by comparing pre- and post-refactoring PR sizes for equivalent changes).
- **SC-006**: New team members can locate the source file for any chat, webhook, or API concern within 30 seconds using file navigation alone (verified by onboarding feedback).
- **SC-007**: Concurrent access to chat state produces zero race conditions under load testing with at least 100 simultaneous requests per session.
- **SC-008**: All refactoring changes are shipped incrementally — no single pull request modifies more than one refactoring target from the top-6 list.
- **SC-009**: Zero circular import errors detected across all split modules when the full test suite and build are run.
- **SC-010**: Frontend bundle size for individual pages does not increase by more than 2% after the API client split (domain-scoped code-splitting should maintain or reduce bundle sizes).

## Assumptions

- The existing test suite provides sufficient coverage to detect behavioral regressions from refactoring. If coverage gaps are discovered, they will be filled before or during the refactoring, not deferred.
- The refactoring is purely internal — no public API contracts (HTTP endpoints, WebSocket events, exported type names) change. Consumers of the application see identical behavior before and after.
- The team will adopt a "one refactoring target per PR" strategy to minimize merge conflicts and enable incremental review.
- The co-located test pattern (`.test.tsx` alongside source files) will be the standardized convention for frontend tests, as it is already the majority pattern and aligns with common industry practice.
- Module-level re-exports from original file paths will be maintained temporarily to avoid breaking in-flight work, then removed after all references are updated.
- The state manager class will be a singleton scoped to the application lifespan, instantiated during startup and cleaned up during shutdown, with a factory method for creating isolated test instances.
- Performance characteristics (response times, memory usage) will not degrade as a result of the refactoring. If splitting introduces measurable overhead (e.g., from additional module imports), it will be addressed before merging.
