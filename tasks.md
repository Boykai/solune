# Tasks: Codebase Modularity Review

**Input**: Design documents from `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/`
**Prerequisites**: plan.md (required), research.md (9 decisions), data-model.md (module topology), contracts/ (5 interface contracts)

**Tests**: No new tests are required — this is a behavior-preserving refactoring with existing test coverage (5200+ backend, 2200+ frontend). All existing tests must pass after each target. See `quickstart.md` for verification commands.

**Organization**: Tasks are grouped by refactoring target (mapped to user stories) to enable independent implementation and verification of each target.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which refactoring target this task belongs to (US1–US7)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `solune/backend/src/` (Python/FastAPI)
- **Frontend**: `solune/frontend/src/` (TypeScript/React)
- **Tests**: `solune/backend/tests/unit/` (pytest), `solune/frontend/src/__tests__/` (Vitest)

## User Story ↔ Refactoring Target Mapping

| Story | Target | Priority | Description |
|-------|--------|----------|-------------|
| US1 | Target 1 | P1 | Split `api/chat.py` → `api/chat/` package |
| US2 | Target 2 | P1 | Extract `ProposalOrchestrator` service |
| US3 | Target 5 | P1 | Consolidate backend global state → `ChatStateManager` |
| US4 | Target 6 | P2 | Split `api/webhooks.py` → `api/webhooks/` package |
| US5 | Target 3 | P2 | Split `services/api.ts` → `services/api/` package |
| US6 | Target 4 | P2 | Domain-scoped types → `types/*.ts` |
| US7 | Bonus | P3 | Extract `services/bootstrap.py` from `main.py` |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create package directories and establish baseline test results

- [ ] T001 Run full backend test suite to establish baseline in `solune/backend/` (`python -m pytest tests/unit/ -q --timeout=120`)
- [ ] T002 Run full frontend test suite to establish baseline in `solune/frontend/` (`npm test`)
- [ ] T003 [P] Create `solune/backend/src/api/chat/` package directory
- [ ] T004 [P] Create `solune/backend/src/api/webhooks/` package directory
- [ ] T005 [P] Create `solune/frontend/src/services/api/` package directory

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extract shared utilities and base modules that multiple user stories depend on

**⚠️ CRITICAL**: US1 (chat split) foundational modules must complete before US2 and US3 can begin

- [ ] T006 Create `ChatStateManager` class skeleton in `solune/backend/src/api/chat/state.py` with `__init__`, stub methods for `get_messages`, `set_messages`, `get_proposal`, `set_proposal`, `get_recommendation`, `set_recommendation`, `get_lock`, `cleanup` per `contracts/chat-package-interface.md`
- [ ] T007 [P] Create shared helper functions module in `solune/backend/src/api/chat/helpers.py` extracting `_retry_persist`, `_persist_message`, `_persist_proposal`, `_persist_recommendation`, `_default_expires_at`, `_resolve_repository`, `_trigger_signal_delivery`, `_safe_validation_detail` from `solune/backend/src/api/chat.py`
- [ ] T008 [P] Create `FileUploadResponse` model in `solune/backend/src/api/chat/models.py` extracted from `solune/backend/src/api/chat.py`
- [ ] T009 [P] Create shared API client module in `solune/frontend/src/services/api/client.ts` extracting `apiClient`, `handleApiError`, `API_BASE_URL`, and request helpers from `solune/frontend/src/services/api.ts` per `contracts/frontend-api-package-interface.md`

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Split `api/chat.py` → `api/chat/` Package (Priority: P1) 🎯 MVP

**Goal**: Decompose the 2930-line monolithic `api/chat.py` into 10 focused sub-modules inside an `api/chat/` package, maintaining backward compatibility via barrel re-export

**Independent Test**: `python -m pytest tests/unit/test_api_chat.py -v --timeout=120` — all existing chat tests pass; `python -c "from src.api.chat import router; print('OK')"` confirms backward-compatible import

### Implementation for User Story 1

- [ ] T010 [US1] Extract dispatch handlers into `solune/backend/src/api/chat/dispatch.py` moving `_handle_agent_command`, `_handle_transcript_upload`, `_handle_feature_request`, `_handle_status_change`, `_handle_task_generation`, `_extract_transcript_content`, `_post_process_agent_response` from `solune/backend/src/api/chat.py`
- [ ] T011 [US1] Extract message CRUD endpoints into `solune/backend/src/api/chat/messages.py` moving `get_messages`, `add_message`, `clear_messages`, `get_session_messages`, `send_message`, `send_message_stream` from `solune/backend/src/api/chat.py`
- [ ] T012 [US1] Extract proposal/recommendation endpoints into `solune/backend/src/api/chat/proposals.py` moving `store_proposal`, `get_proposal`, `confirm_proposal`, `cancel_proposal`, `store_recommendation`, `get_recommendation`, `upload_file` from `solune/backend/src/api/chat.py`
- [ ] T013 [US1] Extract plan mode endpoints into `solune/backend/src/api/chat/plans.py` moving all 14 plan functions (`send_plan_message`, `get_plan_endpoint`, `update_plan_endpoint`, `approve_plan_endpoint`, `exit_plan_mode_endpoint`, plan step CRUD) from `solune/backend/src/api/chat.py`
- [ ] T014 [P] [US1] Extract conversation CRUD endpoints into `solune/backend/src/api/chat/conversations.py` moving `create_conversation`, `list_conversations`, `update_conversation`, `delete_conversation` from `solune/backend/src/api/chat.py`
- [ ] T015 [US1] Extract SSE streaming endpoints into `solune/backend/src/api/chat/streaming.py` moving `send_message_stream`, `send_plan_message_stream` from `solune/backend/src/api/chat.py`
- [ ] T016 [US1] Create router aggregation in `solune/backend/src/api/chat/__init__.py` combining sub-routers from messages, proposals, plans, conversations, streaming per `contracts/chat-package-interface.md`
- [ ] T017 [US1] Delete original `solune/backend/src/api/chat.py` and update all imports across the codebase (search for `from src.api.chat import` and `from src.api import chat`)
- [ ] T018 [US1] Update test imports in `solune/backend/tests/unit/test_api_chat.py` and any other test files that import from `src.api.chat` to use new sub-module paths or barrel
- [ ] T019 [US1] Verify backward compatibility: `from src.api.chat import router` works, run `python -m pytest tests/unit/ -q --timeout=120`

**Checkpoint**: api/chat.py split complete — all 40 chat endpoints respond identically, all tests pass

---

## Phase 4: User Story 2 — Extract `ProposalOrchestrator` Service (Priority: P1)

**Goal**: Convert the 348-line `confirm_proposal()` god function into a testable `ProposalOrchestrator` service class with 6 focused private methods

**Independent Test**: `python -m pytest tests/unit/test_api_chat.py -k "confirm_proposal or proposal" -v` — all proposal tests pass; `ProposalOrchestrator` can be instantiated with mocked dependencies

**Dependencies**: Requires US1 (Phase 3) complete so `proposals.py` exists in `api/chat/`

### Implementation for User Story 2

- [ ] T020 [US2] Create `ProposalOrchestrator` class skeleton in `solune/backend/src/services/proposal_orchestrator.py` with `__init__(chat_state, chat_store)` and `async def confirm()` signature per `contracts/proposal-orchestrator-interface.md`
- [ ] T021 [US2] Extract `_validate_proposal()` method in `solune/backend/src/services/proposal_orchestrator.py` — retrieve proposal from cache/store, validate ownership and expiration
- [ ] T022 [US2] Extract `_apply_edits()` method in `solune/backend/src/services/proposal_orchestrator.py` — pure function applying user title/description edits
- [ ] T023 [P] [US2] Extract `_create_github_issue()` method in `solune/backend/src/services/proposal_orchestrator.py` — create GitHub issue from proposal, return (issue_url, issue_number)
- [ ] T024 [P] [US2] Extract `_add_to_project()` method in `solune/backend/src/services/proposal_orchestrator.py` — add issue to GitHub project board
- [ ] T025 [US2] Extract `_persist_status()` method in `solune/backend/src/services/proposal_orchestrator.py` — update proposal status in SQLite with retry logic
- [ ] T026 [US2] Extract `_broadcast_update()` method in `solune/backend/src/services/proposal_orchestrator.py` — send updated proposal to WebSocket clients (best-effort)
- [ ] T027 [US2] Wire `confirm()` method to delegate to `_validate_proposal` → `_apply_edits` → `_create_github_issue` → `_add_to_project` → `_persist_status` → `_broadcast_update` in `solune/backend/src/services/proposal_orchestrator.py`
- [ ] T028 [US2] Update `solune/backend/src/api/chat/proposals.py` to instantiate and call `ProposalOrchestrator.confirm()` instead of inline logic
- [ ] T029 [US2] Verify: `python -m pytest tests/unit/test_api_chat.py -k "confirm_proposal or proposal" -v` and `python -m pytest tests/unit/ -q --timeout=120`

**Checkpoint**: ProposalOrchestrator extracted — confirm_proposal endpoint returns identical responses, error handling preserved

---

## Phase 5: User Story 3 — Consolidate Backend Global State → `ChatStateManager` (Priority: P1)

**Goal**: Replace 4 module-level mutable dicts (`_messages`, `_proposals`, `_recommendations`, `_locks`) with a `ChatStateManager` class using `BoundedDict` caches, injected via FastAPI `Depends()`

**Independent Test**: `python -m pytest tests/unit/test_api_chat.py -v --timeout=120` — all chat tests pass; no module-level mutable dicts remain in `api/chat/`; `ChatStateManager` respects capacity limits

**Dependencies**: Requires US1 (Phase 3) complete so `state.py` exists in `api/chat/`

### Implementation for User Story 3

- [ ] T030 [US3] Implement full `ChatStateManager` class in `solune/backend/src/api/chat/state.py` with `BoundedDict` backing for `_messages` (max 1000), `_proposals` (max 5000), `_recommendations` (max 5000), `_locks` (max 10000) and `_global_lock` per `data-model.md` ChatStateManager section
- [ ] T031 [US3] Wire `ChatStateManager` instantiation to FastAPI lifespan in `solune/backend/src/main.py` — create on startup, attach to `app.state.chat_state_manager`, cleanup on shutdown
- [ ] T032 [US3] Create `Depends()` provider function for `ChatStateManager` in `solune/backend/src/dependencies.py` resolving from `request.app.state.chat_state_manager`
- [ ] T033 [US3] Update `solune/backend/src/api/chat/messages.py` to use injected `ChatStateManager` instead of module-level `_messages` dict
- [ ] T034 [US3] Update `solune/backend/src/api/chat/proposals.py` to use injected `ChatStateManager` instead of module-level `_proposals` dict
- [ ] T035 [US3] Update `solune/backend/src/api/chat/streaming.py` to use injected `ChatStateManager` instead of module-level state dicts
- [ ] T036 [US3] Update `solune/backend/src/api/chat/plans.py` to use injected `ChatStateManager` for state access
- [ ] T037 [US3] Update `solune/backend/src/api/chat/helpers.py` to accept `ChatStateManager` as parameter instead of accessing module globals
- [ ] T038 [US3] Remove all module-level mutable dicts (`_messages`, `_proposals`, `_recommendations`, `_locks`, `_global_lock`) from `solune/backend/src/api/chat/` sub-modules
- [ ] T039 [US3] Verify: no module-level `dict` in `api/chat/` (`grep -r "^_messages\|^_proposals\|^_recommendations\|^_locks" src/api/chat/`), run `python -m pytest tests/unit/ -q --timeout=120`

**Checkpoint**: All in-memory state consolidated in ChatStateManager — capacity-limited, lifecycle-managed, injectable

---

## Phase 6: User Story 4 — Split `api/webhooks.py` → `api/webhooks/` Package (Priority: P2)

**Goal**: Decompose the 1033-line monolithic `api/webhooks.py` into 6 focused sub-modules inside an `api/webhooks/` package, organized by GitHub event type

**Independent Test**: `python -m pytest tests/unit/test_webhooks.py -v --timeout=120` — all webhook tests pass; `from src.api.webhooks import router` works

### Implementation for User Story 4

- [ ] T040 [P] [US4] Extract signature verification and payload parsing into `solune/backend/src/api/webhooks/common.py` with `verify_signature`, `parse_webhook_payload`, `WebhookContext` class per `contracts/webhooks-package-interface.md`
- [ ] T041 [P] [US4] Extract PR event handlers into `solune/backend/src/api/webhooks/pull_requests.py` moving `handle_pull_request_event` and related PR handlers from `solune/backend/src/api/webhooks.py`
- [ ] T042 [P] [US4] Extract CI check handlers into `solune/backend/src/api/webhooks/check_runs.py` moving `handle_check_run_event` and related check run handlers from `solune/backend/src/api/webhooks.py`
- [ ] T043 [P] [US4] Extract issue event handlers into `solune/backend/src/api/webhooks/issues.py` moving `handle_issues_event` and related issue handlers from `solune/backend/src/api/webhooks.py`
- [ ] T044 [US4] Create dispatch registry in `solune/backend/src/api/webhooks/handlers.py` with `WEBHOOK_HANDLERS` dict mapping event type → handler function per `contracts/webhooks-package-interface.md`
- [ ] T045 [US4] Create router aggregation in `solune/backend/src/api/webhooks/__init__.py` combining sub-routers from pull_requests, check_runs, issues, handlers
- [ ] T046 [US4] Delete original `solune/backend/src/api/webhooks.py` and update all imports across the codebase
- [ ] T047 [US4] Update test imports in `solune/backend/tests/unit/test_webhooks.py` and verify: `python -m pytest tests/unit/test_webhooks.py -v --timeout=120`

**Checkpoint**: webhooks.py split complete — all event handlers respond identically, signature verification unchanged

---

## Phase 7: User Story 5 — Split `services/api.ts` → `services/api/` Package (Priority: P2)

**Goal**: Decompose the 1876-line monolithic `services/api.ts` into 18 domain-scoped files plus a barrel re-export, improving code-splitting and review scope

**Independent Test**: `npm run build` succeeds; `npm test` passes; `import { chatApi } from '@/services/api'` resolves correctly

### Implementation for User Story 5

- [ ] T048 [P] [US5] Extract `authApi` into `solune/frontend/src/services/api/auth.ts` importing from `./client`
- [ ] T049 [P] [US5] Extract `chatApi`, `conversationApi` into `solune/frontend/src/services/api/chat.ts` importing from `./client`
- [ ] T050 [P] [US5] Extract `boardApi` into `solune/frontend/src/services/api/board.ts` importing from `./client`
- [ ] T051 [P] [US5] Extract `tasksApi` into `solune/frontend/src/services/api/tasks.ts` importing from `./client`
- [ ] T052 [P] [US5] Extract `projectsApi` into `solune/frontend/src/services/api/projects.ts` importing from `./client`
- [ ] T053 [P] [US5] Extract `settingsApi` into `solune/frontend/src/services/api/settings.ts` importing from `./client`
- [ ] T054 [P] [US5] Extract `workflowApi` into `solune/frontend/src/services/api/workflow.ts` importing from `./client`
- [ ] T055 [P] [US5] Extract `metadataApi`, `signalApi` into `solune/frontend/src/services/api/metadata.ts` importing from `./client`
- [ ] T056 [P] [US5] Extract `agentsApi`, `agentToolsApi` into `solune/frontend/src/services/api/agents.ts` importing from `./client`
- [ ] T057 [P] [US5] Extract `pipelinesApi` into `solune/frontend/src/services/api/pipelines.ts` importing from `./client`
- [ ] T058 [P] [US5] Extract `choresApi` into `solune/frontend/src/services/api/chores.ts` importing from `./client`
- [ ] T059 [P] [US5] Extract `toolsApi` into `solune/frontend/src/services/api/tools.ts` importing from `./client`
- [ ] T060 [P] [US5] Extract `appsApi` into `solune/frontend/src/services/api/apps.ts` importing from `./client`
- [ ] T061 [P] [US5] Extract `activityApi` into `solune/frontend/src/services/api/activity.ts` importing from `./client`
- [ ] T062 [P] [US5] Extract `cleanupApi` into `solune/frontend/src/services/api/cleanup.ts` importing from `./client`
- [ ] T063 [P] [US5] Extract `modelsApi` into `solune/frontend/src/services/api/models.ts` importing from `./client`
- [ ] T064 [P] [US5] Extract `mcpApi` into `solune/frontend/src/services/api/mcp.ts` importing from `./client`
- [ ] T065 [US5] Create barrel re-export in `solune/frontend/src/services/api/index.ts` exporting all namespace objects per `contracts/frontend-api-package-interface.md`
- [ ] T066 [US5] Delete original `solune/frontend/src/services/api.ts` and update any direct imports across the codebase
- [ ] T067 [US5] Verify: `npm run build` succeeds, `npm test` passes, bundle size within ±5%

**Checkpoint**: services/api.ts split complete — all API namespaces importable via barrel, tree-shaking enabled

---

## Phase 8: User Story 6 — Domain-Scoped Types → `types/*.ts` (Priority: P2)

**Goal**: Split the 1525-line `types/index.ts` into 10 domain-scoped files plus a barrel re-export, reducing merge conflicts and improving IDE navigation

**Independent Test**: `npx tsc --noEmit` reports zero new errors; `npm test` passes; `import { ChatMessage } from '@/types'` resolves correctly

### Implementation for User Story 6

- [ ] T068 [P] [US6] Create `solune/frontend/src/types/common.ts` with shared types (`PaginatedResponse`, `ApiError`, `UUID`, `DateString`, `UserSession`) per `contracts/domain-types-interface.md`
- [ ] T069 [P] [US6] Extract chat domain types into `solune/frontend/src/types/chat.ts` (`ChatMessage`, `ChatMessageRequest`, `AITaskProposal`, `IssueRecommendation`, `Conversation`, `ProposalConfirmRequest`)
- [ ] T070 [P] [US6] Extract board domain types into `solune/frontend/src/types/board.ts` (`BoardItem`, `BoardColumn`, `BoardView`, `DragResult`)
- [ ] T071 [P] [US6] Extract pipeline domain types into `solune/frontend/src/types/pipeline.ts` (`Pipeline`, `PipelineStep`, `PipelineRun`, `StepStatus`)
- [ ] T072 [P] [US6] Extract agent domain types into `solune/frontend/src/types/agents.ts` (`Agent`, `AgentConfig`, `AgentPreview`, `LifecycleStatus`)
- [ ] T073 [P] [US6] Extract task domain types into `solune/frontend/src/types/tasks.ts` (`Task`, `TaskStatus`, `TaskPriority`, `TaskFilter`)
- [ ] T074 [P] [US6] Extract project domain types into `solune/frontend/src/types/projects.ts` (`Project`, `ProjectSettings`, `Repository`)
- [ ] T075 [P] [US6] Extract settings domain types into `solune/frontend/src/types/settings.ts` (`UserSettings`, `NotificationPrefs`, `ThemeConfig`)
- [ ] T076 [P] [US6] Extract chore domain types into `solune/frontend/src/types/chores.ts` (`Chore`, `ChoreStatus`, `ChoreFrequency`)
- [ ] T077 [P] [US6] Extract workflow domain types into `solune/frontend/src/types/workflow.ts` (`Workflow`, `WorkflowRun`, `WorkflowStep`)
- [ ] T078 [US6] Convert `solune/frontend/src/types/index.ts` to barrel re-export only — remove all type definitions, replace with `export * from './common'`, `export * from './chat'`, etc. per `contracts/domain-types-interface.md`
- [ ] T079 [US6] Verify: `npx tsc --noEmit` zero new errors, `npm run build` succeeds, `npm test` passes

**Checkpoint**: types/index.ts split complete — all types importable via barrel, no circular imports between domain files

---

## Phase 9: User Story 7 — Extract `services/bootstrap.py` from `main.py` (Priority: P3)

**Goal**: Extract bootstrap logic from `main.py` (859 lines) into `services/bootstrap.py`, reducing `main.py` to ~120 lines of declarative app definition

**Independent Test**: App starts correctly (`python -c "from src.main import app; print('OK')"`); `python -m pytest tests/unit/ -q --timeout=120` passes

### Implementation for User Story 7

- [ ] T080 [US7] Create `solune/backend/src/services/bootstrap.py` with function signatures: `async def initialize_services(app)`, `async def run_migrations(app)`, `async def start_background_tasks(app)`, `async def shutdown_services(app)` per `data-model.md` bootstrap section
- [ ] T081 [US7] Extract service initialization logic from `solune/backend/src/main.py` lifespan into `initialize_services()` in `solune/backend/src/services/bootstrap.py`
- [ ] T082 [US7] Extract migration running logic from `solune/backend/src/main.py` into `run_migrations()` in `solune/backend/src/services/bootstrap.py`
- [ ] T083 [US7] Extract background task setup (polling loops, agent sync, cleanup) from `solune/backend/src/main.py` into `start_background_tasks()` in `solune/backend/src/services/bootstrap.py`
- [ ] T084 [US7] Extract shutdown/cleanup logic from `solune/backend/src/main.py` into `shutdown_services()` in `solune/backend/src/services/bootstrap.py`
- [ ] T085 [US7] Simplify `solune/backend/src/main.py` to ~120 lines: app creation, middleware registration, router inclusion, lifespan calling bootstrap functions
- [ ] T086 [US7] Verify: app starts correctly, `python -m pytest tests/unit/ -q --timeout=120` passes

**Checkpoint**: main.py simplified to declarative app definition — all lifecycle logic in bootstrap.py

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Cleanup and consistency improvements that span multiple refactoring targets

- [ ] T087 [P] Standardize frontend test layout: move co-located `.test.tsx` files in `solune/frontend/src/components/layout/` to `solune/frontend/src/components/layout/__tests__/` per research.md R8 decision
- [ ] T088 Resolve circular dependency in `solune/backend/src/dependencies.py` — replace lazy `_get_session_dep()` import workaround with direct implementation per research.md R9 decision
- [ ] T089 [P] Add barrel exports for `solune/frontend/src/hooks/index.ts` re-exporting domain hooks
- [ ] T090 [P] Add barrel exports for `solune/frontend/src/lib/index.ts` re-exporting utility functions
- [ ] T091 [P] Add barrel exports for `solune/frontend/src/utils/index.ts` re-exporting utility functions
- [ ] T092 Update `solune/backend/src/api/__init__.py` to import from new package paths (`api/chat/`, `api/webhooks/`)
- [ ] T093 Run full backend test suite: `cd solune/backend && python -m pytest tests/unit/ -q --timeout=120` (must maintain ≥80% coverage)
- [ ] T094 Run full frontend test suite: `cd solune/frontend && npm test` (must maintain ≥60% statement coverage)
- [ ] T095 Verify no circular import warnings in backend: `python -c "from src.main import app"` completes without warnings
- [ ] T096 Update `architecture.md` and `project-structure.md` documentation if they reference old file paths

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — creates shared modules used by all backend stories
- **US1: Chat Split (Phase 3)**: Depends on Foundational (Phase 2) — BLOCKS US2 and US3
- **US2: ProposalOrchestrator (Phase 4)**: Depends on US1 (Phase 3) — `proposals.py` must exist
- **US3: ChatStateManager (Phase 5)**: Depends on US1 (Phase 3) — `state.py` must exist
- **US4: Webhooks Split (Phase 6)**: Depends on Foundational (Phase 2) only — independent of US1
- **US5: Frontend API Split (Phase 7)**: Depends on Setup (Phase 1) only — independent of backend work
- **US6: Domain Types (Phase 8)**: Depends on Setup (Phase 1) only — independent, parallel with US5
- **US7: Bootstrap Extract (Phase 9)**: Depends on US3 (Phase 5) — ChatStateManager wiring in main.py should settle first
- **Polish (Phase 10)**: Depends on all user stories being complete

### User Story Dependencies

```text
Phase 1: Setup ─────────────────────────────────────────────────────────────┐
Phase 2: Foundational ──────────────────────────────────────────────────────┤
                                                                            │
Phase 3: US1 (Chat Split) ─────┬───────────────────────────────────────────┤
                                ├─► Phase 4: US2 (ProposalOrchestrator) ───┤
                                └─► Phase 5: US3 (ChatStateManager) ───────┤
                                                          │                │
Phase 6: US4 (Webhooks Split) ──── (independent) ─────────┤                │
Phase 7: US5 (Frontend API) ────── (independent) ─────────┤                │
Phase 8: US6 (Domain Types) ────── (independent) ─────────┤                │
                                                           │                │
Phase 9: US7 (Bootstrap) ──────── (after US3) ────────────┤                │
                                                           │                │
Phase 10: Polish ──────────────── (after all) ─────────────┘                │
```

