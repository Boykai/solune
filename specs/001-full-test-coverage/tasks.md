# Tasks: 100% Test Coverage with Bug Fixes

**Input**: Design documents from `/specs/001-full-test-coverage/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests ARE the core deliverable of this feature — every task is test-related. The spec mandates 100% coverage across backend and frontend.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. The plan's 6 phases map to 4 user stories (P1–P4).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Monorepo**: `solune/backend/` (Python 3.12+, FastAPI, pytest) + `solune/frontend/` (TypeScript, React 18+, Vitest)
- Backend source: `solune/backend/src/`; tests: `solune/backend/tests/`
- Frontend source: `solune/frontend/src/`; tests co-located as `*.test.tsx`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish current state and verify existing test infrastructure is functional before making changes.

- [ ] T001 Run full backend test suite to record current baseline in solune/backend/ (`uv run pytest --cov=src --cov-branch`)
- [ ] T002 Run full frontend test suite to record current baseline in solune/frontend/ (`npm run test:coverage`)
- [ ] T003 [P] Review existing test infrastructure: solune/backend/tests/conftest.py, solune/backend/tests/helpers/factories.py, solune/backend/tests/helpers/assertions.py
- [ ] T004 [P] Review existing test infrastructure: solune/frontend/src/test/test-utils.tsx, solune/frontend/src/test/setup.ts, solune/frontend/src/test/a11y-helpers.ts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix known bugs and CI errors to establish a green baseline — ALL user story work depends on this

**⚠️ CRITICAL**: No coverage expansion can begin until all bug fixes are applied and existing suites pass

- [ ] T005 Fix devcontainers/ci@v0.3 invalid tag — pin to valid release tag in .github/workflows/devcontainer.yml
- [ ] T006 [P] Fix silent exception swallowing in verify_project_access() — log at WARNING and re-raise as HTTPException(403) in solune/backend/src/dependencies.py
- [ ] T007 [P] Add configurable timeout guard (default 5s) to RateLimitKeyMiddleware session resolution with IP-based fallback in solune/backend/src/middleware/rate_limit.py
- [ ] T008 [P] Improve McpValidationError to include field_errors: dict[str, list[str]] parameter in solune/backend/src/exceptions.py
- [ ] T009 Run full backend suite to confirm green baseline (`uv run pytest` — exit code 0, zero failures) in solune/backend/
- [ ] T010 Run full frontend suite to confirm green baseline (`npm run lint && npm run type-check && npm run test && npm run build`) in solune/frontend/

**Checkpoint**: Green baseline established — all existing tests pass reliably. Coverage expansion can now begin.

---

## Phase 3: User Story 1 — Fix Known Bugs and Establish Green Baseline (Priority: P1) 🎯 MVP

**Goal**: All 4 known bugs are resolved with tests proving correct behavior; existing suites pass with zero failures.

**Independent Test**: Run `uv run pytest` (backend) and `npm run test` (frontend) — zero failures; manually verify error propagation in patched code paths.

### Tests for User Story 1

> **NOTE: Write tests for each bug fix to verify correct behavior**

- [ ] T011 [P] [US1] Add test for verify_project_access() exception propagation (log + HTTPException 403) in solune/backend/tests/unit/test_dependencies.py
- [ ] T012 [P] [US1] Add test for RateLimitKeyMiddleware timeout behavior (timeout triggers IP-based fallback) in solune/backend/tests/unit/test_rate_limit.py
- [ ] T013 [P] [US1] Add test for McpValidationError field-level errors (field_errors dict serializes into response) in solune/backend/tests/unit/test_exceptions.py
- [ ] T014 [P] [US1] Add CI validation test for devcontainer.yml — verify pinned tag format in .github/workflows/devcontainer.yml

### Implementation for User Story 1

- [ ] T015 [US1] Verify all 4 bug fix tests pass (from T011–T014) confirming fixes from Phase 2 are correct
- [ ] T016 [US1] Run full backend + frontend suites end-to-end to confirm green baseline in solune/backend/ and solune/frontend/

**Checkpoint**: US1 complete — green baseline established, all bug fixes verified with dedicated tests.

---

## Phase 4: User Story 2 — Raise Backend Test Coverage to 100% (Priority: P2)

**Goal**: Comprehensive backend tests covering all services, branches, and edge cases — 100% line and branch coverage.

**Independent Test**: `uv run pytest --cov=src --cov-branch --cov-fail-under=100` passes; `uv run mutmut results` shows ≥85% kill rate on src/services/.

### Sub-Phase 4a: Backend Untested Services (78% → ~85%)

- [ ] T017 [P] [US2] Create test_agent_middleware.py with class-based tests for all paths in solune/backend/tests/unit/test_agent_middleware.py (target: solune/backend/src/services/agent_middleware.py)
- [ ] T018 [P] [US2] Create test_agent_provider.py with class-based tests for all paths in solune/backend/tests/unit/test_agent_provider.py (target: solune/backend/src/services/agent_provider.py)
- [ ] T019 [P] [US2] Create test_collision_resolver.py with tests for all resolution strategies in solune/backend/tests/unit/test_collision_resolver.py (target: solune/backend/src/services/collision_resolver.py)
- [ ] T020 [P] [US2] Create test_tools_presets.py for tools preset logic in solune/backend/tests/unit/test_tools_presets.py (target: solune/backend/src/services/tools/presets.py)
- [ ] T021 [P] [US2] Add tests for chores service modules if not already fully covered in solune/backend/tests/unit/test_chores_service.py (target: solune/backend/src/services/chores/)
- [ ] T022 [US2] Extend test_agents.py to cover _get_service() (0% → 100%), filter/sort logic, and all pending/purge/bulk branches in solune/backend/tests/unit/test_agents.py (target: solune/backend/src/api/agents.py)
- [ ] T023 [US2] Extend test_activity.py to cover missing branches at lines 50, 54, 64, 69 in solune/backend/tests/unit/test_activity.py (target: solune/backend/src/api/activity.py)
- [ ] T024 [US2] Verify backend coverage ≥85% line and ≥80% branch after sub-phase 4a (`uv run pytest --cov=src --cov-branch --cov-fail-under=85`)
- [ ] T025 [US2] Run mutation testing on new service modules and verify ≥80% kill rate (`uv run mutmut run` targeting new test files)

### Sub-Phase 4b: Backend Branch Coverage Blitz (85% → ~95%)

- [ ] T026 [US2] Audit solune/backend/coverage.json to identify all files with <90% branch coverage and create a remediation list
- [ ] T027 [P] [US2] Add branch tests for error paths, edge cases, None values, empty collections in all API files under solune/backend/src/api/
- [ ] T028 [P] [US2] Add branch tests for error paths, edge cases, None values, empty collections in all service files under solune/backend/src/services/
- [ ] T029 [P] [US2] Add integration test for cache layer flows in solune/backend/tests/integration/test_cache_integration.py (target: solune/backend/src/services/cache.py)
- [ ] T030 [P] [US2] Add integration test for encryption key rotation in solune/backend/tests/integration/test_encryption_rotation.py (target: solune/backend/src/services/encryption.py)
- [ ] T031 [P] [US2] Add integration test for MCP store operations in solune/backend/tests/integration/test_mcp_store_integration.py (target: solune/backend/src/services/mcp_store.py)
- [ ] T032 [P] [US2] Add integration test for template files I/O error handling in solune/backend/tests/integration/test_template_files_errors.py (target: solune/backend/src/services/template_files.py)
- [ ] T033 [P] [US2] Extend Hypothesis property tests for all Pydantic model roundtrips in solune/backend/tests/property/test_model_roundtrips.py
- [ ] T034 [P] [US2] Extend Hypothesis property tests for URL parsing edge cases in solune/backend/tests/property/test_url_parsing.py
- [ ] T035 [P] [US2] Extend Hypothesis property tests for label extraction edge cases in solune/backend/tests/property/test_label_extraction.py
- [ ] T036 [US2] Add migration rollback and corruption recovery tests in solune/backend/tests/integration/test_migrations.py
- [ ] T037 [US2] Verify backend coverage ≥95% line and ≥90% branch after sub-phase 4b (`uv run pytest --cov=src --cov-branch --cov-fail-under=95`)
- [ ] T038 [US2] Run mutation testing on src/services/ and verify ≥85% kill rate (`uv run mutmut run`)

### Sub-Phase 4c: Backend Coverage to 100%

- [ ] T039 [US2] Audit remaining coverage gaps — identify all files still below 100% line or branch coverage in solune/backend/
- [ ] T040 [US2] Add tests for all remaining uncovered lines and branches across solune/backend/src/
- [ ] T041 [US2] Add justified `# pragma: no cover` comments for legitimately unreachable code (TYPE_CHECKING, defensive assertions) in solune/backend/src/
- [ ] T042 [US2] Verify backend coverage reaches 100% line and 100% branch (`uv run pytest --cov=src --cov-branch --cov-fail-under=100`)

