# Feature Specification: Linting Clean Up

**Feature Branch**: `004-linting-cleanup`  
**Created**: 2026-04-02  
**Status**: Draft  
**Input**: User description: "Linting Clean Up"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Test Type-Check Gate Expansion (Priority: P1)

A contributor opens a pull request that introduces a new type error in a backend test file or a frontend test file. Today the CI pipeline does not type-check tests, so the error passes unnoticed and reaches the default branch. After this feature is delivered, the CI pipeline and local pre-commit hook catch the error before merge, and the contributor receives a clear, actionable diagnostic pointing to the offending line.

**Why this priority**: Until tests are included in the type-check gates, suppressions hidden in test code cannot be discovered or removed. Every subsequent cleanup phase depends on this gate being in place first.

**Independent Test**: Can be fully tested by adding a deliberate type error to a backend test file and a frontend test file and verifying that CI and pre-commit both fail with a clear diagnostic. Delivers immediate value by preventing new type regressions in test code.

**Acceptance Scenarios**:

1. **Given** the CI pipeline runs on a pull request, **When** a backend test file contains a type error, **Then** the backend test type-check step fails and reports the file, line, and error description.
2. **Given** the CI pipeline runs on a pull request, **When** a frontend test file contains a type error, **Then** the frontend test type-check step fails and reports the file, line, and error description.
3. **Given** a contributor runs the local pre-commit hook, **When** staged changes include a type error in a test file, **Then** the hook fails before the commit is created.
4. **Given** all test files are type-correct, **When** CI runs the new test type-check steps, **Then** both steps pass without error.

---

### User Story 2 - Backend Source Suppression Removal (Priority: P2)

A maintainer reviews backend source code and finds that inline type-suppression comments (`# type: ignore`) are replaced with properly typed constructs. The code is easier to understand, refactor, and extend because the type checker validates every expression. Bugs that were previously hidden behind suppressed diagnostics are exposed and fixed in the same pass.

**Why this priority**: Backend source suppressions are the largest single category (~46 items) and involve shared patterns (async task typing, cache generics, config/vendor boundaries). Resolving the shared patterns first creates reusable solutions that accelerate the remaining one-off fixes.

**Independent Test**: Can be tested by running the backend type checker on source code with zero `# type: ignore` comments remaining in authored source code and verifying a clean exit. Delivers value by catching latent type bugs in production code.

**Acceptance Scenarios**:

1. **Given** backend source files under `solune/backend/src/`, **When** all `# type: ignore` comments in authored (non-vendor, non-generated) code are removed, **Then** the backend type checker exits with zero errors.
2. **Given** a suppression was hiding an actual defect, **When** the suppression is removed and the code is corrected, **Then** the existing test suite continues to pass and the previously masked behaviour is fixed.
3. **Given** a suppression exists because a third-party library lacks type stubs, **When** the suppression is replaced with a narrow protocol, type alias, or stub, **Then** the replacement covers only the minimal surface needed.

---

### User Story 3 - Backend Test Suppression Removal (Priority: P3)

A contributor working on backend tests finds that test helpers and fixtures use properly typed fakes instead of loosely typed objects annotated with `# type: ignore`. Tests are easier to write, read, and maintain because the type checker validates mock interfaces against real production types.

**Why this priority**: Backend test suppressions (~28 items) are concentrated in a few test modules. Resolving them requires the typed helper pattern established in P2 and the test type-check gate from P1.

**Independent Test**: Can be tested by running the backend test type-check configuration with zero `# type: ignore` comments in test code and verifying a clean exit plus all tests passing.

**Acceptance Scenarios**:

1. **Given** backend test files under `solune/backend/tests/`, **When** all `# type: ignore` comments are removed, **Then** the backend test type-check exits cleanly.
2. **Given** a test used a loosely typed fake, **When** the fake is replaced with a typed helper conforming to the production interface, **Then** the test still passes and the type checker accepts the helper.
3. **Given** all test suppressions are resolved, **When** the backend test type-check is turned on in the normal CI gate, **Then** CI passes on the default branch.

---

### User Story 4 - Frontend Production Suppression Removal (Priority: P4)

A contributor working on frontend source code finds that `@ts-expect-error` comments and unsafe `as unknown as` casts in production components and hooks are replaced with type-safe alternatives. Runtime edge cases that were previously masked by the casts are fixed or handled explicitly.

**Why this priority**: Frontend production suppressions are fewer but carry higher runtime risk. They span hooks (voice input), lazy loading, API services, and drag-and-drop components. Fixing them may expose and resolve latent runtime bugs.

**Independent Test**: Can be tested by running the frontend type checker with zero `@ts-expect-error` and zero `as unknown as` in production source files (excluding test infrastructure) and verifying a clean exit plus all existing tests passing.

**Acceptance Scenarios**:

1. **Given** frontend source files (excluding test files), **When** all `@ts-expect-error`, `@ts-ignore`, and `as unknown as` casts in authored code are removed, **Then** the frontend type checker exits cleanly.
2. **Given** an unsafe cast was masking a potential runtime failure, **When** the cast is replaced with a proper type guard or narrowing, **Then** the runtime behaviour is tested and the edge case is handled.
3. **Given** production suppressions are resolved, **When** the existing frontend test and E2E suites run, **Then** all tests pass.

---

### User Story 5 - Frontend Test Standardisation and Regression Guardrails (Priority: P5)

A contributor writing a new frontend test uses the project's typed mock foundation in the test setup file rather than ad-hoc `as unknown as` casts or `@ts-expect-error` directives. A dedicated frontend test type-check command runs in CI and pre-commit, preventing future regression. ESLint rules are tightened to flag new suppressions as errors.

