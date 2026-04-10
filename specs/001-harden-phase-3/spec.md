# Feature Specification: Harden Phase 3 — Code Quality & Tech Debt

**Feature Branch**: `001-harden-phase-3`  
**Created**: 2026-04-10  
**Status**: Draft  
**Input**: User description: "Harden Phase 3 — Code Quality & Tech Debt: Remove module-level singletons tagged TODO(018-codebase-audit-refactor), upgrade pre-release dependencies, consolidate Stryker mutation configs, fix plan-mode orphaned chat history."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Remove Module-Level Singletons (Priority: P1)

As a developer working on Solune, I want all service instances to be obtained through a consistent dependency-injection pattern so that services are testable, lifecycle-managed, and free of hidden global state.

Currently, two module-level singleton instances (in the GitHub Projects service and agents modules) are imported directly by 27+ files. An accessor function already exists that prefers the registered instance and falls back to the module-level global. This story completes the migration: every consumer obtains the service through the accessor, and the module-level singletons are removed.

**Why this priority**: Module-level singletons create hidden coupling, make unit testing harder (global state leaks between tests), and block safe concurrent request handling. Eliminating them is the highest-value code-quality improvement because it affects the most files and removes the largest source of tech debt flagged by the codebase audit.

**Independent Test**: Can be fully tested by running the entire backend test suite after removing the module-level singletons and verifying that all 27+ consumer files obtain the service through the accessor. No user-facing behavior changes.

**Acceptance Scenarios**:

1. **Given** a backend codebase with two module-level singletons tagged `TODO(018-codebase-audit-refactor)`, **When** a developer removes both singletons and migrates all 27+ consumers to use the accessor pattern, **Then** the full backend test suite passes with no regressions.
2. **Given** a background task or non-request context that previously imported the singleton directly, **When** the task runs after migration, **Then** it obtains the service through the accessor's fallback path without errors.
3. **Given** a request-scoped context (API route handler), **When** it needs the service after migration, **Then** it receives the instance registered on `app.state` via the accessor.
4. **Given** the codebase after migration, **When** a developer searches for the old direct-import pattern, **Then** zero occurrences remain outside of the accessor's own fallback definition.

---

### User Story 2 — Upgrade Pre-Release Dependencies (Priority: P2)

As a developer, I want all pre-release and beta dependencies to be upgraded to their latest stable (or latest pre-release) versions so that Solune benefits from bug fixes, performance improvements, and API stabilizations — and so that the project is not blocked by known issues in outdated betas.

Eight packages are currently pinned to pre-release versions: the GitHub Copilot SDK (v0.x), Azure AI Inference (1.0.0b9), three Agent Framework packages (1.0.0b1), and three OpenTelemetry instrumentation packages (0.54b0). The Copilot SDK additionally requires a package rename from `github-copilot-sdk` to `copilot-sdk` as part of the v2 upgrade.

**Why this priority**: Outdated betas carry known bugs and may introduce breaking changes without warning. Upgrading reduces supply-chain risk and keeps the project aligned with upstream APIs. This is P2 because it does not change application behavior — it only changes versions — but a failed upgrade could temporarily break the build.

**Independent Test**: Can be fully tested by upgrading each package, running the full test suite (backend unit, integration, and e2e), and verifying that all tests pass. No user-facing behavior changes unless an upstream API changed semantics.

**Acceptance Scenarios**:

1. **Given** the current dependency manifest with 8 pre-release packages, **When** a developer upgrades all packages to their target versions, **Then** the dependency resolver installs successfully with no conflicts.
2. **Given** the upgraded dependencies, **When** the full backend test suite runs, **Then** all tests pass with no new failures.
3. **Given** the Copilot SDK rename from `github-copilot-sdk` to `copilot-sdk`, **When** a developer updates all import references, **Then** no import errors occur and all Copilot-dependent features work correctly.
4. **Given** the upgraded OpenTelemetry instrumentation packages, **When** the application starts and handles requests, **Then** telemetry data is emitted correctly with no instrumentation errors.

