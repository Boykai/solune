# Implementation Plan: Performance Review

**Branch**: `001-performance-review` | **Date**: 2026-04-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-performance-review/spec.md`

## Summary

Deliver a balanced first pass of measurable, low-risk performance improvements across both backend and frontend. The approach captures baselines before any code changes, then targets the highest-value issues already surfaced in the codebase: backend GitHub API churn during idle board viewing (WebSocket change detection, sub-issue cache reuse, polling refinement) and frontend board responsiveness (broad query invalidation, full-list rerenders, hot event listeners). Board virtualization, major service decomposition, and new dependencies are explicitly deferred unless first-pass measurements prove them necessary.

## Technical Context

**Language/Version**: Python ≥3.12 (Pyright targets 3.13) — backend; TypeScript ~6.0.2 — frontend
**Primary Dependencies**: FastAPI, Uvicorn, githubkit, httpx, Pydantic v2, slowapi (backend); React 19, TanStack React Query 5, @dnd-kit, Radix UI, Vite 8, Tailwind CSS 4 (frontend)
**Storage**: SQLite via aiosqlite (durable settings/sessions); in-memory `InMemoryCache` for transient data (board, projects, sub-issues)
**Testing**: pytest + pytest-asyncio (backend); Vitest + React Testing Library (frontend); Playwright for E2E
**Target Platform**: Linux server (Docker) — backend; Modern browsers (SPA served via nginx) — frontend
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: ≥50% idle API call reduction (SC-001); ≥30% fewer GitHub calls with warm sub-issue caches (SC-002); lightweight updates reflected in <2s (SC-003); single board fetch per 2s debounce window (SC-004); ≥30 FPS on 50+ item boards (SC-005); stable derived-data computation counts (SC-006)
**Constraints**: No new external dependencies; no architectural rewrites; preserve existing rate-limit handling and manual refresh semantics; zero test regressions (SC-007)
**Scale/Scope**: Typical boards of 50–100 items across 4–8 columns; single-user rate-limit budget over 4+ hour sessions (SC-010)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Specification-First Development | ✅ PASS | `spec.md` contains 6 prioritized user stories (P1–P3) with Given-When-Then acceptance scenarios, clear scope boundaries, and out-of-scope declarations. |
| II | Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates from `.specify/templates/`. No custom sections required. |
| III | Agent-Orchestrated Execution | ✅ PASS | `speckit.plan` agent produces plan.md, research.md, data-model.md, contracts/, quickstart.md. Handoff to `speckit.tasks` for tasks.md. |
| IV | Test Optionality with Clarity | ✅ PASS | The spec explicitly requests test extension (User Story 5, FR-012). Tests are in-scope and mandated by the feature specification, not added speculatively. |
| V | Simplicity and DRY | ✅ PASS | All optimizations are low-risk (memoization, throttling, cache reuse, debouncing). No new abstractions, patterns, or dependencies introduced. Complexity Tracking not needed. |

**Pre-Phase 0 Gate Result**: All principles satisfied. Proceeding to Phase 0 research.

### Post-Phase 1 Re-Check

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Specification-First | ✅ PASS | Design artifacts (research.md, data-model.md, contracts/, quickstart.md) trace directly to spec requirements FR-001–FR-015. |
| II | Template-Driven | ✅ PASS | All generated artifacts follow template structure. No custom sections added. |
| III | Agent-Orchestrated | ✅ PASS | Phase 0 and Phase 1 outputs complete. Ready for `speckit.tasks` handoff. |
| IV | Test Optionality | ✅ PASS | Test extension scope confirmed in research.md RT-008. Extends existing test classes — no new test infrastructure. |
| V | Simplicity and DRY | ✅ PASS | Research confirmed all optimizations use existing patterns (RT-005, RT-007). No new abstractions. Contract defines behavioral rules only, no new API surfaces. |

**Post-Phase 1 Gate Result**: All principles satisfied. Design phase complete.

## Project Structure

### Documentation (this feature)

```text
specs/001-performance-review/
├── plan.md              # This file
├── research.md          # Phase 0: research findings
├── data-model.md        # Phase 1: key entities and state model
├── quickstart.md        # Phase 1: implementation quick-start guide
├── contracts/           # Phase 1: API contract notes
│   └── refresh-policy.md
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── board.py             # Board cache, sub-issue invalidation, manual refresh
│   │   │   ├── projects.py          # Project list, WebSocket subscription, board warmup
│   │   │   └── workflow.py          # Duplicate repo-resolution path
│   │   ├── services/
│   │   │   ├── cache.py             # InMemoryCache, coalesced_fetch, data hashing
│   │   │   ├── websocket.py         # ConnectionManager, broadcast_to_project
│   │   │   ├── copilot_polling/
│   │   │   │   └── polling_loop.py  # Polling hot path, rate-limit thresholds
│   │   │   └── github_projects/
│   │   │       └── service.py       # GraphQL coalescing, rate-limit tracking
│   │   └── utils.py                 # Shared repo resolution (4-step fallback)
│   └── tests/
│       └── unit/
│           ├── test_cache.py          # 38 tests — cache TTL, hashing, coalesced fetch
│           ├── test_api_board.py      # 75 tests — board cache, sub-issue invalidation
│           └── test_copilot_polling.py # 317 tests — polling lifecycle, rate limits
├── frontend/
│   ├── src/
│   │   ├── hooks/
│   │   │   ├── useRealTimeSync.ts       # WebSocket + fallback polling
│   │   │   ├── useBoardRefresh.ts       # Auto-refresh, manual refresh, debouncing
│   │   │   ├── useProjectBoard.ts       # Board query, adaptive polling, change detection
│   │   │   ├── useRealTimeSync.test.tsx  # 44 tests — WS lifecycle, fallback, debounce
│   │   │   └── useBoardRefresh.test.tsx  # 32 tests — timer, dedup, visibility
│   │   ├── components/
│   │   │   ├── board/
│   │   │   │   ├── BoardColumn.tsx       # Column rendering (memo'd)
│   │   │   │   ├── IssueCard.tsx         # Card rendering (memo'd)
│   │   │   │   └── AddAgentPopover.tsx   # Agent popover (not memo'd)
│   │   │   └── chat/
│   │   │       └── ChatPopup.tsx         # Resize drag (RAF-gated)
│   │   └── pages/
│   │       └── ProjectsPage.tsx          # Board orchestration, 11+ queries
│   └── tests/                            # (hooks co-located with source)
└── docs/
```

**Structure Decision**: Existing web application layout (backend + frontend under `solune/`). No structural changes. All modifications target existing files listed above.

## Complexity Tracking

> No violations detected. All changes use existing patterns (memoization, throttling, cache reuse, debouncing) already present in the codebase. No new abstractions, dependencies, or architectural patterns introduced.