**Checkpoint**: US2 complete — backend at 100% line and branch coverage; mutation testing kills ≥85% of mutants.

---

## Phase 5: User Story 3 — Raise Frontend Test Coverage to 100% (Priority: P3)

**Goal**: Comprehensive frontend tests covering all components, hooks, and user flows — 100% across all metrics (statements, branches, functions, lines).

**Independent Test**: `npm run test:coverage` reports 100% all metrics; `npm run test:a11y` passes; all E2E green.

**Note**: Phase 5 (sub-phases 5a–5b) can run in PARALLEL with Phase 4 (sub-phases 4b–4c) since they target different codebases.

### Sub-Phase 5a: Frontend Component Coverage Sprint (50% → ~80%)

#### Agent Components (0% → 100%)

- [ ] T043 [P] [US3] Create AgentAvatar.test.tsx with render + a11y tests in solune/frontend/src/components/agents/AgentAvatar.test.tsx
- [ ] T044 [P] [US3] Create AgentCard.test.tsx with render + a11y tests in solune/frontend/src/components/agents/AgentCard.test.tsx
- [ ] T045 [P] [US3] Create AgentChatFlow.test.tsx with render + a11y tests in solune/frontend/src/components/agents/AgentChatFlow.test.tsx
- [ ] T046 [P] [US3] Create AgentIconCatalog.test.tsx with render + a11y tests in solune/frontend/src/components/agents/AgentIconCatalog.test.tsx
- [ ] T047 [P] [US3] Create AgentIconPickerModal.test.tsx with render + a11y tests in solune/frontend/src/components/agents/AgentIconPickerModal.test.tsx
- [ ] T048 [P] [US3] Create AgentInlineEditor.test.tsx with render + a11y tests in solune/frontend/src/components/agents/AgentInlineEditor.test.tsx
- [ ] T049 [P] [US3] Create BulkModelUpdateDialog.test.tsx with render + a11y tests in solune/frontend/src/components/agents/BulkModelUpdateDialog.test.tsx
- [ ] T050 [P] [US3] Create ToolsEditor.test.tsx with render + a11y tests in solune/frontend/src/components/agents/ToolsEditor.test.tsx

