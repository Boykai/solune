# Quickstart: Multi-Phase App Creation with Auto-Merge Pipeline Orchestration

**Branch**: `copilot/create-implementation-plan-for-app` | **Date**: 2026-04-06

## Prerequisites

- Python 3.11+ with `uv` package manager
- Node.js 18+ with npm
- SQLite (bundled with Python)
- GitHub Copilot access (for speckit.plan agent)
- Valid GitHub token with repo/project permissions

## Setup

```bash
# Backend
cd solune/backend
uv sync

# Frontend
cd solune/frontend
npm install
```

## Run Backend Tests

```bash
cd solune/backend

# Full unit test suite
PATH=$HOME/.local/bin:$PATH uv run pytest tests/unit/ -x --cov=src --cov-report=term-missing

# Specific test files for this feature (once implemented)
PATH=$HOME/.local/bin:$PATH uv run pytest tests/unit/test_plan_parser.py -v
PATH=$HOME/.local/bin:$PATH uv run pytest tests/unit/test_app_plan_orchestrator.py -v

# Linting and type checking
PATH=$HOME/.local/bin:$PATH uv run ruff check src tests
PATH=$HOME/.local/bin:$PATH uv run ruff format --check src tests
PATH=$HOME/.local/bin:$PATH uv run pyright src
```

## Run Frontend Tests

```bash
cd solune/frontend

# Full test suite with coverage
npm run test:coverage

# Lint and type check
npm run lint
npm run type-check
npm run build
```

## Key Files to Implement

### Phase 1: Backend Service Layer

| File | Description |
|------|-------------|
| `backend/src/services/app_plan_orchestrator.py` | New — orchestrates full plan-based app creation flow |
| `backend/src/services/plan_parser.py` | New — parses plan.md into PlanPhase objects |
| `backend/src/services/workflow_orchestrator/models.py` | Extend — add `prerequisite_issues` to PipelineState |
| `backend/src/services/pipeline_state_store.py` | Extend — serialize/deserialize `prerequisite_issues` in metadata JSON |

### Phase 2: Pipeline Execution Extensions

| File | Description |
|------|-------------|
| `backend/src/api/pipelines.py` | Extend — add `auto_merge` and `prerequisite_issues` params to `execute_pipeline_launch()` |
| `backend/src/services/copilot_polling/pipeline.py` | Extend — prerequisite check in `_dequeue_next_pipeline()` |
| `backend/src/services/copilot_polling/auto_merge.py` | Verify — confirm dequeue trigger after merge (already exists) |

### Phase 3: API + Frontend

| File | Description |
|------|-------------|
| `backend/src/api/apps.py` | Extend — `POST /apps/create-with-plan`, `GET /apps/{app_name}/plan-status` |
| `backend/src/migrations/042_app_plan_orchestrations.sql` | New — orchestration tracking table |
| `frontend/src/components/apps/CreateAppDialog.tsx` | Extend — post-submit progress view |
| `frontend/src/types/apps.ts` | Extend — new TypeScript interfaces |
| `frontend/src/hooks/useApps.ts` | Extend — new API hooks |

### Phase 4: Tests

| File | Description |
|------|-------------|
| `backend/tests/unit/test_plan_parser.py` | New — parser tests |
| `backend/tests/unit/test_app_plan_orchestrator.py` | New — orchestrator tests |
| `backend/tests/unit/test_copilot_polling.py` | Extend — prerequisite dequeue tests |

## Architecture Flow

```
User submits "Create App with Plan"
        │
        ▼
POST /apps/create-with-plan (returns 202 immediately)
        │
        ▼ (BackgroundTask)
AppPlanOrchestrator.orchestrate_app_creation()
        │
        ├──→ chat_agent_svc.run_plan() → structured plan summary
        │
        ├──→ Create temporary planning issue
        │
        ├──→ assign_copilot_to_issue(custom_agent="speckit.plan")
        │
        ├──→ Poll for "Done!" marker (check_agent_completion_comment)
        │
        ├──→ Fetch plan.md from PR branch (get_file_content_from_ref)
        │
        ├──→ Parse plan.md → PlanPhase objects (plan_parser.py)
        │
        ├──→ Create GitHub Issues per phase (with tracking tables)
        │
        ├──→ Group phases into waves, launch with execute_pipeline_launch()
        │    ├── Wave 1: auto_merge=True, no prerequisites
        │    └── Wave 2+: auto_merge=True, prerequisite_issues=[Wave N-1 issues]
        │
        └──→ Status = "active" → frontend shows issue links
```

## Existing Patterns to Reuse

| Pattern | Location | Usage |
|---------|----------|-------|
| `assign_copilot_to_issue()` | `github_projects/copilot.py:252` | Assign speckit.plan agent |
| `check_agent_completion_comment()` | `github_projects/copilot.py:75` | Poll for agent completion |
| `get_file_content_from_ref()` | `github_projects/repository.py:292` | Fetch plan.md from PR branch |
| `append_tracking_to_body()` | `agent_tracking.py:241` | Add tracking table to phase issues |
| `execute_pipeline_launch()` | `api/pipelines.py:274` | Launch pipeline per phase |
| `_dequeue_next_pipeline()` | `copilot_polling/pipeline.py:49` | Dequeue with prerequisite check |
| `_attempt_auto_merge()` | `copilot_polling/auto_merge.py:31` | Auto-merge after pipeline completion |
| `broadcast_to_project()` | `websocket.py` | WebSocket progress updates |
