# Feature Specification: Fix Issues Systematically

**Feature Branch**: `615-fix-issues-systematically`  
**Created**: 2026-04-03  
**Status**: Draft  
**Input**: User description: "Fix the following issues in a systematic way: Fix Setting page model section, cannot select all models and save them. For example GPT5.4 XHigh. In the app chat, when a user enters a message - it should render in the chat instantly, before the chat agent responses. Remove AI Enhance from app chat - all chat messages should be handled by the app chat agent. When app chat provides task recommendation - a confirm/reject button should render. Agent Pipeline configurations should be saved in database/cache/memory - any Agent Pipeline can be used on any Project and should be stored by user. Chores configurations should be saved in database/cache/memory - any Chores can be used on any Project and should be stored by user. Remove the PR/Issue Template generation processes. On the Activity page, it should provide hyperlinked PR#s and Issue#s."

## User Scenarios & Testing

### User Story 1 - Settings Model Selection Fix (Priority: P1)

As a user configuring AI model preferences, I want all model variants — including those with reasoning effort levels such as GPT5.4 XHigh — to be selectable and saved, so that my chosen model configuration persists across sessions and is used by agents.

**Why this priority**: Model selection is a foundational setting that directly controls agent behavior. If users cannot select and persist certain models, affected agents will produce unexpected results or fall back to defaults, undermining trust in the platform.

**Independent Test**: Can be fully tested by navigating to the Settings page, selecting any model + reasoning effort combination, saving, reloading the page, and verifying the selection is preserved. Delivers value by restoring full model configurability.

**Acceptance Scenarios**:

1. **Given** a user is on the Settings page with the model selector visible, **When** the user selects a model with a reasoning effort level (e.g., "GPT5.4 (XHigh)"), **Then** the selection is accepted without error and displayed in the selector.
2. **Given** a user has selected a model with reasoning effort and clicked Save, **When** the user reloads the Settings page, **Then** the previously selected model and reasoning effort level are still shown as the active selection.
3. **Given** a user has saved a model with reasoning effort, **When** any agent runs on behalf of that user, **Then** the agent uses the saved model and reasoning effort level.

---

### User Story 2 - Instant User Message Rendering in App Chat (Priority: P1)

As a user sending a message in the app chat, I want my message to appear immediately in the chat window before the AI agent responds, so that I have instant visual feedback confirming my message was sent.

**Why this priority**: Immediate message rendering is a core chat UX expectation. Without it, users experience uncertainty about whether their input was received, leading to duplicate messages and a frustrating experience.

**Independent Test**: Can be fully tested by opening the app chat, typing a message, pressing Send, and confirming the message appears instantly in the chat thread as a user bubble before any agent response arrives. Delivers value by providing standard real-time chat behavior.

**Acceptance Scenarios**:

1. **Given** the user has the app chat open and types a message, **When** the user presses Send (or Enter), **Then** the message appears immediately in the chat thread as a user message bubble.
2. **Given** the user has sent a message that now appears in the chat, **When** the agent has not yet responded, **Then** a loading or "thinking" indicator is shown to signal the agent is processing.
3. **Given** the user sends a message while offline or while the agent is unavailable, **When** the message fails to deliver, **Then** the user message remains visible with an error indicator and an option to retry.

---

### User Story 3 - Remove AI Enhance from App Chat (Priority: P1)

As a user of the app chat, I want all messages to be handled uniformly by the chat agent without an AI Enhance toggle, so that the chat experience is simple and consistent.

**Why this priority**: The AI Enhance toggle introduces confusion about which processing path a message takes. Removing it simplifies the user experience and eliminates a source of bugs related to dual message handling.

**Independent Test**: Can be fully tested by opening the app chat interface and verifying there is no AI Enhance toggle, switch, or option visible. Sending any message should go through the standard chat agent flow. Delivers value by simplifying the chat interface and reducing user confusion.

**Acceptance Scenarios**:

1. **Given** the user opens the app chat interface, **When** the chat toolbar and input area are visible, **Then** there is no AI Enhance toggle, switch, or button present.
2. **Given** the user sends any message in the app chat, **When** the message is processed, **Then** it is handled entirely by the chat agent service without any intermediate enhancement step.
3. **Given** a user previously had AI Enhance enabled, **When** the user opens the app chat after this change, **Then** the setting is ignored and all messages flow through the chat agent.

---

### User Story 4 - Task Recommendation Confirm/Reject Buttons (Priority: P2)

As a user receiving task recommendations from the chat agent, I want confirm and reject action buttons to appear with each recommendation so that I can approve or dismiss suggestions directly in the conversation.

**Why this priority**: Task recommendations without actionable controls require users to manually create tasks elsewhere, breaking the conversational workflow. Adding confirm/reject buttons keeps the user in the chat context and reduces friction.

