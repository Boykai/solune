# Feature Specification: Full-Stack Plan Pipeline Enhancement (v2 — Copilot SDK + MAF)

**Feature Branch**: `002-sdk-plan-pipeline`  
**Created**: 2026-04-04  
**Status**: Draft  
**Input**: User description: "Full-Stack Plan Pipeline Enhancement (v2 — Copilot SDK + MAF)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - SDK-Powered Plan Agent Sessions (Priority: P1)

A developer enters plan mode in Solune. Instead of a flag-switched general chat session, a dedicated plan agent session launches with its own system prompt, restricted tool set, and isolated context. The user experiences faster, more focused plan generation because the agent only has access to planning-relevant tools (project context, pipeline listing, plan saving) and follows plan-specific instructions. If the user later switches to implementation mode, a separate agent profile with full tool access takes over — there is no leakage between modes.

**Why this priority**: This is the foundational change — every subsequent feature (versioning hooks, pipeline orchestration, streaming events, step CRUD) depends on the SDK custom agent session infrastructure being in place. Without dedicated agent profiles, tool isolation and CLI interoperability cannot be achieved.

**Independent Test**: Start a plan session and verify the agent can invoke whitelisted tools (project context, pipeline list, save plan) but cannot invoke implementation-only tools (code editing, deployment). Confirm the agent's system prompt matches the plan-specific instructions.

**Acceptance Scenarios**:

1. **Given** the Copilot SDK is available and configured, **When** a user enters plan mode, **Then** a dedicated plan agent session is created with only planning tools (project context, pipeline listing, plan saving) whitelisted
2. **Given** a plan agent session is active, **When** the agent attempts to invoke a tool not in its whitelist, **Then** the tool call is rejected and the user sees no side effects
3. **Given** the speckit pipeline runs, **When** each stage agent is launched, **Then** it receives its own agent profile with stage-specific system prompt and tool set
4. **Given** the SDK session is active, **When** the session exceeds the context window, **Then** automatic compaction preserves planning context without manual intervention

---

### User Story 2 - Automatic Plan Versioning on Save (Priority: P1)

A user is iterating on an implementation plan. Each time the plan is saved — whether by the user clicking save or the agent invoking the save tool — the previous version is automatically captured as a snapshot. The user never needs to manually create backups. Later, the user can browse the version history to see how the plan evolved, compare versions, and understand what changed between iterations.

**Why this priority**: Plan versioning is the second critical building block. It powers the diff highlighting, rollback capability, and version-aware refinement prompt. Session hooks make it automatic and invisible to the user.

**Independent Test**: Save a plan, modify it, save again. Verify two version snapshots exist in the version history with correct timestamps and content. Confirm the snapshot was created by the session hook, not by modifying the save tool itself.

**Acceptance Scenarios**:

1. **Given** a plan exists with content, **When** the save plan tool is invoked, **Then** the system automatically snapshots the current plan content before the overwrite completes
2. **Given** a plan has been saved three times, **When** the user requests version history, **Then** three version snapshots are returned in chronological order with timestamps and content
3. **Given** a plan version snapshot exists, **When** the post-save hook fires, **Then** a plan diff event is emitted to connected clients showing what changed
4. **Given** the save operation fails, **When** the pre-save hook has already taken a snapshot, **Then** the snapshot is still preserved (no rollback of the snapshot)

---

### User Story 3 - Step-Level Feedback and Refinement (Priority: P2)

A user reviews a generated plan and notices that Step 3 needs adjustment. Instead of rewriting the entire prompt, they click "Request Changes" on that specific step and type inline feedback like "This step should use batch processing instead of real-time." The agent receives this structured, step-specific feedback and regenerates only the affected steps while preserving the rest of the plan. The user sees a refinement dialog (not free-text chat) guiding them through the feedback process.

**Why this priority**: Step-level feedback transforms the plan from a one-shot output into an iterative, collaborative document. This directly addresses the most common user pain point of needing to regenerate entire plans for small changes.

**Independent Test**: Generate a plan with multiple steps. Submit feedback on a single step. Verify the agent regenerates only the targeted step and surrounding dependencies, leaving unaffected steps unchanged.

**Acceptance Scenarios**:

1. **Given** a plan with multiple steps, **When** the user submits feedback on a specific step, **Then** the agent receives the feedback with step context and the feedback endpoint returns a success response
2. **Given** step-level feedback is submitted, **When** the agent processes the feedback, **Then** a structured dialog guides the clarification exchange between user and agent
3. **Given** the refinement sidebar is open, **When** the user clicks "Request Changes" on a step, **Then** an inline comment input appears anchored to that step
4. **Given** the agent is refining a step based on feedback, **When** the refinement prompt is constructed, **Then** it includes the plan's version history context so the agent understands prior iterations

---

### User Story 4 - Pipeline Stage Orchestration with Progress Visibility (Priority: P2)

A user triggers the speckit pipeline (specify → plan → tasks → analyze → implement). As each stage runs, the user sees real-time progress: which stage is active, which completed, which failed. If a stage fails, the pipeline pauses and the user can retry or skip. Stages that can run in parallel (like quality assurance, testing, and code review) execute concurrently, reducing total pipeline time.

**Why this priority**: Pipeline orchestration replaces custom orchestration logic with SDK-native sub-agent events, simplifying maintenance. Progress visibility builds user confidence and reduces anxiety during long-running pipeline executions.

**Independent Test**: Trigger a full pipeline run. Verify stage-started, stage-completed, and stage-failed events are emitted in correct order. Verify parallel groups execute concurrently (wall-clock time less than sequential sum).

**Acceptance Scenarios**:

1. **Given** the speckit pipeline is triggered, **When** each stage starts, completes, or fails, **Then** corresponding stage events are emitted to connected clients in real time
2. **Given** stages in a parallel group (e.g., quality assurance, tester, code review), **When** the pipeline reaches that group, **Then** all stages in the group execute concurrently
3. **Given** a stage fails during pipeline execution, **When** the failure event is emitted, **Then** the pipeline pauses and the user can choose to retry, skip, or abort
4. **Given** SDK streaming is active during a stage, **When** the agent generates reasoning or invokes tools, **Then** native SDK events map to enhanced client-facing events (reasoning deltas, tool execution start/completion)

---

### User Story 5 - Step CRUD and Dependency Graph (Priority: P3)

A user wants to restructure a generated plan. They add a new step, reorder existing steps via drag-and-drop, edit step content inline, and delete unnecessary steps. The system validates the dependency graph to prevent circular dependencies. A visual graph shows step relationships so the user understands the execution order. The agent can also add, edit, or delete steps programmatically when prompted.

**Why this priority**: Step CRUD and dependency management give users full control over plan structure. While the plan is useful without this (read-only view with refinement), structural editing enables power users to deeply customize plans.

**Independent Test**: Create a plan, add a step with a dependency, attempt to create a circular dependency (verify rejection), reorder steps via the API, and confirm the dependency graph updates correctly.

**Acceptance Scenarios**:

1. **Given** a draft plan, **When** the user adds, edits, or deletes a step via the interface or API, **Then** the plan updates and dependency graph is revalidated
2. **Given** a step depends on another step, **When** the user attempts to create a circular dependency, **Then** the system rejects the change with an explanation
3. **Given** plan steps with dependencies, **When** the user views the dependency graph, **Then** a visual directed acyclic graph renders showing step relationships and execution order
4. **Given** the user drags a step to a new position, **When** the drop completes, **Then** the step order updates and dependency constraints are re-evaluated
5. **Given** the agent has registered step mutation tools, **When** the agent adds or edits steps programmatically, **Then** the same validation and CRUD logic applies as with user-initiated changes

---

### User Story 6 - Diff Highlighting Between Plan Versions (Priority: P3)

A user wants to see exactly what changed between the current plan and the previous version. When viewing plan history, changed sections are highlighted with additions in green and removals in red. The user can compare any two versions side by side.

**Why this priority**: Diff highlighting completes the versioning story by making version history actionable. Without visual diffs, users must manually compare versions, which is tedious and error-prone.

**Independent Test**: Save a plan twice with different content. Request the version history and render the diff. Verify additions and removals are correctly identified.

**Acceptance Scenarios**:

1. **Given** a plan with at least two versions, **When** the user opens the version history, **Then** version snapshots are listed with timestamps and a summary of changes
2. **Given** the user selects two versions to compare, **When** the diff view renders, **Then** additions, removals, and modifications are visually distinguished

---

### User Story 7 - Copilot CLI Plugin Access (Priority: P4 — Stretch)

A developer working in the terminal wants to create and manage plans without opening the web UI. They install the Solune plan plugin via `copilot /plugin install` and can then use slash commands (`/plan`, `/refine`, `/approve`) directly in Copilot CLI. The same plan pipeline executes as in the web UI.

**Why this priority**: This is a stretch goal that expands accessibility but is not required for the core feature. It depends on all prior phases being complete and stable.

**Independent Test**: Install the CLI plugin, create a plan using CLI commands, verify the plan appears in the web UI with correct content and version history.

**Acceptance Scenarios**:

1. **Given** the CLI plugin is packaged and installable, **When** a user runs the plugin install command, **Then** the plugin installs successfully and plan commands become available
2. **Given** the ACP server mode is enabled, **When** an external tool connects via the Agent Client Protocol, **Then** the plan pipeline is accessible for read and write operations

---

### Edge Cases

- What happens when the SDK session fails to initialize (e.g., Copilot CLI binary not found in the environment)? The system falls back to the existing agent provider with a user-visible warning, preserving current functionality.
- What happens when a pre-save hook snapshot fails but the save itself succeeds? The plan is saved successfully and a warning is logged; the missing snapshot is noted in the version history as a gap.
- What happens when two users simultaneously save the same plan? The system uses optimistic concurrency — the second save creates a version snapshot of the first user's save, preventing data loss.
- What happens when the pipeline orchestrator encounters an unrecoverable stage failure? The pipeline halts at the failed stage, preserves all completed stage outputs, and emits a failure event with actionable context.
- What happens when a step dependency references a deleted step? The deletion is blocked until the dependency is removed or reassigned, with a clear error message listing the dependent steps.
- What happens when the SDK version is incompatible or unavailable? The system detects the incompatibility at startup, logs the issue, and falls back to the existing orchestration path without SDK features.
- What happens when a plan exceeds the context window during iterative refinement? SDK infinite session support automatically compacts the context, preserving the most recent plan state and version history summaries.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create dedicated agent sessions per pipeline stage, each with a stage-specific system prompt and tool whitelist that prevents access to tools outside the stage's scope
- **FR-002**: System MUST automatically snapshot the current plan content before every save operation, without requiring changes to the save tool's implementation
- **FR-003**: System MUST emit real-time streaming events to connected clients for agent reasoning, tool execution, and pipeline stage transitions
- **FR-004**: System MUST support step-level feedback submission that routes structured user input to the active agent session for targeted plan refinement
- **FR-005**: System MUST persist plan version history with timestamps and content, accessible via a history endpoint that returns all snapshots in chronological order
- **FR-006**: System MUST validate plan step dependencies as a directed acyclic graph, rejecting any mutation that would create a circular dependency
- **FR-007**: System MUST support full step CRUD operations (create, read, update, delete) both through user-facing endpoints and agent-invokable tools
- **FR-008**: System MUST execute pipeline stages according to their group configuration — sequential stages run in order, parallel group stages run concurrently
- **FR-009**: System MUST map SDK-native streaming events to client-consumable server-sent events for reasoning deltas, tool execution lifecycle, and sub-agent stage tracking
- **FR-010**: System MUST support drag-and-drop step reordering with automatic dependency constraint re-evaluation
- **FR-011**: System MUST track per-step approval status independently from overall plan approval status
- **FR-012**: System MUST provide version diff capability showing additions, removals, and modifications between any two plan versions
- **FR-013**: System MUST support guided refinement dialogs using structured elicitation rather than free-text chat for step-level feedback
- **FR-014**: System MUST fall back gracefully to the existing agent provider when the SDK is unavailable or incompatible, preserving current functionality
- **FR-015**: System MUST support automatic session context compaction for long planning conversations to maintain coherent context without manual intervention

### Key Entities