**Why this priority**: This is the capstone phase. It standardises the test mock pattern, adds the test type-check gate for the frontend, and tightens ESLint guardrails so that future PRs cannot reintroduce suppressions without explicit justification.

**Independent Test**: Can be tested by running the new frontend test type-check command, then introducing an `@ts-expect-error` in a test file and verifying that both the type-check command and ESLint flag it.

**Acceptance Scenarios**:

1. **Given** frontend test files, **When** all `as unknown as` casts and `@ts-expect-error` directives are migrated to the typed mock foundation, **Then** the new frontend test type-check command exits cleanly.
2. **Given** CI configuration, **When** a PR introduces a new `@ts-expect-error` in a test file, **Then** the frontend test type-check step fails.
3. **Given** ESLint configuration, **When** a PR introduces a new `@ts-expect-error` anywhere in the codebase, **Then** ESLint reports an error for the suppression directive.
4. **Given** the testing documentation, **When** a contributor reads the testing guide, **Then** they find updated guidance on using the typed mock foundation and the new type-check commands.

---

### Edge Cases

- What happens when a third-party library ships without type stubs and a suppression genuinely cannot be removed? The resolution must document the reason in a comment and use the narrowest possible suppression (e.g., a specific error code rather than a bare suppression).
- What happens when removing a suppression reveals a runtime bug in production code? The bug must be fixed in the same change set rather than deferred, to avoid shipping a type-correct but behaviourally broken state.
- What happens when vendor or auto-generated files contain suppressions? They remain out of scope. Only authored source and test code is cleaned.
- What happens when a suppression exists to work around a known upstream type-checker bug? The suppression is kept but narrowed and annotated with a link to the upstream issue.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST include a dedicated backend test type-check configuration that covers all files under `solune/backend/tests/`.
- **FR-002**: The project MUST include a dedicated frontend test type-check configuration that covers all test files currently excluded by the main frontend type-check configuration (files matching `src/test/**`, `src/**/*.test.ts`, `src/**/*.test.tsx`, `src/**/*.spec.ts`, `src/**/*.spec.tsx`).
- **FR-003**: CI MUST execute both new test type-check configurations as distinct steps, reporting failures independently from existing source type-check steps.
- **FR-004**: The local pre-commit hook MUST execute both new test type-check commands, failing the commit if either reports errors.
- **FR-005**: All `# type: ignore` comments in authored backend source files (`solune/backend/src/`) MUST be removed or replaced with properly typed constructs; the backend source type checker MUST exit cleanly.
- **FR-006**: All `# type: ignore` comments in authored backend test files (`solune/backend/tests/`) MUST be removed or replaced with typed helpers; the backend test type-check MUST exit cleanly.
- **FR-007**: All `@ts-expect-error`, `@ts-ignore`, and unnecessary `as unknown as` casts in authored frontend source files (excluding test infrastructure) MUST be removed or replaced with type-safe constructs; the frontend type checker MUST exit cleanly.
- **FR-008**: All `@ts-expect-error`, `@ts-ignore`, and unnecessary `as unknown as` casts in authored frontend test files MUST be migrated to the typed mock foundation or equivalent typed helpers; the frontend test type-check MUST exit cleanly.
- **FR-009**: ESLint rules MUST be tightened to treat new suppression directives (`@ts-expect-error`, `@ts-ignore`) as errors.
- **FR-010**: Runtime defects exposed by removing suppressions MUST be fixed in the same change set.
- **FR-011**: Vendor, generated, and third-party output files MUST remain out of scope; no changes to files outside authored source and test code.
- **FR-012**: The testing documentation MUST be updated to reflect the new type-check commands, typed mock foundation guidance, and tightened lint rules.
- **FR-013**: When a suppression genuinely cannot be removed (e.g., missing upstream type stubs), the remaining suppression MUST use the narrowest possible form (e.g., specific error code) and include a comment explaining the reason.

### Assumptions

- The backend type checker remains at `standard` type-checking mode; no change to the global strictness level is required.
- The frontend strict mode setting remains unchanged; the new test type-check configuration inherits the same strictness.
- The existing test setup file in the frontend provides a sufficient typed mock foundation that can be extended for additional test patterns without introducing a new dependency.
- Suppressions in files generated by tools (e.g., OpenAPI codegen output) or vendored third-party code are not modified.
- The backend uses `uv` as the package runner and the frontend uses `npm` scripts; no new tooling is introduced.
- The ~46 backend source suppressions, ~28 backend test suppressions, and ~53 frontend source/test suppression matches referenced in the parent issue represent the current authored-code inventory at the time of specification.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero type-suppression comments remain in authored backend source and test files after cleanup, verified by a repository-wide search.
- **SC-002**: Zero type-suppression directives and unnecessary unsafe casts remain in authored frontend source and test files after cleanup, verified by a repository-wide search.
- **SC-003**: CI completes all lint, type-check (including new test type-check steps), test, and build stages with a clean pass on the default branch after the feature is merged.
- **SC-004**: The local pre-commit hook completes all validation steps (including new test type-check commands) with a clean pass on a repository with no pending changes.
- **SC-005**: All existing backend tests (unit, integration, concurrency) pass with no regressions after suppression removal.
- **SC-006**: All existing frontend tests (unit, component, E2E) pass with no regressions after suppression removal.
- **SC-007**: No new lint or type-check suppressions are introduced during the cleanup; the net suppression count is reduced to zero for authored code.
- **SC-008**: Testing documentation reflects the complete set of type-check commands and updated contributor guidance within one release cycle of the feature merge.
