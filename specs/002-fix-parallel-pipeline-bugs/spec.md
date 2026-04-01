# Feature Specification: Fix Parallel Pipeline Execution Bugs

**Feature Branch**: `002-fix-parallel-pipeline-bugs`
**Created**: 2026-03-31
**Status**: Ready
**Input**: User description: "Plan: Fix Parallel Pipeline Execution Bugs"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Parallel Agents Execute Simultaneously (Priority: P1)

As a user who triggers a pipeline containing a parallel execution group, I expect all agents in that group to become active at the same time rather than one-at-a-time. Currently, only the first agent in a parallel group is checked and activated during each polling cycle, leaving the remaining agents stuck in a "Pending" state indefinitely. This bug negates the purpose of parallel execution groups.

**Why this priority**: This is the core defect. Parallel groups are fundamentally broken — they behave identically to sequential groups. Every pipeline with a parallel stage is affected, resulting in significantly longer execution times and misleading status indicators.

**Independent Test**: Can be fully tested by triggering a pipeline with a 3-agent parallel group and verifying all 3 agents show 🔄 Active simultaneously within a single polling cycle, delivering correct parallel execution behavior.

**Acceptance Scenarios**:

1. **Given** a pipeline with a parallel group containing 3 agents (all Pending), **When** the polling loop processes the pipeline, **Then** all 3 agents are checked for completion status during the same poll cycle (not just the first agent).
2. **Given** a parallel group where agent 2 of 3 completes, **When** the polling loop runs, **Then** the system detects agent 2's completion and advances it individually without affecting agents 1 and 3 that are still running.
3. **Given** a parallel group where all 3 agents have completed, **When** the polling loop runs, **Then** the group is marked complete and the pipeline advances to the next group.

---

### User Story 2 - Sequential Group Completion Detection (Priority: P1)

As a user running a pipeline with sequential execution groups, I expect the system to correctly detect when a sequential group has finished processing all its agents. Currently, sequential groups unconditionally report as incomplete, which can cause the pipeline to stall or behave unpredictably after the last agent in a sequential group finishes.

**Why this priority**: This is a correctness bug that can block pipeline advancement. Even though sequential execution appears to work in many cases (because the flat agent index may advance past the group), the faulty completion signal can cause edge-case stalls and incorrect state reporting.

**Independent Test**: Can be fully tested by creating a pipeline with a sequential group of 2 agents, advancing the internal index past both agents, and verifying the group reports as complete.

**Acceptance Scenarios**:

1. **Given** a sequential group with 2 agents where both have been processed (agent index in group equals group size), **When** the system checks if the group is complete, **Then** it returns true.
2. **Given** a sequential group with 3 agents where only 2 have been processed, **When** the system checks if the group is complete, **Then** it returns false.
3. **Given** a pipeline that transitions from a completed sequential group to the next group, **When** the sequential group correctly signals completion, **Then** the pipeline seamlessly advances to the next group.

---

### User Story 3 - Parallel Agent Recovery After Restart (Priority: P2)

As a user whose pipeline was interrupted (e.g., by a service restart), I expect all agents in a parallel group to be reassigned and recovered, not just the first one. Currently, the recovery path only looks at a single agent when reconstructing state, leaving the other parallel agents permanently unassigned.

**Why this priority**: Recovery correctness is critical for reliability, but this scenario is less frequent than the primary polling bug. Users who experience a service restart during a parallel stage will see only 1 of N agents recover, requiring manual intervention for the rest.

**Independent Test**: Can be fully tested by simulating a pipeline with a 3-agent parallel group where none of the agents appear in the tracking table as Active or assigned, and verifying that all 3 agents are reassigned during the recovery path.

**Acceptance Scenarios**:

1. **Given** a parallel group with 3 agents where none have been assigned (no tracking table entries, no pending assignments), **When** the recovery logic runs, **Then** all 3 unassigned agents are reassigned (not just the first one).
2. **Given** a parallel group with 3 agents where agent 1 is already Active but agents 2 and 3 are unassigned, **When** the recovery logic runs, **Then** only agents 2 and 3 are reassigned while agent 1 is left untouched.
3. **Given** a sequential group with an unassigned agent, **When** the recovery logic runs, **Then** only the single current agent is reassigned (existing behavior preserved).

---

### Edge Cases

- What happens when a parallel group contains only 1 agent? The system should treat it identically to a sequential single-agent group — no behavioral difference.
- What happens when a parallel group contains an empty agents list? The system should skip the empty group and advance to the next group without errors.
- What happens when all agents in a parallel group fail? The group should still be marked as complete (all agents are in a terminal state) and the pipeline's failure handling logic should determine whether to continue or abort.
- What happens when the polling loop detects completion for multiple parallel agents in the same cycle? Each completed agent should be advanced individually, and the group should only advance when all agents reach a terminal state.
- How does the system handle a mix of sequential and parallel groups in the same pipeline? Each group should be evaluated according to its own execution mode — sequential groups check one agent at a time, parallel groups check all agents.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a way to retrieve all active agents in the current group when the group's execution mode is "parallel", returning the full list of agents rather than only the first agent.
- **FR-002**: System MUST fall back to returning a single-element list containing only the current agent when the group's execution mode is "sequential" or when no groups are configured.
- **FR-003**: System MUST correctly detect sequential group completion by comparing the current agent index within the group against the total number of agents in that group.
- **FR-004**: System MUST check completion status for every agent in a parallel group during each polling cycle, not just the first agent.
- **FR-005**: System MUST advance each completed parallel agent individually while leaving non-completed agents running.
- **FR-006**: System MUST only advance the pipeline to the next group once all agents in a parallel group have reached a terminal state (completed or failed).
- **FR-007**: System MUST reassign all unassigned agents in a parallel group during the recovery path after state reconstruction, not just the first agent.
- **FR-008**: System MUST preserve existing sequential pipeline behavior — no changes to how sequential agents or sequential groups are processed.
- **FR-009**: System MUST skip empty groups (groups with no agents) without errors during both normal polling and recovery.
- **FR-010**: System MUST NOT modify the initial launch stagger behavior (intentional rate-limit protection) when dispatching parallel agents for the first time.

### Key Entities

- **PipelineState**: Tracks per-issue pipeline progress. Key attributes: groups (ordered list of execution groups), current group index, current agent index within group, execution mode, parallel agent statuses, completed/failed agent lists.
- **PipelineGroupInfo**: Defines a single execution group within a pipeline. Key attributes: list of agent names, execution mode (sequential or parallel), per-agent status tracking.
- **Polling Loop**: Periodic process (60-second cycle) that checks agent completion and advances pipeline state. Interacts with PipelineState to determine which agents to check.
- **Recovery Path**: Fallback logic that detects and reassigns agents that were never assigned (e.g., after a service restart). Uses tracking table and in-memory pending assignment cache for deduplication.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When a pipeline with a parallel group of N agents is triggered, all N agents show 🔄 Active status simultaneously within a single polling cycle (not spread across N cycles).
- **SC-002**: Pipeline total execution time for a parallel group of 3 agents is approximately equal to the slowest agent's duration (not the sum of all 3 agents' durations).
- **SC-003**: Sequential group completion is correctly detected 100% of the time — no false "incomplete" signals after all agents in a sequential group have been processed.
- **SC-004**: After a service restart during a parallel stage, 100% of unassigned parallel agents are recovered and reassigned within a single recovery cycle.
- **SC-005**: All existing pipeline tests continue to pass with zero regressions — sequential pipeline behavior is unchanged.
- **SC-006**: The fix resolves the previously reported symptoms where the G2 parallel group showed 1 Active + 2 Pending instead of all 3 Active.

## Assumptions

- The existing `_advance_pipeline` method correctly handles individual agent advancement within parallel groups (marks individual agents done, advances group index only when all are terminal). No changes are needed to this method.
- The initial launch stagger (`asyncio.sleep(2)`) in `execute_full_workflow` is intentional rate-limit protection and is not a bug to be fixed.
- The `determine_next_action` logic in `agent_tracking.py` is a separate, lower-priority recovery path that is out of scope for this fix.
- The existing parallel agent status tracking (via `parallel_agent_statuses` and `PipelineGroupInfo.agent_statuses`) provides sufficient state information; no new state fields are required.
- Empty groups (groups with zero agents) should be silently skipped during iteration, consistent with existing behavior in the `current_agent` property.
