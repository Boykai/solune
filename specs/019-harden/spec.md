# Feature Specification: #Harden

**Feature Branch**: `019-harden`
**Created**: 2026-04-10
**Status**: Draft
**Input**: User description: "Harden Solune's reliability, code quality, CI/CD, observability, and developer experience — no new features, just making what exists better."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Fix Malformed Agent Config Crash (Priority: P1)

As a developer using Solune's chat refinement workflow, I want the system to gracefully reject malformed agent configurations so that broken config entries never crash the chat interface or produce confusing errors.

**Why this priority**: A malformed-but-parseable agent config (e.g., `tools: [123, null, {}]`) currently escapes validation and breaks chat refinement at runtime. This is the only remaining unresolved bug in the hardening scope and directly impacts user-facing reliability.

**Independent Test**: Can be tested by submitting an agent config with invalid tool entries and verifying the system returns a safe fallback (None) instead of a crash or corrupted preview.

**Acceptance Scenarios**:

1. **Given** an agent config where `tools` is a string (e.g., `tools: "read"`), **When** `_extract_agent_preview()` processes it, **Then** the function returns `None` and chat refinement continues without error.
2. **Given** an agent config where `tools` contains non-string elements (e.g., `tools: [123, null, {}]`), **When** `_extract_agent_preview()` processes it, **Then** the function returns `None`.
3. **Given** an agent config where `tools` contains empty strings (e.g., `tools: ["", " "]`), **When** `_extract_agent_preview()` processes it, **Then** the function returns `None`.
4. **Given** a valid agent config with proper tool entries (e.g., `tools: ["read", "write"]`), **When** `_extract_agent_preview()` processes it, **Then** the function returns a valid `AgentPreview` object as before.

---

### User Story 2 — Increase Backend Test Coverage (Priority: P1)

As a maintainer of the Solune backend, I want comprehensive test coverage across all modules so that regressions are caught before they reach production and new contributors can safely modify code with confidence.

**Why this priority**: Approximately 30 backend modules (prompt templates, copilot polling internals, MCP tools, chores service, middleware) have zero test coverage. Raising the coverage threshold from 75% to 80% ensures ongoing quality enforcement via CI.

**Independent Test**: Can be verified by running the backend test suite with coverage reporting and confirming the report meets the 80% threshold with no untested critical modules.

**Acceptance Scenarios**:

1. **Given** the backend test suite, **When** a full coverage run completes, **Then** overall line coverage is at or above 80%.
2. **Given** each of the ~30 previously untested modules, **When** the test suite runs, **Then** each module has at least one test exercising its primary logic path.
3. **Given** the `pyproject.toml` configuration, **When** CI runs coverage checks, **Then** the `fail_under` threshold is set to 80 and enforced.

---

### User Story 3 — Increase Frontend Test Coverage (Priority: P1)

As a maintainer of the Solune frontend, I want expanded component-level test coverage so that UI regressions are caught early and the codebase remains safe to refactor.

**Why this priority**: Approximately 61 frontend components across 7 feature areas (chores, agents, tools, settings, UI primitives, pipeline, chat) lack tests. Raising thresholds ensures ongoing quality gates.

**Independent Test**: Can be verified by running the frontend test suite with coverage reporting and confirming the updated thresholds are met: statements 60%, branches 52%, functions 50%, lines 60%.

**Acceptance Scenarios**:

1. **Given** the frontend test suite, **When** a full coverage run completes, **Then** statement coverage is at or above 60%, branch coverage at or above 52%, function coverage at or above 50%, and line coverage at or above 60%.
2. **Given** each of the ~61 previously untested components, **When** the test suite runs, **Then** each component has at least one test covering its primary render and interaction paths.
3. **Given** the frontend test configuration, **When** CI runs coverage checks, **Then** the updated thresholds are enforced.

---

### User Story 4 — Expand Property-Based Testing (Priority: P2)

As a maintainer, I want property-based tests covering round-trip serialization, API validation edge cases, and migration idempotency so that subtle data-corruption and boundary-condition bugs are caught automatically.

**Why this priority**: Only 7 backend and 6 frontend property test files exist. Property-based testing catches edge cases that example-based tests miss, particularly around data serialization and validation boundaries.

**Independent Test**: Can be verified by running the property test suites and confirming new test files cover round-trip serialization, API validation, and migration idempotency scenarios.

**Acceptance Scenarios**:

1. **Given** any backend model (Agent, Pipeline, Chat), **When** it is serialized and then deserialized, **Then** the result is identical to the original (round-trip property).
2. **Given** any API endpoint, **When** it receives boundary or randomized input, **Then** it either returns a valid response or a well-formed error — never a crash or corrupted state.
3. **Given** a database migration, **When** it is applied, rolled back, and re-applied, **Then** the final schema state is identical to a single application (idempotency property).

---

### User Story 5 — Integrate Accessibility Auditing in E2E Tests (Priority: P2)

As a user with assistive technology, I want all primary application flows to pass automated accessibility audits so that the application is usable regardless of ability.

**Why this priority**: The `@axe-core/playwright` package is installed but only used in 2 of 19 E2E spec files. Expanding a11y checks to auth, board, chat, and settings flows ensures accessibility compliance across the most important user journeys.

