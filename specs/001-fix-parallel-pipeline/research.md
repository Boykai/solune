# Research: Fix Parallel Pipeline Execution Bugs

**Feature**: 001-fix-parallel-pipeline | **Date**: 2026-03-31

## R-001: Parallel Group Agent Retrieval Pattern

**Question**: How should `current_agents` return agents for parallel groups without breaking the existing `current_agent` interface?

**Decision**: Add a new `current_agents` property that returns `list[str]` — all non-terminal agents in the current group for parallel mode, or `[current_agent]` for sequential mode.

**Rationale**: The existing `current_agent` property is used in 20+ locations throughout the codebase (pipeline.py, orchestrator.py, agent_tracking.py, webhooks.py, workflow.py). Changing its return type from `str | None` to `list[str]` would require updating every call site and break backward compatibility. A new additive property is the lowest-risk approach.

**Alternatives considered**:
- **Change `current_agent` return type to `list[str]`** — Rejected: too many call sites to update (20+), high regression risk
- **Add an optional `parallel=True` parameter to `current_agent`** — Rejected: property can't accept parameters without becoming a method; changing to method breaks all existing call sites
- **Add a standalone function `get_current_agents(pipeline)`** — Rejected: violates encapsulation; the property belongs on the dataclass

## R-002: Sequential Group Completion Detection

**Question**: Why does `is_complete` return `False` unconditionally for sequential groups, and what is the correct fix?

**Decision**: Add a check `current_agent_index_in_group >= len(group.agents)` before the `return False` on the sequential branch of `is_complete`.

**Rationale**: The current code at models.py:211 has a bare `return False` for the sequential (`else`) branch. This was likely an oversight during the initial group-aware implementation — the parallel branch correctly checks terminal statuses, but the sequential branch never checks whether all agents in the group have been processed. The fix checks if the within-group agent index has advanced past the last agent, which is the same condition used in `_advance_pipeline` (pipeline.py:1492) to detect sequential group completion.

**Alternatives considered**:
- **Check `completed_agents` list membership** — Rejected: `completed_agents` is a flat list that doesn't track per-group state; could miss agents across groups
- **Add a separate `is_group_complete()` method** — Rejected: over-engineering for a one-line fix; `is_complete` is the right place for this logic

## R-003: Polling Loop Parallel Agent Iteration

**Question**: How should `_process_pipeline_completion` be restructured to check all parallel agents per cycle?

**Decision**: Replace the single `current_agent` check (pipeline.py:672-696) with a `for agent in pipeline.current_agents` loop. For each agent, call `_check_agent_done_on_sub_or_parent`. If any agent completes, call `_advance_pipeline` for it. Use the existing `_advance_pipeline` which already handles parallel groups correctly.

**Rationale**: The existing code fetches `pipeline.current_agent` (singular) which always returns `agents[0]` for parallel groups because `current_agent_index_in_group` stays at 0. The fix is minimal: iterate over the new `current_agents` list instead of checking a single agent. The `_advance_pipeline` function already has correct parallel group logic (marks individual agents done, advances group index only when all agents are terminal), so no changes are needed there.

**Alternatives considered**:
- **Refactor `_process_pipeline_completion` into separate parallel/sequential handlers** — Rejected: unnecessary complexity; a loop handles both cases
- **Add parallel-specific logic inside `_advance_pipeline`** — Rejected: `_advance_pipeline` already works correctly for parallel groups; the bug is in the caller, not the callee

## R-004: Recovery Path for Unassigned Parallel Agents

**Question**: How should the "agent never assigned" recovery path handle parallel groups?

**Decision**: Iterate over `pipeline.current_agents` in the recovery section (pipeline.py:698-806) instead of checking only `current_agent`. For each unassigned agent, perform the same tracking-table and in-memory checks, then dispatch if needed.

**Rationale**: After state reconstruction (e.g., container restart), a parallel group may have multiple agents that were never assigned. The current code only checks `current_agent` (always `agents[0]`), leaving `agents[1..N]` permanently unassigned. The fix applies the same recovery logic to all agents in the group.

**Alternatives considered**:
- **Add a separate recovery function for parallel groups** — Rejected: duplicates logic; iterating over `current_agents` reuses the same checks
- **Fix `determine_next_action` in `agent_tracking.py` instead** — Rejected: explicitly out of scope per parent issue decisions; that's a separate, lower-priority recovery path

## R-005: Terminal Agent Filtering in `current_agents`

**Question**: Should `current_agents` return all agents in a parallel group or only non-terminal ones?

**Decision**: Return only non-terminal agents (those not in `completed` or `failed` status in the group's `agent_statuses` map).

**Rationale**: The polling loop should only check agents that haven't finished yet. Including completed agents would cause redundant `_check_agent_done_on_sub_or_parent` calls and potentially duplicate `_advance_pipeline` calls. Filtering at the property level keeps the polling loop simple and prevents wasted API calls.

**Alternatives considered**:
- **Return all agents and filter in the polling loop** — Rejected: pushes filtering responsibility to every caller; DRY principle
- **Return agents with their statuses as tuples** — Rejected: over-complicates the interface; simple `list[str]` is sufficient
