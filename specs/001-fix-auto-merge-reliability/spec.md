# Feature Specification: Fix Auto-Merge Reliability (4 Root Causes)

**Feature Branch**: `001-fix-auto-merge-reliability`
**Created**: 2026-04-06
**Status**: Draft
**Input**: User description: "Auto-merge fails when CI takes longer than the 7-minute retry window. Four root causes compound — the retry window is too short, pipeline state is removed before merge succeeds, the webhook fallback only checks L1 cache, and reconstructed pipelines lose the auto_merge flag."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Auto-Merge Succeeds After Slow CI (Priority: P1)

A developer enables auto-merge on their pull request and pushes code. The CI pipeline takes 10–15 minutes to complete all checks. After CI passes, the system automatically merges the pull request without manual intervention — regardless of how long CI took.

**Why this priority**: This is the core reliability fix. Today, auto-merge silently fails for any CI suite exceeding ~7 minutes, forcing developers to manually merge or re-trigger the process. Extending the retry budget is the highest-impact, lowest-risk change that directly addresses the most visible symptom.

**Independent Test**: Can be fully tested by creating a pipeline with auto-merge enabled and simulating CI completion after a delay longer than 7 minutes. Delivers immediate value — developers no longer see auto-merge failures on slow CI suites.

**Acceptance Scenarios**:

1. **Given** a pull request with auto-merge enabled and CI takes 12 minutes, **When** all CI checks pass, **Then** the system retries the merge within the extended retry window and the pull request is merged automatically.
2. **Given** a pull request with auto-merge enabled and CI takes 2 minutes, **When** all CI checks pass, **Then** the system merges the pull request on the first retry attempt (no regression for fast CI).
3. **Given** a pull request with auto-merge enabled and CI takes 20 minutes, **When** all CI checks pass, **Then** the system retries up to the maximum number of attempts over approximately 23 minutes before reporting a merge failure.

---

### User Story 2 - Auto-Merge Recovers After State Eviction (Priority: P2)

A developer has auto-merge enabled. The system temporarily loses the in-memory record of the pipeline's auto-merge status (due to cache eviction or a service restart). When a CI completion event arrives, the system recovers the auto-merge intent from persistent storage and proceeds with the merge.

**Why this priority**: Cache eviction and service restarts are common in production. Without recovery, auto-merge silently fails even when CI completes quickly. This story ensures resilience by adding a secondary lookup layer so that no auto-merge intent is lost.

**Independent Test**: Can be fully tested by simulating an L1 cache miss (clearing the in-memory cache) and then triggering a CI completion webhook. The system should recover the pipeline's auto-merge flag from persistent storage and proceed to merge.

**Acceptance Scenarios**:

1. **Given** a pipeline with auto-merge enabled whose in-memory state was evicted, **When** a CI completion event arrives, **Then** the system recovers the auto-merge intent from persistent storage and triggers the merge.
2. **Given** a pipeline with auto-merge enabled whose state was evicted from both in-memory and persistent storage, **When** a CI completion event arrives and the project has auto-merge enabled at the project level, **Then** the system still triggers the merge using the project-level setting.
3. **Given** a pipeline with auto-merge disabled at the project level and no stored pipeline state, **When** a CI completion event arrives, **Then** the system does not attempt an auto-merge.

---

### User Story 3 - Pipeline State Preserved During Retry (Priority: P2)

A developer's auto-merge attempt is deferred (CI still running, merge conflict detected but retryable, etc.). The system preserves the pipeline's state so that subsequent retry attempts and webhook events can still find and act on the auto-merge intent.

**Why this priority**: Without state preservation during retries, each retry attempt starts from scratch and cannot find the pipeline — causing silent failures. This is the root cause of the "state removed before merge succeeds" issue and must be fixed alongside the retry extension.

**Independent Test**: Can be fully tested by triggering a merge attempt that returns a "retry later" status and then verifying the pipeline state still exists in the cache for the next retry attempt.

**Acceptance Scenarios**:

1. **Given** an auto-merge attempt that returns "retry later", **When** the retry loop schedules the next attempt, **Then** the pipeline state remains available in the cache for the next attempt and for any incoming webhook events.
2. **Given** an auto-merge attempt that succeeds (merge completed), **When** the merge is finalized, **Then** the pipeline state is removed from the cache.
3. **Given** an auto-merge attempt that fails permanently (non-retryable error), **When** the failure is recorded, **Then** the pipeline state is removed from the cache.
4. **Given** the retry loop encounters an unexpected error mid-retry, **When** the error is caught, **Then** the pipeline state is still cleaned up to prevent state leaks.

---

### User Story 4 - Existing Auto-Merge Behavior Preserved (Priority: P3)

All existing auto-merge workflows (fast CI, immediate merge, manual merge override, auto-merge disabled) continue to work exactly as they do today. No regressions are introduced for pipelines that do not experience slow CI or state eviction.

**Why this priority**: Regression prevention is critical. The system has ~40 existing auto-merge tests covering happy paths, edge cases, and failure modes. All must continue to pass after these changes.

**Independent Test**: Can be tested by running the full existing auto-merge test suite and verifying 100% pass rate with no behavioral changes for unaffected code paths.

**Acceptance Scenarios**:

1. **Given** a pipeline with auto-merge disabled, **When** CI completes, **Then** no merge is attempted (unchanged behavior).
2. **Given** a pipeline with auto-merge enabled and CI passes on the first attempt, **When** merge succeeds, **Then** the pipeline state is cleaned up and the pipeline transitions to Done (unchanged behavior).
3. **Given** all existing auto-merge tests, **When** the test suite runs after these changes, **Then** all existing tests pass without modification.

---

### Edge Cases

- What happens when the retry loop is mid-retry and the service restarts? The persistent storage fallback ensures the auto-merge intent is recoverable on the next webhook event.
- What happens when two webhook events arrive simultaneously for the same pull request? The existing locking mechanisms prevent duplicate merge attempts; the deferred removal ensures both events can find the pipeline state.
- What happens when a merge is retried but the pull request was closed or merged manually in the meantime? The merge attempt detects the already-merged or closed state and removes the pipeline state without error.
- What happens when the persistent storage fallback returns stale data for a pipeline that was intentionally cancelled? The project-level setting check acts as the final authority — if auto-merge is disabled at the project level, no merge is attempted regardless of stale state.
- What happens when the maximum retry count is exhausted? The system broadcasts a merge failure notification and cleans up the pipeline state.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST retry auto-merge attempts up to 5 times using exponential backoff, providing a total retry window of at least 23 minutes.
- **FR-002**: System MUST use a base retry delay of 45 seconds with exponential backoff (45s, 90s, 180s, 360s, 720s) to cover both fast and slow CI suites.
- **FR-003**: System MUST attempt to recover auto-merge pipeline state from persistent storage when the in-memory cache does not contain the pipeline for a given issue.
- **FR-004**: System MUST fall back to the project-level auto-merge setting when both in-memory and persistent storage lookups fail to find pipeline state.
- **FR-005**: System MUST NOT remove pipeline state from the cache when a merge attempt returns "retry later" — the state must remain available for subsequent retry attempts and webhook events.
- **FR-006**: System MUST remove pipeline state from the cache immediately when a merge attempt reaches a terminal outcome (merged, merge failed, or DevOps intervention needed).
- **FR-007**: System MUST remove pipeline state as a safety net when the retry loop exits due to an unexpected error, preventing state leaks.
- **FR-008**: System MUST preserve the existing behavior where pipeline state is removed immediately when auto-merge is not active for a pipeline.
- **FR-009**: System MUST pass all existing auto-merge tests without modification after these changes are applied.
- **FR-010**: System MUST correctly handle the auto-unregister logic (checking active pipeline count) only after pipeline state is removed, not before.

### Key Entities

- **Pipeline State**: Represents an active CI/CD pipeline for a pull request. Key attributes: issue number, project ID, auto-merge flag, current status, retry count. Relationship: belongs to a Project.
- **Auto-Merge Setting**: A project-level configuration that indicates whether pull requests in the project should be automatically merged after CI passes. Serves as the last-resort fallback when pipeline-specific state is unavailable.
- **Retry Budget**: The total time window and attempt count allocated for auto-merge retries. Defined by a maximum retry count and a base delay with exponential backoff.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Auto-merge succeeds for CI suites completing within 20 minutes, covering 95%+ of typical CI durations without manual intervention.
- **SC-002**: Auto-merge recovery succeeds within 5 seconds of a CI completion event, even when the in-memory cache has been cleared (e.g., after a service restart).
- **SC-003**: Zero auto-merge failures caused by premature state removal during the retry window — pipeline state remains available for the full duration of the retry loop.
- **SC-004**: 100% of existing auto-merge tests pass after these changes, with no regressions in merge behavior for fast CI suites (under 5 minutes).
- **SC-005**: The system cleans up all pipeline state within 60 seconds of a terminal merge outcome (success, failure, or DevOps escalation), preventing state leaks.
- **SC-006**: Auto-merge failure notifications are delivered to developers within 2 minutes of retry exhaustion, providing clear visibility into why the merge did not complete.

### Assumptions

- CI suite durations for the target environment typically range from 2 to 15 minutes, with rare outliers up to 20 minutes.
- The persistent storage layer is available and responsive during normal operation; transient storage failures are handled by existing error handling.
- The project-level auto-merge setting is the authoritative source of truth when pipeline-specific state is unavailable.
- Service restarts are infrequent (less than once per day) and do not coincide with the majority of auto-merge windows.
- The existing locking mechanisms are sufficient to prevent race conditions between concurrent webhook events and retry attempts.
