# Implementation Plan: Enrich Activity Page with Meaningful Events

**Branch**: `002-enrich-activity-events` | **Date**: 2026-03-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-enrich-activity-events/spec.md`

## Summary

The Activity page currently tracks 8 event types (CRUD for pipeline/agent/tool/app/chore, cleanup, webhook, status_change) but misses critical operations like pipeline launches, settings changes, project lifecycle, workflow completions, and granular webhook events. This plan adds ~12 new backend `log_event` calls across settings, projects, pipelines, orchestrator, and webhooks endpoints; a new `GET /activity/stats` summary endpoint with server-side SQL aggregation; and enriches the frontend Activity page with a stats dashboard header, time-bucketed grouping, status badges, and entity context pills. No database migration is needed — new event types reuse the existing `activity_events` schema as new string values.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript/React (frontend)
**Primary Dependencies**: FastAPI, Pydantic, aiosqlite (backend); React, Vite, TailwindCSS (frontend)
**Storage**: SQLite via aiosqlite (no schema changes — reuses existing `activity_events` table)
**Testing**: pytest + pytest-asyncio (backend), Vitest (frontend)
**Target Platform**: Linux server (Docker)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: Stats endpoint responds within 2 seconds (SC-002); SQL aggregation for efficiency (FR-009)
**Constraints**: Activity logging must never block primary operations (fire-and-forget via `activity_logger.log_event`); no new database migration; no charting library
**Scale/Scope**: ~12 new `log_event` call sites across 5 backend files; 1 new API endpoint; 1 new service function; frontend: 1 new hook, 1 new API method, expanded ActivityPage with stats cards + time grouping + badges/pills

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | `spec.md` exists with 6 prioritized user stories (P1-P3), Given-When-Then acceptance scenarios, edge cases, and clear scope boundaries (excluded: login tracking, search analytics, cache events) |
| II. Template-Driven | ✅ PASS | All artifacts follow canonical templates from `.specify/templates/` |
| III. Agent-Orchestrated | ✅ PASS | Single-responsibility: this plan phase produces design artifacts; implementation deferred to `/speckit.tasks` + `/speckit.implement` |
| IV. Test Optionality | ✅ PASS | Spec explicitly requests backend and frontend tests (Phase 4 in issue description); tests will be included in task generation |
| V. Simplicity and DRY | ✅ PASS | Uses existing `log_event` fire-and-forget pattern for all new event points; stats use simple SQL COUNT/GROUP BY; time bucketing is client-side only; stats as number cards (no charting library). No new abstractions beyond a single `get_activity_stats()` function |

**Gate Result**: ALL PASS — proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/002-enrich-activity-events/
├── plan.md              # This file
├── research.md          # Phase 0: Research findings
├── data-model.md        # Phase 1: Entity and data model
├── quickstart.md        # Phase 1: Developer quickstart guide
├── contracts/           # Phase 1: API contracts
│   └── activity-stats.yaml  # Stats endpoint contract
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── api/
│   │   ├── activity.py          # MODIFY: Add GET /activity/stats route (before /{entity_type}/{entity_id})
│   │   ├── pipelines.py         # MODIFY: Add log_event in execute_pipeline_launch
│   │   ├── projects.py          # MODIFY: Add log_event for project creation and selection
│   │   ├── settings.py          # MODIFY: Add log_event for settings updates
│   │   └── webhooks.py          # MODIFY: Enrich webhook log_event with granular actions
│   ├── models/
│   │   └── activity.py          # MODIFY: Add ActivityStats Pydantic model
│   └── services/
│       ├── activity_service.py  # MODIFY: Add get_activity_stats() query function
│       ├── activity_logger.py   # EXISTING: log_event (no changes needed)
│       └── workflow_orchestrator/
│           └── orchestrator.py  # MODIFY: Add log_event for workflow completion and agent triggering
└── tests/
    └── unit/
        └── test_api_activity.py # MODIFY: Add stats endpoint tests

solune/frontend/
├── src/
│   ├── pages/
│   │   └── ActivityPage.tsx     # MODIFY: Add stats dashboard, time grouping, badges, pills, new categories
│   ├── hooks/
│   │   └── useActivityStats.ts  # NEW: Hook for fetching activity stats
│   ├── services/
│   │   └── api.ts               # MODIFY: Add activityApi.stats() method
│   └── types/
│       └── index.ts             # MODIFY: Add ActivityStats type
└── tests/
    └── [frontend test files for stats, time bucketing, categories]
```

**Structure Decision**: Web application structure. Changes span both `solune/backend/` (new log points, stats endpoint, stats service function) and `solune/frontend/` (stats UI, time grouping, visual enhancements). No new modules or packages — all changes extend existing files except one new frontend hook (`useActivityStats.ts`).

## Constitution Re-Check (Post-Design)

*Re-evaluation after Phase 1 design artifacts are complete.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Design artifacts (data-model, contracts, quickstart) all trace back to spec.md requirements FR-001 through FR-016 |
| II. Template-Driven | ✅ PASS | All generated artifacts follow canonical templates |
| III. Agent-Orchestrated | ✅ PASS | Plan phase complete; handoff to `/speckit.tasks` for task decomposition |
| IV. Test Optionality | ✅ PASS | Tests explicitly requested in spec — backend tests for log_event calls and stats endpoint; frontend tests for stats rendering and time bucketing |
| V. Simplicity and DRY | ✅ PASS | All new log points use the same `log_event(db, event_type=..., ...)` pattern; single `get_activity_stats()` SQL function; frontend time bucketing is a pure utility function; stats cards follow existing stat-box pattern from CelestialCatalogHero |

**Gate Result**: ALL PASS — ready for Phase 2 (`/speckit.tasks`).

## Complexity Tracking

> No constitution violations — this section is intentionally empty.
