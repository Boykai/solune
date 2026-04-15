# Implementation Plan: Loading Performance

**Branch**: `003-loading-performance` | **Date**: 2026-04-15 | **Spec**: [./spec.md](./spec.md)
**Input**: Parent issue Boykai/solune#1904 — Loading Performance (PR #1915)

## Summary

Reduce the project-selection critical path by keeping `POST /projects/{id}/select` and the first `GET /board/projects/{id}` focused on interactive board data only: pre-warm board data as soon as a project is selected, skip Done/closed sub-issue fetches during the initial load, defer reconciliation and other non-essential background work until after the board is interactive, and preserve existing cached Done-item/sub-issue data so the board still renders the same parent cards and GitHub pill links.

The current codebase already includes two important mitigations that this plan must preserve: `select_project()` reuses `verify_project_access` results to avoid one duplicate `list_user_projects()` call, and `_start_copilot_polling()` already starts with a 45-second delay. The remaining work is concentrated in the board-loading hot path (`backend/src/services/github_projects/board.py`) and the frontend loading experience (`frontend/src/hooks/useProjectBoard.ts`, `frontend/src/pages/ProjectsPage.tsx`).

## Technical Context

**Language/Version**: Python 3.12+ (backend); TypeScript ~6.0.2 + React 19.2 (frontend)  
**Primary Dependencies**: FastAPI, Pydantic v2, existing `InMemoryCache`/`cached_fetch`, `aiosqlite`-backed `done_items_store`, GitHub GraphQL/REST helpers, TanStack Query, Vitest, Playwright performance specs  
**Storage**: Existing in-memory cache plus SQLite-backed `done_items_cache` / session state; no new persistence system required  
**Testing**: Backend `uv run pytest` unit/performance coverage for board/projects services and APIs; frontend `npm run test`, `npm run type-check`, `npm run lint`, `npm run build`, plus existing Playwright project-load performance spec when credentials are available  
**Target Platform**: Solune web application (`solune/backend` + `solune/frontend`)  
**Project Type**: Web application performance enhancement  
**Performance Goals**: Small-project board interactive in under 2 seconds; large-project meaningful active-board content in about 5 seconds with an 8-second upper acceptance bound for active columns; repeat visits served from warm cache in under 500 ms  
**Constraints**: Preserve current board UX (parent issues + GitHub-linked sub-issue pills), avoid architectural rewrites, keep manual refresh capable of full data refresh, do not start non-essential background work on the initial critical path, continue serving stale/Done-cache fallback when GitHub is slow or unavailable  
**Scale/Scope**: Backend board-loading orchestration, cache/dedup behavior, selection warm-up scheduling, frontend progressive loading indicators, targeted backend/frontend/performance tests, no required database migration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Specification-First Development**: PASS — `./spec.md` defines prioritized user stories, acceptance scenarios, edge cases, and measurable outcomes for the loading-performance work.
- **II. Template-Driven Workflow**: PASS — This plan and all supporting artifacts are being generated from the canonical Speckit workflow for `./` and mirrored to the copilot branch root publication files.
- **III. Agent-Orchestrated Execution**: PASS — The work decomposes cleanly into backend critical-path shaping, selection/dedup orchestration, frontend progressive rendering, and validation.
- **IV. Test Optionality with Clarity**: PASS — The spec explicitly includes independent testing criteria, so the plan includes targeted backend unit/performance coverage plus frontend hook/page and optional Playwright validation.
- **V. Simplicity and DRY**: PASS — The plan reuses existing cache, Done-item persistence, `cached_fetch`, project selection flow, and frontend query architecture instead of introducing new services or storage.

**Post-Phase-1 Re-check**: PASS — Research and design keep the solution inside existing board/projects API seams, add only incremental response metadata and scheduling helpers, and reuse the current cache + Done-item store for deferred work. No constitution violations or complexity exceptions are required.

## Project Structure

### Documentation (this feature)

```text
.
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output — performance strategy decisions
├── data-model.md        # Phase 1 output — board load policy/state models
├── quickstart.md        # Phase 1 output — implementation + validation guide
├── contracts/
│   └── loading-performance-api.yaml
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── board.py                        # Board load contract / refresh semantics
│   │   │   └── projects.py                     # Project selection warm-up + polling timing
│   │   ├── models/
│   │   │   └── board.py                        # Board response metadata for partial/deferred loads
│   │   ├── services/
│   │   │   ├── cache.py                        # Shared cache helpers / request dedup reuse points
│   │   │   ├── done_items_store.py             # Done-item persistence reused for cached pills
│   │   │   ├── github_projects/
│   │   │   │   ├── board.py                    # Pagination, sub-issue fetch policy, reconciliation split
│   │   │   │   ├── issues.py                   # Sub-issue cache behavior
│   │   │   │   └── service.py                  # Existing GraphQL in-flight coalescing
│   │   │   └── copilot_polling/
│   │   │       └── polling_loop.py             # Preserve deferred background polling start
│   └── tests/
│       ├── performance/
│       │   └── test_board_load_time.py         # Existing perf regression harness
│       └── unit/
│           ├── test_api_board.py               # Board API behavior / refresh cache handling
│           ├── test_api_projects.py            # Selection and warm-up behavior
│           ├── test_board.py                   # Board service behavior
│           └── test_github_projects.py         # GitHub service / cache behavior
└── frontend/
    ├── e2e/
    │   └── project-load-performance.spec.ts    # Existing end-to-end timing check
    └── src/
        ├── hooks/
        │   ├── useProjectBoard.ts              # Board query state + progressive loading support
        │   └── useProjects.ts                  # Project selection query/mutation coordination
        ├── pages/
        │   └── ProjectsPage.tsx                # Loading indicator / partial Done-column progress UX
        ├── services/
        │   ├── api.ts                          # Board query params / response metadata
        │   └── schemas/                        # Update schema guards if response shape changes
        └── components/
            └── board/                          # Progress indicator / fallback banner reuse points
```

