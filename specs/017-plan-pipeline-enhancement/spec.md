# Feature Specification: Full-Stack Plan Pipeline Enhancement

**Feature Branch**: `017-plan-pipeline-enhancement`  
**Created**: 2026-04-04  
**Status**: Draft  
**Input**: User description: "Full-Stack Plan Pipeline Enhancement"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Iterative Plan Refinement with Per-Step Feedback (Priority: P1)

A user creates a plan via the `/plan` command and reviews the generated steps. Rather than accepting or rejecting the entire plan, the user wants to provide targeted feedback on individual steps — for example, noting that Step 3 needs more detail or that Step 5 should be split into two steps. The system captures these per-step comments and feeds them back to the AI agent, which regenerates the plan addressing the specific feedback. The user can repeat this cycle until satisfied.

**Why this priority**: The current "Request Changes" button only refocuses the global input, providing no structured way to give step-level feedback. This is the most immediate pain point blocking effective plan iteration and is the core fix enabling all subsequent features.

**Independent Test**: Can be fully tested by creating a plan, clicking "Request Changes" on an individual step, entering a comment, submitting it, and verifying that the regenerated plan addresses the feedback. Delivers immediate value by replacing the broken refinement workflow.

**Acceptance Scenarios**:

1. **Given** a user has a generated plan with multiple steps displayed in PlanPreview, **When** the user clicks "Request Changes," **Then** inline comment inputs appear next to each step.
2. **Given** the user has entered feedback on one or more steps, **When** the user submits the feedback, **Then** the AI agent receives the per-step comments and regenerates the plan addressing each comment.
3. **Given** the plan has been regenerated after feedback, **When** the user views the updated plan, **Then** the plan reflects changes that address the submitted comments.

---

### User Story 2 - Plan Versioning and Change Tracking (Priority: P1)

A user iterates on a plan through multiple refinement cycles and wants to see what changed between versions. The system maintains a version history of every plan revision, and the user can visually identify which steps were added, modified, or unchanged by viewing diff highlights (yellow border for changed steps, green border for new steps).

**Why this priority**: Without version history, users lose all context of previous plan states once a refinement occurs. Versioning is foundational for diff highlighting, rollback confidence, and audit trails. It also enables export of any version.

**Independent Test**: Can be fully tested by creating a plan, refining it at least once, and verifying that a version history is available and that diff highlights correctly indicate changed and new steps.

**Acceptance Scenarios**:

1. **Given** a plan has been refined at least once, **When** the user views the plan, **Then** changed steps display a yellow border and new steps display a green border.
2. **Given** a plan has multiple versions, **When** the user requests the plan history, **Then** the system returns all previous version snapshots in chronological order.
3. **Given** a plan at version N, **When** the AI agent regenerates the plan, **Then** the system automatically increments the version number and snapshots the previous state before overwriting.

---

### User Story 3 - Step Management (Add, Edit, Delete, Reorder) (Priority: P2)

A user reviews a generated plan and wants to customize it by adding a missing step, editing an existing step's title or description, removing an irrelevant step, or reordering steps to better reflect the desired execution sequence. The user performs these operations directly in the plan view through inline editing, an "Add Step" button, delete with confirmation, and drag-and-drop reordering.

**Why this priority**: After refinement, users often need fine-grained control to adjust individual steps rather than requesting another full regeneration. This transforms the plan from a read-only AI output into an editable, user-owned artifact.

**Independent Test**: Can be fully tested by creating a plan, then performing each CRUD operation (add, edit, delete, reorder) and verifying the plan updates correctly each time.

**Acceptance Scenarios**:

1. **Given** a plan is displayed, **When** the user clicks on a step's title or description, **Then** an inline editing field appears allowing direct text modification.
2. **Given** a plan is displayed, **When** the user clicks "Add Step," **Then** a new step is appended to the plan with editable fields.
3. **Given** a plan has a step with no dependents, **When** the user deletes that step, **Then** the step is removed from the plan.
4. **Given** a plan has a step with dependents, **When** the user attempts to delete it, **Then** a confirmation dialog displays the affected dependent steps before proceeding.
5. **Given** a plan with multiple steps, **When** the user drags a step to a new position, **Then** the step order updates and persists.

---

