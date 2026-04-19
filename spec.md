# Feature Specification: Refactor main.py Lifespan into src/startup/ Step Package

**Feature Branch**: `002-lifespan-startup-steps`
**Created**: 2026-04-18
**Status**: Draft
**Input**: User description: "Refactor main.py Lifespan into src/startup/ Step Package — Extract the fifteen responsibilities currently inlined in lifespan() into a src/startup/ package of named, individually-testable steps."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Developer Tests a Single Startup Step in Isolation (Priority: P1)

A backend developer wants to verify that the database initialization step works correctly without booting the entire application. Today, the only way to test any startup logic is to launch the full server because all fifteen responsibilities are woven into a single 160-line function. After this refactor, the developer writes a unit test that creates a minimal context, runs the database step, and asserts the expected side-effects — all in under one second.

**Why this priority**: Testability is the primary driver for this refactor. Until steps can be tested independently, every startup change carries regression risk that can only be caught by slow, flaky integration tests.

**Independent Test**: Can be fully tested by running a single step with a mock context and asserting the expected outcome — no server boot required.

**Acceptance Scenarios**:

1. **Given** a step module exists for "database initialization", **When** a developer runs its unit test with a mocked database connection, **Then** the test passes or fails in under 2 seconds and validates that the database is initialised and assigned to the application state.
2. **Given** a step module exists for "pipeline state cache", **When** a developer runs its unit test with a mock database, **Then** the test asserts the cache initialisation function was called exactly once.
3. **Given** a step module has `fatal=True`, **When** it raises an exception during its test, **Then** the test verifies the runner propagates the exception (does not swallow it).

---

### User Story 2 — Developer Reorders or Adds a Startup Step (Priority: P2)

A backend developer needs to add a new initialisation step (e.g., a new cache warm-up) to the application startup sequence. Today, this means editing the middle of a dense 160-line function and hoping the insertion point is correct. After this refactor, the developer creates a new step module, adds it to the declarative step list at the desired position, and marks it `fatal` or non-fatal. The runner executes it in order automatically.

**Why this priority**: Maintainability directly impacts developer velocity. A declarative step list makes ordering explicit and changes reviewable at a glance.

**Independent Test**: Can be fully tested by injecting a list of fake steps into the runner and asserting execution order matches the list order.

**Acceptance Scenarios**:

1. **Given** a declarative startup step list, **When** a developer adds a new step at position 5, **Then** the runner executes it after step 4 and before step 6.
2. **Given** a step list with 15 entries, **When** a developer removes a step from the middle, **Then** all remaining steps still execute in their declared order without code changes to the runner.

---

### User Story 3 — Operations Engineer Diagnoses a Slow or Failing Boot (Priority: P2)

An operations engineer notices the application is taking longer than usual to start. Today, startup logs are mixed in with general application output and lack timing information. After this refactor, each step emits a structured log line with the step name, status (ok/failed/skipped), and duration in milliseconds. The engineer can quickly identify which step is slow or failing.

**Why this priority**: Observability during startup is critical for production incident response. Structured per-step logs eliminate guesswork.

**Independent Test**: Can be fully tested by running the startup runner with fake steps and capturing log output, asserting each log line contains the required fields.

**Acceptance Scenarios**:

1. **Given** the application starts up, **When** all steps succeed, **Then** one structured log line per step is emitted containing `step`, `status`, and `duration_ms` fields.
2. **Given** a non-fatal step fails during startup, **When** the engineer reviews logs, **Then** the failed step's log entry shows status "failed" with error details, and subsequent steps still appear in the log.
3. **Given** a conditional step (e.g., telemetry) is skipped, **When** the engineer reviews logs, **Then** the log entry for that step shows status "skipped".

---

### User Story 4 — Developer Verifies Shutdown Correctness After a Fatal Step Failure (Priority: P3)