**Structure Decision**: Keep the change inside the existing backend `projects` + `board` APIs and the existing frontend `useProjects` / `useProjectBoard` / `ProjectsPage` flow. The feature is a performance-focused enhancement of current behavior, not a new product surface, so existing service, cache, and UX seams are the correct boundaries.

## Phase Execution Plan

### Phase 1 — Reshape the Board Critical Path

**Goal**: Make the first board response fast enough to render active work immediately without losing correctness for Done/closed items.

| Step | Action | Details |
|------|--------|---------|
| 1.1 | Split initial vs deferred board work | Refactor `backend/src/services/github_projects/board.py:get_board_data()` into explicit stages: project/item pagination, initial item grouping, deferred Done/closed enrichment, and deferred reconciliation. |
| 1.2 | Skip Done/closed sub-issue fetches on initial load | Reuse existing item status data to suppress REST `/sub_issues` fetches for Done/closed parents during initial load while still loading active parents and always skipping items labeled `sub-issue`. |
| 1.3 | Reuse stored Done data for pill rendering | Continue using `done_items_store` and cached sub-issue payloads so Done-column parent cards can render their existing pill links without refetching metadata on the critical path. |
| 1.4 | Defer reconciliation to a background pass | Remove reconciliation from the initial synchronous response path and schedule it after the first interactive board payload has been cached or returned. |
| 1.5 | Preserve explicit full refresh behavior | Keep `refresh=true` as the manual “full refresh” escape hatch, extending it so explicit refresh also reloads Done/closed sub-issues and reconciliation before the refreshed cache is finalized. |
| 1.6 | Add/extend backend coverage | Update board service/API tests for partial-load metadata, Done/closed skip rules, refresh semantics, and stale/Done-cache fallbacks. |

**Dependencies**: None — this defines the core behavior the rest of the work builds around.

**Output**: A board API/service design that returns interactive data first and defers expensive correctness work without changing user-visible board content.

### Phase 2 — Warm Selection and Deduplicate Concurrent Work

**Goal**: Start useful work earlier and ensure identical concurrent requests reuse the same upstream result.

| Step | Action | Details |
|------|--------|---------|
| 2.1 | Pre-warm board data from project selection | Extend `POST /projects/{id}/select` in `backend/src/api/projects.py` to start a best-effort board warm-up task immediately after session update so the frontend’s first board request can hit a warm cache. |
| 2.2 | Introduce API-level in-flight dedup where missing | Reuse the existing GraphQL coalescing in `github_projects/service.py` and add request-level coalescing for `list_projects`, `list_board_projects`, and selection-triggered warm-up/board fetch paths where concurrent callers can still double-trigger work. |
| 2.3 | Cancel or supersede stale warm-up work | Ensure rapid project switching or a second selection cancels/invalidates warm-up and deferred background work tied to the previously selected project. |
| 2.4 | Keep non-essential polling off the critical path | Preserve the delayed Copilot polling start and ensure any new warm-up/deferred scheduling does not accidentally reintroduce immediate background contention. |
| 2.5 | Add/extend selection-path tests | Cover selection warm-up, stale project cancellation, deduplicated project-list calls, and polling timing expectations in backend tests. |

**Dependencies**: Phase 1 defines what “warm” board data means and what remains deferred.

**Output**: The first board request after project selection shares a warmed or coalesced result instead of starting from zero.

### Phase 3 — Progressive Frontend Loading Experience

**Goal**: Let users see and interact with active work as soon as the backend can provide it, while communicating background progress clearly.

| Step | Action | Details |
|------|--------|---------|
| 3.1 | Extend frontend types and API client | Update `frontend/src/services/api.ts`, related schema guards, and frontend types so the board response can expose partial-load metadata (for example, whether Done/reconciliation work is still pending). |
| 3.2 | Use warmed board results in `useProjectBoard()` | Keep the current TanStack Query flow, but teach it to treat the initial board payload as interactive-ready while allowing deferred refresh completion to merge in later. |
| 3.3 | Surface Done-column progress in `ProjectsPage` | Reuse existing loading/progress banner patterns to show a subtle indicator when Done/history backfill is still in progress without blocking the board itself. |
| 3.4 | Preserve manual full refresh UX | Ensure existing refresh controls can request the “full” load path and clearly distinguish between initial load, background backfill, and refresh failures. |
| 3.5 | Add/extend frontend tests | Update hook/page tests for project selection, progressive board rendering, Done-column progress indication, and non-blocking error handling. |