---

### User Story 3 — Consolidate Stryker Mutation Configs (Priority: P3)

As a developer running mutation tests, I want a single Stryker configuration entry point that supports shard selection so that I don't have to remember which of 4 separate config files to invoke and so that CI can dynamically select shards without maintaining duplicate configuration.

Currently the frontend has 5 Stryker config files: one base config and 4 shard configs (hooks-data, hooks-board, hooks-general, lib). Each shard duplicates threshold settings and only varies in its `mutate` glob patterns and report output paths.

**Why this priority**: This is a developer-experience improvement. Consolidation removes duplication, reduces the chance of config drift, and simplifies CI. It is P3 because it does not affect runtime behavior or code quality directly — only the developer workflow for running mutation tests.

**Independent Test**: Can be fully tested by running Stryker with each shard selection (e.g., via an environment variable) and verifying that the mutation report output matches the current per-config behavior.

**Acceptance Scenarios**:

1. **Given** 4 separate Stryker shard configs, **When** a developer consolidates them into a single entry point with shard selection, **Then** running the unified config with each shard produces the same mutation targets and report paths as the original separate configs.
2. **Given** the consolidated config, **When** a developer runs Stryker without specifying a shard, **Then** all mutation targets from all shards are included (full run).
3. **Given** the consolidated config, **When** CI selects a specific shard, **Then** only the mutation targets for that shard are executed.
4. **Given** the consolidation is complete, **When** a developer checks the frontend directory, **Then** the 4 individual shard config files have been removed and only the unified config remains.

---

### User Story 4 — Verify Plan-Mode Chat History Fix (Priority: P4)

As a user interacting with plan mode, I want my messages to only be saved after the plan-mode service is confirmed available so that I don't see orphaned messages in my chat history from failed plan-mode attempts.

Investigation confirms this fix is already implemented: both the non-streaming and streaming plan-mode endpoints persist user messages only after `get_chat_agent_service()` succeeds. This story requires verification only — no code changes.

**Why this priority**: This is P4 because the fix is already in place. The only work is to add or confirm test coverage ensuring the correct ordering is maintained, preventing future regressions.

**Independent Test**: Can be fully tested by simulating a plan-mode request where the service is unavailable and verifying that no user message is persisted. Then simulating a successful request and verifying the message is persisted.

**Acceptance Scenarios**:

1. **Given** the plan-mode chat service is unavailable, **When** a user sends a plan-mode message (non-streaming), **Then** no user message is persisted to the chat history and a service-unavailable response is returned.
2. **Given** the plan-mode chat service is unavailable, **When** a user sends a streaming plan-mode message, **Then** no user message is persisted and a service-unavailable response is returned.
3. **Given** the plan-mode chat service is available, **When** a user sends a plan-mode message, **Then** the user message is persisted to chat history after the service confirms availability.
4. **Given** regression test coverage for the message-persistence ordering, **When** a future change reorders the persist-then-check logic, **Then** the test fails, catching the regression.

---

### Edge Cases

- What happens if a background task needs the service during application shutdown, after `app.state` has been torn down? The accessor must handle a missing `app.state` gracefully (3.1).
- What happens if an upgraded dependency introduces a breaking API change? The upgrade must be tested incrementally, one package at a time, so that breakage is isolated (3.2).
- What happens if the Copilot SDK v2 rename leaves stale references to the old package name in lock files or transitive dependencies? A full dependency resolution and lock-file regeneration must be performed (3.2).
- What happens if a developer runs Stryker without setting the shard environment variable? The consolidated config must default to a full mutation run covering all targets (3.3).
- What happens if a new hook is added after consolidation? The general-shard pattern must automatically include new hooks not explicitly assigned to another shard (3.3).

## Requirements *(mandatory)*

### Functional Requirements

**3.1 — Singleton Removal**

