# Feature Specification: Page Updates

**Feature Branch**: `006-page-updates`  
**Created**: 2026-04-14  
**Status**: Draft  
**Input**: User description: "Page Updates — Fix broken Add New Chat Panel button on Home Page, replace built-in saved pipelines with four predefined pipeline configurations (GitHub, Spec Kit, Default, App Builder), and improve Agents page UX including richer agent tiles, layout reordering, removal of unused sections, and viewport fixes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Home Page: Add New Chat Panel Button Works (Priority: P1)

A user visits the Home Page and clicks the "Add New Chat Panel" button. The button responds correctly and creates a new chat panel as expected. Currently this button is broken and non-functional, which blocks users from creating new chat panels — a core interaction on the Home Page.

**Why this priority**: This is a bug fix for a broken core feature on the Home Page. Users cannot perform a primary action (creating a new chat panel), which directly impacts the application's usability. Bug fixes for broken functionality take highest priority.

**Independent Test**: Navigate to the Home Page, click the "Add New Chat Panel" button, and verify a new chat panel is created and displayed.

**Acceptance Scenarios**:

1. **Given** a user is on the Home Page, **When** they click the "Add New Chat Panel" button, **Then** a new chat panel is created and visible on the page.
2. **Given** a user is on the Home Page, **When** they click the "Add New Chat Panel" button multiple times, **Then** each click creates an additional chat panel without errors.
3. **Given** a user is on the Home Page with no existing chat panels, **When** they click the "Add New Chat Panel" button, **Then** the first chat panel is created and the page layout adjusts to display it.

---

### User Story 2 - Pipeline Page: Built-in Saved Pipelines (Priority: P1)

A user navigates to the Pipeline page and sees exactly four built-in saved pipelines available: "GitHub", "Spec Kit", "Default", and "App Builder". Each pipeline contains a predefined set of agents configured in the "In progress" stage. These replace any previously existing built-in pipelines. The user can select any of these pipelines to use as a starting workflow configuration.

**Why this priority**: The Pipeline page is a central workflow configuration surface. Providing the correct built-in pipelines ensures users have access to curated, ready-to-use workflow templates that match the application's core use cases. Incorrect or missing pipelines directly reduce user productivity.

**Independent Test**: Navigate to the Pipeline page, verify exactly four built-in saved pipelines are listed (GitHub, Spec Kit, Default, App Builder), and confirm each contains the correct agents in the correct configuration.

**Acceptance Scenarios**:

1. **Given** a user navigates to the Pipeline page, **When** the page loads, **Then** exactly four built-in saved pipelines are displayed: "GitHub", "Spec Kit", "Default", and "App Builder".
2. **Given** a user views the "GitHub" pipeline, **When** they inspect its configuration, **Then** it contains only "GitHub Copilot (Auto) (Group 1)" in the "In progress" stage.
3. **Given** a user views the "Spec Kit" pipeline, **When** they inspect its configuration, **Then** it contains the following agents in the "In progress" stage, all set to Auto and Group 1: speckit.specify, speckit.plan, speckit.tasks, speckit.analyze, speckit.implement.
4. **Given** a user views the "Default" pipeline, **When** they inspect its configuration, **Then** it contains the following agents in the "In progress" stage, all set to Auto and Group 1: speckit.specify, speckit.plan, speckit.tasks, speckit.analyze, speckit.implement, Quality Assurance, Tester, Linter, Copilot Review, Judge.
5. **Given** a user views the "App Builder" pipeline, **When** they inspect its configuration, **Then** it contains the following agents in the "In progress" stage, all set to Auto and Group 1: speckit.specify, speckit.plan, speckit.tasks, speckit.analyze, speckit.implement, Architect, Quality Assurance, Tester, Linter, Copilot Review, Judge.
6. **Given** any previously existing built-in saved pipelines, **When** the update is applied, **Then** only the four specified pipelines remain as built-in saved pipelines.

---

### User Story 3 - Agents Page: Richer Agent Tiles for Awesome Copilot Browser (Priority: P2)

A user browsing the "Browse Awesome Copilot Agents" section sees agent tiles that are metadata-rich, displaying relevant information at a glance. Each tile can be clicked to expand and reveal additional details, or link out to the Awesome Copilots website directly (whichever provides the best user experience). This replaces the current plain tile layout with a more informative and interactive design.

**Why this priority**: Improving agent discovery directly enhances the user's ability to find and adopt agents for their workflows. Richer tiles reduce friction by surfacing key information without requiring users to navigate away from the page.

**Independent Test**: Navigate to the Agents page, scroll to the "Browse Awesome Copilot Agents" section, and verify each agent tile displays metadata (name, description, and any available tags or categories). Click a tile and verify it either expands to show more details or opens the Awesome Copilots website.

**Acceptance Scenarios**:

1. **Given** a user is on the Agents page, **When** they view the "Browse Awesome Copilot Agents" section, **Then** each agent is displayed as a metadata-rich tile showing at minimum the agent name and a brief description.
2. **Given** a user clicks on an agent tile, **When** the tile interaction completes, **Then** the user either sees expanded details inline or is directed to the relevant Awesome Copilots page.
3. **Given** a user views the agent tiles, **When** the tiles render, **Then** they follow modern card-based UI patterns with clear visual hierarchy and accessible interaction affordances.

---

### User Story 4 - Agents Page: Section Reordering and Layout Cleanup (Priority: P2)

A user navigates to the Agents page and sees an improved layout. The "Agent PRs waiting on main" section appears above the "Browse Awesome Copilot Agents" section, providing immediate visibility into pending agent work. The orbital map has been removed from the right side. The "Agent Archive" section has been removed, and the "Refresh agents" and "+ Add agent" buttons have been relocated near the "Curate agent rituals" and "Review assignments" buttons for a cleaner, more logical grouping of actions.

**Why this priority**: Layout and information hierarchy improvements ensure that the most actionable content (pending PRs) is visible first, and that action buttons are logically grouped. This reduces cognitive load and improves task efficiency.

**Independent Test**: Navigate to the Agents page and verify: (1) "Agent PRs waiting on main" appears before "Browse Awesome Copilot Agents", (2) no orbital map is visible on the right side, (3) the "Agent Archive" section is not present, (4) "Refresh agents" and "+ Add agent" buttons are positioned near "Curate agent rituals" and "Review assignments" buttons.

**Acceptance Scenarios**:

1. **Given** a user navigates to the Agents page, **When** the page loads, **Then** the "Agent PRs waiting on main" section is positioned above the "Browse Awesome Copilot Agents" section.
2. **Given** a user navigates to the Agents page, **When** the page loads, **Then** there is no orbital map displayed on the right side of the page.
3. **Given** a user navigates to the Agents page, **When** the page loads, **Then** the "Agent Archive" section is not present.
4. **Given** a user navigates to the Agents page, **When** the page loads, **Then** the "Refresh agents" and "+ Add agent" buttons are visually grouped near the "Curate agent rituals" and "Review assignments" buttons.

---

### User Story 5 - Agents Page: Rename "Refresh Models" to "Refresh Agents" (Priority: P2)

A user on the Agents page sees a "Refresh agents" button (previously labeled "Refresh models"). Clicking this button refreshes the Awesome Copilot agents catalog from the actual source, fetching the latest available agents.

**Why this priority**: The label "Refresh models" is misleading since the action refreshes agents, not models. Correcting the label improves clarity and reduces user confusion. The underlying functionality (refreshing from the source catalog) ensures the agent list stays current.

**Independent Test**: Navigate to the Agents page, locate the "Refresh agents" button, click it, and verify the Awesome Copilot agents catalog is refreshed with current data from the source.

**Acceptance Scenarios**:

1. **Given** a user is on the Agents page, **When** the page loads, **Then** the button is labeled "Refresh agents" (not "Refresh models").
2. **Given** a user clicks the "Refresh agents" button, **When** the refresh completes, **Then** the Awesome Copilot agents catalog is updated from the external source.

---

### User Story 6 - Agents Page: Fix "+ Add Agent" Viewport Positioning (Priority: P2)

A user clicks the "+ Add Agent" button on the Agents page, and the resulting dialog or panel appears within the browser's viewable area. Currently, it pops up below the viewable screen, requiring users to scroll down to find it — a usability bug.

**Why this priority**: This is a usability fix. When an action triggers a UI element that appears outside the viewport, users may not realize anything happened, leading to confusion and repeated clicks. Fixing the positioning ensures the add-agent interaction is immediately visible.

**Independent Test**: Navigate to the Agents page, click "+ Add Agent", and verify the resulting UI element (dialog, panel, or form) is fully visible within the browser viewport without needing to scroll.

**Acceptance Scenarios**:

1. **Given** a user clicks the "+ Add Agent" button, **When** the add-agent UI element appears, **Then** it is fully visible within the browser's current viewport.
2. **Given** a user clicks the "+ Add Agent" button from any scroll position on the Agents page, **When** the add-agent UI element appears, **Then** the page scrolls or the element is positioned so that it is visible without manual scrolling.

---

### Edge Cases

