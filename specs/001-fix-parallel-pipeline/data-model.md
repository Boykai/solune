# Data Model: Fix Parallel Pipeline Execution Bugs

**Feature**: 001-fix-parallel-pipeline | **Date**: 2026-03-31

## Entity: PipelineState

**Location**: `solune/backend/src/services/workflow_orchestrator/models.py`
**Type**: Python `@dataclass`

### Existing Fields (no changes)

| Field | Type | Description |
|-------|------|-------------|
| `issue_number` | `int` | Issue being processed |
| `project_id` | `str` | GitHub project ID |
| `status` | `str` | Current pipeline status |
| `agents` | `list[str]` | Flat list of all agent slugs |
| `current_agent_index` | `int` | Global agent index (flat) |
| `completed_agents` | `list[str]` | Agents that have finished |
| `groups` | `list[PipelineGroupInfo]` | Ordered execution groups |
| `current_group_index` | `int` | Index into `groups` |
| `current_agent_index_in_group` | `int` | Index within current group |
| `execution_mode` | `str` | Top-level mode (`"sequential"` / `"parallel"`) |
| `parallel_agent_statuses` | `dict[str, str]` | Flat parallel status map (legacy) |
| `failed_agents` | `list[str]` | Agents that failed |

### Existing Properties (no changes)

| Property | Return Type | Description |
|----------|-------------|-------------|
| `current_agent` | `str \| None` | First/only active agent in current group — unchanged |
| `next_agent` | `str \| None` | Next agent after current (flat index) |
| `is_parallel_stage_failed` | `bool` | Whether any parallel agent has failed |

### New Property: `current_agents`

| Property | Return Type | Description |
|----------|-------------|-------------|
| `current_agents` | `list[str]` | All active/pending agents in the current group |

**Behaviour**:
- When `groups` exist and current group is `"parallel"`: returns all agents in the group whose status in `agent_statuses` is NOT `"completed"` or `"failed"`
- When `groups` exist and current group is `"sequential"`: returns `[current_agent]` (single-element list) or `[]` if `current_agent` is `None`
- When no groups (flat fallback): returns `[current_agent]` or `[]`

### Modified Property: `is_complete`

**Bug**: The sequential branch unconditionally returns `False` (L211).

**Fix**: Before returning `False`, check `current_agent_index_in_group >= len(group.agents)`. If true, the sequential group is complete — continue the existing empty-group-skipping logic and return `True` if no more non-empty groups remain.

**Before**:
```python
# L206-211
if group.execution_mode == "parallel":
    if len(group.agent_statuses) < len(group.agents):
        return False
    return all(s in ("completed", "failed") for s in group.agent_statuses.values())
return False  # ← BUG: always False for sequential
```

**After**:
```python
if group.execution_mode == "parallel":
    if len(group.agent_statuses) < len(group.agents):
        return False
    return all(s in ("completed", "failed") for s in group.agent_statuses.values())
# Sequential: check if all agents in group have been processed
if self.current_agent_index_in_group >= len(group.agents):
    # Current group done — check if there are more non-empty groups
    next_idx = idx + 1
    while next_idx < len(self.groups) and not self.groups[next_idx].agents:
        next_idx += 1
    return next_idx >= len(self.groups)
return False
```

## Entity: PipelineGroupInfo

**Location**: `solune/backend/src/services/workflow_orchestrator/models.py`
**Type**: Python `@dataclass`
**Changes**: None — existing structure is sufficient.

| Field | Type | Description |
|-------|------|-------------|
| `group_id` | `str` | Unique group identifier |
| `execution_mode` | `str` | `"sequential"` or `"parallel"` |
| `agents` | `list[str]` | Ordered list of agent slugs in group |
| `agent_statuses` | `dict[str, str]` | Per-agent status tracking map |

## Relationships

```
PipelineState
├── groups: list[PipelineGroupInfo]  (ordered, 0..N)
│   └── agents: list[str]           (ordered, 1..N per group)
│   └── agent_statuses: dict        (agent_name → status)
├── agents: list[str]               (flat, all agents across groups)
└── completed_agents: list[str]     (flat, terminal agents)
```

## State Transitions

### Agent Status (within PipelineGroupInfo.agent_statuses)

```
pending → active → completed
                 → failed
```

### Group Lifecycle

```
[enter group]
  ├── parallel:  dispatch all agents → poll all agents → all terminal → advance
  └── sequential: dispatch agent[0] → complete → dispatch agent[1] → ... → all done → advance
```

## Validation Rules

- `current_agents` returns empty list `[]` when pipeline is complete (no current group)
- `current_agents` never contains agents with `"completed"` or `"failed"` status
- `is_complete` returns `True` only when ALL groups (including sequential) have been fully processed
- `current_agent` behaviour is unchanged — always returns `agents[current_agent_index_in_group]` for the current group
