# Tasks: Codebase Modularity Review

**Input**: Design documents from `specs/002-codebase-modularity-review/`
**Prerequisites**: `specs/002-codebase-modularity-review/spec.md`

**Tests**: Dedicated test-writing tasks are NOT explicitly requested in the feature specification. Verification tasks (T009, T010, T099, T100) confirm existing tests continue to pass after each refactoring step (FR-007, SC-004).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. Each user story corresponds to one of the top-6 refactoring targets. User Story 7 (test layout standardization) is a cross-cutting concern.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the sub-package scaffolding, re-export shims, and shared utilities that every refactoring target depends on.

- [x] T001 Create backend chat sub-package directory and `__init__.py` with re-exports in `solune/backend/src/api/chat/__init__.py`
- [x] T002 [P] Create backend webhooks sub-package directory and `__init__.py` with re-exports in `solune/backend/src/api/webhooks/__init__.py`
- [ ] T003 [P] Create frontend domain API module directory and barrel `index.ts` with re-exports in `solune/frontend/src/services/api/index.ts`
- [ ] T004 [P] Create frontend domain types directory and barrel `index.ts` with re-exports in `solune/frontend/src/types/index.ts` (temporary shim)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extract shared utilities, types, and state infrastructure that multiple user stories depend on. MUST complete before any user story work begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T005 Extract shared chat types, constants, and persistence-retry config from `solune/backend/src/api/chat.py` (lines 70-102) into `solune/backend/src/api/chat/constants.py`
- [x] T006 [P] Extract SQLite persistence helpers (message CRUD, proposal persistence, recommendation persistence) from `solune/backend/src/api/chat.py` (lines 89-286) into `solune/backend/src/api/chat/persistence.py`
- [ ] T007 [P] Extract shared API infrastructure (ApiError class, getCsrfToken, normalizeApiError, onAuthExpired, STATE_CHANGING_METHODS) from `solune/frontend/src/services/api.ts` (lines 105-230) into `solune/frontend/src/services/api/client.ts`
- [ ] T008 [P] Extract shared/cross-domain TypeScript types (User, AuthResponse, APIError, common enums, utility types) from `solune/frontend/src/types/index.ts` into `solune/frontend/src/types/shared.ts`
- [ ] T009 Verify all existing backend tests pass after persistence and constants extraction (`uv run pytest` from `solune/backend/`)
- [ ] T010 Verify all existing frontend tests pass after shared API client and types extraction (`npm run test` from `solune/frontend/`)

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 — Split Monolithic Backend Chat Endpoint (Priority: P1) 🎯 MVP

**Goal**: Split the 2930-line `solune/backend/src/api/chat.py` into focused modules within a `chat/` sub-package so each concern (messages, proposals, plans, dispatch, streaming) can be navigated, edited, and tested independently.

**Independent Test**: Run the full backend test suite and verify every existing chat endpoint returns identical responses. Each new module can be imported and tested in isolation.

### Implementation for User Story 1

- [x] T011 [US1] Extract message endpoints (create_conversation, list_conversations, update_conversation, delete_conversation, get_messages, clear_messages, send_message) from `solune/backend/src/api/chat.py` into `solune/backend/src/api/chat/messages.py`
- [x] T012 [US1] Extract streaming endpoint (send_message_stream and SSE helpers) from `solune/backend/src/api/chat.py` into `solune/backend/src/api/chat/streaming.py`
- [x] T013 [US1] Extract proposal endpoints (confirm_proposal, cancel_proposal) and recommendation logic from `solune/backend/src/api/chat.py` into `solune/backend/src/api/chat/proposals.py`
- [x] T014 [US1] Extract plan endpoints (send_plan_message, send_plan_message_stream, get_plan_endpoint, plan step CRUD) from `solune/backend/src/api/chat.py` into `solune/backend/src/api/chat/plans.py`
- [x] T015 [US1] Extract file upload endpoint and validation helpers from `solune/backend/src/api/chat.py` into `solune/backend/src/api/chat/uploads.py`
- [x] T016 [US1] Update `solune/backend/src/api/chat/__init__.py` to compose the combined router from all sub-module routers, preserving all URL prefixes and tags
- [x] T017 [US1] Update `solune/backend/src/api/__init__.py` (or wherever the chat router is registered) to import from the new `chat` package instead of the old monolithic file
- [x] T018 [US1] Remove the original monolithic `solune/backend/src/api/chat.py` file after all routes are migrated and verified
- [ ] T019 [US1] Verify no single file in `solune/backend/src/api/chat/` exceeds 600 lines (SC-001) and all existing tests pass

**Checkpoint**: User Story 1 delivers the single biggest backend maintainability win. All chat endpoints work identically to before.

---

## Phase 4: User Story 2 — Extract Proposal Orchestration into a Dedicated Service (Priority: P1)

**Goal**: Extract the ~346-line `confirm_proposal()` god function into a dedicated `ProposalOrchestrator` service class with individually testable methods and dependency injection for all external dependencies.

**Independent Test**: Each orchestrator method can be unit-tested with mocked dependencies. The end-to-end flow via the existing endpoint produces identical behavior.

### Implementation for User Story 2

- [ ] T020 [US2] Create `ProposalOrchestrator` service class skeleton with constructor accepting injected dependencies (GitHub client, workflow manager, agent assignment service, polling service, WebSocket broadcast) in `solune/backend/src/services/proposal_orchestrator.py`
- [ ] T021 [US2] Extract proposal validation logic (exists check, expiry check) into `ProposalOrchestrator.validate_proposal()` method in `solune/backend/src/services/proposal_orchestrator.py`
- [ ] T022 [US2] Extract edit-application logic into `ProposalOrchestrator.apply_edits()` method in `solune/backend/src/services/proposal_orchestrator.py`
- [ ] T023 [US2] Extract GitHub issue creation and project linkage into `ProposalOrchestrator.create_github_issue()` method in `solune/backend/src/services/proposal_orchestrator.py`
- [ ] T024 [US2] Extract workflow setup and agent assignment into `ProposalOrchestrator.setup_workflow()` method in `solune/backend/src/services/proposal_orchestrator.py`
- [ ] T025 [US2] Extract polling start and WebSocket broadcast into `ProposalOrchestrator.start_polling_and_broadcast()` method in `solune/backend/src/services/proposal_orchestrator.py`
- [ ] T026 [US2] Create `ProposalOrchestrator.confirm()` orchestration method that calls each step in sequence in `solune/backend/src/services/proposal_orchestrator.py`
- [ ] T027 [US2] Register `ProposalOrchestrator` as a FastAPI dependency via `Depends()` in `solune/backend/src/dependencies.py`
- [ ] T028 [US2] Refactor `confirm_proposal()` endpoint in `solune/backend/src/api/chat/proposals.py` to delegate to `ProposalOrchestrator.confirm()`
- [ ] T029 [US2] Verify all existing proposal-related tests pass and the end-to-end confirmation flow is unchanged

**Checkpoint**: User Story 2 makes the highest-risk code path testable and extensible.

---

## Phase 5: User Story 3 — Split Monolithic Frontend API Client (Priority: P1)

**Goal**: Split the 1876-line `solune/frontend/src/services/api.ts` into domain-scoped modules so each domain's API logic can be edited, tested, and code-split independently.

**Independent Test**: Every API call produces the same request/response. All existing frontend tests pass. Each domain module can be imported independently.

### Implementation for User Story 3

- [ ] T030 [P] [US3] Extract `authApi` namespace into `solune/frontend/src/services/api/auth.ts`
- [ ] T031 [P] [US3] Extract `projectsApi` and `tasksApi` namespaces into `solune/frontend/src/services/api/projects.ts`
- [ ] T032 [P] [US3] Extract `conversationApi` and `chatApi` namespaces into `solune/frontend/src/services/api/chat.ts`
- [ ] T033 [P] [US3] Extract `boardApi` namespace into `solune/frontend/src/services/api/board.ts`
- [ ] T034 [P] [US3] Extract `settingsApi` namespace into `solune/frontend/src/services/api/settings.ts`
- [ ] T035 [P] [US3] Extract `workflowApi` namespace into `solune/frontend/src/services/api/workflow.ts`
- [ ] T036 [P] [US3] Extract `metadataApi` and `signalApi` namespaces into `solune/frontend/src/services/api/metadata.ts`
- [ ] T037 [P] [US3] Extract `mcpApi` namespace into `solune/frontend/src/services/api/mcp.ts`
- [ ] T038 [P] [US3] Extract `cleanupApi` namespace into `solune/frontend/src/services/api/cleanup.ts`
- [ ] T039 [P] [US3] Extract `choresApi` namespace into `solune/frontend/src/services/api/chores.ts`
- [ ] T040 [P] [US3] Extract `agentsApi` namespace into `solune/frontend/src/services/api/agents.ts`
- [ ] T041 [P] [US3] Extract `pipelinesApi` namespace into `solune/frontend/src/services/api/pipelines.ts`
- [ ] T042 [P] [US3] Extract `modelsApi`, `toolsApi`, and `agentToolsApi` namespaces into `solune/frontend/src/services/api/tools.ts`
- [ ] T043 [P] [US3] Extract `appsApi` namespace into `solune/frontend/src/services/api/apps.ts`
- [ ] T044 [P] [US3] Extract `activityApi` namespace into `solune/frontend/src/services/api/activity.ts`
- [ ] T045 [US3] Update `solune/frontend/src/services/api/index.ts` barrel to re-export all domain API modules, preserving the same public export surface
- [ ] T046 [US3] Update all import sites across `solune/frontend/src/` to import from domain-specific modules or the barrel (search-and-replace `from '../services/api'` and `from '../../services/api'` etc.)
- [ ] T047 [US3] Remove the original monolithic `solune/frontend/src/services/api.ts` file after all imports are migrated
- [ ] T048 [US3] Verify no single file in `solune/frontend/src/services/api/` exceeds 400 lines (SC-002) and all frontend tests, lint, type-check, and build pass

**Checkpoint**: User Story 3 delivers the highest-impact frontend maintainability improvement. All API integrations work identically.

---

## Phase 6: User Story 4 — Domain-Scoped Frontend Types (Priority: P2)

**Goal**: Split the 1525-line `solune/frontend/src/types/index.ts` into domain-scoped type files so developers edit only the relevant domain's types and cross-domain coupling is visible and minimized.

**Independent Test**: The full frontend build succeeds with zero type errors. All existing type references resolve correctly.

### Implementation for User Story 4

- [ ] T049 [P] [US4] Extract auth and user types into `solune/frontend/src/types/auth.ts`
- [ ] T050 [P] [US4] Extract project and task types into `solune/frontend/src/types/projects.ts`
- [ ] T051 [P] [US4] Extract chat, conversation, and mention types into `solune/frontend/src/types/chat.ts`
- [ ] T052 [P] [US4] Extract proposal and recommendation types into `solune/frontend/src/types/proposals.ts`
- [ ] T053 [P] [US4] Extract board and issue types into `solune/frontend/src/types/board.ts`
- [ ] T054 [P] [US4] Extract settings and preferences types into `solune/frontend/src/types/settings.ts`
- [ ] T055 [P] [US4] Extract workflow and pipeline types into `solune/frontend/src/types/pipeline.ts`
- [ ] T056 [P] [US4] Extract agent types into `solune/frontend/src/types/agents.ts`
- [ ] T057 [P] [US4] Extract signal types into `solune/frontend/src/types/signals.ts`
- [ ] T058 [P] [US4] Extract MCP types into `solune/frontend/src/types/mcp.ts`
- [ ] T059 [P] [US4] Extract cleanup types into `solune/frontend/src/types/cleanup.ts`
- [ ] T060 [P] [US4] Extract chore types into `solune/frontend/src/types/chores.ts`
- [ ] T061 [P] [US4] Extract plan and plan-step types into `solune/frontend/src/types/plans.ts`
- [ ] T062 [P] [US4] Extract activity and tool types into `solune/frontend/src/types/activity.ts`
- [ ] T063 [US4] Update `solune/frontend/src/types/index.ts` to be a barrel that re-exports from all domain type files and `shared.ts`, preserving backward compatibility
- [ ] T064 [US4] Update import sites across `solune/frontend/src/` to import from domain-specific type files where beneficial (optional — barrel re-exports maintain compatibility)
- [ ] T065 [US4] Verify no single domain type file exceeds 400 lines (SC-002) and all frontend tests, lint, type-check, and build pass