- **Plan**: Represents an implementation plan associated with a chat session. Key attributes: identifier, associated chat, current version number, content (structured steps), status (draft, approved, archived), timestamps
- **Plan Version**: A point-in-time snapshot of a plan's content. Key attributes: identifier, parent plan reference, version number, full content snapshot, creation timestamp, trigger (auto-save hook, manual save)
- **Plan Step**: An individual action item within a plan. Key attributes: identifier, parent plan reference, title, description, order position, dependencies (references to other steps), approval status (pending, approved, rejected), assignable metadata
- **Agent Profile**: Configuration for a pipeline stage agent. Key attributes: stage identifier, system prompt, tool whitelist, permission level (read-only or full), group assignment (serial or parallel group identifier)
- **Pipeline Execution**: Tracks a single run of the speckit pipeline. Key attributes: identifier, triggering user, start timestamp, current stage, stage statuses (pending, running, completed, failed), outputs per stage

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can generate a complete implementation plan from a feature description within the same time as the current system (no regression), with individual stage progress visible throughout
- **SC-002**: Plan version snapshots are created automatically on every save — 100% of save operations produce a corresponding version entry with no user intervention required
- **SC-003**: Users can submit step-level feedback and receive a refined plan within a single interaction cycle, without regenerating the entire plan
- **SC-004**: Pipeline stages configured for parallel execution complete in less wall-clock time than sequential execution of the same stages (measurable improvement for groups of 2+ parallel stages)
- **SC-005**: Step dependency validation prevents 100% of circular dependency attempts, with a clear rejection message returned to the user
- **SC-006**: Users can view and compare any two plan versions, with changes visually distinguished, within 3 seconds of requesting the comparison
- **SC-007**: The system remains fully functional when the SDK is unavailable — all existing plan features continue to work via the fallback path, with no user-facing errors
- **SC-008**: Users can add, edit, delete, and reorder plan steps and see the dependency graph update in under 2 seconds per operation
- **SC-009**: Real-time streaming events are delivered to the client for every agent reasoning delta, tool execution event, and pipeline stage transition — no silent gaps during plan generation
- **SC-010**: 90% of users who use step-level feedback successfully refine their plan without needing to restart the plan generation process

## Assumptions

- The Copilot Python SDK v1.0.17+ is available and stable enough for production use. All SDK calls are wrapped behind the agent provider abstraction to absorb breaking changes in future SDK versions.
- The Copilot CLI binary is available in the deployment environment (Docker/CI). If not, the system falls back to the existing agent provider.
- Python 3.12+ is used in the backend, as required by the SDK.
- The existing agent provider pattern (`agent_provider.py` wrapping `CopilotClient` behind `GitHubCopilotAgent`) is preserved as the abstraction layer — SDK features are accessed through this layer, not directly.
- Plan versioning uses the existing database infrastructure with new migrations; no new database engine or external storage is required.
- The frontend communicates with the backend via server-sent events (SSE) for real-time updates, consistent with the current architecture.
- Concurrent plan editing by multiple users on the same plan is handled via optimistic concurrency (last-write-wins with version snapshots), not real-time collaborative editing.
- CLI plugin and ACP server features (Phase 4) are stretch goals and not required for the initial release.
- The existing plan approval flow is preserved — new features are additive and do not break current workflows.
- Performance baselines for plan generation time are established from current system metrics before the upgrade.

## Dependencies

- **Copilot Python SDK ≥1.0.17**: Required for custom agents, session hooks, sub-agent events, streaming deltas, and elicitation features
- **Existing agent provider layer** (`agent_provider.py`): Must be extended, not replaced — SDK session creation routes through this layer
- **Database migration system**: New migrations required for plan versioning and step status tables
- **Frontend SSE infrastructure**: Must support new event types for stage tracking and elicitation
- **Parent Issue #716**: This specification aligns with and is tracked under the parent planning issue

## Out of Scope

- General chat agent changes — only plan mode sessions are affected by this enhancement
- Mobile-specific UI — web-first approach; mobile responsiveness follows existing patterns
- Breaking changes to the existing plan approval flow — all additions are backward-compatible
- Azure OpenAI provider changes — this feature uses the Copilot SDK path exclusively
- Real-time collaborative editing — concurrent users are handled via optimistic concurrency, not live collaboration
- Custom model selection within plan sessions — the SDK manages model routing
