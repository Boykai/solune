# Tasks: Codebase Modularity Review

**Input**: Design documents from `/specs/001-codebase-modularity-review/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: New unit tests are included for extracted classes (ChatStateManager, ProposalOrchestrator) as specified in plan.md and spec.md (FR-002, FR-005, SC-005, SC-007). No TDD approach — tests validate extraction correctness.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. User stories map to the 6 refactoring targets identified in the parent issue #1471.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `solune/backend/src/`, `solune/backend/tests/`
- **Frontend**: `solune/frontend/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish blocking prerequisites — extract shared backend services that multiple user stories depend on

- [ ] T001 Create `solune/backend/src/services/chat_state_manager.py` — define `ChatStateManager` class with constructor accepting `db: aiosqlite.Connection`, `chat_store: ChatStore`, optional `max_retries: int = 3`, `base_delay: float = 0.1`; implement `get_lock(key) → asyncio.Lock`, `get_messages(session_id)`, `add_message(session_id, message)`, `clear_messages(session_id)`, `get_proposal(proposal_id)`, `store_proposal(proposal_id, proposal)`, `get_recommendation(rec_id)`, `store_recommendation(rec_id, rec)` methods per `contracts/chat-state-manager-api.yaml`; move `_messages`, `_proposals`, `_recommendations`, `_locks` dicts and their accessor/retry logic from `solune/backend/src/api/chat.py` into this class
- [ ] T002 Create unit tests in `solune/backend/tests/unit/test_chat_state_manager.py` — test that `ChatStateManager` can be instantiated with mocked deps, test `get_lock()` returns same lock for same key, test `get_messages()` read-through cache (cache hit + SQLite fallback), test `add_message()` write-through, test `store_proposal()` / `get_proposal()` round-trip, test `store_recommendation()` / `get_recommendation()` round-trip, test multiple independent instances have separate state (SC-007)
- [ ] T003 Register `ChatStateManager` DI in `solune/backend/src/dependencies.py` — add `get_chat_state_manager(request: Request) → ChatStateManager` factory that reads from `request.app.state.chat_state_manager`; instantiate `ChatStateManager` during FastAPI lifespan in `solune/backend/src/main.py` and store on `app.state.chat_state_manager` (FR-011)
- [ ] T004 Create `solune/backend/src/services/bootstrap.py` — extract startup/shutdown helper functions from `solune/backend/src/main.py` lifespan: `auto_start_copilot_polling()`, `discover_and_register_active_projects()`, `restore_app_pipeline_polling()`, `startup_agent_mcp_sync()`, `polling_watchdog_loop()`, `session_cleanup_loop()`; update `main.py` lifespan to delegate to these bootstrap functions (FR-007)
- [ ] T005 Update `solune/backend/tests/unit/test_main.py` — update patch paths for lifespan tests to use `src.main.X` for imports from bootstrap module; add direct tests for bootstrap functions patching at `src.services.bootstrap.X`
- [ ] T006 Run backend tests to verify Phase 1: `cd solune/backend && python -m pytest tests/unit/test_chat_state_manager.py tests/unit/test_main.py -v`

**Checkpoint**: ChatStateManager + bootstrap.py extracted and tested — user story implementation can now begin

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extract ProposalOrchestrator service — required by US1 (chat split) and US2 (testable confirmation)

**⚠️ CRITICAL**: US1 and US2 both depend on this extraction; US3–US7 do not