#### Board Components (24% → 100%)

- [ ] T051 [P] [US3] Create AddAgentPopover.test.tsx with render + a11y tests in solune/frontend/src/components/board/AddAgentPopover.test.tsx
- [ ] T052 [P] [US3] Create AgentCardSkeleton.test.tsx with render + a11y tests in solune/frontend/src/components/board/AgentCardSkeleton.test.tsx
- [ ] T053 [P] [US3] Create AgentColumnCell.test.tsx with render + a11y tests in solune/frontend/src/components/board/AgentColumnCell.test.tsx
- [ ] T054 [P] [US3] Create AgentConfigRow.test.tsx with render + a11y tests in solune/frontend/src/components/board/AgentConfigRow.test.tsx
- [ ] T055 [P] [US3] Create AgentDragOverlay.test.tsx with render + a11y tests in solune/frontend/src/components/board/AgentDragOverlay.test.tsx
- [ ] T056 [P] [US3] Create AgentPresetSelector.test.tsx with render + a11y tests in solune/frontend/src/components/board/AgentPresetSelector.test.tsx
- [ ] T057 [P] [US3] Create BoardColumnSkeleton.test.tsx with render + a11y tests in solune/frontend/src/components/board/BoardColumnSkeleton.test.tsx
- [ ] T058 [P] [US3] Create BoardDragOverlay.test.tsx with render + a11y tests in solune/frontend/src/components/board/BoardDragOverlay.test.tsx
- [ ] T059 [P] [US3] Create BoardToolbar.test.tsx with render + a11y tests in solune/frontend/src/components/board/BoardToolbar.test.tsx
- [ ] T060 [P] [US3] Create CleanUpAuditHistory.test.tsx with render + a11y tests in solune/frontend/src/components/board/CleanUpAuditHistory.test.tsx
- [ ] T061 [P] [US3] Create CleanUpButton.test.tsx with render + a11y tests in solune/frontend/src/components/board/CleanUpButton.test.tsx
- [ ] T062 [P] [US3] Create CleanUpSummary.test.tsx with render + a11y tests in solune/frontend/src/components/board/CleanUpSummary.test.tsx
- [ ] T063 [P] [US3] Create IssueCardSkeleton.test.tsx with render + a11y tests in solune/frontend/src/components/board/IssueCardSkeleton.test.tsx
- [ ] T064 [P] [US3] Create PipelineStagesSection.test.tsx with render + a11y tests in solune/frontend/src/components/board/PipelineStagesSection.test.tsx
- [ ] T065 [P] [US3] Create ProjectBoardContent.test.tsx with render + a11y tests in solune/frontend/src/components/board/ProjectBoardContent.test.tsx
- [ ] T066 [P] [US3] Create ProjectBoardErrorBanners.test.tsx with render + a11y tests in solune/frontend/src/components/board/ProjectBoardErrorBanners.test.tsx
- [ ] T067 [P] [US3] Create RefreshButton.test.tsx with render + a11y tests in solune/frontend/src/components/board/RefreshButton.test.tsx
- [ ] T068 [P] [US3] Create colorUtils.test.ts with unit tests in solune/frontend/src/components/board/colorUtils.test.ts

