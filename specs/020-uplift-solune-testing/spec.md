# Feature Specification: Uplift Solune Testing — Remove Skips, Fix Bugs, Apply Modern Best Practices

**Feature Branch**: `020-uplift-solune-testing`
**Created**: 2026-04-08
**Status**: Draft
**Input**: Parent issue #1149 — Uplift Solune Testing: Remove Skips, Fix Bugs, Apply Modern Best Practices

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Remove All Backend Test Skips (Priority: P1)

As a backend developer, I need every skipped test to either pass or be removed, so that the test suite provides honest coverage metrics and CI results are trustworthy.

**Why this priority**: Skipped tests hide bugs and inflate perceived coverage. Resolving them first unblocks all downstream quality work.

**Independent Test**: Run `pytest tests/ -v` and confirm zero `SKIPPED` results from `pytest.mark.skip` or `pytest.mark.skipif` (conditional `pytest.skip()` for missing infrastructure is acceptable).

**Acceptance Scenarios**:

1. **Given** test_run_mutmut_shard.py has `@pytest.mark.skipif` for missing CI workflow, **When** the test detects the workflow file in a full clone, **Then** it runs; in a shallow clone it skips gracefully (conditional infrastructure skip — acceptable).
2. **Given** test_import_rules.py has `pytest.skip()` for missing directories, **When** the directories exist, **Then** all architecture tests run; skip is a safety guard only.
3. **Given** test_board_load_time.py and test_custom_agent_assignment.py skip without credentials, **When** credentials are absent, **Then** they skip gracefully (performance/integration marker — acceptable).
4. **Given** no unconditional `@pytest.mark.skip` or `@pytest.mark.xfail` markers remain, **When** CI runs, **Then** all backend tests either pass or skip only due to missing external infrastructure.

---

### User Story 2 — Fix Backend pytest Infrastructure (Priority: P1)

As a backend developer, I need pytest and pytest-asyncio configured with modern best practices so that async tests run reliably without deprecation warnings.

**Independent Test**: Run `pytest tests/ -W error::DeprecationWarning` and confirm zero deprecation-related failures.

**Acceptance Scenarios**:

1. **Given** `asyncio_mode = "auto"` and `asyncio_default_fixture_loop_scope = "function"` in pyproject.toml, **When** pytest runs, **Then** no asyncio configuration warnings appear.
2. **Given** `--cov-fail-under=70` is set in CI, **When** coverage drops below 70%, **Then** CI fails.
3. **Given** filterwarnings is configured, **When** tests run, **Then** only intentional deprecation suppressions are active.

---

### User Story 3 — Fix Frontend Vitest Infrastructure (Priority: P1)

As a frontend developer, I need Vitest configured with proper environment, globals, coverage, and setup files so that tests run reliably and axe matchers are available.

**Independent Test**: Run `npm run test` and confirm zero configuration warnings.

**Acceptance Scenarios**:

1. **Given** `environment = "happy-dom"` and `globals = true` in vitest.config.ts, **When** tests run, **Then** global test functions work without imports.
2. **Given** `coverage.provider = "v8"` with `statements >= 50`, **When** coverage runs, **Then** thresholds are enforced.
3. **Given** setupFiles includes `src/test/setup.ts`, **When** tests run, **Then** jest-dom and jest-axe matchers are available.

---

### User Story 4 — Resolve Frontend Skipped E2E Tests (Priority: P2)

As a frontend developer, I need all E2E test skips to be conditional on infrastructure availability only, so that when the infrastructure is present all tests run.

**Independent Test**: With backend/frontend running and auth state saved, run `npx playwright test` and confirm all tests execute.

**Acceptance Scenarios**:

1. **Given** integration.spec.ts skips when backend is unavailable, **When** backend is running, **Then** all integration tests execute.
2. **Given** project-load-performance.spec.ts skips without auth state or env vars, **When** prerequisites are met, **Then** all perf tests execute.
3. **Given** no unconditional `.skip`, `.todo`, `xit`, or `xdescribe` markers exist, **When** all infrastructure is available, **Then** zero tests are skipped.

---

### User Story 5 — Add Net-New Coverage for Critical Untested Paths (Priority: P2)

As a developer, I need meaningful tests for high-risk code paths that currently have zero coverage, so that regressions in critical functionality are caught before production.

**Independent Test**: Run coverage reports and confirm >=10 percentage-point increase from baseline in targeted modules.

**Acceptance Scenarios**:

1. **Given** resolve_repository() in utils.py has tests, **When** tests run, **Then** cache hit, GraphQL fallback, and error cases are covered.
2. **Given** webhooks.py HMAC validation has tests, **When** tests run, **Then** valid and invalid signatures are tested.
3. **Given** tools/presets.py has tests, **When** tests run, **Then** preset catalog enumeration is verified.
4. **Given** frontend api.ts has tests, **When** tests run, **Then** authenticated requests and retry logic are covered.
5. **Given** at least one axe accessibility assertion exists per page component, **When** tests run, **Then** basic a11y compliance is verified.