**Independent Test**: Can be verified by running the E2E suite and confirming that axe-core a11y assertions pass on auth, board, chat, and settings pages with zero violations.

**Acceptance Scenarios**:

1. **Given** the login and logout pages, **When** an axe-core accessibility audit runs, **Then** zero accessibility violations are reported.
2. **Given** the board navigation view, **When** an axe-core accessibility audit runs, **Then** zero accessibility violations are reported.
3. **Given** the chat interaction interface, **When** an axe-core accessibility audit runs, **Then** zero accessibility violations are reported.
4. **Given** the settings pages, **When** an axe-core accessibility audit runs, **Then** zero accessibility violations are reported.

---

### User Story 6 — Remove Module-Level Singletons (Priority: P2)

As a developer contributing to Solune, I want module-level singletons replaced with a consistent dependency-injection pattern so that services are easier to test, mock, and reason about.

**Why this priority**: Two service files contain module-level singletons tagged with `TODO(018-codebase-audit-refactor)`. These singletons make testing harder and violate the project's DI conventions. Refactoring to use `app.state` consistently improves maintainability.

**Independent Test**: Can be verified by confirming that the singleton module-level variables are removed, an accessor function pattern is in place, and all 17+ consuming files work correctly (passing CI).

**Acceptance Scenarios**:

1. **Given** the refactored service modules, **When** a request-context caller accesses the service, **Then** it retrieves the instance from `app.state` via the accessor function.
2. **Given** the refactored service modules, **When** a non-request caller (background task) accesses the service, **Then** it retrieves the instance via the accessor function's fallback mechanism.
3. **Given** the refactored codebase, **When** the full test suite runs, **Then** all tests pass without modification to test assertions (only mock targets may change).
4. **Given** the refactored codebase, **When** searching for `TODO(018-codebase-audit-refactor)`, **Then** no singleton TODO markers remain in service.py or agents.py.

---

### User Story 7 — Upgrade Pre-Release Dependencies (Priority: P3)

As a maintainer, I want pre-release dependencies upgraded to their latest stable (or latest pre-release) versions so that the project stays current, reduces upgrade debt, and benefits from upstream fixes.

**Why this priority**: Eight packages are pinned to early pre-release versions. Deferring upgrades increases the risk of breaking changes accumulating, while serial upgrades with CI validation manage risk incrementally.

**Independent Test**: Can be verified by upgrading each dependency in isolation, running the full CI suite after each upgrade, and confirming no test regressions.

**Acceptance Scenarios**:

1. **Given** the OpenTelemetry instrumentation packages, **When** upgraded to the latest compatible version, **Then** all CI jobs pass and telemetry data is emitted correctly.
2. **Given** the `azure-ai-inference` package, **When** upgraded to the latest 1.x version, **Then** all AI inference calls succeed and CI passes.
3. **Given** the `agent-framework-*` packages, **When** upgraded to the latest 1.x beta, **Then** agent orchestration functions correctly and CI passes.
4. **Given** the `github-copilot-sdk` package, **When** upgraded from v0.x to v2 (`>=1.0.17`), **Then** all Copilot integration features work and CI passes.

---

### User Story 8 — Consolidate Stryker Mutation Configs (Priority: P3)

As a developer running mutation tests, I want a single unified Stryker configuration so that mutation testing is simpler to run, maintain, and extend.

**Why this priority**: Four specialized Stryker configs share approximately 80% of their content. Consolidating into one file with target selection reduces maintenance overhead and configuration drift.

**Independent Test**: Can be verified by running `npx stryker run` with each target profile (all, hooks-board, hooks-data, hooks-general, lib) and confirming identical mutation results compared to the current separate configs.

**Acceptance Scenarios**:

1. **Given** the unified `stryker.config.mjs`, **When** run with `STRYKER_TARGET=all`, **Then** all mutation targets are tested and results match the combined output of the previous separate configs.
2. **Given** the unified config, **When** run with a specific target (e.g., `STRYKER_TARGET=hooks-board`), **Then** only the board hooks are mutated and results match the previous `stryker-hooks-board.config.mjs` output.
3. **Given** the repository, **When** searching for Stryker config files, **Then** only `stryker.config.mjs` exists (the 4 specialized configs have been removed).
4. **Given** CI workflows and package.json scripts, **When** mutation testing is triggered, **Then** the unified config is referenced correctly.

---

### Edge Cases

