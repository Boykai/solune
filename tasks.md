---
description: "Task list for eliminating the dual-init singleton pattern"
---

# Tasks: Eliminate the "Dual-Init" Singleton Pattern

**Input**: Design documents from `/specs/002-dual-init-singleton/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Test infrastructure changes ARE the core deliverable (FR-004 through FR-009; constitution check IV). The resettable registry, autouse fixture, and `dependency_overrides` migration are test-time utilities. No separate TDD-style test suite is added — the existing backend test suite (`uv run pytest`) is the acceptance gate for every phase.

**Organization**: Tasks are grouped by user story. The four user stories map to the four priorities (P1–P4) described in `spec.md`. Stories 1 and 2 are independent; Story 3 depends on both; Story 4 depends on Story 2. Each story is a shippable increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

## Path Conventions

Web app structure (per plan.md). All edits live under `solune/backend/src/`, `solune/backend/tests/`, or `specs/002-dual-init-singleton/`. Paths are repo-relative from the workspace root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the one new module that multiple user stories depend on.

- [ ] T001 Create [solune/backend/src/services/resettable_state.py](solune/backend/src/services/resettable_state.py) with `register_resettable(name, reset_fn)` and `reset_all()` per `contracts/resettable-state-contract.md` § S1. The module exposes exactly two public functions: `register_resettable` appends `(name, reset_fn)` to a module-level `_registry` list; `reset_all` iterates the list, calling each `reset_fn()` inside a `try/except` that logs exceptions but does not raise (FR-006). ~30 lines total.

**Checkpoint**: Registry module exists and is importable. No production code references it yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Register all service singletons on `app.state` and provide `Depends()`-compatible accessor functions — the two primitives that every user story builds upon.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 Update lifespan in [solune/backend/src/main.py](solune/backend/src/main.py) — register `ChatAgentService`, `PipelineRunService`, and `GitHubAuthService` on `app.state` during startup per `contracts/lifespan-registration-contract.md` § L1. Wrap each constructor in a `try/except` that logs `CRITICAL` and re-raises (FR-010, § L2). Follow the ordering constraint: database first, then stateless services, then services depending on `db` (§ L5). Remove the `set_dispatcher(_alert_dispatcher)` dual-registration call (§ L3).
- [ ] T003 [P] Update [solune/backend/src/dependencies.py](solune/backend/src/dependencies.py) — add four new accessor functions (`get_chat_agent_service`, `get_pipeline_run_service`, `get_github_auth_service`, `get_alert_dispatcher`) per `contracts/accessor-contract.md` § A1, § A4. Each is a single `return request.app.state.X` with lazy `TYPE_CHECKING` imports (§ A3, FR-011). Remove fallback-to-global logic from the three existing accessors (`get_github_service`, `get_connection_manager`, `get_database`) per § A2 — each body becomes a single `return` statement with no `getattr` fallback.

**Checkpoint**: Foundation ready — `app.state` is the single source of truth for all nine attributes (§ L4). All seven accessor functions read exclusively from `app.state`. User story implementation can now begin.

---

## Phase 3: User Story 1 — Single Source of Truth for All Service Singletons (Priority: P1) 🎯 MVP

**Goal**: Every endpoint that previously imported a service singleton directly now receives it via `Depends(get_X)`. No production code path reads from a module-level global.

**Independent Test**: Run `uv run pytest --timeout=120 -x -q` from `solune/backend/`. All existing tests pass. Run `grep -rn 'getattr.*app.state' src/dependencies.py` — zero matches. Run the canary from `quickstart.md` § Story 1.

### Migrate API route handlers to Depends() (all [P] — different files)

- [ ] T004 [P] [US1] Update [solune/backend/src/api/board.py](solune/backend/src/api/board.py) — remove top-level `from src.services.github_projects import github_projects_service`; add `github_service: GitHubProjectsService = Depends(get_github_service)` parameter to every route handler that uses it; replace all `github_projects_service.method()` calls with `github_service.method()`.
- [ ] T005 [P] [US1] Update [solune/backend/src/api/projects.py](solune/backend/src/api/projects.py) — replace top-level imports of `github_projects_service`, `connection_manager`, and `github_auth_service` with `Depends(get_github_service)`, `Depends(get_connection_manager)`, and `Depends(get_github_auth_service)` parameters in each route handler that uses them.
- [ ] T006 [P] [US1] Update [solune/backend/src/api/tasks.py](solune/backend/src/api/tasks.py) — replace top-level imports of `github_projects_service` and `connection_manager` with `Depends(get_github_service)` and `Depends(get_connection_manager)` parameters in each route handler.
- [ ] T007 [P] [US1] Update [solune/backend/src/api/workflow.py](solune/backend/src/api/workflow.py) — replace top-level imports of `github_projects_service` and `connection_manager` with `Depends(get_github_service)` and `Depends(get_connection_manager)` parameters in each route handler.
- [ ] T008 [P] [US1] Update [solune/backend/src/api/chores.py](solune/backend/src/api/chores.py) — replace top-level `github_projects_service` import with `Depends(get_github_service)` parameter in each route handler.
- [ ] T009 [P] [US1] Update [solune/backend/src/api/pipelines.py](solune/backend/src/api/pipelines.py) — remove `_run_service_instance` global and `_get_run_service()` lazy-init function; replace all `_get_run_service()` calls (7 sites) with `Depends(get_pipeline_run_service)` parameter; replace `github_projects_service` import with `Depends(get_github_service)`.
- [ ] T010 [P] [US1] Update [solune/backend/src/api/webhooks.py](solune/backend/src/api/webhooks.py) — replace top-level `github_projects_service` import with `Depends(get_github_service)` parameter in each route handler.
- [ ] T011 [P] [US1] Update [solune/backend/src/api/chat.py](solune/backend/src/api/chat.py) — replace all `get_chat_agent_service()` calls (5 sites at lines 1180, 1542, 2135, 2212, 2519 per research.md R2) with `Depends(get_chat_agent_service)` parameter; replace local `github_projects_service` imports (lines 429, 540) with `Depends(get_github_service)`.
- [ ] T012 [P] [US1] Update [solune/backend/src/api/auth.py](solune/backend/src/api/auth.py) — replace top-level `github_auth_service` import with `Depends(get_github_auth_service)` parameter in each route handler.
- [ ] T013 [P] [US1] Update [solune/backend/src/api/metadata.py](solune/backend/src/api/metadata.py), [solune/backend/src/api/agents.py](solune/backend/src/api/agents.py), and [solune/backend/src/api/tools.py](solune/backend/src/api/tools.py) — replace local `github_projects_service` imports inside functions with `Depends(get_github_service)` parameter on the enclosing route handler.
- [ ] T014 [P] [US1] Update [solune/backend/src/api/apps.py](solune/backend/src/api/apps.py) — replace local `connection_manager` import (line 555 per research.md R2) with `Depends(get_connection_manager)` parameter on the enclosing route handler.

### Migrate non-route-handler code (background tasks)

- [ ] T015 [US1] Update [solune/backend/src/services/copilot_polling/recovery.py](solune/backend/src/services/copilot_polling/recovery.py) and [solune/backend/src/services/copilot_polling/polling_loop.py](solune/backend/src/services/copilot_polling/polling_loop.py) — replace `get_dispatcher()` calls (2 sites in recovery.py, 1 in polling_loop.py per research.md R3) with `app.state.alert_dispatcher` access via the `app` reference already threaded through the polling infrastructure. Remove `from src.services.alert_dispatcher import get_dispatcher` imports.

### Clean up module-level globals (now unused by production code)

- [ ] T016 [P] [US1] Nullify `github_projects_service` global in [solune/backend/src/services/github_projects/service.py](solune/backend/src/services/github_projects/service.py) — set to `None` (or remove entirely). Verify no production import site reads from this variable.
- [ ] T017 [P] [US1] Nullify `connection_manager` global in [solune/backend/src/services/websocket.py](solune/backend/src/services/websocket.py) — set to `None`. Verify no production import site reads from this variable.
- [ ] T018 [P] [US1] Nullify `github_auth_service` global in [solune/backend/src/services/github_auth.py](solune/backend/src/services/github_auth.py) — set to `None`. Verify no production import reads from this variable.
- [ ] T019 [P] [US1] Remove `get_chat_agent_service()` lazy-init function and nullify `_chat_agent_service` in [solune/backend/src/services/chat_agent.py](solune/backend/src/services/chat_agent.py). If any direct callers remain after T011, replace them with a `RuntimeError("Use Depends(get_chat_agent_service) instead")` stub per data-model.md § E2.
- [ ] T020 [P] [US1] Remove `set_dispatcher()` and `get_dispatcher()` functions from [solune/backend/src/services/alert_dispatcher.py](solune/backend/src/services/alert_dispatcher.py); nullify `_dispatcher` sentinel per data-model.md § E2. Verify `grep -rn 'set_dispatcher\|get_dispatcher' solune/backend/src/` returns zero matches (excluding comments).

### Verification

- [ ] T021 [US1] Run `uv run pytest --timeout=120 -x -q` from `solune/backend/`; MUST exit 0 (FR-012, SC-005). Run the canary from `quickstart.md` § Story 1 (start the app, verify all singletons on `app.state`). Run the grep checks: zero `getattr.*app.state` in `dependencies.py`, zero direct singleton imports in `src/api/`.

**Checkpoint**: Story 1 complete. `app.state` is the single source of truth. All 11 API modules use `Depends()`. All 6 service module globals are `None` or removed. Existing test suite passes unchanged.

---

## Phase 4: User Story 2 — Resettable State Registry for Test Isolation (Priority: P2)

**Goal**: Every piece of mutable state that was previously cleared manually in `_clear_test_caches()` is now registered with the resettable state registry and automatically reset by the autouse fixture.

**Independent Test**: Run the canary from `quickstart.md` § Story 2 — mutate devops tracking in one test, assert it is empty in the next test, with no manual cleanup.

### Register mutable state entries (all [P] — different modules)

- [ ] T022 [P] [US2] Register general caches with resettable_state in [solune/backend/src/services/](solune/backend/src/services/) modules that define the LRU `cache` and `settings_cache` (via `clear_settings_cache()`) — add `register_resettable()` calls per `contracts/resettable-state-contract.md` § S2 Pattern A.
- [ ] T023 [P] [US2] Register [solune/backend/src/api/chat.py](solune/backend/src/api/chat.py) mutable state: `_messages`, `_proposals`, `_recommendations`, `_locks` — add `register_resettable()` calls with `.clear()` reset per § S2 Pattern A.
- [ ] T024 [P] [US2] Register [solune/backend/src/services/pipeline_state_store.py](solune/backend/src/services/pipeline_state_store.py) mutable state: `_pipeline_states`, `_issue_main_branches`, `_issue_sub_issue_map`, `_agent_trigger_inflight`, `_project_launch_locks`, `_store_lock`, `_db` — add `register_resettable()` calls per § S2 Patterns A and B.
- [ ] T025 [P] [US2] Register [solune/backend/src/services/workflow_orchestrator/](solune/backend/src/services/workflow_orchestrator/) mutable state: `_transitions`, `_workflow_configs`, `_tracking_table_cache`, `_orchestrator_instance` — add `register_resettable()` calls per § S2 Patterns A and B.
- [ ] T026 [P] [US2] Register [solune/backend/src/services/copilot_polling/state.py](solune/backend/src/services/copilot_polling/state.py) collections: 17 collections, scalars, and locks (lines 312–349 of `conftest.py`) — add `register_resettable()` calls per § S2 Patterns A, B, and C (locks replaced with fresh `asyncio.Lock()` instances).
- [ ] T027 [P] [US2] Register mutable state in [solune/backend/src/services/websocket.py](solune/backend/src/services/websocket.py) (`_ws_lock`), [solune/backend/src/services/settings_store.py](solune/backend/src/services/settings_store.py) (`_queue_mode_cache`, `_auto_merge_cache`), [solune/backend/src/services/signal_chat.py](solune/backend/src/services/signal_chat.py) (`_signal_pending`), and [solune/backend/src/services/github_auth.py](solune/backend/src/services/github_auth.py) (`_oauth_states`) — add `register_resettable()` calls per § S2 Patterns A and C.
- [ ] T028 [P] [US2] Register mutable state in [solune/backend/src/services/agent_creator.py](solune/backend/src/services/agent_creator.py) (`_agent_sessions`), [solune/backend/src/services/agents/service.py](solune/backend/src/services/agents/service.py) (`_chat_sessions`, `_chat_session_timestamps`), and [solune/backend/src/services/chores/chat.py](solune/backend/src/services/chores/chat.py) (`_conversations`) — add `register_resettable()` calls per § S2 Pattern A.
- [ ] T029 [P] [US2] Register mutable state in [solune/backend/src/services/template_files.py](solune/backend/src/services/template_files.py) (`_cached_files`, `_cached_warnings`), [solune/backend/src/services/app_templates/registry.py](solune/backend/src/services/app_templates/registry.py) (`_cache`), [solune/backend/src/services/done_items_store.py](solune/backend/src/services/done_items_store.py) (`_db`), and [solune/backend/src/services/session_store.py](solune/backend/src/services/session_store.py) (`_encryption_service`) — add `register_resettable()` calls per § S2 Pattern B.

### Update autouse fixture

- [ ] T030 [US2] Replace the body of the `_clear_test_caches()` fixture in [solune/backend/tests/conftest.py](solune/backend/tests/conftest.py) with `reset_all()` calls per `contracts/resettable-state-contract.md` § S4: import `reset_all` from `src.services.resettable_state`, call `reset_all()` before `yield`, call `reset_all()` after `yield`. Remove all manual `.clear()` / `= None` / `= asyncio.Lock()` lines that are now covered by the registry.

### Verification

- [ ] T031 [US2] Run `uv run pytest --timeout=120 -x -q` from `solune/backend/`; MUST exit 0 (SC-005). Verify registry completeness: `python -c "from src.main import create_app; from src.services.resettable_state import _registry; print(len(_registry))"` — count MUST be ≥ 30 (data-model.md § E4). Run the canary from `quickstart.md` § Story 2. Verify `_clear_test_caches()` fixture body contains only `reset_all()` calls and `yield` (SC-003).

**Checkpoint**: Story 2 complete. The resettable registry covers all previously ad-hoc-cleared state. The autouse fixture is reduced to three lines. Any new mutable state registered with `@resettable_state` is automatically cleaned up.

---

## Phase 5: User Story 3 — Tests Mock at the FastAPI Boundary Only (Priority: P3)

**Goal**: Every test that previously used multiple `patch()` calls to mock a service singleton now uses a single `app.dependency_overrides` entry. The total number of distinct `patch()` target paths for service singletons is reduced to zero (SC-002).

**Independent Test**: Pick an endpoint test that today requires ≥3 `patch()` calls for `GitHubProjectsService`. Rewrite it to use only `app.dependency_overrides[get_github_service]`. Confirm it passes identically. Run the canary from `quickstart.md` § Story 3.

### Update conftest.py client fixture

- [ ] T032 [US3] Update the `client` fixture in [solune/backend/tests/conftest.py](solune/backend/tests/conftest.py) — remove all `patch()` calls that target service singleton import paths (e.g., `src.api.board.github_projects_service`, `src.api.projects.github_projects_service`). Replace with `app.dependency_overrides[get_X] = lambda: mock_X` entries for each service per data-model.md § E6. The `app` instance is created fresh per test, so overrides do not bleed (§ S5).

### Update individual test files (all [P] — different test files)

- [ ] T033 [P] [US3] Update test files that patch `GitHubProjectsService` at multiple module paths — replace multi-path `patch()` calls with single `app.dependency_overrides[get_github_service]` entries. Audit `grep -rn 'patch.*github_projects_service' solune/backend/tests/` to find all sites. Includes at minimum: [solune/backend/tests/test_label_validation.py](solune/backend/tests/test_label_validation.py) (the `mock_cp.github_projects_service = AsyncMock()` pattern from the issue description).
- [ ] T034 [P] [US3] Update test files that patch `ConnectionManager` or `ChatAgentService` at multiple module paths — replace with `app.dependency_overrides[get_connection_manager]` and `app.dependency_overrides[get_chat_agent_service]` entries. Audit `grep -rn 'patch.*connection_manager\|patch.*get_chat_agent_service\|patch.*_chat_agent_service' solune/backend/tests/` to find all sites.
- [ ] T035 [P] [US3] Update test files that patch `GitHubAuthService`, `PipelineRunService`, or `AlertDispatcher` at multiple module paths — replace with `app.dependency_overrides` entries for `get_github_auth_service`, `get_pipeline_run_service`, `get_alert_dispatcher`. Audit `grep -rn 'patch.*github_auth_service\|patch.*_run_service_instance\|patch.*get_dispatcher\|patch.*alert_dispatcher' solune/backend/tests/` to find all sites.

### Verify override cleanup

- [ ] T036 [US3] Verify that `app.dependency_overrides` is automatically scoped per test in [solune/backend/tests/conftest.py](solune/backend/tests/conftest.py) — confirm the `client` fixture creates a fresh `app` via `create_app()` so overrides do not bleed between tests (FR-008, § S5). If the fixture reuses a shared `app` instance, add `app.dependency_overrides.clear()` to the teardown.

### Verification

- [ ] T037 [US3] Run `uv run pytest --timeout=120 -x -q` from `solune/backend/`; MUST exit 0 (SC-005). Verify zero remaining singleton patches: `grep -rn "patch.*github_projects_service\|patch.*connection_manager\|patch.*github_auth_service\|patch.*get_chat_agent_service\|patch.*_run_service_instance" solune/backend/tests/` — MUST return zero matches (SC-002). Run the canary from `quickstart.md` § Story 3.

**Checkpoint**: Story 3 complete. Tests mock at the FastAPI boundary only. A new contributor can mock any service by writing a single `app.dependency_overrides` line (SC-004).

---

## Phase 6: User Story 4 — Module-Level Caches and Mutable Dicts Centralised (Priority: P4)

**Goal**: The template-file cache, devops tracking dict, and all remaining ad-hoc-cleared mutable state are confirmed to be registered with the resettable registry and automatically reset. Manual cleanup code in individual test files is removed.

**Independent Test**: Run the canary from `quickstart.md` § Story 4 — populate the template-file cache in one test, assert it is `None` in the next.

### Remove remaining manual cleanup

- [ ] T038 [P] [US4] Remove manual `_devops_tracking.clear()` calls from [solune/backend/tests/conftest.py](solune/backend/tests/conftest.py) (if any remain after T030) and [solune/backend/tests/](solune/backend/tests/) test files (e.g., `test_auto_merge.py` per issue description). The registry-based reset from T026 now handles this automatically.
- [ ] T039 [P] [US4] Remove any remaining ad-hoc `mock_cp.github_projects_service = AsyncMock()` patterns or manual singleton assignment in [solune/backend/tests/](solune/backend/tests/) test files. These are now covered by `dependency_overrides` (T032–T035).

### Verification

- [ ] T040 [US4] Run `uv run pytest --timeout=120 -x -q` from `solune/backend/`; MUST exit 0 (SC-005). Run the canary from `quickstart.md` § Story 4 (template cache auto-resets between tests). Verify `set_dispatcher` / `get_dispatcher` are fully removed: `grep -rn 'def set_dispatcher\|def get_dispatcher' solune/backend/src/` returns zero matches. Verify no manual `_devops_tracking.clear()` remains: `grep -rn '_devops_tracking.clear()' solune/backend/tests/` returns zero matches.

**Checkpoint**: Story 4 complete. All module-level caches and mutable dicts are centrally managed. No ad-hoc cleanup code remains.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all stories and documentation.

- [ ] T041 [P] Run all four `quickstart.md` verification recipes (Stories 1–4) end-to-end from `solune/backend/`. Confirm every grep check, canary script, and `uv run pytest` invocation passes.
- [ ] T042 [P] Run `uv run pyright src` from `solune/backend/` to verify no type errors are introduced by the refactoring. Address any new diagnostics.
- [ ] T043 Run the full test suite `uv run pytest --timeout=120 -q` (no `-x`) from `solune/backend/` to verify zero test-isolation failures (SC-005) and full backward compatibility (FR-012).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** — T001 — no dependencies; can start immediately.
- **Foundational (Phase 2)** — T002, T003 — depends on T001 only for the resettable_state module to exist (T003 does not import it, but Phase 2 logically follows Phase 1). T002 and T003 are parallelizable (different files).
- **User Story 1 (Phase 3)** — depends on Foundational (Phase 2) completion (accessors and lifespan registrations must exist before API modules can use `Depends()`).
- **User Story 2 (Phase 4)** — depends on Setup (Phase 1) for the registry module. Independent of User Story 1 — can run in parallel with US1 if staffed.
- **User Story 3 (Phase 5)** — depends on BOTH User Story 1 (all singletons accessed via `Depends()`) and User Story 2 (autouse fixture handles cleanup). Must wait for both.
- **User Story 4 (Phase 6)** — depends on User Story 2 (registry registrations) and User Story 3 (dependency_overrides migration). Can start after both.
- **Polish (Phase 7)** — depends on all user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational (Phase 2). Independent of US2/US3/US4.
- **User Story 2 (P2)**: Depends on Setup (Phase 1). Independent of US1.
- **User Story 3 (P3)**: Depends on US1 + US2 — both must be complete.
- **User Story 4 (P4)**: Depends on US2 + US3 — cleanup of manual patterns.

### Within Each User Story

- **US1**: API migration (T004–T014, parallelizable across files) → background task migration (T015) → module-level global cleanup (T016–T020, parallelizable) → verification (T021).
- **US2**: Registration across modules (T022–T029, parallelizable) → conftest.py update (T030) → verification (T031).
- **US3**: conftest.py client fixture update (T032) → test file updates (T033–T035, parallelizable) → override cleanup verification (T036) → full verification (T037).
- **US4**: Remove manual cleanup (T038–T039, parallelizable) → verification (T040).

### Parallel Opportunities

- T002 and T003 are different files (`main.py` vs `dependencies.py`) → run in parallel.
- T004–T014 are different API modules → all run in parallel within US1.
- T016–T020 are different service modules → all run in parallel within US1.
- T022–T029 are different service modules → all run in parallel within US2.
- T033–T035 are different test file groups → all run in parallel within US3.
- T038 and T039 are different test file groups → run in parallel within US4.
- T041 and T042 are independent checks → run in parallel in Polish.

### Across-story parallelism

US1 and US2 are independent of each other and CAN be worked on in parallel. US3 must wait for both US1 and US2. US4 must wait for US2 and US3.

---

## Parallel Example: User Story 1

```text
# Phase 2 (Foundational) — parallelise across files:
Task T002: Update lifespan in main.py (registers singletons)
Task T003: Update dependencies.py (add/fix accessors)

# Phase 3 Step 1 — parallelise ALL API module migrations:
Task T004: api/board.py
Task T005: api/projects.py
Task T006: api/tasks.py
Task T007: api/workflow.py
Task T008: api/chores.py
Task T009: api/pipelines.py
Task T010: api/webhooks.py
Task T011: api/chat.py
Task T012: api/auth.py
Task T013: api/metadata.py + api/agents.py + api/tools.py
Task T014: api/apps.py

# Phase 3 Step 3 — parallelise ALL global cleanups:
Task T016: services/github_projects/service.py
Task T017: services/websocket.py
Task T018: services/github_auth.py
Task T019: services/chat_agent.py
Task T020: services/alert_dispatcher.py
```

## Parallel Example: User Story 2

```text
# Register mutable state — parallelise ALL module registrations:
Task T022: General caches
Task T023: api/chat.py state
Task T024: pipeline_state_store.py state
Task T025: workflow_orchestrator/ state
Task T026: copilot_polling/state.py collections
Task T027: websocket.py + settings_store.py + signal_chat.py + github_auth.py
Task T028: agent_creator.py + agents/service.py + chores/chat.py
Task T029: template_files.py + app_templates/ + done_items_store.py + session_store.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T003)
3. Complete Phase 3: User Story 1 (T004–T021)
4. **STOP and VALIDATE**: All existing tests pass; canary confirms all singletons on `app.state`
5. Deploy/demo if ready — the app is functionally identical, but internal wiring is clean

