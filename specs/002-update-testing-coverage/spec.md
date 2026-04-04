# Feature Specification: Update Testing Coverage

**Branch**: `copilot/update-testing-coverage` | **Date**: 2026-04-04 | **Priority**: P1

## Summary

Improve testing coverage across the Solune backend and frontend codebases by targeting the most impactful files and branches first, using modern best practices. Include meaningful e2e tests for overall UX validation. Discover and resolve codebase bugs as coverage increases. Remove stale, outdated, or low-quality tests.

## User Stories

### US1 — Increase Backend Line and Branch Coverage [P1]

**As a** maintainer, **I want** backend test coverage to increase from 79% line / 70% branch to ≥85% line / ≥78% branch, **so that** critical business logic is well-protected against regressions.

**Acceptance Criteria (Given-When-Then)**:
- Given the top 15 backend files by missing lines, when new tests are written, then each file's line coverage should increase by ≥15 percentage points.
- Given the top 10 files by missing branches, when new branch-path tests are added, then branch coverage should increase by ≥10 percentage points.

### US2 — Increase Frontend Coverage Thresholds [P1]

**As a** maintainer, **I want** frontend vitest coverage thresholds raised from 50/44/41/50 to ≥60/55/52/60 (statements/branches/functions/lines), **so that** UI components and hooks have stronger regression protection.

**Acceptance Criteria**:
- Given the vitest.config.ts thresholds, when updated, then CI passes with the new thresholds.
- Given hooks and services with low coverage, when new tests are written, then they meet or exceed the new thresholds.

### US3 — Meaningful E2E Tests for Core UX Flows [P2]

**As a** user, **I want** critical UX flows validated end-to-end, **so that** overall application quality is maintained across deployments.

**Acceptance Criteria**:
- Given existing e2e specs, when reviewed, then stale/broken specs are removed or updated.
- Given core flows (auth, chat, pipeline, board, agent creation), when e2e tests run, then they validate the complete user journey.

### US4 — Remove Stale/Bad Tests [P2]

**As a** maintainer, **I want** outdated, redundant, or broken tests removed, **so that** the test suite remains fast, reliable, and maintainable.

**Acceptance Criteria**:
- Given the test suite, when analyzed, then tests with no assertions, duplicate coverage, or testing removed features are identified.
- Given identified stale tests, when removed, then CI continues to pass and coverage does not regress significantly.

### US5 — Discover and Fix Bugs During Coverage Increase [P3]

**As a** developer, **I want** bugs discovered during test-writing to be resolved, **so that** increasing coverage also improves code quality.

**Acceptance Criteria**:
- Given new tests that reveal bugs, when the bug is identified, then a fix is applied alongside the test.

## Scope Boundaries

**In Scope**: Backend unit/integration tests, frontend unit/component tests, e2e Playwright tests, test quality improvements, coverage threshold increases, bug fixes discovered during testing.

**Out of Scope**: Performance testing infrastructure changes, mutation testing baseline changes, CI pipeline architecture changes, new testing frameworks.
