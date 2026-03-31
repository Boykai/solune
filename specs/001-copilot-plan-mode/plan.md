# Implementation Plan: Copilot-Style Planning Mode (v2)

**Branch**: `001-copilot-plan-mode` | **Date**: 2026-03-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-copilot-plan-mode/spec.md`

## Summary

Add a persistent `/plan` command to Solune's chat that enters a dedicated planning mode. The agent researches the selected project's repository context, generates a structured implementation plan with ordered steps and dependency annotations, and supports iterative refinement via natural-language follow-ups. Real-time SSE thinking events provide phase-aware feedback during agent processing. On approval, the plan converts into a GitHub parent issue with linked sub-issues per step. The feature spans backend (data model, plan agent service, SSE events, issue creation) and frontend (plan preview card, thinking indicator, plan mode banner, state management hook).

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript 6.0 + React 19 (frontend)
**Primary Dependencies**: FastAPI ≥0.135, agent-framework-core ≥1.0.0b1, agent-framework-github-copilot ≥1.0.0b1, sse-starlette ≥3.0, githubkit ≥0.14, Pydantic ≥2.12 (backend); React 19, @tanstack/react-query 5.91, lucide-react 1.7, Tailwind CSS 4.2 (frontend)
**Storage**: SQLite via aiosqlite ≥0.22 (WAL mode, file-based at `~/.solune/solune.db`)
**Testing**: pytest + pytest-asyncio (backend), Vitest + @testing-library/react (frontend), Playwright (e2e)
**Target Platform**: Linux server (backend), Modern browsers (frontend)
**Project Type**: Web application (separate backend + frontend)
**Performance Goals**: Plan generation <30s (SC-001), refinement iteration <15s (SC-002), issue creation <60s for ≤20 steps (SC-004), thinking indicator latency <1s (SC-005)
**Constraints**: SQLite single-writer (mitigated by WAL mode + busy_timeout), GitHub Issues API rate limits (60 unauthenticated / 5,000 authenticated per hour)
**Scale/Scope**: Plans with up to 20 steps (per SC-004), single concurrent plan per chat session

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Gate (before Phase 0)

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Specification-First Development | ✅ PASS | spec.md contains 6 prioritized user stories (P1–P3), Given-When-Then acceptance scenarios, 19 functional requirements, and clear scope boundaries. |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates: spec.md, plan.md, research.md, data-model.md, contracts/, quickstart.md. |
| III. Agent-Orchestrated Execution | ✅ PASS | speckit.specify → speckit.plan → speckit.tasks → speckit.implement chain respected. Plan agent has single responsibility (planning). |
| IV. Test Optionality with Clarity | ✅ PASS | Tests not mandated in spec. Testing strategy documented in quickstart.md for when tests are added during implementation. |
| V. Simplicity and DRY | ✅ PASS | No new dependencies required. Plan mode reuses existing agent framework, SSE infrastructure, SQLite storage, and Pydantic model patterns. No premature abstractions. |

### Post-Design Gate (after Phase 1)

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Specification-First Development | ✅ PASS | All design artifacts trace back to spec.md functional requirements (FR-001 through FR-019). |
| II. Template-Driven Workflow | ✅ PASS | research.md, data-model.md, contracts/plan-api.md, quickstart.md all generated following template structure. |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan agent is a single-responsibility agent with its own prompt (`plan_instructions.py`), restricted toolset (`register_plan_tools()`), and dedicated entry points (`run_plan()`/`run_plan_stream()`). |
| IV. Test Optionality with Clarity | ✅ PASS | Testing strategy documented but not mandated. Test files listed in quickstart.md for implementation phase. |
| V. Simplicity and DRY | ✅ PASS | Design reuses existing patterns: `chat_store.py` CRUD pattern for plan persistence, `@tool` decorator for `save_plan`, `EventSourceResponse` for SSE, `ChatAgentService` dispatch pattern for mode routing, `ActionType` enum for plan actions. No new libraries. Two new tables follow established schema conventions. |

## Project Structure

### Documentation (this feature)

```text
specs/001-copilot-plan-mode/
├── plan.md              # This file
├── spec.md              # Feature specification (input)
├── research.md          # Phase 0: Research findings and decisions
├── data-model.md        # Phase 1: Entity definitions and schema
├── quickstart.md        # Phase 1: Developer quickstart guide
├── contracts/
│   └── plan-api.md      # Phase 1: API endpoint contracts
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── models/
│   │   │   ├── chat.py              # MODIFY: Add PLAN_CREATE to ActionType
│   │   │   └── plan.py              # NEW: Plan + PlanStep Pydantic models
│   │   ├── prompts/
│   │   │   └── plan_instructions.py # NEW: Plan-mode system prompt
│   │   ├── services/
│   │   │   ├── chat_store.py        # MODIFY: Add plan CRUD functions
│   │   │   ├── chat_agent.py        # MODIFY: Add run_plan() + run_plan_stream()
│   │   │   ├── agent_tools.py       # MODIFY: Add save_plan tool + register_plan_tools()
│   │   │   └── plan_issue_service.py # NEW: Plan → GitHub Issues creation
│   │   ├── api/
│   │   │   └── chat.py              # MODIFY: Add plan mode routes
│   │   └── migrations/
│   │       └── 035_chat_plans.sql   # NEW: Plan tables migration
│   └── tests/
│       └── unit/
│           ├── test_plan_models.py       # NEW: Plan model tests
│           ├── test_plan_store.py        # NEW: Plan CRUD tests
│           ├── test_plan_agent.py        # NEW: Plan agent dispatch tests
│           ├── test_plan_tools.py        # NEW: save_plan tool tests
│           └── test_plan_issue_service.py # NEW: Issue creation tests
│
└── frontend/
    ├── src/
    │   ├── types/
    │   │   └── index.ts             # MODIFY: Add Plan, PlanStep, ThinkingEvent types
    │   ├── services/
    │   │   └── api.ts               # MODIFY: Add onThinking callback, plan API methods
    │   ├── components/
    │   │   └── chat/
    │   │       ├── MessageBubble.tsx      # MODIFY: Render PlanPreview for plan_create
    │   │       ├── ChatInterface.tsx      # MODIFY: ThinkingIndicator + plan mode banner
    │   │       ├── PlanPreview.tsx        # NEW: Rich plan display card
    │   │       └── ThinkingIndicator.tsx  # NEW: Phase-aware loading indicator
    │   └── hooks/
    │       └── usePlan.ts           # NEW: Plan state management hook
    └── src/
        └── components/chat/
            ├── __tests__/
            │   ├── PlanPreview.test.tsx        # NEW
            │   └── ThinkingIndicator.test.tsx  # NEW
            └── ...
