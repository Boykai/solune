# Implementation Plan: Performance Review

**Branch**: `002-performance-review` | **Date**: 2026-03-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-performance-review/spec.md`

## Summary

Deliver a balanced first pass of measurable, low-risk performance gains across backend and frontend. The approach starts by capturing baselines and instrumentation, then targets the highest-value issues already identified in the codebase: backend GitHub API churn around board refreshes and polling, and frontend board responsiveness issues caused by broad query invalidation, full-list rerenders, and hot event listeners. Broader architectural refactors (virtualization, large service decomposition) are explicitly deferred unless first-pass measurements prove them necessary.

The technical approach prioritizes surgical fixes to existing code paths — tightening WebSocket subscription change-detection, ensuring sub-issue cache reuse on warm reads, decoupling lightweight task updates from expensive board data queries on the frontend, and rationalizing the interaction between the four refresh sources (real-time, auto-refresh, fallback polling, manual). Low-risk render optimizations (memoization, prop stabilization, event listener throttling) round out the frontend work.

## Technical Context

**Language/Version**: Python ≥3.12 (target 3.13) for backend; TypeScript with React 19 for frontend
**Primary Dependencies**: FastAPI ≥0.135.0, httpx ≥0.28.0, githubkit (backend); React 19.2.0, @tanstack/react-query 5.96.0, @dnd-kit/core 6.3.1 (frontend)
**Storage**: In-memory cache (`src/services/cache.py`) with TTL-based entries; no external database for board data
**Testing**: pytest with asyncio (backend); Vitest 4.0.18 + Playwright 1.58.2 (frontend)
**Target Platform**: Linux server (backend); Modern browsers (frontend)
**Project Type**: Web application (backend + frontend)
**Performance Goals**: ≥50% reduction in idle board API requests over 5 minutes (SC-001); ≥20% faster board load on representative boards (SC-002); zero unnecessary full-board reloads from single-task updates (SC-003); smooth 60fps drag-and-drop interactions (SC-005)
**Constraints**: Must not introduce new external dependencies; must not change cache TTL values; must not alter polling/auto-refresh intervals; all existing tests must pass post-optimization (SC-006)
**Scale/Scope**: Representative board: 5+ columns, 50+ visible tasks; shared GitHub API rate-limit budget across all features

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First Development | ✅ PASS | spec.md contains prioritized user stories (P1–P3), Given-When-Then acceptance scenarios, clear scope boundaries, and out-of-scope declarations |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates from `.specify/templates/` |
| III. Agent-Orchestrated Execution | ✅ PASS | Single-responsibility agent (`speckit.plan`) producing defined outputs; handoff to `speckit.tasks` for Phase 2 |
| IV. Test Optionality with Clarity | ✅ PASS | Tests explicitly requested in spec (FR-016, FR-017, FR-018, User Story 5); regression coverage is a defined deliverable |
| V. Simplicity and DRY | ✅ PASS | Feature scope limited to low-risk optimizations; no new abstractions, no new dependencies; complexity deferred unless measurements justify it |

**Gate Result**: ALL PASS — proceed to Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/002-performance-review/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── refresh-contract.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── board.py           # Board cache TTL (300s), manual refresh, sub-issue invalidation
│   │   │   ├── projects.py        # WebSocket subscription, change detection, stale revalidation
│   │   │   └── workflow.py        # Repository resolution (uses shared utils.py)
│   │   ├── services/
│   │   │   ├── cache.py           # CacheEntry[T], cached_fetch(), TTL/stale/hash support
│   │   │   ├── copilot_polling/
│   │   │   │   └── polling_loop.py  # 60s poll cycle, rate-limit-aware step skipping
│   │   │   └── github_projects/
│   │   │       └── service.py     # GraphQL coalescing, cycle cache, sub-issue fetching (600s TTL)
│   │   └── utils.py               # Centralized resolve_repository(), BoundedSet/Dict
│   └── tests/unit/
│       ├── test_cache.py          # TTL, stale fallback, hash change detection, cached_fetch
│       ├── test_api_board.py      # Cache reuse, manual refresh, sub-issue invalidation, hash stability
│       └── test_copilot_polling.py  # Sub-issue filtering, rate-limit budgeting, step execution
├── frontend/
│   ├── src/
│   │   ├── hooks/
│   │   │   ├── useRealTimeSync.ts      # WebSocket + fallback polling, debounced invalidation
│   │   │   ├── useBoardRefresh.ts      # 5-min auto-refresh, manual refresh, debounce, visibility API
│   │   │   └── useProjectBoard.ts      # Board query, adaptive polling, change detection hash
│   │   ├── components/board/
│   │   │   ├── BoardColumn.tsx         # memo'd column, useMemo grouping, droppable
│   │   │   ├── IssueCard.tsx           # memo'd card, label/body memoization, draggable
│   │   │   └── AddAgentPopover.tsx     # Radix popover, memoized filtering
│   │   ├── components/chat/
│   │   │   └── ChatPopup.tsx           # RAF-gated resize, lifecycle-scoped listeners
│   │   └── pages/
│   │       └── ProjectsPage.tsx        # useMemo aggregations, optimistic mutations
│   └── src/hooks/
│       ├── useRealTimeSync.test.tsx   # WebSocket lifecycle, message handling, fallback
│       └── useBoardRefresh.test.tsx   # Timer dedup, manual refresh, visibility API
```

**Structure Decision**: Existing web application layout (backend + frontend) under `solune/`. No new directories or modules needed — all changes target existing files within the current structure.

## Complexity Tracking

> No constitution violations detected. No complexity justifications required.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)* | — | — |
