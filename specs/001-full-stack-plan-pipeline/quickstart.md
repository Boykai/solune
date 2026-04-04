# Quickstart: Full-Stack Plan Pipeline Enhancement (v2 — Copilot SDK + MAF)

**Branch**: `001-full-stack-plan-pipeline` | **Date**: 2026-04-04

## Prerequisites

- Python 3.12+ with `uv` package manager
- Node.js 20+ with npm
- Git
- GitHub Copilot CLI (required for Copilot SDK sessions)
- Active GitHub OAuth token (for Copilot provider)

## Setup

### 1. Install Backend Dependencies

```bash
cd solune/backend
uv sync
```

This installs the updated `copilot-sdk>=1.0.17` and all other dependencies.

### 2. Run Database Migrations

Migrations run automatically on backend startup, but to verify:

```bash
cd solune/backend
uv run python -c "from src.services.database import run_migrations; import asyncio; asyncio.run(run_migrations())"
```

New migrations:
- `040_plan_versioning.sql` — Adds `version` column to `chat_plans`, creates `chat_plan_versions` table
- `041_plan_step_status.sql` — Adds `approval_status` column to `chat_plan_steps`

### 3. Install Frontend Dependencies

```bash
cd solune/frontend
npm install
```

### 4. Start Development Servers

```bash
# Terminal 1: Backend
cd solune/backend
uv run uvicorn src.main:app --reload --port 8000

# Terminal 2: Frontend
cd solune/frontend
npm run dev
```

## Feature Walkthrough

### Creating a Plan (Existing + Enhanced)

1. Navigate to a project in the Solune UI
2. Open the chat interface
3. Type `/plan <feature description>` (e.g., `/plan Add user authentication`)
4. The plan agent (now using SDK custom agent session) will:
   - Research the project context (SSE: `thinking` → `researching`)
   - Draft an implementation plan (SSE: `thinking` → `planning`)
   - Save the plan via `save_plan` tool (SSE: `tool_result` → `plan_create`)

### Plan Versioning (New)

Each `save_plan` call automatically:
1. **Pre-hook**: Snapshots the current plan version to `chat_plan_versions`
2. **Save**: Updates the plan with incremented version number
3. **Post-hook**: Emits a `plan_diff` SSE event

View version history:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/plans/{plan_id}/history
```

### Step Feedback (New)

Submit per-step feedback:
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"feedback_type": "comment", "content": "This step needs more detail on error handling"}' \
  http://localhost:8000/api/plans/{plan_id}/steps/{step_id}/feedback
```

### Step CRUD (New)

Add a step:
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Add rate limiting", "description": "Implement rate limiting middleware", "dependencies": []}' \
  http://localhost:8000/api/plans/{plan_id}/steps
```

Update a step:
```bash
curl -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Add rate limiting v2", "dependencies": ["<other_step_id>"]}' \
  http://localhost:8000/api/plans/{plan_id}/steps/{step_id}
```

Reorder steps:
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"step_order": [{"step_id": "...", "position": 0}, {"step_id": "...", "position": 1}]}' \
  http://localhost:8000/api/plans/{plan_id}/steps/reorder
```

### Dependency Graph (New)

The frontend renders a visual DAG of step dependencies in the `PlanDependencyGraph` component. Steps with unmet dependencies are visually distinct.

### SDK Streaming Events (Enhanced)

The SSE stream now includes additional events:
- `reasoning` — Real-time agent thought process
- `tool_start` — Tool execution beginning
- `stage_started/completed/failed` — Pipeline stage progress
- `plan_diff` — Version diff after save

## Verification

### Backend Tests

```bash
cd solune/backend

# Plan store versioning + step CRUD + DAG validation
uv run pytest -q tests/unit/test_plan_store.py tests/unit/test_api_chat.py

# SDK sessions, hooks, sub-agent events
uv run pytest tests/unit/test_plan_agent_provider.py tests/unit/test_pipeline_orchestrator.py

# Full coverage
uv run pytest tests/unit/ --cov=src --cov-fail-under=75
```

### Frontend Tests

```bash
cd solune/frontend

# Plan components and hooks
npm test -- --run PlanPreview.test.tsx usePlan.test.tsx PlanDependencyGraph.test.tsx

# Lint + type check
npm run lint -- --quiet && npx tsc --noEmit
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_PROVIDER` | `copilot` | AI backend (copilot or azure_openai) |
| `COPILOT_MODEL` | `gpt-4o` | Copilot model for agent sessions |
| `AGENT_COPILOT_TIMEOUT_SECONDS` | `120` | Timeout for Copilot agent calls |
| `AGENT_STREAMING_ENABLED` | `true` | Enable SSE streaming |
| `AGENT_SESSION_TTL_SECONDS` | `3600` | Agent session TTL |
| `AGENT_MAX_CONCURRENT_SESSIONS` | `100` | Max concurrent sessions |

### SDK Configuration

The Copilot SDK requires the Copilot CLI to be installed and available in `PATH`. For containerized deployments, configure via:

```python
# SubprocessConfig for local CLI
SubprocessConfig(cli_path="/usr/local/bin/copilot")

# ExternalServerConfig for remote server
ExternalServerConfig(url="http://copilot-server:8080")
```
