# Tasks: Harden Phase 2

**Input**: Design documents from `/specs/1240-harden-phase-2/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/coverage-thresholds.yaml ✅, quickstart.md ✅

**Tests**: Tests ARE the deliverable for this feature — every task either writes tests or updates test infrastructure. This is a test-only workstream with no runtime code changes.

**Organization**: Tasks are grouped by user story (workstream) to enable independent implementation and testing. All four workstreams (US1–US4) are independent and can run in parallel after the foundational phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Web app monorepo**: `solune/backend/` (Python 3.13, FastAPI, pytest), `solune/frontend/` (TypeScript ~6.0, React 19, Vitest, Playwright)
- **Backend tests**: `solune/backend/tests/unit/`, `solune/backend/tests/property/`
- **Frontend tests**: `solune/frontend/src/components/*/__tests__/`, `solune/frontend/src/lib/`
- **E2E tests**: `solune/frontend/e2e/`

---

## Phase 1: Setup (Coverage Audit & Baseline)

**Purpose**: Establish current coverage baselines and identify specific files/components to target

- [ ] T001 Run backend coverage audit (`pytest --cov=src --cov-report=term-missing`) and identify the 30 lowest-coverage files in solune/backend/
- [ ] T002 [P] Run frontend coverage audit (`npx vitest run --coverage`) and identify all untested components across chores, agents, tools, settings, ui, pipeline in solune/frontend/
- [ ] T003 [P] Review existing axe-core patterns in solune/frontend/e2e/ui.spec.ts and solune/frontend/e2e/protected-routes.spec.ts to confirm integration approach

---

## Phase 2: Foundational (Verify Test Infrastructure)

**Purpose**: Confirm existing test infrastructure supports all workstreams — no new frameworks or tools needed

**⚠️ CRITICAL**: All workstreams reuse existing infrastructure. This phase validates readiness, not creation.

- [ ] T004 Verify backend test fixtures — confirm conftest.py fixtures, Hypothesis profiles (dev: 20 examples, CI: 200), and asyncio_mode=auto in solune/backend/pyproject.toml and solune/backend/tests/conftest.py
- [ ] T005 [P] Verify frontend test utilities — confirm @/test/test-utils.tsx wrapper (OnboardingProvider, TooltipProvider), vi.mock() patterns, and @fast-check/vitest integration in solune/frontend/src/test/test-utils.tsx and solune/frontend/vitest.config.ts
- [ ] T006 [P] Verify E2E fixtures — confirm fixtures.ts (unauthenticated) and authenticated-fixtures.ts (authenticated + mockApi) are functional in solune/frontend/e2e/

**Checkpoint**: Test infrastructure verified — all four user story workstreams can now begin in parallel

---

## Phase 3: User Story 1 — Backend Test Depth (Priority: P1) 🎯 MVP

**Goal**: Raise backend coverage from 75% to 80% by deepening tests in ~35 existing test files across 5 module groups. Focus on untested branches, error paths, guard clauses, and async exception handlers.

**Independent Test**: Run `pytest --cov=src --cov-fail-under=80` — all tests pass with ≥80% combined coverage.

### Prompts Module Tests

- [ ] T007 [P] [US1] Deepen prompt template tests — add edge cases for empty inputs, special characters, and malformed context to solune/backend/tests/unit/test_prompts_agent_instructions.py
- [ ] T008 [P] [US1] Deepen prompt template tests — add boundary tests for template variable substitution failures to solune/backend/tests/unit/test_prompts_issue_generation.py
- [ ] T009 [P] [US1] Deepen prompt template tests — add edge cases for ambiguous labels and empty classification input to solune/backend/tests/unit/test_prompts_label_classification.py
- [ ] T010 [P] [US1] Deepen prompt template tests — add error path tests for missing plan context to solune/backend/tests/unit/test_prompts_plan_instructions.py
- [ ] T011 [P] [US1] Deepen prompt template tests — add edge cases for empty task lists and special characters to solune/backend/tests/unit/test_prompts_task_generation.py
- [ ] T012 [P] [US1] Deepen prompt template tests — add edge cases for empty transcripts and malformed input to solune/backend/tests/unit/test_prompts_transcript_analysis.py

### Copilot Polling Module Tests

- [ ] T013 [P] [US1] Deepen copilot polling tests — add recovery path tests, timeout handling, and async exception handlers across solune/backend/tests/unit/test_copilot_polling_*.py (11 files covering state_validation, recovery, pipeline_state_service, and internal modules)

### MCP Server Tools Tests

- [ ] T014 [P] [US1] Deepen MCP tools tests — add error response, pagination boundary, and auth failure tests to solune/backend/tests/unit/test_mcp_tool_activity.py and solune/backend/tests/unit/test_mcp_tool_agents.py
- [ ] T015 [P] [US1] Deepen MCP tools tests — add error response and edge case tests to solune/backend/tests/unit/test_mcp_tool_apps.py and solune/backend/tests/unit/test_mcp_tool_chat.py
- [ ] T016 [P] [US1] Deepen MCP tools tests — add error response and pagination tests to solune/backend/tests/unit/test_mcp_tool_chores.py and solune/backend/tests/unit/test_mcp_tool_pipelines.py
- [ ] T017 [P] [US1] Deepen MCP tools tests — add error response and edge case tests to solune/backend/tests/unit/test_mcp_tool_projects.py and solune/backend/tests/unit/test_mcp_tool_tasks.py

### Chores Service Tests

- [ ] T018 [P] [US1] Deepen chores service tests — add scheduler edge cases (overlapping schedules, timezone boundaries, missed triggers) to solune/backend/tests/unit/test_chores_scheduler.py
- [ ] T019 [P] [US1] Deepen chores service tests — add template builder variations (empty templates, nested variables, special characters) to solune/backend/tests/unit/test_chores_template_builder.py
- [ ] T020 [P] [US1] Deepen chores service tests — add edge cases to solune/backend/tests/unit/test_chores_chat.py, test_chores_counter.py, and test_chores_service.py

### Middleware Tests

- [ ] T021 [P] [US1] Deepen middleware tests — add missing header propagation and correlation ID edge cases to solune/backend/tests/unit/test_middleware_request_id.py
- [ ] T022 [P] [US1] Deepen middleware tests — add rate limit boundary tests (exactly at limit, burst patterns, reset timing) to solune/backend/tests/unit/test_middleware_rate_limit.py
- [ ] T023 [P] [US1] Deepen middleware tests — add CSP header variation tests and policy override scenarios to solune/backend/tests/unit/test_middleware_csp.py
- [ ] T024 [P] [US1] Deepen middleware tests — add edge cases for CSRF token validation and admin guard role checks to solune/backend/tests/unit/test_middleware_csrf.py and solune/backend/tests/unit/test_middleware_admin_guard.py

**Checkpoint**: Backend coverage should now meet or exceed 80%. Run `pytest --cov=src --cov-fail-under=80` to verify.

---

## Phase 4: User Story 2 — Frontend Component Test Coverage (Priority: P1)

**Goal**: Add unit tests for ~69 untested frontend components to raise coverage thresholds (statements 50→60%, branches 44→52%, functions 41→50%, lines 50→60%). Each test file covers rendering, primary user interactions, and key state changes.

**Independent Test**: Run `npx vitest run --coverage` — all tests pass with statements ≥60%, branches ≥52%, functions ≥50%, lines ≥60%.

### Pipeline Component Tests (16 components — highest gap count)

- [ ] T025 [P] [US2] Create tests for ModelSelector, ParallelStageGroup, and PipelineStagesOverview in solune/frontend/src/components/pipeline/__tests__/
- [ ] T026 [P] [US2] Create tests for remaining 13 partially-tested pipeline components — add missing branch and interaction coverage in solune/frontend/src/components/pipeline/__tests__/

### Chores Component Tests (13 components — user-critical flow)

- [ ] T027 [P] [US2] Create tests for AddChoreModal, ChoreCard, ChoreChatFlow, and ChoreInlineEditor in solune/frontend/src/components/chores/__tests__/
- [ ] T028 [P] [US2] Create tests for ChoreScheduleConfig, ChoresGrid, ChoresPanel, and ChoresSaveAllBar in solune/frontend/src/components/chores/__tests__/
- [ ] T029 [P] [US2] Create tests for ChoresSpotlight, ChoresToolbar, ConfirmChoreModal, FeaturedRitualsPanel, and PipelineSelector in solune/frontend/src/components/chores/__tests__/

### UI Component Tests (13 components — shared primitives)

- [ ] T030 [P] [US2] Create tests for alert-dialog, character-counter, confirmation-dialog, and copy-button in solune/frontend/src/components/ui/__tests__/
- [ ] T031 [P] [US2] Create tests for dialog, hover-card, keyboard-shortcut-modal, and popover in solune/frontend/src/components/ui/__tests__/
- [ ] T032 [P] [US2] Create tests for skeleton, tooltip, and remaining 3 partially-tested UI components in solune/frontend/src/components/ui/__tests__/

### Agents Component Tests (11 components — core feature)

- [ ] T033 [P] [US2] Create tests for AddAgentModal, AgentAvatar, AgentCard, and AgentChatFlow in solune/frontend/src/components/agents/__tests__/
- [ ] T034 [P] [US2] Create tests for AgentIconCatalog, AgentIconPickerModal, AgentInlineEditor, and AgentsPanel in solune/frontend/src/components/agents/__tests__/
- [ ] T035 [P] [US2] Create tests for BulkModelUpdateDialog, InstallConfirmDialog, and ToolsEditor in solune/frontend/src/components/agents/__tests__/

### Tools Component Tests (9 components — MCP integration)

- [ ] T036 [P] [US2] Create tests for EditRepoMcpModal, GitHubMcpConfigGenerator, and McpPresetsGallery in solune/frontend/src/components/tools/__tests__/
- [ ] T037 [P] [US2] Create tests for RepoConfigPanel, ToolCard, ToolChips, ToolSelectorModal, ToolsPanel, and UploadMcpModal in solune/frontend/src/components/tools/__tests__/

### Settings Component Tests (7 components — user preferences)

- [ ] T038 [P] [US2] Create tests for AIPreferences, PrimarySettings, ProjectSettings, and SignalConnection in solune/frontend/src/components/settings/__tests__/
- [ ] T039 [P] [US2] Create tests for remaining 3 partially-tested settings components — add missing branch and interaction coverage in solune/frontend/src/components/settings/__tests__/

**Checkpoint**: Frontend coverage should now meet or exceed statements 60%, branches 52%, functions 50%, lines 60%. Run `npx vitest run --coverage` to verify.

---

## Phase 5: User Story 3 — Property-Based Testing Expansion (Priority: P2)

**Goal**: Expand property-based testing from 15 files (9 backend + 6 frontend) to 21 files by adding round-trip serialization, API validation edge cases, and migration/state idempotency tests. Target: ≥30 distinct properties across all new files.

**Independent Test**: Run `pytest tests/property/ -v` (backend) and `npx vitest run --testPathPattern="property"` (frontend) — all new property tests pass.

### Backend Property Tests (Hypothesis)

- [ ] T040 [P] [US3] Create round-trip serialization property tests — generate arbitrary Pydantic model instances and verify model → dict → model equality for API request/response types in solune/backend/tests/property/test_api_model_roundtrips.py
- [ ] T041 [P] [US3] Create API validation edge case property tests — test boundary values, Unicode strings, empty strings, and max-length field constraints in solune/backend/tests/property/test_api_validation_properties.py
- [ ] T042 [P] [US3] Create migration idempotency property tests — verify pipeline config migrations applied twice produce identical results in solune/backend/tests/property/test_migration_idempotency.py

### Frontend Property Tests (fast-check)

- [ ] T043 [P] [US3] Create API type round-trip serialization property tests — verify TypeScript API interfaces survive JSON.parse(JSON.stringify()) round-trip in solune/frontend/src/lib/apiTypes.property.test.ts
- [ ] T044 [P] [US3] Create form validation edge case property tests — test input boundaries, Unicode, and special characters against form validators in solune/frontend/src/lib/formValidation.property.test.ts
- [ ] T045 [P] [US3] Create pipeline state transition invariant property tests — verify all state transition sequences reach valid terminal states in solune/frontend/src/lib/pipelineState.property.test.ts

**Checkpoint**: Property test suite expanded to 21 files with ≥30 distinct properties. Run full property test suites to verify.

---

## Phase 6: User Story 4 — Accessibility Auditing in E2E Tests (Priority: P2)

**Goal**: Add @axe-core/playwright accessibility audits to 4 user-critical E2E flows (auth, board, chat, settings), checking WCAG 2.1 AA compliance (wcag2a, wcag2aa, wcag21a, wcag21aa tags).

**Independent Test**: Run `npx playwright test` — all E2E specs pass with zero WCAG 2.1 AA violations in audited pages.

### Accessibility Audit Integration

- [ ] T046 [P] [US4] Add @axe-core/playwright a11y audit to authentication flow — import AxeBuilder, audit /login page after load, assert zero WCAG 2.1 AA violations in solune/frontend/e2e/auth.spec.ts (uses fixtures.ts)
- [ ] T047 [P] [US4] Add @axe-core/playwright a11y audit to board navigation flow — audit /projects board view after authenticated load, assert zero violations in solune/frontend/e2e/board-navigation.spec.ts (uses authenticated-fixtures.ts)
- [ ] T048 [P] [US4] Add @axe-core/playwright a11y audit to chat interaction flow — audit /projects chat view after authenticated load, assert zero violations in solune/frontend/e2e/chat-interaction.spec.ts (uses authenticated-fixtures.ts)
- [ ] T049 [P] [US4] Add @axe-core/playwright a11y audit to settings management flow — audit /settings page after authenticated load, assert zero violations in solune/frontend/e2e/settings-flow.spec.ts (uses authenticated-fixtures.ts)

**Checkpoint**: All 4 target E2E specs now include accessibility audits. Total axe-core coverage: 6 specs (2 existing + 4 new).

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Bump coverage thresholds (MUST be final step after all tests pass), validate full CI, and confirm documentation accuracy

- [ ] T050 Raise backend coverage threshold from 75 to 80 — update `fail_under = 80` in solune/backend/pyproject.toml under [tool.coverage.report]
- [ ] T051 [P] Raise frontend coverage thresholds — update statements: 60, branches: 52, functions: 50, lines: 60 in solune/frontend/vitest.config.ts under test.coverage.thresholds
- [ ] T052 Run full CI validation — confirm all 9 CI jobs (Backend, Backend Advanced, Frontend, Frontend E2E, Docs Lint, Diagrams, Contract Validation, Build Validation, Docker Build) pass with updated thresholds
- [ ] T053 [P] Validate quickstart.md — execute all commands in specs/1240-harden-phase-2/quickstart.md and confirm expected outputs

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — verifies infrastructure readiness
- **User Stories (Phase 3–6)**: All depend on Foundational phase completion
  - All four user stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order: US1 (P1) → US2 (P1) → US3 (P2) → US4 (P2)
- **Polish (Phase 7)**: Depends on ALL user stories being complete — threshold bumps MUST be last

### User Story Dependencies

- **US1 — Backend Test Depth (P1)**: Can start after Foundational (Phase 2). No dependencies on other stories.
- **US2 — Frontend Component Coverage (P1)**: Can start after Foundational (Phase 2). No dependencies on other stories.
- **US3 — Property-Based Testing (P2)**: Can start after Foundational (Phase 2). No dependencies on other stories.
- **US4 — Accessibility E2E (P2)**: Can start after Foundational (Phase 2). No dependencies on other stories.

### Within Each User Story

- **US1**: All 5 module groups (prompts, copilot_polling, mcp_tools, chores, middleware) can be worked in parallel — they target different files
- **US2**: All 6 component categories (pipeline, chores, ui, agents, tools, settings) can be worked in parallel — they target different directories
- **US3**: All 6 property test files can be created in parallel — they are independent files
- **US4**: All 4 E2E spec modifications can be done in parallel — they are independent spec files

### Parallel Opportunities

- **Phase 1**: T001, T002, T003 can run in parallel (different ecosystems)
- **Phase 2**: T004, T005, T006 can run in parallel (different ecosystems)
- **Phase 3 (US1)**: T007–T012 (prompts) all in parallel; T014–T017 (MCP tools) all in parallel; T018–T020 (chores) all in parallel; T021–T024 (middleware) all in parallel
- **Phase 4 (US2)**: T025–T039 all in parallel (each targets a different component category or batch)
- **Phase 5 (US3)**: T040–T045 all in parallel (6 independent test files)
- **Phase 6 (US4)**: T046–T049 all in parallel (4 independent spec files)
- **Phase 7**: T050 and T051 in parallel (different config files); T052 must wait for both

---

## Parallel Example: User Story 1

```text
# Launch all prompts tests in parallel (different files, no dependencies):
T007: "Deepen tests for agent_instructions in tests/unit/test_prompts_agent_instructions.py"
T008: "Deepen tests for issue_generation in tests/unit/test_prompts_issue_generation.py"
T009: "Deepen tests for label_classification in tests/unit/test_prompts_label_classification.py"
T010: "Deepen tests for plan_instructions in tests/unit/test_prompts_plan_instructions.py"
T011: "Deepen tests for task_generation in tests/unit/test_prompts_task_generation.py"
T012: "Deepen tests for transcript_analysis in tests/unit/test_prompts_transcript_analysis.py"

# Launch all middleware tests in parallel (different files):
T021: "Deepen tests for request_id in tests/unit/test_middleware_request_id.py"
T022: "Deepen tests for rate_limit in tests/unit/test_middleware_rate_limit.py"
T023: "Deepen tests for csp in tests/unit/test_middleware_csp.py"
T024: "Deepen tests for csrf + admin_guard in tests/unit/test_middleware_csrf.py + test_middleware_admin_guard.py"
```

## Parallel Example: User Story 2

```text
# Launch all frontend component category batches in parallel (different directories):
T025-T026: "Pipeline tests in components/pipeline/__tests__/"
T027-T029: "Chores tests in components/chores/__tests__/"
T030-T032: "UI tests in components/ui/__tests__/"
T033-T035: "Agents tests in components/agents/__tests__/"
T036-T037: "Tools tests in components/tools/__tests__/"
T038-T039: "Settings tests in components/settings/__tests__/"
```

## Parallel Example: User Story 3

```text
# Launch all property test files in parallel (independent files):
T040: "Backend round-trip serialization in tests/property/test_api_model_roundtrips.py"
T041: "Backend API validation in tests/property/test_api_validation_properties.py"
T042: "Backend migration idempotency in tests/property/test_migration_idempotency.py"
T043: "Frontend API type round-trip in src/lib/apiTypes.property.test.ts"
T044: "Frontend form validation in src/lib/formValidation.property.test.ts"
T045: "Frontend pipeline state in src/lib/pipelineState.property.test.ts"
```

## Parallel Example: User Story 4

```text
# Launch all a11y audit additions in parallel (independent spec files):
T046: "Auth a11y audit in e2e/auth.spec.ts"
T047: "Board a11y audit in e2e/board-navigation.spec.ts"
T048: "Chat a11y audit in e2e/chat-interaction.spec.ts"
T049: "Settings a11y audit in e2e/settings-flow.spec.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (audit baselines)
2. Complete Phase 2: Foundational (verify infrastructure)
3. Complete Phase 3: User Story 1 — Backend Test Depth
4. **STOP and VALIDATE**: Run `pytest --cov=src --cov-fail-under=80` independently
5. Backend coverage gate is secured — deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Infrastructure verified
2. Add US1 (Backend Tests) → Run `pytest --cov=src --cov-fail-under=80` → ✅ Backend secured
3. Add US2 (Frontend Tests) → Run `npx vitest run --coverage` → ✅ Frontend secured
4. Add US3 (Property Tests) → Run property test suites → ✅ Data boundaries hardened
5. Add US4 (A11y Audits) → Run `npx playwright test` → ✅ Accessibility monitored
6. Bump all thresholds (Phase 7) → Run full CI → ✅ Thresholds enforced
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers after Phase 2 completes:

- **Developer A**: US1 — Backend Test Depth (prompts, copilot_polling, MCP tools, chores, middleware)
- **Developer B**: US2 — Frontend Component Tests (pipeline, chores, ui, agents, tools, settings)
- **Developer C**: US3 — Property-Based Testing (3 backend + 3 frontend files)
- **Developer D**: US4 — Accessibility E2E (4 spec file modifications)
- Stories complete and integrate independently; threshold bumps happen after all merge

---

## Summary

| Metric | Value |
|---|---|
| **Total tasks** | 53 |
| **US1 (Backend Test Depth)** | 18 tasks (T007–T024) |
| **US2 (Frontend Component Coverage)** | 15 tasks (T025–T039) |
| **US3 (Property-Based Testing)** | 6 tasks (T040–T045) |
| **US4 (Accessibility E2E)** | 4 tasks (T046–T049) |
| **Setup + Foundational** | 6 tasks (T001–T006) |
| **Polish** | 4 tasks (T050–T053) |
| **Parallel opportunities** | 49 of 53 tasks marked [P] |
| **Suggested MVP scope** | US1 only (Phase 3) — secures backend coverage gate |
| **Independent stories** | All 4 user stories are fully independent |

### Format Validation

✅ All 53 tasks follow the required checklist format: `- [ ] [TaskID] [P?] [Story?] Description with file path`
✅ Setup/Foundational/Polish tasks have NO story label
✅ User story tasks (T007–T049) have correct [US1]/[US2]/[US3]/[US4] labels
✅ All tasks include specific file paths
✅ [P] marker used only for tasks targeting different files with no incomplete dependencies

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Threshold bumps (T050, T051) are the LAST tasks — never bump before all tests pass
- All workstreams are independent — zero cross-story dependencies
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- TypeScript 6.0 note: Use explicit initialization (`let x: T = null`) instead of definite assignment (`let x!: T`) for nullable types to avoid TS2454
