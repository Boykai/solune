# Implementation Plan: Full-Stack Plan Pipeline Enhancement (v2 — Copilot SDK + MAF)

**Branch**: `001-full-stack-plan-pipeline` | **Date**: 2026-04-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-full-stack-plan-pipeline/spec.md`

## Summary

Evolve the `/plan` pipeline into a versioned, step-editable planning surface powered by the Copilot Python SDK v1.0.17's native multi-agent, session hook, and streaming primitives. This replaces the current `is_plan_mode` flag-based switching in `chat_agent.py` with dedicated SDK custom agent sessions, adds automatic plan versioning via session hooks, step-level CRUD with DAG validation, and enhanced SSE streaming mapped from SDK events. The existing `agent-framework-github-copilot` wrapper is retained for general chat; plan mode routes through new SDK custom agent factory. Research findings (see [research.md](research.md)) confirm SDK custom agents, session hooks, and sub-agent events are the optimal approach for each capability.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript 6.0+ (frontend)
**Primary Dependencies**: FastAPI 0.135+, `copilot-sdk>=1.0.17` (upgrade from `github-copilot-sdk>=0.1.30`), `agent-framework-core>=1.0.0b1`, `agent-framework-github-copilot>=1.0.0b1`, React 19.2, `@tanstack/react-query` 5.96, `@dnd-kit` (existing)
**Storage**: SQLite via `aiosqlite>=0.22.0` (existing) — new migrations for versioning and step status
**Testing**: `pytest` (backend, coverage ≥75%), Vitest (frontend), Playwright (e2e)
**Target Platform**: Linux server (Docker), Web browser (SPA)
**Project Type**: Web application (backend + frontend)
**Performance Goals**: SSE streaming latency <200ms for plan events; plan save <500ms including version snapshot
**Constraints**: Backward-compatible with existing plan approval flow; no breaking changes to `/plans/{plan_id}` GET/PATCH/approve/exit endpoints
**Scale/Scope**: Existing user base; plan versions bounded per plan (≤100 versions typical); step count ≤50 per plan

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Specification-First** | ✅ PASS | `spec.md` created with P1-P4 prioritized user stories, Given-When-Then acceptance criteria, independent test criteria |
| **II. Template-Driven** | ✅ PASS | All artifacts follow `.specify/templates/` structure: plan.md, research.md, data-model.md, quickstart.md, contracts/ |
| **III. Agent-Orchestrated** | ✅ PASS | Pipeline uses single-responsibility agents (solune-plan, solune-specify, etc.) with clear inputs/outputs via SDK custom agent profiles |
| **IV. Test Optionality** | ✅ PASS | Tests included because: (a) spec P1 acceptance criteria require SDK hook verification, (b) DAG validation in P3 requires unit tests for cycle detection, (c) existing coverage threshold (≥75%) must be maintained |
| **V. Simplicity/DRY** | ✅ PASS | SDK session hooks replace manual versioning logic; SDK custom agents replace flag-based mode switching; existing `register_plan_tools()` reused without modification. See Complexity Tracking for justified complexity. |

**Post-Phase 1 Re-check**: ✅ PASS — Data model adds 2 tables (plan_versions, step status column) with clear purpose. API contracts extend existing endpoints additively. No unnecessary abstractions introduced.

## Project Structure

### Documentation (this feature)

```text
specs/001-full-stack-plan-pipeline/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: SDK research and decision records
├── data-model.md        # Phase 1: Entity definitions and migration schemas
├── quickstart.md        # Phase 1: Setup and usage guide
├── contracts/           # Phase 1: API and type contracts
│   ├── plan-pipeline-v2.openapi.yaml   # OpenAPI 3.1 contract
│   └── plan-pipeline-v2.types.ts       # TypeScript type extensions
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   └── chat.py                    # MODIFY — step CRUD, feedback, history endpoints
│   │   ├── models/
│   │   │   └── plan.py                    # MODIFY — PlanVersion model, version field, StepApprovalStatus
│   │   ├── services/
│   │   │   ├── agent_provider.py          # MODIFY — route plan mode to SDK custom agent sessions
│   │   │   ├── plan_agent_provider.py     # NEW — custom agent profiles, session hooks, SDK factory
│   │   │   ├── pipeline_orchestrator.py   # NEW — multi-stage pipeline via sub-agent events
│   │   │   ├── chat_agent.py              # MODIFY — SDK event stream mapping, hook wiring
│   │   │   ├── chat_store.py              # MODIFY — versioning, step CRUD, DAG validation
│   │   │   ├── agent_tools.py             # MODIFY — @define_tool for step CRUD
│   │   │   └── completion_providers.py    # MODIFY — update for SDK v1.0.17 compatibility
│   │   ├── prompts/
│   │   │   └── plan_instructions.py       # MODIFY — version-aware refinement, elicitation guidance
│   │   └── migrations/
│   │       ├── 040_plan_versioning.sql    # NEW — version column, plan_versions table
│   │       └── 041_plan_step_status.sql   # NEW — step approval_status column
│   ├── tests/
│   │   └── unit/
│   │       ├── test_plan_store.py         # MODIFY — versioning, step CRUD, DAG tests
│   │       ├── test_api_chat.py           # MODIFY — new endpoint tests
│   │       ├── test_plan_agent_provider.py # NEW — SDK session, hook tests
│   │       └── test_pipeline_orchestrator.py # NEW — orchestrator tests
│   └── pyproject.toml                     # MODIFY — upgrade copilot-sdk pin
│
└── frontend/
    └── src/
        ├── components/
        │   └── chat/
        │       ├── PlanPreview.tsx         # MODIFY — step approval, inline editing
        │       └── PlanDependencyGraph.tsx # NEW — DAG visualization
        ├── hooks/
        │   └── usePlan.ts                 # MODIFY — versioning, step CRUD, feedback mutations
        ├── services/
        │   └── api.ts                     # MODIFY — new API calls for step CRUD, history, feedback
        └── types/
            └── index.ts                   # MODIFY — v2 types (version, StepApprovalStatus, new events)
