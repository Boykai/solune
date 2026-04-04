# Implementation Plan: Full-Stack Plan Pipeline Enhancement

**Branch**: `016-plan-pipeline-enhancement` | **Date**: 2026-04-04 | **Spec**: `/specs/016-plan-pipeline-enhancement/spec.md`
**Input**: Feature specification from parent issue [#687](https://github.com/Boykai/solune/issues/687)

## Summary

Evolve the `/plan` pipeline from a simple create-refine-approve loop into a versioned, step-editable planning surface with a dependency graph, structured refinement, and board-sync progress tracking. The enhancement spans three phases across 16 steps: Phase 1 delivers an iterative refinement loop (versioning, step feedback, guided prompts, diff highlights), Phase 2 adds step CRUD with a dependency DAG and drag-and-drop reordering, and Phase 3 polishes thinking events, adds export, and introduces board-sync progress tracking.

The approach builds on the existing SQLite/aiosqlite storage layer (repo pattern with `BEGIN IMMEDIATE` transactions), the FastAPI SSE streaming in `chat_agent.py`, and the `@dnd-kit` drag-and-drop patterns already proven in `ExecutionGroupCard.tsx`. Two new migrations (040, 041) extend the schema; no new npm dependencies are required.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript/React 19 (frontend)
**Primary Dependencies**: FastAPI, aiosqlite, Pydantic v2 (backend); React 19, @tanstack/react-query 5, @dnd-kit 6/10, Tailwind CSS 4 (frontend)
**Storage**: SQLite via aiosqlite; repo pattern with `BEGIN IMMEDIATE` transactions; latest migration is 039
**Testing**: pytest with coverage ≥75% (backend); Vitest with coverage ≥50% statements (frontend); Playwright E2E
**Target Platform**: Linux server (Docker containers on Azure Container Apps), modern browsers
**Project Type**: Web application (backend + frontend)
**Performance Goals**: Plan operations <200ms p95; SSE streaming latency <100ms first byte; DAG validation <10ms for ≤15 steps
**Constraints**: SQLite single-writer (transactions must be short); max 15 plan steps (simplifies DAG layout); no new npm dependencies for graph visualization
**Scale/Scope**: Single-user per session; plans contain 3–15 steps; version history unbounded but expected <50 versions per plan

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Specification-First Development — ✅ PASS

The parent issue (#687) provides a detailed specification with 16 prioritized steps, clear acceptance criteria per step, and explicit scope boundaries (three phases). Each step has defined dependencies and verification criteria.

### II. Template-Driven Workflow — ✅ PASS

This plan follows the canonical `plan-template.md` structure. All artifacts (research.md, data-model.md, contracts/, quickstart.md) use the prescribed output formats. No custom sections added without justification.

### III. Agent-Orchestrated Execution — ✅ PASS

The plan decomposes into single-responsibility phases: speckit.plan (this document) → speckit.tasks → speckit.implement. Each phase produces well-defined outputs consumed by the next.

### IV. Test Optionality with Clarity — ✅ PASS

Tests are mandated by the specification:
- Backend: `test_plan_store.py`, `test_api_chat.py` covering versioning, step CRUD, DAG validation, export, feedback
- Frontend: `PlanPreview.test.tsx`, `usePlan.test.tsx`, `PlanDependencyGraph.test.tsx`
- Coverage thresholds: backend ≥75%, frontend ≥50%

### V. Simplicity and DRY — ✅ PASS

- Reuses existing `@dnd-kit` patterns from `ExecutionGroupCard.tsx` (no new DnD library)
- Custom SVG for dependency graph (no new npm dep; max 15 nodes keeps it simple)
- Feedback is transient (injected into agent context), avoiding a new table
- Polling for board sync (simpler than webhooks for SQLite)
- Extends existing `/approve` endpoint rather than creating new ones where possible

### Post-Design Re-check — ✅ PASS

All five principles remain satisfied after Phase 1 design. The data model adds two tables and one column (minimum viable schema). API contracts extend existing patterns. No unnecessary abstractions introduced.

## Project Structure

### Documentation (this feature)

```text
specs/016-plan-pipeline-enhancement/
├── plan.md              # This file
├── research.md          # Phase 0: technology decisions and research
├── data-model.md        # Phase 1: entity definitions and relationships
├── quickstart.md        # Phase 1: developer getting-started guide
├── contracts/           # Phase 1: OpenAPI contract definitions
│   ├── plan-versioning.yaml
│   ├── step-crud.yaml
│   ├── step-feedback.yaml
│   └── plan-export.yaml
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── api/
│   │   └── chat.py                    # New endpoints: feedback, history, step CRUD, export, selective approve
│   ├── models/
│   │   └── plan.py                    # PlanVersion model, step mutation schemas, version field
│   ├── services/
│   │   ├── chat_store.py              # Versioning logic, step CRUD, DAG validation
│   │   ├── chat_agent.py              # Richer SSE events, feedback context injection
│   │   ├── agent_tools.py             # save_plan version increment
│   │   ├── plan_issue_service.py      # Selective step approval
│   │   └── dag_validator.py           # New: topological sort + cycle detection utility
│   ├── prompts/
│   │   └── plan_instructions.py       # Guided refinement, step feedback injection
│   └── migrations/
│       ├── 040_plan_versioning.sql    # New: version column + chat_plan_versions table
│       └── 041_plan_step_status.sql   # New: issue_status column on chat_plan_steps
└── tests/
    └── unit/
        ├── test_plan_store.py         # Versioning, step CRUD, DAG tests
        └── test_api_chat.py           # Endpoint integration tests

solune/frontend/
├── src/
│   ├── components/
│   │   └── chat/
│   │       ├── PlanPreview.tsx              # Step CRUD, refinement sidebar, DnD, diff, progress, export
│   │       ├── PlanDependencyGraph.tsx      # New: SVG dependency graph
│   │       └── ThinkingIndicator.tsx        # Breadcrumbs, collapsible tool details
│   ├── hooks/
│   │   └── usePlan.ts                       # New mutations: feedback, step CRUD, history, export
│   ├── services/
│   │   └── api.ts                           # New client functions for all endpoints
│   └── types/
│       └── index.ts                         # PlanVersion, StepFeedback, extended interfaces
└── tests/
    ├── src/components/chat/
    │   ├── PlanPreview.test.tsx
    │   └── PlanDependencyGraph.test.tsx
    └── src/hooks/
        └── usePlan.test.tsx
```

**Structure Decision**: Web application (backend + frontend) following the existing `solune/backend` and `solune/frontend` directory structure. All changes extend existing files except for `dag_validator.py` (backend utility) and `PlanDependencyGraph.tsx` (frontend component), which are new single-purpose modules.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New `dag_validator.py` module | Isolates topological sort + cycle detection logic for testability | Inline in `chat_store.py` would mix graph logic with persistence concerns |
| `chat_plan_versions` table | Required for version history and diff computation | JSON column on `chat_plans` would limit query capabilities and grow unbounded in a single row |
| Custom SVG component | Lightweight dependency graph visualization for ≤15 nodes | Third-party library (d3, dagre) would add npm dependency for a simple use case |
