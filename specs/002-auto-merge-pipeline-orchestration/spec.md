# Feature Specification: Multi-Phase App Creation with Auto-Merge Pipeline Orchestration

**Feature Branch**: `002-auto-merge-pipeline-orchestration`  
**Created**: 2026-04-06  
**Status**: Draft  
**Input**: User description: "Multi-Phase App Creation with Auto-Merge Pipeline Orchestration — When a user creates a new app, Solune will: (1) generate an initial plan via the built-in chat plan agent, (2) launch speckit.plan as a Copilot coding agent to produce a detailed plan.md, (3) parse the phases from plan.md, (4) create one GitHub Parent Issue per phase with Agent Pipelines, (5) execute phases sequentially — each phase auto-merges to main before the next starts — so subsequent phases always branch from updated code."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Plan-Driven App Creation (Priority: P1)

A user opens the Solune app-creation dialog, provides a description of the app they want to build, and submits. The system automatically generates a structured implementation plan broken into phases, creates trackable issues for each phase, and begins executing Phase 1 — all without further user input.

**Why this priority**: This is the core value proposition. Without the ability to go from a description to a planned, phased execution, no other part of the feature delivers value.

**Independent Test**: Can be fully tested by submitting an app description and verifying that (a) a plan is generated, (b) phases are parsed, and (c) corresponding issues appear on the project board.

**Acceptance Scenarios**:

1. **Given** a user is on the app creation screen, **When** they enter an app description and submit, **Then** the system acknowledges the request within 5 seconds and begins planning in the background.
2. **Given** a plan has been generated, **When** the system parses the plan, **Then** it creates one parent issue per phase on the project board, ordered by dependency, each with a summary of the phase's scope and steps.
3. **Given** all phase issues are created, **When** the orchestration completes setup, **Then** the first wave of agent pipelines launches automatically for phases with no dependencies.

---

### User Story 2 — Sequential Phase Execution with Auto-Merge (Priority: P2)

Once Phase 1's agent pipeline completes and its pull request is merged to the main branch, the system automatically starts Phase 2 — which branches from the now-updated main so it builds on Phase 1's merged code. This continues until all phases are complete.

**Why this priority**: Auto-merge gating is what ensures each phase builds on the previous one's merged code, preventing merge conflicts and ensuring code coherence across phases. Without it, phases would be independent and potentially conflicting.

**Independent Test**: Can be tested by simulating two sequential phases: verify that Phase 2's pipeline only starts after Phase 1's pull request has been merged, and that Phase 2 branches from the updated main.

**Acceptance Scenarios**:

1. **Given** a phase's agent pipeline has completed and its pull request passes all checks, **When** auto-merge is triggered, **Then** the pull request is merged to the main branch automatically.
2. **Given** a phase has been merged to main, **When** the system checks the queue for the next phase, **Then** it starts only those phases whose prerequisite phases have all been merged.
3. **Given** multiple phases exist in the same dependency wave, **When** they have no inter-dependencies, **Then** they execute in parallel within that wave.
4. **Given** a phase's prerequisites have not all been merged, **When** the system evaluates whether to dequeue it, **Then** the phase remains queued and is re-evaluated after the next merge event.

---

### User Story 3 — Real-Time Planning Progress Visibility (Priority: P3)

While the system is planning and orchestrating, the user sees a live progress view showing each stage: plan generation, phase parsing, issue creation, and pipeline launches. Links to created issues appear as they are generated.

**Why this priority**: Transparency is important for user trust, but the orchestration itself works correctly without it. This story enhances the user experience without being a prerequisite for the core workflow.

**Independent Test**: Can be tested by initiating app creation and verifying that the progress view updates through each state transition and displays correct links to created issues.

**Acceptance Scenarios**:

1. **Given** app creation has been initiated, **When** the orchestration transitions between states (planning → phase parsing → issue creation → pipeline launch), **Then** the user sees the current state and a visual indicator of progress.
2. **Given** phase issues are being created, **When** each issue is created, **Then** a link to the new issue appears in the progress view within 5 seconds.
3. **Given** the orchestration encounters an error at any stage, **When** the error occurs, **Then** the user is shown a clear error message identifying which stage failed and what went wrong.

---

