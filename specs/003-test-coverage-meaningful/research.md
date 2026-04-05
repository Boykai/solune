# Research: Increase Test Coverage with Meaningful Tests

**Branch**: `copilot/increase-test-coverage-backend` | **Date**: 2026-04-05

## Research Tasks

### R1. Backend regression-test expansion strategy

**Decision**: Extend the existing backend unit suites in `/home/runner/work/solune/solune/solune/backend/tests/unit` for `chat`, `board`, `apps`, `settings`, `onboarding`, `pipeline_estimate`, `completion_providers`, and `utils`, and create only the missing `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_templates.py`.

**Rationale**: The repository already has established async API and service test patterns, plus reusable fixtures in `/home/runner/work/solune/solune/solune/backend/tests/conftest.py`. Expanding those files keeps setup DRY, preserves local conventions, and makes the new coverage read as regression protection instead of a second competing test harness.

**Alternatives considered**:
- Creating parallel “coverage only” files for every module — rejected because it would fragment existing behavioral coverage.
- Adding integration-style backend suites — rejected because the spec explicitly keeps scope at unit/behavioral tests.

### R2. Backend bug-fix validation pattern

**Decision**: Represent each backend bug fix as a failing-then-passing behavioral contract tied to the API or service seam nearest the user-visible failure, with the code fix made inline in the same change set.

**Rationale**: The spec requires each bug to be covered by a regression test and forbids separating bug fixes from the tests that expose them. Exercising the closest public seam keeps the tests robust during refactors and avoids fragile assertions against private implementation details.

**Alternatives considered**:
- Deep unit tests against internal helpers only — rejected because they would miss the externally visible failure mode.
- Fixing bugs first and adding tests afterward — rejected because it weakens the regression proof required by the specification.

### R3. Frontend behavioral test strategy

**Decision**: Use colocated Vitest + Testing Library suites under `/home/runner/work/solune/solune/solune/frontend/src`, relying on `/home/runner/work/solune/solune/solune/frontend/src/test/setup.ts`, `/home/runner/work/solune/solune/solune/frontend/src/test/test-utils.tsx`, and existing mock-hook patterns.

**Rationale**: The current frontend already favors behavior-driven tests with `userEvent`, accessible queries, mocked hooks, and targeted async waits. Matching that style is the most reliable way to cover complex component behavior like search, undo, keyboard flow, and state deduplication without introducing snapshot-heavy or implementation-coupled tests.

**Alternatives considered**:
- Snapshot-only component coverage — rejected because the feature requires meaningful interaction contracts.
- New frontend test utilities or dependencies — rejected because existing setup already supports these scenarios and the spec disallows new test-tool adoption.

### R4. Coverage verification approach

**Decision**: Verify with a two-pass workflow: targeted module/file runs first, then aggregate repository-standard coverage/lint/type-check commands for backend and frontend.

**Rationale**: Targeted runs localize failures quickly and confirm the exact thresholds called out in the spec, while aggregate runs prove that the broader suite remains green and that no regressions were introduced elsewhere. This also matches the repo’s current toolchain (`uv run pytest`, `npm run test:coverage`, `ruff`, `pyright`, `eslint`, and TypeScript checks).

**Alternatives considered**:
- Running only full coverage commands — rejected because it obscures which target module missed its threshold.
- Tracking only line coverage deltas — rejected because the spec also imposes branch and per-module expectations.

### R5. Contract surface for this feature

**Decision**: Capture the externally visible backend HTTP behaviors under test in a single OpenAPI contract at `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/contracts/test-coverage-surfaces.openapi.yaml`, and leave non-HTTP service-level scenarios documented in the plan/data model instead of inventing synthetic APIs.

**Rationale**: Several functional requirements map cleanly to real backend endpoints (`/api/v1/chat/upload`, `/api/v1/settings/*`, `/api/v1/onboarding/state`, `/api/v1/templates`, `/api/v1/apps/import`), while others target internal service behavior (`pipeline_estimate`, `completion_providers`, `utils`). One additive OpenAPI file keeps the design concrete without forcing fake REST endpoints for purely internal logic.

**Alternatives considered**:
- Separate contract files per module — rejected because one feature-scoped API contract is easier to review and maintain.
- Creating pseudo-API contracts for internal utilities — rejected because that would misrepresent the actual system boundary.

### R6. Remaining technical-context clarifications

**Decision**: Treat deterministic execution, shallow mocking, and no-new-dependencies as explicit planning constraints rather than unresolved questions.

**Rationale**: Repository inspection resolved the only meaningful unknowns: language versions, test runners, code layout, and the current fixture strategy are all already explicit in the codebase. No `NEEDS CLARIFICATION` items remain after this research phase.

**Alternatives considered**:
- Deferring flakiness-handling details to implementation — rejected because the spec already flags async determinism as a core edge case.
