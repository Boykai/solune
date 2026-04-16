# Feature Specification: Remove Lint/Test Ignores & Fix Discovered Bugs

**Feature Branch**: `003-remove-lint-ignores`  
**Created**: 2026-04-16  
**Status**: Draft  
**Input**: User description: "Systematically remove lint, type-check, test-skip, coverage, and mutation ignores across the Solune repo. Keep only ignores that are truly framework/tooling-required, and replace any remaining ones with a concise reason justification. Any bug surfaced by removal is fixed inline in the same PR unless the fix is genuinely large."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Backend Suppression Cleanup (Priority: P1)

As a contributor working on the backend, I want all non-essential lint, type-check, and coverage suppressions removed so that static analysis tools catch real bugs and the codebase maintains a high quality bar without hidden blind spots.

**Why this priority**: The backend contains a Bandit B608 suppression that may be masking real SQL injection vulnerabilities. Type-ignore and noqa markers hide potential type errors and code quality issues. Removing these first addresses the highest-risk area (security) and establishes the pattern for the rest of the cleanup.

**Independent Test**: Can be fully tested by running the backend linting, type-checking, and test suites with the suppressions removed and verifying all checks pass with zero new suppressions that lack a reason justification.

**Acceptance Scenarios**:

1. **Given** the backend codebase with the Bandit B608 global exclusion, **When** the exclusion is removed, **Then** all previously suppressed SQL paths are audited and use parameterized queries, and `bandit -r src` passes cleanly.
2. **Given** backend source files containing `# type: ignore` markers, **When** the markers are removed, **Then** all affected call sites use properly typed models, casts, or refactored fixtures, and `pyright` passes without errors.
3. **Given** backend source files containing `# noqa` markers, **When** each marker is evaluated, **Then** non-essential markers (E402, PTH118/PTH119, F401) are removed by fixing the underlying code, and any retained marker (B008 for dependency injection) includes a concise `reason:` justification.
4. **Given** backend source files containing `# pragma: no cover` markers, **When** the markers are removed, **Then** either new tests cover the previously excluded branches or dead code is deleted.
5. **Given** a skipped test in `test_run_mutmut_shard.py`, **When** the skip condition is replaced, **Then** the test runs successfully via a fixture or test setup that provides the required environment.
6. **Given** the backend configuration files, **When** line-length ignores and type-checking thresholds are tightened, **Then** all backend checks pass at the stricter settings.

---

### User Story 2 - Frontend Suppression Cleanup (Priority: P1)

As a contributor working on the frontend, I want all non-essential ESLint, TypeScript, and mutation-testing suppressions removed so that the linter and type checker catch stale-closure bugs, accessibility violations, and type safety issues before they reach production.

**Why this priority**: The 5 `react-hooks/exhaustive-deps` suppressions are the most likely source of stale-state bugs in the application. Removing them alongside `@typescript-eslint/no-explicit-any`, accessibility suppressions, and mutation-testing ignores delivers the highest quality improvement for the frontend.

**Independent Test**: Can be fully tested by running the frontend linting (with zero warnings), type-checking, test suite with coverage, and mutation testing with `ignoreStatic = false`, and verifying all checks pass.

**Acceptance Scenarios**:

1. **Given** frontend components with `react-hooks/exhaustive-deps` suppressions, **When** the suppressions are removed, **Then** the affected hooks use stable callbacks or hoisted stable values, and the lint rule passes without suppression.
2. **Given** frontend files with `@typescript-eslint/no-explicit-any` suppressions, **When** the suppressions are removed, **Then** the affected code uses proper type annotations, and the lint rule passes.
3. **Given** the `useChatPanels.ts` hook with `react-hooks/set-state-in-effect` suppression, **When** the suppression is removed, **Then** the hook is refactored to avoid setting state inside an effect, and the rule passes.
4. **Given** frontend files with `jsx-a11y` suppressions for autofocus and click handlers, **When** the suppressions are removed, **Then** autofocus cases use imperative focus handling or a focus-trap pattern, and click-on-non-interactive cases use semantic buttons or keyboard handlers.
5. **Given** the test setup file with `@ts-expect-error` directives, **When** the directives are removed, **Then** proper ambient declarations or typed shims replace the suppressed type errors.
6. **Given** the e2e fixtures file with a file-wide `react-hooks/rules-of-hooks` disable, **When** the disable is removed, **Then** helper functions are renamed so the lint rule no longer misfires.
7. **Given** the Stryker mutation testing configuration with `ignoreStatic = true`, **When** the setting is changed to `false`, **Then** any resulting mutation gaps are closed by adding or improving tests.
8. **Given** the test TypeScript configuration with `noUnusedLocals` and `noUnusedParameters` disabled, **When** both settings are re-enabled, **Then** all unused locals and parameters are removed or prefixed, and type checking passes.
9. **Given** the ESLint configuration with rules set to `warn` or `off`, **When** the rules are audited and appropriate ones promoted to `error`, **Then** all resulting lint issues are fixed and the lint passes with zero warnings.

---

### User Story 3 - E2E Test Skip Cleanup (Priority: P2)

As a QA contributor, I want the dynamic `test.skip()` calls in E2E tests replaced with structured environment-based test wiring so that tests are either explicitly included or excluded by configuration rather than hidden by runtime skip logic.

**Why this priority**: Dynamic test skips obscure which tests actually run in each environment. Replacing them with tag-driven or project-based configuration makes the test matrix transparent and auditable, reducing the risk of silently skipped regressions.

**Independent Test**: Can be tested by running the Playwright test suite in both the default and CI environments and verifying that the correct tests run based on configuration rather than runtime skip checks.

**Acceptance Scenarios**:

1. **Given** integration and performance spec files with dynamic `test.skip()` calls, **When** the skips are replaced with tag-driven project setup, **Then** the tests are wired to run or not run based on explicit environment configuration.
2. **Given** the Playwright configuration with `forbidOnly` and `testIgnore` for `save-auth-state.ts`, **When** the configuration is reviewed, **Then** the reason for the ignore is documented clearly in a comment.

---

### User Story 4 - Infrastructure Suppression Cleanup (Priority: P2)

As an infrastructure contributor, I want the Bicep secret-output suppressions reviewed and minimized so that secrets are not unnecessarily exposed in deployment outputs, and any remaining suppressions are justified.

**Why this priority**: Secret output suppressions may mask real security concerns where sensitive values are exposed in deployment logs. Reviewing and refactoring these outputs reduces the attack surface of the deployment pipeline.

**Independent Test**: Can be tested by running `az bicep build` on all infrastructure modules and verifying that outputs either use secure references or carry documented justification for the suppression.

**Acceptance Scenarios**:

1. **Given** Bicep modules with `#disable-next-line outputs-should-not-contain-secrets` suppressions, **When** each output is reviewed, **Then** outputs that can safely move behind secure references are refactored, and only truly required suppressions remain with documented justification.
2. **Given** the refactored infrastructure modules, **When** `az bicep build` is run, **Then** all modules compile without errors.

---

### User Story 5 - Suppression Policy and CI Guard (Priority: P3)

As a team lead, I want a CI guard that prevents new suppressions from being introduced without a reason, and a documented policy explaining the suppression standards, so that the cleanup is sustained over time.

**Why this priority**: Without enforcement, suppressions will accumulate again over time. A CI guard and policy document ensure ongoing compliance. This is lower priority because it is a governance concern rather than a direct quality improvement.

**Independent Test**: Can be tested by introducing a suppression without a `reason:` marker in a test branch and verifying the CI guard fails the build.

**Acceptance Scenarios**:

1. **Given** the repository with all suppressions cleaned up, **When** a contributor adds a new suppression without a `reason:` justification, **Then** the CI pipeline fails and reports which suppression is missing a reason.
2. **Given** the repository documentation, **When** a contributor looks for suppression guidelines, **Then** a policy note explains that all remaining suppressions must carry a reason.
3. **Given** the `.gitignore` and `.prettierignore` files, **When** they are reviewed, **Then** stale entries are removed and no conflicting `.eslintignore` or `.ruffignore` files exist.

---

### User Story 6 - Baseline Capture and Verification (Priority: P3)

As a project maintainer, I want a recorded baseline of the current green state (all checks passing) before any changes begin, and a final verification that all checks still pass after the cleanup, so that regressions are immediately detectable.

**Why this priority**: The baseline provides a safety net. If any cleanup step introduces a regression, the recorded baseline makes it easy to identify what broke. This is lower priority because it is a process step, not a deliverable.

**Independent Test**: Can be tested by comparing the post-cleanup check results against the recorded baseline and verifying all results are equal or improved.

**Acceptance Scenarios**:

1. **Given** the repository before any changes, **When** the baseline is captured, **Then** the results of all linting, type-checking, testing, coverage, and mutation checks are recorded.
2. **Given** the repository after all cleanup changes, **When** the full verification suite is run, **Then** all checks pass and results are equal to or better than the baseline.