```

**Structure Decision**: Web application structure (Option 2). The repository already uses `solune/backend/` and `solune/frontend/` layout. All changes follow existing directory conventions. New files are placed in existing service/model directories. No new top-level directories needed.

## Implementation Phases

### Phase 0 — Copilot SDK Agent Orchestration Layer

**Step 0A: Upgrade SDK + define plan agent profile** (no dependencies)
- Pin `copilot-sdk>=1.0.17` in `pyproject.toml` (replace `github-copilot-sdk>=0.1.30,<1`)
- Create `plan_agent_provider.py`:
  - `PLAN_AGENT_PROFILE`: custom_agents dict with tool whitelist (`get_project_context`, `get_pipeline_list`, `save_plan`) and `PLAN_SYSTEM_INSTRUCTIONS` prompt
  - `SPECKIT_AGENT_PROFILES`: profiles for each pipeline stage agent
  - `create_plan_session()`: factory wrapping `CopilotClient.create_session()`
- Update `create_agent()` in `agent_provider.py` to route plan mode to SDK custom agent sessions

**Step 0B: Session hooks for plan versioning** (depends on 0A)
- Register `on_pre_tool_use` hook: when `toolName == "save_plan"`, call `snapshot_plan_version()` to save current plan state
- Register `on_post_tool_use` hook: after `save_plan` completes, emit `plan_diff` delta as SSE event
- Hook registration in `plan_agent_provider.py`

**Step 0C: Sub-agent pipeline orchestrator** (depends on 0A)
- Create `pipeline_orchestrator.py`:
  - Sequence speckit agents via SDK sessions
  - Listen for `subagent.completed/failed` to drive stage transitions
  - Support parallel groups via `asyncio.gather()`
  - Emit `stage_started/completed/failed` SSE events
- Wire into `chat_agent.py` for pipeline-mode execution

**Step 0D: Streaming event upgrade** (depends on 0A, parallel with 0B–0C)
- Map SDK events to enhanced SSE:
  - `assistant.reasoning_delta` → `reasoning` event
  - `tool.execution_start` → `tool_start` event
  - `assistant.intent` → enhanced `thinking` event
  - `subagent.*` → `stage_*` events
- Preserve existing event shape for backward compatibility

### Phase 1 — Iterative Refinement Loop

**Step 1: Plan versioning schema** (no dependencies, parallel with Phase 0)
- Migration `040_plan_versioning.sql`: add `version` column to `chat_plans`, create `chat_plan_versions` table
- Update `Plan` model in `plan.py` with `version: int` field and `PlanVersion` model
- Add `snapshot_plan_version()` and `get_plan_versions()` to `chat_store.py`
- The `on_pre_tool_use` hook from Step 0B calls `snapshot_plan_version()` automatically

**Step 2: Step-level feedback via elicitation** (depends on 1 + 0A)
- `POST /plans/{plan_id}/steps/{step_id}/feedback` endpoint in `chat.py`
- Use SDK `on_user_input_request` handler for agent ↔ user clarification dialogs
- `StepFeedbackRequest`/`StepFeedbackResponse` models

**Step 3: Guided refinement prompt** (depends on 1)
- Enhance `PLAN_SYSTEM_INSTRUCTIONS` in `plan_instructions.py` with:
  - Version-history awareness (current version number, change summary)
  - Per-step comment injection (feedback content prefixed to agent context)
  - Elicitation usage instructions

**Step 4: Refinement sidebar** (no backend dependencies, parallel with 1–3)
- "Request Changes" button → inline per-step comment input in `PlanPreview.tsx`
- Handle elicitation SSE events from agent
- Update `usePlan.ts` with feedback mutation

**Step 5: Diff highlight** (depends on 1 + 4)
- `GET /plans/{plan_id}/history` endpoint returning version snapshots
- Frontend client-side diff rendering between version snapshots
- Version selector in plan UI

### Phase 2 — Step CRUD + Dependency Graph

**Step 6: Step mutation APIs** (depends on 1)
- `POST /plans/{plan_id}/steps` — add step
- `PATCH /plans/{plan_id}/steps/{step_id}` — update step
- `DELETE /plans/{plan_id}/steps/{step_id}` — delete step (cascade removes from other steps' dependencies)
- Register matching `@define_tool` functions in `agent_tools.py` (`add_step`, `edit_step`, `delete_step`)

**Step 7: DAG validation** (depends on 6)
- Implement Kahn's algorithm for topological sort in `chat_store.py`
- Validate on every step add/update/reorder — reject circular dependencies with 400 error
- Migration `041_plan_step_status.sql`: add `approval_status` column

**Step 8: Inline editing** (depends on 6)
- Click-to-edit step title/description in `PlanPreview.tsx`
- Optimistic updates via `usePlan.ts` mutations

**Step 9: Drag-and-drop reorder** (depends on 6)
- `POST /plans/{plan_id}/steps/reorder` endpoint
- Frontend `@dnd-kit` integration for step reordering (library already in deps)

**Step 10: Dependency graph** (depends on 7)
- New `PlanDependencyGraph.tsx` component rendering DAG with step nodes and dependency edges
- Visual distinction for approval status (pending/approved/rejected)

**Step 11: Per-step approval** (depends on 7)
- `POST /plans/{plan_id}/steps/{step_id}/approve` endpoint
- Individual step approve/reject UI buttons in `PlanPreview.tsx`

### Phase 3 — Thinking Polish + Export + Board Sync

**Step 12: Enhanced thinking indicator** (mostly done by 0D)
- Update `ThinkingIndicator.tsx` to handle new event types (`reasoning`, `tool_start`, `stage_*`)
- Progressive disclosure: show stage progress for pipeline execution

**Step 13: Reasoning stream** (depends on 0D)
- Display `reasoning` events in collapsible "Agent Thinking" panel
- Pipeline stage progress bar driven by `stage_*` events

**Step 14: Plan export** (depends on 1)
- `GET /plans/{plan_id}/export?format=markdown` — export plan as markdown
- `GET /plans/{plan_id}/export?format=github_issues` — preview issue format

**Step 15: Board sync** (depends on 6)
- After plan approval, sync step status changes to project board columns
- Bidirectional: board column changes reflect in plan step status

**Step 16: Batch operations** (depends on 6 + 11)
- Select multiple steps → bulk approve/reject/delete
- Bulk dependency assignment

### Phase 4 — Copilot CLI Plugin + ACP Interop (Stretch)

**Step 17: CLI plugin packaging** (depends on Phases 0–2)
- Create `solune/cli-plugin/` directory with:
  - `plugin.json` — plugin manifest
  - `agents/solune-plan.agent.md` — plan agent definition
  - `skills/plan-crud/SKILL.md` — step CRUD skill definition
  - `hooks/hooks.json` — hook registration
  - `.mcp.json` — MCP server configuration
- Enables `copilot /plugin install` for CLI-native plan mode

**Step 18: ACP server endpoint** (depends on 17)
- Optional `--acp` mode exposing plan pipeline via Agent Client Protocol
- Configuration via `ExternalServerConfig(url=...)` for containerized deployments

## Dependency Graph

```
Phase 0:  [0A] ──→ [0B] ──→ (hooks wired)
            │ ──→ [0C] ──→ (orchestrator ready)
            │ ──→ [0D] ──→ (streaming enhanced)