- What happens when the user has previously created custom pipelines — do they persist alongside the new built-in pipelines, or are they overwritten? **Assumption**: Custom pipelines are preserved; only the built-in saved pipelines are replaced.
- What happens when the Awesome Copilots source is unreachable and the user clicks "Refresh agents"? **Assumption**: The system displays a user-friendly error message indicating the refresh failed and retains the last successfully loaded agent catalog.
- What happens when the browser viewport is very small (mobile or resized) and the user clicks "+ Add Agent"? **Assumption**: The add-agent UI element is responsive and adapts to the available viewport size.
- What happens when there are no agents in the "Agent PRs waiting on main" section? **Assumption**: The section is still visible with an empty state message (e.g., "No agent PRs waiting") rather than being hidden.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST render a functional "Add New Chat Panel" button on the Home Page that creates a new chat panel when clicked.
- **FR-002**: System MUST display exactly four built-in saved pipelines on the Pipeline page: "GitHub", "Spec Kit", "Default", and "App Builder".
- **FR-003**: The "GitHub" built-in pipeline MUST contain only "GitHub Copilot (Auto) (Group 1)" in the "In progress" stage.
- **FR-004**: The "Spec Kit" built-in pipeline MUST contain the agents speckit.specify, speckit.plan, speckit.tasks, speckit.analyze, and speckit.implement, all set to Auto and Group 1 in the "In progress" stage.
- **FR-005**: The "Default" built-in pipeline MUST contain the agents speckit.specify, speckit.plan, speckit.tasks, speckit.analyze, speckit.implement, Quality Assurance, Tester, Linter, Copilot Review, and Judge, all set to Auto and Group 1 in the "In progress" stage.
- **FR-006**: The "App Builder" built-in pipeline MUST contain the agents speckit.specify, speckit.plan, speckit.tasks, speckit.analyze, speckit.implement, Architect, Quality Assurance, Tester, Linter, Copilot Review, and Judge, all set to Auto and Group 1 in the "In progress" stage.
- **FR-007**: System MUST remove any previously existing built-in saved pipelines that are not among the four specified pipelines.
- **FR-008**: System MUST preserve any user-created custom pipelines when updating built-in saved pipelines.
- **FR-009**: Agent tiles in the "Browse Awesome Copilot Agents" section MUST display metadata including at minimum the agent name and description.
- **FR-010**: Agent tiles MUST be interactive — either expandable to show more details or linking to the Awesome Copilots website.
- **FR-011**: The "Agent PRs waiting on main" section MUST be positioned above the "Browse Awesome Copilot Agents" section on the Agents page.
- **FR-012**: The orbital map MUST be removed from the right side of the Agents page.
- **FR-013**: The "Agent Archive" section MUST be removed from the Agents page.
- **FR-014**: The "Refresh agents" and "+ Add agent" buttons MUST be relocated near the "Curate agent rituals" and "Review assignments" buttons.
- **FR-015**: The "Refresh models" button MUST be renamed to "Refresh agents".
- **FR-016**: The "Refresh agents" button MUST refresh the Awesome Copilot agents catalog from the external source when clicked.
- **FR-017**: The "+ Add Agent" UI element MUST appear within the browser's viewable viewport when activated.

### Key Entities

- **Chat Panel**: A conversational interface element on the Home Page that users create to interact with AI agents.
- **Built-in Saved Pipeline**: A predefined workflow configuration containing a set of agents organized into stages. Built-in pipelines are system-provided and not user-editable.
- **Pipeline Agent**: An individual agent within a pipeline, configured with a mode (Auto/Manual), group assignment, and stage placement (e.g., "In progress").
- **Agent Tile**: A visual card element representing an external agent in the Awesome Copilot agents catalog, displaying metadata and supporting interaction (expand or link out).
- **Agent PR**: A pull request submitted by an agent that is pending review or merge into the main branch.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can successfully create a new chat panel from the Home Page on every attempt (100% success rate for the "Add New Chat Panel" button).
- **SC-002**: Exactly four built-in saved pipelines are visible on the Pipeline page, each containing the correct agents as specified.
- **SC-003**: Users can identify the purpose and metadata of an agent tile within 3 seconds of viewing the Agents page catalog.
- **SC-004**: The "+ Add Agent" UI element is fully visible within the viewport 100% of the time when activated, regardless of scroll position.
- **SC-005**: The "Refresh agents" button successfully updates the agent catalog from the external source within a reasonable time (under 5 seconds for user-perceived response).
- **SC-006**: All Agents page layout changes (section reordering, orbital map removal, archive removal, button relocation) are reflected correctly on page load without layout shifts or visual artifacts.
- **SC-007**: No previously working functionality is broken by these changes — all existing features outside the scope of these updates continue to work as before.

## Assumptions

- The "Add New Chat Panel" button bug is a frontend issue (click handler not firing, routing error, or similar) rather than a backend service outage.
- "speckit.impliment" in the original issue description is a typo for "speckit.implement" — the spec uses the correct spelling.
- Custom pipelines created by users are persisted separately from built-in saved pipelines and will not be affected by changes to built-in pipelines.
- The Awesome Copilots agent catalog has an external source (API or data file) that the "Refresh agents" button can fetch from.
- The orbital map removal refers to a visual/decorative component and removing it has no impact on functional features.
- The "Agent Archive - Broader space for every active assistant" section is a legacy UI component that is no longer needed.
- The "+ Add Agent" viewport issue is a layout/positioning problem where the element renders below the visible area.