**MVP scope**: T001–T021 (21 tasks). After merge, `app.state` is the single source of truth for every service singleton. Tests still use `patch()` (cleaned up in US3), but the production code is fully migrated.

### Incremental Delivery

1. **Setup + Foundational (T001–T003)** → registry module and app.state registrations ready
2. **User Story 1 (T004–T021)** → production code migrated → test independently → MVP! (SC-001)
3. **User Story 2 (T022–T031)** → test cleanup automated → test independently (SC-003, SC-006)
4. **User Story 3 (T032–T037)** → tests mock at FastAPI boundary → test independently (SC-002, SC-004)
5. **User Story 4 (T038–T040)** → remaining manual cleanup removed → test independently
6. **Polish (T041–T043)** → end-to-end validation across all stories

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With two or more developers:

1. **Developer A**: Setup (T001) → Foundational (T002) → User Story 1 (T004–T021)
2. **Developer B**: Setup (T001) → Foundational (T003) → User Story 2 (T022–T031)
3. Once US1 + US2 merge → Developer A: User Story 3 (T032–T037)
4. After US3 → Developer B: User Story 4 (T038–T040)
5. Any developer: Polish (T041–T043)

### Reviewer guidance per PR

- **US1 reviewer**: Confirm every accessor in `dependencies.py` is a single `return request.app.state.X` with no fallback. Verify all API modules use `Depends()` — no direct singleton imports remain. Run `uv run pytest`.
- **US2 reviewer**: Confirm `_clear_test_caches()` is reduced to `reset_all()` + `yield` + `reset_all()`. Verify the registry count is ≥ 30 entries. Run `uv run pytest`.
- **US3 reviewer**: Run `grep -rn "patch.*github_projects_service" tests/` — must return zero matches. Confirm `dependency_overrides` entries cover all seven services. Run `uv run pytest`.
- **US4 reviewer**: Confirm no manual `_devops_tracking.clear()` or `set_dispatcher()` calls remain anywhere in `tests/` or `src/`. Run `uv run pytest`.