#### Settings Components (24% → 100%)

- [ ] T069 [P] [US3] Create AIPreferences.test.tsx with render + a11y tests in solune/frontend/src/components/settings/AIPreferences.test.tsx
- [ ] T070 [P] [US3] Create AISettingsSection.test.tsx with render + a11y tests in solune/frontend/src/components/settings/AISettingsSection.test.tsx
- [ ] T071 [P] [US3] Create AdvancedSettings.test.tsx with render + a11y tests in solune/frontend/src/components/settings/AdvancedSettings.test.tsx
- [ ] T072 [P] [US3] Create DisplayPreferences.test.tsx with render + a11y tests in solune/frontend/src/components/settings/DisplayPreferences.test.tsx
- [ ] T073 [P] [US3] Create DisplaySettings.test.tsx with render + a11y tests in solune/frontend/src/components/settings/DisplaySettings.test.tsx
- [ ] T074 [P] [US3] Create GlobalSettings.test.tsx with render + a11y tests in solune/frontend/src/components/settings/GlobalSettings.test.tsx
- [ ] T075 [P] [US3] Create NotificationPreferences.test.tsx with render + a11y tests in solune/frontend/src/components/settings/NotificationPreferences.test.tsx
- [ ] T076 [P] [US3] Create NotificationSettings.test.tsx with render + a11y tests in solune/frontend/src/components/settings/NotificationSettings.test.tsx
- [ ] T077 [P] [US3] Create PrimarySettings.test.tsx with render + a11y tests in solune/frontend/src/components/settings/PrimarySettings.test.tsx
- [ ] T078 [P] [US3] Create ProjectSettings.test.tsx with render + a11y tests in solune/frontend/src/components/settings/ProjectSettings.test.tsx
- [ ] T079 [P] [US3] Create SignalConnection.test.tsx with render + a11y tests in solune/frontend/src/components/settings/SignalConnection.test.tsx
- [ ] T080 [P] [US3] Create WorkflowDefaults.test.tsx with render + a11y tests in solune/frontend/src/components/settings/WorkflowDefaults.test.tsx
- [ ] T081 [P] [US3] Create globalSettingsSchema.test.ts with unit tests in solune/frontend/src/components/settings/globalSettingsSchema.test.ts

#### Pipeline Components (28% → 100%)

- [ ] T082 [P] [US3] Create ExecutionGroupCard.test.tsx with render + a11y tests in solune/frontend/src/components/pipeline/ExecutionGroupCard.test.tsx
- [ ] T083 [P] [US3] Create ModelSelector.test.tsx with render + a11y tests in solune/frontend/src/components/pipeline/ModelSelector.test.tsx
- [ ] T084 [P] [US3] Create ParallelStageGroup.test.tsx with render + a11y tests in solune/frontend/src/components/pipeline/ParallelStageGroup.test.tsx
- [ ] T085 [P] [US3] Create PipelineModelDropdown.test.tsx with render + a11y tests in solune/frontend/src/components/pipeline/PipelineModelDropdown.test.tsx
- [ ] T086 [P] [US3] Create PipelineRunHistory.test.tsx with render + a11y tests in solune/frontend/src/components/pipeline/PipelineRunHistory.test.tsx
- [ ] T087 [P] [US3] Create PipelineStagesOverview.test.tsx with render + a11y tests in solune/frontend/src/components/pipeline/PipelineStagesOverview.test.tsx
- [ ] T088 [P] [US3] Create PipelineToolbar.test.tsx with render + a11y tests in solune/frontend/src/components/pipeline/PipelineToolbar.test.tsx
- [ ] T089 [P] [US3] Create PresetBadge.test.tsx with render + a11y tests in solune/frontend/src/components/pipeline/PresetBadge.test.tsx
- [ ] T090 [P] [US3] Create UnsavedChangesDialog.test.tsx with render + a11y tests in solune/frontend/src/components/pipeline/UnsavedChangesDialog.test.tsx

#### Remaining Components (layout, common, auth, tools, activity, command-palette, help, onboarding)

- [ ] T091 [P] [US3] Add tests for untested components in solune/frontend/src/components/activity/ (all .tsx files)
- [ ] T092 [P] [US3] Add tests for untested components in solune/frontend/src/components/command-palette/ (all .tsx files)
- [ ] T093 [P] [US3] Add tests for remaining untested components in solune/frontend/src/components/auth/ (all .tsx files without .test.tsx)
- [ ] T094 [P] [US3] Add tests for remaining untested components in solune/frontend/src/components/help/ (all .tsx files without .test.tsx)
- [ ] T095 [P] [US3] Add tests for remaining untested components in solune/frontend/src/components/onboarding/ (all .tsx files without .test.tsx)
- [ ] T096 [P] [US3] Add tests for remaining untested components in solune/frontend/src/components/tools/ (all .tsx files without .test.tsx)
- [ ] T097 [P] [US3] Add tests for remaining untested components in solune/frontend/src/components/common/ (all .tsx files without .test.tsx)

#### Missing Pages & Hooks

- [ ] T098 [P] [US3] Create ActivityPage.test.tsx with render, navigation, and a11y tests in solune/frontend/src/pages/ActivityPage.test.tsx
- [ ] T099 [P] [US3] Create useAdaptivePolling.test.ts with all code paths in solune/frontend/src/hooks/useAdaptivePolling.test.ts
- [ ] T100 [P] [US3] Create useBoardProjection.test.ts with all code paths in solune/frontend/src/hooks/useBoardProjection.test.ts
- [ ] T101 [P] [US3] Create useConfirmation.test.tsx with all code paths in solune/frontend/src/hooks/useConfirmation.test.tsx
- [ ] T102 [P] [US3] Create useUndoRedo.test.ts with all code paths in solune/frontend/src/hooks/useUndoRedo.test.ts

#### Sub-Phase 5a Verification

- [ ] T103 [US3] Verify frontend coverage ≥80% all metrics (`npm run test:coverage`) in solune/frontend/
- [ ] T104 [US3] Verify accessibility tests pass (`npm run test:a11y`) in solune/frontend/

### Sub-Phase 5b: Frontend Branch & Edge Case Coverage (80% → 100%)

- [ ] T105 [US3] Audit solune/frontend/coverage-final.json to identify all files with <100% branch coverage and create remediation list
- [ ] T106 [P] [US3] Add error, loading, and empty state tests for every component in solune/frontend/src/components/
- [ ] T107 [P] [US3] Add property tests (@fast-check/vitest) for complex hooks in solune/frontend/src/hooks/ (useAdaptivePolling, useBoardProjection, useUndoRedo)
- [ ] T108 [P] [US3] Add property tests (@fast-check/vitest) for untested transforms in solune/frontend/src/lib/
- [ ] T109 [P] [US3] Add negative path tests for API errors (401/403/404/500) in solune/frontend/src/services/ test files
- [ ] T110 [P] [US3] Add negative path tests for invalid form inputs across form components in solune/frontend/src/components/
- [ ] T111 [P] [US3] Add WebSocket disconnect/reconnect tests in solune/frontend/src/hooks/ or solune/frontend/src/services/
- [ ] T112 [US3] Create App.test.tsx with route matching, lazy loading, and error boundary tests in solune/frontend/src/App.test.tsx (target: solune/frontend/src/App.tsx — currently 0%)
- [ ] T113 [P] [US3] Extend E2E test for ActivityPage flows in solune/frontend/e2e/activity.spec.ts
- [ ] T114 [P] [US3] Extend E2E tests for agent CRUD negative paths in solune/frontend/e2e/agent-creation.spec.ts
- [ ] T115 [P] [US3] Extend E2E tests for offline/error recovery scenarios in solune/frontend/e2e/error-recovery.spec.ts

### Sub-Phase 5c: Frontend Coverage to 100%

- [ ] T116 [US3] Audit remaining coverage gaps — identify all files still below 100% across all metrics in solune/frontend/
- [ ] T117 [US3] Add tests for all remaining uncovered lines, branches, functions, and statements across solune/frontend/src/
- [ ] T118 [US3] Verify frontend coverage reaches 100% all metrics (`npm run test:coverage`) in solune/frontend/
- [ ] T119 [US3] Run frontend mutation testing and verify ≥80% kill rate on hooks+lib (`npm run test:mutate`) in solune/frontend/

**Checkpoint**: US3 complete — frontend at 100% across all coverage metrics; mutation testing kills ≥80% on hooks+lib.

---

## Phase 6: User Story 4 — Lock In 100% Thresholds and Prevent Regression (Priority: P4)

**Goal**: Coverage thresholds permanently set to 100% and enforced in CI; mutation testing expanded; singletons refactored to DI.

**Independent Test**: Attempt to merge a change that reduces coverage below 100% — CI rejects it.

### Configuration Threshold Updates

- [ ] T120 [P] [US4] Update backend fail_under from 75 to 100 in solune/backend/pyproject.toml [tool.coverage.report]
- [ ] T121 [P] [US4] Update frontend coverage thresholds to 100/100/100/100 in solune/frontend/vitest.config.ts
- [ ] T122 [P] [US4] Expand mutmut paths_to_mutate from ["src/services/"] to ["src/"] in solune/backend/pyproject.toml [tool.mutmut]
- [ ] T123 [P] [US4] Expand Stryker mutateFiles to include src/components/**/*.tsx and src/pages/**/*.tsx in solune/frontend/stryker.config.mjs

### Singleton Refactor

- [ ] T124 [US4] Refactor module-level singletons in solune/backend/src/services/github_projects/service.py to dependency injection pattern
- [ ] T125 [US4] Refactor module-level singletons in solune/backend/src/api/agents.py to dependency injection pattern (TODO debt)
- [ ] T126 [US4] Update existing tests affected by singleton refactor to use DI injection in solune/backend/tests/

### CI Regression Guard

- [ ] T127 [US4] Add CI coverage regression guard — ensure pipeline fails on any coverage decrease in .github/workflows/ci.yml

### Final Verification

- [ ] T128 [US4] Verify backend passes with 100% threshold (`uv run pytest --cov=src --cov-branch --cov-fail-under=100`) in solune/backend/
- [ ] T129 [US4] Verify frontend passes with 100% thresholds (`npm run test:coverage` enforced at 100%) in solune/frontend/
- [ ] T130 [US4] Run expanded mutation testing backend — verify ≥85% kill rate on all src/ (`uv run mutmut run`) in solune/backend/
- [ ] T131 [US4] Run expanded mutation testing frontend — verify ≥80% kill rate including components+pages (`npm run test:mutate`) in solune/frontend/
- [ ] T132 [US4] Run full CI pipeline end-to-end and confirm green (`uv run pytest` + `npm run lint && npm run type-check && npm run test:coverage && npm run build`)

**Checkpoint**: US4 complete — 100% thresholds locked in, CI regression guard active, mutation testing expanded.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup and validation across all user stories

- [ ] T133 [P] Document coverage exclusion policy (pragma: no cover usage) in solune/backend/ and solune/frontend/
- [ ] T134 [P] Verify all new test files follow existing conventions (class-based backend, co-located frontend, a11y checks)
- [ ] T135 Run quickstart.md validation — execute all commands from specs/001-full-test-coverage/quickstart.md and confirm they work
- [ ] T136 Verify backend contracts from specs/001-full-test-coverage/contracts/backend-coverage-contract.md (all phase acceptance commands pass)
- [ ] T137 Verify frontend contracts from specs/001-full-test-coverage/contracts/frontend-coverage-contract.md (all phase acceptance commands pass)
- [ ] T138 Final end-to-end CI validation: all tests pass, all thresholds met, all E2E green

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (Phase 2) — validates bug fixes
- **US2 (Phase 4)**: Depends on US1 (Phase 3) — requires green baseline; backend-only work
- **US3 (Phase 5)**: Depends on US1 (Phase 3) — requires green baseline; frontend-only work
  - **⚡ Sub-Phase 5a can run in PARALLEL with Phase 4 Sub-Phases 4b–4c** (different codebases)
- **US4 (Phase 6)**: Depends on US2 AND US3 completion — requires 100% coverage before locking thresholds
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

```text
Phase 1 (Setup)
    └──→ Phase 2 (Foundational: Bug Fixes)
              └──→ Phase 3 (US1: Verify Bug Fixes)
                        ├──→ Phase 4 (US2: Backend Coverage) ─────────╮
                        │        ├── 4a: Untested Services (→85%)     │
                        │        ├── 4b: Branch Blitz (→95%)    ◄──parallel──► Phase 5a/5b
                        │        └── 4c: Final Backend (→100%)        │
                        │                                             │
                        └──→ Phase 5 (US3: Frontend Coverage) ────────╯
                                 ├── 5a: Component Sprint (→80%)
                                 ├── 5b: Branch & Edge Cases (→100%)
                                 └── 5c: Final Frontend (→100%)
                                                                     ╲
                                                                      ↘
                                                                 Phase 6 (US4: Hardening)
                                                                      └──→ Phase 7 (Polish)
```

### Within Each User Story

- Models/entities before services
- Services before endpoints/components
- Tests written first where possible (Red-Green-Refactor)
- Verification checkpoint at end of each sub-phase
- Story complete before moving to dependent stories

### Parallel Opportunities

**Within Phase 2 (Foundational)**:
- T006, T007, T008 can all run in parallel (different source files)

**Within Phase 3 (US1 Tests)**:
- T011, T012, T013, T014 can all run in parallel (different test files)

**Within Phase 4a (Backend Untested Services)**:
- T017, T018, T019, T020, T021 can all run in parallel (different test files targeting different modules)

**Within Phase 4b (Backend Branch Blitz)**:
- T027–T035 can all run in parallel (different test files)

**Cross-Phase Parallelism (MAJOR OPPORTUNITY)**:
- Phase 4 sub-phases 4b–4c (backend) and Phase 5 sub-phases 5a–5b (frontend) are independent codebases
- Two developers can work simultaneously: one on backend branch coverage, one on frontend components

**Within Phase 5a (Frontend Components)**:
- ALL component test creation tasks (T043–T102) can run in parallel (each targets a different file)

**Within Phase 5b (Frontend Edge Cases)**:
- T106–T111, T113–T115 can all run in parallel (different concerns, different files)

**Within Phase 6 (Hardening)**:
- T120–T123 can all run in parallel (different config files)

---

## Parallel Example: User Story 2 (Backend Coverage)

```bash
# Launch all untested service tests together (Sub-Phase 4a):
Task: "Create test_agent_middleware.py in tests/unit/test_agent_middleware.py"
Task: "Create test_agent_provider.py in tests/unit/test_agent_provider.py"
Task: "Create test_collision_resolver.py in tests/unit/test_collision_resolver.py"
Task: "Create test_tools_presets.py in tests/unit/test_tools_presets.py"

# Launch all integration tests together (Sub-Phase 4b):
Task: "Add integration test for cache layer in tests/integration/test_cache_integration.py"
Task: "Add integration test for encryption key rotation in tests/integration/test_encryption_rotation.py"
Task: "Add integration test for MCP store in tests/integration/test_mcp_store_integration.py"
Task: "Add integration test for template files I/O in tests/integration/test_template_files_errors.py"

# Launch all property tests together (Sub-Phase 4b):
Task: "Extend Hypothesis property tests for Pydantic roundtrips in tests/property/test_model_roundtrips.py"
Task: "Extend Hypothesis property tests for URL parsing in tests/property/test_url_parsing.py"
Task: "Extend Hypothesis property tests for label extraction in tests/property/test_label_extraction.py"
```

## Parallel Example: User Story 3 (Frontend Coverage)

```bash
# Launch ALL agent component tests in parallel (Sub-Phase 5a):
Task: "Create AgentAvatar.test.tsx"
Task: "Create AgentCard.test.tsx"
Task: "Create AgentChatFlow.test.tsx"
Task: "Create AgentIconCatalog.test.tsx"
# ... (8 agent component files, all independent)

# Launch ALL board component tests in parallel (Sub-Phase 5a):
Task: "Create AddAgentPopover.test.tsx"
Task: "Create AgentCardSkeleton.test.tsx"
# ... (18 board component files, all independent)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup — record current baselines
2. Complete Phase 2: Foundational — fix all 4 known bugs
3. Complete Phase 3: US1 — verify bug fixes with dedicated tests
4. **STOP and VALIDATE**: Run full suites, confirm green baseline
5. Merge if ready — bug fixes provide immediate value

### Incremental Delivery

1. Complete Setup + Foundational + US1 → Green baseline (MVP!)
2. Add US2 (Backend Coverage) → Verify 100% backend → Merge
3. Add US3 (Frontend Coverage) → Verify 100% frontend → Merge
4. Add US4 (Hardening) → Lock thresholds → Merge
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With two developers:

1. Both complete Setup + Foundational + US1 together
2. Once US1 is done:
   - **Developer A**: US2 (Backend Coverage — Phases 4a → 4b → 4c)
   - **Developer B**: US3 (Frontend Coverage — Phases 5a → 5b → 5c)
3. Both join for US4 (Hardening) after their respective coverage targets are met
4. Final Polish together

### Estimated Task Distribution

| Phase | Tasks | Parallelizable | Estimated Effort |
|-------|-------|---------------|------------------|
| Setup (Phase 1) | 4 | 2 | Small |
| Foundational (Phase 2) | 6 | 3 | Medium |
| US1 — Bug Fix Tests (Phase 3) | 6 | 4 | Small |
| US2 — Backend Coverage (Phase 4) | 26 | 18 | Large |
| US3 — Frontend Coverage (Phase 5) | 77 | 67 | Very Large |
| US4 — Hardening (Phase 6) | 13 | 4 | Medium |
| Polish (Phase 7) | 6 | 2 | Small |
| **TOTAL** | **138** | **100 (72%)** | — |

---

## Notes

- [P] tasks = different files, no dependencies — safe to parallelize
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Backend conventions: class-based tests, conftest.py fixtures, factories.py, assertions.py, AsyncMock
- Frontend conventions: co-located test files, renderWithProviders(), expectNoA11yViolations(), vi.mock()
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Phase 5a–5b frontend work can run in parallel with Phase 4b–4c backend work (different codebases)
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
