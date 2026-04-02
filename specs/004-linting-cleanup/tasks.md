# Tasks: Linting Clean Up

**Input**: Design documents from `/specs/004-linting-cleanup/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md, contracts/

**Tests**: Tests are in scope — the spec mandates type-check gates and test suppression cleanup (FR-001 through FR-012).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/frontend/src/`
- **Tests**: `solune/backend/tests/`, `solune/frontend/src/**/*.test.{ts,tsx}`
- **CI/Config**: `.github/workflows/ci.yml`, `solune/.pre-commit-config.yaml`, `solune/scripts/pre-commit`

## Phase 1: Setup (Audit & Baseline)

**Purpose**: Verify current suppression inventory and confirm existing CI gates pass before any changes.

- [ ] T001 Audit backend source suppressions — confirm ~46 `# type: ignore` and ~9 `# pyright:` directives in solune/backend/src/ using grep
- [ ] T002 [P] Audit backend test suppressions — confirm ~28 `# type: ignore` comments in solune/backend/tests/ using grep
- [ ] T003 [P] Audit frontend source and test suppressions — confirm ~18 production and ~51 test suppression matches in solune/frontend/src/ using grep
- [ ] T004 Verify existing CI gates pass on the current branch before making changes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ Note**: For this feature, User Story 1 (Phase 3) serves as the foundational blocking prerequisite. All subsequent user stories depend on the type-check gates established in Phase 3. No separate foundational tasks are needed.

**Checkpoint**: Proceed directly to Phase 3 (US1).

---

## Phase 3: User Story 1 — Test Type-Check Gate Expansion (Priority: P1) 🎯 MVP

**Goal**: Add dedicated backend and frontend test type-check configurations, wire them into CI and pre-commit, so test type errors become visible before merge.

**Independent Test**: Add a deliberate type error to a backend test file and a frontend test file; verify that both CI steps and pre-commit hooks fail with a clear diagnostic pointing to the offending line.

### Implementation for User Story 1

- [ ] T005 [US1] Create frontend test type-check configuration in solune/frontend/tsconfig.test.json — extend tsconfig.json, include all src files (remove test exclusions), add vitest/globals types
- [ ] T006 [US1] Add `type-check:test` npm script to solune/frontend/package.json — command: `tsc --noEmit -p tsconfig.test.json`
- [ ] T007 [US1] Add backend and frontend test type-check CI steps to .github/workflows/ci.yml — backend: `uv run pyright tests` (working-directory: solune/backend), frontend: `npm run type-check:test` (working-directory: solune/frontend); both as distinct steps with independent failure reporting
- [ ] T008 [US1] Add backend-pyright-tests and frontend-typecheck-tests hooks to solune/.pre-commit-config.yaml — backend: `bash -c 'cd solune/backend && pyright tests'` on `^solune/backend/.*\.py$`, frontend: `bash -c 'cd solune/frontend && npx tsc --noEmit -p tsconfig.test.json'` on `^solune/frontend/.*\.(ts|tsx)$`
- [ ] T009 [US1] Add test type-check steps to solune/scripts/pre-commit — add backend pyright tests and frontend tsc test steps after existing type-check steps
- [ ] T010 [US1] Update testing documentation with new type-check commands in solune/docs/testing.md — document `uv run pyright tests` and `npm run type-check:test`
- [ ] T011 [US1] Verify backend test type-check runs and reports current errors — run `uv run pyright tests` in solune/backend/ and confirm diagnostic output
- [ ] T012 [US1] Verify frontend test type-check runs and reports current errors — run `npm run type-check:test` in solune/frontend/ and confirm diagnostic output

**Checkpoint**: At this point, test type errors are visible in CI and pre-commit. All subsequent cleanup phases can be verified against these gates.

---

## Phase 4: User Story 2 — Backend Source Suppression Removal (Priority: P2)

**Goal**: Remove all ~55 `# type: ignore` comments and `# pyright:` file-level directives from authored backend source code under `solune/backend/src/`, replacing them with properly typed constructs. Fix any runtime bugs exposed by the removal.

