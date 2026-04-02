# Feature Specification: UI/UX Responsive & Mobile Review

**Feature Branch**: `532-uiux-responsive-mobile-review`  
**Created**: 2026-04-02  
**Status**: Draft  
**Input**: User description: "Systematic audit of all Solune frontend surfaces for responsive, modern, reactive, and mobile-friendly design. Research found 1 high, 6 medium, and 12+ low-severity gaps across board, chat, pipeline, settings, and shared layout."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Mobile Chat Usability (Priority: P1)

A user opens the Solune chat on their phone (375px screen) to ask a question or review a task. When they tap the chat input field, the virtual keyboard slides up. The chat input must remain visible and usable above the keyboard so the user can type their message, review previews, and send without scrolling or losing context.

**Why this priority**: The virtual keyboard overlapping the chat input is the only high-severity issue identified. It blocks core functionality — users literally cannot see what they are typing on mobile. This affects every mobile chat interaction.

**Independent Test**: Can be fully tested by opening the chat on a mobile device (or emulator), tapping the input field, and verifying the input stays visible above the keyboard. Delivers immediate value for all mobile chat users.

**Acceptance Scenarios**:

1. **Given** a user on a 375px-wide mobile device with the chat open, **When** they tap the message input and the virtual keyboard appears, **Then** the chat input field remains visible above the keyboard and the user can type and send a message.
2. **Given** a user on an iOS device with a notch (safe area), **When** the chat is open in fullscreen, **Then** the chat content respects safe area insets and no content is hidden behind the notch or home indicator.
3. **Given** a user viewing a task preview or plan preview in chat on mobile, **When** the preview renders, **Then** the preview fits within the viewport width without horizontal scrolling.
4. **Given** a user tapping a chat toolbar button on mobile, **When** the button is rendered, **Then** the touch target is at least 44×44 pixels.

---

### User Story 2 — Mobile Navigation & Layout Shell (Priority: P1)

A user navigates the Solune application on a mobile phone. The sidebar, top bar, breadcrumbs, notifications, and command palette must all be usable on a narrow screen. Touch targets must be large enough for finger taps, popover menus must not overflow the screen, and navigation elements must truncate gracefully rather than break the layout.

**Why this priority**: Navigation is the gateway to every feature. If users cannot navigate on mobile, no other responsive fix matters. Touch target sizing and layout overflow are foundational issues.

**Independent Test**: Can be tested by navigating through the application on a 375px viewport, verifying all navigation elements are reachable and usable without horizontal overflow.

**Acceptance Scenarios**:

1. **Given** a user on a 375px mobile screen, **When** they open the sidebar, **Then** it appears as a full-height overlay with a dismissable backdrop, traps focus within itself, and closes when the backdrop is tapped.
2. **Given** a user on mobile, **When** they try to tap the Help button in the top bar, **Then** the button touch target is at least 44×44 pixels.
3. **Given** a deep navigation path (e.g., Home > Project > Board > Column > Issue), **When** rendered on a narrow screen, **Then** breadcrumb segments truncate with ellipsis rather than causing horizontal overflow.
4. **Given** a user on a 375px screen, **When** the notification dropdown opens, **Then** the dropdown panel fits within the visible viewport without overflowing off-screen.
5. **Given** a user on mobile, **When** they open the command palette, **Then** it occupies the full width of the screen and results are scrollable.

---

### User Story 3 — Kanban Board Mobile Experience (Priority: P2)

A user manages their project board on a mobile phone. They need to view columns, scroll between them, read issue cards, and potentially drag issues. The board must be swipe-friendly on narrow screens, provide visual cues that more content exists beyond the viewport, and display columns at an appropriate height for mobile.

**Why this priority**: The project board is a core feature of Solune. While it functions on mobile today, the experience has several medium-severity usability gaps: columns are too tall, no scroll affordance, no snap behavior, and potential horizontal overflow with many columns.

**Independent Test**: Can be tested by loading a board with 3+ columns on a 375px viewport, verifying horizontal scroll works with snap behavior, gradient affordance is visible, and columns are appropriately sized.

**Acceptance Scenarios**:

1. **Given** a board with 3+ columns on a mobile screen, **When** the user scrolls horizontally, **Then** the scroll snaps to each column start for predictable positioning.
2. **Given** a board with off-screen columns, **When** the board first loads on mobile, **Then** a visual gradient on the trailing edge signals that more content exists to the right.
3. **Given** a board column on mobile, **When** rendered, **Then** the column height is proportionally shorter than on desktop to fit the mobile viewport.
4. **Given** an issue card on a narrow screen, **When** it renders, **Then** the card text, labels, and assignees truncate gracefully without layout breakage.

---

### User Story 4 — Pipeline View on Mobile (Priority: P2)

A user reviews their project pipeline on a mobile device. Pipeline stages must be readable with appropriately scaled font sizes and widths, and the flow graph must be navigable via touch gestures (scroll and zoom).

**Why this priority**: Pipeline is a key visualization feature. Stage sizing and font scaling are medium-to-low severity issues that can make the pipeline difficult to read on mobile.

**Independent Test**: Can be tested by loading the pipeline view on a 375px viewport and verifying stage widths fit, text is readable, and the flow graph responds to touch gestures.

**Acceptance Scenarios**:

1. **Given** a pipeline with multiple stages on mobile, **When** rendered, **Then** each stage has a minimum width that fits on a 375px screen without overlap or overflow.
2. **Given** pipeline stage names, **When** rendered on mobile, **Then** font sizes scale down appropriately for the smaller viewport.
3. **Given** the pipeline flow graph on a touch device, **When** a user performs pinch-to-zoom or swipe gestures, **Then** the graph responds with smooth zoom and scroll behavior.

---

### User Story 5 — Modals & Forms on Mobile (Priority: P2)

A user interacts with modals and forms (e.g., creating an issue, editing settings, adding an agent) on their phone. Modals must scroll correctly when content exceeds the screen, form inputs must be full-width on mobile, validation errors must not push content off-screen, and the virtual keyboard must not hide form fields.

**Why this priority**: Modals are the primary interaction pattern for creating and editing content. If users cannot complete forms on mobile, productivity drops. The settings page padding and modal scrollability affect multiple workflows.

**Independent Test**: Can be tested by opening each modal on a 375px viewport, filling in forms, verifying scroll behavior, and confirming no content is hidden behind the keyboard.

**Acceptance Scenarios**:

1. **Given** any modal on a mobile screen, **When** its content exceeds the viewport height, **Then** the modal is internally scrollable up to 85% of the viewport height.
2. **Given** a modal open on mobile, **When** the user taps outside the modal content area, **Then** the modal dismisses.
3. **Given** the settings page on mobile, **When** rendered, **Then** the page uses comfortable padding that does not waste excessive screen real estate (not more than ~10% of viewport width on each side).
4. **Given** a form with validation errors on mobile, **When** errors appear inline, **Then** the error messages do not push other content off-screen or cause horizontal overflow.
5. **Given** any form input in a modal on mobile, **When** rendered, **Then** the input spans the full width of the modal content area.

---

### User Story 6 — Visual Consistency & Accessibility Polish (Priority: P3)

A user with accessibility needs (e.g., reduced motion preference, screen reader, keyboard navigation) or who switches between light and dark mode on mobile expects a consistent, accessible experience. All animations must respect the user's motion preferences, focus indicators must be visible in both themes, and layout stacking must be predictable without visual overlaps.

**Why this priority**: Accessibility and visual polish are important for inclusivity but are lower risk since the existing foundation already supports reduced motion and both themes. These are verify-and-fix items rather than new features.

**Independent Test**: Can be tested by enabling reduced motion in device settings and verifying animations are disabled, toggling dark mode on mobile and checking all text is readable, and tabbing through interactive elements to verify focus indicators.

**Acceptance Scenarios**:

1. **Given** a user with `prefers-reduced-motion: reduce` enabled, **When** they navigate the application, **Then** all decorative animations are disabled and no visual breakage occurs.
2. **Given** a user on mobile in dark mode, **When** they view any page, **Then** all text has sufficient contrast and is readable against the dark background.
3. **Given** a keyboard-only user navigating modals, **When** a modal opens, **Then** focus is trapped within the modal and a visible focus ring appears on the active element in both light and dark themes.
4. **Given** the application at any viewport, **When** overlapping UI elements are present (e.g., notification dropdown over chat), **Then** the stacking order is predictable and consistent with the centralized z-index hierarchy.

---

### User Story 7 — Comprehensive Responsive Test Coverage (Priority: P3)

A developer making future frontend changes needs confidence that responsive behavior is not regressed. End-to-end tests must cover the key mobile interactions across all major surfaces (board, chat, pipeline, agents, chores, settings) at multiple viewport sizes, including new device dimensions.

**Why this priority**: Test coverage prevents regressions and is foundational for long-term quality, but it is lower priority than the user-facing fixes themselves.

**Independent Test**: Can be tested by running the E2E test suite and verifying all responsive test specs pass at all viewport sizes in the viewport matrix.

**Acceptance Scenarios**:

1. **Given** the viewport matrix includes at least five device dimensions (375px, 414px, 768px, 820px, 1280px wide), **When** the full E2E suite runs, **Then** all responsive test specs pass at every viewport.
2. **Given** a developer modifies a board component, **When** the responsive board E2E tests run, **Then** they assert scroll affordance visibility, snap behavior, and column height responsiveness.
3. **Given** new E2E test files for pipeline, agents, chores, and chat surfaces, **When** they run on the CI pipeline, **Then** they validate mobile-specific behaviors at the defined viewport matrix.

---

### Edge Cases

- What happens when the user rotates their phone from portrait to landscape while a modal is open? The modal must resize and remain scrollable without content loss.
- How does the chat behave when the virtual keyboard is dismissed mid-typing? The chat container must smoothly restore to full height without visual jank.
- What happens when a board has only one column on mobile? The scroll affordance gradient should not appear when there is no overflow.
- How does the notification dropdown behave at exactly the 375px boundary with a very long notification? Text must truncate and the dropdown must not exceed the viewport width.
- What happens when a user switches between dark and light themes while a modal is open on mobile? The modal must re-render in the new theme without layout shift.
- How does the pipeline flow graph behave when there is only one stage? Touch gestures should still work without errors.
- What happens when a breadcrumb path has a single very long segment (e.g., a 60-character project name)? The segment must truncate with ellipsis.

## Requirements *(mandatory)*

### Functional Requirements

**Phase 1 — Layout & Navigation Shell**

- **FR-001**: The sidebar on mobile MUST render as a fixed overlay with backdrop dismissal, focus trapping, and accessible `aria-modal` attributes.
- **FR-002**: All top bar interactive elements MUST have touch targets of at least 44×44 CSS pixels on viewports below 768px.
- **FR-003**: Breadcrumb navigation MUST truncate individual segments with ellipsis on narrow screens and MUST NOT cause horizontal page overflow at 375px.
- **FR-004**: The notification dropdown MUST constrain its width to the available viewport on screens narrower than its default panel width.
- **FR-005**: The command palette MUST occupy full width on mobile viewports and results MUST be scrollable.
- **FR-006**: The rate-limit indicator MUST NOT push primary page content below the visible fold on any viewport.

**Phase 2A — Board**

- **FR-007**: Board column heights MUST be responsive, using a shorter height on mobile viewports and progressively taller heights at tablet and desktop breakpoints.
- **FR-008**: The board grid MUST use a narrower column minimum width on mobile to prevent forced horizontal overflow when multiple columns exist.
- **FR-009**: A visual scroll affordance (e.g., gradient fade) MUST appear on the trailing edge of the board container when horizontally scrollable content exists on mobile.
- **FR-010**: The board container MUST support scroll-snap behavior on mobile so that horizontal swipes align to column boundaries.
- **FR-011**: Issue card content (text, labels, assignees) MUST truncate gracefully at 375px without layout breakage.

**Phase 2B — Chat**

- **FR-012**: The chat interface on mobile MUST remain usable when the virtual keyboard is visible — the message input MUST stay above the keyboard at all times.
- **FR-013**: Chat size parameters MUST NOT interfere with the mobile fullscreen layout.
- **FR-014**: Message previews (task previews, plan previews) MUST fit within the mobile viewport width without horizontal scroll.
- **FR-015**: The chat history popover MUST span the full available width on mobile rather than using a fixed-width position.
- **FR-016**: The chat text input MUST use an appropriate input mode so that the mobile keyboard presents a standard text layout.
- **FR-017**: All chat toolbar buttons MUST have touch targets of at least 44×44 CSS pixels on viewports below 768px.

**Phase 2C — Pipeline**

- **FR-018**: Pipeline stage containers MUST use a reduced minimum width on mobile to fit within a 375px viewport.
- **FR-019**: Pipeline header text MUST scale to a smaller size on mobile and a standard size at wider breakpoints.
- **FR-020**: The pipeline flow graph MUST be scrollable and zoomable via touch gestures on mobile.

**Phase 2D — Other Pages**

- **FR-021**: Agent cards MUST reflow to a single-column layout on mobile.
- **FR-022**: Chore grid spacing MUST scale appropriately between mobile and desktop viewports.
- **FR-023**: Template tiles MUST stack vertically on mobile.
- **FR-024**: The activity timeline MUST remain readable on narrow screens without clipping.
- **FR-025**: Help page FAQ accordions MUST expand without causing horizontal overflow.

**Phase 3 — Modals & Forms**