### User Story 4 — Dependency-Aware Wave Execution (Priority: P3)

Phases are grouped into "waves" based on their dependency relationships. All phases in Wave 1 (no dependencies) execute in parallel. Wave 2 phases (which depend on Wave 1 phases) only begin after their specific prerequisites are merged. This minimizes total execution time while respecting ordering constraints.

**Why this priority**: Wave-based parallelism is an optimization over strict sequential execution. The system delivers value with pure sequential execution; waves improve throughput for plans with independent phases.

**Independent Test**: Can be tested by creating a plan with at least three phases where Phase 1 and Phase 2 are independent (Wave 1) and Phase 3 depends on both. Verify Phases 1 and 2 run in parallel and Phase 3 starts only after both are merged.

**Acceptance Scenarios**:

1. **Given** a plan with phases that have no dependencies on each other, **When** the system creates pipelines, **Then** those phases are assigned to the same wave and launched simultaneously.
2. **Given** a plan with phases that depend on earlier phases, **When** the system creates pipelines, **Then** dependent phases are assigned to later waves and queued with prerequisite references.
3. **Given** a wave contains three phases and one fails, **When** the other two succeed, **Then** only the dependent phases whose specific prerequisites all succeeded are eligible to proceed.

---

### Edge Cases

- What happens when the plan agent generates a plan with zero parseable phases? The system should report an error to the user and halt orchestration gracefully.
- What happens when a phase's agent pipeline fails (e.g., agent times out, tests fail)? The system should mark the phase as failed, halt dependent phases, and notify the user with details on which phase failed and why.
- What happens when auto-merge fails due to merge conflicts? The system should notify the user, pause the pipeline queue, and provide guidance on resolving the conflict manually.
- What happens when the user creates multiple apps simultaneously? Each orchestration should operate independently with its own state, issues, and pipeline queue.
- What happens when the speckit.plan agent takes longer than expected (e.g., exceeds 30 minutes)? The system should enforce a timeout, report the failure, and allow the user to retry.
- What happens when the plan contains circular dependencies (Phase A depends on Phase B, Phase B depends on Phase A)? The system should detect the cycle during phase parsing and report an error.
- What happens when a phase issue is manually closed or edited by a user during orchestration? The system should detect the state mismatch and either reconcile or alert the user.

## Requirements *(mandatory)*

### Functional Requirements

**Plan Generation & Parsing**

- **FR-001**: System MUST generate a structured implementation plan from a user-provided app description using a two-stage process: a fast initial plan followed by a detailed plan document.
- **FR-002**: System MUST parse the detailed plan document into discrete implementation phases, extracting for each phase: an index, title, description, list of steps, and dependency information.
- **FR-003**: System MUST detect dependency relationships between phases, distinguishing between sequential dependencies ("depends on Phase N") and parallel-eligible phases ("parallel with Phase N" or no dependency declared).
- **FR-004**: System MUST detect and reject circular dependencies between phases, reporting the cycle to the user.

**Issue Creation & Project Management**

- **FR-005**: System MUST create one parent issue per parsed phase on the project board, including: the phase number and total count, the app name and description, the phase content from the plan, and an agent tracking table.
- **FR-006**: System MUST add each phase issue to the project board with an initial status of "Backlog."
- **FR-007**: System MUST create a temporary planning issue for the speckit.plan agent and close it after the plan is retrieved.

**Pipeline Orchestration & Execution**

- **FR-008**: System MUST group phases into dependency waves, where Wave 1 contains all phases with no dependencies, Wave 2 contains phases depending only on Wave 1 phases, and so on.
- **FR-009**: System MUST launch all pipelines within a wave simultaneously (parallel execution within a wave).
- **FR-010**: System MUST queue pipelines for later waves with references to their prerequisite phase issues.
- **FR-011**: System MUST verify that all prerequisite phase issues have their pull requests merged to the main branch before dequeuing a queued pipeline.
- **FR-012**: System MUST skip queued pipelines whose prerequisites are not yet met and re-evaluate them after each merge event.

**Auto-Merge**

- **FR-013**: System MUST enable auto-merge for each phase pipeline individually, not as a project-wide setting.
- **FR-014**: System MUST trigger pipeline queue evaluation after each successful auto-merge to start eligible dependent phases.
- **FR-015**: System MUST ensure that pipelines for later phases branch from the updated main branch (after prior phases have been merged).