**Independent Test**: Run `uv run pyright src` in `solune/backend/` with zero `# type: ignore` or `# pyright:` directives remaining in authored source; verify clean exit. Run `uv run pytest tests/unit/ -q` to confirm no regressions.

### Group 1: asyncio.Task Type Parameters (7 suppressions)

- [ ] T013 [US2] Add `asyncio.Task[None]` or `asyncio.Task[T]` type parameters to bare `asyncio.Task` in solune/backend/src/services/task_registry.py (5 suppressions)
- [ ] T014 [P] [US2] Add asyncio.Task type parameter in solune/backend/src/services/model_fetcher.py (1 suppression)
- [ ] T015 [P] [US2] Add asyncio.Task type parameter and fix cache generic return type in solune/backend/src/services/github_projects/service.py (2 suppressions — 1 asyncio.Task + 1 cache)

### Group 2: Cache Generic Return Values (7 remaining suppressions)

- [ ] T016 [US2] Make LRUCache/TTLCache generic with `Generic[V]` or add explicit `typing.cast()` at entry/exit points in solune/backend/src/services/cache.py (6 suppressions)
- [ ] T017 [P] [US2] Fix cache generic return value with cast() or TypeVar bound in solune/backend/src/utils.py (1 suppression)

### Group 3: OTel Typing Stubs (7 suppressions)

- [ ] T018 [P] [US2] Add return type annotations (`-> None`, `-> T`), proper base class inheritance, and parameter types to `_RequestIDSpanProcessor`, `_NoOpTracer`, `_NoOpMeter` in solune/backend/src/services/otel_setup.py (7 suppressions)

### Group 4: Optional/Vendor Import Suppressions (7 suppressions)

- [ ] T019 [US2] Fix optional imports with `TYPE_CHECKING` guards, remove inline pyright directive, and fix return type annotation in solune/backend/src/services/completion_providers.py (6 suppressions — 4 optional import + 1 pyright directive + 1 return type)
- [ ] T020 [P] [US2] Fix optional import with `TYPE_CHECKING` guard in solune/backend/src/services/agent_provider.py (1 suppression)

### Group 5: Pyright File-Level Directives (8 directives)

- [ ] T021 [P] [US2] Remove `# pyright: reportAttributeAccessIssue=false` file-level directives from 8 modules in solune/backend/src/services/github_projects/ — board.py, repository.py, branches.py, agents.py, projects.py, copilot.py, issues.py, pull_requests.py; add narrow per-line `# pyright: ignore[reportAttributeAccessIssue]` with comment only where genuinely needed

### Group 6: Config/Dynamic Boundary Suppressions (5 suppressions)

- [ ] T022 [US2] Create `RequestIdLogRecord` protocol extending `logging.LogRecord` with `request_id` attribute, fix suppressions in solune/backend/src/logging_utils.py (3 suppressions)
- [ ] T023 [P] [US2] Fix Settings construction typing — use narrow `# pyright: ignore[reportCallIssue]` with Pydantic explanation or add `@classmethod` factory in solune/backend/src/config.py (1 suppression)
- [ ] T024 [P] [US2] Fix frozen model field mutation — use `object.__setattr__()` or proper setter in solune/backend/src/services/workflow_orchestrator/config.py (1 suppression)

### Group 7: Row Indexing / Dict Operations (6 suppressions)

- [ ] T025 [US2] Fix row indexing type suppressions in solune/backend/src/services/metadata_service.py (3 suppressions)
- [ ] T026 [P] [US2] Fix dict.get argument typing in solune/backend/src/services/agents/service.py (1 suppression)
- [ ] T027 [P] [US2] Fix dict iteration typing in solune/backend/src/services/tools/service.py (1 suppression)
- [ ] T028 [P] [US2] Fix rate-limit handler typing in solune/backend/src/main.py (1 suppression)

### Group 8: Assignment / Return Type (3 suppressions)

- [ ] T029 [US2] Fix assignment type suppressions in solune/backend/src/api/chat.py (2 suppressions)
- [ ] T030 [P] [US2] Fix agent mapping return type in solune/backend/src/api/workflow.py (1 suppression)

### Verification for User Story 2

- [ ] T031 [US2] Verify zero backend source suppressions — grep for `# type: ignore` and `# pyright:` in solune/backend/src/; run `uv run pyright src` and confirm clean exit
- [ ] T032 [US2] Run backend linting and test suite — `uv run ruff check src && uv run ruff format --check src && uv run pytest tests/unit/ -q --tb=short` in solune/backend/

**Checkpoint**: All backend source suppressions removed. Type checker validates every expression in production code.

---

## Phase 5: User Story 3 — Backend Test Suppression Removal (Priority: P3)

**Goal**: Remove all ~28 `# type: ignore` comments from authored backend test code under `solune/backend/tests/`, replacing loosely typed fakes with typed helpers conforming to production interfaces.

**Independent Test**: Run `uv run pyright tests` in `solune/backend/` with zero `# type: ignore` comments remaining in test code; verify clean exit. Run `uv run pytest tests/ -q` to confirm all tests pass.

### Implementation for User Story 3

- [ ] T033 [US3] Replace `Settings()` calls with `model_construct()` or explicit required kwargs in solune/backend/tests/integration/test_production_mode.py (6 suppressions)
- [ ] T034 [US3] Create typed `FakeL1Cache` / `FakePipelineState` dataclass helpers and replace untyped fakes in solune/backend/tests/unit/test_metadata_service.py (8 suppressions)
- [ ] T035 [P] [US3] Fix `retry_after` attribute and mock attr-defined suppression in solune/backend/tests/unit/test_api_board.py (2 suppressions)
- [ ] T036 [US3] Reuse `RequestIdLogRecord` protocol from T022 and fix LogRecord attribute suppressions in solune/backend/tests/unit/test_logging_utils.py (5 suppressions)
- [ ] T037 [P] [US3] Fix frozen field mutation with `object.__setattr__()` or `model_construct()` in solune/backend/tests/unit/test_polling_loop.py (1 suppression)
- [ ] T038 [P] [US3] Fix generator yield typing in solune/backend/tests/unit/test_template_files.py (1 suppression)
- [ ] T039 [P] [US3] Fix TypedDict typing with dict literal or spread in solune/backend/tests/unit/test_pipeline_state_store.py (1 suppression)
- [ ] T040 [P] [US3] Fix frozen field mutation in solune/backend/tests/unit/test_transcript_detector.py (1 suppression)
- [ ] T041 [P] [US3] Fix frozen field mutation in solune/backend/tests/unit/test_agent_output.py (1 suppression)
- [ ] T042 [US3] Replace direct method-assign with `unittest.mock.patch.object()` in solune/backend/tests/concurrency/test_transaction_safety.py (2 suppressions)

### Verification for User Story 3

- [ ] T043 [US3] Verify zero backend test suppressions — grep for `# type: ignore` in solune/backend/tests/; run `uv run pyright tests` and confirm clean exit
- [ ] T044 [US3] Run full backend test suite — `uv run pytest tests/ -q --tb=short` in solune/backend/ to confirm zero regressions

**Checkpoint**: All backend test suppressions removed. Backend test type-checking can be permanently enabled in CI.

---

## Phase 6: User Story 4 — Frontend Production Suppression Removal (Priority: P4)

**Goal**: Remove all ~18 production suppressions (`@ts-expect-error`, `as unknown as`, `eslint-disable`) from authored frontend source files under `solune/frontend/src/` (excluding test files), replacing them with type-safe alternatives. Fix any runtime edge cases exposed by the tighter types.

**Independent Test**: Run `npm run type-check` and `npm run lint` in `solune/frontend/` with zero `@ts-expect-error`, zero `as unknown as`, and only intentional documented `eslint-disable` remaining in production files; verify clean exit. Run `npm test` to confirm all tests pass.

### Type Suppression Fixes (5 casts)

- [ ] T045 [US4] Add `isThinkingEvent()` type guard function and remove `as unknown as` cast in solune/frontend/src/services/api.ts (1 suppression)
- [ ] T046 [P] [US4] Declare `SortableItemProps` interface matching dnd-kit types and remove `as unknown as` casts in solune/frontend/src/components/board/AgentColumnCell.tsx (2 suppressions)
- [ ] T047 [P] [US4] Create `ServerErrorShape` type with optional `detail` field and type guard, remove `as unknown as` casts in solune/frontend/src/components/settings/McpSettings.tsx (2 suppressions)

