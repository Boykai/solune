# Feature Specification: Fix App Building Project Recovery

**Feature Branch**: `001-fix-app-building-recovery`  
**Created**: 2026-04-15  
**Status**: Draft  
**Input**: User description: "Fix App Building Project Recovery — App building projects (new-repo) fail recovery across all three scenarios (restart, project selection, normal operation) because _launch_phase_pipelines() doesn't forward target_repo to execute_pipeline_launch()."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - App Pipeline Launches Target the Correct Repository (Priority: P1)

When a user creates a new app that lives in a separate repository (e.g., "colove"), the system launches development pipelines. These pipelines must create their parent issues, sub-issues, and polling tasks on the **app's own repository** — not on the default/main repository. Today the repository information is lost during the pipeline launch step, causing issues to be created in the wrong place and scoped polling to never start.

**Why this priority**: This is the root cause of the failure. Without forwarding the target repository to the pipeline launch function, every downstream recovery path also breaks. Fixing this one problem restores correct behavior during normal (non-recovery) operation and is the prerequisite for the other two fixes.

**Independent Test**: Can be fully tested by launching an app-building pipeline for a cross-repo project and verifying that the pipeline launch receives the correct target repository, scoped polling is activated, and the pipeline state records the correct repository owner and name.

**Acceptance Scenarios**:

1. **Given** a user initiates app creation targeting a new external repository (e.g., owner="Boykai", repo="colove"), **When** the system launches phase pipelines, **Then** each pipeline launch call receives the target repository (owner, repo) so parent issues are created on the correct repository.
2. **Given** a pipeline is launched with a target repository specified, **When** the pipeline start logic evaluates scoped polling, **Then** scoped app-pipeline polling is activated (use_app_scoped_polling=True) because target_repo is present.
3. **Given** a pipeline is launched with a target repository specified, **When** the pipeline state is persisted, **Then** the state records the correct repository_owner and repository_name values.

---

### User Story 2 - Pipeline State Preserves Repository Info After Reconstruction (Priority: P2)

When the system restarts and needs to reconstruct pipeline state from stored data (issue comments, tracking tables), the reconstructed pipeline state must include the repository owner and name. Without this information, the system cannot determine whether a pipeline belongs to a cross-repo app and cannot restore scoped polling.

**Why this priority**: Reconstruction is the first thing that happens after a restart. If repository information is lost during reconstruction, even a correct launch (from Story 1) cannot survive a container restart because the recovery logic has no way to identify which repo the pipeline belongs to.

**Independent Test**: Can be fully tested by invoking the pipeline state reconstruction function with known owner/repo values and verifying the resulting PipelineState object has repository_owner and repository_name populated.

**Acceptance Scenarios**:

1. **Given** a pipeline was originally created for a cross-repo app (owner="Boykai", repo="colove"), **When** the system reconstructs the pipeline state from issue comments after a restart, **Then** the reconstructed PipelineState contains the correct repository_owner and repository_name.
2. **Given** a pipeline was originally created for a same-repo app (matching the default repository), **When** the system reconstructs the pipeline state, **Then** the reconstructed PipelineState still records the default repository_owner and repository_name (preserving consistency).

---

### User Story 3 - Project Selection Restores App-Pipeline Polling (Priority: P3)

When a user selects a project from the project list (e.g., switching between projects), the system starts standard Copilot polling for that project. However, if the selected project has active cross-repo app pipelines, the system must also restore scoped app-pipeline polling for those pipelines. Today, selecting a project does not check for or restore app-pipeline polling.

**Why this priority**: This scenario affects users who switch between projects during an active app build. While less common than a full restart (Story 2), it still causes cross-repo pipelines to silently stop being monitored, leading to stalled builds that require manual intervention.

**Independent Test**: Can be fully tested by selecting a project that has active cross-repo pipeline states and verifying that scoped app-pipeline polling tasks are started for each matching pipeline.

**Acceptance Scenarios**:

1. **Given** a project has active (non-complete) pipeline states for a cross-repo app, **When** a user selects that project, **Then** the system starts scoped app-pipeline polling for each cross-repo pipeline in a fire-and-forget manner.
2. **Given** a project has only same-repo pipeline states (matching the default repository), **When** a user selects that project, **Then** no additional scoped polling is started (same-repo pipelines are handled by the main polling loop).
3. **Given** a project has no active pipeline states, **When** a user selects that project, **Then** no app-pipeline restoration logic runs and no errors occur.

---

### Edge Cases

- What happens when the target repository has been deleted or the user no longer has access? The pipeline launch should fail gracefully with an error logged, and the orchestration should report the failure rather than silently creating issues on the wrong repo.
- What happens when multiple cross-repo pipelines exist for the same project? Each pipeline should get its own independent scoped polling task keyed by project_id, consistent with the existing ensure_app_pipeline_polling deduplication logic.
- What happens when a pipeline state is reconstructed but the original issue has been deleted from GitHub? The reconstruction function already handles this gracefully (returns an empty-agent pipeline that is not cached); the repository fields should still be populated on the returned state.
- What happens when a user selects a project during an in-progress pipeline launch? The standard Copilot polling restarts (existing behavior), and the app-pipeline restoration runs independently in a fire-and-forget task, so there is no conflict.
- What happens when the pipeline state store contains entries with empty repository_owner/repository_name from before this fix? The existing self-healing backfill logic in the restart recovery path resolves the repo via the GitHub API and patches the state. This fix ensures new entries are correct from the start.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST forward the target repository (owner, repo) from the app creation orchestrator to each pipeline launch call so that parent issues and sub-issues are created on the correct repository.
- **FR-002**: System MUST ensure that when a target repository is provided during pipeline launch, scoped app-pipeline polling is activated for that pipeline.
- **FR-003**: System MUST populate repository_owner and repository_name on the PipelineState when reconstructing pipeline state from issue comments, using the owner and repo values already available to the reconstruction function.
- **FR-004**: System MUST restore scoped app-pipeline polling for active cross-repo pipelines when a user selects a project, mirroring the existing restart recovery logic but scoped to the selected project.
- **FR-005**: System MUST NOT start additional scoped polling for same-repo pipelines (those matching the default repository), as these are handled by the main polling loop.
- **FR-006**: System MUST perform app-pipeline restoration during project selection as a fire-and-forget background task so that the project selection response is not delayed.
- **FR-007**: System MUST log informational messages when scoped polling is restored during project selection, consistent with the existing restart recovery logging pattern.

### Key Entities

- **PipelineState**: Represents the current state of a development pipeline. Key attributes: issue_number, project_id, status, agents, repository_owner, repository_name, is_complete. The repository_owner and repository_name fields identify which GitHub repository the pipeline's issues live on.
- **Orchestration**: Represents an app creation workflow. Contains app_name, project_id, owner, repo, and orchestration steps (spec generation, plan parsing, issue creation, pipeline launching). The owner/repo values from orchestration must flow through to each pipeline launch.
- **App-Pipeline Polling Task**: A scoped background task that monitors a specific cross-repo pipeline. Keyed by project_id to prevent duplicates. Automatically stops when the pipeline completes.

## Assumptions

- The `orchestrate_app_creation` function already has correct `owner` and `repo` values available — no new data source or lookup is needed; the fix is purely about forwarding these values.
- The `_reconstruct_pipeline_state` function signature already includes `owner` and `repo` parameters — the fix is about using them when constructing the PipelineState, not about obtaining them.
- The `_restore_app_pipeline_polling()` function in main.py is the authoritative reference for how app-pipeline restoration should work — the new project-selection helper mirrors this pattern.
- Same-repo app pipelines continue to use the main polling loop. Only cross-repo app pipelines (where owner/repo differ from the default) require scoped polling.
- Pipeline state key collision (issue_number as primary key without repository qualifier) is out of scope for this feature. A separate follow-up with a data migration is recommended.
- Orchestration retry/resume logic for failed `orchestrate_app_creation` calls is a separate follow-up and not part of this fix.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of app-building pipelines targeting an external repository create their parent issues on the correct repository (zero misrouted issues).
- **SC-002**: After a container restart, all active cross-repo app pipelines resume scoped polling within one polling cycle (under 90 seconds).
- **SC-003**: When a user selects a project with active cross-repo pipelines, scoped polling is restored within 5 seconds of project selection completing.
- **SC-004**: Reconstructed pipeline states for cross-repo apps contain correct repository_owner and repository_name values in 100% of cases, eliminating the need for API-based self-healing lookups.
- **SC-005**: All existing automated tests continue to pass with no regressions — the fix is backward-compatible with same-repo pipeline workflows.
- **SC-006**: Zero user-reported incidents of app-building pipelines stalling due to issues being created on the wrong repository or scoped polling not starting.
