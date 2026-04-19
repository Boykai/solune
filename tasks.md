# Tasks: Refactor main.py Lifespan into src/startup/ Step Package

**Input**: Design documents from `/specs/002-lifespan-startup-steps/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Explicitly requested — FR-018 mandates independently unit-testable steps, SC-001 requires sub-2s tests, SC-005 requires structured-log assertions.

**Organisation**: Tasks map to the four-PR delivery strategy from plan.md. User stories are assigned per phase based on primary value delivered.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app (backend only)**: `solune/backend/src/` for source, `solune/backend/tests/` for tests
- All paths relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the directory scaffolding for the new startup package and test package

- [x] T001 Create startup package directories with `__init__.py` at `solune/backend/src/startup/__init__.py` and `solune/backend/src/startup/steps/__init__.py`
- [x] T002 [P] Create test package directory with `__init__.py` at `solune/backend/tests/unit/startup/__init__.py`

---

## Phase 2: Foundational — PR1: Scaffold + Runner (Blocking Prerequisites)

**Purpose**: Build the Step Protocol, StartupContext, runner functions, and runner tests. This phase enables all subsequent user story work.

**⚠️ CRITICAL**: No step migration (Phases 3–5) can begin until this phase is complete.

**Delivers**: `src/startup/protocol.py`, `src/startup/runner.py`, `src/startup/__init__.py`, `src/startup/steps/__init__.py`, `tests/unit/startup/conftest.py`, `tests/unit/startup/test_protocol.py`, `tests/unit/startup/test_runner.py`

- [x] T003 Implement Step Protocol (`@runtime_checkable`), StepOutcome frozen dataclass (`name`, `status`, `duration_ms`, `error`), and StartupContext mutable dataclass (`app`, `settings`, `task_registry`, `db`, `background`, `shutdown_hooks`) per contracts in `solune/backend/src/startup/protocol.py`
- [x] T004 Implement StartupError exception class and `run_startup(steps, ctx) -> list[StepOutcome]` with duplicate-name validation, per-step `request_id_var` wrapping, `skip_if` evaluation, timing via `time.perf_counter()`, structured logging, and fatal/non-fatal error handling per runner-contract.md § R1 in `solune/backend/src/startup/runner.py`
- [x] T005 Implement `run_shutdown(ctx, *, shutdown_timeout=30.0) -> list[StepOutcome]` with LIFO hook iteration, `asyncio.wait_for` timeout, built-in trailing hooks (drain task_registry, stop polling, close database), and never-raise guarantee per runner-contract.md § R2 in `solune/backend/src/startup/runner.py`
- [x] T006 [P] Populate public re-exports (`run_startup`, `run_shutdown`, `StartupContext`, `Step`, `StepOutcome`, `StartupError`) in `solune/backend/src/startup/__init__.py`
- [x] T007 [P] Declare empty `STARTUP_STEPS: list[Step] = []` placeholder in `solune/backend/src/startup/steps/__init__.py`
- [x] T008 [P] Create shared test fixtures (`make_test_ctx` factory, `FakeStep` helper class with configurable `name`/`fatal`/`run`/`skip_if`) in `solune/backend/tests/unit/startup/conftest.py`
- [x] T009 [P] Create Protocol conformance tests — verify a FakeStep `isinstance` check, verify missing-member rejection, verify `skip_if` is optional — in `solune/backend/tests/unit/startup/test_protocol.py`
- [x] T010 Create startup runner tests covering scenarios 1–9 from runner-contract.md § R4 (all-succeed, non-fatal-fail, fatal-fail, skip, skip_if-raises, duplicate-names, empty-list, structured-log-output, request_id_var-per-step) in `solune/backend/tests/unit/startup/test_runner.py`

**Checkpoint**: Runner is functional with fake steps — `uv run pytest tests/unit/startup/ -v` passes. No behaviour change in `main.py` yet.

---

## Phase 3: User Story 1 — Developer Tests a Single Startup Step in Isolation (Priority: P1) 🎯 MVP

**Goal**: Migrate steps 1–9 (logging through Sentry) into individual step modules so each can be unit-tested with mocked dependencies in under 2 seconds — no full app boot required.

**Independent Test**: Run `uv run pytest tests/unit/startup/test_s01_logging.py -v` (or any single step test) — passes in <2s with no server boot.

**PR Alignment**: PR 2 — Move Pure Init Steps

### Implementation for User Story 1

- [x] T011 [P] [US1] Create LoggingStep class (`name="logging"`, `fatal=True`) wrapping `setup_logging()` call in `solune/backend/src/startup/steps/s01_logging.py`
- [x] T012 [P] [US1] Create AsyncioExcHandlerStep class (`name="asyncio_exception_handler"`, `fatal=False`) wrapping asyncio exception handler setup in `solune/backend/src/startup/steps/s02_asyncio_exc.py`
- [x] T013 [P] [US1] Create DatabaseStep class (`name="database"`, `fatal=True`) wrapping `init_database()` and setting `ctx.db` and `ctx.app.state.db` in `solune/backend/src/startup/steps/s03_database.py`
- [x] T014 [P] [US1] Create PipelineCacheStep class (`name="pipeline_state_cache"`, `fatal=True`) wrapping `init_pipeline_state_store(db)` in `solune/backend/src/startup/steps/s04_pipeline_cache.py`
- [x] T015 [P] [US1] Create DoneItemsCacheStep class (`name="done_items_cache"`, `fatal=True`) wrapping `init_done_items_store(db)` in `solune/backend/src/startup/steps/s05_done_items_cache.py`
- [x] T016 [P] [US1] Create SingletonServicesStep class (`name="singleton_services"`, `fatal=True`) wrapping service singleton initialisation (`github_projects_service`, `connection_manager`) in `solune/backend/src/startup/steps/s06_singleton_svcs.py`
- [x] T017 [P] [US1] Create AlertDispatcherStep class (`name="alert_dispatcher"`, `fatal=False`) wrapping AlertDispatcher init in `solune/backend/src/startup/steps/s07_alert_dispatcher.py`
- [x] T018 [P] [US1] Create OtelStep class (`name="otel"`, `fatal=False`, `skip_if` returns `not ctx.settings.otel_enabled`) wrapping OpenTelemetry init in `solune/backend/src/startup/steps/s08_otel.py`
- [x] T019 [P] [US1] Create SentryStep class (`name="sentry"`, `fatal=False`, `skip_if` returns `not ctx.settings.sentry_dsn`) wrapping Sentry SDK init in `solune/backend/src/startup/steps/s09_sentry.py`

### Tests for User Story 1

- [x] T020 [P] [US1] Create unit test asserting `setup_logging()` is called and step conforms to Step Protocol in `solune/backend/tests/unit/startup/test_s01_logging.py`
- [x] T021 [P] [US1] Create unit test asserting asyncio exception handler is installed on the running loop in `solune/backend/tests/unit/startup/test_s02_asyncio_exc.py`
- [x] T022 [P] [US1] Create unit test with mock db asserting `init_database()` is called and `ctx.db` + `ctx.app.state.db` are set in `solune/backend/tests/unit/startup/test_s03_database.py`
- [x] T023 [P] [US1] Create unit test with mock db asserting `init_pipeline_state_store` is called exactly once in `solune/backend/tests/unit/startup/test_s04_pipeline_cache.py`
- [x] T024 [P] [US1] Create unit test with mock db asserting `init_done_items_store` is called exactly once in `solune/backend/tests/unit/startup/test_s05_done_items_cache.py`
- [x] T025 [P] [US1] Create unit test asserting singleton services are initialised and assigned to `ctx.app.state` in `solune/backend/tests/unit/startup/test_s06_singleton_svcs.py`
- [x] T026 [P] [US1] Create unit test asserting AlertDispatcher is created and assigned to `ctx.app.state` in `solune/backend/tests/unit/startup/test_s07_alert_dispatcher.py`
- [x] T027 [P] [US1] Create unit tests asserting OTel step runs when `otel_enabled=True`, reports `"skipped"` when `otel_enabled=False` in `solune/backend/tests/unit/startup/test_s08_otel.py`
- [x] T028 [P] [US1] Create unit tests asserting Sentry step runs when `sentry_dsn` is set, reports `"skipped"` when `sentry_dsn` is empty in `solune/backend/tests/unit/startup/test_s09_sentry.py`

### Integration for User Story 1

- [x] T029 [US1] Register steps 1–9 in `STARTUP_STEPS` list (importing from `s01_logging` through `s09_sentry`) in `solune/backend/src/startup/steps/__init__.py`
- [x] T030 [US1] Update `lifespan()` to create `StartupContext`, call `run_startup(STARTUP_STEPS[:9], ctx)` for steps 1–9, store `startup_report` on `app.state`, and keep inline code for steps 10–15 below in `solune/backend/src/main.py`

**Checkpoint**: Steps 1–9 are individually testable — `uv run pytest tests/unit/startup/ -v` passes. Existing integration tests still pass (`uv run pytest tests/integration/ -v`). App boots identically.

---

## Phase 4: User Story 2 + User Story 3 — Declarative Step List Complete + Structured Boot Diagnostics (Priority: P2)

**Goal (US2)**: All 15 steps are declared in a single ordered list — adding, removing, or reordering a step is a one-line change.

**Goal (US3)**: Every startup step emits a structured log line with `step`, `status`, and `duration_ms` keys — an operations engineer can diagnose any slow or failing boot at a glance.

**Independent Test (US2)**: Inject a custom step list with a new step at position 5; assert the runner executes it after step 4 and before step 6.

**Independent Test (US3)**: Run `run_startup` with all 15 steps (mocked dependencies); capture log output and assert each line contains the required fields.

**PR Alignment**: PR 3 — Move Pipeline/Polling Steps (Steps 10–15)

### Implementation for User Story 2

- [x] T031 [P] [US2] Create SignalWsStep class (`name="signal_ws_listener"`, `fatal=False`) wrapping Signal WebSocket listener setup and registering a shutdown hook via `ctx.shutdown_hooks.append(stop_signal_ws_listener)` in `solune/backend/src/startup/steps/s10_signal_ws.py`
- [x] T032 [P] [US2] Create CopilotPollingStep class (`name="copilot_polling_autostart"`, `fatal=False`) relocating `_auto_start_copilot_polling` helper verbatim in `solune/backend/src/startup/steps/s11_copilot_polling.py`
- [x] T033 [P] [US2] Create MultiProjectStep class (`name="multi_project_discovery"`, `fatal=False`) relocating `_discover_and_register_active_projects` helper verbatim in `solune/backend/src/startup/steps/s12_multi_project.py`
- [x] T034 [P] [US2] Create PipelineRestoreStep class (`name="app_pipeline_polling_restore"`, `fatal=False`) relocating `_restore_app_pipeline_polling` helper verbatim in `solune/backend/src/startup/steps/s13_pipeline_restore.py`
- [x] T035 [P] [US2] Create AgentMcpSyncStep class (`name="agent_mcp_sync"`, `fatal=False`) wrapping `_startup_agent_mcp_sync` fire-and-forget via `ctx.task_registry` in `solune/backend/src/startup/steps/s14_agent_mcp_sync.py`
- [x] T036 [P] [US2] Create BackgroundLoopsStep class (`name="background_loops"`, `fatal=True`) relocating `_session_cleanup_loop` and `_polling_watchdog_loop` verbatim and appending both to `ctx.background` in `solune/backend/src/startup/steps/s15_background_loops.py`

### Tests for User Story 3

- [x] T037 [P] [US3] Create unit test asserting SignalWsStep registers a shutdown hook in `ctx.shutdown_hooks` in `solune/backend/tests/unit/startup/test_s10_signal_ws.py`
- [x] T038 [P] [US3] Create unit test asserting CopilotPollingStep calls the relocated helper and exceptions are swallowed (`fatal=False`) in `solune/backend/tests/unit/startup/test_s11_copilot_polling.py`
- [x] T039 [P] [US3] Create unit test asserting MultiProjectStep calls the relocated helper with mocked dependencies in `solune/backend/tests/unit/startup/test_s12_multi_project.py`
- [x] T040 [P] [US3] Create unit test asserting PipelineRestoreStep calls the relocated helper with mocked dependencies in `solune/backend/tests/unit/startup/test_s13_pipeline_restore.py`
- [x] T041 [P] [US3] Create unit test asserting AgentMcpSyncStep fires via `ctx.task_registry.create_task()` in `solune/backend/tests/unit/startup/test_s14_agent_mcp_sync.py`
- [x] T042 [P] [US3] Create unit test asserting BackgroundLoopsStep appends exactly 2 coroutines to `ctx.background` in `solune/backend/tests/unit/startup/test_s15_background_loops.py`

### Integration for User Stories 2 + 3

- [x] T043 [US2] Register steps 10–15 in `STARTUP_STEPS` list (complete all 15 entries) in `solune/backend/src/startup/steps/__init__.py`
- [x] T044 [US2] Replace remaining inline startup code in `lifespan()` with `run_startup(STARTUP_STEPS, ctx)` for all 15 steps in `solune/backend/src/main.py`
- [x] T045 [US3] Remove relocated private helper functions (`_auto_start_copilot_polling`, `_discover_and_register_active_projects`, `_restore_app_pipeline_polling`, `_startup_agent_mcp_sync`, `_polling_watchdog_loop`, `_session_cleanup_loop`) from `solune/backend/src/main.py`

**Checkpoint**: All 15 steps go through the declarative runner. `uv run pytest tests/unit/startup/ -v` passes. `uv run pytest tests/integration/ -v` passes. Structured log lines emitted for every step.

---

## Phase 5: User Story 4 — Developer Verifies Shutdown Correctness After a Fatal Step Failure (Priority: P3)

**Goal**: Shutdown hooks run in LIFO order, built-in trailing hooks (drain tasks, stop polling, close database) always execute even after a fatal startup failure, and each hook is subject to a 30-second timeout.

**Independent Test**: Inject a fatal step that raises, then assert the database-close trailing hook still runs.

**PR Alignment**: PR 4 — Shutdown Mirror

### Implementation for User Story 4

- [x] T046 [US4] Replace `lifespan()` `finally:` block with `await run_shutdown(ctx)` call so that shutdown uses the runner with LIFO hooks and built-in trailing hooks in `solune/backend/src/main.py`

### Tests for User Story 4

- [x] T047 [US4] Add shutdown runner tests covering scenarios 10–13 from runner-contract.md § R4 (LIFO hook order, hook failure logged but does not block subsequent hooks, trailing hooks run after fatal startup, hook timeout cancellation) in `solune/backend/tests/unit/startup/test_runner.py`
- [x] T048 [US4] Add dedicated SC-006 test: force a fatal startup step, assert `ctx.db.close()` trailing hook still executes in `solune/backend/tests/unit/startup/test_runner.py`

**Checkpoint**: Shutdown is fully managed by the runner. `uv run pytest tests/unit/startup/ -v -k shutdown` passes. `lifespan()` is now ~30 lines.

---

## Phase 6: User Story 5 — Developer Reduces main.py Line Count (Priority: P3)

**Goal**: `main.py` is a concise orchestrator (≤250 lines). No file in `src/startup/` exceeds 120 lines. The entry point is readable and focused.

**Independent Test**: `wc -l solune/backend/src/main.py` returns ≤250; `find solune/backend/src/startup/ -name '*.py' | xargs wc -l` shows no file >120 lines.

### Validation for User Story 5

- [x] T049 [US5] Verify `main.py` contains ≤ 250 lines (SC-002) — trim any remaining dead code, unused imports, or orphaned comments in `solune/backend/src/main.py`
- [x] T050 [US5] Verify no single file in `src/startup/` exceeds 120 lines (SC-003) — split any oversized module if needed under `solune/backend/src/startup/`

**Checkpoint**: Line-count targets met. `main.py` ≤ 250 lines, all startup files ≤ 120 lines.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final quality gates and regression verification across all user stories

- [x] T051 [P] Run pyright type check on new startup package (`uv run pyright src/startup/`) — must exit 0
- [x] T052 [P] Run ruff lint on new startup package (`uv run ruff check src/startup/`) — must exit 0
- [x] T053 Run full test suite (`uv run pytest tests/ -v --timeout=120`) to verify zero regression against existing unit and integration tests (SC-004)
- [x] T054 Run quickstart.md verification recipes for all four PR phases to confirm end-to-end correctness

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2 / PR1)**: Depends on Phase 1 completion — **BLOCKS all user stories**
- **US1 (Phase 3 / PR2)**: Depends on Phase 2 (needs protocol + runner)
- **US2 + US3 (Phase 4 / PR3)**: Depends on Phase 3 (steps 1–9 must be wired before adding 10–15)
- **US4 (Phase 5 / PR4)**: Depends on Phase 4 (all 15 steps must be migrated before shutdown mirror)
- **US5 (Phase 6)**: Depends on Phase 5 (line-count target only achievable after full extraction)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependency on other user stories. **This is the MVP.**
- **US2 + US3 (P2)**: Depends on US1 completion (step list builds incrementally — steps 1–9 must exist before adding 10–15)
- **US4 (P3)**: Depends on US2/US3 (shutdown mirror requires all steps to be runner-managed)
- **US5 (P3)**: Depends on US4 (line-count target requires the `finally` block to be extracted)

### PR Mapping

| PR | Phases | User Stories | Independently Shippable? |
|---|---|---|---|
| PR 1 | 1 + 2 | Foundation | ✅ No behaviour change |
| PR 2 | 3 | US1 (P1) | ✅ Steps 1–9 via runner; 10–15 remain inline |
| PR 3 | 4 | US2 + US3 (P2) | ✅ All 15 steps via runner |
| PR 4 | 5 + 6 + 7 | US4 + US5 (P3) | ✅ Full extraction complete |

### Within Each User Story

- Step modules (T011–T019, T031–T036) before tests (T020–T028, T037–T042)
- Tests before integration wiring (T029–T030, T043–T045, T046)
- All step/test modules marked [P] can run in parallel within their group
- Integration tasks are sequential (they modify shared files)

---

## Parallel Opportunities

### Phase 2: Foundational

```text
# After T003+T004+T005 (protocol.py + runner.py — sequential, same conceptual unit):
Parallel: T006 (re-exports __init__.py)
        + T007 (steps/__init__.py)
        + T008 (conftest.py)
        + T009 (test_protocol.py)
# Then: T010 (test_runner.py — depends on conftest)
```

### Phase 3: US1 Step Modules (all [P])

```text
Parallel: T011 (s01_logging) + T012 (s02_asyncio_exc) + T013 (s03_database)
        + T014 (s04_pipeline_cache) + T015 (s05_done_items_cache)
        + T016 (s06_singleton_svcs) + T017 (s07_alert_dispatcher)
        + T018 (s08_otel) + T019 (s09_sentry)
```

### Phase 3: US1 Test Modules (all [P])

```text
Parallel: T020 + T021 + T022 + T023 + T024 + T025 + T026 + T027 + T028
```

### Phase 4: US2 Step Modules (all [P])

```text
Parallel: T031 (s10_signal_ws) + T032 (s11_copilot_polling)
        + T033 (s12_multi_project) + T034 (s13_pipeline_restore)
        + T035 (s14_agent_mcp_sync) + T036 (s15_background_loops)
```

### Phase 4: US3 Test Modules (all [P])

```text
Parallel: T037 + T038 + T039 + T040 + T041 + T042
```

---

## Implementation Strategy

### MVP First (US1 Only — PR1 + PR2)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational / PR1 (T003–T010)
3. Complete Phase 3: US1 / PR2 (T011–T030)
4. **STOP and VALIDATE**: Run `uv run pytest tests/unit/startup/ -v` + `uv run pytest tests/integration/ -v`
5. Ship PR1 and PR2 — steps 1–9 are testable in isolation

### Incremental Delivery

1. PR1 (Phases 1+2) → Runner ready, fake-step tests green → Ship
2. PR2 (Phase 3 / US1) → Steps 1–9 testable, integration tests green → Ship (**MVP!**)
3. PR3 (Phase 4 / US2+US3) → All 15 steps declarative, structured logs complete → Ship
4. PR4 (Phases 5+6+7 / US4+US5) → Shutdown mirrored, line counts met, full suite green → Ship
5. Each PR adds value without breaking previous PRs

### Parallel Team Strategy

With multiple developers:

1. Team completes Phases 1+2 together (PR1)
2. Once Phase 2 is done:
   - Developer A: US1 step modules (T011–T019)
   - Developer B: US1 test modules (T020–T028) — can start as soon as step modules are drafted
3. After US1 integration (T029–T030):
   - Developer A: US2 step modules (T031–T036)
   - Developer B: US3 test modules (T037–T042) — can start as soon as step modules are drafted
4. US4 + US5 are small enough for a single developer (T046–T050)

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in this phase
- [US*] label maps task to specific user story for traceability
- Steps are classes implementing a `typing.Protocol` — not functions, not base-class inheritance
- Helper function relocations (T032–T036) are **verbatim** — no logic changes, only `try/except` removal (runner handles errors)
- `request_id_var` wrapping moves from individual helpers into the runner (T004) — per-step correlation is automatic
- Commit after each task or logical group
- Stop at any checkpoint to validate the current increment independently
- Avoid: modifying step internal logic, changing TaskGroup strategy, moving `create_app()`, touching singleton globals