A developer wants to ensure that even when a fatal startup step fails and aborts the boot, critical cleanup still happens — for example, the database connection is closed. Today, there is a single `finally` block that handles all cleanup, and its behaviour when certain steps haven't run is hard to reason about. After this refactor, shutdown hooks run in reverse-registration order, and built-in trailing hooks (drain tasks, stop polling, close database) always execute regardless of which startup step failed.

**Why this priority**: Resource cleanup correctness prevents connection leaks and data corruption, but it is an edge case (fatal failures are rare).

**Independent Test**: Can be fully tested by injecting a fatal step that raises an exception and asserting the database-close hook still runs.

**Acceptance Scenarios**:

1. **Given** a fatal step fails during startup, **When** the shutdown sequence runs, **Then** the database connection is still closed.
2. **Given** three shutdown hooks were registered in order A → B → C, **When** shutdown executes, **Then** hooks run in order C → B → A (LIFO).
3. **Given** a shutdown hook itself fails, **When** the remaining hooks execute, **Then** the failure is logged but does not prevent subsequent hooks from running.

---

### User Story 5 — Developer Reduces main.py Line Count (Priority: P3)

A developer wants the main application entry point to be concise and focused on orchestration rather than business logic. Today, main.py is approximately 900 lines, with over half dedicated to startup/shutdown logic and private helper functions. After this refactor, main.py shrinks to approximately 250 lines, with the startup/shutdown logic distributed across focused, single-responsibility modules.

**Why this priority**: Codebase readability and onboarding speed improve when the entry point is a short orchestrator, but this is a secondary benefit behind testability and maintainability.

**Independent Test**: Can be verified by counting lines in main.py and confirming no module in the new startup package exceeds 120 lines.

**Acceptance Scenarios**:

1. **Given** the refactor is complete, **When** main.py is measured, **Then** it contains no more than 250 lines.
2. **Given** the startup package is complete, **When** any single file in the package is measured, **Then** it contains no more than 120 lines.

---

### Edge Cases

- What happens when a conditional step's skip condition itself throws an exception? The runner MUST treat this as a step failure and apply the step's fatal/non-fatal policy.
- What happens when the same step name appears twice in the step list? The runner MUST reject duplicate names at startup with a clear error.
- What happens when a non-fatal step modifies shared state and then a later fatal step fails? Shutdown hooks MUST still run, and any partial state changes from the non-fatal step are not automatically rolled back (this mirrors current behaviour).
- What happens when a background loop coroutine is queued but the task group never starts (because a fatal step fails before that point)? The queued coroutines MUST be discarded without execution, and this MUST be logged.
- What happens during shutdown when a hook takes longer than expected? Each shutdown hook MUST be subject to a reasonable timeout to prevent shutdown from hanging indefinitely.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST extract each startup responsibility from the current lifespan function into a separate, named step module.
- **FR-002**: Each step MUST have a stable name identifier used in logs, metrics, and the startup outcome report.
- **FR-003**: Each step MUST be marked as either fatal (failure aborts startup) or non-fatal (failure is logged and startup continues).
- **FR-004**: Each step MAY have an optional skip condition that, when true, causes the runner to record the step as "skipped" and proceed to the next step.
- **FR-005**: The startup runner MUST execute steps sequentially in the order they appear in the declared step list.
- **FR-006**: The startup runner MUST measure wall-clock duration for each step and include it in the log output.
- **FR-007**: The startup runner MUST set a per-step correlation identifier for log tracing before executing each step.
- **FR-008**: When a fatal step fails, the runner MUST log the exception and re-raise it so the application framework aborts the cold start.
- **FR-009**: When a non-fatal step fails, the runner MUST log a warning with exception details and continue to the next step.
- **FR-010**: After all steps complete, the runner MUST collect and surface a startup outcome report (step name, status, duration, error if any) on the application state for future introspection.
- **FR-011**: The shutdown runner MUST execute registered shutdown hooks in reverse-registration order (LIFO).
- **FR-012**: Built-in trailing shutdown hooks (drain task registry, stop polling, close database) MUST always run, even if a fatal startup step failed or a shutdown hook itself fails.
- **FR-013**: Background loop coroutines queued by steps MUST be started inside the existing task group after all steps have completed.
- **FR-014**: The main entry point file MUST remain the location of the application factory function; only startup and shutdown logic moves to the new package.
- **FR-015**: All fifteen existing startup responsibilities MUST be preserved with identical side-effects and ordering after the refactor.
- **FR-016**: The private helper functions that implement long-running loops and startup tasks MUST be relocated verbatim (no behaviour changes) into the new step modules.
- **FR-017**: The refactor MUST be deliverable in multiple independent, individually-shippable pull requests that do not break the application between merges.
- **FR-018**: Each step module MUST be independently unit-testable with mocked dependencies and no requirement to boot the full application.

