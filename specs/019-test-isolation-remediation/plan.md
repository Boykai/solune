# Implementation Plan: Test Isolation & State-Leak Remediation

**Branch**: `copilot/speckit-plan-test-isolation-remediation` | **Date**: 2026-04-07 | **Spec**: [#1077](https://github.com/Boykai/solune/issues/1077)
**Input**: Parent issue #1077 — Test Isolation & State-Leak Remediation

## Summary

The backend `_clear_test_caches` autouse fixture (conftest.py:245-267) only clears 3 of 20+ module-level mutable globals (`cache`, `_system_marked_ready_prs`, `clear_settings_cache()`), creating widespread cross-test state leaks. The frontend has a fake-timer leak in `useFileUpload.test.ts`, an ordering-dependent UUID counter in `setup.ts`, and several test files with `vi.spyOn()` but no `vi.restoreAllMocks()` cleanup.

The fix expands the central autouse fixture to clear ALL discovered module-level mutable state, adds `pytest-randomly` to surface ordering regressions, and fixes frontend cleanup gaps. The integration conftest's `_reset_integration_state` is left as defense-in-depth.

## Technical Context

**Language/Version**: Python >=3.12 (backend), TypeScript 6.0 (frontend)
**Primary Dependencies**: FastAPI, pytest, pytest-asyncio, pytest-randomly (NEW), Vitest, React 19.2.0
**Storage**: SQLite via aiosqlite (existing — `_db` globals in `pipeline_state_store.py`, `done_items_store.py` need clearing)
**Testing**: pytest (backend), Vitest + Testing Library (frontend)
**Target Platform**: Linux server (backend), Modern browsers (frontend)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: N/A — test infrastructure change, no runtime impact
**Constraints**: Zero breaking changes to production code; all existing tests must continue passing; coverage thresholds maintained (75% backend, 50% frontend)
**Scale/Scope**: 15+ backend modules with mutable globals; 5 frontend test files with cleanup gaps

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Parent issue #1077 provides detailed module-by-module specification with exact line numbers and clearing strategy |
| II. Template-Driven Workflow | ✅ PASS | Using canonical plan template; all artifacts in `specs/019-test-isolation-remediation/` |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan phase produces plan.md, research.md, data-model.md, quickstart.md; handoff to tasks phase |
| IV. Test Optionality | ✅ PASS | This feature IS about test infrastructure — verification via multiple random seeds is explicitly requested in Phase 4 |
| V. Simplicity and DRY | ✅ PASS | Central autouse fixture is the DRY approach — impossible to forget per-file cleanup. Reset locks to `None` (not `new Lock()`) is the simplest correct approach for asyncio |

**Gate Result**: ✅ ALL PASS — proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/019-test-isolation-remediation/
├── plan.md              # This file
├── research.md          # Phase 0: asyncio lock lifecycle, pytest-randomly config, vitest cleanup
├── data-model.md        # Phase 1: fixture structure and global state inventory
├── quickstart.md        # Phase 1: step-by-step developer guide
├── contracts/
│   ├── backend-fixture.md   # Contract for expanded _clear_test_caches fixture
│   └── frontend-cleanup.md  # Contract for frontend test cleanup patterns
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── pyproject.toml                              # Phase 2: add pytest-randomly to dev deps
│   ├── tests/
│   │   ├── conftest.py                             # Phase 1: expand _clear_test_caches (lines 245-267)
│   │   └── integration/
│   │       └── conftest.py                         # Phase 1: keep _reset_integration_state as defense-in-depth
│   └── src/
│       └── services/                               # Reference only — globals defined here, cleared in fixture
│           ├── pipeline_state_store.py              # _pipeline_states, _issue_main_branches, etc.
│           ├── copilot_polling/
│           │   ├── state.py                         # 20+ collections, locks, scalars
│           │   └── chat.py                          # _conversations (if exists)
│           ├── websocket.py                         # _ws_lock
│           ├── settings_store.py                    # _queue_mode_cache, _auto_merge_cache
│           ├── signal_chat.py                       # _signal_pending
│           ├── github_auth.py                       # _oauth_states
│           ├── agent_creator.py                     # _agent_sessions
│           ├── template_files.py                    # _cached_files, _cached_warnings
│           ├── app_templates/registry.py            # _cache
│           └── done_items_store.py                  # _db
│
└── frontend/
    └── src/
        ├── test/setup.ts                            # Phase 3: reset UUID counter via beforeEach
        └── hooks/
            └── useFileUpload.test.ts                # Phase 3: add afterEach vi.useRealTimers()
        ├── layout/
        │   ├── TopBar.test.tsx                      # Phase 3: add afterEach vi.restoreAllMocks()
        │   └── AuthGate.test.tsx                    # Phase 3: add afterEach vi.restoreAllMocks()
        └── hooks/
            ├── useAuth.test.tsx                     # Phase 3: add afterEach vi.restoreAllMocks()
            └── useAdaptivePolling.test.ts            # Already correct — has vi.restoreAllMocks()
```

**Structure Decision**: Web application (Option 2). This feature modifies test infrastructure across `solune/backend/tests/` and `solune/frontend/src/` — no new directories.

## Execution Phases (from Issue #1077)

### Phase 1 — Backend: Expand Central Autouse Fixture (CRITICAL)

| Step | Target | What to Clear | Current Status |
|------|--------|--------------|----------------|
| 1.1a | `api/chat.py:92-95` | `_messages`, `_proposals`, `_recommendations`, `_locks` | Only in integration conftest |
| 1.1b | `pipeline_state_store.py:28-41` | `_pipeline_states`, `_issue_main_branches`, `_issue_sub_issue_map`, `_agent_trigger_inflight`, `_project_launch_locks`, `_store_lock=None`, `_db=None` | `_project_launch_locks` never cleared (BUG) |
| 1.1c | `workflow_orchestrator/orchestrator.py` | `_orchestrator_instance=None`, `_tracking_table_cache` | Only in integration conftest |
| 1.1d | `workflow_orchestrator/config.py:38-41` | `_transitions`, `_workflow_configs` | Only in integration conftest |
| 1.1e | `copilot_polling/state.py:47-274` | 20+ collections, BoundedSet/Dict clears, scalar resets | Only `_system_marked_ready_prs` cleared |
| 1.1f | `websocket.py:12` | `_ws_lock=None` | Only in integration conftest |
| 1.1g | `settings_store.py:506,543` | `_queue_mode_cache`, `_auto_merge_cache` | Manual per-test only |
| 1.1h | `signal_chat.py:33` | `_signal_pending` | Never cleared |
| 1.1i | `github_auth.py:35` | `_oauth_states` | Never cleared |
| 1.1j | `agent_creator.py:107` | `_agent_sessions` | Never cleared |
| 1.1k | `template_files.py:49-50` | `_cached_files=None`, `_cached_warnings=None` | Never cleared |
| 1.1l | `app_templates/registry.py:13` | `_cache=None` | Never cleared |
| 1.1m | `done_items_store.py:27` | `_db=None` | Never cleared |
| 1.1n | `session_store.py:18` | `_encryption_service=None` | Never cleared |
| 1.2 | Event-loop locks | Reset `_ws_lock`, `_store_lock`, `_polling_state_lock`, `_polling_startup_lock` to `None` | Locks created in wrong event loop |
| 1.3 | Integration conftest | Keep `_reset_integration_state` as defense-in-depth | No changes needed |

### Phase 2 — Backend: Add pytest-randomly (HIGH)

| Step | Target | Action |
|------|--------|--------|
| 2.1 | `pyproject.toml` dev deps | Add `pytest-randomly>=3.16.0` |
| 2.2 | Verification | Run 3x with `--randomly-seed` values 12345, 99999, 42 |

### Phase 3 — Frontend: Fix Timer & UUID Leaks (HIGH)

| Step | Target | Action |
|------|--------|--------|
| 3.1 | `useFileUpload.test.ts:33` | Add `afterEach(() => { vi.useRealTimers(); })` |
| 3.2 | `setup.ts:10-18` | Reset `_counter = 0` in a `beforeEach` hook |
| 3.3a | `TopBar.test.tsx` | Add `afterEach(() => { vi.restoreAllMocks(); })` |
| 3.3b | `AuthGate.test.tsx` | Add `afterEach(() => { vi.restoreAllMocks(); })` |
| 3.3c | `useAuth.test.tsx` | Add `afterEach(() => { vi.restoreAllMocks(); })` |

### Phase 4 — Verification

| Step | Verification | Expected |
|------|-------------|----------|
| 4.1 | Backend: `pytest --randomly-seed=12345` | All pass |
| 4.2 | Backend: `pytest --randomly-seed=99999` | All pass |
| 4.3 | Backend: `pytest --randomly-seed=42` | All pass |
| 4.4 | Frontend: `npx vitest run --reporter=verbose` | No regressions |
| 4.5 | Coverage: backend ≥75%, frontend ≥50% | Thresholds met |
| 4.6 | Integration/concurrency tests | Pass with expanded fixture layering |

## Design Decisions

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| Central autouse fixture over per-file cleanup | DRY — impossible to forget; single point of maintenance | Per-file fixtures: error-prone, easy to forget new modules |
| Reset lazy-init locks to `None` (not `new Lock()`) | Avoids creating asyncio.Lock in wrong event loop; lock recreated on first use | `asyncio.Lock()`: binds to fixture's event loop, fails in test's loop |
| `_project_launch_locks` confirmed bug — cleared in fixture | Never cleared anywhere in codebase | Leave as-is: perpetual leak across tests |
| Scope excludes pytest-xdist, DI refactoring, new tests | Focused remediation; DI is architectural change | Full DI migration: too large, different issue |

## Constitution Re-Check (Post Phase 1 Design)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Issue #1077 serves as detailed specification |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates |
| III. Agent-Orchestrated Execution | ✅ PASS | Single-responsibility plan phase output |
| IV. Test Optionality | ✅ PASS | Test infrastructure is the feature |
| V. Simplicity and DRY | ✅ PASS | Central fixture is maximally DRY; no new abstractions |

**Gate Result**: ✅ ALL PASS — proceed to tasks phase

## Complexity Tracking

> No violations — all approaches use the simplest correct pattern.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | — | — |
