# Research: Fix Parallel Pipeline Execution Bugs

**Feature**: 002-fix-parallel-pipeline-bugs
**Date**: 2026-03-31
**Status**: Complete

## Research Tasks

### RT-001: current_agent vs current_agents — Additive Property Design

**Context**: The `current_agent` property (singular) is used in 20+ places throughout the codebase for sequential pipeline logic, logging, and label management. We need a way to retrieve ALL agents in a parallel group without breaking these existing consumers.

**Decision**: Add a new `current_agents` (plural) property to `PipelineState` that returns a `list[str]`. For parallel groups, it returns all agents in the current group. For sequential groups, it returns a single-element list containing the current agent. The existing `current_agent` property remains unchanged.

**Rationale**: Modifying the return type of `current_agent` (from `str | None` to `list[str]`) would require changes to 20+ call sites across the codebase — a massive change surface for a targeted bug fix. Adding a new property provides the parallel-aware interface the polling loop needs while preserving backward compatibility for all sequential consumers.

**Alternatives considered**:
- **Change `current_agent` return type to `list[str]`**: Would require updating 20+ call sites across `pipeline.py`, `orchestrator.py`, `agent_tracking.py`, and test files. Excessive change surface, high regression risk.
- **Add a `get_agents(parallel: bool)` method**: Unnecessary parameterization — the property already knows the group's execution mode and can dispatch internally. A method adds no value over a property here.
- **Use `current_group.agents` directly in callers**: Breaks encapsulation — callers shouldn't need to know about group internals or handle empty-group skipping themselves. The property centralizes this logic.

---

### RT-002: Sequential Group is_complete Bug Analysis

**Context**: At `models.py` (is_complete property), sequential groups check whether the group is complete. The issue reports that sequential groups unconditionally return `False`. Need to verify the exact bug and determine the fix.

**Decision**: The sequential branch of `is_complete` should check `self.current_agent_index_in_group >= len(group.agents)`. When the agent index has advanced past the last agent in the group, the group is complete. This mirrors how flat (non-grouped) sequential pipelines check `self.current_agent_index >= len(self.agents)`.

**Rationale**: The `current_agent_index_in_group` tracks progress within a group. When it equals or exceeds the group's agent count, all agents in that group have been processed. This is the natural completion condition, consistent with the flat pipeline fallback logic.

**Alternatives considered**:
- **Check `completed_agents` intersection with `group.agents`**: More complex, requires set operations, and doesn't account for the fact that `completed_agents` is a flat list that may contain agents from other groups.
- **Add a `completed` boolean field to `PipelineGroupInfo`**: Adds state that must be kept in sync with the index — a redundant signal that increases the risk of inconsistency. The index-based check is the single source of truth.

---

### RT-003: Polling Loop Parallel Iteration Strategy

**Context**: `_process_pipeline_completion` in `pipeline.py` is the main polling loop function called every 60 seconds. It currently checks a single `current_agent` for completion. For parallel groups, this means only agent[0] is ever checked, leaving other agents permanently in "Pending" state.

**Decision**: Replace the single-agent check with a `for agent in pipeline.current_agents` loop. For each non-completed agent, call `_check_agent_done_on_sub_or_parent`. If any agent completes, call `_advance_pipeline` for it. The existing `_advance_pipeline` already handles parallel groups correctly (marks individual agents done via `agent_statuses`, advances group index only when all agents are terminal).

**Rationale**: The `current_agents` property returns all active agents for parallel groups and a single agent for sequential groups. Iterating over this list unifies the polling logic for both modes — a sequential group with one current agent iterates exactly once (no behavioral change), while a parallel group iterates over all agents. The `_advance_pipeline` function's existing parallel logic ensures individual agent completion doesn't prematurely advance the group.

**Alternatives considered**:
- **Check group execution mode explicitly in the polling loop**: Adds branching logic that mirrors what `current_agents` already encapsulates. Violates DRY — the property exists to abstract this decision.
- **Spawn separate polling tasks per parallel agent**: Over-engineered; the polling loop is already synchronous within a cycle. Multiple agents can be checked sequentially within the same cycle since each check is a lightweight GitHub API call that completes quickly.
- **Use asyncio.gather for parallel agent checks**: Premature optimization; checking 3-5 agents sequentially within a 60-second poll cycle adds negligible overhead. The bottleneck is the poll interval itself, not the per-agent check latency.

---

### RT-004: Recovery Path Parallel Agent Reassignment

**Context**: The recovery logic in `pipeline.py` detects agents that were "never assigned" (not in the tracking table, not in the pending assignments cache) and reassigns them. This logic also uses `current_agent` (singular), meaning only agent[0] is checked for reassignment after a service restart.

**Decision**: Iterate over `pipeline.current_agents` in the recovery path. For each agent, check:
1. Is it already completed or failed? → Skip.
2. Is it Active in the tracking table? → Skip.
3. Is it in the pending assignments cache? → Skip.
4. Otherwise → Reassign it by calling `assign_agent_for_status` with the agent's flat index.

**Rationale**: The recovery path's purpose is to detect and fix agents that fell through the cracks during a restart. For parallel groups, ALL agents in the group may need recovery, not just the first. The same skip-conditions apply to each agent individually, so the existing guard logic (tracking check, pending check) works per-agent within a loop.

**Alternatives considered**:
- **Batch reassignment with a single orchestrator call**: The orchestrator's `assign_agent_for_status` is designed for single-agent assignment. Creating a batch API adds complexity and a new code path that would need its own tests. Per-agent calls are simple and correct.
- **Reconstruct full group state from GitHub API**: Over-fetching; the tracking table and pending cache already provide the information needed to determine assignment status. No new API calls required beyond the existing per-agent check.

---

### RT-005: _advance_pipeline Correctness Verification

**Context**: The issue states that `_advance_pipeline` already handles parallel groups correctly. Need to verify this before relying on it.

**Decision**: Confirmed — `_advance_pipeline` is correct and requires no changes. For parallel groups, it:
1. Marks the completed agent in `group.agent_statuses` as "completed".
2. Checks if ALL agents in the group have terminal statuses (`completed` or `failed`).
3. Only advances `current_group_index` when all agents are terminal.
4. Skips empty groups after advancement.

**Rationale**: The function's parallel logic correctly implements per-agent tracking and group-level advancement. The bug is not in advancement but in the polling loop that fails to detect completion for agents other than agent[0].

**Alternatives considered**:
- **Refactor `_advance_pipeline` to accept an agent name parameter**: Not needed — it already uses `pipeline.current_agent` internally and advances the correct agent based on calling context. The fix is upstream (in the polling loop), not in the advancement function.

---

### RT-006: Initial Launch Stagger — Bug or Feature?

**Context**: `execute_full_workflow` in `orchestrator.py` dispatches parallel agents with a 2-second `asyncio.sleep(2)` stagger between each agent. The issue identifies this as intentional rate-limit protection, but it should be verified.

**Decision**: Confirmed — the stagger is intentional and should NOT be removed. It prevents hitting GitHub API rate limits when creating multiple agent sub-issues simultaneously. The stagger only applies to the initial dispatch in `execute_full_workflow`, not to the polling loop.

**Rationale**: GitHub's API has rate limits (5,000 requests/hour for authenticated users, with lower burst limits). Dispatching 3 agents simultaneously would send 3 `create_issue` calls within milliseconds, risking a 429 response. The 2-second stagger spaces these calls safely while still launching all agents within a single pipeline setup cycle.

**Alternatives considered**:
- **Remove stagger, add retry-with-backoff**: More complex, adds error handling code, and still risks hitting rate limits during bursts. The stagger is simpler and prevents the problem proactively.
- **Make stagger configurable**: YAGNI — 2 seconds is a reasonable default. Configuration adds complexity without demonstrated need.
