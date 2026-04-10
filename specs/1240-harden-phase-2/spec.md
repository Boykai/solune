# Feature Specification: Harden Phase 2 — Test Coverage Improvement

**Feature Branch**: `1240-harden-phase-2`  
**Created**: 2026-04-10  
**Status**: Draft  
**Input**: User description: "Solune's reliability, code quality, CI/CD, observability, and developer experience — no new features, just making what exists better. Phase 2 — Test Coverage Improvement: 2.1 Backend coverage 75→80%, 2.2 Frontend coverage (statements 50→60%, branches 44→52%, functions 41→50%), 2.3 Property-based testing expansion, 2.4 Axe-core/Playwright accessibility integration."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Backend Test Depth (Priority: P1)

As a developer working on Solune's backend, I want all modules to have thorough test coverage so that regressions are caught before they reach production, and the team can confidently refactor code without fear of breaking existing behavior.

**Why this priority**: Backend modules power all user-facing functionality. Gaps in coverage for prompt templates, copilot polling, MCP tools, chores service, and middleware create blind spots where bugs can hide in error paths, edge cases, and async code paths. Raising the coverage threshold from 75% to 80% directly reduces production incident risk.

**Independent Test**: Can be fully tested by running `pytest --cov=src --cov-fail-under=80` on the backend and confirming all new tests pass. Delivers the value of a higher confidence bar for every future backend change.

**Acceptance Scenarios**:

1. **Given** the backend test suite at 75% coverage, **When** a developer runs the full test suite with coverage reporting, **Then** overall coverage meets or exceeds 80%.
2. **Given** a backend module with untested error paths (e.g., middleware request-ID propagation with missing headers), **When** new tests are added for those paths, **Then** the tests exercise the error-handling code and confirm the expected behavior.
3. **Given** the backend CI job enforces `fail_under = 75`, **When** the threshold is raised to 80 and the test suite runs, **Then** the CI job passes without failure.
4. **Given** a previously untested branch in a prompt template module, **When** a test exercises that branch with edge-case input (empty strings, special characters), **Then** the template produces a valid output or raises an appropriate error.

---

### User Story 2 — Frontend Component Test Coverage (Priority: P1)

As a developer working on Solune's frontend, I want every user-facing component to have unit tests so that UI regressions are caught early, and threshold enforcement prevents coverage from eroding over time.

**Why this priority**: Approximately 69 frontend components lack any test coverage. These span user-critical flows including chores management, agent configuration, tool selection, settings, pipeline visualization, and shared UI primitives. Without tests, UI changes risk breaking existing functionality with no automated safety net.

**Independent Test**: Can be fully tested by running `npx vitest run --coverage` on the frontend and confirming thresholds (statements ≥ 60%, branches ≥ 52%, functions ≥ 50%, lines ≥ 60%) are met. Delivers the value of a reliable UI test baseline.

**Acceptance Scenarios**:

1. **Given** ~69 frontend components without test files, **When** test files are created for each component, **Then** each test file covers at minimum: rendering without errors, key user interactions, and primary state changes.
2. **Given** frontend coverage thresholds at statements 50%, branches 44%, functions 41%, lines 50%, **When** the new tests are added and thresholds updated, **Then** the frontend CI job passes with statements ≥ 60%, branches ≥ 52%, functions ≥ 50%, lines ≥ 60%.
3. **Given** a component that depends on hooks or external services, **When** its test file mocks those dependencies, **Then** the component renders correctly and handles mock return values as expected.
4. **Given** a shared UI primitive (e.g., confirmation dialog, tooltip) used across multiple features, **When** its test covers accessibility attributes and keyboard interactions, **Then** the test confirms the component meets basic usability expectations.

---

### User Story 3 — Property-Based Testing Expansion (Priority: P2)

As a developer, I want property-based tests to cover data serialization boundaries, validation edge cases, and migration idempotency so that the system is resilient to unexpected inputs and data transformations.

**Why this priority**: Property-based tests catch classes of bugs that example-based tests miss — boundary values, Unicode handling, round-trip serialization fidelity, and state machine invariants. Currently only 15 property test files exist (9 backend, 6 frontend). Expanding this coverage hardens the most fragile data paths.

**Independent Test**: Can be fully tested by running `pytest tests/property/ -v` (backend) and `npx vitest run --testPathPattern="property"` (frontend). Delivers the value of confidence that data serialization and validation are correct for arbitrary valid inputs.

