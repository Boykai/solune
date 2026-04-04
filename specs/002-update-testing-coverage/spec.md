# Feature Specification: Update Testing Coverage

**Feature Branch**: `002-update-testing-coverage`
**Created**: 2026-04-04
**Status**: Draft
**Input**: User description: "Update testing coverage as much as possible. Start with most impactful branches/files/functions. Use modern best practices. e2e tests are important for overall UX. Resolve any codebase discovered bugs/issues as test coverage increases. Remove stale/old/bad tests."

## User Scenarios & Testing

### User Story 1 - Increase Backend Unit and Branch Coverage (Priority: P1)

As a maintainer, I want backend test coverage to increase significantly by targeting the most impactful files and branches first, so that critical business logic across all 40+ service modules is well-protected against regressions.

**Why this priority**: The backend contains the core business logic (services, API routes, models) that drives the entire application. Gaps in backend coverage directly translate to undetected regressions in features like copilot polling, GitHub Projects integration, pipeline orchestration, and agent management. The current 75% coverage threshold leaves significant risk in complex service modules.

**Independent Test**: Can be fully tested by running `cd solune/backend && uv run pytest --cov=src --cov-report=json` and verifying that overall line coverage exceeds 85% and branch coverage exceeds 78%. Each newly covered file can be validated independently by running pytest against individual test modules.

**Acceptance Scenarios**:

1. **Given** the backend has service modules with below-average line coverage, **When** new unit tests are written for the top 15 files by missing lines, **Then** each targeted file's line coverage increases by at least 15 percentage points.
2. **Given** the backend has files with low branch coverage, **When** new branch-path tests are added for the top 10 files by missing branches, **Then** branch coverage for each targeted file increases by at least 10 percentage points.
3. **Given** the backend coverage threshold is configured at 75%, **When** the threshold is raised to 85%, **Then** CI passes with the new threshold without skipping or ignoring any source files.
4. **Given** a complex service module with multiple code paths (e.g., copilot polling, pipeline orchestration), **When** tests cover both success and failure paths, **Then** all conditional branches within those modules are exercised.

---

### User Story 2 - Increase Frontend Unit and Component Coverage (Priority: P1)

As a maintainer, I want frontend vitest coverage thresholds raised from the current 50/44/41/50 (statements/branches/functions/lines) to at least 60/55/52/60, so that UI components, hooks, and business logic have stronger regression protection.

**Why this priority**: The frontend has 186+ test files but relatively low coverage thresholds. With 60+ custom hooks and 17+ component directories driving the user experience, insufficient coverage risks shipping broken UI flows for board management, chat, pipeline monitoring, and agent creation.

**Independent Test**: Can be fully tested by running `cd solune/frontend && npm run test:coverage` and verifying the new thresholds pass. Individual hook and component test files can be validated by running vitest against specific test files.

**Acceptance Scenarios**:

1. **Given** the vitest.config.ts coverage thresholds are set to 50/44/41/50, **When** the thresholds are raised to 60/55/52/60, **Then** CI passes with the new thresholds.
2. **Given** hooks and service modules with low coverage, **When** new tests are written for uncovered functions and branches, **Then** the coverage for those modules meets or exceeds the new thresholds.
3. **Given** a component renders conditional UI based on state, **When** tests cover all conditional rendering paths, **Then** branch coverage for that component reaches at least 55%.

---

### User Story 3 - Meaningful E2E Tests for Core UX Flows (Priority: P2)

As a user, I want critical UX flows validated end-to-end with modern Playwright tests, so that overall application quality is maintained across deployments and I can trust that core workflows function correctly.

**Why this priority**: E2E tests validate the full user journey across both frontend and backend, catching integration issues that unit tests miss. The existing 29 Playwright spec files cover many flows, but some may be stale or incomplete. Core flows like authentication, chat interaction, board navigation, pipeline monitoring, and agent creation must be thoroughly validated.

**Independent Test**: Can be fully tested by running `cd solune/frontend && npm run test:e2e` against a running application and verifying all spec files pass. Each e2e spec file can be run independently to validate a specific flow.

**Acceptance Scenarios**:

1. **Given** existing e2e spec files, **When** reviewed for correctness, **Then** stale or broken specs are updated or removed.
2. **Given** core user flows (authentication, chat, board, pipeline, agent creation, settings), **When** e2e tests run, **Then** each flow is validated from start to finish including expected navigation, data display, and user interaction.
3. **Given** a new e2e test for a core flow, **When** run in the Playwright CI configuration (chromium + firefox projects), **Then** the test passes in both browser environments.
4. **Given** responsive design is part of the UX, **When** e2e tests run at different viewport sizes, **Then** responsive behavior is validated for critical pages.

---

### User Story 4 - Remove Stale, Outdated, and Low-Quality Tests (Priority: P2)

As a maintainer, I want outdated, redundant, or broken tests removed from both backend and frontend test suites, so that the test suite remains fast, reliable, and maintainable.

**Why this priority**: Stale tests slow down CI, create false confidence in coverage numbers, and increase maintenance burden. Tests with no meaningful assertions, tests for removed features, and duplicate tests waste developer time and obscure real coverage gaps.

**Independent Test**: Can be validated by identifying candidate tests for removal, removing them, and confirming that CI still passes and coverage metrics do not regress significantly (less than 2% overall drop per removed test batch).

**Acceptance Scenarios**:

1. **Given** the test suite, **When** analyzed for quality, **Then** tests with no assertions, empty test bodies, or testing removed features are identified and cataloged.
2. **Given** identified stale tests, **When** removed, **Then** CI continues to pass and overall coverage does not regress by more than 2%.
3. **Given** duplicate tests covering the same functionality, **When** consolidated into single well-written tests, **Then** test execution time decreases while maintaining the same coverage.
4. **Given** tests that rely on implementation details rather than behavior, **When** refactored to test behavior, **Then** they become resilient to code refactoring.

---

### User Story 5 - Discover and Fix Bugs During Coverage Increase (Priority: P3)

As a developer, I want bugs discovered while writing new tests to be documented and resolved, so that increasing coverage also directly improves code quality.

**Why this priority**: Writing tests for previously untested code paths frequently reveals latent bugs such as unhandled edge cases, incorrect error handling, or race conditions. Fixing these bugs alongside the test that exposed them ensures higher code quality and prevents regression.

**Independent Test**: Can be validated by writing a test that exposes the bug (test initially fails), applying the fix (test passes), and confirming all other tests continue to pass.

**Acceptance Scenarios**:

1. **Given** new tests that reveal unexpected behavior, **When** the root cause is identified, **Then** a fix is applied alongside the test that exposed it.
2. **Given** a bug fix is applied, **When** the full test suite runs, **Then** no existing tests break as a result of the fix.
3. **Given** a discovered bug, **When** documented, **Then** the bug description, affected module, and fix are recorded in the commit message or pull request description.

---

### Edge Cases

- What happens when raising coverage thresholds causes a previously passing CI to fail? Tests must be added before thresholds are raised.
- How should tests handle flaky behavior in async operations? Use deterministic mocking (freezegun for time, AsyncMock for async calls) and appropriate timeouts.
- What happens when removing stale tests causes coverage to drop below thresholds? Coverage thresholds should only be raised after sufficient new tests compensate for any removed tests.
- How should e2e tests handle authentication state? Use Playwright's storageState for session persistence and the existing auth-setup project configuration.
- What happens when a discovered bug requires changes outside the scope of this feature? Document the bug and create a separate issue; do not expand scope beyond testing coverage.

## Requirements

### Functional Requirements

- **FR-001**: The project MUST raise backend coverage from the current 75% threshold to at least 85% overall line coverage and 78% branch coverage.
- **FR-002**: The project MUST raise frontend vitest coverage thresholds from 50/44/41/50 to at least 60/55/52/60 (statements/branches/functions/lines).
- **FR-003**: The project MUST add new backend unit tests targeting the top 15 files by missing lines and top 10 files by missing branches, prioritizing service modules (copilot polling, GitHub Projects, pipeline orchestration, workflow orchestrator).
- **FR-004**: The project MUST add new frontend unit and component tests targeting hooks, services, and components with below-average coverage.
- **FR-005**: The project MUST review all existing e2e Playwright spec files and update or remove stale, broken, or redundant ones.
- **FR-006**: The project MUST ensure e2e tests cover core UX flows: authentication, chat interaction, board navigation, pipeline monitoring, agent creation, and settings management.
- **FR-007**: The project MUST identify and remove tests that have no assertions, empty test bodies, test removed features, or duplicate existing coverage.
- **FR-008**: The project MUST fix any bugs discovered during test writing, with the fix committed alongside the test that exposed it.
- **FR-009**: All new tests MUST follow existing project conventions: pytest with async support and conftest fixtures for backend; vitest with Testing Library and factory patterns for frontend; Playwright with fixture-based setup for e2e.
- **FR-010**: New tests MUST NOT introduce flaky behavior. Async tests must use deterministic mocking, and e2e tests must have appropriate retry and timeout configurations.
- **FR-011**: Coverage thresholds MUST only be raised after sufficient tests are added to meet the new thresholds; thresholds must never be raised before tests are in place.