**Independent Test**: Can be fully tested by triggering a task recommendation from the chat agent (e.g., asking the agent to suggest a task) and verifying that confirm and reject buttons appear on the recommendation message. Clicking each button should produce the correct outcome. Delivers value by making task creation seamless within the chat.

**Acceptance Scenarios**:

1. **Given** the chat agent sends a message containing a task recommendation, **When** the recommendation message renders in the chat, **Then** Confirm and Reject buttons are visible and clearly labeled.
2. **Given** a task recommendation with Confirm and Reject buttons is visible, **When** the user clicks Confirm, **Then** the recommended task is created and the user sees a success confirmation in the chat.
3. **Given** a task recommendation with Confirm and Reject buttons is visible, **When** the user clicks Reject, **Then** the recommendation is dismissed, no task is created, and the user sees a dismissal acknowledgment.
4. **Given** a task recommendation has been confirmed or rejected, **When** the user views the same recommendation message, **Then** the action buttons are replaced with a status indicator showing the action taken (e.g., "Confirmed" or "Rejected").

---

### User Story 5 - User-Scoped Agent Pipeline Storage (Priority: P2)

As a user managing agent pipelines, I want pipeline configurations stored at the user level rather than per-project, so that I can reuse any pipeline across all of my projects.

**Why this priority**: Per-project pipeline storage forces users to recreate identical configurations for each project. Moving to user-scoped storage eliminates redundant configuration work and enables a consistent pipeline library.

**Independent Test**: Can be fully tested by creating a pipeline configuration in one project, switching to a different project, and verifying the pipeline is still listed and usable. Delivers value by making pipelines portable across projects.

**Acceptance Scenarios**:

1. **Given** a user creates a new agent pipeline configuration while working in Project A, **When** the user switches to Project B, **Then** the pipeline created in Project A is visible and selectable in Project B.
2. **Given** a user edits a pipeline configuration from Project B, **When** the user returns to Project A, **Then** the edits are reflected in the pipeline as viewed from Project A.
3. **Given** a user deletes a pipeline, **When** the user views any project, **Then** the deleted pipeline no longer appears in any project's pipeline list.

---

### User Story 6 - User-Scoped Chores Storage and Remove PR/Issue Templates (Priority: P2)

As a user managing chores, I want chore configurations stored at the user level and the PR/Issue template generation process removed, so that chores are reusable across projects and do not produce unwanted repository artifacts.

**Why this priority**: Like pipelines, per-project chore storage leads to duplication. Additionally, automatic PR/Issue template generation creates unexpected files in repositories, which can confuse teams and pollute version control.

**Independent Test**: Can be fully tested by creating a chore in one project, switching to another project and verifying the chore is available, and then running a chore to confirm no PR or Issue templates are generated in the repository. Delivers value by simplifying chore management and removing unintended side effects.

**Acceptance Scenarios**:

1. **Given** a user creates a chore configuration while working in Project A, **When** the user switches to Project B, **Then** the chore is visible and usable in Project B.
2. **Given** a user runs any chore, **When** the chore completes, **Then** no PR template or Issue template files are generated or committed to the repository.
3. **Given** a user deletes a chore, **When** the user views any project, **Then** the deleted chore no longer appears in any project's chore list.

---

### User Story 7 - Activity Page Hyperlinked PR#s and Issue#s (Priority: P2)

As a user viewing the Activity page, I want PR numbers and Issue numbers displayed as clickable hyperlinks so that I can navigate directly to the relevant GitHub resource without manually searching.

**Why this priority**: Plain-text PR and Issue numbers on the Activity page require users to copy-paste or manually navigate to GitHub. Hyperlinking these references reduces context-switching and improves workflow efficiency.

**Independent Test**: Can be fully tested by viewing the Activity page with events that reference PR#s or Issue#s and verifying that each reference is rendered as a clickable link that opens the correct GitHub PR or Issue. Delivers value by streamlining navigation between the app and GitHub.

**Acceptance Scenarios**:

1. **Given** an activity event references a PR (e.g., "PR #42"), **When** the event is displayed on the Activity page, **Then** "#42" is rendered as a hyperlink pointing to the correct GitHub pull request URL.
2. **Given** an activity event references an Issue (e.g., "Issue #15"), **When** the event is displayed on the Activity page, **Then** "#15" is rendered as a hyperlink pointing to the correct GitHub issue URL.
3. **Given** an activity event references multiple PR#s and Issue#s, **When** the event renders, **Then** each reference is independently hyperlinked to its respective GitHub resource.

### Edge Cases