- What happens when `_extract_agent_preview()` receives a config with `tools: None`? The function must return `None` without raising an exception.
- What happens when a dependency upgrade introduces a breaking API change? Each upgrade is an isolated commit with a full CI gate; a failing upgrade is reverted before proceeding.
- What happens when coverage thresholds are raised but new tests are flaky? Flaky tests must be identified and stabilized before the threshold increase is merged — thresholds should only be raised after confirmed stable coverage.
- What happens when axe-core reports violations that are false positives or upstream library issues? Known false positives should be documented and suppressed with specific axe-core rule exclusions, not blanket disables.
- What happens when the Stryker target environment variable is unset? The unified config should default to the "all" target, preserving current behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST return `None` from `_extract_agent_preview()` when the `tools` field is not a list.
- **FR-002**: System MUST return `None` from `_extract_agent_preview()` when any element in the `tools` list is not a non-empty string.
- **FR-003**: System MUST enforce a backend test coverage threshold of 80% in CI.
- **FR-004**: System MUST enforce frontend test coverage thresholds of 60% statements, 52% branches, 50% functions, and 60% lines in CI.
- **FR-005**: System MUST include property-based tests for round-trip serialization of all core backend models.
- **FR-006**: System MUST include property-based tests for API validation boundary conditions.
- **FR-007**: System MUST include property-based tests verifying database migration idempotency.
- **FR-008**: System MUST run axe-core accessibility audits in E2E tests for auth, board, chat, and settings flows.
- **FR-009**: System MUST provide service instances through accessor functions rather than module-level singletons for the two services tagged with `TODO(018-codebase-audit-refactor)`.
- **FR-010**: System MUST support request-context and non-request-context service access through the accessor pattern.
- **FR-011**: System MUST upgrade all eight identified pre-release dependencies to their latest compatible versions with isolated CI validation per upgrade.
- **FR-012**: System MUST consolidate the four specialized Stryker mutation configs into a single unified config with target selection.
- **FR-013**: The unified Stryker config MUST default to the "all" target when no target is specified.

### Key Entities

- **BoundedDict**: A capacity-limited ordered dictionary with LRU-like eviction. Used for the resolved memory leak fix (already in place). Key attributes: `maxlen`, `touch()` method for LRU refresh.
- **AgentPreview**: A data model representing a preview of an agent configuration. Key attributes: `tools` (list of strings), config metadata. The validation gap in its construction is the target of FR-001/FR-002.
- **Service Singletons**: Module-level instances of `GitHubProjectsService` and `AgentsService` that need refactoring to accessor functions. Key relationships: consumed by 17+ modules including background tasks and request handlers.
- **Stryker Config**: Mutation testing configuration controlling which source files are mutated. Key attributes: `mutate` glob patterns, runner settings, reporter settings, score thresholds.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero runtime crashes caused by malformed agent configurations containing non-string tool entries, empty strings, or null values.
- **SC-002**: Backend test coverage reaches or exceeds 80% as reported by the CI coverage tool, up from the current 75% threshold.
- **SC-003**: Frontend test coverage meets or exceeds the raised thresholds — 60% statements, 52% branches, 50% functions, 60% lines — as reported by the CI coverage tool.
- **SC-004**: Property-based test file count increases from 13 total (7 backend + 6 frontend) to at least 19 total, covering round-trip serialization, API validation edge cases, and migration idempotency.
- **SC-005**: Axe-core accessibility audits run in at least 6 E2E spec files (up from 2), covering auth, board, chat, and settings flows with zero violations.
- **SC-006**: Module-level singleton TODO markers (`TODO(018-codebase-audit-refactor)`) are eliminated from both service files, and all 17+ consuming modules function correctly via the accessor pattern.
- **SC-007**: All eight pre-release dependencies are upgraded to their latest compatible versions with zero test regressions after each upgrade.
- **SC-008**: Stryker mutation testing operates from a single config file, reducing configuration files from 5 to 1, with identical mutation results across all targets.
- **SC-009**: All CI pipeline jobs pass after each phase of changes is merged, confirming no regressions are introduced.

## Assumptions

- Bugs 1.1 (memory leak), 1.2 (lifecycle status), and 3.4 (orphaned chat history) are already resolved in the current codebase and require no further action. This is confirmed by prior research (see `research.md` R1, R2, R7).
- The existing `BoundedDict` utility in `utils.py` is stable and does not need modification.
- The `@axe-core/playwright` package version `^4.10.1` currently installed is sufficient for the a11y integration work.
- Pre-release dependency upgrades will target the latest available version at the time of implementation; exact version numbers will be determined during the upgrade process.
- The 80% backend coverage and raised frontend thresholds are achievable with the ~91 identified untested modules/components without requiring major architectural changes.
- The singleton refactor will follow the accessor-function pattern documented in the existing TODO comments, not introduce a new DI framework.
- The Stryker consolidation will use an environment variable (`STRYKER_TARGET`) for target selection, consistent with how the CI workflow parameterizes other tools.

## Scope Boundaries

### In Scope

- Fix the residual validation gap in `_extract_agent_preview()` (Bug 1.3)
- Write new unit tests for ~30 untested backend modules
- Write new component tests for ~61 untested frontend components
- Expand property-based tests (backend and frontend)
- Integrate axe-core into additional E2E specs
- Refactor two module-level singletons to accessor functions
- Upgrade eight pre-release dependencies
- Consolidate Stryker mutation configs

### Out of Scope

- New user-facing features or UI changes
- Database schema changes or migrations
- API contract changes (no new endpoints, no breaking changes)
- Bugs 1.1, 1.2, and 3.4 (already resolved)
- Performance optimization beyond preventing regressions
- Changes to the CI/CD pipeline structure (only config threshold updates)
- Upgrading stable (non-pre-release) dependencies
