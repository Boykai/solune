# Quickstart: Human Agent — Delay Until Auto-Merge

**Feature**: 001-human-agent-delay-until-auto-merge | **Date**: 2026-04-04

## Prerequisites

- Python 3.11+ with `uv` package manager
- Node.js 18+ with npm
- Docker and docker-compose (for full-stack development)
- Access to the Solune repository

## Development Setup

```bash
# Clone and navigate to repo
cd solune

# Backend setup
cd solune/backend
uv sync
uv run pytest --co -q  # Verify test collection works

# Frontend setup
cd ../frontend
npm install
npm run build  # Verify build works
```

## Where to Start

### Phase 1: Backend Changes (start here)

#### Step 1.1 — Config flow (config.py)

**File**: `solune/backend/src/services/workflow_orchestrator/config.py`
**Lines**: 367-378 (group-aware path) and 393-405 (legacy fallback)

**What to change**: Merge full `node.config` dict into `AgentAssignment.config` so `delay_seconds` flows through.

```python
# BEFORE (line 371-376):
config={
    "model_id": node.model_id,
    "model_name": node.model_name,
}
if node.model_id
else None,

# AFTER:
config={
    **node.config,
    "model_id": node.model_id,
    "model_name": node.model_name,
}
if node.model_id or node.config
else None,
```

Apply the same change to both the group-aware path (line 371) and the legacy fallback (line 397).

#### Step 1.2 — PipelineState field (models.py)

**File**: `solune/backend/src/services/workflow_orchestrator/models.py`
**Line**: After line 177 (`auto_merge: bool = False`)

**What to add**:
```python
# Per-agent config dict for runtime access (e.g., human delay_seconds)
agent_configs: dict[str, dict] = field(default_factory=dict)
```

#### Step 1.3 — Populate agent_configs at launch (pipelines.py)

**File**: `solune/backend/src/api/pipelines.py`
**Lines**: ~467-489 (PipelineState construction)

**What to add**: When constructing `PipelineState`, populate `agent_configs` from the workflow configuration's `AgentAssignment.config` dicts.

#### Step 1.4 — Delay-then-merge execution (pipeline.py)

**File**: `solune/backend/src/services/copilot_polling/pipeline.py`
**Lines**: 1951-2039 (the "Human Agent Skip" block)

**What to change**: Replace the skip-only logic with delay-aware logic:

```python
if next_agent == "human":
    delay_seconds = None
    agent_config = pipeline.agent_configs.get("human", {})
    if isinstance(agent_config, dict):
        delay_seconds = agent_config.get("delay_seconds")

    if delay_seconds is not None:
        # Validate
        if not isinstance(delay_seconds, int) or not (1 <= delay_seconds <= 86400):
            logger.warning("Invalid delay_seconds=%r for human agent, ignoring", delay_seconds)
            delay_seconds = None

    if delay_seconds is not None:
        # NEW: Delay-then-merge path
        # 1. Comment on sub-issue with delay info
        # 2. Loop asyncio.sleep(15) checking sub-issue status
        # 3. On expiry or early cancel: _attempt_auto_merge()
        # 4. Close sub-issue, mark completed, advance
        ...
    else:
        # EXISTING: Skip-if-auto-merge or manual-wait
        remaining_agents = pipeline.agents[pipeline.current_agent_index:]
        is_last_step = len(remaining_agents) == 1
        if is_last_step:
            # ... existing skip logic ...
```

#### Step 1.5 — Validation

Validation is part of Step 1.4 — the guard check before entering the delay loop.

### Phase 2: Frontend Changes (can start after Step 1.1)

#### Step 2.1 — Delay toggle on AgentNode

**File**: `solune/frontend/src/components/pipeline/AgentNode.tsx`

**What to add**: When `agentNode.agent_slug === 'human'`, render below the model selector:
- Toggle: "Delay until auto-merge" (off by default)
- When on: `<input type="number" min={1} max={86400}>` for seconds
- Updates: `onModelSelect` or dedicated callback that sets `config.delay_seconds`

#### Step 2.2 — Verify config merge

**File**: `solune/frontend/src/hooks/usePipelineBoardMutations.ts`
**Line**: 193

The spread `{ ...a, ...updates }` already merges partial updates correctly. Verify that updating `config.delay_seconds` doesn't clobber `config.model_id`.

#### Step 2.3 — Display badge

**File**: `solune/frontend/src/components/pipeline/AgentNode.tsx`

Show badge based on config:
- `delay_seconds` set: `⏱️ Auto-merge: {formatDuration(delay_seconds)}`
- Not set: `Manual review`

### Phase 3: Polish

#### Step 3.1 — Tracking table

**File**: `solune/backend/src/services/agent_tracking.py`

Render delayed human row as `⏱️ Delay ({formatted_duration})` while waiting.

#### Step 3.2 — Sub-issue body

**File**: `solune/backend/src/services/workflow_orchestrator/orchestrator.py` or `agents.py`

Append to human sub-issue body: `"⏱️ Auto-merge in {duration}. Close early to skip."`

## Running Tests

```bash
# Backend unit tests
cd solune/backend
uv run pytest tests/unit/test_human_delay.py -v

# Backend full suite (verify no regressions)
uv run pytest --cov=src --cov-report=json \
  --ignore=tests/property --ignore=tests/fuzz \
  --ignore=tests/chaos --ignore=tests/concurrency

# Frontend tests
cd ../frontend
npm run test
npm run test:coverage
```

## Key Files Reference

| File | Purpose | Phase |
|------|---------|-------|
| `solune/backend/src/models/pipeline.py` | `PipelineAgentNode` model (config dict) | Reference |
| `solune/backend/src/models/agent.py` | `AgentAssignment` model (config flow) | Reference |
| `solune/backend/src/services/workflow_orchestrator/config.py` | Config flow conversion | Phase 1.1 |
| `solune/backend/src/services/workflow_orchestrator/models.py` | `PipelineState` (new field) | Phase 1.2 |
| `solune/backend/src/api/pipelines.py` | Pipeline launch | Phase 1.3 |
| `solune/backend/src/services/copilot_polling/pipeline.py` | Execution logic | Phase 1.4-1.5 |
| `solune/backend/src/services/copilot_polling/auto_merge.py` | `_attempt_auto_merge()` | Reference |
| `solune/backend/src/services/agent_tracking.py` | Tracking display | Phase 3.1 |
| `solune/backend/src/services/workflow_orchestrator/orchestrator.py` | Sub-issue body | Phase 3.2 |
| `solune/frontend/src/components/pipeline/AgentNode.tsx` | UI toggle + badge | Phase 2.1, 2.3 |
| `solune/frontend/src/hooks/usePipelineBoardMutations.ts` | Config merge | Phase 2.2 |
| `solune/frontend/src/types/index.ts` | `PipelineAgentNode` type | Reference |