Phase 1:  [1] ──→ [2] (needs 1 + 0A)
            │ ──→ [3] (needs 1)
            │     [4] (parallel, no backend deps)
            └──→ [5] (needs 1 + 4)

Phase 2:  [6] (needs 1) ──→ [7] ──→ [10]
            │                │ ──→ [11]
            │ ──→ [8]
            │ ──→ [9]

Phase 3:  [12] (needs 0D)
          [13] (needs 0D)
          [14] (needs 1)
          [15] (needs 6)
          [16] (needs 6 + 11)

Phase 4:  [17] (needs Phases 0–2) ──→ [18]
```

## Agents Pipeline (SDK Mapping)

| # | Group | Agent | SDK Integration |
|---|-------|-------|-----------------|
| 1 | G1 (series) | speckit.plan | CopilotClient custom agent: `solune-plan` |
| 2 | G1 (series) | speckit.specify | CopilotClient custom agent: `solune-specify` |
| 3 | G1 (series) | speckit.tasks | CopilotClient custom agent: `solune-tasks` |
| 4 | G1 (series) | speckit.analyze | CopilotClient custom agent: `solune-analyze` (read-only tools) |
| 5 | G1 (series) | speckit.implement | CopilotClient custom agent: `solune-implement` (full tools) |
| 6 | G2 (parallel) | quality-assurance | CopilotClient session with QA prompt |
| 7 | G2 (parallel) | tester | CopilotClient session with test prompt |
| 8 | G2 (parallel) | copilot-review | SDK permission: read-only, no write tools |
| 9 | G3 (parallel) | judge | CopilotClient session, compare outputs |
| 10 | G3 (parallel) | linter | `@define_tool` wrapping lint scripts |
| 11 | G4 (series) | devops | `@define_tool` wrapping deploy scripts |

## Files Changed

| Area | File | Change Type | Description |
|------|------|-------------|-------------|
| Backend SDK | `pyproject.toml` | MODIFY | Upgrade `copilot-sdk>=1.0.17` |
| Backend agent factory | `agent_provider.py` | MODIFY | Route plan mode to SDK custom agent sessions |
| Backend plan agent | `plan_agent_provider.py` | NEW | Custom agent profiles, session hooks, SDK factory |
| Backend orchestrator | `pipeline_orchestrator.py` | NEW | Multi-stage pipeline via sub-agent events |
| Backend models | `plan.py` | MODIFY | `PlanVersion`, `version` field, `StepApprovalStatus` |
| Backend store | `chat_store.py` | MODIFY | Versioning, step CRUD, DAG validation |
| Backend API | `chat.py` | MODIFY | Step CRUD, feedback, history endpoints |
| Backend prompts | `plan_instructions.py` | MODIFY | Version-aware refinement, elicitation guidance |
| Backend agent | `chat_agent.py` | MODIFY | SDK event stream mapping, hook wiring |
| Backend tools | `agent_tools.py` | MODIFY | `@define_tool` for step CRUD |
| Backend providers | `completion_providers.py` | MODIFY | SDK v1.0.17 compatibility |
| Migration | `040_plan_versioning.sql` | NEW | Version column, plan_versions table |
| Migration | `041_plan_step_status.sql` | NEW | Step approval_status column |
| Frontend | `PlanPreview.tsx` | MODIFY | Step approval, inline editing, feedback |
| Frontend | `PlanDependencyGraph.tsx` | NEW | DAG visualization component |
| Frontend | `ThinkingIndicator.tsx` | MODIFY | Handle v2 SSE event types |
| Frontend | `usePlan.ts` | MODIFY | Versioning, step CRUD, feedback mutations |
| Frontend | `api.ts` | MODIFY | New API calls for step CRUD, history, feedback |
| Frontend | `types/index.ts` | MODIFY | V2 types (version, approval, events) |
| CLI plugin | `solune/cli-plugin/` | NEW | Phase 4 stretch — CLI plugin packaging |

## Verification

```bash
# Backend — versioning, step CRUD, DAG
cd solune/backend
uv run pytest -q tests/unit/test_plan_store.py tests/unit/test_api_chat.py