- **FR-026**: All modals MUST be constrained to a maximum of 85% of the viewport height with internal scrolling for overflow content.
- **FR-027**: All modals MUST dismiss when the user taps outside the modal content area.
- **FR-028**: All form inputs inside modals MUST span full width on mobile.
- **FR-029**: Modal form content MUST NOT be hidden behind the virtual keyboard.
- **FR-030**: The settings page MUST use responsive padding — compact on mobile and spacious on desktop.
- **FR-031**: Inline validation error messages MUST NOT push page content off-screen or cause horizontal overflow.

**Phase 4 — Polish & Accessibility**

- **FR-032**: All z-index values MUST be defined as named tokens in a centralized location; scattered hard-coded z-index values MUST be replaced with references to these tokens.
- **FR-033**: All decorative animations MUST be disabled when the user has `prefers-reduced-motion: reduce` enabled, with no visual breakage.
- **FR-034**: Focus-visible indicators MUST be present and visible on all interactive elements in both light and dark themes.
- **FR-035**: All interactive elements MUST meet a minimum touch target of 44×44 CSS pixels on mobile viewports.
- **FR-036**: No text content MUST be clipped or overflow at a 375px viewport width.
- **FR-037**: Both light and dark themes MUST render correctly on all tested mobile viewports with adequate text contrast.
- **FR-038**: Scrollable containers (e.g., infinite scroll) MUST scroll without perceptible jank on mobile devices.

**Phase 5 — Test Coverage**

- **FR-039**: Existing E2E responsive tests MUST be expanded to include assertions for sidebar collapse, chat visibility, board scroll affordance, modal scrollability, and touch target sizes.
- **FR-040**: New E2E test files MUST be created for pipeline, agents, chores, and chat responsive scenarios.
- **FR-041**: The viewport test matrix MUST include at least five device dimensions covering mobile, large mobile, tablet, large tablet, and desktop.
- **FR-042**: Visual regression snapshots MUST be captured for key mobile layouts to detect future regressions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No horizontal scrollbar appears at 375px, 414px, 768px, 820px, or 1280px viewport widths on any page (Home, Projects, Pipeline, Settings, Activity, Help).
- **SC-002**: Users can type and send a chat message on a 375px mobile device with the virtual keyboard open — the input field remains visible throughout the interaction.
- **SC-003**: All interactive elements (buttons, links, drag handles, toolbar actions) measure at least 44×44 CSS pixels on mobile viewports.
- **SC-004**: Users can complete settings form changes on a 375px device without any form field being hidden behind the keyboard or cut off by the viewport.
- **SC-005**: All responsive E2E test specs (existing expanded + 4 new files) pass at all five viewport dimensions.
- **SC-006**: Lighthouse mobile audits on the four key pages (Home, Projects, Pipeline, Settings) achieve Performance ≥ 90 and Accessibility ≥ 95.
- **SC-007**: Enabling `prefers-reduced-motion: reduce` disables all decorative animations with no visual breakage across all pages.
- **SC-008**: Both light and dark themes render correctly on 375px, 768px, and 1280px viewports — all text is readable and no elements are visually misaligned.
- **SC-009**: Kanban board horizontal swipe on mobile snaps to column boundaries, and a visual affordance is present when off-screen content exists.
- **SC-010**: Modal interactions (open, scroll, dismiss, form submission) work correctly on a 375px mobile viewport across all 13 modals.

## Assumptions

- **Mobile-first approach**: Default styles target mobile (below 640px); the 768px breakpoint is the primary override for tablet and desktop layouts.
- **No new dependencies**: All fixes use existing responsive utilities and patterns already established in the codebase. No new third-party tools or libraries will be introduced.
- **Frontend only**: Backend API, data models, and server infrastructure are out of scope.
- **Builds on prior audit**: The February 2026 UX audit found 0 critical and 1 minor issue. This review extends that work to address newly identified gaps.
- **PWA deferred**: Progressive Web App features (manifest, service worker) are out of scope and deferred for a separate feature.
- **Lighthouse CI deferred**: A Lighthouse performance gate in CI is out of scope; manual Lighthouse audits will be used for verification.
- **Touch drag-and-drop**: The existing drag-and-drop capability supports touch natively. Explicit touch configuration will only be added if real-device testing reveals issues.
- **Standard error handling**: User-friendly error messages and appropriate fallbacks follow existing patterns in the codebase.
- **Viewport targets**: The primary mobile target is 375×667 (iPhone SE/8); secondary targets are 414×896 (iPhone XR), 768×1024 (iPad), 820×1180 (iPad Air), and 1280×800 (desktop).
- **Scope of modal audit**: All 13 existing modals are in scope; the list includes agent creation, issue detail, chore creation, app creation, and tool selection modals, among others identified during implementation.