---

### User Story 6 — Validate Full Suite and CI Green (Priority: P3)

As a team lead, I need CI to pass end-to-end with zero skip markers and all quality gates met, so that the team has confidence in every merge.

**Independent Test**: Push to CI and confirm all jobs exit 0.

**Acceptance Scenarios**:

1. **Given** backend runs ruff, pyright, pytest with coverage, **When** CI executes, **Then** all checks pass.
2. **Given** frontend runs lint, type-check, test, build, **When** CI executes, **Then** all checks pass.
3. **Given** E2E runs Playwright in Chromium, **When** CI executes, **Then** tests pass (with continue-on-error for infra).
4. **Given** CHANGELOG.md is updated, **When** PR is reviewed, **Then** Fixed entries describe all production bugs resolved.

---

### Edge Cases

- What if a backend skip is for a test that requires live infrastructure (GitHub tokens, running backend)? Conditional `pytest.skip()` inside the test body with clear error messages is acceptable — these are infrastructure guards, not test quality issues.
- What if removing an `@pytest.mark.xfail` reveals a real production bug? Fix the production bug first, then remove the marker.
- What if the frontend useAuth.test.tsx is flaky in parallel mode? Verify with both `--pool=forks` and `--pool=threads` to confirm isolation.
- What if adding axe assertions reveals a11y violations? Fix the violations in the components as part of the coverage step.
- What if coverage thresholds cannot be met? Adjust thresholds to achievable levels while documenting the gap for future work.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All unconditional `@pytest.mark.skip` and `@pytest.mark.xfail` markers MUST be removed from backend tests.
- **FR-002**: All `.skip`, `.todo`, `xit`, `xdescribe` markers MUST be removed from frontend tests (conditional infrastructure skips via `test.skip()` inside test body are acceptable).
- **FR-003**: pytest config MUST use `asyncio_mode = "auto"` and `asyncio_default_fixture_loop_scope = "function"`.
- **FR-004**: CI MUST enforce `--cov-fail-under=70` for backend.
- **FR-005**: Vitest config MUST use `happy-dom` environment, `globals = true`, `v8` coverage provider with `statements >= 50`.
- **FR-006**: Frontend setup file MUST configure jest-dom and jest-axe matchers.
- **FR-007**: Backend tests MUST use `AsyncMock` for coroutines and `httpx.AsyncClient` with `ASGITransport` for endpoint tests.
- **FR-008**: Frontend tests MUST use `userEvent.setup()` instead of `fireEvent` and `screen` queries instead of `container.querySelector`.
- **FR-009**: Net-new tests MUST cover: `resolve_repository()`, HMAC validation, preset catalog, api.ts retry, and at least one axe assertion per page component.
- **FR-010**: CHANGELOG.md MUST include Fixed entries for any production bugs discovered during the uplift.
- **FR-011**: All CI jobs MUST exit 0 with zero remaining unconditional skip markers.

### Key Entities

- **Skip Marker**: A test annotation (`@pytest.mark.skip`, `test.skip()`, etc.) that causes a test to be skipped during execution. The uplift targets unconditional skips for removal and ensures conditional skips have clear justifications.
- **Test Infrastructure**: The configuration, fixtures, setup files, and utilities that support test execution. Includes pytest config, Vitest config, conftest.py fixtures, and test setup files.
- **Coverage Threshold**: Minimum code coverage percentage that CI enforces. Backend: 70% (CI), Frontend: 50% statements.
- **axe Assertion**: An accessibility compliance check using jest-axe that validates DOM output against WCAG standards.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero unconditional `@pytest.mark.skip` or `@pytest.mark.xfail` in backend tests.
- **SC-002**: Zero unconditional `.skip`, `.todo`, `xit`, `xdescribe` in frontend tests.
- **SC-003**: Backend pytest runs with zero asyncio deprecation warnings.
- **SC-004**: Frontend `npm run test` runs with zero configuration warnings.
- **SC-005**: Backend coverage >= 70% in CI.
- **SC-006**: Frontend coverage statements >= 50%.
- **SC-007**: All CI jobs exit 0.
- **SC-008**: Coverage increase >= 10 percentage points in targeted modules.
- **SC-009**: CHANGELOG.md updated with Fixed entries for production bugs.

## Assumptions

- The existing pytest-asyncio config (`asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "function"`) is already correct and does not need changes.
- pytest-randomly is already installed (`>=3.16.0` in dev deps).
- Vitest config already has `globals = true`, `environment = "happy-dom"`, and proper setup files.
- The 8 backend skip markers are all conditional (runtime `pytest.skip()` or `@pytest.mark.skipif`) and appropriate for their context.
- The 6 frontend E2E skip markers are conditional infrastructure guards that are appropriate.
- The spec 019-test-isolation-remediation handles state-leak and isolation concerns; this spec focuses on skip removal, bug fixes, coverage, and best practices.
- Standard performance expectations apply — this feature has no runtime performance impact beyond CI execution time.