**Checkpoint**: User Story 4 makes type definitions navigable and reviewable by domain. All existing imports continue to work.

---

## Phase 7: User Story 5 — Consolidate Backend Global State into a Managed Class (Priority: P2)

**Goal**: Wrap the module-level `_messages`, `_proposals`, `_recommendations`, and `_locks` dictionaries into a `ChatStateManager` class with explicit initialization, cleanup, and concurrency controls, eliminating race condition risk.

**Independent Test**: Instantiate the state manager in a test, verify concurrent operations do not corrupt state, and confirm cleanup properly releases resources.

### Implementation for User Story 5

- [ ] T066 [US5] Create `ChatStateManager` class with typed state dictionaries, lock management, and initialization in `solune/backend/src/services/chat_state_manager.py`
- [ ] T067 [US5] Implement `ChatStateManager.get_lock()` with per-key asyncio.Lock creation and cleanup in `solune/backend/src/services/chat_state_manager.py`
- [ ] T068 [US5] Implement `ChatStateManager.get_messages()`, `set_messages()`, `get_proposal()`, `set_proposal()`, `get_recommendation()`, `set_recommendation()` with concurrency-safe access in `solune/backend/src/services/chat_state_manager.py`
- [ ] T069 [US5] Implement `ChatStateManager.cleanup()` for graceful shutdown (release locks, clear caches) in `solune/backend/src/services/chat_state_manager.py`
- [ ] T070 [US5] Implement `ChatStateManager.create_test_instance()` factory method for isolated test instances in `solune/backend/src/services/chat_state_manager.py`
- [ ] T071 [US5] Instantiate `ChatStateManager` as a singleton during application lifespan in `solune/backend/src/main.py` and register as a FastAPI dependency in `solune/backend/src/dependencies.py`
- [ ] T072 [US5] Refactor all chat sub-modules (`messages.py`, `proposals.py`, `plans.py`, `streaming.py`, `uploads.py`, `persistence.py`) to inject `ChatStateManager` via `Depends()` instead of using module-level globals
- [ ] T073 [US5] Invoke `ChatStateManager.cleanup()` during application shutdown in `solune/backend/src/main.py` lifespan context
- [ ] T074 [US5] Verify all existing tests pass and no module-level mutable state remains in chat sub-package files

**Checkpoint**: User Story 5 eliminates race condition risk and enables proper lifecycle management of in-memory chat state.

---

## Phase 8: User Story 6 — Split Backend Webhooks Endpoint (Priority: P2)

**Goal**: Split the 1025-line `solune/backend/src/api/webhooks.py` into event-type-specific handler modules within a `webhooks/` sub-package so each event type can be modified and tested independently.

**Independent Test**: Send test webhook payloads for each event type and verify the correct handler module processes each event with identical behavior.

### Implementation for User Story 6

