# Feature Specification: Human Agent — Delay Until Auto-Merge

**Feature Branch**: `001-human-agent-delay-until-auto-merge`  
**Created**: 2026-04-04  
**Status**: Draft  
**Input**: User description: "Extend the existing Human agent node with an optional 'Delay until auto-merge' config. When set (n seconds), the pipeline creates the human sub-issue, waits the configured duration, then auto-merges the parent PR. When unset, current behavior — pipeline pauses until the user manually closes the sub-issue or comments 'Done!'."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Configure Delay on Human Agent Node (Priority: P1)

A pipeline owner wants to add a timed review window to a Human agent step. They open the pipeline board, select the Human agent node, and enable "Delay until auto-merge." They enter the number of seconds they want the pipeline to wait before automatically merging. After saving, the pipeline stores this setting and uses it during the next execution.

**Why this priority**: This is the core configuration capability. Without the ability to set a delay, no other behavior in this feature can function. It is the foundational interaction that all other stories depend on.

**Independent Test**: Can be fully tested by opening a pipeline board with a Human agent node, toggling the delay setting on, entering a value, and confirming the value persists after save. Delivers value by allowing users to configure the feature end-to-end.

**Acceptance Scenarios**:

1. **Given** a pipeline with a Human agent node and the delay toggle is off, **When** the user enables "Delay until auto-merge" and enters 300 seconds, **Then** the node config stores `delay_seconds: 300` and displays a badge reading "⏱️ Auto-merge: 5m."
2. **Given** a pipeline with a Human agent node that has `delay_seconds: 300`, **When** the user disables the "Delay until auto-merge" toggle, **Then** `delay_seconds` is removed from the config and the badge reads "Manual review."
3. **Given** a pipeline with a Human agent node, **When** the user enters a value of 0 or a negative number, **Then** the system prevents the invalid value from being saved and displays a validation message.
4. **Given** a pipeline with a Human agent node, **When** the user enters a value exceeding 86400 seconds (24 hours), **Then** the system prevents the invalid value from being saved and displays a validation message.
5. **Given** a pipeline with a non-Human agent node, **When** the user views that agent's configuration, **Then** no "Delay until auto-merge" toggle or input is displayed.

---

### User Story 2 — Pipeline Executes Delay Then Auto-Merges (Priority: P1)

A pipeline owner has configured a Human agent node with a 5-minute delay. When the pipeline reaches the Human step, it creates a sub-issue for the reviewer (preserving the audit trail), posts a comment indicating the auto-merge countdown, waits 5 minutes, and then automatically merges the parent pull request. The sub-issue is closed after the merge completes.

**Why this priority**: This is the core runtime behavior and the primary value proposition of the feature. The timed grace period replaces the current all-or-nothing approach where auto-merge either skips the Human step entirely (no review window) or requires manual intervention.

**Independent Test**: Can be fully tested by configuring a Human agent with a short delay (e.g., 30 seconds), triggering a pipeline run, and observing that the sub-issue is created, the countdown comment is posted, the wait completes, and auto-merge is triggered. Delivers value by providing a review window with automatic progression.

**Acceptance Scenarios**:

1. **Given** a pipeline with a Human agent configured with `delay_seconds: 300`, **When** the pipeline reaches the Human step, **Then** a sub-issue is created (assigned to the issue creator), a comment "⏱️ Auto-merge in 5m" is posted on the sub-issue, and the pipeline enters a waiting state.
2. **Given** the pipeline is in the delay-waiting state, **When** the configured delay period expires, **Then** the system triggers the auto-merge process for the parent pull request, closes the sub-issue, and advances the pipeline to the next step.
3. **Given** a pipeline with a Human agent configured with `delay_seconds: 300` and the sub-issue body, **When** the sub-issue is created, **Then** the body includes "⏱️ Auto-merge in 5m. Close early to skip."

---

### User Story 3 — Early Cancellation by Closing the Sub-Issue (Priority: P2)

A reviewer receives a sub-issue created by the Human agent delay step. After reviewing the changes, they close the sub-issue before the delay timer expires. The pipeline detects the early closure and proceeds immediately with auto-merge instead of waiting for the full delay to elapse.

**Why this priority**: Early cancellation significantly improves the user experience for reviewers who complete their review before the timer runs out. Without it, reviewers would be forced to wait for the full delay even after finishing their review.

**Independent Test**: Can be fully tested by configuring a Human agent with a long delay (e.g., 600 seconds), triggering a pipeline run, then closing the sub-issue after 30 seconds. Verify the pipeline proceeds immediately. Delivers value by eliminating unnecessary wait time.

