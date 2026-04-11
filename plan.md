# Implementation Plan: Codebase Modularity Review

**Branch**: `copilot/speckit-plan-codebase-modularity-review` | **Date**: 2026-04-11 | **Spec**: [#1355](https://github.com/Boykai/solune/issues/1355)
**Input**: Parent issue #1355 — Codebase Modularity Review (Overall 6.5/10). Domain-driven at the directory level, but several monolithic hotspots undermine maintainability.

## Summary

Decompose the six highest-impact monolithic hotspots identified in the codebase modularity review into smaller, domain-scoped modules. The backend focus is splitting the 2,930-line `api/chat.py` into five route modules, extracting a `ProposalOrchestrator` service from the 345-line `confirm_proposal()` function, consolidating module-level global state into a managed `ChatStateManager` class, and splitting the 1,033-line `api/webhooks.py` into domain-specific handlers. The frontend focus is splitting the 1,876-line `services/api.ts` into per-domain API clients and the 1,525-line `types/index.ts` into domain-scoped type files. All refactors are behavior-preserving — no functional changes, only structural improvements to testability, code-splitting, and review scope.

| Phase | Scope | Key Output |
|-------|-------|------------|
| 1 | Backend — Split `api/chat.py` into route modules + state manager | `api/chat/` package with 7 modules |
| 2 | Backend — Extract `ProposalOrchestrator` service | `services/proposal_orchestrator.py` |
| 3 | Backend — Split `api/webhooks.py` into handlers | `api/webhooks/` package with 4 modules |
| 4 | Frontend — Split `services/api.ts` into domain clients | `services/api/` directory with 11 modules |
| 5 | Frontend — Domain-scoped types | `types/` directory with 9 domain files |
| 6 | Verification — full test suite, import audit, no regressions | All 5,200+ backend tests pass; all 2,200+ frontend tests pass |

## Technical Context

**Language/Version**: Python ≥3.12 (pyright targets 3.13, Dockerfile uses 3.14-slim) / TypeScript ~6.0.2
**Primary Dependencies**: FastAPI + aiosqlite + Pydantic v2 (backend); React 19 + @tanstack/react-query 5 + Zod 4 + Tailwind CSS 4 (frontend)
**Storage**: SQLite via aiosqlite — no schema changes in this refactor
**Testing**: pytest with `asyncio_mode=auto` (backend, coverage ≥80%, 5,200+ tests); Vitest (frontend, statements ≥60%, 2,200+ tests)
**Target Platform**: Linux server (containerized backend), SPA in modern browsers (frontend)
**Project Type**: Web application (Python backend + TypeScript frontend)
**Performance Goals**: Zero performance regression — refactors are purely structural
**Constraints**: Behavior-preserving only; no API contract changes; no migration changes; all existing tests must continue to pass unchanged
**Scale/Scope**: ~15 backend files affected, ~12 frontend files affected; 0 new features, 0 schema changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Feature fully specified in parent issue #1355 with detailed modularity audit, impact scores, and six ranked refactoring targets |
| II. Template-Driven Workflow | ✅ PASS | This plan follows `plan-template.md`; supplementary artifacts generated per workflow |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan agent produces plan; implement agent will execute phased tasks with clear handoffs |
| IV. Test Optionality | ✅ PASS | No new tests required — this is a behavior-preserving refactor. Existing tests serve as regression safety net (5,200+ backend, 2,200+ frontend) |
| V. Simplicity and DRY | ✅ PASS | Refactors reduce complexity by splitting monolithic files; `ChatStateManager` and `ProposalOrchestrator` are justified abstractions replacing ad-hoc patterns |

**Gate Result**: PASS — no violations. Proceed to Phase 0.

### Post-Design Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | All refactoring targets trace back to the modularity audit in #1355 |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates |
| III. Agent-Orchestrated Execution | ✅ PASS | Clear phase boundaries; each phase is independently verifiable via test suite |
| IV. Test Optionality | ✅ PASS | No new tests needed; existing tests validate behavioral equivalence |
| V. Simplicity and DRY | ✅ PASS | Each refactor removes complexity (smaller files, explicit state management, domain isolation) without introducing new abstractions beyond what's justified |

**Post-Design Gate Result**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
plan.md              # This file (speckit.plan output)
research.md          # Phase 0 output (refactoring decisions & research)
data-model.md        # Phase 1 output (module dependency model)
quickstart.md        # Phase 1 output (developer guide for executing refactors)
contracts/           # Phase 1 output (module interface contracts)
├── chat-api-modules.yaml
└── frontend-api-modules.yaml
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── api/
│   │   ├── chat/                          # NEW package replacing monolithic chat.py
│   │   │   ├── __init__.py                # Re-export router, preserves import paths
│   │   │   ├── router.py                  # Combined APIRouter with sub-routers
│   │   │   ├── messages.py                # GET/POST/DELETE /messages endpoints
│   │   │   ├── conversations.py           # CRUD /conversations endpoints
│   │   │   ├── proposals.py               # /proposals confirm + cancel, upload
│   │   │   ├── plans.py                   # /plans/* endpoints
│   │   │   ├── streaming.py               # /messages/stream, /messages/plan/stream SSE
│   │   │   └── state.py                   # ChatStateManager class (replaces module globals)
│   │   ├── webhooks/                      # NEW package replacing monolithic webhooks.py
│   │   │   ├── __init__.py                # Re-export router
│   │   │   ├── router.py                  # Main webhook dispatcher
│   │   │   ├── pull_requests.py           # PR event handlers
│   │   │   ├── check_runs.py             # Check run/suite event handlers
│   │   │   └── helpers.py                 # Shared utilities (signature verify, issue extraction)
│   │   └── ... (other api modules unchanged)
│   ├── services/
│   │   ├── proposal_orchestrator.py       # NEW — extracted from confirm_proposal()
│   │   └── ... (other services unchanged)
│   └── ... (models, middleware unchanged)
└── tests/
    └── unit/                              # 5,200+ existing tests serve as regression net

solune/frontend/
├── src/
│   ├── types/                             # REFACTOR: split index.ts → domain files
│   │   ├── index.ts                       # Barrel re-export (backward compat)
│   │   ├── chat.ts                        # Chat domain types
│   │   ├── board.ts                       # Board/kanban types
│   │   ├── pipeline.ts                    # Pipeline/workflow types
│   │   ├── tasks.ts                       # Task domain types
│   │   ├── agents.ts                      # Agent domain types
│   │   ├── settings.ts                    # Settings types
│   │   ├── plans.ts                       # Plan domain types
│   │   └── common.ts                      # Shared enums, base types
│   ├── services/
│   │   ├── api/                           # NEW directory replacing monolithic api.ts
│   │   │   ├── index.ts                   # Barrel re-export (backward compat)
│   │   │   ├── client.ts                  # Base HTTP client, ApiError, onAuthExpired
│   │   │   ├── auth.ts                    # authApi namespace
│   │   │   ├── chat.ts                    # chatApi + conversationApi namespaces
│   │   │   ├── board.ts                   # boardApi namespace
│   │   │   ├── projects.ts               # projectsApi namespace
│   │   │   ├── tasks.ts                   # tasksApi namespace
│   │   │   ├── settings.ts               # settingsApi namespace
│   │   │   ├── workflow.ts               # workflowApi namespace
│   │   │   ├── agents.ts                 # Agent-related API + types
│   │   │   ├── signal.ts                 # signalApi namespace
│   │   │   └── metadata.ts              # metadataApi, mcpApi, cleanupApi, choresApi
│   │   └── schemas/                       # Unchanged
│   └── ... (components, hooks, pages unchanged)
```

**Structure Decision**: Existing web application structure. Changes span both `solune/backend/` and `solune/frontend/`. No new top-level directories; all new files follow existing organizational patterns. Barrel re-exports ensure backward compatibility — existing `from src.api.chat import router` and `import { chatApi } from '../services/api'` paths continue to work.

## Complexity Tracking

> No Constitution Check violations — this section is intentionally empty.

---

## Phase 0: Research

See `research.md` for full details. Summary of decisions:

### R1: Chat Module Split Strategy

**Decision**: Convert `api/chat.py` (2,930 lines) into a Python package `api/chat/` with an `__init__.py` that re-exports the combined `router`. Internal modules share state via `state.py` (ChatStateManager singleton).

**Rationale**: A package-based split preserves the existing import path (`from src.api.chat import router`) via `__init__.py` re-exports. Each module gets its own router that is included in the combined router via `router.include_router()`. The ChatStateManager replaces the three module-level dicts (`_messages`, `_proposals`, `_locks`) with an explicit lifecycle-managed class.

### R2: ProposalOrchestrator Extraction Strategy

**Decision**: Extract the `confirm_proposal()` body (~345 lines spanning GitHub API calls, workflow setup, agent assignment, polling start, and WebSocket broadcast) into a `ProposalOrchestrator` service class with individually testable methods.

**Rationale**: The god function violates single-responsibility and is untestable in isolation. A service class with methods like `validate_proposal()`, `setup_github_workflow()`, `assign_agent()`, `start_polling()`, and `broadcast_result()` allows mocking individual steps in tests. The service is injected via FastAPI `Depends()`, consistent with existing DI patterns.

### R3: Webhooks Split Strategy

**Decision**: Convert `api/webhooks.py` (1,033 lines) into a package `api/webhooks/` with handlers split by GitHub event type: `pull_requests.py`, `check_runs.py`, and shared `helpers.py`.

**Rationale**: The webhook dispatcher (`github_webhook()`) is a natural routing point — it already switches on event type. Moving each handler to its own module reduces file size to ~300-400 lines each and makes PR reviews scoped to a single event type.

### R4: Frontend API Client Split Strategy

**Decision**: Replace `services/api.ts` (1,876 lines) with a `services/api/` directory containing one file per API domain. A barrel `index.ts` re-exports all namespace objects for backward compatibility.

**Rationale**: The monolithic client prevents tree-shaking and makes code reviews span unrelated domains. Per-domain files improve code-splitting (lazy-loaded pages only import the API namespaces they need) and reduce merge conflicts. The shared `client.ts` module contains `ApiError`, `onAuthExpired`, and the base fetch wrapper.

### R5: Frontend Types Split Strategy

**Decision**: Replace the monolithic `types/index.ts` (1,525 lines) with domain-scoped files (`chat.ts`, `board.ts`, `pipeline.ts`, `tasks.ts`, `agents.ts`, `settings.ts`, `plans.ts`, `common.ts`). The `index.ts` becomes a barrel that re-exports everything.

**Rationale**: A single types file forces all consumers to parse 1,525 lines for any import. Domain-scoped files reduce cognitive load and improve IDE navigation. Cross-domain type references use explicit imports from sibling files (e.g., `import { Project } from './common'`).

### R6: Global State Consolidation Strategy

**Decision**: Wrap the three module-level dicts (`_messages: dict[str, list[ChatMessage]]`, `_proposals: dict[str, AITaskProposal]`, `_locks: dict[str, asyncio.Lock]`) in a `ChatStateManager` class instantiated during the app lifespan.

**Rationale**: Module-level dicts have no lifecycle management — they accumulate entries indefinitely and create race condition risks under concurrent access. The `ChatStateManager` class provides explicit initialization, cleanup, capacity bounds (using `BoundedDict` for locks), and thread-safe access patterns. It's registered on `app.state` like other singletons and injected via `Depends()`.

---

## Phase 1: Design & Contracts

### 1.1 — Backend `api/chat/` Package Design

The monolithic `api/chat.py` (2,930 lines, 32 functions, 14 endpoints) is split into:

| Module | Lines (est.) | Endpoints | Functions |
|--------|-------------|-----------|-----------|
| `state.py` | ~80 | 0 | `ChatStateManager` class with `get_lock()`, `get_messages()`, `set_messages()`, `get_proposal()`, `set_proposal()` |
| `conversations.py` | ~120 | 4 | `create_conversation()`, `list_conversations()`, `update_conversation()`, `delete_conversation()` |
| `messages.py` | ~450 | 3 | `get_messages()`, `clear_messages()`, `send_message()`, helper functions for persistence and signal delivery |
| `proposals.py` | ~150 | 2 | `confirm_proposal()` (thin wrapper calling `ProposalOrchestrator`), `cancel_proposal()`, `upload_file()` |
| `plans.py` | ~300 | 6+ | All `/plans/*` endpoints |
| `streaming.py` | ~500 | 2 | `send_message_stream()`, `send_plan_message_stream()`, SSE helper functions |
| `router.py` | ~30 | 0 | Combines sub-routers into single `router` |
| `__init__.py` | ~5 | 0 | Re-exports `router` for backward compat |

**Shared dependencies** between modules:
- `state.py` → imported by all endpoint modules for state access
- `messages.py` → `_persist_message()`, `_retry_persist()` used by streaming.py
- Helper functions (`_resolve_repository()`, `_handle_agent_command()`, etc.) → stay in `messages.py` or move to a `_helpers.py` internal module

### 1.2 — `ProposalOrchestrator` Service Design

```python
class ProposalOrchestrator:
    """Orchestrates the multi-step proposal confirmation workflow."""

    def __init__(
        self,
        github_service: GitHubProjectsService,
        connection_manager: ConnectionManager,
        copilot_poller: CopilotPollingService,
    ):
        self._github = github_service
        self._ws = connection_manager
        self._poller = copilot_poller

    async def confirm(self, proposal: AITaskProposal, session: UserSession) -> AITaskProposal:
        """Main entry point — replaces the god function."""
        validated = await self.validate_proposal(proposal)
        workflow = await self.setup_github_workflow(validated, session)
        agent = await self.assign_agent(workflow)
        await self.start_polling(agent, workflow)
        await self.broadcast_result(validated, session)
        return validated

    async def validate_proposal(self, proposal: AITaskProposal) -> AITaskProposal: ...
    async def setup_github_workflow(self, proposal: AITaskProposal, session: UserSession) -> WorkflowContext: ...
    async def assign_agent(self, workflow: WorkflowContext) -> AgentAssignment: ...
    async def start_polling(self, agent: AgentAssignment, workflow: WorkflowContext) -> None: ...
    async def broadcast_result(self, proposal: AITaskProposal, session: UserSession) -> None: ...
```

**Injection**: Registered via `Depends()` in the endpoint, using existing DI patterns:

```python
async def get_proposal_orchestrator(request: Request) -> ProposalOrchestrator:
    return ProposalOrchestrator(
        github_service=get_github_service(request),
        connection_manager=get_connection_manager(request),
        copilot_poller=request.app.state.copilot_poller,
    )
```

### 1.3 — Backend `api/webhooks/` Package Design

The monolithic `api/webhooks.py` (1,033 lines, 11 functions) is split into:

| Module | Lines (est.) | Functions |
|--------|-------------|-----------|
| `helpers.py` | ~120 | `verify_webhook_signature()`, `extract_issue_number_from_pr()`, `_resolve_issue_for_pr()`, `classify_pull_request_activity()` |
| `pull_requests.py` | ~400 | `handle_pull_request_event()`, `update_issue_status_for_copilot_pr()`, `handle_copilot_pr_ready()`, `_get_auto_merge_pipeline()` |
| `check_runs.py` | ~200 | `handle_check_run_event()`, `handle_check_suite_event()` |
| `router.py` | ~250 | `github_webhook()` dispatcher endpoint (imports handlers) |
| `__init__.py` | ~5 | Re-exports `router` |

### 1.4 — `ChatStateManager` Class Design

```python
class ChatStateManager:
    """Manages in-memory chat state with lifecycle control."""

    def __init__(self, lock_capacity: int = 10_000):
        self._messages: dict[str, list[ChatMessage]] = {}
        self._proposals: dict[str, AITaskProposal] = {}
        self._locks: BoundedDict[str, asyncio.Lock] = BoundedDict(maxsize=lock_capacity)

    def get_lock(self, key: str) -> asyncio.Lock:
        """Get or create a lock for the given key (LRU-evicted at capacity)."""
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    # Message cache accessors
    def get_messages(self, session_id: str) -> list[ChatMessage]: ...
    def set_messages(self, session_id: str, messages: list[ChatMessage]) -> None: ...
    def append_message(self, session_id: str, message: ChatMessage) -> None: ...

    # Proposal cache accessors
    def get_proposal(self, proposal_id: str) -> AITaskProposal | None: ...
    def set_proposal(self, proposal_id: str, proposal: AITaskProposal) -> None: ...
    def remove_proposal(self, proposal_id: str) -> None: ...

    def clear(self) -> None:
        """Cleanup during app shutdown."""
        self._messages.clear()
        self._proposals.clear()
        self._locks.clear()
```

**Registration**: Instantiated in `lifespan()` and stored on `app.state.chat_state`:

```python
# In lifespan():
app.state.chat_state = ChatStateManager(lock_capacity=10_000)
yield
app.state.chat_state.clear()
```

### 1.5 — Frontend `services/api/` Directory Design

The monolithic `services/api.ts` (1,876 lines, 13 namespace objects) is split into:

| Module | Namespace Objects | Lines (est.) |
|--------|------------------|-------------|
| `client.ts` | `ApiError`, `onAuthExpired()`, base fetch helpers | ~140 |
| `auth.ts` | `authApi` | ~40 |
| `chat.ts` | `chatApi`, `conversationApi` | ~450 |
| `board.ts` | `boardApi` | ~60 |
| `projects.ts` | `projectsApi` | ~50 |
| `tasks.ts` | `tasksApi` | ~50 |
| `settings.ts` | `settingsApi` | ~80 |
| `workflow.ts` | `workflowApi` | ~60 |
| `agents.ts` | Agent types + API functions | ~400 |
| `signal.ts` | `signalApi` | ~40 |
| `metadata.ts` | `metadataApi`, `mcpApi`, `cleanupApi`, `choresApi` | ~200 |
| `index.ts` | Barrel re-export of all namespaces | ~20 |

**Backward compatibility**: `services/api/index.ts` re-exports everything that `services/api.ts` currently exports. Existing imports like `import { chatApi } from '../services/api'` resolve to `services/api/index.ts` and continue to work.

### 1.6 — Frontend `types/` Domain Split Design

The monolithic `types/index.ts` (1,525 lines, 40+ types) is split into:

| Module | Types | Lines (est.) |
|--------|-------|-------------|
| `common.ts` | `SenderType`, `ActionType`, `ProposalStatus`, `RecommendationStatus`, `User`, `AuthResponse`, `Project`, `ProjectListResponse` | ~120 |
| `chat.ts` | `ChatMessage`, `ChatMessageRequest`, `ChatMessagesResponse`, `AITaskProposal`, `IssueRecommendation`, `Conversation`, `ConversationsListResponse`, `MessageStatus` | ~250 |
| `board.ts` | `StatusColumn`, `BoardColumnConfig`, kanban-related types | ~100 |
| `tasks.ts` | `Task`, `TaskCreateRequest`, `TaskListResponse`, `TaskCreateActionData`, `StatusUpdateActionData` | ~150 |
| `pipeline.ts` | `PipelineLaunchActionData`, `Pipeline`, workflow/stage types | ~150 |
| `plans.ts` | `Plan`, `PlanStep`, `PlanStatus`, `ThinkingPhase`, `ThinkingEvent`, `StepApprovalStatus`, `DependencyGraphNode`, `DependencyGraphEdge`, plan-related request/response types | ~300 |
| `agents.ts` | Agent-related types, lifecycle status, MCP config types | ~200 |
| `settings.ts` | Settings-related types | ~100 |
| `index.ts` | Barrel re-export of all domain files | ~20 |

**Cross-domain references**: Types that reference entities from other domains use explicit imports:
```typescript
// types/chat.ts
import type { Project } from './common';
import type { Task } from './tasks';
```

---

## Phase Execution Details

### Phase 1: Split `api/chat.py` → `api/chat/` package

**Prerequisites**: None (first phase)
**Verification**: All 5,200+ backend tests pass; `from src.api.chat import router` still works

**Steps**:
1. Create `api/chat/` directory with `__init__.py`
2. Extract `ChatStateManager` into `api/chat/state.py` — replace the three module-level dicts
3. Extract conversation endpoints into `api/chat/conversations.py`
4. Extract message endpoints + helper functions into `api/chat/messages.py`
5. Extract proposal/upload endpoints into `api/chat/proposals.py`
6. Extract plan endpoints into `api/chat/plans.py`
7. Extract streaming endpoints into `api/chat/streaming.py`
8. Create `api/chat/router.py` combining all sub-routers
9. Update `__init__.py` to re-export `router` (preserves `from src.api.chat import router`)
10. Update imports in `main.py` and any other files importing from `api.chat`
11. Run full backend test suite

**Risk**: Import path changes may break test patches. Mitigation: Search for all `patch('src.api.chat.*')` in tests and update target paths.

### Phase 2: Extract `ProposalOrchestrator` service

**Prerequisites**: Phase 1 complete (proposals.py exists as thin wrapper)
**Verification**: All backend tests pass; `confirm_proposal` endpoint behavior unchanged

**Steps**:
1. Create `services/proposal_orchestrator.py` with `ProposalOrchestrator` class
2. Extract the logical steps from `confirm_proposal()` into service methods
3. Create `get_proposal_orchestrator()` dependency function
4. Update `api/chat/proposals.py` to inject and call the orchestrator
5. Run full backend test suite

**Risk**: The god function may have implicit dependencies on local state captured in closures. Mitigation: Careful extraction with explicit parameter passing; verify each step returns expected values.

### Phase 3: Split `api/webhooks.py` + consolidate global state

**Prerequisites**: Phase 1 complete (ChatStateManager exists)
**Verification**: All backend tests pass; webhook handling behavior unchanged

**Steps**:
1. Create `api/webhooks/` directory with `__init__.py`
2. Extract helper functions into `api/webhooks/helpers.py`
3. Extract PR handlers into `api/webhooks/pull_requests.py`
4. Extract check run/suite handlers into `api/webhooks/check_runs.py`
5. Move webhook dispatcher into `api/webhooks/router.py`
6. Register `ChatStateManager` on `app.state` in `lifespan()`
7. Update all references from module-level dicts to `ChatStateManager` via `Depends()`
8. Run full backend test suite

### Phase 4: Split `services/api.ts` → `services/api/` directory

**Prerequisites**: None (independent of backend phases)
**Verification**: All 2,200+ frontend tests pass; `npm run build` succeeds

**Steps**:
1. Create `services/api/` directory
2. Extract `ApiError`, `onAuthExpired`, base fetch utilities into `services/api/client.ts`
3. Extract each namespace object into its domain file (auth.ts, chat.ts, board.ts, etc.)
4. Create `services/api/index.ts` barrel that re-exports all namespaces
5. Delete old `services/api.ts`
6. Verify all imports resolve (TypeScript compiler check)
7. Run full frontend test suite

**Risk**: Some test files may mock `services/api` at the module level. Mitigation: The barrel re-export preserves the import shape, so mocks should continue to work.

### Phase 5: Domain-scoped types

**Prerequisites**: Phase 4 complete (API modules may import types)
**Verification**: All frontend tests pass; `npm run build` succeeds; `tsc --noEmit` passes

**Steps**:
1. Analyze dependency graph of types in `types/index.ts`
2. Create domain files: `common.ts`, `chat.ts`, `board.ts`, `tasks.ts`, `pipeline.ts`, `plans.ts`, `agents.ts`, `settings.ts`
3. Move types to appropriate domain files with cross-domain imports
4. Update `types/index.ts` to be a barrel re-export
5. Verify all imports resolve
6. Run full frontend test suite

**Risk**: Circular imports between domain type files. Mitigation: Extract shared base types to `common.ts` first; enforce unidirectional dependencies.

### Phase 6: Verification

**Prerequisites**: All previous phases complete
**Verification**: Complete CI pipeline passes

**Steps**:
1. Run full backend test suite: `cd solune/backend && python -m pytest tests/unit/ -q --timeout=120`
2. Run backend type check: `cd solune/backend && pyright`
3. Run backend lint: `cd solune/backend && ruff check src/`
4. Run full frontend test suite: `cd solune/frontend && npm test`
5. Run frontend type check: `cd solune/frontend && tsc --noEmit`
6. Run frontend lint: `cd solune/frontend && npm run lint`
7. Run frontend build: `cd solune/frontend && npm run build`
8. Audit imports: verify no imports reference deleted monolithic files
9. Verify line counts: each new module should be <500 lines
