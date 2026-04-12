# Feature Specification: Simplify Page Headers for Focused UI

**Feature Branch**: `copilot/speckitplan-create-compact-header`  
**Created**: 2026-04-11  
**Status**: Draft  
**Input**: User description: "Simplify Page Headers for Focused UI — Replace the large CelestialCatalogHero hero sections (~20% of viewport, ~350–450px tall) with a compact, single-row page header across 6 pages."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compact Page Header Reclaims Vertical Space (Priority: P1)

A user navigates to any of the six main pages (Projects, Agents, Agents Pipeline, Tools, Chores, Help). Instead of seeing a large decorative hero section that occupies roughly 20% of the viewport (~350–450px tall), they see a compact, single-row header (~80–100px tall) that still presents all essential information — page identity (eyebrow and title), contextual badge, and action buttons — without requiring the user to scroll past decorative content to reach the page's primary working area.

**Why this priority**: The hero sections consume significant vertical real estate on every major page. Reducing header height directly increases the visible working area for content that users interact with (board columns, agent catalogs, tool lists, chore templates). This is the core value of the feature — every user benefits immediately on every page load.

**Independent Test**: Navigate to each of the six affected pages and verify that the header occupies approximately 80–100px of vertical space, all essential information (eyebrow, title, badge, actions) remains visible, and the primary content area starts higher on the page than before.

**Acceptance Scenarios**:

1. **Given** a user navigates to the Projects page, **When** the page loads, **Then** the header is rendered as a single-row compact layout occupying no more than ~100px of vertical space.
2. **Given** a user navigates to any of the six affected pages, **When** the page loads, **Then** the eyebrow label, page title, and action buttons are all visible in the header without scrolling.
3. **Given** a page has a contextual badge (e.g., repository or project name), **When** the header renders, **Then** the badge is displayed in the header row.
4. **Given** the previous hero occupied ~350–450px, **When** the compact header is used instead, **Then** the primary content area gains approximately 250–370px of additional visible space above the fold.

---

### User Story 2 - Stats Displayed as Compact Inline Chips (Priority: P1)

A user viewing a page with contextual statistics (e.g., board columns count, pipeline count, assignment count) sees these stats rendered as small pill or chip elements inline with the header, rather than as large decorative moonwell cards that consumed significant horizontal and vertical space.

**Why this priority**: Stats provide valuable at-a-glance context. Displaying them as compact chips preserves this value while eliminating the large card layout. This is essential to the compact header working correctly — without chip-style stats, the header cannot stay within its height target.

**Independent Test**: Navigate to a page with stats (e.g., Projects page with 4 stats) and verify that each stat is displayed as a small inline chip showing label and value, and that all stats fit within the single-row header layout.

**Acceptance Scenarios**:

1. **Given** a page provides stats (label/value pairs), **When** the compact header renders, **Then** each stat appears as a small pill/chip element showing both the label and value.
2. **Given** a page has multiple stats (e.g., 4 stats on the Projects page), **When** the header renders on desktop, **Then** all stats are visible inline without overflowing the header row.
3. **Given** a page has no stats (e.g., Help page), **When** the header renders, **Then** the stat area is omitted and the header layout adjusts gracefully.

---

### User Story 3 - Description as Single-Line Subtitle (Priority: P2)

A user reading the page header sees the page description rendered as a single-line subtitle below the title. The full description is accessible by hovering, which expands the text to show all content. This keeps the header compact by default while preserving the descriptive context for users who want it.

**Why this priority**: Descriptions provide helpful context but are not essential for every page visit. A single-line treatment with hover-to-expand balances information density with compactness. It's a P2 because the header is still functional without this refinement.

**Independent Test**: Navigate to a page with a description, verify the description is visible as a single truncated line, hover over it, and verify the full text becomes visible.

**Acceptance Scenarios**:

1. **Given** a page has a description, **When** the compact header renders, **Then** the description appears as a single line of text, truncated with an ellipsis if it exceeds the available width.
2. **Given** the description is truncated, **When** the user hovers over it, **Then** the full description text is revealed.
3. **Given** a page has a short description that fits on one line, **When** the header renders, **Then** the description is displayed in full without truncation or hover behavior.

