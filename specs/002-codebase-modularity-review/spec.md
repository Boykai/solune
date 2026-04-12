# Feature Specification: Codebase Modularity Review

**Feature Branch**: `002-codebase-modularity-review`  
**Created**: 2026-04-12  
**Status**: Draft  
**Input**: User description: "Codebase Modularity Review"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Split Monolithic Backend Endpoint File (Priority: P1)

A backend developer needs to add a new message-related feature to the chat system. Currently, they must navigate a single ~2900-line endpoint file that mixes message handling, proposal management, plan operations, dispatch logic, and streaming concerns. After the refactoring, they open only the focused module relevant to their task, make their change confidently without risk of unintended side effects in unrelated logic, and submit a pull request that reviewers can assess quickly because it touches only one cohesive module.

**Why this priority**: This is the single biggest maintainability win. The monolithic endpoint file is the most-edited file in the backend, making it the highest-friction point for developers. Splitting it unblocks easier testing, faster reviews, and reduced merge conflicts for every subsequent change.

**Independent Test**: Can be fully tested by verifying that all existing endpoint tests pass after the split, that each new module has clear responsibility boundaries, and that no circular dependencies are introduced between the split modules.

**Acceptance Scenarios**:

1. **Given** the monolithic chat endpoint file, **When** it is split into focused modules by responsibility (messages, proposals, plans, dispatch, streaming), **Then** each resulting module contains only the endpoints and helpers for its domain, and no module exceeds 600 lines.
2. **Given** the split modules, **When** a developer imports a module, **Then** it does not transitively pull in unrelated endpoint logic from sibling modules.
3. **Given** the existing test suite, **When** all tests are run after the split, **Then** every test passes without modification (behavior-preserving refactor).
4. **Given** the split modules, **When** a new endpoint is added to the messages domain, **Then** the developer only needs to edit the messages module, and the pull request diff is scoped to that module alone.

---

### User Story 2 - Extract Proposal Orchestration Service (Priority: P1)

A backend developer needs to test the proposal confirmation workflow in isolation. Currently, the core orchestration logic lives inside a single ~450-line function that combines multiple concerns — external service calls, workflow setup, agent assignment, polling initialization, and real-time broadcasting. After refactoring, the orchestration logic is encapsulated in a dedicated service with testable methods, each handling a single responsibility. The developer can write unit tests for each step independently without mocking the entire endpoint stack.

**Why this priority**: The "god function" is the second-highest-impact modularity problem. It prevents unit testing, makes debugging difficult, and creates a bottleneck where any change to one concern (e.g., agent assignment) risks breaking others (e.g., real-time broadcasting).

**Independent Test**: Can be fully tested by verifying that the extracted service methods can be invoked and tested individually with mocked dependencies, and that the original endpoint delegates to the service without duplicating logic.

**Acceptance Scenarios**:

1. **Given** the monolithic orchestration function, **When** it is extracted into a dedicated service, **Then** the service exposes distinct methods for each step of the orchestration workflow.
2. **Given** the extracted service, **When** a developer writes a unit test for a single orchestration step, **Then** only that step's direct dependencies need to be mocked — not the entire endpoint or unrelated orchestration steps.
3. **Given** the extracted service, **When** the original endpoint is called, **Then** it delegates to the service and produces identical behavior to the pre-refactor implementation.
4. **Given** the extracted service, **When** a new orchestration step is added, **Then** it can be added as a new method without modifying existing methods.

---

### User Story 3 - Split Monolithic Frontend API Client (Priority: P1)

A frontend developer needs to update an API call for the board feature. Currently, all API calls across every domain live in a single ~1900-line file with 17 namespace objects. After refactoring, each domain has its own API module. The developer opens only the board API module, makes the change, and the build system can tree-shake unused API calls from other domains, reducing bundle size for pages that don't use them.