### Within Each User Story

- Shared modules (helpers, state, models) before endpoints
- Internal modules (dispatch) before external-facing modules (streaming)
- Router aggregation (`__init__.py`) after all sub-modules exist
- Delete original file only after all sub-modules are wired
- Import updates after deletion
- Verification as final step

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T003, T004, T005)
- All Foundational tasks marked [P] can run in parallel (T007, T008, T009)
- Once Foundational is complete, US4 (Webhooks) can proceed independently of US1 (Chat)
- US5 (Frontend API) and US6 (Domain Types) are fully independent of all backend work and can proceed in parallel
- Within US4 (Webhooks): T040, T041, T042, T043 can all run in parallel
- Within US5 (Frontend API): T048–T064 can all run in parallel (each is a separate domain file)
- Within US6 (Domain Types): T068–T077 can all run in parallel (each is a separate domain file)
- Within US2 (ProposalOrchestrator): T023, T024 can run in parallel
- All Polish tasks marked [P] can run in parallel (T087, T089, T090, T091)

---

## Parallel Example: User Story 1 (Chat Split)

```bash
# Phase 2 foundational tasks can run in parallel:
Task T007: "Extract helpers into solune/backend/src/api/chat/helpers.py"
Task T008: "Extract FileUploadResponse into solune/backend/src/api/chat/models.py"

# Conversation extraction is independent of other endpoint modules:
Task T014: "Extract conversations into solune/backend/src/api/chat/conversations.py"
# can run parallel with T010–T013 since conversations.py has no internal deps
```

## Parallel Example: User Story 5 (Frontend API Split)

```bash
# All domain API files can be extracted in parallel (each touches a different file):
Task T048: "Extract authApi into solune/frontend/src/services/api/auth.ts"
Task T049: "Extract chatApi into solune/frontend/src/services/api/chat.ts"
Task T050: "Extract boardApi into solune/frontend/src/services/api/board.ts"
Task T051: "Extract tasksApi into solune/frontend/src/services/api/tasks.ts"
Task T052: "Extract projectsApi into solune/frontend/src/services/api/projects.ts"
# ... (all T048-T064 in parallel)
```

## Parallel Example: User Story 6 (Domain Types)

```bash
# All domain type files can be extracted in parallel (each touches a different file):
Task T068: "Create solune/frontend/src/types/common.ts"
Task T069: "Extract chat types into solune/frontend/src/types/chat.ts"
Task T070: "Extract board types into solune/frontend/src/types/board.ts"
# ... (all T068-T077 in parallel)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (shared modules)
3. Complete Phase 3: User Story 1 — Split `api/chat.py`
4. **STOP and VALIDATE**: Run full backend test suite, verify all 40 chat endpoints respond identically
5. This alone is the "single biggest maintainability win" per the modularity review

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add US1 (Chat Split) → Test → Verify (MVP! — 2930 lines → 10 files)
3. Add US2 (ProposalOrchestrator) → Test → Verify (348-line god function → testable service)
4. Add US3 (ChatStateManager) → Test → Verify (4 global dicts → managed class)
5. Add US4 (Webhooks Split) → Test → Verify (1033 lines → 6 files)
6. Add US5 + US6 (Frontend) → Build + Test → Verify (3400 lines → ~30 files)
7. Add US7 (Bootstrap) → Test → Verify (859 lines → ~120 + ~700)
8. Polish → Final verification

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - **Developer A**: US1 (Chat Split) → US2 (ProposalOrchestrator) → US3 (ChatStateManager)
   - **Developer B**: US4 (Webhooks Split) → US7 (Bootstrap)
   - **Developer C**: US5 (Frontend API) + US6 (Domain Types)
3. All converge for Phase 10 (Polish)

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific refactoring target for traceability
- Each user story should be independently completable and verifiable via existing tests
- No new tests needed — 5200+ backend + 2200+ frontend tests serve as regression suite
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- Backward compatibility maintained via barrel re-exports (`__init__.py` / `index.ts`)
- Avoid: cross-module circular imports, removing public exports, changing API endpoint URLs