---

### User Story 4 - Stats Toggle on Mobile Viewports (Priority: P2)

A user on a mobile device sees the compact header without stats cluttering the limited screen space. Stats are hidden by default on mobile and accessible via a toggle control, keeping the header clean and focused on the essentials (title, badge, actions) when screen real estate is most constrained.

**Why this priority**: Mobile viewports cannot comfortably display all header elements in a single row. Hiding stats behind a toggle prevents the compact header from becoming crowded on small screens while still making the data accessible when needed.

**Independent Test**: View any stats-bearing page on a mobile viewport, verify stats are hidden by default, activate the toggle, and verify stats become visible.

**Acceptance Scenarios**:

1. **Given** a user views a page with stats on a mobile-width viewport, **When** the header renders, **Then** the stats are hidden by default.
2. **Given** stats are hidden on mobile, **When** the user activates the stats toggle, **Then** all stats become visible.
3. **Given** a page has no stats, **When** the header renders on mobile, **Then** no toggle control is displayed.

---

### User Story 5 - Decorative Elements Removed from Page Headers (Priority: P3)

A user navigating the application no longer sees animated celestial decorations (orbiting rings, twinkling stars, floating moons, glowing beams, hanging stars) in page headers. The celestial theme is preserved elsewhere in the application (sidebar, global chrome) but headers are clean and content-focused.

**Why this priority**: Removing decorative elements reduces visual noise and loading overhead in headers. The theme is maintained elsewhere, so the brand identity is preserved. This is P3 because it's a natural consequence of replacing the hero component — it doesn't require separate effort.

**Independent Test**: Navigate to each affected page and verify that no animated decorative elements (orbits, stars, moons, beams) appear in the header area.

**Acceptance Scenarios**:

1. **Given** a user navigates to any of the six affected pages, **When** the header renders, **Then** no animated celestial elements (orbits, twinkling stars, floating moons, pulsing glows, gradient beams) are present in the header.
2. **Given** the old hero component displayed a "Current Ritual" aside panel, **When** the compact header renders, **Then** no aside panel or note section is present.

---

### User Story 6 - Consistent Header Experience Across All Six Pages (Priority: P1)

A user navigating between the six main pages (Projects, Agents, Agents Pipeline, Tools, Chores, Help) experiences a consistent header layout across all pages. Each page uses the same compact header format with its own eyebrow, title, badge, stats, and actions, creating a unified and predictable navigation experience.

**Why this priority**: Consistency across all six pages is essential for the feature to deliver its full value. A partial rollout would create a jarring experience where some pages have large heroes and others have compact headers.

**Independent Test**: Navigate to all six pages in sequence and verify each uses the same compact header layout pattern, with only the content (eyebrow, title, stats, actions) differing per page.

**Acceptance Scenarios**:

1. **Given** a user navigates between all six affected pages, **When** each page loads, **Then** each page uses the same compact header layout with the same structural elements (eyebrow, title, badge area, stats area, actions area).
2. **Given** the Help page currently has fewer props (no badge, no stats), **When** the compact header renders on the Help page, **Then** the header gracefully omits missing sections while maintaining the same overall layout structure.

---

### Edge Cases