**Dependencies**: Phases 1–2 provide response metadata and warm-cache behavior.

**Output**: The frontend becomes interactive as soon as active data is ready and communicates deferred Done/history work without showing a broken state.

### Phase 4 — Verification and Performance Regression Guardrails

**Goal**: Confirm the optimized load path works for both correctness and performance.

| Step | Action | Details |
|------|--------|---------|
| 4.1 | Backend targeted validation | Run the existing board/projects unit tests plus the performance regression harness for the board endpoint. |
| 4.2 | Frontend targeted validation | Run existing hook/page tests and standard frontend type-check/lint/build validation for the updated loading flow. |
| 4.3 | Optional authenticated E2E timing check | Re-run the Playwright project-load performance spec when auth state and a real `E2E_PROJECT_ID` are available. |
| 4.4 | Manual verification | Select a project, confirm the board becomes interactive before Done/history backfill completes, verify manual refresh still reloads everything, and verify rapid project switching cancels stale background work. |

**Dependencies**: Phases 1–3 complete.

**Output**: Verified loading-performance improvements with regression coverage around correctness, UX, and measured timing.

## Verification Matrix

| Check | Command / Method | After Phase |
|-------|------------------|-------------|
| Markdown plan artifacts | `cd . && npx --yes markdownlint-cli plan.md research.md data-model.md quickstart.md --config solune/.markdownlint.json` | 0, 1 |
| Backend board/projects unit tests | `cd solune/backend && uv run --with pytest --with pytest-asyncio pytest tests/unit/test_api_board.py tests/unit/test_api_projects.py tests/unit/test_board.py tests/unit/test_github_projects.py -q` | 1, 2, 4 |
| Backend board performance harness | `cd solune/backend && PERF_GITHUB_TOKEN=... PERF_PROJECT_ID=... uv run --with pytest pytest tests/performance/test_board_load_time.py -m performance -q` | 4 |
| Frontend targeted tests | `cd solune/frontend && npm run test -- --reporter=verbose --run src/hooks/useProjects.test.tsx src/hooks/useProjectBoard.test.tsx src/pages/ProjectsPage.test.tsx` | 3, 4 |
| Frontend type safety | `cd solune/frontend && npm run type-check` | 3, 4 |
| Frontend lint | `cd solune/frontend && npm run lint` | 4 |
| Frontend build | `cd solune/frontend && npm run build` | 4 |
| Playwright project-load timing | `cd solune/frontend && E2E_PROJECT_ID=... npx playwright test e2e/project-load-performance.spec.ts --headed` | 4 |
| Manual flow validation | Select project → board interactive → Done/history backfill indicator → full refresh → rapid project switch cancellation | 4 |

## Decisions

| Decision | Rationale |
|----------|-----------|
| **Keep `GET /board/projects/{id}` as the main board endpoint** | Minimizes change surface and lets the frontend reuse the existing query path; performance gains come from changing load phases, not inventing a new transport. |
| **Use existing Done-item persistence as the initial Done/history data source** | `done_items_store` already exists and is specifically intended for fast cold-start and stale fallback behavior, so it should anchor the Done-column optimization instead of a new table or cache. |
| **Treat manual refresh as the full-fidelity path** | It preserves correctness for rare Done/closed changes without forcing every initial load to pay the same cost. |
| **Warm board data during selection, but never block selection on it** | Users benefit when the board request lands on a warm cache, but selection must still return quickly even if warm-up fails. |
| **Preserve delayed Copilot polling instead of moving it back onto the hot path** | The code already shows a 45-second delay; the plan should not regress that mitigation while introducing new background work. |

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Done/closed skip logic hides pills for items without cached sub-issue data | Users could see incomplete Done cards on first load | Use stored Done-item payloads as the primary fallback and document manual refresh / background backfill as the completeness path. |
| Deferred reconciliation misses items longer than expected | Board accuracy could lag after first render | Make reconciliation idempotent, schedule it immediately after interactive load, and surface changes via existing query invalidation/refresh mechanisms. |
| Warm-up tasks race with rapid project switching | Wasted work or stale board cache entries | Key warm-up/deferred tasks by project/session and cancel or supersede stale tasks when selection changes. |
| Extra response metadata causes frontend schema drift | Board page could fail parsing after backend changes | Update backend models, frontend schemas, and hook/page tests together under one contract. |
| Reusing cache/in-flight primitives incompletely | Duplicate work could still happen under cold-start concurrency | Add explicit tests around concurrent `GET /projects`, `GET /board/projects`, and selection-triggered warm-up paths. |

## Complexity Tracking

> No constitution violations found. No complexity justifications required.
