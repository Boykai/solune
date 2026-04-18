# Implementation Plan: Eliminate the "Dual-Init" Singleton Pattern

**Branch**: `002-dual-init-singleton` | **Date**: 2026-04-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-dual-init-singleton/spec.md`

## Summary

Make `app.state` the single source of truth for every service singleton, eliminating the "dual-init" pattern where services live as both module-level globals and `app.state` attributes with fallback logic in accessors. Turn module-level globals into `None` sentinels, introduce a `@resettable_state` registry for automatic test cleanup, and replace ad-hoc multi-path `patch()` calls with single `app.dependency_overrides` entries. The migration is internal wiring only — no endpoint behaviour changes.

## Technical Context

**Language/Version**: Python 3.13 (per `[tool.pyright] pythonVersion = "3.13"` in `solune/backend/pyproject.toml`)
**Primary Dependencies**: FastAPI (lifespan, `Depends()`, `app.state`, `dependency_overrides`); Starlette (Request, State); pytest / pytest-asyncio (autouse fixtures, `conftest.py`)
**Storage**: aiosqlite (existing; not modified by this feature — only the `get_database` accessor is refactored)
**Testing**: pytest with pytest-asyncio; `uv run pytest` from `solune/backend/`; existing `conftest.py` autouse fixtures for cache isolation
**Target Platform**: Linux server (CI on `ubuntu-latest`); local development via Docker Compose
**Project Type**: Web application — `solune/backend/` (Python) + `solune/frontend/` (TypeScript). This feature touches the backend tree only.
**Performance Goals**: No measurable latency regression on endpoint response times. Service initialisation remains sequential during lifespan startup (FR-010, SC-007).
**Constraints**: Full backward compatibility for all existing API endpoints (FR-012). No new third-party dependencies. Tests must run sequentially within a single event loop (existing pytest-asyncio default).
**Scale/Scope**: ~80 Python modules under `solune/backend/src/`. 8 service singletons to migrate. ~50 module-level mutable globals to register with the resettable registry. ~200 `patch()` calls in the test suite, of which ~40 target service singleton import paths.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
|---|---|
| **I. Specification-First Development** | ✅ `spec.md` exists with four prioritised P1–P4 user stories, Given-When-Then acceptance scenarios per story, explicit Independent Test sections, edge cases, and bounded scope. |
| **II. Template-Driven Workflow** | ✅ `spec.md` and this `plan.md` follow `.specify/templates/`. No ad-hoc sections beyond the templates. |
| **III. Agent-Orchestrated Execution** | ✅ This artifact is the `/speckit.plan` output; it explicitly hands off to `/speckit.tasks` for task decomposition. |
| **IV. Test Optionality with Clarity** | ✅ The spec explicitly mandates test changes (FR-004 through FR-009). The resettable registry and autouse fixture are test-time utilities. Test infrastructure is a core deliverable, not optional. |
| **V. Simplicity and DRY** | ✅ Uses FastAPI's built-in `Depends()` and `dependency_overrides` — no new DI framework. The `@resettable_state` decorator is a thin registry (~30 lines) with no runtime overhead in production. The existing `conftest.py` fixture is the extension point, not a custom plugin. |

**Result**: PASS — proceed to Phase 0. No entries in Complexity Tracking.

### Post-Design Re-check (after Phase 1 artifacts)

Re-evaluated after generating `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`. No new frameworks introduced. The `@resettable_state` decorator adds a single new module (`solune/backend/src/services/resettable_state.py`, ~30 lines). The contracts use FastAPI's existing `Depends()` mechanism exclusively. **Result**: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/002-dual-init-singleton/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (entities and relationships)
├── quickstart.md        # Phase 1 output (per-story verification recipes)
├── contracts/
│   ├── accessor-contract.md        # Dependency accessor function contract
│   ├── resettable-state-contract.md # @resettable_state registry contract
│   └── lifespan-registration-contract.md # app.state registration contract
├── checklists/
│   └── requirements.md  # Created during /speckit.specify
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created here)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── dependencies.py              # Primary edit: remove fallback-to-global logic from existing
│   │   │                                #   accessors; add new accessors for ChatAgentService,
│   │   │                                #   PipelineRunService, GitHubAuthService, AlertDispatcher
│   │   ├── main.py                      # Primary edit: lifespan registers ALL singletons on app.state;
│   │   │                                #   fail-fast on constructor errors (FR-010)
│   │   ├── services/
│   │   │   ├── resettable_state.py      # NEW: @resettable_state decorator + registry (~30 lines)
│   │   │   ├── chat_agent.py            # Edit: _chat_agent_service stays None; get_chat_agent_service()
│   │   │   │                            #   removed or redirected to app.state
│   │   │   ├── github_auth.py           # Edit: github_auth_service global → None sentinel
│   │   │   ├── alert_dispatcher.py      # Edit: set_dispatcher()/get_dispatcher() removed; _dispatcher → None
│   │   │   ├── websocket.py             # Edit: connection_manager global stays for import compat,
│   │   │   │                            #   but production reads go through app.state
│   │   │   ├── github_projects/
│   │   │   │   └── service.py           # Edit: github_projects_service global → None sentinel
│   │   │   ├── copilot_polling/
│   │   │   │   └── state.py             # Edit: _devops_tracking + other BoundedDicts registered
│   │   │   │                            #   with @resettable_state
│   │   │   ├── template_files.py        # Edit: _cached_files, _cached_warnings registered
│   │   │   │                            #   with @resettable_state
│   │   │   └── ...                      # Other modules with caches: register with @resettable_state
│   │   └── api/
│   │       ├── chat.py                  # Edit: replace get_chat_agent_service() calls with Depends()
│   │       ├── auth.py                  # Edit: replace github_auth_service direct import with Depends()
│   │       ├── projects.py              # Edit: remove direct global imports; use Depends() accessors
│   │       ├── tasks.py                 # Edit: remove direct global imports; use Depends() accessors
│   │       ├── workflow.py              # Edit: remove direct global imports; use Depends() accessors
│   │       ├── board.py                 # Edit: remove direct global imports; use Depends() accessors
│   │       ├── chores.py               # Edit: remove direct global imports; use Depends() accessors
│   │       ├── pipelines.py            # Edit: replace _get_run_service() with Depends() accessor
│   │       └── ...                      # Other API modules with direct singleton imports
│   └── tests/
│       ├── conftest.py                  # Primary edit: replace _clear_test_caches() body with
│       │                                #   resettable registry enumeration; reduce ~40 service
│       │                                #   patch() calls to dependency_overrides only
│       └── ...                          # Individual test files: replace multi-path patch() with
│                                        #   single dependency_overrides entries
```

**Structure Decision**: Single web-application backend. All source edits are confined to `solune/backend/`. One new module is created (`src/services/resettable_state.py`). No new directories, no frontend changes, no CI workflow changes.

## Complexity Tracking

> No constitutional violations to justify. Section intentionally empty.
