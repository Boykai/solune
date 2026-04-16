# Feature Specification: Agents Page UI Improvements

**Feature Branch**: `003-agents-page-ui`
**Created**: 2026-04-16
**Status**: Draft
**Input**: User description: "Agents Page UI Improvements — fix AddAgentModal viewport issue, reorder sections and remove Featured Agents, make sections collapsible"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add Agent Modal Is Fully Visible (Priority: P1)

A user clicks the "+ Add Agent" button on the Agents page to configure a new agent. The modal dialog opens and is fully visible in the viewport. When the modal content is taller than the viewport (e.g., an agent with many configuration fields), the user can scroll within the overlay to see the entire modal, starting from the top. The modal remains centered when its content is shorter than the viewport.

**Why this priority**: This is a usability bug fix. Users currently cannot see or interact with the top portion of the modal when content exceeds viewport height, blocking agent configuration entirely.

**Independent Test**: Can be fully tested by opening the Add Agent modal with varying viewport heights and verifying the modal top is always reachable by scrolling.

**Acceptance Scenarios**:

1. **Given** the Agents page is loaded and the user clicks "+ Add Agent", **When** the modal content fits within the viewport, **Then** the modal appears vertically centered on screen.
2. **Given** the Agents page is loaded and the user clicks "+ Add Agent", **When** the modal content is taller than the viewport, **Then** the modal starts at the top of the overlay and the user can scroll down to see all content.
3. **Given** the Add Agent modal is open with tall content, **When** the user scrolls within the modal overlay, **Then** the top of the modal (including its title and close button) is reachable without the modal being clipped above the visible area.

---

### User Story 2 - Reorganized Agents Page Layout (Priority: P1)

A user navigates to the Agents page and sees a streamlined layout. The sections render in a clear, logical order: Quick Actions, Save Banner (when applicable), Pending Changes (when applicable), Catalog Controls (project agents filter/sort/grid), and then the Awesome Catalog (community agents browser). The formerly present "Featured Agents" section is no longer displayed.

**Why this priority**: Removing clutter (Featured Agents) and reordering sections improves discoverability of the most-used controls. Catalog Controls for project agents should appear before the community catalog since users primarily manage their own project agents.

**Independent Test**: Can be fully tested by loading the Agents page and verifying the rendered section order visually and in the DOM.

**Acceptance Scenarios**:

1. **Given** the Agents page loads successfully with agents present, **When** the user views the page, **Then** sections appear in this order: Quick Actions → Save Banner → Pending Changes → Catalog Controls → Awesome Catalog.
2. **Given** the Agents page loads successfully, **When** the user inspects the page, **Then** there is no "Featured Agents" section anywhere on the page.
3. **Given** the Agents page is in a loading or error state, **When** the page transitions to the loaded state, **Then** the Catalog Controls section appears only when agents data is available (guarded by the existing loading/error check), while the Awesome Catalog section renders unconditionally.

---

### User Story 3 - Collapsible Page Sections (Priority: P2)

A user on the Agents page can collapse and expand individual sections by clicking a chevron icon in each section header. This allows users to focus on the section they care about and hide others to reduce visual noise. All sections default to expanded so that the existing user experience is preserved on page load.

**Why this priority**: This is a usability enhancement that improves information density management. Users who frequently use the Agents page can collapse sections they rarely need, but new users see everything by default.

**Independent Test**: Can be fully tested by clicking each section's chevron and verifying the section body toggles visibility, and that page reload restores all sections to expanded.

**Acceptance Scenarios**:

1. **Given** the Agents page is loaded with all sections visible, **When** the user clicks the chevron icon on the "Pending Changes" section header, **Then** the Pending Changes section body collapses (hides) and the chevron rotates to indicate collapsed state.
2. **Given** a section is collapsed, **When** the user clicks the chevron icon on that section header again, **Then** the section body expands (shows) and the chevron rotates back to the expanded state.
3. **Given** the Agents page is loaded for the first time (or after a full page refresh), **When** the user views the page, **Then** all sections (Pending Changes, Catalog Controls, Awesome Catalog) are expanded by default.
4. **Given** any section is collapsed, **When** the user interacts with other sections (e.g., filtering agents in Catalog Controls), **Then** the collapsed state of other sections is preserved and does not change.

---

### Edge Cases

- What happens when the Agents page loads with zero agents? The Catalog Controls section remains hidden (existing guard: `!isLoading && !error && agents?.length > 0`), but the Awesome Catalog still renders.
- What happens when a user resizes the browser window while the Add Agent modal is open? The modal should remain scrollable and the top should stay accessible.
- What happens when a section is collapsed and its underlying data changes (e.g., pending changes are saved)? The section should maintain its collapsed state; it should not auto-expand when data updates.
- What happens when all collapsible sections are collapsed? The page should still render the Quick Actions and Save Banner sections normally (these are not collapsible).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Add Agent modal overlay MUST allow scrolling to the top of the modal when content exceeds viewport height.
- **FR-002**: The Add Agent modal MUST remain visually centered when its content fits within the viewport.
- **FR-003**: The "Featured Agents" section MUST be completely removed from the Agents page, including all associated display logic and computed values used exclusively by that section.
- **FR-004**: The Agents page MUST render its loaded-state sections in this order: Quick Actions → Save Banner → Pending Changes → Catalog Controls → Awesome Catalog.
- **FR-005**: The Catalog Controls section MUST remain guarded by the existing condition that checks for loaded, non-error state with agents present.
- **FR-006**: The Awesome Catalog section MUST continue to render unconditionally (regardless of loading/error state).
- **FR-007**: The Pending Changes, Catalog Controls, and Awesome Catalog sections MUST each have a clickable chevron icon in their header that toggles visibility of the section body.
- **FR-008**: All collapsible sections MUST default to expanded (visible) state on page load.
- **FR-009**: The chevron icon MUST visually indicate the current collapsed/expanded state (e.g., rotation or direction change).
- **FR-010**: Collapsing or expanding one section MUST NOT affect the state of other sections.
- **FR-011**: All dead code associated with the removed Featured Agents section MUST be cleaned up, including unused imports, computed values, and state variables.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can access and interact with the full Add Agent modal content regardless of viewport size — the modal top is never clipped above the visible area.
- **SC-002**: The Agents page presents sections in the defined order (Quick Actions → Save Banner → Pending Changes → Catalog Controls → Awesome Catalog) with no Featured Agents section present.
- **SC-003**: Users can collapse and expand each of the three designated sections (Pending Changes, Catalog Controls, Awesome Catalog) independently with a single click.
- **SC-004**: Page load preserves existing user experience — all sections are expanded by default.
- **SC-005**: The application builds without errors and all existing agent-related tests continue to pass after changes.
- **SC-006**: No unused code (imports, variables, computed values) related to the removed Featured Agents section remains in the codebase.

## Assumptions

- The existing inner dialog element already has styling that centers the modal vertically when content is short and allows scroll-to-top when content is tall. The fix only requires changing the outer overlay alignment from center-aligned to start-aligned.
- A downward-pointing chevron icon is already available in the project's icon library.
- The collapsible section pattern follows existing patterns used elsewhere in the application for section toggle behavior, using inline state management rather than introducing a new reusable component.
- Collapse state is ephemeral (not persisted to storage). A page refresh resets all sections to expanded.
- The Quick Actions and Save Banner sections are NOT made collapsible — only Pending Changes, Catalog Controls, and Awesome Catalog sections receive collapsible behavior.

## Scope Boundaries

### In Scope

- Fix AddAgentModal viewport alignment issue
- Remove Featured Agents section and all exclusively-related code
- Reorder Catalog Controls above Awesome Catalog
- Add collapsible toggle to Pending Changes, Catalog Controls, and Awesome Catalog sections
- Clean up unused imports and variables

### Out of Scope

- Persisting collapse state across sessions (e.g., localStorage)
- Adding animation/transitions to collapse/expand behavior (unless trivially available)
- Refactoring collapsible behavior into a reusable component
- Changes to the Quick Actions or Save Banner sections
- Any changes to agent data fetching, filtering, or sorting logic
- Mobile-specific responsive design changes
