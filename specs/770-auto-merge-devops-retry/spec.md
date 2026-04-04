# Feature Specification: Auto-Merge After All Agents Complete + CI Pass + DevOps Retry

**Feature Branch**: `copilot/speckit-plan-auto-merge-implementation`  
**Created**: 2026-04-04  
**Status**: Draft  
**Input**: User description: "Auto-Merge After All Agents Complete + CI Pass + DevOps Retry — close three gaps: DevOps agent definition, post-DevOps re-merge trigger, and webhook handler wiring"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pipeline Auto-Merges After All Agents Complete and CI Passes (Priority: P1)

As a project maintainer using the automated agent pipeline, I want the system to automatically squash-merge the parent pull request once all agents have completed their work and all CI checks pass, so that completed features are merged without manual intervention.

**Why this priority**: This is the core value proposition — hands-free merge after pipeline completion. Without this working end-to-end, the pipeline requires manual merge steps which defeats automation. This story represents the happy-path that all other stories build upon.

**Independent Test**: Can be fully tested by triggering a pipeline where all agents complete successfully and CI passes. The parent PR should transition from draft to ready-for-review and be squash-merged automatically, with the issue marked as "Done".

**Acceptance Scenarios**:

1. **Given** all agents in a pipeline have completed their work and the issue is transitioned to "In Review", **When** the system detects pipeline completion, **Then** the parent PR is converted from draft to ready-for-review and squash-merged within 5 minutes of CI passing.
2. **Given** CI checks are still pending after pipeline completion, **When** the system polls for CI status, **Then** it retries up to 3 times with increasing wait periods (approximately 60s, 120s, 240s) before escalating.
3. **Given** the parent PR is successfully merged, **When** the merge completes, **Then** the issue status is updated to "Done" and a summary comment is posted on the issue.

---

### User Story 2 - DevOps Agent Resolves CI Failures and Merge Conflicts (Priority: P1)

As a project maintainer, I want the system to automatically dispatch a DevOps agent when CI fails or merge conflicts are detected during auto-merge, so that common blockers are resolved without my involvement.

**Why this priority**: Without the DevOps agent, CI failures and merge conflicts stall the pipeline permanently. This is the critical failure-recovery path — equally important to the happy-path since CI failures are common in real-world development.

**Independent Test**: Can be tested by triggering a pipeline where CI deliberately fails (e.g., a linting error). The system should dispatch the DevOps agent, which diagnoses the failure, pushes a fix, and signals completion.

**Acceptance Scenarios**:

1. **Given** auto-merge detects a CI failure on the parent PR, **When** the failure is identified, **Then** a DevOps agent is dispatched with context about which checks failed and why.
2. **Given** a DevOps agent has been dispatched for a CI failure, **When** the agent is already active for the same issue, **Then** a duplicate dispatch is prevented (deduplication).
3. **Given** a DevOps agent has been dispatched, **When** the agent completes its work and signals "Done!", **Then** the system re-attempts the auto-merge process.
4. **Given** the DevOps agent fails to resolve the issue after 2 attempts, **When** the cap is reached, **Then** the system stops retrying, broadcasts a failure notification, and leaves the issue in "In Review" for human intervention.

---

### User Story 3 - CI Events Proactively Trigger Merge and Recovery (Priority: P2)

As a project maintainer, I want CI completion and failure events to proactively trigger merge attempts or DevOps recovery, so that the system responds immediately to CI status changes rather than relying solely on periodic polling.

**Why this priority**: Webhook-driven triggers provide a faster response path compared to polling alone. While the polling fallback (Story 4) ensures resilience, webhooks significantly reduce the time between CI completion and merge, improving the user experience.

**Independent Test**: Can be tested by simulating a CI `check_suite` success event for a PR associated with an auto-merge issue. The system should immediately attempt to merge. Similarly, a `check_run` failure event should trigger DevOps dispatch.

**Acceptance Scenarios**:

1. **Given** a `check_suite` event indicates all CI checks passed for a PR linked to an auto-merge issue, **When** the webhook is received, **Then** the system immediately re-attempts auto-merge for the associated issue.
2. **Given** a `check_run` event indicates a CI check failed for a PR linked to an auto-merge issue, **When** the webhook is received, **Then** the system dispatches a DevOps agent with the failure context (check name, failure reason, logs).
3. **Given** a CI event is received for a PR not associated with any auto-merge issue, **When** the webhook handler processes it, **Then** no action is taken and the event is logged and ignored gracefully.

---

### User Story 4 - System Recovers After Restart or Webhook Loss (Priority: P2)

As a project maintainer, I want the system to recover and continue the auto-merge process even after a server restart or missed webhook, so that no pipeline gets permanently stuck in "In Review" status.

**Why this priority**: Server restarts and webhook delivery failures are inevitable in production. Without a resilient polling fallback, issues can become permanently stalled, requiring manual intervention and undermining trust in the automation.

**Independent Test**: Can be tested by simulating a server restart while a DevOps agent is active. After restart, the periodic review of "In Review" issues should detect the DevOps "Done!" signal and re-attempt merge.

**Acceptance Scenarios**:

1. **Given** an issue is in "In Review" with auto-merge enabled and no active pipeline, **When** the periodic review cycle runs, **Then** the system checks for DevOps completion signals and re-attempts merge if appropriate.
2. **Given** a DevOps agent completed its work during a server outage and posted "Done!", **When** the server restarts and the polling fallback runs, **Then** the system detects the completion and proceeds with auto-merge.
3. **Given** an issue has been in "In Review" with no progress for an extended period, **When** the polling fallback detects a stale state, **Then** the system re-evaluates the issue's CI status and takes appropriate action (re-merge or re-dispatch DevOps).

---

### User Story 5 - Failure Notifications for Unrecoverable Issues (Priority: P3)

As a project maintainer, I want to receive clear notifications when the auto-merge pipeline cannot recover automatically, so that I know exactly which issues require my attention and why.

**Why this priority**: While lower than the recovery stories, clear failure communication is essential for maintainer trust. Without it, maintainers cannot distinguish between "in progress" and "permanently stuck" pipelines.

**Independent Test**: Can be tested by exhausting DevOps retry attempts (2 failures). The system should post a clear failure message on the issue explaining what was tried and what failed.

**Acceptance Scenarios**:

1. **Given** the DevOps agent has failed to resolve CI issues after 2 attempts, **When** the retry cap is reached, **Then** a failure notification is broadcast and a comment is posted on the issue explaining the situation.
2. **Given** auto-merge has failed after all retry attempts, **When** no further automated recovery is possible, **Then** the issue remains in "In Review" with a clear indication that human intervention is required.

---

### Edge Cases

- What happens when multiple CI `check_run` failure events arrive simultaneously for the same PR? The system must deduplicate DevOps dispatches to prevent multiple agents working on the same failure.
- How does the system handle a DevOps agent that becomes unresponsive and never posts "Done!"? A maximum polling window (approximately 1 hour) should prevent indefinite waiting.
- What happens when CI passes but the branch has a merge conflict that was not present when the pipeline started? The merge attempt should fail gracefully and dispatch DevOps to resolve the conflict.
- What happens when a webhook event arrives for a PR whose associated issue has already been marked "Done"? The handler should check issue status and skip already-completed issues.
- What happens if the DevOps agent pushes a fix that causes a different CI failure? The system should treat it as a new failure and count it toward the DevOps retry cap.
- What happens when two webhooks (check_suite success + check_run failure) arrive in quick succession with conflicting signals? The system should use the most recent overall CI status rather than acting on individual events in isolation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST automatically attempt to squash-merge the parent PR when all pipeline agents have completed and the issue transitions to "In Review".
- **FR-002**: System MUST convert the parent PR from draft to ready-for-review before attempting the merge.
- **FR-003**: System MUST retry the merge up to 3 times with exponential backoff (approximately 60s, 120s, 240s) when CI checks are still pending.
- **FR-004**: System MUST dispatch a DevOps agent when CI checks fail or merge conflicts are detected during auto-merge.
- **FR-005**: System MUST provide the DevOps agent with contextual information about the failure, including which checks failed, failure reasons, and relevant log excerpts.
- **FR-006**: System MUST prevent duplicate DevOps agent dispatches for the same issue (deduplication guard).
- **FR-007**: System MUST cap DevOps agent retry attempts at 2 per issue and stop automated recovery when the cap is reached.
- **FR-008**: System MUST re-attempt auto-merge after the DevOps agent signals completion by posting a "Done!" comment.
- **FR-009**: System MUST schedule a polling mechanism (at approximately 120-second intervals) to detect DevOps agent completion, providing resilience against webhook delivery failures.
- **FR-010**: System MUST limit the post-DevOps polling window to a maximum of approximately 30 polling cycles to prevent indefinite resource consumption.
- **FR-011**: System MUST handle `check_suite` completion events by re-attempting auto-merge when all CI checks pass for PRs linked to auto-merge issues.
- **FR-012**: System MUST handle `check_run` failure events by dispatching the DevOps agent with failure context for PRs linked to auto-merge issues.
- **FR-013**: System MUST include a periodic review of issues stuck in "In Review" status to recover from server restarts and missed webhooks.
- **FR-014**: System MUST broadcast real-time notifications for key state changes: DevOps dispatch, successful merge, and unrecoverable failure.
- **FR-015**: System MUST update the issue status to "Done" after a successful merge and post a summary comment.
- **FR-016**: System MUST gracefully skip webhook events for PRs not associated with any auto-merge issue.
- **FR-017**: System MUST include the DevOps agent in the registry of available built-in agents so it can be discovered and dispatched through the standard agent orchestration flow.

### Key Entities

- **DevOps Agent**: A built-in agent specialized in diagnosing CI failures, resolving merge conflicts, and pushing fixes to PR branches. Dispatched automatically when the auto-merge process encounters blockers. Defined as a template with a persona, capabilities, and workflow instructions.
- **Auto-Merge Result**: The outcome of a merge attempt, carrying status (merged, retry needed, DevOps needed, failed), PR number, merge commit reference, and error details. Used to determine next actions in the pipeline.
- **Post-DevOps Retry State**: Tracks active polling sessions waiting for DevOps agent completion. Contains the issue context, polling count, and dispatch timestamp. Bounded to prevent unbounded memory growth.
- **Pipeline Metadata (DevOps Fields)**: Extension of existing pipeline metadata to track DevOps state: whether a DevOps agent is currently active, how many attempts have been made, and whether auto-merge is enabled for the issue.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When all pipeline agents complete and CI passes, the parent PR is automatically merged within 5 minutes of the last CI check completing, with zero manual intervention required.
- **SC-002**: When CI fails during auto-merge, the DevOps agent is dispatched within 30 seconds of failure detection and receives accurate failure context.
- **SC-003**: After the DevOps agent resolves a CI failure and signals completion, the system re-attempts merge within 3 minutes (accounting for polling interval).
- **SC-004**: The system successfully recovers from a server restart and resumes pending auto-merge workflows within one polling cycle of restart.
- **SC-005**: Webhook-triggered merge attempts respond within 2 seconds of event receipt, ensuring the user-facing experience remains responsive.
- **SC-006**: When the DevOps agent exhausts its 2-attempt cap, a clear failure notification reaches the maintainer within 1 minute.
- **SC-007**: Duplicate DevOps dispatches are prevented with 100% reliability — no issue ever has more than one active DevOps agent at a time.
- **SC-008**: The end-to-end happy path (all agents complete → CI passes → auto-merge) succeeds on the first attempt at least 90% of the time in normal conditions.
- **SC-009**: The end-to-end recovery path (CI fails → DevOps fixes → re-merge) completes within 10 minutes of the initial failure, assuming a single DevOps attempt is sufficient.