- What happens when a user selects a model variant that is later removed or deprecated from the model list? The system should display a warning that the saved model is no longer available and prompt the user to select a new one.
- What happens when a user sends a message in app chat but the network connection drops mid-send? The message should remain visible with a "failed to send" indicator and a retry option.
- What happens when the chat agent returns a task recommendation with missing or invalid data (e.g., no task title)? The confirm/reject buttons should still render, but confirming should show a validation error prompting the user to provide the missing information.
- What happens when a user has pipelines or chores created under the old per-project storage model? Existing configurations should be migrated to user-scoped storage automatically, preserving all settings.
- What happens when an activity event references a PR# or Issue# from a repository that the user does not have access to? The hyperlink should still be rendered, and clicking it should lead to GitHub's standard "not found" or "permission denied" page.
- What happens when the same pipeline or chore name exists across multiple users? Each user's configurations are scoped to their own account, so name collisions between different users are not a concern.

## Requirements

### Functional Requirements

- **FR-001**: System MUST allow users to select any available model variant, including those with reasoning effort levels (e.g., GPT5.4 XHigh), from the Settings page model selector.
- **FR-002**: System MUST persist the selected model and reasoning effort level when the user saves settings, and restore the selection when the Settings page is revisited.
- **FR-003**: System MUST display user-sent messages in the app chat immediately upon submission, before the agent responds (optimistic rendering).
- **FR-004**: System MUST show a loading or "thinking" indicator in the chat while the agent is processing a user message.
- **FR-005**: System MUST remove the AI Enhance toggle from the app chat interface entirely.
- **FR-006**: System MUST route all app chat messages through the chat agent service without any intermediate enhancement step.
- **FR-007**: System MUST display Confirm and Reject action buttons on chat messages that contain task recommendations from the agent.
- **FR-008**: System MUST create a task when the user clicks Confirm on a task recommendation, and dismiss the recommendation when the user clicks Reject.
- **FR-009**: System MUST replace Confirm/Reject buttons with a status indicator after the user takes action on a recommendation.
- **FR-010**: System MUST store agent pipeline configurations at the user level, making them available across all of the user's projects.
- **FR-011**: System MUST store chore configurations at the user level, making them available across all of the user's projects.
- **FR-012**: System MUST NOT generate PR template or Issue template files in the repository when chores are run.
- **FR-013**: System MUST render PR numbers and Issue numbers as clickable hyperlinks on the Activity page, pointing to the corresponding GitHub resources.
- **FR-014**: System MUST handle failed message sends in app chat by showing a "failed" indicator and a retry option on the user's message bubble.

### Key Entities

- **Model Setting**: Represents a user's saved model configuration including model identifier and reasoning effort level (e.g., "GPT5.4", "XHigh"). Belongs to a single user.
- **Chat Message**: A message in the app chat thread, either from a user or the chat agent. User messages support optimistic rendering. Agent messages may contain task recommendations.
- **Task Recommendation**: A structured suggestion from the chat agent within a chat message that includes a proposed task title, description, and action controls (confirm/reject). Linked to a chat message and optionally to a created task.
- **Agent Pipeline Configuration**: A reusable configuration defining an agent pipeline's steps, models, and parameters. Owned by a user and accessible across all of that user's projects.
- **Chore Configuration**: A reusable configuration defining a chore's actions and parameters. Owned by a user and accessible across all of that user's projects. No longer generates repository template files.
- **Activity Event**: A record of an action or occurrence displayed on the Activity page. May reference one or more GitHub PR numbers or Issue numbers, which are rendered as hyperlinks.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can select and save any model variant (including all reasoning effort levels) from the Settings page, and the selection persists after page reload — 100% of available models are selectable.
- **SC-002**: User-sent messages in app chat appear in the chat thread within 200 milliseconds of pressing Send, before any agent response.
- **SC-003**: The AI Enhance toggle is completely absent from the app chat interface — zero UI elements reference AI Enhance in the chat.
- **SC-004**: 100% of task recommendations from the chat agent display Confirm and Reject action buttons.
- **SC-005**: Users can access the same pipeline configurations across all their projects — a pipeline created in one project is visible in all other projects within 5 seconds.
- **SC-006**: Users can access the same chore configurations across all their projects — a chore created in one project is visible in all other projects within 5 seconds.
- **SC-007**: Running any chore produces zero PR template or Issue template files in the repository.
- **SC-008**: 100% of PR# and Issue# references on the Activity page are rendered as clickable hyperlinks to the correct GitHub resources.
- **SC-009**: All seven fixes can be completed and deployed independently without blocking each other.

## Assumptions

- The application already has a Settings page with a model selector component that supports some model variants; the fix extends it to support all variants.
- The app chat already has a working message flow between user and agent; this specification addresses rendering timing and removal of the AI Enhance path.
- The chat agent already has the capability to generate task recommendations in its responses; this specification adds UI controls for acting on those recommendations.
- Pipeline and chore configurations currently exist in some form (per-project); the migration to user-scoped storage preserves existing data.
- The Activity page already displays PR# and Issue# text references; this specification makes them hyperlinked.
- The GitHub repository URL for each project is known and accessible to the system for constructing hyperlinks.
