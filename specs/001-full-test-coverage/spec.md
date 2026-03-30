# Feature Specification: 100% Test Coverage with Bug Fixes

**Feature Branch**: `001-full-test-coverage`  
**Created**: 2026-03-30  
**Status**: Draft  
**Input**: User description: "Plan: 100% Test Coverage with Bug Fixes"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Fix Known Bugs and Establish Green Baseline (Priority: P1)

As a developer, I need all known bugs and CI errors resolved so that the existing test suites pass reliably and provide a trustworthy foundation before adding new tests.

**Why this priority**: Without a green baseline, new test results are unreliable. Silent exception swallowing can mask production failures, and pinned CI dependencies prevent reproducible builds. This must come first.

**Independent Test**: Can be verified by running the full backend and frontend test suites end-to-end and confirming zero failures, zero warnings from the fixed areas, and correct error propagation in the patched code paths.

**Acceptance Scenarios**:

1. **Given** the CI pipeline references a devcontainer configuration, **When** CI runs, **Then** it uses a valid, pinned tag and completes without configuration errors.
2. **Given** a user calls a function that verifies project access and the verification fails, **When** the failure occurs, **Then** the error is logged or re-raised—never silently swallowed.
3. **Given** rate-limiting middleware resolves a user session, **When** the session resolution takes longer than the configured timeout, **Then** the request is handled gracefully without hanging indefinitely.
4. **Given** a validation error occurs in the MCP layer, **When** the error is raised, **Then** it includes field-level detail so the caller knows which input was invalid.
5. **Given** all bug fixes are applied, **When** the full backend and frontend test suites run, **Then** every test passes (green baseline established).

---

### User Story 2 — Raise Backend Test Coverage to 100% (Priority: P2)

As a developer, I need comprehensive backend tests covering all services, branches, and edge cases so that regressions are caught automatically and code changes can be made with confidence.

**Why this priority**: The backend is the system of record; untested service code (agent middleware, agent provider, collision resolver) and low branch coverage (69%) represent the highest risk for undetected regressions. Covering these paths directly reduces production incident likelihood.

**Independent Test**: Can be verified by running backend tests with coverage reporting and confirming line coverage ≥ 100% and branch coverage ≥ 100%. Mutation testing confirms that tests are meaningful (not just exercising code without asserting behavior).

**Acceptance Scenarios**:

1. **Given** agent middleware has zero test coverage, **When** tests are added for all code paths, **Then** coverage for that module reaches 100% line and branch.
2. **Given** agent provider has zero test coverage, **When** tests are added for all code paths, **Then** coverage for that module reaches 100% line and branch.
3. **Given** collision resolver has zero test coverage, **When** tests are added for all resolution strategies, **Then** coverage for that module reaches 100% line and branch.
4. **Given** the agents service is at 62% coverage, **When** tests are added for `_get_service()`, filter/sort logic, and all pending/purge/bulk branches, **Then** coverage for that module reaches 100%.
5. **Given** activity service has missing branch coverage at specific lines, **When** tests exercise every conditional path, **Then** branch coverage for that module reaches 100%.
6. **Given** files with less than 100% branch coverage exist, **When** tests are added for every conditional branch (error paths, edge cases, None values, empty collections), **Then** overall backend branch coverage reaches 100%.
7. **Given** integration flows for cache, encryption key rotation, MCP store, and template file I/O are untested, **When** integration tests are added, **Then** those flows are exercised and validated end-to-end.
8. **Given** property-based tests exist for some models, **When** Hypothesis property tests are extended to cover all Pydantic model roundtrips, URL parsing edge cases, and label extraction, **Then** those edge cases are covered.
9. **Given** migration tests exist, **When** rollback and corruption scenarios are added, **Then** migration robustness is validated.
10. **Given** all backend tests pass, **When** mutation testing runs on `src/services/`, **Then** at least 85% of mutants are killed.

---

### User Story 3 — Raise Frontend Test Coverage to 100% (Priority: P3)

As a developer, I need comprehensive frontend tests covering all components, hooks, and user flows so that UI regressions and accessibility issues are caught before reaching users.

**Why this priority**: Frontend coverage is currently at 50% statements / 44% branches / 41% functions. Many critical component categories (Agents, Board, Settings, Pipeline) have coverage between 0–28%. Users interact directly with these surfaces, making regressions highly visible.

**Independent Test**: Can be verified by running frontend tests with coverage reporting and confirming 100% across all metrics (statements, branches, functions, lines). Accessibility checks pass for every component.

**Acceptance Scenarios**:

1. **Given** 9 Agent components have 0% coverage, **When** tests are added for each (AddAgentModal, AgentAvatar, AgentCard, AgentChatFlow, AgentIconCatalog, AgentIconPickerModal, AgentInlineEditor, AgentsPanel, BulkModelUpdateDialog, ToolsEditor), **Then** each component has 100% coverage and passes accessibility validation.
2. **Given** Board components are at 24% coverage with ~20 untested files, **When** tests are added for all untested components, **Then** Board component coverage reaches 100%.
3. **Given** Settings components are at 24% coverage with ~12 untested files, **When** tests are added for all untested components, **Then** Settings component coverage reaches 100%.
4. **Given** Pipeline components are at 28% coverage with ~15 untested files, **When** tests are added for all untested components, **Then** Pipeline component coverage reaches 100%.
5. **Given** 4 hooks are untested (useAdaptivePolling, useBoardProjection, useConfirmation, useUndoRedo), **When** tests are added, **Then** each hook has 100% coverage.
6. **Given** ActivityPage has no test file, **When** a test file is created, **Then** the page has 100% coverage and passes accessibility validation.
7. **Given** all component tests exist, **When** error, loading, and empty states are tested for every component, **Then** branch coverage reaches 100%.
8. **Given** complex hooks and transforms exist, **When** property-based tests are added, **Then** edge cases in those hooks are validated.
9. **Given** the application has API interaction points, **When** negative path tests are added for error status codes (401, 403, 404, 500), invalid form inputs, and WebSocket disconnection, **Then** all error handling paths are covered.
10. **Given** App routing is at 0% coverage, **When** tests are added for route matching, lazy loading, and error boundaries, **Then** routing coverage reaches 100%.
11. **Given** E2E tests exist, **When** they are extended to cover ActivityPage, agent CRUD negative paths, and offline/error recovery, **Then** end-to-end flows are comprehensively validated.

---

### User Story 4 — Lock In 100% Thresholds and Prevent Regression (Priority: P4)

As a team lead, I need coverage thresholds permanently set to 100% and enforced in CI so that coverage can never regress without an explicit, reviewed decision.

**Why this priority**: Without locked-in thresholds, coverage naturally erodes over time as new code is added without tests. Hardening the pipeline ensures the investment in test coverage is protected long-term.

**Independent Test**: Can be verified by attempting to merge a change that reduces coverage below 100% and confirming CI rejects it.

**Acceptance Scenarios**:

1. **Given** backend coverage has reached 100%, **When** the coverage threshold configuration is updated, **Then** the minimum required coverage is set to 100%.
2. **Given** frontend coverage has reached 100%, **When** the coverage threshold configuration is updated, **Then** all metric thresholds (statements, branches, functions, lines) are set to 100%.
3. **Given** mutation testing scope covers only services, **When** the scope is expanded, **Then** mutation testing covers all source code.
4. **Given** frontend mutation testing scope is limited, **When** the scope is expanded, **Then** mutation testing includes components and pages.
5. **Given** module-level singletons exist as technical debt, **When** they are refactored to use dependency injection, **Then** the modules are independently testable without global state.
6. **Given** all thresholds are locked, **When** a code change is pushed that decreases coverage, **Then** CI fails and the change cannot merge.

---

### Edge Cases

- What happens when a test file import fails due to a circular dependency introduced during coverage expansion?
- How does the system handle a component that only renders conditionally (e.g., behind a feature flag) — is coverage still required?
- What happens when mutation testing generates a mutant in auto-generated or vendored code?
- How does the team handle a scenario where 100% coverage is unreachable for a specific code path (e.g., platform-specific branches, defensive unreachable code)?
- What happens when a third-party dependency update causes a previously passing test to fail during the coverage campaign?
- How are flaky tests handled — tests that pass intermittently and may inflate perceived coverage?

## Requirements *(mandatory)*

### Functional Requirements

**Phase 1: Bug Fixes & CI Stability**

- **FR-001**: CI configuration MUST reference a valid, pinned tag for devcontainer dependencies (not a floating or invalid tag).
- **FR-002**: The project access verification function MUST either log or re-raise exceptions — silent swallowing MUST be eliminated.
- **FR-003**: Rate-limiting middleware MUST enforce a configurable timeout on session resolution to prevent indefinite blocking.
- **FR-004**: Validation errors in the MCP layer MUST include field-level error details in the exception payload.
- **FR-005**: All existing test suites MUST pass (green baseline) before new tests are added.

**Phase 2: Backend Untested Services**

- **FR-006**: Every backend service module MUST have a corresponding test module covering all code paths.
- **FR-007**: New test files MUST follow existing conventions: fixture-based setup, factory-generated test data, centralized assertion helpers, async-compatible mocking, and class-based test organization.
- **FR-008**: Backend line coverage MUST reach at least 85% after this phase; branch coverage MUST reach at least 80%.
- **FR-009**: Mutation testing MUST kill at least 80% of mutants in newly tested service modules.

**Phase 3: Backend Branch Coverage Blitz**

- **FR-010**: Every backend source file MUST achieve at least 90% branch coverage.
- **FR-011**: Integration tests MUST cover cache layer, encryption key rotation, MCP store, and template file I/O error scenarios.
- **FR-012**: Property-based tests MUST validate all data model roundtrips, URL parsing edge cases, and label extraction.
- **FR-013**: Migration tests MUST cover rollback and data corruption recovery scenarios.
- **FR-014**: Overall backend line coverage MUST reach at least 95%; branch coverage MUST reach at least 90%.
- **FR-015**: Mutation testing MUST kill at least 85% of mutants in `src/services/`.

