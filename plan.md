# Implementation Plan: Codebase Modularity Review

**Branch**: `copilot/create-implementation-plan` | **Date**: 2026-04-11 | **Spec**: [#1367](https://github.com/Boykai/solune/issues/1367)
**Input**: Parent issue #1367 — Codebase Modularity Review (Overall: 6.5/10). Decompose monolithic hotspots into domain-scoped modules without changing public API surface or database schema.

## Summary

Refactor six monolithic hotspots across the backend (Python/FastAPI) and frontend (TypeScript/React) into domain-scoped modules. The refactoring targets, prioritized by impact:

1. **Split `api/chat.py`** (2930 lines → 10-file package) — the single biggest maintainability win
2. **Extract `ProposalOrchestrator`** service — convert 348-line god function into testable service class
3. **Split `services/api.ts`** (1876 lines → 18-file package) — improves frontend code-splitting and review scope
4. **Domain-scoped types** — `types/index.ts` (1525 lines → 11 domain files) — reduces merge conflicts
5. **Consolidate backend global state** — wrap 4 module-level dicts in `ChatStateManager` class
6. **Split `api/webhooks.py`** (1033 lines → 6-file package) — focused event handlers

All refactoring is **behavior-preserving** — no new features, no API changes, no schema changes. All existing tests must pass after each target.

| Phase | Scope | Targets | Key Output |
|-------|-------|---------|------------|
| 0 | Research | All targets | `research.md` with 9 decisions |
| 1 | Design & Contracts | All targets | `data-model.md`, `contracts/`, `quickstart.md` |
| 2 | Backend Chat Split | Target 1 + 2 + 5 | `api/chat/` package, `ProposalOrchestrator`, `ChatStateManager` |
| 3 | Backend Webhooks + Bootstrap | Target 6 + bonus | `api/webhooks/` package, `services/bootstrap.py` |
| 4 | Frontend API + Types Split | Target 3 + 4 | `services/api/` package, `types/*.ts` |
| 5 | Cleanup & Consistency | Test layout, barrel exports, circular deps | Standardized test dirs, import cleanup |

## Technical Context

**Language/Version**: Python ≥3.12 (pyright targets 3.13) / TypeScript 5.x
**Primary Dependencies**: FastAPI + aiosqlite + Pydantic v2 (backend); React 18 + @tanstack/react-query 5 + Zod 4 + Tailwind CSS 4 (frontend)
**Storage**: SQLite via aiosqlite — **no schema changes** in this refactoring
**Testing**: pytest with `asyncio_mode=auto` (backend, coverage ≥80%, 5200+ tests); Vitest (frontend, statements ≥60%, 2200+ tests)
**Target Platform**: Linux server (containerized backend), SPA in modern browsers (frontend)
**Project Type**: Web application (Python backend + TypeScript frontend)
**Performance Goals**: Zero performance regression — all changes are code-organizational
**Constraints**: Backward-compatible imports via barrel re-exports; no breaking API changes; no new dependencies
**Scale/Scope**: 6 refactoring targets across 2 codebases; ~8000 lines of code reorganized

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Issue #1367 provides complete specification with scored assessment, prioritized targets, and measurable outcomes |
| II. Template-Driven Workflow | ✅ PASS | This plan follows `plan-template.md`; all artifacts use canonical templates |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan agent produces plan; implement agent will execute phased tasks |
| IV. Test Optionality | ✅ PASS | No new tests required — this is a refactoring with existing test coverage. Tests validate that no regressions are introduced. |
| V. Simplicity and DRY | ✅ PASS | All splits follow domain boundaries; no new abstractions beyond `ChatStateManager` (which consolidates existing globals) and `ProposalOrchestrator` (which extracts an existing god function) |

**Gate Result**: PASS — no violations. Proceed to Phase 0.

### Post-Design Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | All design artifacts trace to issue #1367's six refactoring targets |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates |
| III. Agent-Orchestrated Execution | ✅ PASS | Clear phase boundaries with explicit handoffs; each target independently verifiable |
| IV. Test Optionality | ✅ PASS | Existing 5200+ backend + 2200+ frontend tests serve as regression suite; no new test authoring needed |
| V. Simplicity and DRY | ✅ PASS | Module splits follow existing domain boundaries; `ProposalOrchestrator` is the only new class with behavior (others are structural reorganizations) |

**Post-Design Gate Result**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
plan.md              # This file (speckit.plan output)
research.md          # Phase 0 output (9 research decisions)
data-model.md        # Phase 1 output (target module topology)
quickstart.md        # Phase 1 output (developer guide)
contracts/           # Phase 1 output (module interface contracts)
├── chat-package-interface.md
├── proposal-orchestrator-interface.md
├── webhooks-package-interface.md
├── frontend-api-package-interface.md
└── domain-types-interface.md
```

### Source Code — Backend Changes

```text
solune/backend/src/
├── api/
│   ├── chat/                    # NEW PACKAGE (from chat.py)
│   │   ├── __init__.py          # Router aggregation
│   │   ├── state.py             # ChatStateManager class
│   │   ├── helpers.py           # Shared utilities
│   │   ├── dispatch.py          # Message processing handlers
│   │   ├── messages.py          # Message CRUD endpoints
│   │   ├── proposals.py         # Proposal/recommendation endpoints
│   │   ├── plans.py             # Plan mode endpoints
│   │   ├── conversations.py     # Conversation CRUD endpoints
│   │   ├── streaming.py         # SSE streaming endpoints
│   │   └── models.py            # Module-local models
│   ├── webhooks/                # NEW PACKAGE (from webhooks.py)
│   │   ├── __init__.py          # Router aggregation
│   │   ├── common.py            # Signature verification, payload parsing
│   │   ├── pull_requests.py     # PR event handlers
│   │   ├── check_runs.py        # CI check handlers
│   │   ├── issues.py            # Issue event handlers
│   │   └── handlers.py          # Dispatch registry
│   └── [other files unchanged]
├── services/
│   ├── proposal_orchestrator.py # NEW (extracted from confirm_proposal)
│   ├── bootstrap.py             # NEW (extracted from main.py)
│   └── [other files unchanged]
├── main.py                      # SIMPLIFIED (~120 lines, from 859)
└── dependencies.py              # CLEANED (circular dep resolved)
```

### Source Code — Frontend Changes

```text
solune/frontend/src/
├── services/
│   ├── api/                     # NEW PACKAGE (from api.ts)
│   │   ├── index.ts             # Barrel re-export
│   │   ├── client.ts            # Shared API client
│   │   ├── auth.ts              # authApi
│   │   ├── chat.ts              # chatApi, conversationApi
│   │   ├── board.ts             # boardApi
│   │   ├── tasks.ts             # tasksApi
│   │   ├── projects.ts          # projectsApi
│   │   ├── settings.ts          # settingsApi
│   │   ├── workflow.ts          # workflowApi
│   │   ├── metadata.ts          # metadataApi, signalApi
│   │   ├── agents.ts            # agentsApi, agentToolsApi
│   │   ├── pipelines.ts         # pipelinesApi
│   │   ├── chores.ts            # choresApi
│   │   ├── tools.ts             # toolsApi
│   │   ├── apps.ts              # appsApi
│   │   ├── activity.ts          # activityApi
│   │   ├── cleanup.ts           # cleanupApi
│   │   ├── models.ts            # modelsApi
│   │   └── mcp.ts               # mcpApi
│   └── schemas/                 # [unchanged]
├── types/
│   ├── index.ts                 # BARREL RE-EXPORT ONLY (from 1525 lines)
│   ├── common.ts                # Shared types (PaginatedResponse, ApiError, etc.)
│   ├── chat.ts                  # Chat domain types
│   ├── board.ts                 # Board domain types
│   ├── pipeline.ts              # Pipeline domain types
│   ├── agents.ts                # Agent domain types
│   ├── tasks.ts                 # Task domain types
│   ├── projects.ts              # Project domain types
│   ├── settings.ts              # Settings domain types
│   ├── chores.ts                # Chore domain types
│   └── workflow.ts              # Workflow domain types
└── [other files unchanged]
```

**Structure Decision**: Web application with Python backend + TypeScript frontend. Both sides use package-with-barrel patterns to split monolithic files while maintaining backward-compatible imports.

## Refactoring Targets — Detailed Breakdown

### Target 1: Split `api/chat.py` → `api/chat/` Package

**Priority**: Highest — the single biggest maintainability win
**Before**: 2930 lines, 40 functions, 5 distinct responsibilities in one file
**After**: 10 files in a package, each 20-650 lines

| Step | Action | Verification |
|------|--------|-------------|
| 1.1 | Create `api/chat/__init__.py` with combined router | `from src.api.chat import router` works |
| 1.2 | Extract `ChatStateManager` into `state.py` | Class can be instantiated independently |
| 1.3 | Extract helper functions into `helpers.py` | Helpers importable from sub-module |
| 1.4 | Extract dispatch handlers into `dispatch.py` | Handlers importable from sub-module |
| 1.5 | Move message endpoints to `messages.py` | Message tests pass |
| 1.6 | Move proposal/recommendation code to `proposals.py` | Proposal tests pass |
| 1.7 | Move conversation endpoints to `conversations.py` | Conversation tests pass |
| 1.8 | Move plan mode endpoints to `plans.py` | Plan tests pass |
| 1.9 | Move streaming endpoints to `streaming.py` | Streaming tests pass |
| 1.10 | Move `FileUploadResponse` to `models.py` | Upload tests pass |
| 1.11 | Delete original `api/chat.py` | No import errors |
| 1.12 | Update all test imports | Full test suite passes |

**Dependencies**: None — can start immediately
**Risk**: Import path changes may break tests (mitigated by barrel re-export + test import updates)

### Target 2: Extract `ProposalOrchestrator` Service

**Priority**: High — converts untestable god function into testable service
**Before**: `confirm_proposal()` — 348 lines, touches GitHub API + SQLite + WebSocket + validation
**After**: `ProposalOrchestrator` class with 6 focused methods

| Step | Action | Verification |
|------|--------|-------------|
| 2.1 | Create `services/proposal_orchestrator.py` with class skeleton | Class importable |
| 2.2 | Extract `_validate_proposal()` method | Validation tests pass in isolation |
| 2.3 | Extract `_apply_edits()` method | Edit tests pass as pure function |
| 2.4 | Extract `_create_github_issue()` method | GitHub mock tests pass |
| 2.5 | Extract `_add_to_project()` method | Project assignment tests pass |
| 2.6 | Extract `_persist_status()` method | Persistence retry tests pass |
| 2.7 | Extract `_broadcast_update()` method | WebSocket mock tests pass |
| 2.8 | Wire `confirm()` to delegate to private methods | End-to-end proposal tests pass |
| 2.9 | Update `api/chat/proposals.py` to use orchestrator | API integration tests pass |

**Dependencies**: Target 1 (chat package split) should complete first so `proposals.py` exists
**Risk**: Low — behavior is preserved; only the call structure changes

### Target 3: Split `services/api.ts` → `services/api/` Package

**Priority**: High — improves frontend code-splitting and review scope
**Before**: 1876 lines, 20 namespace objects in one file
**After**: 18 domain files + barrel re-export + shared client

| Step | Action | Verification |
|------|--------|-------------|
| 3.1 | Create `services/api/client.ts` with shared utilities | API client importable |
| 3.2 | Extract each namespace into its domain file | Each file compiles independently |
| 3.3 | Create `services/api/index.ts` barrel | `import { chatApi } from '@/services/api'` works |
| 3.4 | Delete original `services/api.ts` | Build succeeds |
| 3.5 | Update API test imports | All frontend tests pass |

**Dependencies**: None — independent of backend work
**Risk**: Tree-shaking behavior may change (mitigated by bundle size comparison)

### Target 4: Domain-Scoped Types — `types/index.ts` → `types/*.ts`

**Priority**: Medium — reduces merge conflicts, improves IDE navigation
**Before**: 1525 lines, all domains in one file
**After**: 11 domain files + barrel re-export

| Step | Action | Verification |
|------|--------|-------------|
| 4.1 | Create `types/common.ts` with shared types | Compiles independently |
| 4.2 | Extract each domain's types to its file | Each file compiles with only `./common` import |
| 4.3 | Replace `types/index.ts` content with barrel re-exports | `import { ChatMessage } from '@/types'` works |
| 4.4 | Run TypeScript compiler | Zero new errors |

**Dependencies**: None — can proceed in parallel with Target 3
**Risk**: Circular imports between domain types (mitigated by strict common-only import rule)

### Target 5: Consolidate Backend Global State — `ChatStateManager`

**Priority**: Medium — addresses race conditions and memory management
**Before**: 4 module-level dicts with no lifecycle management
**After**: `ChatStateManager` class with capacity limits, injected via `Depends()`

| Step | Action | Verification |
|------|--------|-------------|
| 5.1 | Create `ChatStateManager` class in `api/chat/state.py` | Class instantiates correctly |
| 5.2 | Migrate `_messages` dict to `BoundedDict` in manager | Message caching works |
| 5.3 | Migrate `_proposals` dict | Proposal caching works |
| 5.4 | Migrate `_recommendations` dict | Recommendation caching works |
| 5.5 | Migrate `_locks` dict with `_global_lock` protection | Lock creation is thread-safe |
| 5.6 | Wire `ChatStateManager` to FastAPI lifespan | App starts with manager in `app.state` |
| 5.7 | Update all endpoints to use injected manager | Full test suite passes |
| 5.8 | Remove module-level dicts | No global mutable state in `api/chat/` |

**Dependencies**: Target 1 (chat package split) — `state.py` is part of the new package
**Risk**: Medium — changing state management can introduce subtle bugs (mitigated by running full test suite after each step)

### Target 6: Split `api/webhooks.py` → `api/webhooks/` Package

**Priority**: Medium — focused event handlers, mirrors GitHub event taxonomy
**Before**: 1033 lines, all event types in one file
**After**: 6 files in a package

| Step | Action | Verification |
|------|--------|-------------|
| 6.1 | Create `api/webhooks/__init__.py` with combined router | `from src.api.webhooks import router` works |
| 6.2 | Extract signature verification to `common.py` | Verification logic standalone |
| 6.3 | Extract PR handlers to `pull_requests.py` | PR webhook tests pass |
| 6.4 | Extract check run handlers to `check_runs.py` | Check run tests pass |
| 6.5 | Extract issue handlers to `issues.py` | Issue webhook tests pass |
| 6.6 | Create dispatch registry in `handlers.py` | All event types dispatch correctly |
| 6.7 | Delete original `api/webhooks.py` | No import errors |

**Dependencies**: None — independent of other targets
**Risk**: Low — webhook handlers are inherently event-type-scoped

### Bonus: Extract `services/bootstrap.py` from `main.py`

**Priority**: Low — improves main.py readability
**Before**: `main.py` at 859 lines mixes app definition with lifecycle management
**After**: `main.py` ~120 lines (declarative) + `bootstrap.py` ~700 lines (initialization)

| Step | Action | Verification |
|------|--------|-------------|
| B.1 | Create `services/bootstrap.py` with initialization functions | Functions importable |
| B.2 | Move service initialization logic | App starts correctly |
| B.3 | Move migration running logic | Migrations apply on startup |
| B.4 | Move background task setup | Polling/sync loops start |
| B.5 | Simplify `main.py` to app definition + lifespan call | App starts and all endpoints respond |

**Dependencies**: None
**Risk**: Low — startup logic is well-contained

## Execution Order and Dependencies

```text
Phase 2 (Backend Core):
  Target 1: Split api/chat.py ──────┐
  Target 5: ChatStateManager ───────┤ (depends on Target 1)
  Target 2: ProposalOrchestrator ───┘ (depends on Target 1)

Phase 3 (Backend Supporting):
  Target 6: Split api/webhooks.py ── (independent)
  Bonus: Extract bootstrap.py ────── (independent)

Phase 4 (Frontend):
  Target 3: Split services/api.ts ── (independent)
  Target 4: Domain-scoped types ──── (independent, parallel with Target 3)

Phase 5 (Cleanup):
  Test layout standardization ────── (after all splits complete)
  Circular dep resolution ─────────── (after backend splits complete)
  Barrel export consistency ────────── (after all splits complete)
```

## Success Metrics

| Metric | Before | After | How to Verify |
|--------|--------|-------|---------------|
| Largest backend file | 2930 lines (`chat.py`) | ~650 lines (`plans.py`) | `wc -l` on all backend files |
| Longest function | 348 lines (`confirm_proposal`) | ~60 lines (`ProposalOrchestrator.confirm`) | AST analysis |
| Frontend API file | 1876 lines (`api.ts`) | ~250 lines (`chat.ts`) | `wc -l` on all API files |
| Frontend types file | 1525 lines (`index.ts`) | ~300 lines (largest domain) | `wc -l` on type files |
| Module-level global state | 4 mutable dicts | 0 (all in `ChatStateManager`) | Grep for module-level `dict` |
| Backend test suite | All pass | All pass | `pytest tests/unit/ -q` |
| Frontend test suite | All pass | All pass | `npm test` |
| Backend coverage | ≥80% | ≥80% | `pytest --cov-fail-under=80` |
| Frontend coverage | ≥60% stmts | ≥60% stmts | `npm test -- --coverage` |

## Complexity Tracking

> **No violations identified** — all refactoring targets follow constitution principles.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |
