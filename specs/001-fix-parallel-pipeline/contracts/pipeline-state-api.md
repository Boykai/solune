# Internal API Contract: PipelineState Properties

**Feature**: 001-fix-parallel-pipeline | **Date**: 2026-03-31
**Type**: Internal Python API (no REST/GraphQL — these are in-process property calls)

## Overview

This feature modifies internal Python dataclass properties. There are no external HTTP API changes. The contracts below define the expected behaviour of the modified/new properties for use by the polling loop and tests.

## Contract: `PipelineState.current_agents`

**Type**: Read-only property
**Returns**: `list[str]`
**Location**: `solune/backend/src/services/workflow_orchestrator/models.py`

### Preconditions

- `PipelineState` instance is valid (has `issue_number`, `project_id`, `status`, `agents`)

### Postconditions

| Scenario | Input State | Expected Return |
|----------|-------------|-----------------|
| Parallel group, all pending | `groups=[PipelineGroupInfo(mode="parallel", agents=["a","b","c"], statuses={})]` | `["a", "b", "c"]` |
| Parallel group, one completed | `groups=[PipelineGroupInfo(mode="parallel", agents=["a","b","c"], statuses={"a": "completed"})]` | `["b", "c"]` |
| Parallel group, all terminal | `groups=[PipelineGroupInfo(mode="parallel", agents=["a","b"], statuses={"a": "completed", "b": "failed"})]` | `[]` |
| Sequential group, first agent | `groups=[PipelineGroupInfo(mode="sequential", agents=["x","y"])], index_in_group=0` | `["x"]` |
| Sequential group, past end | `groups=[PipelineGroupInfo(mode="sequential", agents=["x"])], index_in_group=1` | `[]` |
| No groups (flat), has agent | `agents=["a","b"], current_agent_index=0` | `["a"]` |
| No groups (flat), complete | `agents=["a"], current_agent_index=1` | `[]` |
| Pipeline complete (past groups) | `groups=[...], current_group_index >= len(groups)` | `[]` |

### Invariants

- Return value never contains agents with status `"completed"` or `"failed"` in the current group's `agent_statuses`
- Return value is always a subset of the current group's `agents` list
- For sequential groups, return value has at most 1 element
- `current_agent` (singular) continues to return the first element of `current_agents` for non-empty results

## Contract: `PipelineState.is_complete` (modified)

**Type**: Read-only property
**Returns**: `bool`
**Location**: `solune/backend/src/services/workflow_orchestrator/models.py`

### Change Summary

Sequential group branch now checks `current_agent_index_in_group >= len(group.agents)` instead of returning `False` unconditionally.

### Postconditions

| Scenario | Input State | Expected Return |
|----------|-------------|-----------------|
| Sequential group, all agents processed | `index_in_group >= len(group.agents)`, no more groups | `True` |
| Sequential group, agent remaining | `index_in_group < len(group.agents)` | `False` |
| Parallel group, all terminal | All statuses are `"completed"` or `"failed"` | `True` |
| Parallel group, some active | At least one status is not terminal | `False` |
| Past all groups | `current_group_index >= len(groups)` | `True` |
| Empty groups skipped | Only empty groups remain | `True` |

### Backward Compatibility

- All existing parallel group behaviour unchanged
- All existing flat (no groups) behaviour unchanged
- Only sequential group detection is fixed (previously always returned `False`)

## Contract: Polling Loop Behaviour

**Function**: `_process_pipeline_completion` in `pipeline.py`
**Type**: Internal async function

### Change Summary

Completion check section iterates over `pipeline.current_agents` instead of checking single `pipeline.current_agent`.

### Expected Behaviour

| Scenario | Before (Bug) | After (Fix) |
|----------|-------------|-------------|
| Parallel group with 3 pending agents | Checks only `agents[0]` | Checks all 3 agents |
| Parallel group with 1 completed, 2 active | Checks only `agents[0]` (already done — no-op) | Checks the 2 active agents |
| Sequential group | Checks `current_agent` | Checks `current_agent` (via `current_agents` returning single-element list) |
| Recovery: parallel group after restart | Re-dispatches only `agents[0]` | Re-dispatches all unassigned agents |
