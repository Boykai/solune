# Feature Specification: Copilot-Style Planning Mode (v2)

**Feature Branch**: `001-copilot-plan-mode`  
**Created**: 2026-03-31  
**Status**: Draft  
**Input**: User description: "Plan: /plan — Copilot-Style Planning Mode (v2). Add a persistent planning mode scoped to the selected project/repo. The agent researches context, asks clarifying questions, and iterates until the user approves. An approved plan becomes a GitHub Parent Issue with each step as a sub-issue. Real-time thinking/phase indicators via SSE keep the user informed throughout."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enter Plan Mode and Create a Plan (Priority: P1)

A user who has a selected project types `/plan` followed by a description of what they want to build (e.g., `/plan Add user authentication with OAuth2`). The system enters plan mode: the agent researches the project context (repository structure, existing issues, code patterns), then produces a structured implementation plan with a title, summary, and ordered steps. Each step is scoped as a future GitHub issue with a title, description, and dependency annotations. The plan is displayed in-chat as a rich preview card showing the project name, plan status, and each step.

**Why this priority**: This is the core value proposition — without the ability to create a plan, no other plan feature matters. It delivers immediate value by letting users go from an idea to a structured, reviewable implementation plan in a single interaction.

**Independent Test**: Can be fully tested by typing `/plan <description>` in a chat session with a selected project and verifying a structured plan appears in the chat. Delivers value as a standalone planning tool even without approval or issue creation.

**Acceptance Scenarios**:

1. **Given** a user has a selected project with a linked repository, **When** they type `/plan Add a notifications system` and send the message, **Then** the system enters plan mode, the agent researches the project context, and a structured plan with title, summary, and ordered steps is displayed as a rich preview card in the chat.
2. **Given** a user sends `/plan` with no description, **When** the message is processed, **Then** the system responds with a prompt asking the user to provide a description of what they want to plan.
3. **Given** a user has no selected project, **When** they type `/plan Add feature X`, **Then** the system responds with an error message indicating a project must be selected first.
4. **Given** a user sends `/plan Build a REST API for user management`, **When** the agent generates the plan, **Then** each plan step includes a title, description, and dependency annotations indicating which steps must be completed before it.

---

### User Story 2 - Iterate and Refine the Plan (Priority: P1)

After the initial plan is generated, the user reviews it and provides feedback in natural language (e.g., "Split step 3 into two smaller steps" or "Add error handling considerations to step 2"). The system remains in plan mode — all follow-up messages are automatically routed to the plan agent without needing to prefix with `/plan`. The agent incorporates the feedback and updates the plan in-place, preserving the conversation trail. The user can iterate as many times as needed.

**Why this priority**: Iteration is essential to plan quality. A plan that cannot be refined is rarely useful. This story is co-equal with P1 because planning is inherently iterative and the mode-persistence design is a core architectural decision.

**Independent Test**: Can be fully tested by generating a plan, then sending follow-up refinement messages and verifying the plan updates in-place while conversation history is preserved.

**Acceptance Scenarios**:

1. **Given** a plan has been generated and plan mode is active, **When** the user sends a follow-up message like "Add a step for database migrations before step 2", **Then** the plan is updated in-place with the new step and the updated plan is displayed.
2. **Given** plan mode is active, **When** the user sends a follow-up message, **Then** the message is automatically routed to the plan agent without requiring a `/plan` prefix.
3. **Given** the user has iterated on a plan three times, **When** they review the conversation, **Then** all previous versions of the plan are visible in the conversation history as a trail of refinements.
4. **Given** plan mode is active, **When** the user sends feedback referencing a specific step (e.g., "Step 4 should depend on step 2"), **Then** the agent updates the dependency annotations accordingly.

---

### User Story 3 - Real-Time Thinking Indicators (Priority: P2)

While the agent is researching context, drafting the plan, or incorporating feedback, the user sees real-time phase indicators in the chat interface instead of a generic loading animation. The indicators show what the agent is currently doing: "Researching project context…", "Drafting implementation plan…", or "Incorporating your feedback…" with appropriate icons and animations.

**Why this priority**: This is a UX quality feature that significantly improves the user experience during the wait time. Planning takes longer than normal chat responses, making feedback especially important, but the feature can function without it.

**Independent Test**: Can be tested by triggering plan mode and observing that phase-specific indicators appear during agent processing, with transitions between phases as work progresses.

**Acceptance Scenarios**:

1. **Given** the user has sent a `/plan` command, **When** the agent begins researching the project context, **Then** a "Researching project context…" indicator with a search icon is displayed in the chat.
2. **Given** the agent has finished researching, **When** it begins drafting the plan, **Then** the indicator transitions to "Drafting implementation plan…" with a list icon.
3. **Given** the user has sent feedback on an existing plan, **When** the agent begins processing the feedback, **Then** the indicator shows "Incorporating your feedback…" with an edit icon.
4. **Given** thinking indicators are being displayed, **When** the agent completes its work and the plan is ready, **Then** the thinking indicators are replaced by the plan preview card.

---

### User Story 4 - Approve Plan and Create GitHub Issues (Priority: P2)

Once the user is satisfied with the plan, they click an "Approve & Create Issues" button on the plan preview card. The system creates a GitHub parent issue containing the plan title, summary, and a checklist of all steps, then creates individual sub-issues for each step linked to the parent. The plan card updates to show the status as completed, with links to the created parent issue and each sub-issue. Solune's existing pipeline system handles execution per-issue after creation.

**Why this priority**: This is the key outcome — turning a plan into actionable GitHub issues. While it depends on P1 stories for plan creation, it completes the value loop by connecting plans to the team's existing workflow.

**Independent Test**: Can be tested by creating and approving a plan, then verifying that a parent issue and sub-issues are created in the target repository with correct titles, descriptions, checklist, and linking.

**Acceptance Scenarios**:

1. **Given** a plan is in "draft" status and the user is satisfied, **When** they click "Approve & Create Issues", **Then** a progress spinner is shown while the system creates a parent GitHub issue and one sub-issue per plan step in the target repository.
2. **Given** the system has successfully created all issues, **When** creation is complete, **Then** the plan card updates to show "Completed" status with a "View Parent Issue" link and each step displays a badge linking to its corresponding GitHub issue.
3. **Given** the plan has steps with dependency annotations, **When** issues are created, **Then** each sub-issue body includes references to its dependency issues (e.g., "Depends on #42").
4. **Given** the user clicks "Approve & Create Issues", **When** issue creation fails for any step (e.g., due to permissions or network errors), **Then** the system shows an error message with details about which steps failed and allows the user to retry.

---

### User Story 5 - Exit Plan Mode (Priority: P3)

A user who is in plan mode but wants to return to normal chat can exit plan mode. After a plan is approved, a "Exit Plan Mode" button is displayed. The user can also explicitly exit at any time by using an exit action. Exiting plan mode returns the chat to normal operation where messages are processed by the standard chat agent.

**Why this priority**: This is necessary for a complete user experience but is a simpler interaction that relies on the plan mode infrastructure from P1.

**Independent Test**: Can be tested by entering plan mode, then exiting and verifying that subsequent messages are handled by the normal chat agent rather than the plan agent.

**Acceptance Scenarios**:

1. **Given** plan mode is active with an approved plan, **When** the user clicks "Exit Plan Mode", **Then** plan mode is deactivated and subsequent messages are processed by the normal chat agent.
2. **Given** plan mode is active with a draft plan, **When** the user exits plan mode, **Then** the draft plan is preserved for potential future reference and the chat returns to normal mode.
3. **Given** the user has exited plan mode, **When** they send a new message, **Then** the message is handled by the standard chat agent without any plan-mode context.

---

### User Story 6 - Plan Mode Banner and Context Display (Priority: P3)

While plan mode is active, a persistent banner is displayed above the chat input area showing "Plan mode — {project_name}" to remind the user of the current context. The plan preview card shows a project badge with the repository owner and name. This context helps users understand which project and repository the plan targets.

**Why this priority**: This is a UX polish feature that prevents confusion about which project is being planned for. It improves clarity but is not essential for plan functionality.

**Independent Test**: Can be tested by entering plan mode and verifying that the banner appears above the input with the correct project name, and disappears when plan mode is exited.

**Acceptance Scenarios**:

1. **Given** the user enters plan mode for project "My App", **When** the plan mode is active, **Then** a banner reading "Plan mode — My App" is displayed above the chat input area.
2. **Given** plan mode is active, **When** the plan preview card is displayed, **Then** it includes a project badge showing the repository owner and name (e.g., "octocat/my-app").
3. **Given** the user exits plan mode, **When** the mode is deactivated, **Then** the plan mode banner is removed from the chat interface.

---

### Edge Cases

- What happens when the user switches to a different project while plan mode is active? The system should exit plan mode and notify the user that the plan was scoped to the previous project.
- What happens when the user's session expires during plan mode? The plan state should be persisted so it can be resumed on re-authentication.
- What happens when the target repository is deleted or the user loses access during plan approval? The system should surface a clear error explaining that issue creation failed due to access issues.
- What happens when the agent encounters a repository with no code or context? The agent should still produce a plan based on the user's description, noting that limited project context was available.
- What happens when a plan has zero steps? The system should not allow approval of an empty plan and should prompt the user to add at least one step.
- What happens when GitHub rate limits are hit during issue creation? The system should pause, surface a progress indicator showing which issues were created and which are pending, and retry after the rate limit window.
- What happens when two users simultaneously enter plan mode for the same project? Each user should have their own independent plan session since plan mode is scoped to the user's chat session, not the project.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to enter plan mode by sending a `/plan` command followed by a feature description in the chat.
- **FR-002**: System MUST persist the plan mode state in the user's agent session so that all follow-up messages are automatically routed to the plan agent until the user approves the plan or explicitly exits.
- **FR-003**: System MUST store each plan record with the associated project identifier, project name, repository owner, and repository name so that plans are scoped to a specific project and repository.
- **FR-004**: System MUST generate a structured plan containing a title, summary, and an ordered list of steps, where each step has a title, description, and optional dependency annotations.
- **FR-005**: System MUST update the plan in-place when the user provides refinement feedback, preserving the conversation trail of all iterations.
- **FR-006**: System MUST emit real-time thinking events during agent processing that indicate the current phase: "researching" (project context analysis), "planning" (drafting the plan), or "refining" (incorporating user feedback).
- **FR-007**: System MUST display phase-aware thinking indicators in the chat interface that replace the generic loading animation, showing appropriate icons and labels for each phase.
- **FR-008**: System MUST provide an "Approve & Create Issues" action that, when triggered, creates a parent GitHub issue containing the plan title, summary, and a checklist of steps, plus one sub-issue per plan step in the target repository.
- **FR-009**: System MUST update each plan step with the corresponding GitHub issue number and URL after successful issue creation.
- **FR-010**: System MUST update the plan status to "completed" after all issues have been successfully created.
- **FR-011**: System MUST provide a way to exit plan mode, returning the chat to standard operation.
- **FR-012**: System MUST display a plan mode banner above the chat input showing the project name while plan mode is active.
- **FR-013**: System MUST display the plan as a rich preview card with a project badge (repository owner/name), status badge, step list with dependencies, and action buttons.
- **FR-014**: System MUST restrict the agent's toolset during plan mode to read-only operations plus a plan-saving capability, preventing unintended modifications to the repository or project.
- **FR-015**: System MUST validate that a project is selected before allowing plan mode to be entered.
- **FR-016**: System MUST display created issue links as badges on each plan step after approval is complete.
- **FR-017**: System MUST show a "View Parent Issue" link and "Exit Plan Mode" button after plan approval and issue creation is complete.
- **FR-018**: System MUST include dependency references in sub-issue bodies when steps have dependencies on other steps.
- **FR-019**: System MUST handle partial issue creation failures gracefully by reporting which steps succeeded and which failed, and allowing the user to retry.

### Key Entities

- **Plan**: Represents a structured implementation plan scoped to a specific project and repository. Key attributes: unique identifier, title, summary, status (draft, approved, completed, failed), associated project identifier, project name, repository owner, repository name, parent issue number (populated after approval), parent issue URL (populated after approval), creation timestamp, last-updated timestamp.
- **PlanStep**: Represents an individual step within a plan, scoped as a future GitHub issue. Key attributes: unique identifier, parent plan reference, step order/position, title, description, dependency list (references to other steps that must be completed first), issue number (populated after approval), issue URL (populated after approval).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can go from typing a `/plan` command to viewing a structured implementation plan within 30 seconds for typical project contexts.
- **SC-002**: Users can iterate on a plan (provide feedback and see the updated plan) within 15 seconds per refinement cycle.
- **SC-003**: 90% of users who enter plan mode successfully produce an approved plan without needing to restart the process.
- **SC-004**: Plan approval and GitHub issue creation completes within 60 seconds for plans with up to 20 steps.
- **SC-005**: Users see real-time phase indicators within 1 second of the agent beginning a new processing phase, with no gaps where the interface shows no feedback.
- **SC-006**: 100% of approved plans result in correctly linked parent issues and sub-issues in the target GitHub repository, with accurate dependency references.
- **SC-007**: Users can exit plan mode and return to normal chat within 2 seconds of triggering the exit action.
- **SC-008**: Plan mode correctly persists across follow-up messages — 100% of messages sent while plan mode is active are routed to the plan agent without requiring a `/plan` prefix.

## Assumptions

- Users have already authenticated with GitHub and have a valid session with appropriate repository permissions (read for planning, write for issue creation).
- The selected project has a linked GitHub repository from which the agent can gather context.
- The existing SSE streaming infrastructure supports adding new event types alongside the existing `token`, `tool_call`, `tool_result`, `done`, and `error` events.
- Plan mode is scoped to individual user chat sessions — concurrent users planning for the same project do not interfere with each other.
- The existing pipeline system handles execution of created issues independently; the plan feature is responsible only for plan creation and issue generation.
- Standard web application performance expectations apply (sub-second UI responsiveness for local actions, network-dependent delays for API calls).
- Plans are persisted in the application's existing data store alongside chat sessions and messages.
- GitHub's issue creation API rate limits are sufficient for typical plan sizes (up to 20 steps). For larger plans, graceful retry handling is assumed.