**Acceptance Scenarios**:

1. **Given** the pipeline is waiting during a configured delay period, **When** the reviewer closes the sub-issue before the delay expires, **Then** the pipeline detects the closure within 15 seconds (the polling interval) and proceeds immediately with auto-merge.
2. **Given** the pipeline is waiting during a configured delay period, **When** the reviewer comments "Done!" on the sub-issue before the delay expires, **Then** the pipeline detects the comment within 15 seconds and proceeds immediately with auto-merge.

---

### User Story 4 — Manual Review Behavior Preserved (Priority: P2)

A pipeline owner has a Human agent node with no delay configured (the default). When the pipeline reaches the Human step, it creates a sub-issue and pauses indefinitely until the reviewer manually closes the sub-issue or comments "Done!" This is identical to the existing behavior before this feature was introduced.

**Why this priority**: Backward compatibility is essential. Existing pipelines that rely on manual human review must continue to work identically. Any regression in this behavior would break production workflows.

**Independent Test**: Can be fully tested by running a pipeline with a Human agent that has no `delay_seconds` configured and verifying the pipeline pauses until manual intervention. Delivers value by ensuring existing workflows are unaffected.

**Acceptance Scenarios**:

1. **Given** a pipeline with a Human agent that does NOT have `delay_seconds` configured, **When** the pipeline reaches the Human step, **Then** a sub-issue is created and the pipeline pauses indefinitely until the sub-issue is closed or "Done!" is commented.
2. **Given** a pipeline with auto-merge enabled, a Human agent as the last step, and NO `delay_seconds` configured, **When** the pipeline reaches the Human step, **Then** the existing skip-and-auto-merge behavior is preserved (Human step is skipped entirely).

---

### User Story 5 — Tracking Table Displays Delay Status (Priority: P3)

A user viewing the pipeline tracking table sees clear status information for Human agent steps that are in a delay-waiting state. The tracking display shows a timer icon and the configured delay duration, distinguishing it from a standard manual-wait Human step.

**Why this priority**: Observability is important for pipeline operators but is a polish item. The core feature functions without it, but it helps users understand what is happening during the delay period.

**Independent Test**: Can be fully tested by triggering a pipeline with a delay-configured Human agent and checking the tracking table output for the expected status format. Delivers value by giving operators at-a-glance delay status.

**Acceptance Scenarios**:

1. **Given** a Human agent is in the delay-waiting state with `delay_seconds: 300`, **When** the tracking table is rendered, **Then** the Human agent row displays "⏱️ Delay (5m)."
2. **Given** a Human agent is in the standard manual-wait state (no delay configured), **When** the tracking table is rendered, **Then** the Human agent row displays the existing manual-wait status.

---

### Edge Cases

- What happens when the delay expires but the auto-merge fails (e.g., merge conflicts, failing CI checks)?  
  **Assumed behavior**: The existing `_attempt_auto_merge` function already handles merge failures gracefully (logs the error, does not crash the pipeline). The pipeline proceeds to the next step regardless of merge outcome. This matches the current auto-merge behavior.

- What happens when the delay is set to the minimum value (1 second)?  
  **Assumed behavior**: The system creates the sub-issue, waits at most one polling interval (15 seconds), then triggers auto-merge. The actual wait time may be up to 15 seconds due to polling granularity.

- What happens when the delay is set to the maximum value (86400 seconds / 24 hours)?  
  **Assumed behavior**: The system polls every 15 seconds for up to 24 hours. This results in up to 5,760 polling cycles. The system handles this gracefully since each cycle is a lightweight check.

- What happens when the pipeline is restarted during an active delay period?  
  **Assumed behavior**: Pipeline state is reconstructed from the current step. If the Human agent step is the current step and has a delay configured, the delay starts fresh. Previous elapsed time is not preserved.

- What happens when multiple Human agents in the same pipeline each have different delay values?  
  **Assumed behavior**: Each Human agent operates independently with its own configured delay. The delay applies per-agent, not per-pipeline.

- What happens when the GitHub API is temporarily unreachable during the polling loop?  
  **Assumed behavior**: The existing polling infrastructure handles transient API failures. A single failed poll does not terminate the delay loop; the next polling interval retries.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow pipeline owners to configure an optional `delay_seconds` value on any Human agent node in the pipeline.
- **FR-002**: The `delay_seconds` value MUST be an integer in the range [1, 86400] (1 second to 24 hours). Values outside this range MUST be rejected.
- **FR-003**: The "Delay until auto-merge" configuration option MUST only be available on Human agent nodes (agent_slug === "human"). It MUST NOT appear on other agent types.
- **FR-004**: When `delay_seconds` is configured and the pipeline reaches the Human step, the system MUST create a sub-issue assigned to the issue creator (preserving the audit trail).
- **FR-005**: When `delay_seconds` is configured, the sub-issue body MUST include a message indicating the auto-merge countdown and instructions for early cancellation (e.g., "⏱️ Auto-merge in {duration}. Close early to skip.").
- **FR-006**: When `delay_seconds` is configured, the system MUST post a comment on the sub-issue indicating the auto-merge countdown (e.g., "⏱️ Auto-merge in {formatted_duration}").
- **FR-007**: After the configured delay expires, the system MUST trigger the auto-merge process for the parent pull request.
- **FR-008**: During the delay period, the system MUST poll every 15 seconds to check if the sub-issue has been closed or a "Done!" comment has been posted.
- **FR-009**: If the sub-issue is closed or "Done!" is commented before the delay expires, the system MUST proceed immediately with auto-merge without waiting for the remaining delay.
- **FR-010**: After auto-merge is triggered (whether by delay expiration or early cancellation), the system MUST close the sub-issue and advance the pipeline to the next step.
- **FR-011**: When `delay_seconds` is NOT configured on a Human agent node, the system MUST preserve existing behavior: the pipeline pauses until the reviewer manually closes the sub-issue or comments "Done!"
- **FR-012**: When `delay_seconds` is NOT configured, auto-merge is active, and the Human agent is the last step, the system MUST preserve the existing skip-and-auto-merge behavior.
- **FR-013**: The Human agent node in the pipeline board MUST display a badge indicating the current mode: "⏱️ Auto-merge: {formatted_duration}" when delay is configured, or "Manual review" when it is not.
- **FR-014**: The pipeline tracking table MUST display "⏱️ Delay ({formatted_duration})" for Human agents in the delay-waiting state.
- **FR-015**: The `delay_seconds` configuration MUST be stored in the existing `PipelineAgentNode.config` dictionary. No database schema migration is required.

### Key Entities

- **PipelineAgentNode**: Represents an agent step in a pipeline. Contains a `config` dictionary that stores agent-specific settings. For Human agents, this dictionary may include `delay_seconds` (integer, optional).
- **Human Sub-Issue**: A GitHub issue created when the pipeline reaches a Human agent step. Serves as the audit trail and communication channel between the pipeline and the reviewer. When delay is configured, the sub-issue body includes auto-merge timing information and early cancellation instructions.
- **Pipeline State**: Runtime state of an executing pipeline. Extended with `agent_configs` mapping (agent_slug → config dict) so the execution loop can access `delay_seconds` without re-querying configuration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Pipeline owners can configure a delay value on a Human agent node and have the pipeline automatically merge after the specified duration, 100% of the time when no merge conflicts or CI failures exist.
- **SC-002**: Reviewers who close the sub-issue early experience pipeline progression within 15 seconds of closure (the polling interval), eliminating unnecessary wait time.
- **SC-003**: Existing pipelines with Human agents and no delay configured continue to operate identically to pre-feature behavior, with zero regressions in manual-review workflows.
- **SC-004**: Pipeline operators can determine whether a Human agent step is in delay-wait mode or manual-wait mode at a glance from the tracking table and pipeline board, reducing status ambiguity.
- **SC-005**: Invalid delay configurations (values outside [1, 86400], non-integer values, or delay on non-Human agents) are rejected before pipeline execution, preventing runtime errors.

### Assumptions

- The existing `PipelineAgentNode.config` dictionary is the appropriate storage location for `delay_seconds`. No schema migration is needed.
- The existing `_attempt_auto_merge()` function handles all auto-merge complexity (CI checks, mergeability, squash merge) and does not need modification.
- The 15-second polling interval (matching the existing polling loop cadence) provides acceptable granularity for early cancellation detection.
- Pipeline restarts during an active delay period result in the delay starting fresh (elapsed time is not preserved).
- The delay feature applies to any Human agent in the pipeline, regardless of its position (not just the last step).
- The maximum delay of 24 hours (86400 seconds) is sufficient for all practical review windows.
- Duration formatting follows human-readable conventions (e.g., 300s → "5m", 3600s → "1h", 90s → "1m 30s").