### User Story 4 - Dependency Graph Visualization (Priority: P2)

A user views a plan with steps that have interdependencies and wants to understand the execution order and relationships visually. The system displays a dependency graph showing steps as nodes arranged in topological layers, with edges indicating dependencies. Clicking a node in the graph scrolls to the corresponding step in the plan list.

**Why this priority**: As plans grow in complexity, understanding step dependencies through a flat list becomes difficult. A visual graph provides immediate clarity on execution order, parallelizable steps, and critical paths. This is essential for plans with more than a few steps.

**Independent Test**: Can be fully tested by creating a plan where steps have dependencies, viewing the dependency graph, verifying all nodes and edges appear correctly, and clicking a node to confirm it scrolls to the step.

**Acceptance Scenarios**:

1. **Given** a plan with step dependencies defined, **When** the user views the plan, **Then** a dependency graph is displayed showing steps as nodes and dependencies as directed edges.
2. **Given** the dependency graph is visible, **When** the user clicks on a node, **Then** the view scrolls to the corresponding step in the plan list.
3. **Given** a user attempts to create a circular dependency (e.g., Step A depends on Step B, Step B depends on Step A), **When** the mutation is submitted, **Then** the system rejects it with a clear error message indicating the circular dependency.

---

### User Story 5 - Selective Step Approval (Priority: P2)

A user has reviewed and is satisfied with some steps in the plan but wants to keep iterating on others. The user selects individual steps via checkboxes and approves only those selected steps, which triggers issue creation for the approved subset. Unapproved steps remain editable.

**Why this priority**: The current all-or-nothing approval forces users to either approve everything or nothing. Selective approval allows incremental progress — teams can start working on approved steps while the rest of the plan is still being refined.

**Independent Test**: Can be fully tested by creating a plan, selecting a subset of steps via checkboxes, clicking "Approve Selected," and verifying that issues are created only for the approved steps while unapproved steps remain editable.

**Acceptance Scenarios**:

1. **Given** a plan with multiple steps, **When** the user views the plan, **Then** each step has a checkbox for selection.
2. **Given** the user has selected some steps, **When** the user clicks "Approve Selected," **Then** issues are created only for the selected steps.
3. **Given** some steps are approved and some are not, **When** the user views the plan, **Then** approved steps are visually distinguished from unapproved steps.

---

### User Story 6 - Plan Export (Priority: P3)

A user wants to share the plan with stakeholders who do not have access to the application. The user exports the plan as Markdown or copies it to the clipboard for pasting into external tools such as email, documentation, or project management systems.

**Why this priority**: Export is a convenience feature that extends the plan's utility beyond the application. While not core to the planning workflow, it supports team collaboration and documentation needs.

**Independent Test**: Can be fully tested by creating a plan, clicking "Export as Markdown," and verifying the downloaded file contains a well-formatted Markdown representation of the plan. Similarly, "Copy to clipboard" can be tested by pasting into a text editor.

**Acceptance Scenarios**:

1. **Given** a plan exists, **When** the user clicks "Export as Markdown," **Then** a Markdown file is downloaded containing the plan's title, summary, and all steps with their details.
2. **Given** a plan exists, **When** the user clicks "Copy to clipboard," **Then** the plan content is copied to the system clipboard in Markdown format and a success confirmation is shown.

---

### User Story 7 - Progress Tracking with Board Sync (Priority: P3)

After approving steps and having issues created, a user wants to see real-time progress on the plan as issues are completed. The system periodically polls issue statuses and displays a progress bar (e.g., "3/7 issues completed") at the top of the plan view. Individual step status badges reflect the current state of their associated issues.

**Why this priority**: Progress tracking closes the feedback loop between planning and execution. While it depends on prior features (approval, issue creation), it provides significant ongoing value by keeping the plan view as a living dashboard.

**Independent Test**: Can be fully tested by approving steps, simulating issue status changes, and verifying that the progress bar and step status badges update accordingly.

**Acceptance Scenarios**:

1. **Given** a plan has approved steps with associated issues, **When** the user views the plan, **Then** a progress bar displays "X/Y issues completed" at the top.
2. **Given** an issue status changes externally, **When** the system polls for updates, **Then** the corresponding step's status badge updates to reflect the new status.
3. **Given** all issues are completed, **When** the user views the progress bar, **Then** it shows 100% completion.

