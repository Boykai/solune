# Implementation Plan: Codebase Modularity Review

**Branch**: `copilot/codebase-modularity-review-another-one` | **Date**: 2026-04-12 | **Spec**: [#1471](https://github.com/Boykai/solune/issues/1471)
**Input**: Parent issue #1471 — Codebase Modularity Review (Overall 6.5/10)

## Summary

Decompose 6 monolithic hotspots across the Solune backend and frontend into domain-scoped modules to improve maintainability, testability, and code-review ergonomics. The refactoring preserves all existing behavior (zero functional changes) while restructuring files, extracting classes, and introducing barrel re-exports for backward-compatible imports.

**Backend (3 targets):** Split `api/chat.py` (2930 lines → 5 modules), extract `ProposalOrchestrator` service (346 lines from `confirm_proposal()`), and split `api/webhooks.py` (1033 lines → 4 modules). Additionally, consolidate module-level global state into a `ChatStateManager` class and extract bootstrap logic from `main.py` into `services/bootstrap.py`.

**Frontend (2 targets):** Split `services/api.ts` (1876 lines → 15+ domain files) and `types/index.ts` (1525 lines → 13+ domain files), with barrel `index.ts` re-exports ensuring all 265+ existing import sites continue to work unchanged.

| Phase | Scope | Key Output |
|-------|-------|------------|
| 1 | Backend: ChatStateManager + bootstrap.py extraction | `services/chat_state_manager.py`, `services/bootstrap.py` |
| 2 | Backend: ProposalOrchestrator extraction | `services/proposal_orchestrator.py` |
| 3 | Backend: Split api/chat.py into package | `api/chat/__init__.py`, `conversations.py`, `messages.py`, `proposals.py`, `plans.py`, `streaming.py` |
| 4 | Backend: Split api/webhooks.py into package | `api/webhooks/__init__.py`, `handlers.py`, `pull_requests.py`, `ci.py` |
| 5 | Frontend: Split services/api.ts | `services/api/client.ts`, `services/api/auth.ts`, `services/api/chat.ts`, ... + barrel `index.ts` |
| 6 | Frontend: Split types/index.ts | `types/common.ts`, `types/chat.ts`, `types/board.ts`, ... + barrel `index.ts` |
| 7 | Verification | Full test suite pass, import validation, diagram regeneration |

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.x (frontend)
**Primary Dependencies**: FastAPI + Pydantic (backend), React 18 + TanStack Query + Zod (frontend)
**Storage**: aiosqlite (backend persistence for chat state, proposals, settings)
**Testing**: pytest (backend), Vitest (frontend) — statements ≥50%, branches ≥44%
**Target Platform**: Web application (Linux server backend, SPA frontend)
**Project Type**: Web application (monorepo: `solune/backend/` + `solune/frontend/`)
**Performance Goals**: Zero regression — refactoring is structural only, no functional changes
**Constraints**: All 265+ existing import paths must continue to work (barrel re-exports); no new dependencies; existing test suites must pass without modification to test assertions
**Scale/Scope**: ~8,400 lines refactored across 6 files; 265+ consumer files updated via barrel re-exports; 0 new features

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Feature fully specified in parent issue #1471 with detailed audit, 6 ranked targets, and impact assessment |
| II. Template-Driven Workflow | ✅ PASS | This plan follows `plan-template.md`; all supplementary artifacts generated per workflow |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan agent produces plan; implement agent will execute phased tasks with clear handoffs |
| IV. Test Optionality | ✅ PASS | Existing tests must pass unchanged; new unit tests added for extracted classes (ChatStateManager, ProposalOrchestrator); no TDD mandate — tests validate extraction correctness |
| V. Simplicity and DRY | ✅ PASS | Refactoring reduces complexity (smaller files, single-responsibility modules); no new abstractions beyond what the issue specifies; barrel re-exports avoid import churn |

**Gate Result**: PASS — no violations. Proceed to Phase 0.

### Post-Design Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | All design artifacts (data-model, contracts, research) trace to issue #1471 targets |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates |
| III. Agent-Orchestrated Execution | ✅ PASS | 7 sequential phases with clear inputs/outputs per phase |
| IV. Test Optionality | ✅ PASS | Extracted classes get unit tests; existing tests require only import-path patches |
| V. Simplicity and DRY | ✅ PASS | Each module has a single responsibility; barrel files eliminate duplication; no premature abstraction |

**Post-Design Gate Result**: PASS — proceed to task generation.

## Project Structure

### Documentation (this feature)

```text
specs/001-codebase-modularity-review/
├── plan.md              # This file
├── research.md          # Phase 0 output — best practices for Python/TS module splitting
├── data-model.md        # Phase 1 output — entity relationships for extracted classes
├── quickstart.md        # Phase 1 output — developer guide for the new module layout
├── contracts/           # Phase 1 output — module interface contracts
│   ├── chat-state-manager-api.yaml
│   ├── proposal-orchestrator-api.yaml
│   ├── chat-package-api.yaml
│   ├── webhooks-package-api.yaml
│   ├── frontend-api-client-api.yaml
│   └── frontend-types-api.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── api/
│   │   ├── chat/                    # NEW: Package replacing chat.py
│   │   │   ├── __init__.py          # Router aggregation + re-exports
│   │   │   ├── conversations.py     # Conversation CRUD endpoints
│   │   │   ├── messages.py          # Message endpoints + streaming
│   │   │   ├── proposals.py         # Proposal confirm/cancel endpoints
│   │   │   ├── plans.py             # Plan CRUD + steps + approval
│   │   │   └── streaming.py         # SSE streaming helpers
│   │   ├── webhooks/                # NEW: Package replacing webhooks.py
│   │   │   ├── __init__.py          # Router aggregation
│   │   │   ├── handlers.py          # Main dispatcher + security
│   │   │   ├── pull_requests.py     # PR event handlers
│   │   │   └── ci.py                # Check run/suite handlers
│   │   └── ...                      # Other API modules unchanged
│   ├── services/
│   │   ├── chat_state_manager.py    # NEW: Extracted from chat.py globals
│   │   ├── proposal_orchestrator.py # NEW: Extracted from confirm_proposal()
│   │   ├── bootstrap.py             # NEW: Extracted from main.py lifespan
│   │   └── ...                      # Other services unchanged
│   ├── main.py                      # MODIFIED: Slim lifespan calling bootstrap
│   └── dependencies.py              # MODIFIED: Add ChatStateManager + orchestrator DI
└── tests/
    ├── unit/
    │   ├── test_chat_state_manager.py     # NEW
    │   ├── test_proposal_orchestrator.py  # NEW
    │   └── test_main.py                   # MODIFIED: Patch paths updated
    └── integration/                       # MODIFIED: Patch paths updated

solune/frontend/
├── src/
│   ├── services/
│   │   ├── api/                     # NEW: Package replacing api.ts
│   │   │   ├── index.ts             # Barrel re-export (backward compat)
│   │   │   ├── client.ts            # Base request(), ApiError, CSRF, auth listener
│   │   │   ├── auth.ts              # authApi namespace
│   │   │   ├── projects.ts          # projectsApi namespace
│   │   │   ├── tasks.ts             # tasksApi namespace
│   │   │   ├── chat.ts              # conversationApi + chatApi namespaces
│   │   │   ├── board.ts             # boardApi namespace
│   │   │   ├── settings.ts          # settingsApi namespace
│   │   │   ├── workflow.ts          # workflowApi + metadataApi namespaces
│   │   │   ├── signal.ts            # signalApi namespace
│   │   │   ├── mcp.ts              # mcpApi namespace
│   │   │   ├── cleanup.ts           # cleanupApi namespace
│   │   │   ├── chores.ts            # choresApi namespace
│   │   │   ├── agents.ts            # agentsApi namespace
│   │   │   ├── pipelines.ts         # pipelinesApi + modelsApi namespaces
│   │   │   ├── tools.ts             # toolsApi + agentToolsApi namespaces
│   │   │   ├── apps.ts              # appsApi namespace
│   │   │   └── activity.ts          # activityApi namespace
│   │   └── schemas/                 # Unchanged
│   ├── types/                       # REFACTORED: Domain-scoped files
│   │   ├── index.ts                 # Barrel re-export (backward compat)
│   │   ├── common.ts               # Enums + shared primitives (ProjectType, SenderType, etc.)
│   │   ├── auth.ts                  # User, AuthResponse
│   │   ├── projects.ts              # Project, StatusColumn, ProjectListResponse
│   │   ├── tasks.ts                 # Task, TaskCreateRequest, TaskListResponse
│   │   ├── chat.ts                  # ChatMessage, ActionData, Conversation, Mention, etc.
│   │   ├── proposals.ts             # AITaskProposal, ProposalConfirmRequest, IssueRecommendation
│   │   ├── plans.ts                 # Plan, PlanStep, PlanStatus, approval types
│   │   ├── board.ts                 # BoardItem, BoardColumn, BoardProject, etc.
│   │   ├── settings.ts              # EffectiveUserSettings, GlobalSettings, etc.
│   │   ├── workflow.ts              # WorkflowResult, WorkflowConfiguration, etc.
│   │   ├── pipeline.ts              # PipelineConfig, PipelineStage, PipelineAgentNode, etc.
│   │   ├── agents.ts                # AgentSource, AgentAssignment, AgentPreset, etc.
│   │   ├── signal.ts                # SignalConnection, SignalPreferences, etc.
│   │   ├── mcp.ts                   # McpConfiguration, McpToolConfig, etc.
│   │   ├── cleanup.ts               # BranchInfo, CleanupPreflightResponse, etc.
│   │   ├── chores.ts                # Chore, ChoreTemplate, ChoreStatus, etc.
│   │   ├── activity.ts              # ActivityEvent, ActivityStats
│   │   ├── ui.ts                    # NavRoute, SidebarState, Notification, etc.
│   │   ├── apps.ts                  # Unchanged (already separate)
│   │   └── app-template.ts          # Unchanged (already separate)
│   └── ...                          # Components, hooks, pages unchanged
└── ...
```

**Structure Decision**: Web application (Option 2). Backend and frontend are in `solune/backend/` and `solune/frontend/` respectively. All refactoring targets are within these two directories. The monorepo structure under `solune/` is preserved.

## Complexity Tracking

> No Constitution Check violations — this section is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