# Backend — SDK sessions, hooks, sub-agent events
uv run pytest tests/unit/test_plan_agent_provider.py tests/unit/test_pipeline_orchestrator.py

# Backend — full coverage
uv run pytest tests/unit/ --cov=src --cov-fail-under=75

# Frontend — plan components and hooks
cd solune/frontend
npm test -- --run PlanPreview.test.tsx usePlan.test.tsx PlanDependencyGraph.test.tsx

# Frontend — lint + type check
npm run lint -- --quiet && npx tsc --noEmit
```

## Decisions

| Decision | Rationale |
|----------|-----------|
| Custom agents over mode-switching | Replace `is_plan_mode` flag with SDK custom agent profiles — cleaner tool isolation, CLI interop |
| Session hooks for versioning | `on_pre_tool_use` intercepts before `save_plan` — automatic snapshot without modifying the tool |
| Elicitation for feedback | SDK's `ask_user` + `session.ui.elicitation()` provide structured dialogs, richer than free-text |
| Sub-agent events for pipeline | SDK's `subagent.*` events map directly to pipeline stage tracking |
| CLI plugin as Phase 4 | Stretch goal — packages plan agents for `copilot /plugin install` |
| `copilot-sdk>=1.0.17` | Latest public preview; Python 3.11+ required (project uses 3.12+) |
| Kahn's algorithm for DAG | O(V+E) cycle detection, standard for topological sort validation |
| Additive API changes only | New endpoints alongside existing; no breaking changes to plan approval flow |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New `plan_agent_provider.py` module | Separates SDK custom agent factory from general agent creation | Adding to `agent_provider.py` would mix general and plan-specific concerns; constitution principle III requires single-responsibility |
| New `pipeline_orchestrator.py` module | SDK sub-agent event handling requires dedicated orchestration logic | Extending `pipelines/service.py` would mix configuration (presets) with runtime orchestration; separation enables independent testing |
| Two new database migrations | Plan versioning (040) and step status (041) serve distinct purposes | Single migration would be harder to roll back independently; standard practice for additive schema changes |