- What happens when a page has no badge, no stats, and only one action (e.g., Help page)? The header should render cleanly with only the eyebrow, title, description, and single action button visible.
- What happens when stat values are very long strings (e.g., a long pipeline name)? Stat chips should truncate long values with an ellipsis to prevent layout overflow.
- What happens when there are many action buttons (e.g., Tools page has 3 buttons)? The actions area should accommodate multiple buttons without breaking the single-row layout on desktop, and should wrap gracefully on narrower viewports.
- What happens when the browser viewport is resized from desktop to mobile while the page is open? The header should responsively adjust, hiding stats and adapting layout without requiring a page reload.
- What happens when the badge text is long (e.g., "organization-name/very-long-repository-name")? The badge should truncate with an ellipsis rather than pushing other header elements out of alignment.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST display a compact, single-row page header on all six affected pages (Projects, Agents, Agents Pipeline, Tools, Chores, Help) with a height target of approximately 80–100px.
- **FR-002**: The compact header MUST display the following elements when provided: eyebrow label, page title, description (as subtitle), contextual badge, stats (as pill/chip elements), and action buttons.
- **FR-003**: The compact header MUST arrange content in a single-row layout: eyebrow and title on the left, badge in the center, and action buttons on the right.
- **FR-004**: The page description MUST be rendered as a single-line subtitle, truncated with an ellipsis when it exceeds the available width, and MUST expand to show the full text on hover.
- **FR-005**: Stats MUST be rendered as small pill/chip elements rather than large card-style layouts.
- **FR-006**: Stats MUST be hidden by default on mobile viewports and accessible via a toggle control.
- **FR-007**: The compact header MUST NOT include any decorative animated elements (orbiting rings, twinkling stars, floating moons, gradient beams, hanging stars, pulsing glows).
- **FR-008**: The compact header MUST NOT include a "Current Ritual" aside panel or a dedicated note section.
- **FR-009**: The compact header MUST gracefully handle missing optional props (badge, stats, actions) by omitting those sections without breaking the layout.
- **FR-010**: All six pages MUST use the same compact header layout to ensure visual consistency across the application.
- **FR-011**: The previous hero section and any visual styles exclusively used by it MUST be removed from the codebase after all pages have been migrated.
- **FR-012**: All existing automated tests MUST continue to pass after the migration, with no regressions introduced.

### Key Entities

- **Compact Page Header**: The new single-row header element that replaces the hero section on all six pages. Displays eyebrow, title, description, badge, stats, actions, and supports custom styling. Does not include a "Current Ritual" note section.
- **Stat Chip**: A small pill-shaped inline element displaying a label and value pair, used to present page-level statistics compactly within the header row.
- **Affected Pages**: The six pages sharing the hero component — Projects, Agents, Agents Pipeline, Tools, Chores, and Help — all of which must be migrated simultaneously.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All six affected pages display a compact header that occupies no more than approximately 100px of vertical space, down from ~350–450px — a reduction of at least 70% in header height.
- **SC-002**: Users can see the primary content area (board, catalog, tool list) without scrolling past the header on a standard 1080p viewport (1920×1080).
- **SC-003**: All essential information (eyebrow, title, badge, actions) remains visible and accessible in the compact header on every affected page.
- **SC-004**: On mobile viewports (≤768px width), the header remains usable and does not overflow or obscure content, with stats accessible via a toggle.
- **SC-005**: No animated decorative elements are present in any page header after the migration.
- **SC-006**: All existing automated tests pass without modification (except tests specifically for the removed hero component, which are updated or removed).
- **SC-007**: The six pages present a visually consistent header experience — same layout structure, same spacing, same interaction patterns — differing only in per-page content (eyebrow text, title, stats, actions).
- **SC-008**: The removed hero section and its exclusively-used visual styles are no longer present in the codebase, leaving no dead code.

## Assumptions

- The big-bang rollout approach (migrating all six pages simultaneously) is preferred over a gradual rollout because all pages share the same hero component, making a simultaneous swap simpler and avoiding an inconsistent intermediate state.
- The ~80–100px height target is a guideline, not a hard constraint. Minor variance is acceptable as long as the header remains visually compact and single-row on desktop.
- The celestial theme is preserved in other parts of the application (sidebar, global chrome), so removing decorative elements from headers does not diminish the overall brand identity.
- The "Current Ritual" aside card is removed entirely because it duplicated the page description and consumed significant horizontal space (~22rem on large screens) without adding unique value.
- Stats on the Help page are not applicable (the Help page currently passes no stats), so the compact header must handle the zero-stats case gracefully.
- The description hover-to-expand behavior uses standard interaction patterns (e.g., CSS line-clamp with hover expansion) and does not require complex scripting.
- Mobile breakpoint for hiding stats aligns with the application's existing responsive breakpoints.
- Action buttons vary per page (1–3 buttons, mix of link and click handlers) and the compact header must accommodate this range without layout issues.