- [x] T075 [P] [US6] Extract webhook signature verification and shared utilities (verify_webhook_signature, extract_issue_number_from_pr, classify_pull_request_activity) from `solune/backend/src/api/webhooks.py` into `solune/backend/src/api/webhooks/utils.py`
- [x] T076 [P] [US6] Extract `_processed_delivery_ids` deduplication state and the main `github_webhook()` router dispatcher from `solune/backend/src/api/webhooks.py` into `solune/backend/src/api/webhooks/router.py`
- [x] T077 [P] [US6] Extract pull request event handlers (handle_pull_request_event, handle_copilot_pr_ready, update_issue_status_for_copilot_pr, _resolve_issue_for_pr, _get_auto_merge_pipeline) from `solune/backend/src/api/webhooks.py` into `solune/backend/src/api/webhooks/pull_requests.py`
- [x] T078 [P] [US6] Extract check run and check suite handlers (handle_check_run_event, handle_check_suite_event) from `solune/backend/src/api/webhooks.py` into `solune/backend/src/api/webhooks/check_runs.py`
- [x] T079 [US6] Update `solune/backend/src/api/webhooks/__init__.py` to compose the combined router from sub-module routers, preserving the `/github` endpoint path and webhook signature verification
- [x] T080 [US6] Update `solune/backend/src/api/__init__.py` (or wherever the webhook router is registered) to import from the new `webhooks` package
- [x] T081 [US6] Remove the original monolithic `solune/backend/src/api/webhooks.py` file after all handlers are migrated and verified
- [ ] T082 [US6] Verify all existing webhook-related tests pass and all webhook event types are handled identically

**Checkpoint**: User Story 6 makes webhook handling modular and extensible. Each event type is independently testable.

---

## Phase 9: User Story 7 — Standardize Frontend Test Layout (Priority: P3)

**Goal**: Migrate the 17% of frontend tests using `__tests__/` subdirectories to the co-located pattern (83% majority) and document the convention, so all tests follow a single discoverable layout.

**Independent Test**: All frontend tests are discovered and pass after migration. The test runner requires zero configuration changes.

### Implementation for User Story 7

- [ ] T083 [US7] Move tests from `solune/frontend/src/components/chores/__tests__/` to co-located `.test.tsx` files alongside their source components
- [ ] T084 [P] [US7] Move tests from `solune/frontend/src/components/tools/__tests__/` to co-located `.test.tsx` files alongside their source components
- [ ] T085 [P] [US7] Move tests from `solune/frontend/src/components/agents/__tests__/` to co-located `.test.tsx` files alongside their source components
- [ ] T086 [P] [US7] Move tests from `solune/frontend/src/components/ui/__tests__/` to co-located `.test.tsx` files alongside their source components
- [ ] T087 [P] [US7] Move tests from `solune/frontend/src/components/command-palette/__tests__/` to co-located `.test.tsx` files alongside their source components
- [ ] T088 [P] [US7] Move tests from `solune/frontend/src/components/onboarding/__tests__/` to co-located `.test.tsx` files alongside their source components
- [ ] T089 [P] [US7] Move tests from `solune/frontend/src/hooks/__tests__/` to co-located `.test.ts` files alongside their source hooks
- [ ] T090 [P] [US7] Move tests from `solune/frontend/src/__tests__/` to co-located files alongside their source modules
- [ ] T091 [US7] Remove all empty `__tests__/` directories after migration
- [ ] T092 [US7] Document the co-located test convention in `solune/frontend/CONTRIBUTING.md` or `solune/docs/testing.md` (whichever exists), specifying that test files must be placed alongside source files as `<ComponentName>.test.tsx` or `<module>.test.ts`
- [ ] T093 [US7] Verify all frontend tests are discovered by Vitest and pass after the migration (`npm run test` from `solune/frontend/`)

**Checkpoint**: All frontend tests follow a single, documented co-located convention.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that span multiple refactoring targets and final validation.

