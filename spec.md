# Feature Specification: Page Updates

**Feature Branch**: `006-page-updates`
**Created**: 2026-04-14
**Status**: Draft
**Input**: User description: "Page Updates — Chores and Apps page improvements including UI cleanup, bug fixes, and new functionality"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Chores Page Cleanup (Priority: P1)

As a user managing chores, I want the Chores page to be streamlined so that I only see relevant controls and chore definitions are saved directly in the database rather than through GitHub Templates and pull requests.

**Why this priority**: The Chores page has accumulated outdated UI elements (GitHub Template support, Featured rituals, Plan recurring work, Upkeep studio) and has a critical scroll bug on the "Review upkeep cadence" button that blocks usability. Fixing these issues restores core page functionality and removes confusion from deprecated workflows.

**Independent Test**: Can be fully tested by navigating to the Chores page, verifying removed sections are absent, confirming the scroll bug is resolved, and verifying that chore creation and management works through the database-backed flow.

**Acceptance Scenarios**:

1. **Given** a user navigates to the Chores page, **When** the page loads, **Then** there is no mention of GitHub Templates, no option to create PRs for saving chore definitions, and no "Featured rituals" section visible.
2. **Given** a user navigates to the Chores page, **When** the page loads, **Then** the "Plan recurring work" button is not present.
3. **Given** a user navigates to the Chores page, **When** the page loads, **Then** the "Upkeep studio" section is not present.
4. **Given** a user clicks the "Review upkeep cadence" button, **When** the associated panel or view opens, **Then** the page does not jump or scroll unexpectedly, the bottom of the page content is fully visible, and the user can scroll freely to the top without refreshing.
5. **Given** a user navigates to the Chores page, **When** looking at the "Ritual Maintenance" section, **Then** the "Clean up" and "+ Create chore" controls are located within that section.
6. **Given** a user creates a new chore, **When** they save the chore definition, **Then** the definition is persisted in the database (not via a GitHub Template or pull request).

---

### User Story 2 — Create App Experience Simplification (Priority: P2)

As a user creating a new app, I want the Create App form to be simpler and more intuitive by removing unnecessary fields and reorganizing advanced settings.

**Why this priority**: Streamlining the Create App flow reduces friction for new users and prevents confusion from irrelevant options. Defaulting to the main branch eliminates a decision point that most users don't need to customize.

**Independent Test**: Can be fully tested by opening the Create App experience, verifying the "Target branch" section is absent (with the system defaulting to main), verifying "New Repository Settings" appears under "Advanced options", and confirming "Name override" is not present in "Advanced options".

**Acceptance Scenarios**:

1. **Given** a user opens the Create App experience, **When** the form loads, **Then** there is no "Target branch" section visible, and the system defaults to the main branch.
2. **Given** a user opens the Create App experience, **When** they expand the "Advanced options" section, **Then** "New Repository Settings" controls are located within that section.
3. **Given** a user opens the Create App experience, **When** they expand the "Advanced options" section, **Then** the "Name override" field is not present.

---

### User Story 3 — App Tile Management (Priority: P2)

As a user managing apps, I want to be able to delete apps directly from the App tiles and see their current status at a glance, so I can keep my workspace organized and stay informed.

**Why this priority**: Delete functionality and status visibility are core management capabilities that reduce the need for workarounds and improve day-to-day workflow efficiency.

**Independent Test**: Can be fully tested by viewing App tiles, confirming a delete button is present on each tile, verifying that deleting an app removes it, and checking that app status indicators reflect whether a GitHub Parent Issue is executing in the app's project.

**Acceptance Scenarios**:

1. **Given** a user views the Apps page, **When** looking at any App tile, **Then** a delete button is visible on the tile.
2. **Given** a user clicks the delete button on an App tile, **When** they confirm the deletion, **Then** the app is removed and no longer appears in the list.
3. **Given** an app has an active GitHub Parent Issue executing in its project, **When** the user views the App tile, **Then** a status indicator shows that the app has active execution in progress.
4. **Given** an app has no active GitHub Parent Issue, **When** the user views the App tile, **Then** the status indicator reflects an idle or inactive state.

---

### User Story 4 — App Detail View and History (Priority: P3)

As a user, I want to select an app and see detailed information about its GitHub Project and Agent Pipeline, and I want the History section to include Agent Pipeline updates so I can track all activity in one place.

**Why this priority**: Detailed app views and comprehensive history provide transparency into what agents are doing within each app's project, reducing the need to switch between Solune and GitHub to get a full picture.

**Independent Test**: Can be fully tested by selecting an app, verifying that detailed GitHub Project and Agent Pipeline information is displayed, and checking the History section for Agent Pipeline update entries similar to the Activity page format.

**Acceptance Scenarios**:

1. **Given** a user selects an app from the Apps page, **When** the app detail view opens, **Then** information about the app's GitHub Project is displayed (project name, status, link).
2. **Given** a user selects an app from the Apps page, **When** the app detail view opens, **Then** Agent Pipeline information is displayed (pipeline status, recent runs).
3. **Given** an app has Agent Pipeline activity, **When** the user views the app's History section, **Then** Agent Pipeline updates appear in the history feed in a format consistent with the Activity page.
4. **Given** an app has no Agent Pipeline activity, **When** the user views the app's History section, **Then** the history still loads correctly and indicates no pipeline updates are available.

---

### Edge Cases

- What happens when a user tries to delete an app that has an active GitHub Parent Issue executing? The system should warn the user and require confirmation before proceeding.
- What happens when app status cannot be determined (e.g., GitHub API is unreachable)? The status indicator should show an "unknown" or "unavailable" state rather than failing silently.
- What happens when the "Review upkeep cadence" panel content exceeds the viewport? The page must remain scrollable and not lock the user out of navigation.
- What happens when a user creates a chore after GitHub Template support is removed? The system should use the database-backed flow exclusively with no remnant references to templates.
- What happens when the "Advanced options" section in Create App has no other settings besides "New Repository Settings"? The section should still render correctly and be collapsible.

## Requirements *(mandatory)*

### Functional Requirements

#### Chores Page

- **FR-001**: System MUST remove all UI references to GitHub Templates for chore definitions, including any option to create pull requests for saving chore templates.
- **FR-002**: System MUST remove the "Featured rituals" section from the Chores page.
- **FR-003**: System MUST remove the "Plan recurring work" button from the Chores page.
- **FR-004**: System MUST fix the "Review upkeep cadence" button so that activating it does not cause the page to jump, does not cut off the bottom of the page, and allows the user to scroll back to the top without refreshing.
- **FR-005**: System MUST relocate the "Clean up" and "+ Create chore" controls into the "Ritual Maintenance" section.
- **FR-006**: System MUST remove the "Upkeep studio" section from the Chores page.
- **FR-007**: System MUST persist chore definitions in the database instead of through GitHub Templates or pull requests.

#### Apps — Create App Experience

- **FR-008**: System MUST remove the "Target branch" section from the Create App experience and default to the main branch.
- **FR-009**: System MUST move the "New Repository Settings" controls into the "Advanced options" section of the Create App experience.
- **FR-010**: System MUST remove the "Name override" field from the "Advanced options" section of the Create App experience.

#### Apps — Tile Management

- **FR-011**: System MUST display a delete button on each App tile.
- **FR-012**: System MUST allow users to delete an app via the tile delete button, with a confirmation step before deletion.
- **FR-013**: System MUST display app status on each App tile indicating whether a GitHub Parent Issue is actively executing in the app's project.

#### Apps — Detail View and History

- **FR-014**: System MUST show detailed GitHub Project information when a user selects an app (project name, status, link to project).
- **FR-015**: System MUST show Agent Pipeline information when a user selects an app (pipeline status, recent pipeline runs).
- **FR-016**: System MUST include Agent Pipeline updates in the app's History section, displayed in a format consistent with the Activity page.

### Key Entities

- **Chore**: A recurring task definition with a description, schedule, and configuration. Previously backed by GitHub Templates; now persisted exclusively in the database.
- **App**: A configured application within Solune, associated with a GitHub repository and project. Contains metadata including target branch (now defaulting to main), repository settings, and execution status.
- **App Status**: The current execution state of an app, derived from whether a GitHub Parent Issue is actively running in the app's associated project.
- **Agent Pipeline**: An automated workflow that executes within an app's context. Pipeline runs and updates are tracked and surfaced in the app's History.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can navigate the entire Chores page without encountering scroll bugs, page jumps, or content cutoff — 100% of page content is accessible without requiring a browser refresh.
- **SC-002**: Zero references to GitHub Templates or PR-based chore saving remain visible anywhere in the Chores page UI.
- **SC-003**: Users can complete the Create App flow in fewer steps than before, with the "Target branch" decision removed and settings reorganized under "Advanced options".
- **SC-004**: Users can delete an app from the Apps page in under 3 clicks (click delete → confirm → done).
- **SC-005**: Users can determine the execution status of any app at a glance from the App tiles without opening a detail view.
- **SC-006**: Users can view comprehensive app details (GitHub Project info and Agent Pipeline info) by selecting an app, without needing to navigate to GitHub separately.
- **SC-007**: Agent Pipeline updates appear in app History within the same refresh cycle as other activity entries, consistent with the Activity page format.

## Assumptions

- Chore definitions already have a database-backed storage mechanism available or in progress (per the requirement that definitions are "now saved in the database").
- The "Ritual Maintenance" section already exists on the Chores page as a target for relocated controls.
- The Activity page already displays Agent Pipeline updates in a defined format that can be reused for the app History section.
- App deletion is a soft-delete or includes appropriate cleanup of associated resources (GitHub issues, pipelines) to avoid orphaned data.
- The "Review upkeep cadence" scroll bug is a front-end layout or overflow issue, not a backend data problem.