- [ ] T007 Create `solune/backend/src/services/proposal_orchestrator.py` — define `ProposalOrchestrator` class with constructor accepting `github_service`, `connection_manager`, `chat_state_manager`, `chat_store`, `settings_store` per `contracts/proposal-orchestrator-api.yaml`; extract the 7-phase `confirm_proposal()` logic (~350 lines) from `solune/backend/src/api/chat.py` lines 1606–1951 into methods: `confirm()`, `_validate_proposal()`, `_apply_user_edits()`, `_resolve_repository()`, `_create_github_issue()`, `_broadcast_confirmation()`, `_configure_workflow()`, `_assign_agent_and_start()` (FR-002)
- [ ] T008 Create unit tests in `solune/backend/tests/unit/test_proposal_orchestrator.py` — test each orchestration phase independently with mocked deps (SC-005): test `_validate_proposal()` raises 404/403/410/409, test `_apply_user_edits()` applies title/description, test `_resolve_repository()` returns owner/repo/project_id, test `_create_github_issue()` calls GitHub API, test `_broadcast_confirmation()` sends WebSocket + chat message, test `_configure_workflow()` loads/creates config, test `_assign_agent_and_start()` starts polling
- [ ] T009 Register `ProposalOrchestrator` DI in `solune/backend/src/dependencies.py` — add `get_proposal_orchestrator()` factory using `Depends()` to wire all service deps (FR-010)
- [ ] T010 Run backend tests to verify Phase 2: `cd solune/backend && python -m pytest tests/unit/test_proposal_orchestrator.py -v`

**Checkpoint**: ProposalOrchestrator extracted — chat split and proposal testing stories can proceed

---

## Phase 3: User Story 1 — Developer Navigates and Edits Backend Chat Endpoints (Priority: P1) 🎯 MVP

**Goal**: Split `api/chat.py` (2,930 lines, 25 routes) into a package with 5 domain-scoped sub-modules so developers find code in ≤2 navigation steps

**Independent Test**: Open any chat sub-module, make an isolated change, verify it compiles and passes tests without touching other sub-modules

### Implementation for User Story 1

- [ ] T011 [US1] Create `solune/backend/src/api/chat/__init__.py` — define aggregated `router = APIRouter()` that includes sub-routers from conversations, messages, proposals, plans, streaming; re-export public symbols for backward compatibility (`from src.api.chat import router` must work)
- [ ] T012 [P] [US1] Create `solune/backend/src/api/chat/conversations.py` — extract 4 conversation CRUD routes (POST/GET/PATCH/DELETE `/conversations/*`) from `solune/backend/src/api/chat.py` per `contracts/chat-package-api.yaml`; inject `ChatStateManager` and `ChatStore` via `Depends()`
- [ ] T013 [P] [US1] Create `solune/backend/src/api/chat/messages.py` — extract 3 message routes (GET/DELETE/POST `/messages/*`) from `solune/backend/src/api/chat.py`; inject `ChatStateManager`, `ChatStore`, AI service via `Depends()`
- [ ] T014 [P] [US1] Create `solune/backend/src/api/chat/proposals.py` — extract 2 proposal routes (POST confirm, DELETE cancel `/proposals/*`) from `solune/backend/src/api/chat.py`; delegate `confirm_proposal` to `ProposalOrchestrator` via `Depends()`
- [ ] T015 [P] [US1] Create `solune/backend/src/api/chat/plans.py` — extract 12 plan routes (CRUD + steps + approval `/plans/*`) from `solune/backend/src/api/chat.py`; inject `ChatStore` and plan service via `Depends()`
- [ ] T016 [P] [US1] Create `solune/backend/src/api/chat/streaming.py` — extract 2 SSE streaming routes (POST `/stream`, `/plan-stream`) from `solune/backend/src/api/chat.py`; inject `ChatStateManager` and AI service via `Depends()`
- [ ] T017 [US1] Delete `solune/backend/src/api/chat.py` — remove the original monolithic file after all routes are extracted and verified
- [ ] T018 [US1] Update test patch paths in `solune/backend/tests/` — change patches from `src.api.chat.X` to `src.api.chat.<submodule>.X` (e.g., `src.api.chat.messages.get_settings`, `src.api.chat.proposals.get_github_service`, `src.api.chat.streaming.get_chat_agent_service`) in conftest.py, integration tests, and unit tests
- [ ] T019 [US1] Verify no single chat sub-module exceeds 600 lines (SC-001) and all existing backend tests pass: `cd solune/backend && python -m pytest tests/ -x -q`