- [ ] T094 [P] Extract backend bootstrap and lifecycle logic from `solune/backend/src/main.py` (lines 21-537: auto_start_copilot_polling, discover_and_register_active_projects, restore_app_pipeline_polling, startup_agent_mcp_sync, polling_watchdog_loop, session_cleanup_loop) into `solune/backend/src/services/bootstrap.py` (FR-013)
- [ ] T095 [P] Resolve circular dependency workarounds in `solune/backend/src/dependencies.py` by using TYPE_CHECKING guards consistently and removing lazy import fallbacks where the split modules eliminate the cycles
- [ ] T096 [P] Add barrel exports for frontend hooks in `solune/frontend/src/hooks/index.ts`, `solune/frontend/src/lib/index.ts`, and `solune/frontend/src/utils/index.ts` to improve import ergonomics
- [ ] T097 Verify the full dependency graph across all split modules is acyclic — no circular imports in backend (`python -c "import src.api.chat"` etc.) and no circular references in frontend (`npm run build`) (FR-009, SC-009)
- [ ] T098 Verify frontend bundle size for individual pages does not increase by more than 2% after the API client split (SC-010)
- [ ] T099 Run the complete backend test suite (`uv run pytest` from `solune/backend/`) and confirm 100% of existing tests pass (SC-004)
- [ ] T100 Run the complete frontend test suite (`npm run test && npm run lint && npm run type-check && npm run build` from `solune/frontend/`) and confirm 100% of existing tests pass (SC-004)
- [ ] T101 Update `solune/docs/architecture.md` and `solune/docs/project-structure.md` to reflect the new sub-package structure for chat, webhooks, API client, and types

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phases 3–9)**: All depend on Foundational phase completion
  - US1 and US2 are tightly coupled (US2 refactors code inside the modules created by US1)
  - US3 and US4 can proceed in parallel (different files, different concerns)
  - US5 depends on US1 completion (refactors state used by the split modules)
  - US6 is fully independent of other stories
  - US7 is fully independent of other stories
- **Polish (Phase 10)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no dependencies on other stories
- **US2 (P1)**: Depends on US1 (the `confirm_proposal` endpoint moves to `chat/proposals.py` first, then the orchestrator is extracted from it)
- **US3 (P1)**: Can start after Foundational — independent of backend stories
- **US4 (P2)**: Can start after Foundational — independent of backend stories; can run in parallel with US3
- **US5 (P2)**: Depends on US1 (global state is consumed by the split chat modules; the state manager replaces module-level globals in those modules)
- **US6 (P2)**: Can start after Foundational — fully independent of all other stories
- **US7 (P3)**: Can start after Foundational — fully independent of all other stories

### Within Each User Story

- Extract shared utilities/types first
- Create new modules before removing old files
- Re-export from original paths to maintain backward compatibility during migration
- Remove original files only after all imports are updated
- Verify existing tests pass at each checkpoint

### Recommended Execution Order

1. **Phase 1**: Setup scaffolding (T001–T004)
2. **Phase 2**: Foundational extractions (T005–T010)
3. **US1**: Split chat.py (T011–T019) — single biggest backend win
4. **US2**: Extract ProposalOrchestrator (T020–T029) — requires US1
5. **US3 + US4 + US6 + US7** in parallel:
   - Track A: US3 split api.ts (T030–T048) → US4 split types (T049–T065)
   - Track B: US6 split webhooks.py (T075–T082)
   - Track C: US7 standardize test layout (T083–T093)
6. **US5**: Consolidate global state (T066–T074) — requires US1
7. **Phase 10**: Polish and cross-cutting (T094–T101)

---

## Parallel Examples per Story

### User Story 1

```text
# All sub-module extractions can begin in parallel (different target files):
T011 solune/backend/src/api/chat/messages.py
T012 solune/backend/src/api/chat/streaming.py
T013 solune/backend/src/api/chat/proposals.py
T014 solune/backend/src/api/chat/plans.py
T015 solune/backend/src/api/chat/uploads.py
```

### User Story 3

```text
# All domain API extractions can run in parallel (different target files):
T030 solune/frontend/src/services/api/auth.ts
T031 solune/frontend/src/services/api/projects.ts
T032 solune/frontend/src/services/api/chat.ts
T033 solune/frontend/src/services/api/board.ts
T034 solune/frontend/src/services/api/settings.ts
T035 solune/frontend/src/services/api/workflow.ts
...
```

