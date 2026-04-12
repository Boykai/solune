# Feature Specification: Simplify Page Headers for Focused UI

**Feature Branch**: `001-simplify-page-headers`  
**Created**: 2026-04-12  
**Status**: Draft  
**Input**: User description: "Replace the large CelestialCatalogHero hero sections (~20% of viewport, ~350–450px tall) with a compact, single-row page header. This affects 6 pages that share the same component and reclaims significant vertical space."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compact Page Header Replaces Hero Sections (Priority: P1)

As a user navigating the application, I want page headers to be compact and space-efficient so that I can see more of the actual page content without scrolling past a large decorative hero section.

**Why this priority**: This is the core value proposition of the feature. The current hero sections consume ~20% of the viewport (~350–450px), pushing primary content below the fold. Reclaiming this space directly improves usability and task efficiency across all 6 affected pages.

**Independent Test**: Can be fully tested by visiting any of the 6 affected pages (Projects, Agents, Agents Pipeline, Tools, Chores, Help) and confirming the header occupies ~80–100px instead of ~350–450px, displays the eyebrow, title, badge, stats, and action buttons in a single-row layout, and that the primary page content is immediately visible without scrolling.

**Acceptance Scenarios**:

1. **Given** a user visits the Projects page, **When** the page loads, **Then** the page header displays in a single row at ~80–100px height with eyebrow text, title, badge, stats as pill/chip elements, and action buttons — all without decorative orbits, stars, beams, or aside panels.
2. **Given** a user visits any of the 6 affected pages (Projects, Agents, Agents Pipeline, Tools, Chores, Help), **When** the page loads, **Then** the compact header is used consistently across all pages with the same layout structure.
3. **Given** a user visits a page that previously had a `note` prop in the hero, **When** the compact header renders, **Then** the note content is not displayed (prop has been removed).

---

### User Story 2 - Stats Displayed as Inline Chips (Priority: P1)

As a user reviewing page-level statistics, I want stats displayed as small inline pill/chip elements so that they are visible at a glance without consuming excessive vertical space.

**Why this priority**: Stats are critical contextual information (e.g., project counts, agent counts). Displaying them as compact chips instead of large moonwell cards preserves this information while supporting the space-saving goal.

**Independent Test**: Can be tested by visiting any page with stats (e.g., Projects page with project count stats) and confirming stats appear as small pill/chip elements inline within the header row, not as separate large card components.

**Acceptance Scenarios**:

1. **Given** a page has stats data (e.g., Projects page showing total projects, active projects), **When** the compact header renders, **Then** stats appear as small pill/chip elements arranged inline within the header.
2. **Given** a page has multiple stats, **When** displayed as chips, **Then** all stats are visible without requiring additional vertical space or scrolling.

---

### User Story 3 - Description as Single-Line Subtitle (Priority: P2)

As a user reading page context, I want the page description shown as a concise single-line subtitle that expands on hover so that I get context without the description dominating the header.

**Why this priority**: Description provides useful context but is secondary to the title and stats. A single-line subtitle with expand-on-hover balances information density with space efficiency.

**Independent Test**: Can be tested by visiting a page with a description, confirming it appears truncated to a single line, and hovering to see the full text expand.

**Acceptance Scenarios**:

1. **Given** a page has a long description, **When** the compact header renders, **Then** the description is truncated to a single line.
2. **Given** a page description is truncated, **When** the user hovers over it, **Then** the full description text becomes visible.
3. **Given** a page has a short description that fits in one line, **When** the compact header renders, **Then** the description is fully visible without truncation.

---

### User Story 4 - Mobile-Friendly Header (Priority: P2)

As a mobile user, I want the compact header to adapt gracefully to smaller screens so that I can still access all header information without the layout breaking or becoming crowded.

**Why this priority**: Mobile usability is important for users accessing the application on phones or tablets. Stats and actions need special handling on smaller viewports to avoid crowding.

**Independent Test**: Can be tested by viewing any affected page on a mobile viewport (≤768px) and confirming the header adapts: stats are hidden behind a toggle, and the layout remains usable.

**Acceptance Scenarios**:

1. **Given** a user views a page on a mobile viewport (≤768px), **When** the compact header renders, **Then** stats are hidden by default to avoid crowding the limited space.
2. **Given** stats are hidden on mobile, **When** the user taps a toggle/expand control, **Then** the stats become visible.
3. **Given** a user views a page on a desktop viewport (>768px), **When** the compact header renders, **Then** stats are always visible inline without a toggle.

---

### User Story 5 - Dead Code and Decorative CSS Removed (Priority: P2)

As a developer maintaining the codebase, I want the old CelestialCatalogHero component and its associated decorative CSS removed so that the codebase stays clean and doesn't carry unused code.

**Why this priority**: Dead code increases maintenance burden and confusion. Removing the old hero component and orphaned CSS animations ensures the codebase reflects the current design intent.

**Independent Test**: Can be tested by confirming the CelestialCatalogHero component file no longer exists, that no import references to it remain, and that orphaned CSS classes (celestial-orbit-spin, celestial-twinkle, celestial-float, celestial-pulse-glow, catalog-hero-*, hanging-stars) are removed from stylesheets.

**Acceptance Scenarios**:

1. **Given** the migration to CompactPageHeader is complete, **When** a developer searches the codebase for CelestialCatalogHero, **Then** no references are found (no imports, no usages, no component file).
2. **Given** the old hero decorative CSS classes are no longer referenced, **When** a developer inspects the global CSS, **Then** the orphaned animation classes (celestial-orbit-spin, celestial-twinkle, celestial-float, celestial-pulse-glow, catalog-hero-*, hanging-stars, moonwell if unreferenced) have been removed.

---

### User Story 6 - Consistent Header Experience Across All Pages (Priority: P1)

As a user navigating between pages, I want all 6 affected pages to use the same compact header component so that the experience feels consistent and predictable.

**Why this priority**: Consistency across pages reduces cognitive load. All 6 pages currently share the same hero component, so the replacement must also be shared to maintain UI uniformity.

**Independent Test**: Can be tested by navigating between all 6 affected pages and confirming each uses the identical compact header component with the same layout structure, differing only in content (title, eyebrow, stats, etc.).

**Acceptance Scenarios**:

1. **Given** a user navigates from Projects to Agents to Tools pages, **When** each page loads, **Then** the header component is visually identical in structure — same layout, same sizing, same element positioning.
2. **Given** the 6 affected pages, **When** inspected, **Then** all use the same shared compact header component (not 6 different implementations).

---

### Edge Cases

- What happens when a page has no stats to display? The compact header should render without the stats section, and the remaining elements should fill the available space gracefully.
- What happens when a page has no badge? The badge area should collapse, and the title/eyebrow should remain properly aligned.
- What happens when a page has no action buttons? The right-aligned actions section should collapse without leaving empty space.
- How does the header behave when the title is very long? The title should truncate or wrap gracefully without breaking the single-row layout on desktop.
- What happens on very narrow viewports (<320px)? The header should stack elements vertically if needed, maintaining readability.
- What happens when stats toggle is activated on mobile and then viewport is resized to desktop? Stats should become permanently visible (desktop behavior) without requiring the toggle.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a compact page header component that renders in a single-row layout with a height target of ~80–100px.
- **FR-002**: The compact header MUST display an eyebrow label and title on the left side of the header row.
- **FR-003**: The compact header MUST display a badge element in the center of the header row (when provided).
- **FR-004**: The compact header MUST display action buttons on the right side of the header row (when provided).
- **FR-005**: The compact header MUST render stats as small pill/chip elements inline within the header (when provided).
- **FR-006**: The compact header MUST display the page description as a single-line subtitle that truncates long text.
- **FR-007**: The truncated description MUST expand to show full text when the user hovers over it.
- **FR-008**: On mobile viewports (≤768px), stats MUST be hidden by default and accessible via a toggle/expand control.
- **FR-009**: On desktop viewports (>768px), stats MUST be always visible without requiring user interaction.
- **FR-010**: The compact header MUST NOT include any decorative elements such as orbits, stars, beams, moon graphics, or aside panels.
- **FR-011**: The compact header MUST NOT accept or render a `note` prop.
- **FR-012**: The compact header MUST accept the following props: eyebrow, title, description (as subtitle), badge, stats, actions, and className.
- **FR-013**: All 6 affected pages (Projects, Agents, Agents Pipeline, Tools, Chores, Help) MUST use the same shared compact header component.
- **FR-014**: The old CelestialCatalogHero component file MUST be deleted after all pages are migrated.
- **FR-015**: All orphaned CSS animations and classes associated with the old hero component MUST be removed from global stylesheets.
- **FR-016**: The compact header MUST gracefully handle missing optional props (no stats, no badge, no actions) without layout breakage.

### Key Entities

- **CompactPageHeader**: A reusable, compact page header component that replaces CelestialCatalogHero. Accepts eyebrow, title, description, badge, stats, actions, and className props. Renders in a single-row layout at ~80–100px height.
- **Stat Chip**: A small pill/chip element that displays a single stat (label + value). Multiple chips render inline within the header.
- **Page**: One of the 6 application pages (Projects, Agents, Agents Pipeline, Tools, Chores, Help) that consumes the compact header component with page-specific content.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Page headers across all 6 affected pages occupy no more than 100px of vertical space, reduced from the previous ~350–450px (a reduction of at least 70%).
- **SC-002**: Users can see primary page content (e.g., project lists, agent cards) without scrolling on a standard 1080p viewport.
- **SC-003**: All 6 affected pages render the compact header consistently, with identical layout structure differing only in content.
- **SC-004**: On mobile viewports (≤768px), the header adapts without horizontal overflow or layout breakage.
- **SC-005**: All existing automated tests continue to pass after the migration with no regressions.
- **SC-006**: No references to the old CelestialCatalogHero component remain in the codebase after cleanup.
- **SC-007**: No lint errors or type errors are introduced by the changes.
- **SC-008**: The compact header loads and renders on each page in under 1 second on a standard connection.

## Assumptions

- The celestial/space theme is preserved in other parts of the application (sidebar, global chrome) and does not need to be represented in page headers.
- The "Current Ritual" aside card was duplicating the page description and is intentionally removed without replacement.
- The `note` prop is not needed in the compact header; any information previously in notes is either redundant or can be accessed elsewhere.
- The `moonwell` CSS class may still be referenced by other components outside the hero; it should only be removed if confirmed unreferenced after CelestialCatalogHero deletion.
- A big-bang rollout (all 6 pages at once) is preferred over gradual rollout since all pages share the same component and the replacement is prop-compatible.
- Standard web application performance expectations apply (page loads under 3 seconds, interactive within 1 second).
- The mobile breakpoint of ≤768px follows common responsive design conventions.