### no-explicit-any Fixes (2 suppressions)

- [ ] T048 [P] [US4] Replace `any` with proper `SpeechRecognition` interface typing in solune/frontend/src/hooks/useVoiceInput.ts (1 suppression)
- [ ] T049 [P] [US4] Replace `any` with bounded generic constraint in solune/frontend/src/lib/lazyWithRetry.ts (1 suppression)

### exhaustive-deps Review (7 suppressions)

- [ ] T050 [US4] Review and resolve `eslint-disable react-hooks/exhaustive-deps` in 6 components — use `useCallback`/`useMemo` where appropriate or keep narrowed disable with documented reason: solune/frontend/src/components/chat/ChatInterface.tsx, solune/frontend/src/components/settings/UploadMcpModal.tsx, solune/frontend/src/components/agents/AgentChatFlow.tsx, solune/frontend/src/components/chores/ChoreChatFlow.tsx, solune/frontend/src/components/chores/AddChoreModal.tsx, solune/frontend/src/components/settings/ModelSelector.tsx (6 suppressions)
- [ ] T051 [US4] Review deps comment and resolve or document suppression in solune/frontend/src/hooks/useRealTimeSync.ts (1 suppression)

### jsx-a11y Documentation (4 suppressions)

- [ ] T052 [P] [US4] Add descriptive reason comments to intentional jsx-a11y `eslint-disable` directives in solune/frontend/src/components/ — AddAgentPopover.tsx (1), AgentIconPickerModal.tsx (1), AgentPresetSelector.tsx (2); keep narrowed suppressions as intentional UX decisions

### Verification for User Story 4

- [ ] T053 [US4] Verify frontend production cleanup — run `npm run type-check && npm run lint && npm test` in solune/frontend/ and confirm clean exit

**Checkpoint**: All frontend production suppressions resolved. Type checker and linter validate every expression in production frontend code.

---

## Phase 7: User Story 5 — Frontend Test Standardisation and Regression Guardrails (Priority: P5)

**Goal**: Standardise frontend tests around the typed mock foundation in `setup.ts`, migrate ~51 test suppressions to typed helpers, add a frontend test type-check command to CI and pre-commit, and tighten ESLint rules to prevent future regression.

**Independent Test**: Run `npm run type-check:test` with zero `@ts-expect-error` and zero `as unknown as` in test files; verify clean exit. Introduce a `@ts-expect-error` in a test file and verify both the type-check command and ESLint flag it.

### Mock Foundation Extension

- [ ] T054 [US5] Extend `createMockApi()` with all missing API namespaces (activityApi, agentsApi, agentToolsApi, appsApi, choresApi, cleanupApi, metadataApi, modelsApi, pipelinesApi, toolsApi, workflowApi) and fix `@ts-expect-error` for WebSocket/crypto mocks with proper global type declarations in solune/frontend/src/test/setup.ts

### Hook Test Migration (~34 suppressions)

- [ ] T055 [US5] Migrate hook tests from `as unknown as` casts to `createMockApi()` — batch 1: hooks starting with a-m (e.g., useActivity, useAgents, useApps, useBoard, useChat, useChores, useCleanup, useMetadata, useModels) in solune/frontend/src/hooks/
- [ ] T056 [P] [US5] Migrate hook tests from `as unknown as` casts to `createMockApi()` — batch 2: hooks starting with n-z (e.g., usePipelines, useSettings, useTools, useWorkflow, and remaining hooks) in solune/frontend/src/hooks/

### Remaining Test Suppression Fixes (~17 suppressions)