**Phase 4: Frontend Component Coverage Sprint**

- **FR-016**: Every frontend component MUST have a corresponding test file.
- **FR-017**: Every component test MUST include an accessibility validation check.
- **FR-018**: Component tests MUST use the project's custom render utility (from test-utils) for consistent provider wrapping.
- **FR-019**: All untested hooks MUST have dedicated test coverage.
- **FR-020**: Every page component MUST have a test file (including newly created pages like ActivityPage).
- **FR-021**: Frontend coverage MUST reach at least 80% across all metrics (statements, branches, functions, lines) after this phase.

**Phase 5: Frontend Branch & Edge Case Coverage**

- **FR-022**: Every frontend source file MUST achieve 100% branch coverage.
- **FR-023**: Every component MUST be tested in its error, loading, and empty states.
- **FR-024**: Negative path tests MUST cover all common HTTP error codes (401, 403, 404, 500), invalid form submissions, and WebSocket disconnection.
- **FR-025**: Application routing MUST be tested: route matching, lazy-loaded module loading, and error boundary behavior.
- **FR-026**: E2E tests MUST cover activity page flows, agent CRUD negative paths, and offline/error recovery.
- **FR-027**: Frontend coverage MUST reach 100% across all metrics after this phase.
- **FR-028**: Frontend mutation testing MUST kill at least 80% of mutants in hooks and library modules.

**Phase 6: Hardening & Threshold Lock-In**

- **FR-029**: Backend coverage threshold MUST be set to 100% (fail-under) in the project configuration.
- **FR-030**: Frontend coverage thresholds MUST be set to 100/100/100/100 (statements/branches/functions/lines).
- **FR-031**: Backend mutation testing scope MUST be expanded from services-only to all source code.
- **FR-032**: Frontend mutation testing scope MUST be expanded to include components and pages.
- **FR-033**: Module-level singletons MUST be refactored to a dependency injection pattern for testability.
- **FR-034**: CI MUST include a coverage regression guard that fails the build on any coverage decrease.

**Cross-Cutting Requirements**

- **FR-035**: No new test frameworks MUST be introduced — all tests MUST follow existing conventions exactly.
- **FR-036**: No feature work or unnecessary refactoring MUST be included — scope is limited to coverage improvement and bug fixes.
- **FR-037**: Decorative/trivial components MUST still be tested for rendering correctness and accessibility compliance.

### Assumptions

- The current test infrastructure (fixtures, factories, assertion helpers, custom render utilities) is sufficient and does not need replacement.
- Existing coverage tooling and reporting is correctly configured and produces accurate results.
- The 6-phase ordering reflects actual dependency relationships: Phase 1 must complete before any other phase; Phase 3 depends on Phase 2; Phase 5 depends on Phase 4; Phase 6 depends on all prior phases. Phases 3 and 4 can run in parallel.
- "100% coverage" refers to 100% of measurable lines, branches, functions, and statements — excluding any lines explicitly marked as uncoverable (e.g., type-only imports, defensive unreachable branches documented with justification).
- Mutation testing thresholds are soft targets during intermediate phases and become hard requirements in Phase 6.
- The singleton refactor in Phase 6 is intentionally deferred until a full coverage safety net exists, minimizing risk of introducing regressions during the refactor.

### Dependencies

- **Phase ordering**: Phase 1 → Phase 2 → Phase 3 (backend); Phase 1 → Phase 4 → Phase 5 (frontend); Phases 3 and 4 are independent and parallelizable; Phase 6 depends on completion of Phases 3 and 5.
- **CI pipeline**: Must support coverage reporting, threshold enforcement, and mutation testing for both backend and frontend.
- **Existing test infrastructure**: Fixtures, factories, helpers, and custom render utilities must be available and functional.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All known bugs from Phase 1 are resolved and the full test suite passes with zero failures (green baseline achieved).
- **SC-002**: Backend line coverage reaches 100%; backend branch coverage reaches 100%.
- **SC-003**: Frontend statement coverage reaches 100%; frontend branch coverage reaches 100%; frontend function coverage reaches 100%; frontend line coverage reaches 100%.
- **SC-004**: Backend mutation testing kills at least 85% of generated mutants across all source code.
- **SC-005**: Frontend mutation testing kills at least 80% of generated mutants across hooks, library modules, components, and pages.
- **SC-006**: Every frontend component test includes and passes an accessibility validation check.
- **SC-007**: CI rejects any code change that decreases coverage below 100% for either backend or frontend.
- **SC-008**: Total backend test file count increases from 202 to cover all modules (every source file has a corresponding test).
- **SC-009**: Total frontend test file count increases from 180 to cover all components, hooks, pages, and modules.
- **SC-010**: All 6 phases complete successfully with each phase's verification criteria met before proceeding to the next dependent phase.