### Key Entities

- **Step**: A named unit of startup work with a stable identifier, a fatal/non-fatal designation, an async execution body, and an optional skip condition. Steps are the primary organisational unit of the new startup package.
- **StepOutcome**: The result of executing a single step, containing the step name, final status (ok, failed, skipped), wall-clock duration in milliseconds, and any captured error. A list of StepOutcomes forms the startup report.
- **StartupContext**: A mutable container passed to every step during execution. Holds references to the application instance, settings, database connection, task registry, a list of queued background coroutines, and a list of registered shutdown hooks. Steps read from and write to this context.
- **Startup Report**: An ordered list of StepOutcomes stashed on the application state after startup completes. Provides a machine-readable record of what happened during boot.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every startup step can be unit-tested in isolation — no step requires the full application to boot for testing — and test execution time for any single step is under 2 seconds.
- **SC-002**: The main entry point file contains no more than 250 lines after the full refactor is complete, down from approximately 900 lines today.
- **SC-003**: No single file in the new startup package exceeds 120 lines, ensuring each module stays focused on a single responsibility.
- **SC-004**: All existing integration tests continue to pass without modification, confirming zero behaviour change to the running application.
- **SC-005**: Each startup step produces exactly one structured log line containing the step name, execution status, and duration — verified via log capture in unit tests.
- **SC-006**: A fatal step failure during startup still results in the database connection being properly closed — verified by a dedicated shutdown-correctness test.
- **SC-007**: The refactor is delivered across four or fewer independently-shippable pull requests, with no PR introducing a broken state.
- **SC-008**: The startup step execution order after the refactor exactly matches the current execution order — verified by comparing log output between pre- and post-refactor boots.

## Assumptions

- The existing task group-based background task strategy is retained as-is; this refactor does not change how background tasks are managed at the async runtime level.
- Module-level singleton globals (e.g., `github_projects_service`, `connection_manager`) are out of scope for this refactor and will be addressed by a separate "dual-init" cleanup plan.
- The internal logic of each helper function (polling, cleanup, discovery) is unchanged; only the try/except wrapper and the physical file location change.
- The application factory function remains in the main entry point file; only the lifespan/startup/shutdown logic is extracted.
- A future health check endpoint may surface the startup report, but building that endpoint is out of scope for this feature.
- Pyright strict mode and Ruff BLE policy changes are handled by separate plans and are not part of this refactor.

## Scope Boundaries

### In Scope

- Creating the new startup package with protocol, runner, and step modules
- Relocating the fifteen startup responsibilities into individual step modules
- Relocating private helper functions (polling watchdog loop, session cleanup loop, copilot polling autostart, multi-project discovery, app pipeline polling restore, agent MCP sync) into step modules
- Building the startup and shutdown runner with timing, logging, and error handling
- Adding unit tests for the runner and each step
- Reducing main.py line count to approximately 250 lines

### Out of Scope

- Removing module-level singleton globals (separate "dual-init" cleanup plan)
- Adding a `/api/v1/healthz/startup` endpoint to expose the startup report
- Changing the task group-based background task lifecycle strategy
- Altering any step's internal business logic (moves are verbatim)
- Pyright strict mode or Ruff BLE policy changes
