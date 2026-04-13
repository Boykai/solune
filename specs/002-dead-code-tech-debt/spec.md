# Feature Specification: Remove Dead Code & Tech Debt

**Feature Branch**: `002-dead-code-tech-debt`  
**Created**: 2026-04-13  
**Status**: Draft  
**Input**: User description: "Remove Dead Code & Tech Debt"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Remove Deprecated Backend Modules (Priority: P1)

A developer working on the backend encounters deprecated prompt modules (`issue_generation.py`, `task_generation.py`, `transcript_analysis.py`) and the deprecated `AIAgentService` (`ai_agent.py`). These modules were replaced by `agent_instructions` and `ChatAgentService` in v0.2.0 and marked for removal in v0.3.0. The developer removes these files and migrates the two remaining consumers to the current service, so the codebase no longer carries dead code that could confuse contributors or introduce bugs.

**Why this priority**: Deprecated modules are the largest source of dead code. Removing them eliminates the primary confusion risk for new contributors and prevents accidental use of superseded interfaces.

**Independent Test**: Can be fully tested by running the backend test suite after deletion and verifying zero remaining references to the removed modules via a codebase-wide search.

**Acceptance Scenarios**:

1. **Given** the backend contains `issue_generation.py`, `task_generation.py`, and `transcript_analysis.py`, **When** these files are deleted, **Then** no module in the codebase imports or references them.
2. **Given** `chat.py` lazily imports `get_ai_agent_service`, **When** the import is replaced with `ChatAgentService`, **Then** `identify_target_task()` functionality continues to work correctly via the new service.
3. **Given** `conftest.py` imports `AIAgentService` and defines `mock_ai_agent_service`, **When** these are removed and dependent tests are updated, **Then** all tests pass without the deprecated fixture.
4. **Given** `ai_agent.py` exists, **When** all consumers are migrated and the file is deleted, **Then** a codebase-wide search for `ai_agent` returns zero results (excluding git history and documentation).

---

### User Story 2 - Remove Deprecated Completion Providers (Priority: P1)

A developer finds `completion_providers.py`, a deprecated module with client-pool and factory patterns replaced in v0.2.0. Four active services still lazily import from it. The developer migrates each consumer to the current provider pattern and deletes the deprecated module, reducing the codebase surface area and preventing future coupling to a dead abstraction.

**Why this priority**: This module is imported by four active services. Leaving it creates a maintenance trap where developers may unknowingly build on deprecated foundations.

**Independent Test**: Can be tested by running the backend test suite, type checker, and linter after migration, then verifying zero remaining references to `completion_providers`.

**Acceptance Scenarios**:

1. **Given** `model_fetcher.py` directly imports from `completion_providers`, **When** the import is updated to the current provider, **Then** model fetching works identically and type checks pass.
2. **Given** `agent_provider.py`, `plan_agent_provider.py`, and `label_classifier.py` lazily import from `completion_providers`, **When** each lazy import is migrated, **Then** all dependent functionality works correctly.
3. **Given** `completion_providers.py` exists, **When** all consumers are migrated and the file is deleted, **Then** a codebase-wide search for `completion_providers` returns zero results (excluding git history and documentation).

---

### User Story 3 - Clean Up Frontend Logging (Priority: P2)

A product team member notices debug-level log messages appearing in the browser console of production deployments. The developer wraps unguarded `console.debug()` and `console.warn()` calls in development-only guards, so production users see a clean console and sensitive debugging data is not exposed.

**Why this priority**: Unguarded logging in production is a minor quality issue that affects perceived professionalism and could expose internal data patterns. It is lower priority than removing dead backend modules because it does not block other work.

**Independent Test**: Can be tested by building the frontend in production mode and verifying that the specific log statements do not execute, then building in development mode and verifying they still appear for developers.

**Acceptance Scenarios**:

1. **Given** `api.ts` contains unguarded `console.debug()` calls at three locations, **When** each is wrapped in a development-only guard, **Then** production builds produce no output from those statements.
2. **Given** `usePipelineConfig.ts` contains an unguarded `console.warn()`, **When** it is wrapped in a development-only guard, **Then** the warning only appears in development builds.
3. **Given** `tooltip.tsx` already wraps its `console.warn()` in a development guard, **When** no changes are made to it, **Then** the existing behavior is preserved.

---

### User Story 4 - Evaluate Deprecated Pipeline Metadata Field (Priority: P2)

A developer evaluates whether the deprecated `pipeline_metadata` field in the auto-merge service can be safely removed. The field was marked as deprecated for dedup/retry-cap tracking but is still referenced by active call sites. The developer determines whether removal is safe or whether it requires a data migration, and documents the decision.

**Why this priority**: This is a scoped evaluation that may or may not result in code removal. It has lower impact than removing full deprecated modules but prevents accumulation of stale fields.

**Independent Test**: Can be tested by analyzing current usage of the field, determining if active callers depend on it, and verifying that removal (if safe) does not break tests or runtime behavior.

**Acceptance Scenarios**:

1. **Given** `pipeline_metadata` is marked deprecated in `auto_merge.py`, **When** the field's usage is evaluated across the codebase, **Then** a clear decision is documented: remove (with migration if needed) or defer with justification.
2. **Given** the decision is to remove, **When** the field and all references are deleted, **Then** all backend tests pass and no runtime errors occur in the auto-merge flow.
3. **Given** the decision is to defer, **When** the rationale is documented, **Then** a tracked follow-up item exists for future resolution.

---

### User Story 5 - Organize Root-Level Spec Files (Priority: P3)

A contributor navigating the repository root finds loose spec files (`plan.md`, `spec.md`, `tasks.md`, `data-model.md`, `research.md`, `quickstart.md`) that belong to the "simplify-page-headers" feature but are not in the `specs/` directory. The developer moves them into `specs/000-simplify-page-headers/` for consistency with the mono-spec pattern used by other features.

**Why this priority**: This is a repository organization improvement. It does not affect functionality but improves discoverability and consistency for contributors.

**Independent Test**: Can be tested by verifying all files exist in the new location, the root directory no longer contains the moved files, and no broken references exist.

**Acceptance Scenarios**:

1. **Given** `plan.md`, `spec.md`, `tasks.md`, `data-model.md`, `research.md`, and `quickstart.md` exist at the repository root, **When** they are moved to `specs/000-simplify-page-headers/`, **Then** the new directory contains all six files.
2. **Given** the files are moved, **When** any internal cross-references between the files are checked, **Then** relative links still work in the new location.
3. **Given** the `specs/` directory already contains `001-fleet-dispatch-pipelines/`, **When** `000-simplify-page-headers/` is created, **Then** the directory listing is ordered logically with `000` first.

---

### Edge Cases

- What happens if a consumer of `AIAgentService` uses methods beyond `identify_target_task()`? All call sites must be audited to ensure `ChatAgentService` provides equivalent functionality.
- What happens if `completion_providers.py` is imported dynamically via string-based imports or plugin loading? A comprehensive search must cover dynamic imports, not just static `import` statements.
- What happens if the `pipeline_metadata` field is serialized to persistent storage (database, cache, API responses)? Removal requires verifying no stored data depends on the field schema.
- What happens if root-level spec files are referenced by CI workflows, documentation generators, or README links? All references must be updated or redirected.
- What happens if removing deprecated modules causes circular import resolution changes? The existing import order must be preserved for modules that depend on lazy-import patterns.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST delete `issue_generation.py`, `task_generation.py`, and `transcript_analysis.py` from the prompts directory with zero remaining references in active code.
- **FR-002**: System MUST migrate all `get_ai_agent_service` consumers in `chat.py` to use `ChatAgentService`, preserving identical behavior for `identify_target_task()` functionality.
- **FR-003**: System MUST remove `AIAgentService` imports and the `mock_ai_agent_service` fixture from `conftest.py`, updating all dependent tests to use the current service.
- **FR-004**: System MUST delete `ai_agent.py` after all consumers are migrated, with a codebase-wide search confirming zero remaining references.
- **FR-005**: System MUST migrate `model_fetcher.py` from its direct import of `completion_providers` to the current provider pattern.
- **FR-006**: System MUST migrate lazy imports in `agent_provider.py`, `plan_agent_provider.py`, and `label_classifier.py` away from `completion_providers`.
- **FR-007**: System MUST delete `completion_providers.py` after all consumers are migrated, with a codebase-wide search confirming zero remaining references.
- **FR-008**: System MUST wrap unguarded `console.debug()` calls in `api.ts` with development-only guards so they do not execute in production builds.
- **FR-009**: System MUST wrap the unguarded `console.warn()` in `usePipelineConfig.ts` with a development-only guard.
- **FR-010**: System MUST evaluate the deprecated `pipeline_metadata` field in `auto_merge.py` and either remove it (with migration if needed) or document a deferral with justification.
- **FR-011**: System MUST move root-level spec files (`plan.md`, `spec.md`, `tasks.md`, `data-model.md`, `research.md`, `quickstart.md`) into `specs/000-simplify-page-headers/`.
- **FR-012**: System MUST NOT modify intentional circular import workarounds in `dependencies.py` and `github_projects/service.py`.
- **FR-013**: System MUST NOT modify auto-generated OpenAPI types in `openapi-generated.d.ts`.
- **FR-014**: System MUST preserve all existing test coverage — no tests may be removed unless they exclusively test deleted deprecated code.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A codebase-wide search for `ai_agent`, `completion_providers`, `issue_generation`, `task_generation`, and `transcript_analysis` returns zero hits in active source code after cleanup is complete.
- **SC-002**: All existing backend tests pass after each phase of removal, confirming no regressions.
- **SC-003**: The type checker reports no new errors after migration of deprecated imports.
- **SC-004**: The linter reports no new warnings or errors after all changes.
- **SC-005**: Production frontend builds contain zero console output from the guarded logging statements.
- **SC-006**: Development frontend builds continue to display all debug and warning messages for developer use.
- **SC-007**: All existing frontend tests pass after logging changes.
- **SC-008**: The number of deprecated modules in the backend is reduced from five to zero.
- **SC-009**: The repository root contains zero misplaced spec files after reorganization.
- **SC-010**: Contract validation confirms the OpenAPI schema is unaffected by all changes.
- **SC-011**: Both backend and frontend application builds succeed after all changes.

## Assumptions

- `ChatAgentService` already provides all functionality needed by the remaining consumers of `AIAgentService`, specifically the `identify_target_task()` method or its equivalent.
- The lazy-import patterns in consumer modules are used to avoid circular imports; migration must preserve this pattern where necessary.
- The `import.meta.env.DEV` guard is the established frontend pattern for development-only code, as evidenced by existing usage in `tooltip.tsx`.
- The `prompts/` directory has no `__init__.py` file, so there are no re-exports to clean up for the deprecated prompt modules.
- The `app_service.py` file referenced in the parent issue does not exist in the current codebase; this consumer has already been removed or was misidentified.
- The `tooltip.tsx` `console.warn()` is already wrapped in a development guard and requires no changes.
- The singleton DI refactor (TODO-018) is explicitly out of scope and will be tracked as a separate issue.
- Root-level spec files belong to the "simplify-page-headers" feature based on repository convention and the parent issue's direction.

## Scope Exclusions

- **Circular import workarounds**: Intentional patterns in `dependencies.py` and `github_projects/service.py` are excluded.
- **Auto-generated types**: `openapi-generated.d.ts` is managed by the contract pipeline and excluded.
- **Frontend structural cleanup**: No dead components, hooks, routes, or unused dependencies were identified.
- **Singleton DI refactor**: Module-level singleton replacement with dependency injection is a larger architecture change deferred to a separate issue.