---

### User Story 8 - Enhanced Thinking Indicator (Priority: P3)

While the AI agent is generating or refining a plan, the user sees a detailed thinking indicator that shows the agent's current activity — such as which tools are being used, what context is being gathered, and what plan changes are being computed. This replaces the simple spinner with streaming breadcrumbs and collapsible detail panels.

**Why this priority**: The current thinking indicator provides minimal feedback during plan generation. Richer indicators reduce user anxiety during longer operations and build trust in the AI's reasoning process.

**Independent Test**: Can be fully tested by initiating a plan generation, observing the thinking indicator during the process, and verifying that tool usage and context gathering events are displayed as breadcrumbs.

**Acceptance Scenarios**:

1. **Given** the AI agent is generating a plan, **When** the user observes the thinking indicator, **Then** streaming breadcrumbs show the current phase (researching, planning, refining) and activity details.
2. **Given** the agent uses a tool during generation, **When** the tool call completes, **Then** the thinking indicator displays the tool name and a collapsible detail panel with results.

---

### Edge Cases

- What happens when a user submits feedback on a step that was removed in a concurrent edit? The system should gracefully ignore feedback for non-existent steps and notify the user.
- How does the system handle version conflicts when two users refine the same plan simultaneously? The system should use optimistic concurrency — the second save should detect the version mismatch and prompt the user to refresh.
- What happens when a step deletion would leave orphaned dependencies? The system should cascade-remove the dependency references and warn the user about affected steps.
- How does the system handle drag-and-drop reordering when steps have dependency constraints? The system should validate the new order against the dependency graph and reject reorders that would violate dependency ordering.
- What happens when the external issue tracker is unavailable during status polling? The system should gracefully degrade, retaining the last known status and displaying a stale-data indicator.
- What happens when a plan has zero steps and the user attempts to approve? The system should disable the approval action and display a message indicating no steps are available.
- How does the system handle a plan with the maximum number of steps (15)? The "Add Step" button should be disabled when the step limit is reached, with a tooltip explaining the constraint.

## Requirements *(mandatory)*

### Functional Requirements

**Phase 1 — Iterative Refinement Loop**

- **FR-001**: System MUST maintain a version history for each plan, automatically incrementing the version number and creating a snapshot of the previous state on every modification.
- **FR-002**: System MUST accept per-step feedback comments and incorporate them into the AI agent's context for the next refinement cycle.
- **FR-003**: System MUST enhance AI agent instructions to emit structured refinement suggestions and explicitly address per-step feedback in regenerated plans.
- **FR-004**: System MUST display inline comment inputs per step when the user clicks "Request Changes," replacing the current global-input-focus behavior.
- **FR-005**: System MUST visually highlight step changes between plan versions — yellow border for modified steps, green border for newly added steps.
- **FR-006**: System MUST allow users to access the full plan version history, retrieving all previous version snapshots.

**Phase 2 — Step CRUD and Dependency Graph**

- **FR-007**: System MUST allow users to add, edit, delete, and bulk-reorder plan steps.
- **FR-008**: System MUST validate the step dependency graph on every dependency-modifying mutation, rejecting circular dependencies with a clear error.
- **FR-009**: System MUST support inline editing of step titles and descriptions directly in the plan view.
- **FR-010**: System MUST support drag-and-drop reordering of steps in the plan view.
- **FR-011**: System MUST display a dependency graph visualization showing steps as nodes in topological layers with directed edges for dependencies.
- **FR-012**: System MUST support selective step approval, allowing users to approve a subset of steps and triggering issue creation only for the approved subset.
- **FR-013**: System MUST display a confirmation dialog showing dependent steps when a user attempts to delete a step that has dependents.
- **FR-014**: System MUST cascade-remove dependency references when a step is deleted.

**Phase 3 — Thinking Polish, Export, and Board Sync**

- **FR-015**: System MUST emit enriched real-time events during plan generation, including tool usage, context gathering, and plan diff information.
- **FR-016**: System MUST display streaming breadcrumbs and collapsible tool call details in the thinking indicator during plan generation.
- **FR-017**: System MUST allow users to export a plan as a downloadable Markdown file.
- **FR-018**: System MUST provide a "Copy to clipboard" action that copies the plan in Markdown format.
- **FR-019**: System MUST periodically poll associated issue statuses after step approval and update step status accordingly.
- **FR-020**: System MUST display a progress bar showing "X/Y issues completed" at the top of the plan view, computed from polled issue statuses.