- **FR-001**: The system MUST remove both module-level singleton instances currently tagged with `TODO(018-codebase-audit-refactor)`.
- **FR-002**: All files that currently import the module-level singletons directly MUST be migrated to use the existing accessor function.
- **FR-003**: The accessor function MUST continue to support a fallback path for non-request contexts (background tasks, signal bridges, orchestrators) where `app.state` is not available.
- **FR-004**: The `TODO(018-codebase-audit-refactor)` comment blocks MUST be removed from both files after migration is complete.
- **FR-005**: The full backend test suite MUST pass with no regressions after singleton removal.

**3.2 — Dependency Upgrades**

- **FR-006**: The system MUST upgrade the Copilot SDK from the current `github-copilot-sdk >=0.1.30,<1` to `copilot-sdk >=1.0.17` (package rename + version bump).
- **FR-007**: The system MUST upgrade `azure-ai-inference` from `>=1.0.0b9,<2` to the latest available version.
- **FR-008**: The system MUST upgrade all three `agent-framework-*` packages from `>=1.0.0b1` to the latest available versions.
- **FR-009**: The system MUST upgrade all three `opentelemetry-instrumentation-*` packages from `>=0.54b0,<1` to the latest available versions.
- **FR-010**: All import paths referencing the old Copilot SDK package name MUST be updated to match the new package name.
- **FR-011**: The dependency manifest and lock file MUST resolve cleanly with no conflicts after all upgrades.
- **FR-012**: The full test suite (backend and any integration tests exercising these dependencies) MUST pass after upgrades.

**3.3 — Stryker Config Consolidation**

- **FR-013**: The system MUST consolidate the 4 separate Stryker shard configs into a single unified configuration file.
- **FR-014**: The unified config MUST support shard selection (e.g., via an environment variable) so that each shard can be run independently.
- **FR-015**: When no shard is specified, the unified config MUST run all mutation targets (equivalent to running all 4 shard configs).
- **FR-016**: Each shard in the unified config MUST produce its report at the same output path as the original individual config.
- **FR-017**: The 4 individual shard config files MUST be removed after consolidation.
- **FR-018**: CI workflows referencing the old shard config file names MUST be updated to use the unified config with shard selection.

**3.4 — Plan-Mode Chat History Verification**

- **FR-019**: The system MUST NOT persist user messages to chat history when the plan-mode service is unavailable (verified, no code change expected).
- **FR-020**: Test coverage MUST exist confirming that user messages are persisted only after `get_chat_agent_service()` succeeds for both streaming and non-streaming plan-mode endpoints.

### Assumptions

- The existing accessor function in `dependencies.py` is the canonical pattern for obtaining the GitHub Projects service. No new accessor needs to be created.
- The "17+ non-request context files" referenced in the TODO comments include background tasks, signal bridges, and orchestrator modules that will use the accessor's fallback path.
- For dependency upgrades, "latest available version" means the latest published version at the time of implementation, whether stable or pre-release, as long as it is newer than the current pin. Stable releases are preferred over pre-release when both are available.
- The Stryker consolidation will use an environment variable (e.g., `STRYKER_SHARD`) for shard selection, following the pattern already identified in codebase analysis.
- Plan-mode chat history fix (3.4) requires no code changes — only verification and potential test additions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero occurrences of module-level singleton imports remain in the codebase (outside the accessor's fallback definition) after 3.1 is complete.
- **SC-002**: Zero `TODO(018-codebase-audit-refactor)` markers remain in the codebase after 3.1 is complete.
- **SC-003**: All 8 pre-release dependencies are upgraded to newer versions with the dependency resolver producing a clean install and all tests passing.
- **SC-004**: The Copilot SDK package rename is complete with zero references to the old package name in source code or configuration.
- **SC-005**: The number of Stryker configuration files in the frontend directory is reduced from 5 to 1 (the unified config).
- **SC-006**: Mutation test results from the unified config match the combined results of the 4 individual shard configs (same mutation targets, same thresholds).
- **SC-007**: Test coverage exists for plan-mode message persistence ordering, covering both streaming and non-streaming endpoints.
- **SC-008**: The full CI pipeline (backend tests, frontend tests, build validation) passes with no new failures after all changes are applied.