**Checkpoint**: Chat package split complete — 5 focused modules replace 1 monolithic file. Each module is independently editable and testable.

---

## Phase 4: User Story 2 — Developer Tests Proposal Confirmation Logic in Isolation (Priority: P1)

**Goal**: Enable independent unit testing of each orchestration phase in `confirm_proposal()` — already extracted in Phase 2 (T007–T009)

**Independent Test**: Instantiate `ProposalOrchestrator` with mocked deps, invoke any single phase, verify behavior without exercising other phases

### Implementation for User Story 2

- [ ] T020 [US2] Verify `ProposalOrchestrator` integration — confirm that `solune/backend/src/api/chat/proposals.py` (from T014) delegates to `orchestrator.confirm()` and the endpoint behavior is identical to the pre-extraction flow (same HTTP responses, same side effects, same error handling per FR-012)
- [ ] T021 [US2] Add integration test in `solune/backend/tests/integration/` — test the full proposal confirm endpoint (POST `/proposals/{id}/confirm`) end-to-end to verify identical behavior to pre-extraction state
- [ ] T022 [US2] Verify SC-005: confirm that `solune/backend/tests/unit/test_proposal_orchestrator.py` (from T008) has at least one test per orchestration phase that mocks all other phases

**Checkpoint**: ProposalOrchestrator is fully testable in isolation — each phase can be unit-tested independently

---

## Phase 5: User Story 3 — Developer Modifies a Single Domain's API Client (Priority: P2)

**Goal**: Split `services/api.ts` (1,876 lines, 17+ namespaces) into domain-scoped files so each API domain can be reviewed and modified independently

**Independent Test**: Modify a single domain API file (e.g., `api/board.ts`), run `npx tsc --noEmit`, confirm all imports resolve via barrel re-export

### Implementation for User Story 3

- [ ] T023 [US3] Create `solune/frontend/src/services/api/client.ts` — extract shared HTTP infrastructure from `solune/frontend/src/services/api.ts`: `request<T>()`, `ApiError`, `onAuthExpired`, `API_BASE_URL`, `getCsrfToken()`, `normalizeApiError()` per `contracts/frontend-api-client-api.yaml`
- [ ] T024 [P] [US3] Create `solune/frontend/src/services/api/auth.ts` — extract `authApi` namespace; import `request` from `./client`
- [ ] T025 [P] [US3] Create `solune/frontend/src/services/api/projects.ts` — extract `projectsApi` namespace; import `request` from `./client`
- [ ] T026 [P] [US3] Create `solune/frontend/src/services/api/tasks.ts` — extract `tasksApi` namespace; import `request` from `./client`
- [ ] T027 [P] [US3] Create `solune/frontend/src/services/api/chat.ts` — extract `conversationApi` + `chatApi` namespaces (~450 lines); import `request` from `./client`
- [ ] T028 [P] [US3] Create `solune/frontend/src/services/api/board.ts` — extract `boardApi` namespace; import `request` from `./client`
- [ ] T029 [P] [US3] Create `solune/frontend/src/services/api/settings.ts` — extract `settingsApi` namespace; import `request` from `./client`
- [ ] T030 [P] [US3] Create `solune/frontend/src/services/api/workflow.ts` — extract `workflowApi` + `metadataApi` namespaces; import `request` from `./client`
- [ ] T031 [P] [US3] Create `solune/frontend/src/services/api/signal.ts` — extract `signalApi` namespace; import `request` from `./client`
- [ ] T032 [P] [US3] Create `solune/frontend/src/services/api/mcp.ts` — extract `mcpApi` namespace; import `request` from `./client`
- [ ] T033 [P] [US3] Create `solune/frontend/src/services/api/cleanup.ts` — extract `cleanupApi` namespace; import `request` from `./client`
- [ ] T034 [P] [US3] Create `solune/frontend/src/services/api/chores.ts` — extract `choresApi` namespace; import `request` from `./client`
- [ ] T035 [P] [US3] Create `solune/frontend/src/services/api/agents.ts` — extract `agentsApi` namespace; import `request` from `./client`
- [ ] T036 [P] [US3] Create `solune/frontend/src/services/api/pipelines.ts` — extract `pipelinesApi` + `modelsApi` namespaces; import `request` from `./client`
- [ ] T037 [P] [US3] Create `solune/frontend/src/services/api/tools.ts` — extract `toolsApi` + `agentToolsApi` namespaces; import `request` from `./client`
- [ ] T038 [P] [US3] Create `solune/frontend/src/services/api/apps.ts` — extract `appsApi` namespace; import `request` from `./client`
- [ ] T039 [P] [US3] Create `solune/frontend/src/services/api/activity.ts` — extract `activityApi` namespace; import `request` from `./client`
- [ ] T040 [US3] Create barrel `solune/frontend/src/services/api/index.ts` — re-export all namespaces and public types (`ApiError`, `onAuthExpired`, etc.) so all 63+ existing `import { X } from '@/services/api'` paths work unchanged (FR-008)
- [ ] T041 [US3] Move test file `solune/frontend/src/services/api.test.ts` → `solune/frontend/src/services/api/api.test.ts` — update import paths from `'../api'` to `'./index'`; test structure and assertions remain identical
- [ ] T042 [US3] Delete `solune/frontend/src/services/api.ts` — remove the original monolithic file after barrel re-export is verified
- [ ] T043 [US3] Verify no single API domain file exceeds 400 lines (SC-002) and zero consumer files require import changes (SC-006): `cd solune/frontend && npx tsc --noEmit && npx vitest run`