---

### Edge Cases

- What happens when removing a suppression reveals a bug that requires a large fix? The bug is documented as a follow-up issue and the suppression is temporarily retained with a `reason:` referencing the issue, rather than blocking the entire cleanup.
- What happens when a Bandit B608 removal reveals a SQL injection path in production code? The path is parameterized immediately as a security fix in the same change set, with elevated review priority.
- What happens when re-enabling `noUnusedLocals` flags variables that are used only in type positions? Unused-in-value-position variables are prefixed with an underscore or restructured to satisfy the compiler without losing type information.
- What happens when turning off `ignoreStatic` in Stryker produces hundreds of surviving mutants? The most impactful mutation gaps are closed first, and a threshold is set for acceptable surviving mutants with documentation of the remaining gaps.
- What happens when a `react-hooks/exhaustive-deps` fix changes runtime behavior? The change is accompanied by a test that verifies the corrected behavior, and the old stale-closure behavior is documented as a bug fix.
- What happens when the CI suppression guard has false positives on legitimate patterns (e.g., code comments mentioning "ignore")? The guard uses precise pattern matching against known suppression syntaxes rather than broad keyword matching.

## Requirements *(mandatory)*

### Functional Requirements

#### Phase 0 — Baseline

- **FR-001**: The team MUST capture the current passing state of all backend checks (linting, type-checking, tests with coverage, security scanning) before making changes.
- **FR-002**: The team MUST capture the current passing state of all frontend checks (linting, type-checking, tests with coverage, mutation testing) before making changes.
- **FR-003**: The team MUST capture the current passing state of E2E tests and infrastructure builds before making changes.
- **FR-004**: All baseline results MUST be recorded so that post-cleanup results can be compared against them.

#### Phase 1 — Backend

- **FR-005**: The Bandit B608 global exclusion MUST be removed from backend configuration, and all flagged SQL paths MUST be audited and parameterized.
- **FR-006**: All `# type: ignore` markers in backend service and test files MUST be removed and replaced with properly typed code (typed models, casts, or fixture refactors).
- **FR-007**: The `# noqa: B008` markers for dependency injection MUST be retained but MUST include a `reason:` justification.
- **FR-008**: The `# noqa: E402` markers MUST be removed by reordering or restructuring imports.
- **FR-009**: The `# noqa: PTH118/PTH119` markers MUST be removed by replacing `os.path` usage with `pathlib` equivalents.
- **FR-010**: The `# noqa: F401` re-export markers MUST be removed by defining explicit `__all__` lists.
- **FR-011**: All `# pragma: no cover` markers MUST be removed by either adding tests for the uncovered branches or deleting dead code.
- **FR-012**: The `@pytest.mark.skipif(...)` in the mutation testing shard test MUST be replaced with a fixture or test setup that allows the test to run.
- **FR-013**: The backend line-length exclusion (E501) MUST be removed from the linting configuration.
- **FR-014**: Backend type-checking strictness MUST be increased by raising `reportMissingImports` to error level.
- **FR-015**: Coverage exclusion patterns in backend configuration MUST be reduced to only genuinely necessary cases.

#### Phase 2 — Frontend

- **FR-016**: All 5 `react-hooks/exhaustive-deps` suppressions MUST be removed by using stable callbacks or hoisted stable values.
- **FR-017**: Both `@typescript-eslint/no-explicit-any` suppressions MUST be removed by adding proper type annotations.
- **FR-018**: The `react-hooks/set-state-in-effect` suppression MUST be removed by refactoring the hook to avoid setting state inside an effect.
- **FR-019**: All `jsx-a11y` suppressions MUST be removed by improving element semantics (imperative focus handling, focus-trap patterns, semantic buttons, keyboard handlers).
- **FR-020**: Both `@ts-expect-error` directives in the test setup MUST be replaced with proper ambient declarations or typed shims.
- **FR-021**: The file-wide `react-hooks/rules-of-hooks` disable in the e2e fixtures MUST be removed by renaming helper functions so the rule no longer misfires.
- **FR-022**: The Stryker `ignoreStatic` setting MUST be changed to `false`, and any resulting mutation gaps MUST be closed.
- **FR-023**: The `noUnusedLocals` and `noUnusedParameters` settings MUST be re-enabled in the test TypeScript configuration, and all resulting issues MUST be fixed.
- **FR-024**: The ESLint configuration MUST be audited for rules that should be promoted from `warn` or `off` to `error`, and all resulting lint issues MUST be fixed.

#### Phase 3 — E2E

- **FR-025**: All 6 dynamic `test.skip()` calls in E2E specs MUST be replaced with tag-driven project setup or explicit environment-based test wiring.
- **FR-026**: The `forbidOnly` and `testIgnore` settings for `save-auth-state.ts` MUST be retained with a clear documented reason.

#### Phase 4 — Infrastructure

- **FR-027**: All 3 `#disable-next-line outputs-should-not-contain-secrets` suppressions in Bicep modules MUST be reviewed.
- **FR-028**: Outputs that can safely move behind secure references MUST be refactored.
- **FR-029**: Only suppressions that are truly required by downstream deployment behavior MUST be retained, each with documented justification.

#### Phase 5 — Policy and Enforcement

- **FR-030**: The `.gitignore` and `.prettierignore` files MUST be reviewed and stale entries removed.
- **FR-031**: There MUST be no conflicting `.eslintignore` or `.ruffignore` files that override current configuration.
- **FR-032**: A policy note MUST be added to existing documentation explaining that any remaining suppression must carry a reason.
- **FR-033**: A CI guard MUST be added that fails the build when a new suppression is introduced without a `reason:` marker.

#### Cross-Cutting

- **FR-034**: Any bug discovered during suppression removal MUST be fixed in the same change set, unless the fix is genuinely large, in which case a follow-up issue is created and the suppression is temporarily retained with a `reason:` referencing the issue.
- **FR-035**: Every remaining suppression after cleanup MUST include a concise `reason:` justification explaining why it cannot be removed.

### Key Entities

- **Suppression**: A directive in source code or configuration that tells a static analysis tool to skip a specific check. Examples include `# noqa`, `# type: ignore`, `// eslint-disable`, `@ts-expect-error`, `# pragma: no cover`, `@pytest.mark.skipif`, `#disable-next-line`, and tool-level exclusion lists.
- **Baseline**: A recorded snapshot of all check results (lint, type-check, test, coverage, mutation, security scan, infrastructure build) taken before changes begin, used as a comparison reference for verifying no regressions.
- **Suppression Policy**: A documented standard requiring all remaining suppressions to carry a `reason:` justification, enforced by CI automation.
- **CI Guard**: An automated check in the continuous integration pipeline that scans for new suppression directives and fails the build if any lack a `reason:` marker.

## Assumptions

- The repository is currently in a green state (all checks passing) and can serve as a valid baseline.
- Bandit B608 removal may reveal real SQL parameterization issues that are fixable within the scope of this feature.
- The 5 `react-hooks/exhaustive-deps` fixes will change runtime behavior in a way that corrects stale-closure bugs rather than introducing new ones.
- Turning Stryker `ignoreStatic` off will produce a manageable number of surviving mutants that can be addressed incrementally.
- Bicep secret output refactoring is bounded to the 3 identified modules and does not require changes to downstream deployment pipelines.
- The `reportMissingTypeStubs = true` setting in Pyright may require adding type stub packages; if the fallout is too large, this specific tightening may be deferred with documentation.
- The CI suppression guard can use pattern matching against known suppression syntaxes without significant false-positive rates.
- Renaming e2e fixture helpers to avoid the `rules-of-hooks` lint rule misfire does not break any existing test imports.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The total number of suppressions across the repository is reduced by at least 80% compared to the baseline count.
- **SC-002**: Every remaining suppression includes a `reason:` justification — 100% compliance.
- **SC-003**: All backend checks (linting, type-checking, tests with coverage, security scanning) pass at equal or stricter settings compared to the baseline.
- **SC-004**: All frontend checks (linting with zero warnings, type-checking, tests with coverage) pass at equal or stricter settings compared to the baseline.
- **SC-005**: Frontend mutation testing passes with `ignoreStatic = false` and the surviving mutant count is equal to or lower than the baseline.
- **SC-006**: All E2E tests that were previously dynamically skipped either run successfully via configuration-based wiring or are explicitly excluded by project/tag setup.
- **SC-007**: All infrastructure modules compile without errors after Bicep suppression review and refactoring.
- **SC-008**: The CI suppression guard correctly blocks new suppressions without a `reason:` marker, as verified by a test commit.
- **SC-009**: No user-facing functionality is broken by the cleanup — all existing tests continue to pass.
- **SC-010**: Any bug discovered and fixed during suppression removal is accompanied by a test that prevents regression.