- [ ] T057 [US5] Fix `@ts-expect-error` suppressions for WebSocket mocking in solune/frontend/src/hooks/useRealTimeSync.test.tsx (3 suppressions)
- [ ] T058 [P] [US5] Create typed mock helpers and fix `as unknown as` casts in solune/frontend/src/services/api.test.ts (2 suppressions)
- [ ] T059 [P] [US5] Fix non-API `as unknown as` casts with typed mocks in solune/frontend/src/hooks/ — useBuildProgress.test.ts, useCyclingPlaceholder.test.ts, useVoiceInput.test.ts (5 suppressions)
- [ ] T060 [P] [US5] Fix remaining `as unknown as` type erasure casts in various test files under solune/frontend/src/ (5 suppressions)

### ESLint Regression Guardrails

- [ ] T061 [US5] Tighten ESLint rules in solune/frontend/eslint.config.js — set `@typescript-eslint/ban-ts-comment` to error with `ts-expect-error: allow-with-description` only, verify `@typescript-eslint/no-explicit-any` is error

### Verification for User Story 5

- [ ] T062 [US5] Verify frontend test cleanup — run `npm run type-check:test && npm run lint && npm test` in solune/frontend/ and confirm clean exit with zero test suppressions

**Checkpoint**: All frontend test suppressions resolved. ESLint guardrails prevent future regressions. Frontend test type-checking is permanently enabled.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, and regression prevention across the entire feature.

- [ ] T063 [P] Finalise testing documentation in solune/docs/testing.md — add typed mock foundation usage guidance, ESLint suppression policy, and contributor guidance for the new type-check commands
- [ ] T064 Run full backend validation — `uv run ruff check src tests && uv run ruff format --check src tests && uv run pyright src && uv run pyright tests && uv run pytest tests/ -q` in solune/backend/
- [ ] T065 Run full frontend validation — `npm run lint && npm run type-check && npm run type-check:test && npm test && npm run build` in solune/frontend/
- [ ] T066 Run contract validation — `bash solune/scripts/validate-contracts.sh` from repository root to verify frontend types still align with backend OpenAPI schema
- [ ] T067 Audit zero remaining suppressions in all authored code — grep for `# type: ignore`, `# pyright:`, `@ts-expect-error`, `@ts-ignore`, and `as unknown as` in solune/backend/src/, solune/backend/tests/, and solune/frontend/src/; document any intentionally kept suppressions per FR-013
- [ ] T068 Run quickstart.md validation steps end-to-end from specs/004-linting-cleanup/quickstart.md to confirm all phases are reproducible

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — can start immediately
- **Phase 2 (Foundational)**: No separate tasks — US1 in Phase 3 serves as the blocking prerequisite for all subsequent phases
- **Phase 3 (US1)**: Depends on Phase 1 completion — **BLOCKS all cleanup phases** (Phases 4–7)
- **Phase 4 (US2)**: Depends on Phase 3 — needs test gate to verify source cleanup
- **Phase 5 (US3)**: Depends on Phase 4 — reuses typed helpers (RequestIdLogRecord protocol, cache patterns) created in source cleanup; also depends on Phase 3 for test gate
- **Phase 6 (US4)**: Depends on Phase 3 — needs gate infrastructure pattern; **independent of Phases 4–5** (backend track)
- **Phase 7 (US5)**: Depends on Phase 6 — reuses typed patterns from frontend source cleanup; also depends on Phase 3 for test gate
- **Phase 8 (Polish)**: Depends on all user story phases (3–7) being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Setup — No dependencies on other stories — **BLOCKS US2, US3, US4, US5**
- **US2 (P2)**: Can start after US1 — Creates typed helpers reused by US3
- **US3 (P3)**: Can start after US2 — Reuses RequestIdLogRecord protocol and cache patterns
- **US4 (P4)**: Can start after US1 — Independent of backend stories (US2, US3) — **Can run in parallel with US2/US3**
- **US5 (P5)**: Can start after US4 — Reuses typed patterns from frontend source cleanup

### Within Each User Story

- Shared patterns resolved before one-off fixes
- Each file group verified before moving to next group
- Verification tasks run after all fixes in the story
- Story complete before moving to next priority (unless parallelizing US2/US4)

### Parallel Opportunities

