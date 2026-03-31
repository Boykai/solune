# Feature Specification: Fix Parallel Pipeline Execution Bugs

**Feature Branch**: `001-fix-parallel-pipeline`  
**Created**: 2026-03-31  
**Status**: Draft  
**Input**: User description: "Fix Parallel Pipeline Execution Bugs — Parallel pipeline groups execute agents one-at-a-time instead of simultaneously. The root cause is that the polling loop only checks a single agent per cycle, and for parallel groups that agent is always the first one. Both issues #158 and #144 show the same symptom: a parallel group with 1 Active + 2 Pending instead of all 3 Active."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Parallel Agents Execute Simultaneously (Priority: P1)

When a user triggers a pipeline that contains a parallel agent group (e.g., three quality-assurance agents meant to run concurrently), all agents in that group should be dispatched and monitored at the same time. Currently only the first agent in the group is tracked each polling cycle, leaving the remaining agents stuck in "Pending" while the first one runs alone.

**Why this priority**: This is the core defect. Parallel execution is the primary value proposition of pipeline groups — without it, multi-agent workflows take 3× longer than designed and the user sees misleading status indicators.

**Independent Test**: Can be fully tested by launching a pipeline with a parallel group of 3 agents and verifying all 3 show "Active" status simultaneously within one polling cycle. Delivers the expected concurrent throughput improvement.

**Acceptance Scenarios**:

1. **Given** a pipeline with a parallel group containing agents A, B, and C all in "Pending" status, **When** the polling loop processes the group, **Then** all three agents are dispatched and their statuses transition to "Active" simultaneously.
2. **Given** a parallel group where agent A has completed but agents B and C are still active, **When** the polling loop runs, **Then** agents B and C continue to be monitored and their completion is detected as soon as each finishes — not only on the cycle that happens to check them.
3. **Given** a parallel group where all three agents have reached a terminal state (completed or failed), **When** the polling loop runs, **Then** the pipeline advances to the next group without requiring additional cycles.

---

### User Story 2 - Sequential Group Completion Is Detected (Priority: P2)

When a user runs a pipeline that contains sequential groups (agents run one after another within a group), the system should correctly detect when all agents in a sequential group have finished and advance the pipeline to the next group.

**Why this priority**: Without this fix, pipelines with sequential groups stall indefinitely after the last agent in the group completes — the system never recognises the group as "done" and never transitions to subsequent groups. This blocks any pipeline that mixes sequential and parallel groups.

**Independent Test**: Can be fully tested by creating a pipeline with a sequential group of 2 agents, advancing through both, and verifying the pipeline detects group completion and moves forward.

**Acceptance Scenarios**:

1. **Given** a sequential group with agents X and Y where both have completed, **When** the system evaluates group completion, **Then** the group is correctly identified as complete and the pipeline advances to the next group.
2. **Given** a sequential group where only agent X has completed and agent Y is still pending, **When** the system evaluates group completion, **Then** the group is correctly identified as incomplete and the pipeline stays on the current group.
3. **Given** a pipeline with a sequential group followed by a parallel group, **When** the sequential group completes, **Then** the pipeline transitions to the parallel group and all parallel agents are dispatched concurrently (no stall between groups).

---

### User Story 3 - Recovery of Unassigned Parallel Agents (Priority: P3)

When the system recovers from a transient failure (e.g., after a restart or state reconstruction), all agents in a parallel group that were never assigned should be re-dispatched — not just the first agent in the group.

**Why this priority**: This is a resilience concern. While less frequent than the primary execution bug, it causes the same symptom (only 1 of N agents active) and is harder to diagnose because it only manifests after recovery events.

**Independent Test**: Can be fully tested by simulating a pipeline state reconstruction where a parallel group has agents that were never assigned, and verifying that all unassigned agents are dispatched during recovery.

**Acceptance Scenarios**:

1. **Given** a parallel group with 3 agents where none have been assigned after state reconstruction, **When** the recovery logic runs, **Then** all 3 agents are dispatched (not just the first one).
2. **Given** a parallel group with 3 agents where 1 has been assigned and 2 are still unassigned after reconstruction, **When** the recovery logic runs, **Then** the 2 unassigned agents are dispatched while the already-active agent continues uninterrupted.

---

### Edge Cases

- What happens when a parallel group contains only a single agent? The system should treat it identically to a sequential single-agent group — dispatch the one agent and detect its completion normally.
- How does the system handle a parallel group where all agents fail? The group should still be detected as complete (all agents in terminal state) and the pipeline should advance, applying existing failure-handling rules.
- What happens if the agent status tracking map is only partially initialised when a group is first entered? The system should not prematurely block the group or treat it as "already active" — it should detect a newly-entered group and proceed with assignment.
- What happens when an empty group (zero agents) is encountered? The system should skip it and advance to the next group.
- How does the system behave if the same pipeline is polled concurrently by two loops? The existing state-management serialisation should prevent double-dispatch; this fix must not introduce race conditions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a way to retrieve all agents in the current group when the group is configured for parallel execution, rather than only the first agent.
- **FR-002**: The system MUST monitor and check the completion status of every agent in a parallel group during each polling cycle — not just a single agent.
- **FR-003**: When any agent in a parallel group completes during a polling cycle, the system MUST detect that completion and advance that agent's individual state in the same cycle.
- **FR-004**: The system MUST correctly detect when a sequential group has completed (all agents in the group have been processed) and advance the pipeline to the next group.
- **FR-005**: When the system recovers from a transient failure, it MUST re-dispatch all unassigned agents in a parallel group — not just the first agent.
- **FR-006**: The system MUST NOT change the existing behaviour for sequential pipeline groups or single-agent operations; the fix must be additive and backward-compatible.
- **FR-007**: The existing intentional stagger delay between parallel agent launches (for rate-limit protection) MUST be preserved — the fix addresses monitoring, not initial dispatch timing.
- **FR-008**: The system MUST continue to advance the group index only when all agents in a parallel group have reached a terminal state (completed or failed).

### Key Entities

- **PipelineState**: Represents the current execution state of a pipeline, including which group is active, agent indices, and per-agent status tracking. This is the entity that needs a new "all current agents" accessor alongside the existing single-agent accessor.
- **PipelineGroupInfo**: Defines a group of agents within a pipeline, including execution mode (parallel or sequential), the list of agent identifiers, and a per-agent status map.
- **Polling Loop**: The periodic process (approximately every 60 seconds) that checks agent completion and advances pipeline state. This is the process that currently only checks a single agent per cycle.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When a parallel group of N agents is entered, all N agents show "Active" status within one polling cycle (no agents remain stuck in "Pending").
- **SC-002**: Pipeline throughput for a 3-agent parallel group completes in approximately the time of the slowest agent, not 3× that time (i.e., actual parallel execution rather than serial).
- **SC-003**: Sequential group completion is detected on the first polling cycle after the last agent finishes — zero additional cycles of delay.
- **SC-004**: After a state reconstruction event, all unassigned parallel agents are recovered and dispatched within one polling cycle.
- **SC-005**: All existing pipeline tests continue to pass with no regressions — backward compatibility is fully maintained.
- **SC-006**: The fix introduces no new race conditions — concurrent polling loops do not produce duplicate agent dispatches.

## Assumptions

- The existing `_advance_pipeline` logic for parallel groups is already correct (marks individual agents as done, advances group index only when all agents are terminal) and does not need modification.
- The intentional 2-second stagger delay between parallel agent launches in the initial dispatch is rate-limit protection and is not a bug — it is explicitly out of scope.
- The `determine_next_action` function in `agent_tracking.py` is a separate, lower-priority recovery path and is excluded from this fix's scope.
- The existing single-agent accessor (`current_agent`) will be preserved unchanged, as it is used in 20+ locations for sequential logic. A new plural accessor will be added alongside it.
- Agent status maps (`agent_statuses`) on parallel groups are initialised at group entry time and are expected to contain entries for all agents in the group.