**Background Processing & Status Tracking**

- **FR-016**: System MUST initiate app creation as a background process and return an immediate acknowledgement to the user.
- **FR-017**: System MUST track orchestration progress through defined states: planning, detailed plan generation running, parsing phases, creating issues, launching pipelines, and active.
- **FR-018**: System MUST broadcast state transitions to connected clients in real time.
- **FR-019**: System MUST provide a polling endpoint for clients to query current orchestration status.

**Error Handling**

- **FR-020**: System MUST enforce a configurable timeout on the detailed plan generation stage and report failure if exceeded.
- **FR-021**: System MUST halt dependent phases when a prerequisite phase fails, while allowing unrelated phases to continue.
- **FR-022**: System MUST notify the user when auto-merge fails due to merge conflicts, pausing the queue for affected dependency chains.
- **FR-023**: System MUST handle the case where the plan contains no parseable phases by reporting a clear error to the user.

### Key Entities

- **App Plan Orchestration**: Represents the end-to-end workflow of creating an app from description to active pipelines. Key attributes: app reference, current state, creation timestamp, and references to all created phase issues. Transitions through states: planning → detailed plan running → parsing phases → creating issues → launching pipelines → active.
- **Plan Phase**: A discrete unit of implementation work extracted from the plan document. Key attributes: phase index, title, description, list of steps, dependency references (which phases it depends on), and execution mode (sequential or parallel-eligible).
- **Phase Issue**: A project board issue representing a single phase. Key attributes: phase reference, issue number, pipeline state, merge status. Related to one Plan Phase and one Pipeline.
- **Pipeline State (extended)**: The existing pipeline execution state, extended with: auto-merge flag (whether to merge automatically on completion), and prerequisite issue references (list of phase issue numbers that must be merged before this pipeline can start).
- **Dependency Wave**: A logical grouping of phases that can execute in parallel. Key attributes: wave number, list of phases in the wave, and reference to prior wave. Wave 1 has no prerequisites; subsequent waves depend on all phases in prior waves being merged.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can initiate app creation and receive on-screen confirmation within 5 seconds of submitting their description.
- **SC-002**: The full planning stage (initial plan generation plus detailed plan creation) completes within 20 minutes for typical app descriptions.
- **SC-003**: 100% of parseable phases in a plan result in correctly created, dependency-ordered issues on the project board.
- **SC-004**: Phase pipelines respect dependency ordering: no phase begins execution before all of its prerequisite phases have their pull requests merged to the main branch.
- **SC-005**: Independent phases within the same dependency wave execute in parallel, reducing total elapsed time compared to strict sequential execution by at least 30% for plans with two or more parallel-eligible phases.
- **SC-006**: Users can see orchestration progress update within 5 seconds of each state transition.
- **SC-007**: When a phase fails, all directly dependent phases are halted within 60 seconds, while unrelated phases continue unaffected.
- **SC-008**: The system correctly detects and rejects circular dependencies in 100% of test cases, reporting a clear error to the user.
- **SC-009**: 90% of users who initiate plan-driven app creation successfully reach the "active pipelines" state without manual intervention.

## Assumptions

- The existing chat plan agent and speckit.plan agent are stable and do not require modification for this feature.
- The existing agent pipeline infrastructure (queue mode, dequeue logic, pipeline state storage) is functional and can be extended with new fields.
- The plan document format (plan.md) follows a consistent structure with `## Implementation Phases` and `### Phase N — Title` headings.
- The existing auto-merge capability in the system can be enabled per-pipeline without side effects on other pipelines.
- Performance targets (5-second acknowledgement, 20-minute planning) are based on standard web application expectations and typical agent execution times observed in the current system.
- The project board and issue management features already support creating issues, assigning statuses, and linking to pipelines.

## Out of Scope

- Modifying the speckit.plan agent itself or the plan.md template format.
- Manual phase reordering or editing after orchestration has started.
- Rollback of merged phases if a later phase fails.
- Support for non-GitHub issue trackers or project boards.
- Multi-repository orchestration (all phases operate within a single repository).
