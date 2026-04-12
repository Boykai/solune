# Feature Specification: Simplify Page Headers for Focused UI

**Feature Branch**: `001-simplify-page-headers`
**Created**: 2026-04-12
**Status**: Draft
**Input**: User description: "Replace the large CelestialCatalogHero hero sections (~20% of viewport, ~350–450px tall) with a compact, single-row page header. This affects 6 pages that share the same component and reclaims significant vertical space."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compact Page Header Replaces Oversized Hero (Priority: P1)

As a user, I want page headers to be compact and information-dense so that I can see more of the actual page content without scrolling past large decorative hero sections.

**Why this priority**: The oversized hero sections consume ~20% of the viewport (~350–450px) on every catalog page. Reclaiming this space directly improves content visibility and task efficiency across all 6 affected pages. This is the core value of the feature.

**Independent Test**: Can be fully tested by navigating to any of the 6 affected pages and confirming the header occupies roughly 80–100px, displays eyebrow text, title, badge, and action buttons in a single row, and does not render any decorative elements (orbits, stars, beams, moonwell cards, or the "Current Ritual" aside).

**Acceptance Scenarios**:

1. **Given** a user navigates to the Projects page, **When** the page loads, **Then** the page header is a compact single-row layout occupying approximately 80–100px in height
2. **Given** a user navigates to any of the 6 affected pages (Projects, Agents, Agents Pipeline, Tools, Chores, Help), **When** the page loads, **Then** the header displays the eyebrow label, page title, badge (if provided), and action buttons — all within a single horizontal row
3. **Given** a user views any affected page, **When** the page loads, **Then** no decorative elements such as orbits, stars, moon beams, or the "Current Ritual" aside panel are visible in the header area

---

### User Story 2 - Stats Displayed as Compact Chips (Priority: P1)

As a user, I want page-level statistics presented as small inline chips rather than large cards so that I can quickly scan key metrics without them dominating the header area.

**Why this priority**: Stats are important contextual information but were previously rendered as large moonwell cards that competed with the primary content. Presenting them as compact chips preserves the information while reclaiming vertical space.

**Independent Test**: Can be fully tested by navigating to a page that displays stats (e.g., Projects page) and verifying stats appear as small pill/chip elements inline within the header, not as large card components.

**Acceptance Scenarios**:

1. **Given** a page provides stats data (e.g., item counts, status summaries), **When** the header renders, **Then** each stat is displayed as a small pill or chip element within the header row
2. **Given** a page provides multiple stats, **When** the header renders, **Then** all stats are visible inline without causing the header to exceed its target height

---

### User Story 3 - Description Shown as Single-Line Subtitle (Priority: P2)

As a user, I want the page description to appear as a concise single-line subtitle beneath the title so that I get context without the description consuming excessive vertical space.

**Why this priority**: Page descriptions provide useful context but previously consumed significant space. A single-line subtitle with expand-on-hover provides the best balance of discoverability and space efficiency.

**Independent Test**: Can be fully tested by navigating to any affected page that has a description, verifying it appears as a single truncated line, and then hovering over it to confirm the full text is revealed.

**Acceptance Scenarios**:

1. **Given** a page provides a description, **When** the header renders, **Then** the description is displayed as a single-line subtitle truncated with an ellipsis if it exceeds one line
2. **Given** a page description is truncated to one line, **When** the user hovers over the description, **Then** the description expands in place to reveal the full text

---

### User Story 4 - Mobile-Friendly Header Layout (Priority: P2)

As a mobile user, I want the compact header to adapt gracefully to smaller screens so that I can still access all essential header information without a cluttered interface.

**Why this priority**: Mobile users benefit most from reclaimed vertical space. The compact header must remain usable on narrow viewports without crowding essential elements.

**Independent Test**: Can be fully tested by viewing any affected page on a mobile viewport (≤768px width) and verifying the header remains readable, stats are hidden behind a toggle to avoid crowding, and action buttons remain accessible.

**Acceptance Scenarios**:

1. **Given** a user views an affected page on a mobile viewport (≤768px width), **When** the page loads, **Then** the header layout adapts to a stacked or wrapped arrangement that remains readable
2. **Given** a user views a page with stats on a mobile viewport, **When** the page loads, **Then** stats are hidden by default and accessible via a toggle control
3. **Given** a user views a page on a mobile viewport, **When** the page loads, **Then** action buttons remain visible and tappable

---

### User Story 5 - Dead Code and Orphaned Styles Removed (Priority: P3)

As a developer maintaining the codebase, I want the old CelestialCatalogHero component and its orphaned styles removed after migration so that the codebase stays clean and free of unused code.

**Why this priority**: Cleanup is important for long-term maintainability but delivers no direct user-facing value. It should follow the migration of all 6 pages.

**Independent Test**: Can be fully tested by searching the codebase for references to CelestialCatalogHero and its associated CSS classes (celestial-orbit-spin, celestial-twinkle, celestial-float, celestial-pulse-glow, catalog-hero-*, hanging-stars, moonwell) and confirming no orphaned references remain, all existing tests pass, and there are no type or lint errors.

**Acceptance Scenarios**:

1. **Given** all 6 pages have been migrated to the compact header, **When** a developer searches the codebase, **Then** the CelestialCatalogHero component file no longer exists
2. **Given** the CelestialCatalogHero component has been deleted, **When** a developer searches the global stylesheet, **Then** animation classes and styles exclusively used by the hero (celestial-orbit-spin, celestial-twinkle, celestial-float, celestial-pulse-glow, catalog-hero-*, hanging-stars) have been removed — unless still referenced by other components
3. **Given** cleanup is complete, **When** all frontend tests, linting, and type checks are run, **Then** everything passes with no errors

---

### User Story 6 - Existing Functionality Preserved (Priority: P1)

As a user, I want all existing page functionality (navigation, actions, filtering, content display) to continue working exactly as before after the header is replaced.

**Why this priority**: This is a visual/layout change, not a feature change. Preserving all existing behavior is non-negotiable — no regressions are acceptable.

**Independent Test**: Can be fully tested by exercising all interactive elements on each of the 6 affected pages (clicking action buttons, using filters, navigating to detail views) and verifying they work identically to the current behavior.

**Acceptance Scenarios**:

1. **Given** the compact header is in place on any affected page, **When** a user clicks an action button in the header, **Then** the action triggers the same behavior as before the migration
2. **Given** the compact header is in place, **When** a user interacts with page content below the header, **Then** all content, filtering, and navigation works identically to the previous layout

---

### Edge Cases

- What happens when a page provides no stats? The header renders without a stats section and maintains its compact layout.
- What happens when a page provides no description? The subtitle area is simply omitted; the header does not display empty space.
- What happens when a page provides no badge? The badge area is omitted; title and eyebrow shift to fill the available space.
- What happens when a page provides no action buttons? The right section of the header is empty; the layout remains balanced.
- What happens when description text is extremely long (hundreds of characters)? It is truncated to a single line with an ellipsis; hovering reveals the full text.
- How does the header behave on very narrow viewports (<320px)? The layout degrades gracefully — elements stack vertically rather than overlapping.
- What happens to stats on mobile? They are hidden by default behind a toggle to avoid crowding the narrow viewport.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST render a compact page header on all 6 affected pages (Projects, Agents, Agents Pipeline, Tools, Chores, Help) with a target height of approximately 80–100px
- **FR-002**: Compact header MUST display eyebrow text and page title on the left, badge in the center (when provided), and action buttons on the right in a single-row layout on desktop viewports
- **FR-003**: System MUST render stats as small pill/chip elements inline within the header, replacing the previous large moonwell card presentation
- **FR-004**: System MUST display the page description as a single-line subtitle (truncated with ellipsis if longer), with the full text revealed on hover
- **FR-005**: System MUST NOT render any decorative elements in the page header, including orbits, stars, moon, beams, or the "Current Ritual" aside panel
- **FR-006**: System MUST NOT include a `note` prop in the compact header; the "Current Ritual" aside is permanently removed
- **FR-007**: Compact header MUST accept the following props: eyebrow, title, description (as subtitle), badge, stats, actions, className
- **FR-008**: Compact header MUST adapt its layout for mobile viewports (≤768px) by stacking or wrapping elements to remain readable
- **FR-009**: On mobile viewports (≤768px), stats MUST be hidden by default and accessible via a toggle control
- **FR-010**: System MUST remove the CelestialCatalogHero component file after all 6 pages have been migrated
- **FR-011**: System MUST remove orphaned CSS animation classes and styles (celestial-orbit-spin, celestial-twinkle, celestial-float, celestial-pulse-glow, catalog-hero-*, hanging-stars, moonwell) from the global stylesheet — only if no other components reference them
- **FR-012**: All existing page functionality (actions, navigation, filtering, content display) MUST continue to work identically after the header replacement

### Key Entities

- **CompactPageHeader**: A reusable compact header component accepting eyebrow, title, description, badge, stats, actions, and className. Renders a single-row layout on desktop (~80–100px) and a stacked layout on mobile. Stats are rendered as inline pill/chip elements. Description is a single-line truncated subtitle with expand-on-hover.
- **Stat Chip**: An individual stat display element rendered as a small pill/chip within the header, replacing the previous moonwell card presentation. Each chip shows a label and value.

## Assumptions

- **Big-bang rollout**: All 6 pages will be migrated simultaneously rather than incrementally, since they all share the same hero component and the replacement is prop-compatible.
- **Description expand behavior**: The description single-line subtitle will expand on hover (using CSS line-clamp with hover override), not via a tooltip or separate modal.
- **Mobile breakpoint**: The responsive breakpoint for switching to mobile layout is ≤768px, following standard responsive design conventions.
- **Stats toggle on mobile**: The mobile stats toggle will be a simple show/hide control (e.g., chevron or "Show stats" link), not an accordion or modal.
- **Celestial theme preserved elsewhere**: Removing decorative elements from page headers does not affect the celestial theme used in the sidebar, global chrome, or other non-header components.
- **Moonwell class removal**: The `moonwell` CSS class should only be removed if no other components in the codebase reference it. If other components still use it, it must be preserved.
- **Shared CSS animations**: Celestial animation classes (e.g., `celestial-pulse-glow`, `celestial-orbit-spin`) should only be removed if they are exclusively used by the CelestialCatalogHero. If referenced by other components (such as CelestialLoader), they must be preserved.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Page header height on all 6 affected pages is reduced from ~350–450px to ~80–100px, reclaiming approximately 250–370px of vertical space per page
- **SC-002**: Users can see primary page content (first content item below the header) without scrolling on a standard 1080p desktop viewport on all 6 affected pages
- **SC-003**: All 6 affected pages load and render their compact headers with all provided information (eyebrow, title, badge, stats, actions) visible within the single-row layout
- **SC-004**: 100% of existing frontend tests continue to pass after the migration with no regressions
- **SC-005**: All interactive elements (action buttons, navigation links, filters) on the 6 affected pages continue to function identically after the header replacement
- **SC-006**: On mobile viewports (≤768px), the compact header renders without horizontal overflow and stats are accessible via a toggle
- **SC-007**: The codebase contains zero references to CelestialCatalogHero after cleanup, and zero orphaned CSS classes that were exclusively used by the hero component
- **SC-008**: All linting and type-checking pass with no new errors after the complete migration and cleanup