**Acceptance Scenarios**:

1. **Given** a backend data model used in API requests and responses, **When** a property test generates arbitrary valid instances and round-trips them through serialization (model → dictionary → model), **Then** the reconstructed model equals the original for all generated instances.
2. **Given** API validation rules that restrict field lengths, character sets, or value ranges, **When** a property test generates inputs at and beyond these boundaries, **Then** the validation layer correctly accepts valid inputs and rejects invalid ones with appropriate error messages.
3. **Given** a data migration that transforms pipeline configurations, **When** a property test applies the migration to an arbitrary valid configuration twice, **Then** the result is identical after the first and second application (idempotency).
4. **Given** frontend utility functions that parse, format, or transform data, **When** a property test generates arbitrary valid inputs, **Then** the functions satisfy defined invariants (e.g., parse ∘ format = identity).

---

### User Story 4 — Accessibility Auditing in E2E Tests (Priority: P2)

As a user who relies on assistive technology, I want Solune's key workflows to pass automated accessibility checks so that I can navigate and use the application without barriers.

**Why this priority**: The @axe-core/playwright library is already installed and used in 2 E2E spec files, but 4 user-critical flows (authentication, board navigation, chat interaction, settings management) lack accessibility audits. Integrating axe-core checks into these flows ensures WCAG 2.1 compliance is monitored continuously.

**Independent Test**: Can be fully tested by running `npx playwright test` and confirming that all E2E specs with axe-core checks pass with zero violations for WCAG 2.1 AA tags. Delivers the value of automated accessibility regression detection.

**Acceptance Scenarios**:

1. **Given** the authentication flow E2E spec, **When** an accessibility audit runs on the login page after it fully loads, **Then** zero WCAG 2.1 AA violations are reported.
2. **Given** the board navigation E2E spec, **When** an accessibility audit runs on the projects board view, **Then** zero WCAG 2.1 AA violations are reported.
3. **Given** the chat interaction E2E spec, **When** an accessibility audit runs on the chat view within a project, **Then** zero WCAG 2.1 AA violations are reported.
4. **Given** the settings management E2E spec, **When** an accessibility audit runs on the settings page, **Then** zero WCAG 2.1 AA violations are reported.
5. **Given** a new UI change that introduces an accessibility violation, **When** the E2E suite runs in CI, **Then** the axe-core check fails and reports the specific violation, preventing the change from merging unnoticed.

---

### Edge Cases

- What happens when a backend module has 100% line coverage but untested branches? Tests must target branch coverage, not just line execution.
- How does the system handle a frontend component that cannot be rendered without a complex provider hierarchy? Tests must use the existing `@/test/test-utils` wrapper that provides required context providers.
- What happens when a property test discovers an actual bug in production code? The bug is filed as a separate issue; the property test is still merged as-is to prevent regression.
- What happens when an axe-core audit finds accessibility violations in existing UI? Violations are triaged: critical violations are fixed immediately; non-critical violations are documented and addressed in a follow-up issue. The `axe.exclude()` API can temporarily exclude known-issue elements to unblock the pipeline.
- What happens when adding tests for a component causes the test suite to exceed timeout limits? Individual slow tests are profiled, and expensive mocks are optimized. CI timeout configurations are not changed.
- What happens when a round-trip serialization property test fails due to floating-point precision? The test strategy constrains numeric generation to values that survive JSON serialization without precision loss, or uses approximate equality where appropriate.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backend test suite MUST achieve at least 80% combined line and branch coverage as measured by pytest-cov.
- **FR-002**: All ~30 backend module groups with coverage gaps (prompts, copilot polling, MCP tools, chores service, middleware) MUST have tests that exercise error paths, guard clauses, and async exception handlers.
- **FR-003**: The backend `fail_under` threshold in `pyproject.toml` MUST be raised from 75 to 80 as the final step, after all new tests are verified passing.
- **FR-004**: The frontend test suite MUST achieve at least 60% statement coverage, 52% branch coverage, 50% function coverage, and 60% line coverage as measured by Vitest v8.
- **FR-005**: All ~69 untested frontend components MUST have at least one test file that covers rendering, primary user interactions, and key state changes.
- **FR-006**: The frontend coverage thresholds in `vitest.config.ts` MUST be raised to statements 60, branches 52, functions 50, lines 60 as the final step, after all new tests are verified passing.
- **FR-007**: The backend property test suite MUST include new tests for round-trip serialization of API models, API validation boundary conditions, and migration idempotency.
- **FR-008**: The frontend property test suite MUST include new tests for API type round-trip serialization, form validation edge cases, and pipeline state transition invariants.
- **FR-009**: The E2E test suite MUST include @axe-core/playwright accessibility audits for the authentication, board navigation, chat interaction, and settings management flows.
- **FR-010**: All accessibility audits MUST check against WCAG 2.1 tags: wcag2a, wcag2aa, wcag21a, and wcag21aa.
- **FR-011**: All new tests MUST pass in the existing CI pipeline without modifying CI job configuration or adding new CI jobs.
- **FR-012**: All existing tests MUST continue to pass after the new tests are added — zero regressions allowed.
- **FR-013**: Frontend component tests MUST use the established test utilities (`@/test/test-utils`) and follow existing patterns (co-located test files, `vi.mock()` for dependency isolation).
- **FR-014**: Backend tests MUST use the established test infrastructure (conftest.py fixtures, pytest markers, async test support via `asyncio_mode = "auto"`).
- **FR-015**: Coverage threshold bumps (FR-003 and FR-006) MUST be the final commits in their respective workstreams to avoid blocking CI before all tests are written.