**Why this priority**: The monolithic API client is the frontend's biggest modularity bottleneck. It prevents effective code-splitting, makes reviews harder (any API change touches the same file), and increases the risk of merge conflicts between unrelated domain changes.

**Independent Test**: Can be fully tested by verifying that all existing API-related tests pass, that each domain module exports only its own API calls, and that no module imports from a sibling domain module.

**Acceptance Scenarios**:

1. **Given** the monolithic API client file, **When** it is split into domain-scoped modules, **Then** each module contains only the API calls for its domain, and no module exceeds 300 lines.
2. **Given** the split API modules, **When** a page uses only the chat API, **Then** the build output for that page does not include API calls from unrelated domains (board, pipeline, agents, etc.).
3. **Given** the existing test suite, **When** all tests are run after the split, **Then** every test passes without modification.
4. **Given** the split API modules, **When** two developers work on different domains simultaneously, **Then** their changes touch separate files and do not create merge conflicts.

---

### User Story 4 - Domain-Scoped Frontend Types (Priority: P2)

A frontend developer adds a new type for the pipeline feature. Currently, they must scroll through a single 1500+ line types file shared by all domains, find the right section, add their type, and hope it doesn't clash with types from other domains. After refactoring, types are organized by domain. The developer opens the pipeline types module, adds the new type, and reviewers can see at a glance that only pipeline types were affected.

**Why this priority**: Domain-scoped types improve discoverability and reduce accidental coupling. When all types live in one file, adding a type to one domain can inadvertently affect imports in another. This is a moderate-effort change with broad positive impact on developer experience.

**Independent Test**: Can be fully tested by verifying that all existing type-check and test suites pass, that each domain module exports only its own types, and that import paths are updated consistently across the codebase.

**Acceptance Scenarios**:

1. **Given** the monolithic types file, **When** types are split into domain-scoped modules, **Then** each module contains only the types for its domain.
2. **Given** the split type modules, **When** a developer imports types for the chat domain, **Then** they import from the chat types module and do not transitively import board, pipeline, or agent types.
3. **Given** the existing type-check configuration, **When** type-checking is run after the split, **Then** no new type errors are introduced.
4. **Given** the split type modules and a barrel re-export for backward compatibility, **When** existing import paths are used, **Then** they continue to resolve correctly during a migration period.

---

### User Story 5 - Consolidate Backend Global State (Priority: P2)

A backend developer is investigating a race condition in the chat system. Currently, multiple module-level dictionaries hold shared state (messages, proposals, locks) without lifecycle management. The developer must trace state mutations across multiple functions in a single large file to understand the issue. After refactoring, shared state is encapsulated behind a state manager with clear initialization, access, and cleanup boundaries. The developer can inspect and test state transitions through a well-defined interface.

**Why this priority**: Module-level global state is a correctness and reliability risk. Race conditions from unmanaged shared dictionaries can cause data corruption or inconsistent behavior under load. Consolidating state behind a managed interface eliminates an entire class of bugs.

**Independent Test**: Can be fully tested by verifying that all state access goes through the state manager interface, that the state manager initializes and cleans up correctly during application lifecycle, and that concurrent access tests pass.

**Acceptance Scenarios**:

1. **Given** module-level global dictionaries for chat state, **When** they are consolidated into a state manager, **Then** all state access goes through the state manager's methods — no direct dictionary access remains.
2. **Given** the state manager, **When** the application starts, **Then** the state manager initializes cleanly and is available for injection into dependent services.
3. **Given** the state manager, **When** the application shuts down, **Then** the state manager performs cleanup (releasing locks, clearing transient state) in a deterministic order.
4. **Given** the state manager, **When** concurrent requests access shared state, **Then** the state manager enforces safe access patterns and prevents data corruption.

---

### User Story 6 - Split Backend Webhook Handlers (Priority: P3)

A backend developer needs to modify how pull request webhook events are processed. Currently, all webhook handlers live in a single ~1000-line file covering multiple event types. After refactoring, each event category has its own handler module. The developer modifies only the pull request handler, and reviewers can focus their review on that specific event type.

