# Quickstart: Fix Parallel Pipeline Execution Bugs

**Feature**: 002-fix-parallel-pipeline-bugs
**Date**: 2026-03-31
**Prerequisites**: [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

## Overview

This feature fixes parallel pipeline execution so that ALL agents in a parallel group are checked, advanced, and recovered per polling cycle — instead of only the first agent. The fix is surgical: 2 files modified, 0 new files, ~30-50 lines of code changed.

## Modified Files

### 1. `solune/backend/src/services/workflow_orchestrator/models.py`

Two changes to the `PipelineState` class:

#### Change A: Add `current_agents` property (after existing `current_agent` at ~line 193)

```python
@property
def current_agents(self) -> list[str]:
    """Return ALL agents in the current group for parallel; single for sequential."""
    if self.groups:
        idx = self.current_group_index
        while idx < len(self.groups):
            group = self.groups[idx]
            if group.agents:
                if group.execution_mode == "parallel":
                    return group.agents  # ALL agents for parallel groups
                # Sequential: return single current agent
                if self.current_agent_index_in_group < len(group.agents):
                    return [group.agents[self.current_agent_index_in_group]]
                break  # Index past end of group
            idx += 1  # Skip empty groups
        return []

    # Flat fallback
    agent = self.current_agent
    return [agent] if agent else []
```

#### Change B: Fix `is_complete` for sequential groups (in existing property at ~line 217)

**Before** (sequential branch):
```python
# Sequential: unconditionally returns False (BUG)
return False
```

**After**:
```python
# Sequential: complete when index reaches end of group
return self.current_agent_index_in_group >= len(group.agents)
```

### 2. `solune/backend/src/services/copilot_polling/pipeline.py`

Two changes in `_process_pipeline_completion`:

#### Change C: Polling loop uses `current_agents` (~line 680)

**Before**:
```python
agent = pipeline.current_agent
if agent and agent not in pipeline.completed_agents and agent not in pipeline.failed_agents:
    completed = await _cp._check_agent_done_on_sub_or_parent(
        ..., agent_name=agent, pipeline=pipeline,
    )
    if completed:
        await _advance_pipeline(...)
```

**After**:
```python
for agent in pipeline.current_agents:
    if agent in pipeline.completed_agents or agent in pipeline.failed_agents:
        continue
    completed = await _cp._check_agent_done_on_sub_or_parent(
        ..., agent_name=agent, pipeline=pipeline,
    )
    if completed:
        await _advance_pipeline(...)
```

#### Change D: Recovery path uses `current_agents` (~line 710)

**Before**:
```python
agent = pipeline.current_agent
if agent and agent not in pipeline.completed_agents:
    # ... check tracking, check pending, reassign
```

**After**:
```python
for agent in pipeline.current_agents:
    if agent in pipeline.completed_agents or agent in pipeline.failed_agents:
        continue
    # ... check tracking, check pending, reassign (per-agent)
```

## Files NOT Modified

| File | Reason |
|------|--------|
| `orchestrator.py` | Initial parallel dispatch with 2-second stagger is correct and intentional |
| `_advance_pipeline` | Parallel group advancement logic is already correct |
| `agent_tracking.py` | `determine_next_action` is out of scope (separate lower-priority recovery) |

## Test Files to Extend

### 1. `solune/backend/tests/unit/test_models.py`

Add tests for:
- `test_current_agents_parallel_returns_all` — Verify parallel group returns all agent slugs
- `test_current_agents_sequential_returns_single` — Verify sequential returns one-element list
- `test_current_agents_empty_group_skipped` — Verify empty groups are skipped
- `test_current_agents_flat_fallback` — Verify non-grouped pipeline falls back to `[current_agent]`
- `test_is_complete_sequential_group_done` — Verify sequential group completes when index reaches end
- `test_is_complete_sequential_group_not_done` — Verify sequential group incomplete when agents remain

### 2. `solune/backend/tests/unit/test_copilot_polling.py`

Add tests for:
- `test_process_pipeline_completion_checks_all_parallel_agents` — Verify all agents in parallel group are checked per cycle
- `test_recovery_reassigns_all_unassigned_parallel_agents` — Verify all unassigned agents get reassigned

## Implementation Order

1. **Add `current_agents` property to `PipelineState`** (models.py, Change A)
2. **Fix `is_complete` for sequential groups** (models.py, Change B) — parallel with step 1
3. **Update polling loop to use `current_agents`** (pipeline.py, Change C) — depends on step 1
4. **Update recovery path to use `current_agents`** (pipeline.py, Change D) — depends on step 1, parallel with step 3
5. **Add model property tests** (test_models.py) — depends on steps 1-2
6. **Add polling/recovery tests** (test_copilot_polling.py) — depends on steps 3-4
7. **Run full regression suite** — depends on steps 5-6

## Verification

After implementation, verify each phase:

```bash
cd solune/backend

# Phase 1: Model property fixes
uv run pytest tests/unit/test_models.py -v -k "complete or current_agent"

# Phase 2: Polling loop fix
uv run pytest tests/unit/test_copilot_polling.py -v -k "parallel"

# Phase 3: Property invariants
uv run pytest tests/property/test_pipeline_state_machine.py -v

# Full regression
uv run pytest tests/unit/ tests/property/ -v --tb=short

# Lint
.venv/bin/ruff check src/services/workflow_orchestrator/models.py src/services/copilot_polling/pipeline.py
.venv/bin/ruff format --check src/services/workflow_orchestrator/models.py src/services/copilot_polling/pipeline.py
uv run pyright src/services/workflow_orchestrator/models.py
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| New `current_agents` property (not changing `current_agent`) | `current_agent` used in 20+ places; changing return type has massive blast radius |
| Index-based sequential completion check | Consistent with flat pipeline fallback; single source of truth |
| Loop over `current_agents` in polling loop | Unifies sequential and parallel handling — sequential iterates once |
| No changes to `_advance_pipeline` | Its parallel logic is already correct |
| No changes to `orchestrator.py` stagger | 2-second stagger is intentional rate-limit protection |
| Scope excludes `agent_tracking.py` | Separate lower-priority recovery path; fix would be a distinct PR |