### Key Entities

- **Coverage Threshold**: Represents a numeric coverage gate enforced by CI tooling. Defined in configuration files (`pyproject.toml` for backend, `vitest.config.ts` for frontend). Key attributes: metric name, current value, target value, ecosystem.
- **Untested Component**: A frontend component file that lacks a corresponding test file. Key attributes: component name, category (chores/agents/tools/settings/ui/pipeline), file path, test status (untested/partial/covered).
- **Property Test File**: A test file using property-based testing (Hypothesis or fast-check). Key attributes: file name, ecosystem, testing strategy type (round-trip/invariant/stateful/validation/idempotency), status (existing/planned).
- **E2E Accessibility Spec**: An E2E Playwright spec file with @axe-core/playwright integration. Key attributes: spec file path, target routes, authentication fixture type, WCAG tag set.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Backend test coverage reaches or exceeds 80% (up from 75%) as measured by the CI coverage report, with no regressions in any existing test.
- **SC-002**: Frontend statement coverage reaches or exceeds 60% (up from 50%), branch coverage reaches or exceeds 52% (up from 44%), function coverage reaches or exceeds 50% (up from 41%), and line coverage reaches or exceeds 60% (up from 50%).
- **SC-003**: At least 6 new property test files are added (3 backend, 3 frontend) covering round-trip serialization, validation edge cases, and migration/state idempotency, collectively defining 30 or more distinct properties.
- **SC-004**: Accessibility audits run in 4 additional E2E spec files (auth, board, chat, settings), and all audited pages report zero WCAG 2.1 AA violations.
- **SC-005**: The full CI pipeline (all 9 jobs) passes with the updated coverage thresholds and new tests — no new `continue-on-error` exceptions are introduced.
- **SC-006**: Developer confidence improves: the updated thresholds prevent future PRs from merging if they reduce coverage below the new baselines.
- **SC-007**: All 4 workstreams (backend coverage, frontend coverage, property tests, a11y integration) can be developed, tested, and merged independently without cross-workstream dependencies.

### Assumptions

- All ~30 backend module groups already have at least one corresponding test file (confirmed by research). The work is deepening coverage within existing files, not creating new file skeletons.
- The ~69 untested frontend components can be rendered in isolation using the existing test utility wrapper (`@/test/test-utils`) that provides `OnboardingProvider` and `TooltipProvider`.
- Property-based testing frameworks (Hypothesis 6.131+ for backend, @fast-check/vitest 0.4 for frontend) are already installed and configured with appropriate CI/dev profiles.
- @axe-core/playwright 4.10.1 is already installed and the integration pattern is established in 2 existing E2E spec files (`ui.spec.ts`, `protected-routes.spec.ts`).
- Accessibility violations found during integration are triaged and addressed — critical violations are fixed in this phase, non-critical violations are documented for follow-up.
- No runtime code changes are required — this is a test-only workstream that adds and modifies test files and configuration thresholds.
- The existing CI pipeline structure (9 jobs, blocking/non-blocking configuration) is sufficient and does not need modification.