```

**Structure Decision**: Web application structure (Option 2). The repository already uses `solune/backend/` and `solune/frontend/` as the primary source directories. All new files are placed within the existing directory hierarchy, following established naming conventions (snake_case for Python, PascalCase for React components).

## Implementation Phases

### Phase 1: Backend — Data Model & Storage

**Goal**: Establish the data foundation for plans.

| Step | File | Change | Depends On | FR |
|------|------|--------|------------|-----|
| 1.1 | `backend/src/models/chat.py` | Add `PLAN_CREATE = "plan_create"` to `ActionType` enum | — | FR-001 |
| 1.2 | `backend/src/models/plan.py` | Create `Plan` and `PlanStep` Pydantic models with validation | — | FR-003, FR-004 |
| 1.3 | `backend/src/migrations/035_chat_plans.sql` | Create `chat_plans` + `chat_plan_steps` tables with indices | — | FR-003 |
| 1.4 | `backend/src/services/chat_store.py` | Add plan CRUD: `save_plan()`, `get_plan()`, `update_plan()`, `update_plan_status()`, `update_plan_step_issue()` | 1.2, 1.3 | FR-003, FR-005, FR-009 |

### Phase 2: Backend — Plan Agent Mode & Thinking SSE

**Goal**: Plan agent with mode persistence, restricted tools, and real-time thinking events.

| Step | File | Change | Depends On | FR |
|------|------|--------|------------|-----|
| 2.1 | `backend/src/prompts/plan_instructions.py` | Create `build_plan_instructions(project_name, project_id, repo_owner, repo_name, available_statuses)` | — | FR-001, FR-004, FR-014 |
| 2.2 | `backend/src/services/agent_tools.py` | Add `save_plan` tool + `register_plan_tools()` returning restricted toolset | 1.4 | FR-005, FR-014 |
| 2.3 | `backend/src/services/chat_agent.py` | Add `run_plan()` and `run_plan_stream()` methods; check `is_plan_mode` in `run()`/`run_stream()` for auto-delegation | 2.1, 2.2 | FR-002, FR-006 |
| 2.4 | `backend/src/api/chat.py` | Add plan mode routes: `POST /messages/plan`, `POST /messages/plan/stream`, `GET /plans/{id}`, `PATCH /plans/{id}`, `POST /plans/{id}/approve`, `POST /plans/{id}/exit` | 2.3, 1.4 | FR-001, FR-008, FR-011, FR-015 |

### Phase 3: Backend — Plan → GitHub Issues

**Goal**: Convert approved plans into GitHub parent issue + sub-issues.

| Step | File | Change | Depends On | FR |
|------|------|--------|------------|-----|
| 3.1 | `backend/src/services/plan_issue_service.py` | Create `create_plan_issues(access_token, plan, owner, repo)`: parent issue with checklist body, sub-issues with dependency references, update plan record | 1.4 | FR-008, FR-009, FR-010, FR-018, FR-019 |
| 3.2 | `backend/src/api/chat.py` | Wire approve endpoint to `plan_issue_service` | 3.1, 2.4 | FR-008 |

### Phase 4: Frontend — Types, API & Thinking UX

**Goal**: Type definitions, SSE extension, and thinking indicator component.

| Step | File | Change | Depends On | FR |
|------|------|--------|------------|-----|
| 4.1 | `frontend/src/types/index.ts` | Add `PlanStatus`, `Plan`, `PlanStep`, `ThinkingEvent`, `ThinkingPhase`, `PlanCreateActionData` types; add `'plan_create'` to `ActionType` union | — | FR-001, FR-006 |
| 4.2 | `frontend/src/services/api.ts` | Extend `sendMessageStream` with `onThinking` callback; add `processThinkingFrame`; add `sendPlanMessageStream()`, `getPlan()`, `approvePlan()`, `exitPlanMode()` methods | 4.1 | FR-006, FR-008, FR-011 |
| 4.3 | `frontend/src/components/chat/ThinkingIndicator.tsx` | Create phase-aware indicator: 🔍 researching, 📋 planning, ✏️ refining; animated shimmer/pulse | 4.1 | FR-007 |

### Phase 5: Frontend — Plan UI

**Goal**: Rich plan preview card, state management, and chat integration.

| Step | File | Change | Depends On | FR |
|------|------|--------|------------|-----|
| 5.1 | `frontend/src/hooks/usePlan.ts` | Create hook: `activePlan`, `isPlanMode`, `thinkingPhase` state; `approve()`, `exit()` mutations via React Query | 4.1, 4.2 | FR-002, FR-008, FR-011 |
| 5.2 | `frontend/src/components/chat/PlanPreview.tsx` | Create plan card: header (project badge + status), steps with dependencies, action buttons ("Request Changes", "Approve & Create Issues"), completed state ("View Parent Issue" + "Exit Plan Mode"), issue link badges | 4.1, 5.1 | FR-013, FR-016, FR-017 |
| 5.3 | `frontend/src/components/chat/MessageBubble.tsx` | Render `PlanPreview` when `action_type === 'plan_create'` | 5.2 | FR-013 |
| 5.4 | `frontend/src/components/chat/ChatInterface.tsx` | Replace bounce dots with `ThinkingIndicator` when `thinkingPhase` is set; add plan mode banner above input: "Plan mode — {project_name}" | 4.3, 5.1 | FR-007, FR-012 |

## Dependency Graph

```text
Phase 1 (Data Model)
  1.1 ─┐
  1.2 ─┼─→ 1.4 ──→ Phase 2 (Agent Mode)
  1.3 ─┘              2.1 ─┐
                       2.2 ─┼─→ 2.3 ──→ 2.4
                             │
                             └─→ Phase 3 (Issue Service)
                                   3.1 ──→ 3.2

Phase 4 (Frontend Types/API)         Phase 5 (Frontend UI)
  4.1 ──→ 4.2                          5.1 ──→ 5.2 ──→ 5.3
       └──→ 4.3                                  └──→ 5.4
```

Phases 1–3 (backend) and Phases 4–5 (frontend) can proceed in parallel once Phase 1 data model shapes are agreed upon.

## Complexity Tracking

> No Constitution Check violations found. No complexity justifications required.
