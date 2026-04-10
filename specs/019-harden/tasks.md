# Tasks: #Harden

**Input**: Design documents from `/specs/019-harden/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are a **primary deliverable** in this initiative (Phase 2). Test tasks are included for all user stories.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `solune/backend/src/`, `solune/backend/tests/`
- **Frontend**: `solune/frontend/src/`, `solune/frontend/e2e/`
- **Config**: `solune/backend/pyproject.toml`, `solune/frontend/vitest.config.ts`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify resolved bugs, ensure clean CI baseline

- [ ] T001 Verify bug 1.1 (memory leak) is resolved — confirm `BoundedDict` usage in `solune/backend/src/services/pipeline_state_store.py`
- [ ] T002 Verify bug 1.2 (lifecycle status) is resolved — confirm `PENDING_PR` in all three SQL paths in `solune/backend/src/services/agents/service.py`
- [ ] T003 Verify bug 3.4 (orphaned chat) is resolved — confirm message persistence ordering in `solune/backend/src/api/chat.py`
- [ ] T004 Run full CI suite to establish clean baseline before any changes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix the only remaining bug (1.3) — MUST complete before test coverage phases

**⚠️ CRITICAL**: Bug 1.3 fix must land before Phase 2 test coverage work to avoid test noise

- [ ] T005 Add per-element tool validation in `_extract_agent_preview()` in `solune/backend/src/services/agents/service.py` — after the `isinstance(tools, list)` check at line ~1472, add a guard that returns `None` if any element is not a `str` or is empty/whitespace: `if not all(isinstance(t, str) and t.strip() for t in tools): return None`
- [ ] T006 Add unit tests for malformed tool entries (int, None, empty string, dict, whitespace-only) in `solune/backend/tests/unit/test_agents_service.py`
- [ ] T007 Add unit test for `tools: None` edge case returning `None` in `solune/backend/tests/unit/test_agents_service.py`
- [ ] T008 Add unit test confirming valid tool entries still produce `AgentPreview` in `solune/backend/tests/unit/test_agents_service.py`

**Checkpoint**: Bug 1.3 fixed and validated — clean CI baseline established for coverage work

---

## Phase 3: User Story 1 — Fix Malformed Agent Config Crash (Priority: P1) 🎯 MVP

**Goal**: Gracefully reject malformed agent configurations so broken config entries never crash chat refinement

**Independent Test**: Submit agent config with invalid tool entries and verify the system returns `None` instead of a crash

> **Note**: Implementation for US1 is already covered in Phase 2 (Foundational) tasks T005–T008 since this is the blocking prerequisite bug fix. This phase adds regression and integration-level coverage.

### Tests for User Story 1

- [ ] T009 [P] [US1] Add property-based test for `_extract_agent_preview()` with hypothesis-generated malformed configs in `solune/backend/tests/property/test_model_validation.py`
- [ ] T010 [P] [US1] Add integration test verifying chat refinement handles malformed agent config gracefully in `solune/backend/tests/unit/test_agents_service.py`

### Implementation for User Story 1

- [ ] T011 [US1] Verify the `except (json.JSONDecodeError, KeyError, TypeError, ValueError)` catch block at line ~1484 in `solune/backend/src/services/agents/service.py` covers all new validation paths
- [ ] T012 [US1] Run `python -m pytest tests/unit/test_agents_service.py -k "extract_agent_preview" -v` to validate all US1 tests pass

**Checkpoint**: US1 complete — malformed agent configs are safely rejected, chat refinement is protected

---

## Phase 4: User Story 2 — Increase Backend Test Coverage (Priority: P1)

**Goal**: Cover ~30 untested backend modules and raise coverage threshold from 75% to 80%

**Independent Test**: From `solune/backend/`, run `python -m pytest tests/ --cov=src --cov-fail-under=80 -q` and confirm it passes

### Tests for User Story 2 — Prompt Templates

- [ ] T013 [P] [US2] Add unit tests for agent instructions prompt in `solune/backend/tests/unit/test_agent_instructions_prompt.py` (expand existing)
- [ ] T014 [P] [US2] Add unit tests for issue generation prompt in `solune/backend/tests/unit/test_issue_generation_prompt.py` (expand existing)
- [ ] T015 [P] [US2] Add unit tests for label classification prompt in `solune/backend/tests/unit/test_label_classification_prompts.py` (expand existing)
- [ ] T016 [P] [US2] Add unit tests for plan instructions prompt in `solune/backend/tests/unit/test_plan_instructions.py` (expand existing)
- [ ] T017 [P] [US2] Add unit tests for task generation prompt in `solune/backend/tests/unit/test_task_generation_prompt.py` (expand existing)
- [ ] T018 [P] [US2] Add unit tests for transcript analysis prompt in `solune/backend/tests/unit/test_transcript_analysis_prompt.py` (expand existing)

### Tests for User Story 2 — Copilot Polling Internals

- [ ] T019 [P] [US2] Add unit tests for polling agent_output module in `solune/backend/tests/unit/test_copilot_polling_agent_output.py`
- [ ] T020 [P] [US2] Add unit tests for polling auto_merge module in `solune/backend/tests/unit/test_copilot_polling_auto_merge.py`
- [ ] T021 [P] [US2] Add unit tests for polling completion module in `solune/backend/tests/unit/test_copilot_polling_completion.py`
- [ ] T022 [P] [US2] Add unit tests for polling recovery module in `solune/backend/tests/unit/test_copilot_polling_recovery.py`

### Tests for User Story 2 — MCP Server Tools

- [ ] T023 [P] [US2] Add unit tests for MCP tool: activity in `solune/backend/tests/unit/test_mcp_server/test_tools_activity.py`
- [ ] T024 [P] [US2] Add unit tests for MCP tool: agents in `solune/backend/tests/unit/test_mcp_server/test_tools_agents.py`
- [ ] T025 [P] [US2] Add unit tests for MCP tool: apps in `solune/backend/tests/unit/test_mcp_server/test_tools_apps.py`
- [ ] T026 [P] [US2] Add unit tests for MCP tool: chat in `solune/backend/tests/unit/test_mcp_server/test_tools_chat.py`
- [ ] T027 [P] [US2] Add unit tests for MCP tool: pipelines in `solune/backend/tests/unit/test_mcp_server/test_tools_pipelines.py`
- [ ] T028 [P] [US2] Add unit tests for MCP tool: projects in `solune/backend/tests/unit/test_mcp_server/test_tools_projects.py`
- [ ] T029 [P] [US2] Add unit tests for MCP tool: tasks in `solune/backend/tests/unit/test_mcp_server/test_tools_tasks.py`
- [ ] T030 [P] [US2] Add unit tests for MCP server auth in `solune/backend/tests/unit/test_mcp_server/test_auth.py`

### Tests for User Story 2 — Chores Service Internals

- [ ] T031 [P] [US2] Expand unit tests for chores chat module in `solune/backend/tests/unit/test_chores_chat.py`
- [ ] T032 [P] [US2] Expand unit tests for chores counter module in `solune/backend/tests/unit/test_chores_counter.py`
- [ ] T033 [P] [US2] Expand unit tests for chores scheduler module in `solune/backend/tests/unit/test_chores_scheduler.py`
- [ ] T034 [P] [US2] Expand unit tests for chores template builder module in `solune/backend/tests/unit/test_chores_template_builder.py`

### Tests for User Story 2 — Middleware

- [ ] T035 [P] [US2] Expand unit tests for request_id middleware in `solune/backend/tests/unit/test_request_id_middleware.py`

### Implementation for User Story 2

- [ ] T036 [US2] Update `fail_under` from 75 to 80 in `solune/backend/pyproject.toml` at line ~137
- [ ] T037 [US2] Run `python -m pytest tests/ --cov=src --cov-fail-under=80 -q` to validate 80% threshold is met

**Checkpoint**: US2 complete — backend coverage at 80%+, threshold enforced in CI

---

## Phase 5: User Story 3 — Increase Frontend Test Coverage (Priority: P1)

**Goal**: Cover ~61 untested frontend components and raise coverage thresholds to statements 60%, branches 52%, functions 50%, lines 60%

**Independent Test**: From `solune/frontend/`, run `npx vitest run --coverage` and confirm updated thresholds are met

### Tests for User Story 3 — Chores Components (13)

- [ ] T038 [P] [US3] Add component test for AddChoreModal in `solune/frontend/src/components/chores/AddChoreModal.test.tsx`
- [ ] T039 [P] [US3] Add component test for ChoreCard in `solune/frontend/src/components/chores/ChoreCard.test.tsx`
- [ ] T040 [P] [US3] Add component test for ChoreChatFlow in `solune/frontend/src/components/chores/ChoreChatFlow.test.tsx`
- [ ] T041 [P] [US3] Add component test for ChoreInlineEditor in `solune/frontend/src/components/chores/ChoreInlineEditor.test.tsx`
- [ ] T042 [P] [US3] Add component test for ChoreScheduleConfig in `solune/frontend/src/components/chores/ChoreScheduleConfig.test.tsx`
- [ ] T043 [P] [US3] Add component test for ChoresGrid in `solune/frontend/src/components/chores/ChoresGrid.test.tsx`
- [ ] T044 [P] [US3] Add component test for ChoresPanel in `solune/frontend/src/components/chores/ChoresPanel.test.tsx`
- [ ] T045 [P] [US3] Add component test for ChoresSaveAllBar in `solune/frontend/src/components/chores/ChoresSaveAllBar.test.tsx`
- [ ] T046 [P] [US3] Add component test for ChoresSpotlight in `solune/frontend/src/components/chores/ChoresSpotlight.test.tsx`
- [ ] T047 [P] [US3] Add component test for ChoresToolbar in `solune/frontend/src/components/chores/ChoresToolbar.test.tsx`
- [ ] T048 [P] [US3] Add component test for ConfirmChoreModal in `solune/frontend/src/components/chores/ConfirmChoreModal.test.tsx`
- [ ] T049 [P] [US3] Add component test for FeaturedRitualsPanel in `solune/frontend/src/components/chores/FeaturedRitualsPanel.test.tsx`
- [ ] T050 [P] [US3] Add component test for PipelineSelector in `solune/frontend/src/components/chores/PipelineSelector.test.tsx`

### Tests for User Story 3 — Agents Components (10)

- [ ] T051 [P] [US3] Add component test for AddAgentModal in `solune/frontend/src/components/agents/AddAgentModal.test.tsx`
- [ ] T052 [P] [US3] Add component test for AgentAvatar in `solune/frontend/src/components/agents/AgentAvatar.test.tsx`
- [ ] T053 [P] [US3] Add component test for AgentCard in `solune/frontend/src/components/agents/AgentCard.test.tsx`
- [ ] T054 [P] [US3] Add component test for AgentChatFlow in `solune/frontend/src/components/agents/AgentChatFlow.test.tsx`
- [ ] T055 [P] [US3] Add component test for AgentIconCatalog in `solune/frontend/src/components/agents/AgentIconCatalog.test.tsx`
- [ ] T056 [P] [US3] Add component test for AgentIconPickerModal in `solune/frontend/src/components/agents/AgentIconPickerModal.test.tsx`
- [ ] T057 [P] [US3] Add component test for AgentInlineEditor in `solune/frontend/src/components/agents/AgentInlineEditor.test.tsx`
- [ ] T058 [P] [US3] Add component test for AgentsPanel in `solune/frontend/src/components/agents/AgentsPanel.test.tsx`
- [ ] T059 [P] [US3] Add component test for BulkModelUpdateDialog in `solune/frontend/src/components/agents/BulkModelUpdateDialog.test.tsx`
- [ ] T060 [P] [US3] Add component test for InstallConfirmDialog in `solune/frontend/src/components/agents/InstallConfirmDialog.test.tsx`

### Tests for User Story 3 — Tools Components (9)

- [ ] T061 [P] [US3] Add component tests for 9 untested tools components in `solune/frontend/src/components/tools/*.test.tsx` (one test file per component)

### Tests for User Story 3 — UI Primitives (7)

- [ ] T062 [P] [US3] Add component tests for 7 untested UI primitives in `solune/frontend/src/components/ui/*.test.tsx` (one test file per component)

### Tests for User Story 3 — Settings Components (4)

- [ ] T063 [P] [US3] Add component tests for 4 untested settings components in `solune/frontend/src/components/settings/*.test.tsx` (one test file per component)

### Tests for User Story 3 — Pipeline Components (4)

- [ ] T064 [P] [US3] Add component tests for 4 untested pipeline components in `solune/frontend/src/components/pipeline/*.test.tsx` (one test file per component)

### Tests for User Story 3 — Chat Components (4)

- [ ] T065 [P] [US3] Add component tests for 4 untested chat components in `solune/frontend/src/components/chat/*.test.tsx` (one test file per component)

### Implementation for User Story 3

- [ ] T066 [US3] Update coverage thresholds in `solune/frontend/vitest.config.ts` — statements: 60, branches: 52, functions: 50, lines: 60
- [ ] T067 [US3] Run `npx vitest run --coverage` to validate all raised thresholds are met

**Checkpoint**: US3 complete — frontend coverage meets raised thresholds, enforced in CI

---

## Phase 6: User Story 4 — Expand Property-Based Testing (Priority: P2)

**Goal**: Add property-based tests for round-trip serialization, API validation edge cases, and migration idempotency

**Independent Test**: From `solune/backend/`, run `python -m pytest tests/property/ -v` and from `solune/frontend/`, run `npx vitest run --reporter=verbose -- "*.property.test"` to confirm all property tests pass

### Tests for User Story 4 — Backend Property Tests

- [ ] T068 [P] [US4] Expand round-trip serialization property tests for Agent, Pipeline, Chat models in `solune/backend/tests/property/test_model_roundtrips.py`
- [ ] T069 [P] [US4] Create API validation edge-case property tests in `solune/backend/tests/property/test_api_validation.py`
- [ ] T070 [P] [US4] Create migration idempotency property tests in `solune/backend/tests/property/test_migration_idempotency.py`

### Tests for User Story 4 — Frontend Property Tests

- [ ] T071 [P] [US4] Add property-based tests for agent component props in `solune/frontend/src/components/agents/AgentCard.property.test.ts`
- [ ] T072 [P] [US4] Add property-based tests for pipeline component props in `solune/frontend/src/components/pipeline/PipelineCard.property.test.ts`
- [ ] T073 [P] [US4] Add property-based tests for settings component props in `solune/frontend/src/components/settings/SettingsForm.property.test.ts`

### Implementation for User Story 4

- [ ] T074 [US4] Run full property test suites to confirm all new tests pass — backend: `python -m pytest tests/property/ -v`, frontend: `npx vitest run -- property`

**Checkpoint**: US4 complete — property test count increased from 13 to 19+ files

---

## Phase 7: User Story 5 — Integrate Accessibility Auditing in E2E Tests (Priority: P2)

**Goal**: Expand `@axe-core/playwright` usage from 2 E2E specs to 6+ specs covering auth, board, chat, and settings flows

**Independent Test**: From `solune/frontend/`, run `npx playwright test auth.spec.ts board-navigation.spec.ts chat-interaction.spec.ts settings-flow.spec.ts` and confirm axe-core a11y assertions pass in all target specs

### Tests for User Story 5

- [ ] T075 [P] [US5] Add axe-core a11y audit to auth flow in `solune/frontend/e2e/auth.spec.ts` — import AxeBuilder, add `should pass axe-core accessibility audit` test
- [ ] T076 [P] [US5] Add axe-core a11y audit to board navigation in `solune/frontend/e2e/board-navigation.spec.ts` — import AxeBuilder, add a11y test
- [ ] T077 [P] [US5] Add axe-core a11y audit to chat interaction in `solune/frontend/e2e/chat-interaction.spec.ts` — import AxeBuilder, add a11y test
- [ ] T078 [P] [US5] Add axe-core a11y audit to settings flow in `solune/frontend/e2e/settings-flow.spec.ts` — import AxeBuilder, add a11y test

### Implementation for User Story 5

- [ ] T079 [US5] Run `npx playwright test auth board-navigation chat-interaction settings-flow` to validate all a11y tests pass with zero violations
- [ ] T080 [US5] Document any axe-core rule exclusions for known false positives (if needed) as inline comments in each spec file

**Checkpoint**: US5 complete — axe-core a11y audits run in 6+ E2E specs (up from 2), zero violations

---

## Phase 8: User Story 6 — Remove Module-Level Singletons (Priority: P2)

**Goal**: Replace module-level singletons with accessor-function DI pattern in two service files

**Independent Test**: Run full CI suite and confirm all tests pass; `grep -rn "TODO(018-codebase-audit-refactor)" solune/backend/src/` returns no matches (exit code 1)

### Implementation for User Story 6

- [ ] T081 [US6] Audit all files importing `github_projects_service` singleton — identify all 17+ consumers in `solune/backend/src/`
- [ ] T082 [US6] Audit all files importing the agents singleton from `solune/backend/src/services/github_projects/agents.py`
- [ ] T083 [US6] Implement `get_github_projects_service()` accessor function in `solune/backend/src/services/github_projects/service.py` — replace lines 479–493 with accessor pattern per data-model.md E4
- [ ] T084 [US6] Implement `get_agents_service_instance()` accessor function in `solune/backend/src/services/github_projects/agents.py` — replace lines 399–413 with accessor pattern
- [ ] T085 [US6] Update `solune/backend/src/main.py` to register service instances on `app.state` using accessors
- [ ] T086 [US6] Update `solune/backend/src/dependencies.py` to use accessor function instead of direct import
- [ ] T087 [US6] Update `solune/backend/src/utils.py` to use accessor function (2 import sites at lines ~242, ~300)
- [ ] T088 [US6] Update `solune/backend/src/api/chores.py` to use accessor function (7 usage sites)
- [ ] T089 [US6] Update `solune/backend/src/api/board.py` to use accessor function (5 usage sites)
- [ ] T090 [US6] Update `solune/backend/src/api/chat.py` to use accessor function (6 usage sites)
- [ ] T091 [US6] Update remaining consumer files (background tasks, signal bridge, orchestrator) to use accessor functions
- [ ] T092 [US6] Update all affected test mocks to target the accessor function instead of the direct singleton
- [ ] T093 [US6] Remove `TODO(018-codebase-audit-refactor)` comment blocks from both `solune/backend/src/services/github_projects/service.py` and `solune/backend/src/services/github_projects/agents.py`
- [ ] T094 [US6] Run full backend test suite: `python -m pytest tests/ -q` to confirm no regressions

**Checkpoint**: US6 complete — singletons replaced with accessor pattern, zero TODO(018) markers remain

---

## Phase 9: User Story 7 — Upgrade Pre-Release Dependencies (Priority: P3)

**Goal**: Upgrade 8 pre-release dependencies to latest compatible versions with isolated CI validation

**Independent Test**: Run full CI suite after each upgrade and confirm no test regressions

### Implementation for User Story 7 — OpenTelemetry (Low Risk)

- [ ] T095 [P] [US7] Upgrade `opentelemetry-instrumentation-fastapi` to latest 0.x in `solune/backend/pyproject.toml`
- [ ] T096 [P] [US7] Upgrade `opentelemetry-instrumentation-httpx` to latest 0.x in `solune/backend/pyproject.toml`
- [ ] T097 [P] [US7] Upgrade `opentelemetry-instrumentation-sqlite3` to latest 0.x in `solune/backend/pyproject.toml`
- [ ] T098 [US7] Run CI validation after OpenTelemetry upgrades: `python -m pytest tests/ -q`

### Implementation for User Story 7 — Azure AI (Medium Risk)

- [ ] T099 [US7] Upgrade `azure-ai-inference` to latest 1.x version in `solune/backend/pyproject.toml`
- [ ] T100 [US7] Run CI validation after azure-ai-inference upgrade: `python -m pytest tests/ -q`

### Implementation for User Story 7 — Agent Framework (Medium Risk)

- [ ] T101 [P] [US7] Upgrade `agent-framework-core` to latest 1.x in `solune/backend/pyproject.toml`
- [ ] T102 [P] [US7] Upgrade `agent-framework-azure-ai` to latest 1.x in `solune/backend/pyproject.toml`
- [ ] T103 [P] [US7] Upgrade `agent-framework-github-copilot` to latest 1.x in `solune/backend/pyproject.toml`
- [ ] T104 [US7] Run CI validation after agent-framework upgrades: `python -m pytest tests/ -q`

### Implementation for User Story 7 — Copilot SDK (High Risk)

- [ ] T105 [US7] Upgrade `github-copilot-sdk` from `>=0.1.30,<1` to `>=1.0.17,<2` in `solune/backend/pyproject.toml` (line ~16)
- [ ] T106 [US7] Update type stubs in `solune/backend/src/typestubs/` if SDK v2 changes type signatures
- [ ] T107 [US7] Run full CI validation after Copilot SDK v2 upgrade: `python -m pytest tests/ -q`

**Checkpoint**: US7 complete — all 8 pre-release dependencies upgraded with zero regressions

---

## Phase 10: User Story 8 — Consolidate Stryker Mutation Configs (Priority: P3)

**Goal**: Merge 4 specialized Stryker configs into 1 unified config with `STRYKER_TARGET` env var

**Independent Test**: From `solune/frontend/`, run `STRYKER_TARGET=all npx stryker run` and verify mutation score matches the combined output of the previous separate config runs

### Implementation for User Story 8

- [ ] T108 [US8] Rewrite `solune/frontend/stryker.config.mjs` to support `STRYKER_TARGET` env var with profiles: `all` (default), `hooks-board`, `hooks-data`, `hooks-general`, `lib` — merge mutate patterns from all 4 specialized configs
- [ ] T109 [US8] Update `scripts` in `solune/frontend/package.json` — replace 4 specialized stryker scripts with target-based invocations using `STRYKER_TARGET` env var
- [ ] T110 [US8] Remove `solune/frontend/stryker-hooks-board.config.mjs`
- [ ] T111 [US8] Remove `solune/frontend/stryker-hooks-data.config.mjs`
- [ ] T112 [US8] Remove `solune/frontend/stryker-hooks-general.config.mjs`
- [ ] T113 [US8] Remove `solune/frontend/stryker-lib.config.mjs`
- [ ] T114 [US8] Validate unified config with each target: `STRYKER_TARGET=hooks-board npx stryker run`, `STRYKER_TARGET=hooks-data npx stryker run`, `STRYKER_TARGET=hooks-general npx stryker run`, `STRYKER_TARGET=lib npx stryker run`
- [ ] T115 [US8] Validate default target (`STRYKER_TARGET` unset) runs all mutation targets

**Checkpoint**: US8 complete — Stryker configs reduced from 5 to 1, all targets functional

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation

- [ ] T116 [P] Update `specs/019-harden/quickstart.md` to reflect new coverage thresholds and unified Stryker commands
- [ ] T117 [P] Update any documentation referencing the old Stryker config file names
- [ ] T118 Run full CI pipeline (`backend`, `frontend`, `e2e`, `docs-lint`, `contract-validation`, `build-validation`, `docker-build`) to confirm zero regressions across all jobs
- [ ] T119 Verify success criteria SC-001 through SC-009 from spec.md are all met

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — verification only
- **Foundational (Phase 2)**: No dependencies — bug 1.3 fix
- **US1 (Phase 3)**: Depends on Phase 2 (bug fix is the foundation)
- **US2 (Phase 4)**: Depends on Phase 2 (clean baseline after bug fix)
- **US3 (Phase 5)**: No dependency on US2 — can run in parallel
- **US4 (Phase 6)**: Depends on US2 and US3 being mostly complete (avoid merge conflicts)
- **US5 (Phase 7)**: No dependency on US2/US3 — can run in parallel
- **US6 (Phase 8)**: Depends on US2 complete (stable test suite for regression detection)
- **US7 (Phase 9)**: Depends on US2 and US6 complete (stable baseline for upgrade validation)
- **US8 (Phase 10)**: No dependencies — can start any time
- **Polish (Phase 11)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Bug fix — blocks all other stories (foundational)
- **US2 (P1)**: Backend coverage — independent, can run after US1
- **US3 (P1)**: Frontend coverage — independent, can run in parallel with US2
- **US4 (P2)**: Property tests — best after US2/US3 to avoid merge conflicts
- **US5 (P2)**: A11y integration — independent, can run in parallel with US2/US3
- **US6 (P2)**: Singleton refactor — needs stable test suite (after US2)
- **US7 (P3)**: Dependency upgrades — needs stable baseline (after US2 + US6)
- **US8 (P3)**: Stryker consolidation — fully independent, can start any time

### Within Each User Story

- Tests written first (where applicable)
- Configuration changes after tests are written and passing
- Full validation run at each checkpoint

### Parallel Opportunities

- **US2 + US3 + US5 + US8**: All four can proceed in parallel after Phase 2 (bug fix)
- **Within US2**: All 23 test tasks (T013–T035) are marked [P] — different test files, no conflicts
- **Within US3**: All 28 test tasks (T038–T065) are marked [P] — different component files
- **Within US4**: All 6 property test tasks (T068–T073) are marked [P]
- **Within US5**: All 4 a11y tasks (T075–T078) are marked [P] — different E2E spec files
- **Within US7**: OpenTelemetry packages (T095–T097) can upgrade in parallel; agent-framework packages (T101–T103) can upgrade in parallel
- **Within US8**: Config removal tasks (T110–T113) can execute in parallel after T108

---

## Parallel Example: User Story 2 (Backend Coverage)

```bash
# Launch all prompt template test tasks together (different files, no dependencies):
Task T013: "Add unit tests for agent instructions prompt"
Task T014: "Add unit tests for issue generation prompt"
Task T015: "Add unit tests for label classification prompt"
Task T016: "Add unit tests for plan instructions prompt"
Task T017: "Add unit tests for task generation prompt"
Task T018: "Add unit tests for transcript analysis prompt"

# Launch all MCP tool test tasks together (different files, no dependencies):
Task T023: "Add unit tests for MCP tool: activity"
Task T024: "Add unit tests for MCP tool: agents"
Task T025: "Add unit tests for MCP tool: apps"
Task T026: "Add unit tests for MCP tool: chat"
Task T027: "Add unit tests for MCP tool: pipelines"
Task T028: "Add unit tests for MCP tool: projects"
Task T029: "Add unit tests for MCP tool: tasks"
Task T030: "Add unit tests for MCP server auth"
```

---

## Parallel Example: User Story 3 (Frontend Coverage)

```bash
# Launch all chores component tests together:
Task T038–T050: 13 chores component tests (all [P], different .test.tsx files)

# Launch all agents component tests together:
Task T051–T060: 10 agents component tests (all [P], different .test.tsx files)

# Launch remaining category batches in parallel:
Task T061: Tools components (9 tests)
Task T062: UI primitives (7 tests)
Task T063: Settings components (4 tests)
Task T064: Pipeline components (4 tests)
Task T065: Chat components (4 tests)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verification)
2. Complete Phase 2: Foundational (bug 1.3 fix)
3. Complete Phase 3: User Story 1 (regression tests for bug fix)
4. **STOP and VALIDATE**: Run `python -m pytest tests/unit/test_agents_service.py -k "extract_agent_preview" -v`
5. Deploy if ready — malformed configs are safely handled

### Incremental Delivery

1. **Bug fix** (US1): Immediate reliability improvement
2. **Backend coverage** (US2) + **Frontend coverage** (US3): Quality gates enforced → Deploy
3. **Property tests** (US4) + **A11y** (US5): Deeper testing → Deploy
4. **Singleton refactor** (US6): Maintainability improvement → Deploy
5. **Dependency upgrades** (US7): Currency improvement → Deploy (each upgrade is a separate commit)
6. **Stryker consolidation** (US8): DX improvement → Deploy

### Parallel Team Strategy

With multiple developers after Phase 2 (bug fix) is complete:

- **Developer A**: US2 (backend coverage — 23 test files)
- **Developer B**: US3 (frontend coverage — 28+ test files)
- **Developer C**: US5 (a11y — 4 E2E specs) + US8 (Stryker — config work)
- **Developer D**: US4 (property tests — 6 files, after A/B mostly done)
- **Sequential**: US6 (singleton refactor) → US7 (dependency upgrades) — requires stable baseline

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tasks** | 119 (T001–T119) |
| **US1 tasks** | 4 (T009–T012) |
| **US2 tasks** | 25 (T013–T037) |
| **US3 tasks** | 30 (T038–T067) |
| **US4 tasks** | 7 (T068–T074) |
| **US5 tasks** | 6 (T075–T080) |
| **US6 tasks** | 14 (T081–T094) |
| **US7 tasks** | 13 (T095–T107) |
| **US8 tasks** | 8 (T108–T115) |
| **Setup/Foundational** | 8 (T001–T008) |
| **Polish** | 4 (T116–T119) |
| **Parallel opportunities** | 80+ tasks marked [P] |
| **Suggested MVP scope** | US1 only (Phase 2–3, tasks T005–T012) |

## Notes

- [P] tasks = different files, no dependencies — safe to parallelize
- [Story] label maps each task to a specific user story for traceability
- Each user story is independently completable and testable at its checkpoint
- Bugs 1.1, 1.2, and 3.4 are verified resolved — no tasks needed
- Bug 1.3 is the only code fix; everything else is tests, config, and refactoring
- Commit after each task or logical group
- Stop at any checkpoint to validate the story independently