**Checkpoint**: Frontend API client split complete — 16 domain files + barrel replace 1 monolithic file. All 63+ consumer imports work unchanged.

---

## Phase 6: User Story 4 — Developer Finds and Updates Domain Types (Priority: P2)

**Goal**: Split `types/index.ts` (1,525 lines, 199 exports) into domain-scoped type files so developers find types in ≤2 navigation steps

**Independent Test**: Modify a domain types file (e.g., `types/chat.ts`), run `npx tsc --noEmit`, confirm all imports resolve via barrel re-export

### Implementation for User Story 4

- [ ] T044 [P] [US4] Create `solune/frontend/src/types/common.ts` — extract shared enums and primitives: `ProjectType`, `SenderType`, `ActionType`, `ProposalStatus`, `RecommendationStatus`, `APIError`, `FileAttachment`, `FileUploadResponse`, `FileUploadError`, `MessageStatus` per `contracts/frontend-types-api.yaml`
- [ ] T045 [P] [US4] Create `solune/frontend/src/types/auth.ts` — extract `User`, `AuthResponse` (~15 lines)
- [ ] T046 [P] [US4] Create `solune/frontend/src/types/projects.ts` — extract `StatusColumn`, `Project`, `ProjectListResponse` (~25 lines)
- [ ] T047 [P] [US4] Create `solune/frontend/src/types/tasks.ts` — extract `Task`, `TaskCreateRequest`, `TaskListResponse` (~25 lines)
- [ ] T048 [P] [US4] Create `solune/frontend/src/types/proposals.ts` — extract `AITaskProposal`, `ProposalConfirmRequest`, `IssuePriority`, `IssueSize`, `IssueLabel`, `IssueMetadata`, `RepositoryMetadata`, `IssueRecommendation`, `IssueCreateActionData` (~80 lines); import `ProposalStatus`, `RecommendationStatus` from `./common`
- [ ] T049 [P] [US4] Create `solune/frontend/src/types/plans.ts` — extract `PlanStatus`, `ThinkingPhase`, `StepApprovalStatus`, `Plan`, `PlanStep`, `PlanVersion`, `PlanHistoryResponse`, `PlanCreateActionData`, approval/feedback types (~85 lines)
- [ ] T050 [P] [US4] Create `solune/frontend/src/types/chat.ts` — extract `ChatMessage`, `ActionData`, `Conversation`, `Mention*`, `VoiceInputState`, `ChatPreferences` (~100 lines); import from `./common` (SenderType, ActionType, MessageStatus, FileAttachment), `./proposals` (IssueCreateActionData), `./plans` (PlanCreateActionData) — use direct sibling imports, not barrel
- [ ] T051 [P] [US4] Create `solune/frontend/src/types/board.ts` — extract `BoardItem`, `BoardColumn`, `BoardProject`, `LinkedPR`, `PaginatedResponse`, `RefreshError`, etc. (~340 lines)
- [ ] T052 [P] [US4] Create `solune/frontend/src/types/settings.ts` — extract `EffectiveUserSettings`, `GlobalSettings`, `AIPreferences`, update variants, `ModelOption`, `ModelsResponse` (~130 lines)
- [ ] T053 [P] [US4] Create `solune/frontend/src/types/workflow.ts` — extract `WorkflowResult`, `WorkflowConfiguration`, `PipelineStateInfo`, `AgentNotification` (~55 lines)
- [ ] T054 [P] [US4] Create `solune/frontend/src/types/pipeline.ts` — extract `PipelineConfig`, `PipelineStage`, `PipelineAgentNode`, `PresetPipelineDefinition`, etc. (~130 lines)
- [ ] T055 [P] [US4] Create `solune/frontend/src/types/agents.ts` — extract `AgentSource`, `AgentAssignment`, `AvailableAgent`, `AgentPreset` (~30 lines)
- [ ] T056 [P] [US4] Create `solune/frontend/src/types/signal.ts` — extract `SignalConnection`, `SignalPreferences`, `SignalBanner`, etc. (~45 lines)
- [ ] T057 [P] [US4] Create `solune/frontend/src/types/mcp.ts` — extract `McpConfiguration`, `McpToolConfig`, `McpPreset`, etc. (~90 lines)
- [ ] T058 [P] [US4] Create `solune/frontend/src/types/cleanup.ts` — extract `BranchInfo`, `CleanupPreflightResponse`, `CleanupExecuteRequest`, etc. (~110 lines)
- [ ] T059 [P] [US4] Create `solune/frontend/src/types/chores.ts` — extract `Chore`, `ChoreTemplate`, `ChoreStatus`, `ScheduleType`, etc. (~145 lines)
- [ ] T060 [P] [US4] Create `solune/frontend/src/types/activity.ts` — extract `ActivityEvent`, `ActivityStats` (~20 lines)
- [ ] T061 [P] [US4] Create `solune/frontend/src/types/ui.ts` — extract `NavRoute`, `SidebarState`, `Notification`, `TourStep`, `FaqEntry`, `ResolvedModelInfo` (~60 lines)
- [ ] T062 [US4] Rewrite `solune/frontend/src/types/index.ts` as barrel — replace all type definitions with re-exports: `export * from './common'`, `export * from './auth'`, ..., `export * from './ui'`, plus existing `export * from './apps'` and `export * from './app-template'` per `contracts/frontend-types-api.yaml` (FR-008)
- [ ] T063 [US4] Verify no single types domain file exceeds 400 lines (SC-002) and zero consumer files require import changes — all 202+ existing `import type { X } from '@/types'` paths work: `cd solune/frontend && npx tsc --noEmit && npx vitest run`