### Key Entities

- **Test Suite**: The collection of all tests across backend (223 files) and frontend (186 unit + 29 e2e files), organized by type (unit, integration, e2e, property, fuzz, chaos, concurrency).
- **Coverage Report**: Generated metrics from pytest-cov (backend) and vitest/v8 (frontend) that measure line, branch, statement, and function coverage against configured thresholds.
- **Coverage Threshold**: Configured minimum acceptable coverage percentages in pyproject.toml (backend) and vitest.config.ts (frontend) that must be met for CI to pass.
- **E2E Spec**: A Playwright test file that validates a complete user journey through the application across both frontend and backend systems.
- **Stale Test**: A test that provides no value due to missing assertions, testing removed features, duplicating other tests, or being permanently broken.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Backend overall line coverage reaches at least 85%, up from the current 75% threshold, as measured by the project's coverage reporting tool.
- **SC-002**: Backend branch coverage reaches at least 78%, with branch coverage enabled, as measured by the project's coverage reporting tool.
- **SC-003**: Frontend coverage thresholds are raised to at least 60% statements, 55% branches, 52% functions, and 60% lines, and CI passes with these new thresholds.
- **SC-004**: At least 80% of the backend's top 15 files by missing lines receive new tests that increase their individual file coverage by at least 15 percentage points.
- **SC-005**: All 29 existing frontend e2e spec files are reviewed, with stale or broken specs either updated or removed, resulting in a 100% pass rate across chromium and firefox projects.
- **SC-006**: Core UX flows (authentication, chat, board, pipeline, agent creation, settings) each have at least one comprehensive e2e test that validates the complete user journey.
- **SC-007**: At least 10 stale or low-quality tests are identified and removed or consolidated without overall coverage regressing by more than 2%.
- **SC-008**: All bugs discovered during test writing are fixed, with each bug fix accompanied by a test that validates the fix.
- **SC-009**: The full test suite (backend + frontend unit + e2e) completes successfully in CI after all changes are applied.
- **SC-010**: New tests follow the project's established conventions and use existing test utilities, fixtures, and factories rather than introducing new patterns.

## Assumptions

- The current backend coverage.json (generated 2026-03-30) is a reasonable baseline for identifying coverage gaps, though actual current coverage will be measured fresh during implementation.
- The existing test infrastructure (pytest, vitest, Playwright) is sufficient for the coverage improvements and no new testing frameworks need to be introduced.
- Backend service modules (copilot_polling with 11 sub-modules, github_projects with 11 sub-modules) represent the highest-impact targets for backend coverage improvement due to their complexity and critical business function.
- Frontend hooks (60+ files) and components (17+ directories) represent the highest-impact targets for frontend coverage improvement.
- E2E tests can be validated against a local development environment using the existing Playwright configuration (baseURL: localhost:5173).
- The definition of "stale test" includes: tests with no assertions, tests for features that no longer exist, tests that are permanently skipped, and tests that duplicate coverage of other tests.
- Bug fixes discovered during test writing will be scoped to the module being tested and will not require architectural changes.

## Scope Boundaries

**In Scope**: Backend unit and integration tests, frontend unit and component tests, e2e Playwright tests, test quality improvements (removing stale tests, refactoring brittle tests), coverage threshold increases, bug fixes discovered during testing, updating existing test fixtures and utilities as needed.

**Out of Scope**: Performance testing infrastructure changes, mutation testing threshold changes, CI pipeline architecture changes, introducing new testing frameworks or tools, changes to the Stryker mutation testing configuration, infrastructure or deployment testing beyond what already exists.
