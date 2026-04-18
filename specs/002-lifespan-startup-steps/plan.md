# Implementation Plan: Refactor main.py Lifespan into src/startup/ Step Package

**Branch**: `002-lifespan-startup-steps` | **Date**: 2026-04-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-lifespan-startup-steps/spec.md`

## Summary

Extract the fifteen startup responsibilities currently inlined in `lifespan()` (main.py:642–802, ~160 lines of dense init logic) into a `src/startup/` package of named, individually-testable step classes. Each step implements a `Step` Protocol with `name`, `fatal`, `run(ctx)`, and optional `skip_if(ctx)`. A generic runner (`run_startup`) iterates a declarative step list, measures per-step timing, emits structured logs, and handles fatal-vs-non-fatal uniformly. Shutdown mirrors the pattern via `run_shutdown` with LIFO hook ordering. `create_app()` stays in `main.py`; only lifespan logic moves. Delivered across four independently-shippable PRs: scaffold+runner, pure-init steps, pipeline/polling steps, shutdown mirror.

## Technical Context

**Language/Version**: Python ≥3.12 (Pyright targets 3.13 per `solune/backend/pyproject.toml:119`)
**Primary Dependencies**: FastAPI ≥0.135.0, aiosqlite ≥0.22.0, sentry-sdk[fastapi] ≥2.22.0, OpenTelemetry SDK ≥1.33.0 — all existing; no new dependencies added
**Storage**: SQLite via aiosqlite (async wrapper in `src/services/database.py`); database connection is initialised in lifespan and passed through `StartupContext`
**Testing**: pytest + pytest-asyncio (asyncio_mode = "auto"); new `tests/unit/startup/` package with one test file per step + runner tests. No new test dependencies.
**Target Platform**: Linux server (CI: `ubuntu-latest` via `.github/workflows/ci.yml`); local dev via `uv run`
**Project Type**: Web application — `solune/backend/` (Python) + `solune/frontend/` (TypeScript). This feature touches the backend tree only.
**Performance Goals**: Startup wall-clock MUST NOT regress; per-step overhead of the runner (timing + logging) is <1ms per step. No new I/O paths.
**Constraints**: Zero behaviour change to the running application between pre- and post-refactor boots. All existing integration tests pass without modification. `main.py` drops to ≤250 lines; no startup package file >120 lines.
**Scale/Scope**: Backend is ~80 modules under `solune/backend/src/`. The refactor touches `main.py` (964 lines → ~250), creates ~20 new files in `src/startup/` and `tests/unit/startup/`. Six private helper functions (totalling ~620 lines) relocate verbatim.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
|---|---|
| **I. Specification-First Development** | ✅ `spec.md` exists with five prioritised P1–P3 user stories, Given-When-Then acceptance scenarios per story, Independent Test sections, five edge cases, eighteen functional requirements, and bounded scope (four PR phases, startup/shutdown only). |
| **II. Template-Driven Workflow** | ✅ `spec.md` and this `plan.md` follow `.specify/templates/`. No ad-hoc sections beyond the templates. |
| **III. Agent-Orchestrated Execution** | ✅ This artifact is the `/speckit.plan` output; it explicitly hands off to `/speckit.tasks` for task decomposition. |
| **IV. Test Optionality with Clarity** | ✅ Tests are explicitly requested: spec FR-018 mandates independently unit-testable steps, SC-001 requires sub-2s tests, SC-005 requires structured-log assertions. New `tests/unit/startup/` package is created as part of the feature. |
| **V. Simplicity and DRY** | ✅ The Step Protocol is the minimal abstraction needed to make steps declarative and testable — three required members (`name`, `fatal`, `run`) plus one optional (`skip_if`). `StartupContext` is a mutable dataclass matching the existing `app.state` access pattern (no DI container). Four-PR phasing is the simplest delivery sequence. No Complexity Tracking entries required. |

**Result**: PASS — proceed to Phase 0. No entries in Complexity Tracking.

### Post-Design Re-check (after Phase 1 artifacts)

Re-evaluated after generating `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`. The Step Protocol introduces one new abstraction (justified by testability per spec P1 user story). `StartupContext` mirrors the existing mutable-state pattern (no new paradigm). No new external dependencies. Constraints still satisfied. **Result**: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/002-lifespan-startup-steps/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (Step, StepOutcome, StartupContext entities)
├── quickstart.md        # Phase 1 output (per-PR verification recipes)
├── contracts/
│   ├── step-protocol-contract.md    # Step Protocol and StepOutcome shape
│   ├── runner-contract.md           # run_startup / run_shutdown semantics
│   └── context-contract.md          # StartupContext fields and lifecycle
├── checklists/
│   └── requirements.md              # Created during /speckit.specify
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created here)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── main.py                          # Refactor target (964 → ~250 lines)
│   │   │                                    #   create_app() stays here
│   │   │                                    #   lifespan() shrinks to ~30-line orchestrator
│   │   ├── startup/                         # NEW — startup step package
│   │   │   ├── __init__.py                  # Re-exports: run_startup, run_shutdown,
│   │   │   │                                #   StartupContext, Step, StepOutcome
│   │   │   ├── protocol.py                  # Step Protocol + StepOutcome dataclass
│   │   │   │                                #   + StartupContext dataclass
│   │   │   ├── runner.py                    # run_startup(steps, ctx) / run_shutdown(steps, ctx)
│   │   │   │                                #   timing, logging, error aggregation
│   │   │   └── steps/                       # One module per step
│   │   │       ├── __init__.py              # Exports STARTUP_STEPS list
│   │   │       ├── s01_logging.py           # setup_logging()
│   │   │       ├── s02_asyncio_exc.py       # asyncio exception handler
│   │   │       ├── s03_database.py          # init_database + migrations
│   │   │       ├── s04_pipeline_cache.py    # init_pipeline_state_store
│   │   │       ├── s05_done_items_cache.py  # init_done_items_store
│   │   │       ├── s06_singleton_svcs.py    # github_projects_service, connection_manager
│   │   │       ├── s07_alert_dispatcher.py  # AlertDispatcher init
│   │   │       ├── s08_otel.py              # OpenTelemetry (skip_if not otel_enabled)
│   │   │       ├── s09_sentry.py            # Sentry (skip_if not sentry_dsn)
│   │   │       ├── s10_signal_ws.py         # Signal WebSocket listener
│   │   │       ├── s11_copilot_polling.py   # _auto_start_copilot_polling (verbatim)
│   │   │       ├── s12_multi_project.py     # _discover_and_register_active_projects (verbatim)
│   │   │       ├── s13_pipeline_restore.py  # _restore_app_pipeline_polling (verbatim)
│   │   │       ├── s14_agent_mcp_sync.py    # _startup_agent_mcp_sync (via task_registry)
│   │   │       └── s15_background_loops.py  # enqueue _session_cleanup_loop + _polling_watchdog_loop
│   │   ├── services/
│   │   │   └── task_registry.py             # Unchanged; StartupContext holds reference
│   │   └── middleware/
│   │       └── request_id.py                # Unchanged; runner wraps request_id_var per step
│   └── tests/
│       └── unit/
│           └── startup/                     # NEW — startup test package
│               ├── __init__.py
│               ├── conftest.py              # Shared fixtures (mock ctx, fake steps)
│               ├── test_runner.py           # Runner semantics (fatal, non-fatal, skip, timing)
│               ├── test_protocol.py         # Protocol conformance
│               ├── test_s01_logging.py      # Per-step tests
│               ├── test_s02_asyncio_exc.py
│               ├── test_s03_database.py
│               ├── test_s04_pipeline_cache.py
│               ├── test_s05_done_items_cache.py
│               ├── test_s06_singleton_svcs.py
│               ├── test_s07_alert_dispatcher.py
│               ├── test_s08_otel.py
│               ├── test_s09_sentry.py
│               ├── test_s10_signal_ws.py
│               ├── test_s11_copilot_polling.py
│               ├── test_s12_multi_project.py
│               ├── test_s13_pipeline_restore.py
│               ├── test_s14_agent_mcp_sync.py
│               └── test_s15_background_loops.py
└── (frontend/ unchanged)
```

**Structure Decision**: Web application (Option 2). All source edits are confined to `solune/backend/`. The new `src/startup/` package is a sibling of `src/services/`, `src/api/`, and `src/middleware/` — matching the existing flat-module layout under `src/`. Step modules use a numbered prefix (`s01_`, `s02_`, …) so that file-system ordering matches execution order. No existing directories are moved or renamed.

## Complexity Tracking

> No constitutional violations to justify. Section intentionally empty.