**Checkpoint**: Frontend types split complete — 17+ domain files + barrel replace 1 monolithic file. All 202+ consumer imports work unchanged.

---

## Phase 7: User Story 5 — Developer Manages Chat State Through a Structured Interface (Priority: P3)

**Goal**: Replace module-level global state dicts with `ChatStateManager` (already extracted in Phase 1) so state is explicitly managed and testable

**Independent Test**: Instantiate `ChatStateManager` in a test with no module-level side effects; create multiple independent instances with different state (SC-007)

### Implementation for User Story 5

- [ ] T064 [US5] Update chat package sub-modules (`solune/backend/src/api/chat/conversations.py`, `messages.py`, `proposals.py`, `plans.py`, `streaming.py`) — replace all direct access to module-level `_messages`, `_proposals`, `_recommendations`, `_locks` dicts with calls to `ChatStateManager` methods via `Depends(get_chat_state_manager)` (FR-005)
- [ ] T065 [US5] Remove module-level global state declarations from chat package sub-modules (`solune/backend/src/api/chat/conversations.py`, `messages.py`, `proposals.py`, `streaming.py`) — delete `_messages: dict = {}`, `_proposals: dict = {}`, `_recommendations: dict = {}`, `_locks: dict = {}` and their standalone accessor functions after all references use `ChatStateManager`
- [ ] T066 [US5] Update `solune/backend/src/main.py` lifespan shutdown — add explicit `ChatStateManager` cleanup via `app.state.chat_state_manager` clear methods during application shutdown
- [ ] T067 [US5] Verify ChatStateManager integration: `cd solune/backend && python -m pytest tests/ -x -q`

**Checkpoint**: Chat state consolidated into managed class — no more module-level globals, explicit lifecycle management

---

## Phase 8: User Story 6 — Developer Reviews Webhook Handlers by Event Type (Priority: P3)

**Goal**: Split `api/webhooks.py` (1,033 lines) into a package with sub-modules organized by event type

**Independent Test**: Modify a webhook sub-module (e.g., `pull_requests.py`), verify behavior through existing webhook integration tests

### Implementation for User Story 6

- [ ] T068 [US6] Create `solune/backend/src/api/webhooks/__init__.py` — define aggregated `router = APIRouter()` that includes the handler router; re-export public symbols for backward compatibility
- [ ] T069 [P] [US6] Create `solune/backend/src/api/webhooks/handlers.py` — extract main webhook dispatcher from `solune/backend/src/api/webhooks.py`: `github_webhook()` route, `verify_webhook_signature()`, `_processed_delivery_ids` BoundedSet, `classify_pull_request_activity()`, `extract_issue_number_from_pr()` per `contracts/webhooks-package-api.yaml`
- [ ] T070 [P] [US6] Create `solune/backend/src/api/webhooks/pull_requests.py` — extract PR event handlers: `handle_pull_request_event()`, `handle_copilot_pr_ready()`, `update_issue_status_for_copilot_pr()`
- [ ] T071 [P] [US6] Create `solune/backend/src/api/webhooks/ci.py` — extract CI handlers: `handle_check_run_event()`, `handle_check_suite_event()`, `_get_auto_merge_pipeline()`
- [ ] T072 [US6] Delete `solune/backend/src/api/webhooks.py` — remove the original monolithic file after all handlers are extracted
- [ ] T073 [US6] Update test patch paths in `solune/backend/tests/` — change patches to sub-module level: `src.api.webhooks.handlers.get_settings`, `src.api.webhooks.handlers.get_db`, `src.api.webhooks.handlers.log_event`, `src.api.webhooks.pull_requests.github_projects_service` in integration test files (test_full_workflow.py, test_webhook_dispatch.py, test_webhook_verification.py)
- [ ] T074 [US6] Verify no single webhook sub-module exceeds 600 lines (SC-001) and all webhook tests pass: `cd solune/backend && python -m pytest tests/ -x -q`

**Checkpoint**: Webhooks package split complete — 3 focused modules replace 1 monolithic file, organized by event type

---

## Phase 9: User Story 7 — Developer Reads and Tests Bootstrap Logic Independently (Priority: P3)

**Goal**: Bootstrap functions extracted from `main.py` (already done in Phase 1, T004) are independently testable

**Independent Test**: Import and test individual bootstrap functions with mocked dependencies

### Implementation for User Story 7

- [ ] T075 [US7] Verify `solune/backend/src/services/bootstrap.py` (from T004) is independently testable — confirm each bootstrap function can be imported and tested with mocked deps without loading the full app
- [ ] T076 [US7] Verify `solune/backend/src/main.py` lifespan delegates to bootstrap functions — confirm lifespan function calls bootstrap module and no inline startup/shutdown logic remains in main.py (FR-007)
- [ ] T077 [US7] Verify test coverage in `solune/backend/tests/unit/test_main.py` (from T005) — confirm bootstrap functions have direct tests patching at `src.services.bootstrap.X` and lifespan tests patch at `src.main.X`
- [ ] T078 [US7] Run full backend suite: `cd solune/backend && python -m pytest tests/ -v`

**Checkpoint**: Bootstrap logic fully extracted and independently testable

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, diagram regeneration, and documentation alignment

- [ ] T079 [P] Regenerate architecture diagrams: `bash solune/scripts/generate-diagrams.sh` — the script handles both `.py` files and package directories with `__init__.py` for API route discovery
- [ ] T080 [P] Verify import validation — confirm no circular imports exist between chat sub-modules (sub-modules must only import from shared utilities or ChatStateManager, never from sibling sub-modules per spec edge cases)
- [ ] T081 [P] Verify SC-001: no single backend module exceeds 600 lines — check all files in `api/chat/`, `api/webhooks/`, `services/`
- [ ] T082 [P] Verify SC-002: no single frontend file exceeds 400 lines — check all files in `services/api/`, `types/`
- [ ] T083 [P] Verify SC-006: zero consumer files required import path changes — `git diff --name-only` should show no changes to files outside `api/chat/`, `api/webhooks/`, `services/api/`, `types/`, `tests/`, and `main.py`
- [ ] T084 Run full test suites for final verification — backend: `cd solune/backend && python -m pytest tests/ -v`; frontend: `cd solune/frontend && npx tsc --noEmit && npx vitest run && npx eslint .`
- [ ] T085 Run quickstart.md validation — follow `specs/001-codebase-modularity-review/quickstart.md` Phase 7 verification steps
- [ ] T086 Update `solune/docs/project-structure.md` if it references the old monolithic file paths

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
  - T001–T003: ChatStateManager extraction (required by US1, US5)
  - T004–T005: bootstrap.py extraction (required by US7)
- **Phase 2 (Foundational)**: Depends on Phase 1 (T001–T003) — BLOCKS US1 and US2
  - T007–T009: ProposalOrchestrator extraction (required by chat split)
- **Phase 3 (US1 — Chat Split)**: Depends on Phase 1 + Phase 2
- **Phase 4 (US2 — Proposal Testing)**: Depends on Phase 2 (ProposalOrchestrator) + Phase 3 (chat split for integration)
- **Phase 5 (US3 — API Client Split)**: Depends on Phase 1 only — **can run in parallel with Phases 3–4**
- **Phase 6 (US4 — Types Split)**: Depends on Phase 1 only — **can run in parallel with Phases 3–5**
- **Phase 7 (US5 — ChatStateManager Integration)**: Depends on Phase 1 (T001–T003) + Phase 3 (US1 chat split)
- **Phase 8 (US6 — Webhooks Split)**: Depends on Phase 1 only — **can run in parallel with Phases 3–7**
- **Phase 9 (US7 — Bootstrap Verification)**: Depends on Phase 1 (T004–T005)
- **Phase 10 (Polish)**: Depends on all previous phases

### User Story Dependencies

```
Phase 1 (Setup) ─────┬──→ Phase 2 (Foundational) ──→ Phase 3 (US1) ──→ Phase 4 (US2)
                      │                                     │
                      │                                     └──→ Phase 7 (US5)
                      │
                      ├──→ Phase 5 (US3) ─────────────────────────┐
                      ├──→ Phase 6 (US4) ─────────────────────────┤
                      ├──→ Phase 8 (US6) ─────────────────────────┤
                      └──→ Phase 9 (US7) ─────────────────────────┤
                                                                  │
                                                                  └──→ Phase 10 (Polish)
```

### Within Each User Story