### Key Entities

- **Plan**: Represents a generated plan. Key attributes: title, summary, list of steps, current version number, creation and update timestamps.
- **Plan Version**: A historical snapshot of a plan at a specific version. Key attributes: version number, title, summary, steps snapshot, creation timestamp. Linked to a parent Plan.
- **Plan Step**: An individual action item within a plan. Key attributes: title, description, order position, dependency references (to other steps), approval status, associated issue status.
- **Step Feedback**: A transient comment attached to a specific step during a refinement cycle. Key attributes: step reference, comment text. Not persisted — injected into agent context only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can provide per-step feedback and receive an updated plan addressing their comments within one refinement cycle, completing the feedback-refine loop in under 60 seconds for plans with up to 15 steps.
- **SC-002**: Users can identify what changed between plan versions at a glance through visual diff indicators (colored borders), without needing to manually compare versions.
- **SC-003**: Users can add, edit, delete, and reorder plan steps directly in the plan view, with each operation completing and persisting in under 2 seconds.
- **SC-004**: The system prevents circular dependencies in plan steps, rejecting invalid dependency configurations 100% of the time with a user-understandable error message.
- **SC-005**: Users can visualize step dependencies through a graph and navigate from graph nodes to corresponding steps with a single click.
- **SC-006**: Users can approve a subset of plan steps and have issues created only for the approved subset, maintaining backward compatibility with full-plan approval.
- **SC-007**: Users can export a plan as Markdown or copy it to clipboard with a single action.
- **SC-008**: Users can see real-time plan execution progress ("X/Y issues completed") that updates within 60 seconds of an issue status change.
- **SC-009**: Users receive meaningful activity feedback during plan generation through streaming breadcrumbs, reducing perceived wait time.
- **SC-010**: All plan modifications (step edits, feedback, reorder) maintain version history, enabling users to review any previous plan state.

## Assumptions

- Plans contain a maximum of 15 steps, making a simple topological layout sufficient for the dependency graph and keeping the UI manageable.
- Step-level feedback is transient and incorporated into the AI agent's context rather than stored permanently. Feedback is ephemeral by nature and only relevant for the current refinement cycle.
- The existing drag-and-drop library (@dnd-kit) already installed in the application is sufficient for step reordering.
- No new external library is needed for the dependency graph — a lightweight custom SVG component is adequate given the step count limit.
- Board sync uses polling (periodic status checks) rather than webhooks, which is simpler and compatible with the existing data storage approach.
- Selective step approval extends the existing approval workflow with an optional step filter, maintaining backward compatibility.
- Optimistic concurrency (version-based conflict detection) is the appropriate strategy for handling concurrent plan edits.
- The existing SSE (Server-Sent Events) infrastructure supports the additional event types needed for richer thinking indicators.

## Dependencies

- Existing drag-and-drop library (@dnd-kit) and its established patterns in the codebase.
- Existing SSE event infrastructure for streaming thinking indicators.
- Existing plan approval and issue creation workflow for selective approval extension.
- Existing data migration framework for schema changes.

## Scope Boundaries

### In Scope

- Plan versioning with automatic snapshot creation
- Per-step feedback collection and injection into AI context
- Enhanced AI refinement instructions
- Inline step editing, adding, deleting, and reordering
- Dependency graph visualization (custom SVG)
- DAG validation preventing circular dependencies
- Selective step approval
- Plan export (Markdown download and clipboard copy)
- Board sync via polling
- Progress bar with issue status tracking
- Enhanced thinking indicator with breadcrumbs and collapsible details

### Out of Scope

- Real-time collaborative editing (multi-user simultaneous editing)
- Webhook-based board sync (would require GitHub App setup)
- Plan branching or forking (creating alternative plan variants)
- Undo/redo functionality for step edits
- Plan templates or pre-built plan libraries
- Integration with external project management tools beyond the existing issue tracker
- Step time estimation or scheduling
- Plan commenting or annotation beyond step-level feedback