### User Story 4

```text
# All domain type extractions can run in parallel (different target files):
T049 solune/frontend/src/types/auth.ts
T050 solune/frontend/src/types/projects.ts
T051 solune/frontend/src/types/chat.ts
T052 solune/frontend/src/types/proposals.ts
T053 solune/frontend/src/types/board.ts
...
```

### User Story 6

```text
# Webhook handler extractions can run in parallel (different target files):
T075 solune/backend/src/api/webhooks/utils.py
T076 solune/backend/src/api/webhooks/router.py
T077 solune/backend/src/api/webhooks/pull_requests.py
T078 solune/backend/src/api/webhooks/check_runs.py
```

### User Story 7

```text
# Test migration across domains can run in parallel (different directories):
T083 solune/frontend/src/components/chores/
T084 solune/frontend/src/components/tools/
T085 solune/frontend/src/components/agents/
T086 solune/frontend/src/components/ui/
T087 solune/frontend/src/components/command-palette/
T088 solune/frontend/src/components/onboarding/
T089 solune/frontend/src/hooks/
T090 solune/frontend/src/
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup scaffolding
2. Complete Phase 2: Foundational extractions
3. Complete US1: Split chat.py into 5 focused modules
4. **STOP and VALIDATE**: All existing chat tests pass, no file exceeds 600 lines
5. This single PR delivers the biggest maintainability improvement

### Incremental Delivery

1. **US1** splits the chat endpoint → biggest backend win, unblocks US2 and US5
2. **US2** extracts ProposalOrchestrator → makes highest-risk code path testable
3. **US3** splits the API client → biggest frontend win, enables code-splitting
4. **US4** scopes types by domain → improves navigation and reduces coupling
5. **US5** consolidates global state → eliminates race conditions
6. **US6** splits webhooks → improves webhook handler maintainability
7. **US7** standardizes test layout → improves developer experience
8. Each PR targets ONE refactoring target (SC-008)

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 → US2 → US5 (backend chat + orchestrator + state — sequential due to dependencies)
   - Developer B: US3 → US4 (frontend API + types — sequential, same domain)
   - Developer C: US6 + US7 (backend webhooks + test layout — independent)
3. All developers contribute to Phase 10 polish

---

## Summary

| Metric | Count |
|--------|-------|
| **Total tasks** | 101 |
| **Phase 1 — Setup** | 4 tasks |
| **Phase 2 — Foundational** | 6 tasks |
| **US1 — Split chat.py (P1)** | 9 tasks |
| **US2 — Extract ProposalOrchestrator (P1)** | 10 tasks |
| **US3 — Split api.ts (P1)** | 19 tasks |
| **US4 — Domain-scoped types (P2)** | 17 tasks |
| **US5 — Consolidate global state (P2)** | 9 tasks |
| **US6 — Split webhooks.py (P2)** | 8 tasks |
| **US7 — Standardize test layout (P3)** | 11 tasks |
| **Phase 10 — Polish** | 8 tasks |
| **Parallelizable tasks** | 57 tasks marked [P] |
| **MVP scope** | US1 only (Setup + Foundational + 9 US1 tasks = 19 tasks) |

---

## Notes

- All task lines follow the required checklist format: `- [ ] [TaskID] [P?] [Story?] Description with file path`
- `[P]` marks tasks that can run in parallel (target different files, no incomplete-task dependencies)
- `[USx]` labels appear only inside user story phases (Phases 3–9), not in Setup/Foundational/Polish
- Every task points to an exact repository path so an implementation agent can act without additional clarification
- SC-008 requires one refactoring target per PR — each user story should be a separate pull request
- No test tasks are included because they are not explicitly requested in the spec — all refactoring is validated by ensuring existing tests pass (FR-007, SC-004)