- **Phase 1**: T002 and T003 can run in parallel with each other
- **Phase 3 (US1)**: T005→T006 sequential (tsconfig before npm script); T007, T008, T009 can start after T006
- **Phase 4 (US2)**: All [P] tasks within a group can run in parallel; groups should be completed in order (shared patterns first)
- **Phase 5 (US3)**: T035–T041 (individual file fixes) can run in parallel after T033–T034 (typed helpers created)
- **Phase 6 (US4)**: T046–T049, T052 can all run in parallel (different files)
- **Phase 7 (US5)**: T055 and T056 (hook migration batches) can run in parallel; T057–T060 can run in parallel
- **Cross-story**: US2/US3 (backend) and US4/US5 (frontend) can run in parallel after US1 is complete

---

## Parallel Example: Backend and Frontend Tracks

```text
After US1 (Gate Expansion) completes:

Track A (Backend):                    Track B (Frontend):
├── US2: Backend Source Cleanup       ├── US4: Frontend Source Cleanup
│   ├── [P] T014 model_fetcher.py    │   ├── [P] T046 AgentColumnCell.tsx
│   ├── [P] T015 gh/service.py       │   ├── [P] T047 McpSettings.tsx
│   ├── [P] T017 utils.py            │   ├── [P] T048 useVoiceInput.ts
│   ├── [P] T018 otel_setup.py       │   └── [P] T049 lazyWithRetry.ts
│   └── [P] T021 8× github_projects/ │
├── US3: Backend Test Cleanup         ├── US5: Frontend Test Cleanup
│   ├── [P] T037 polling_loop.py     │   ├── [P] T056 hook batch 2
│   ├── [P] T038 template_files.py   │   ├── [P] T058 api.test.ts
│   └── [P] T040 transcript_det.py   │   └── [P] T059 non-API hooks
└── Done                              └── Done
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (audit baseline)
2. Complete Phase 3: User Story 1 (gate expansion)
3. **STOP and VALIDATE**: Verify both test type-check gates catch errors
4. This alone delivers immediate value — prevents new test type regressions

### Incremental Delivery

1. Setup → US1 (gates) → **Validate** (MVP!)
2. Add US2 (backend source) → **Validate** — zero source suppressions
3. Add US3 (backend test) → **Validate** — backend fully clean
4. Add US4 (frontend source) → **Validate** — frontend production clean
5. Add US5 (frontend test + guardrails) → **Validate** — everything clean
6. Polish → Full validation → **Ship**

### Parallel Team Strategy

With two developers after US1 completes:

- **Developer A**: US2 → US3 (backend track)
- **Developer B**: US4 → US5 (frontend track)
- Both tracks merge for Phase 8 (Polish)

---

## Summary

| Phase | Story | Tasks | Suppressions Addressed |
|-------|-------|-------|----------------------|
| Phase 1: Setup | — | T001–T004 (4) | 0 (audit only) |
| Phase 3: US1 Gate Expansion | P1 | T005–T012 (8) | 0 (infrastructure) |
| Phase 4: US2 Backend Source | P2 | T013–T032 (20) | ~55 (46 type:ignore + 9 pyright) |
| Phase 5: US3 Backend Test | P3 | T033–T044 (12) | ~28 |
| Phase 6: US4 Frontend Source | P4 | T045–T053 (9) | ~18 |
| Phase 7: US5 Frontend Test | P5 | T054–T062 (9) | ~51 + ESLint guardrails |
| Phase 8: Polish | — | T063–T068 (6) | 0 (validation only) |
| **Total** | | **68 tasks** | **~152 suppressions** |

**Parallel opportunities**: 15 cross-file parallel groups identified across phases

**Suggested MVP scope**: Phase 1 + Phase 3 (US1 only) — delivers test type-check gates immediately

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in the same group
- [Story] label maps each task to its user story for traceability
- Each user story is independently completable and testable at its checkpoint
- Verify after each file group or shared pattern resolution
- Commit after each task or logical group
- Stop at any checkpoint to validate the story independently
- Suppressions in vendor, generated, and E2E fixture files (`e2e/fixtures.ts`) are intentionally out of scope per FR-011
- When a suppression genuinely cannot be removed (missing upstream stubs), use the narrowest form with documented reason per FR-013