---

## Format validation

Every task above conforms to: `- [ ] T### [P?] [Story?] Description with file path`.

- ✅ All tasks have a checkbox `- [ ]`.
- ✅ All tasks have a sequential ID (T001–T043, no gaps).
- ✅ All US-phase tasks carry a `[US1]`–`[US4]` story label; Setup (T001), Foundational (T002–T003), and Polish (T041–T043) tasks intentionally have no story label.
- ✅ Parallelisable tasks carry `[P]`.
- ✅ Every task names at least one file path or directory it edits/creates/runs against.

---

## Coverage matrix

| Spec artifact | Tasks |
|---|---|
| FR-001 | T002 (register all singletons on `app.state`) |
| FR-002 | T003 (Depends()-compatible accessors, no fallback) |
| FR-003 | T016–T020 (module-level globals → None) |
| FR-004 | T001 (resettable state registry mechanism) |
| FR-005 | T030 (autouse fixture enumerates registry) |
| FR-006 | T001 (reset_all logs exceptions, continues) |
| FR-007 | T032–T035 (replace multi-path patch with dependency_overrides) |
| FR-008 | T036 (dependency_overrides cleared per test) |
| FR-009 | T022–T029 (register template cache, devops tracking, etc.) |
| FR-010 | T002 (fail-fast try/except during lifespan startup) |
| FR-011 | T003 (lazy imports in accessor bodies) |
| FR-012 | T021, T031, T037, T040, T043 (full test suite passes after each story) |
| SC-001 | T021 (single source of truth verified) |
| SC-002 | T037 (zero singleton patch paths) |
| SC-003 | T031 (80%+ reduction in manual cleanup) |
| SC-004 | T037 (single dependency_overrides line for mocking) |
| SC-005 | T021, T031, T037, T040, T043 (zero test-isolation failures) |
| SC-006 | T001, T030 (single registration point for new state) |
| SC-007 | T002 (sequential service init, no overhead) |
| US1 Independent Test | T021 |
| US2 Independent Test | T031 |
| US3 Independent Test | T037 |
| US4 Independent Test | T040 |

---

## Summary

- **Total tasks**: 43
- **US1 (Single Source of Truth)**: 18 tasks (T004–T021)
- **US2 (Resettable State Registry)**: 10 tasks (T022–T031)
- **US3 (Tests Mock at FastAPI Boundary)**: 6 tasks (T032–T037)
- **US4 (Module-Level Caches Centralised)**: 3 tasks (T038–T040)
- **Setup + Foundational**: 3 tasks (T001–T003)
- **Polish**: 3 tasks (T041–T043)
- **Parallel opportunities**: 35 of 43 tasks are marked [P] or are in parallelisable groups
- **MVP scope**: T001–T021 (21 tasks — Setup + Foundational + User Story 1)
- **Suggested delivery order**: US1 → US2 → US3 → US4 (or US1 ∥ US2 → US3 → US4)