**Why this priority**: Webhook handler splitting is the lowest-risk refactoring target with the most straightforward decomposition. Each event type is already logically independent, making the split mechanical and low-risk while still improving navigability and testability.

**Independent Test**: Can be fully tested by verifying that all webhook-related tests pass after the split, that each handler module processes only its designated event type, and that the webhook router correctly dispatches events to the appropriate handler.

**Acceptance Scenarios**:

1. **Given** the monolithic webhook handler file, **When** it is split by event category, **Then** each resulting module handles only its designated event type(s) and no module exceeds 400 lines.
2. **Given** the split handler modules, **When** a pull request event is received, **Then** it is routed to and processed by only the pull request handler module.
3. **Given** the existing webhook test suite, **When** all tests are run after the split, **Then** every test passes without modification.

---

### Edge Cases

- What happens when split modules need to share utility functions? Shared utilities are extracted into a common helpers module within the same package, avoiding circular imports.
- What happens when a backward-compatible import path (barrel re-export) masks a circular dependency? The barrel file must not import from modules that import from it. Circular dependency detection runs as part of the validation process.
- What happens when the state manager is accessed before initialization? The state manager raises a clear error indicating it has not been initialized, rather than returning undefined or empty state silently.
- What happens when a webhook event type is received that has no dedicated handler after the split? The router falls back to a default handler that logs the unhandled event type and returns an appropriate response without crashing.
- What happens when two developers are simultaneously refactoring different parts of the monolithic file? Each refactoring target is scoped to a distinct module, so after the initial split is merged, subsequent changes to different domains do not conflict.
- What happens when existing test files import directly from the monolithic file paths? Backward-compatible re-exports are provided during a migration period, and a deprecation warning or linting rule flags old import paths for future cleanup.
- What happens when the extracted service has different error handling than the original inline code? The extracted service preserves the original error handling behavior exactly, with no changes to error types or propagation patterns during the refactor.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backend chat endpoint file MUST be split into separate modules organized by responsibility: messages, proposals, plans, dispatch, and streaming.
- **FR-002**: Each split backend module MUST contain only endpoints and helpers related to its designated responsibility, with no module exceeding 600 lines.
- **FR-003**: The proposal orchestration logic MUST be extracted from the monolithic function into a dedicated service with individually testable methods for each orchestration step.
- **FR-004**: The extracted orchestration service MUST be injectable via the existing dependency injection pattern, allowing unit tests to mock individual orchestration steps.
- **FR-005**: The frontend API client file MUST be split into domain-scoped modules (one per domain: auth, chat, board, pipeline, agents, etc.) with no module exceeding 300 lines.
- **FR-006**: Each domain API module MUST export only the API calls relevant to its domain and MUST NOT import from sibling domain API modules.
- **FR-007**: The frontend types file MUST be split into domain-scoped type modules with a barrel re-export file for backward compatibility during migration.
- **FR-008**: All split type modules MUST be self-contained — importing a domain's types MUST NOT transitively pull in types from unrelated domains.
- **FR-009**: Backend module-level global state (messages, proposals, locks dictionaries) MUST be consolidated into a state manager with explicit initialization, access, and cleanup methods.
- **FR-010**: The state manager MUST participate in the application lifecycle — initializing at startup and cleaning up at shutdown.
- **FR-011**: The backend webhook handler file MUST be split by event category into separate handler modules with a router that dispatches events to the correct handler.
- **FR-012**: Every refactoring MUST be behavior-preserving — all existing tests MUST pass without modification after each change.
- **FR-013**: No refactoring MUST introduce new circular dependencies between modules.
- **FR-014**: Backward-compatible import paths (re-exports) MUST be provided for all split modules during a migration period to avoid breaking existing consumers.
- **FR-015**: The refactoring MUST maintain or improve the existing test coverage — no reduction in line or branch coverage is permitted.

### Key Entities

