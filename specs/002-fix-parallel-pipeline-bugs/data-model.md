# Data Model: Fix Parallel Pipeline Execution Bugs

**Feature**: 002-fix-parallel-pipeline-bugs
**Date**: 2026-03-31
**Prerequisites**: [research.md](./research.md)

## Entities

### PipelineState (Existing — Modified)

The core state machine tracking per-issue pipeline progress. Located in `src/services/workflow_orchestrator/models.py`.

| Field | Type | Status | Description |
|-------|------|--------|-------------|
| `issue_number` | `int` | Existing | The GitHub issue this pipeline tracks |
| `project_id` | `str` | Existing | GitHub project identifier |
| `status` | `str` | Existing | Current pipeline status (e.g., "In Progress") |
| `agents` | `list[str]` | Existing | Flat list of all agent slugs in execution order |
| `current_agent_index` | `int` | Existing | Index into flat `agents` list (fallback for non-grouped pipelines) |
| `completed_agents` | `list[str]` | Existing | Agents that have completed successfully |
| `failed_agents` | `list[str]` | Existing | Agents that have failed |
| `execution_mode` | `str` | Existing | Top-level mode: "sequential" or "parallel" |
| `parallel_agent_statuses` | `dict[str, str]` | Existing | Per-agent status for flat parallel pipelines |
| `groups` | `list[PipelineGroupInfo]` | Existing | Ordered list of execution groups |
| `current_group_index` | `int` | Existing | Index of the currently executing group |
| `current_agent_index_in_group` | `int` | Existing | Index within the current group (sequential only) |

**Properties**:

| Property | Return Type | Status | Description |
|----------|-------------|--------|-------------|
| `current_agent` | `str \| None` | Existing — NO CHANGE | Returns the single current agent slug. For groups, returns agent at `current_agent_index_in_group` in current group. Skips empty groups. |
| `current_agents` | `list[str]` | **NEW** | Returns ALL agents in the current group for parallel mode; single-element list for sequential mode. Skips empty groups. Falls back to `[current_agent]` when no groups configured. |
| `is_complete` | `bool` | Existing — **FIXED** | Checks if the pipeline/group has completed. Sequential group fix: checks `current_agent_index_in_group >= len(group.agents)` instead of unconditionally returning `False`. |

---

### PipelineGroupInfo (Existing — No Changes)

Defines a single execution group within a pipeline. Located in `src/services/workflow_orchestrator/models.py`.

| Field | Type | Description |
|-------|------|-------------|
| `group_id` | `str` | Unique group identifier |
| `execution_mode` | `str` | "sequential" or "parallel" |
| `agents` | `list[str]` | Ordered list of agent slugs in this group |
| `agent_statuses` | `dict[str, str]` | Maps agent slug → status ("pending", "active", "completed", "failed") |

**No changes needed** — this entity already has sufficient state tracking for parallel agent statuses.

---

### Polling Loop (Existing — Modified Behavior)

The periodic process in `src/services/copilot_polling/pipeline.py` that checks agent completion and advances pipeline state.

| Aspect | Current Behavior | Fixed Behavior |
|--------|-----------------|----------------|
| Agent check per cycle | Single `current_agent` checked | ALL `current_agents` checked via loop |
| Parallel group handling | Only agent[0] checked | Every non-completed agent checked |
| Agent advancement | Single agent advanced | Each completed agent advanced individually |
| Group advancement | Group advances after single agent | Group advances only when ALL agents terminal |

---

### Recovery Path (Existing — Modified Behavior)

Fallback logic in `src/services/copilot_polling/pipeline.py` that detects and reassigns agents never assigned after state reconstruction.

| Aspect | Current Behavior | Fixed Behavior |
|--------|-----------------|----------------|
| Agent reassignment scope | Single `current_agent` checked | ALL `current_agents` checked via loop |
| Skip conditions | Single agent: completed/failed, tracked, pending | Per-agent: same skip conditions applied individually |
| Parallel group recovery | Only agent[0] reassigned | All unassigned agents reassigned |

---

## Relationships

```text
PipelineState
    │
    ├── Has many: PipelineGroupInfo (via groups field)
    │       │
    │       ├── Has many: agents (list[str])
    │       └── Tracks: agent_statuses (dict[str, str])
    │
    ├── Property: current_agent → str | None (EXISTING, unchanged)
    │       └── Used by: logging, label management, _advance_pipeline
    │
    ├── Property: current_agents → list[str] (NEW)
    │       ├── Used by: _process_pipeline_completion (polling loop)
    │       └── Used by: _process_pipeline_completion (recovery path)
    │
    └── Property: is_complete → bool (FIXED)
            └── Used by: _process_pipeline_completion (completion check)

_process_pipeline_completion (pipeline.py)
    │
    ├── Reads: pipeline.is_complete → decide if pipeline is done
    ├── Iterates: pipeline.current_agents → check each agent's completion
    ├── Calls: _check_agent_done_on_sub_or_parent → per-agent completion check
    ├── Calls: _advance_pipeline → per-agent advancement (NO CHANGES)
    └── Recovery: iterate current_agents → reassign unassigned agents

_advance_pipeline (pipeline.py) — NO CHANGES
    │
    ├── Reads: pipeline.current_agent → identify which agent completed
    ├── Updates: group.agent_statuses[agent] = "completed"
    ├── Checks: all agents terminal → advance current_group_index
    └── Skips: empty groups after advancement
```

## State Transitions

### Parallel Group Agent Lifecycle

```text
[Pending] ──dispatch──→ [Active] ──complete──→ [Completed]
                            │
                            └──fail──→ [Failed]
```

All agents in a parallel group start as "pending" and are dispatched to "active" during initial launch (with 2-second stagger). The polling loop checks ALL active agents per cycle. Each agent transitions independently to "completed" or "failed". The group advances to the next group only when ALL agents have reached a terminal state.

### Sequential Group Agent Lifecycle

```text
[Pending] ──dispatch──→ [Active] ──complete──→ [Completed] ──next──→ [Pending (next agent)]
                            │
                            └──fail──→ [Failed]
```

Sequential groups process one agent at a time. The `current_agent_index_in_group` advances after each agent completes. The group is complete when `current_agent_index_in_group >= len(group.agents)`.

### Pipeline Group Advancement

```text
[Group 0: Sequential] ──all agents done──→ [Group 1: Parallel] ──all agents terminal──→ [Group 2: Sequential] ──...──→ [Pipeline Complete]
```

Empty groups are silently skipped during advancement. The `current_group_index` advances past empty groups automatically.