- Models/classes before services (ChatStateManager → ProposalOrchestrator → chat routes)
- Extraction before deletion of original files
- Test patch updates before verification runs
- Sub-module creation (parallelizable) before router aggregation in `__init__.py`

### Parallel Opportunities

- **Phase 1**: T001 (ChatStateManager) and T004 (bootstrap.py) can run in parallel
- **Phase 3 (US1)**: T012–T016 (5 chat sub-modules) can all run in parallel
- **Phase 5 (US3)**: T024–T039 (16 API domain files) can all run in parallel
- **Phase 6 (US4)**: T044–T061 (17+ type domain files) can all run in parallel
- **Phase 8 (US6)**: T069–T071 (3 webhook sub-modules) can all run in parallel
- **Cross-phase**: US3 (frontend API) + US4 (frontend types) can run in parallel with US1 (backend chat) + US6 (backend webhooks)

---

## Parallel Example: User Story 1 (Chat Split)

```bash
# After Phase 2 is complete, launch all chat sub-modules in parallel:
Task T012: "Create conversations.py in solune/backend/src/api/chat/"
Task T013: "Create messages.py in solune/backend/src/api/chat/"
Task T014: "Create proposals.py in solune/backend/src/api/chat/"
Task T015: "Create plans.py in solune/backend/src/api/chat/"
Task T016: "Create streaming.py in solune/backend/src/api/chat/"

# Then sequentially:
Task T011: "Create __init__.py aggregating all sub-routers"
Task T017: "Delete original chat.py"
Task T018: "Update test patch paths"
Task T019: "Verify all tests pass"
```

## Parallel Example: User Story 3 (Frontend API Split)

```bash
# Launch shared infrastructure first:
Task T023: "Create client.ts with shared HTTP utilities"

# Then all domain files in parallel:
Task T024-T039: "Create 16 domain API files (auth, projects, tasks, ...)"

# Then sequentially:
Task T040: "Create barrel index.ts"
Task T041: "Move test file"
Task T042: "Delete original api.ts"
Task T043: "Verify TypeScript + Vitest"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup (ChatStateManager + bootstrap.py)
2. Complete Phase 2: Foundational (ProposalOrchestrator)
3. Complete Phase 3: User Story 1 (chat.py split)
4. Complete Phase 4: User Story 2 (proposal testing verification)
5. **STOP and VALIDATE**: Run full backend test suite
6. The backend is now maintainable — chat endpoints are navigable, proposals are testable

### Incremental Delivery

1. Phase 1 + Phase 2 → Foundation ready
2. + Phase 3 (US1) + Phase 4 (US2) → Backend chat maintainability achieved (MVP!)
3. + Phase 5 (US3) → Frontend API client split — review-friendly PRs
4. + Phase 6 (US4) → Frontend types split — domain-scoped types
5. + Phase 7 (US5) → Chat state consolidated
6. + Phase 8 (US6) → Webhooks maintainability achieved
7. + Phase 9 (US7) → Bootstrap independently testable
8. + Phase 10 → Final polish and verification

### Parallel Team Strategy

With multiple developers after Phase 1 + Phase 2 are complete:

1. **Developer A** (Backend): Phase 3 (US1 — chat split) → Phase 4 (US2) → Phase 7 (US5) → Phase 8 (US6)
2. **Developer B** (Frontend): Phase 5 (US3 — API split) → Phase 6 (US4 — types split)
3. **Developer C** (Backend): Phase 9 (US7 — bootstrap verification) → Phase 10 (Polish)

Backend and frontend tracks are fully independent after Phase 1.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Zero functional changes — all refactoring is structural (FR-012)
- Zero new dependencies — uses only existing language/framework features
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Test patch paths: after package splits, patch at the sub-module level where the name is used, not the barrel re-export
- Frontend type imports: domain type files (e.g., `chat.ts`) must import from sibling files directly (`import { X } from './proposals'`), never through the barrel `index.ts`, to avoid circular dependencies