- **Endpoint Module**: A focused backend file containing only the route handlers and helpers for a single responsibility domain (e.g., messages, proposals). Each module is independently importable and testable.
- **Orchestration Service**: A dedicated backend service encapsulating multi-step workflow logic (e.g., proposal confirmation). Exposes individually testable methods and is provided via dependency injection.
- **Domain API Module**: A focused frontend file containing only the API client calls for a single domain. Enables per-domain code-splitting and independent testing.
- **Domain Type Module**: A focused frontend file containing only the type definitions for a single domain. Prevents cross-domain type coupling and improves discoverability.
- **State Manager**: A backend component that encapsulates shared mutable state behind a managed interface with lifecycle hooks (init, access, cleanup). Replaces unmanaged module-level global dictionaries.
- **Webhook Handler Module**: A focused backend file containing only the webhook processing logic for a specific event category. Connected to incoming events via a central router/dispatcher.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No single backend endpoint file exceeds 600 lines after refactoring (down from ~2900 lines).
- **SC-002**: No single frontend API client file exceeds 300 lines after refactoring (down from ~1900 lines).
- **SC-003**: The extracted orchestration service has at least 3 independently testable methods, each coverable by a unit test that mocks only its direct dependencies.
- **SC-004**: 100% of existing tests pass without modification after each refactoring step (behavior-preserving guarantee).
- **SC-005**: Test coverage (line and branch) remains at or above pre-refactoring levels for all affected modules.
- **SC-006**: No new circular dependencies are introduced, as verified by dependency analysis tooling.
- **SC-007**: Frontend bundle size for individual pages does not increase after splitting the API client (tree-shaking validates domain isolation).
- **SC-008**: Pull request review time for changes scoped to a single domain decreases — reviewers need to examine only the relevant module, not the entire monolithic file.
- **SC-009**: Merge conflict frequency for the previously monolithic files drops after the split, as concurrent domain changes touch separate files.
- **SC-010**: The state manager passes concurrent access tests demonstrating safe state handling under simultaneous requests.

## Assumptions

- The existing test suite provides sufficient coverage to validate behavior preservation — if a refactoring breaks functionality, it will be caught by existing tests.
- The backend dependency injection pattern (used consistently across the codebase) will accommodate the new orchestration service without architectural changes.
- Backward-compatible re-export files will be maintained for one release cycle to allow gradual migration of import paths across the codebase.
- The refactoring will be performed incrementally — one target at a time — rather than as a single large change, reducing risk and enabling independent review.
- Frontend build tooling supports tree-shaking of the split API modules without additional configuration.
- The existing domain folder structure on both frontend and backend provides a natural decomposition guide for where split modules should reside.
- Concurrent access patterns in the backend are already exercised by integration tests, making the state manager's safety guarantees verifiable with existing test infrastructure.

## Scope Boundaries

**In scope**:
- Splitting the monolithic backend chat endpoint file into responsibility-scoped modules
- Extracting the proposal orchestration logic into a dedicated, testable service
- Splitting the monolithic frontend API client into domain-scoped modules
- Splitting the monolithic frontend types file into domain-scoped modules
- Consolidating backend module-level global state into a managed state component
- Splitting the backend webhook handler file into event-category modules
- Providing backward-compatible re-exports during migration
- Maintaining existing test coverage and behavior

**Out of scope**:
- Adding new features or changing existing behavior — this is a purely structural refactoring
- Refactoring the backend bootstrap/lifecycle management in main.py — that is a separate concern
- Adding barrel exports to all frontend directories — only the split modules get re-exports for compatibility
- Resolving the circular dependency workaround in dependencies.py — that requires a broader architectural change beyond file splitting
- Changing the frontend test layout convention (co-located vs. __tests__ subdirectory) — consistency standardization is a separate initiative
- Adding composite wrapper hooks for deep hook imports — that is an optimization separate from the modularity split
- Migrating from the existing state management patterns to an entirely different architecture
