# Responsive Behavior Contracts

**Feature**: 532-uiux-responsive-mobile-review | **Date**: 2026-04-02

> This feature is frontend-only with no REST/GraphQL API changes. This document defines **responsive behavior contracts** — the expected behavior of each component at each viewport breakpoint. These contracts serve as acceptance criteria for implementation and E2E test assertions.

## Viewport Definitions

| Name | Width × Height | Tailwind Context | Device Reference |
|------|---------------|------------------|-----------------|
| `mobile` | 375 × 667 | Below `sm:` (640px) | iPhone SE / iPhone 8 |
| `mobile-lg` | 414 × 896 | Below `sm:` (640px) | iPhone XR / iPhone 11 |
| `tablet` | 768 × 1024 | At `md:` (768px) | iPad (portrait) |
| `tablet-lg` | 820 × 1180 | Above `md:` (768px) | iPad Air (portrait) |
| `desktop` | 1280 × 800 | Above `lg:` (1024px) | Standard HD |

---

## Phase 1: Layout & Navigation Shell

### Contract: Sidebar

| Viewport | Expected Behavior |
|----------|-------------------|
| mobile (375px) | Sidebar rendered as fixed overlay with z-50; backdrop at z-40 with bg-black/50; closes on backdrop click; aria-modal="true" when open; transition animation smooth; focus trapped within when open |
| tablet (768px+) | Sidebar rendered inline; collapsible with toggle; collapsed width 64px, expanded width 240px; transition-all duration-300 |
| All | No horizontal overflow caused by sidebar at any viewport |

### Contract: TopBar

| Viewport | Expected Behavior |
|----------|-------------------|
| mobile (375px) | Help button ≥44×44px touch target; search text hidden; keyboard shortcut badge hidden; user login text hidden |
| tablet (768px+) | Help button can be standard size; search text visible (md:inline); user login text visible (md:block) |
| All | Fixed height h-16 (64px); backdrop blur active; no content overflow |

### Contract: Breadcrumb

| Viewport | Expected Behavior |
|----------|-------------------|
| mobile (375px) | Container max-width prevents overflow; individual segments truncated with ellipsis when path exceeds available width; no horizontal scrollbar |
| tablet (768px+) | Full breadcrumb path visible; truncation only on very deep paths |
| All | Accessible navigation links; proper ARIA breadcrumb role |

### Contract: NotificationBell

| Viewport | Expected Behavior |
|----------|-------------------|
| mobile (375px) | Dropdown panel width = min(320px, viewport-width - 24px); no viewport overflow; positioned within visible area |
| tablet (768px+) | Standard 320px panel width; positioned relative to bell icon |
| All | z-index uses centralized token; max-h-[320px] with scroll; portal-based rendering |

### Contract: CommandPalette

| Viewport | Expected Behavior |
|----------|-------------------|
| mobile (375px) | Full-width dialog (w-full); padding from edges; results scrollable; keyboard shortcut badges hidden |
| tablet (768px+) | max-w-lg centered; keyboard shortcut badges visible (sm:inline-flex) |
| All | z-index uses centralized tokens; proper focus management; Escape dismisses |

### Contract: RateLimitBar

| Viewport | Expected Behavior |
|----------|-------------------|
| mobile (375px) | Hidden (hidden class); does not push content below fold |
| tablet (768px+) | Visible (md:flex); health bar with color coding |
| All | No layout shift when appearing/disappearing |

---

## Phase 2A: Board

### Contract: BoardColumn

| Viewport | Expected Behavior |
|----------|-------------------|
| mobile (375px) | Height h-[44rem] (704px); max-h-[44rem]; min-h-[28rem]; columns shrink for mobile |
| tablet (768px+) | Height h-[72rem] (1152px); max-h-[72rem]; min-h-[44rem] |
| desktop-xl (1280px+) | Height h-[95rem] (1520px); max-h-[95rem] |
| All | Rounded corners; border; overflow-x-hidden; drag-and-drop feedback ring |

### Contract: ProjectBoard

| Viewport | Expected Behavior |
|----------|-------------------|
| mobile (375px) | Grid columns minmax(min(14rem, 85vw), 1fr); scroll-snap-type: x mandatory; gradient fade affordance on right edge when content overflows; horizontal scroll enabled |
| tablet (768px+) | Grid columns minmax(min(16rem, 85vw), 1fr); scroll affordance if needed |
| All | overflow-x-auto; no vertical clipping; ARIA region label |

### Contract: IssueCard

| Viewport | Expected Behavior |
|----------|-------------------|
| mobile (375px) | min-w-[15rem]; labels truncated; assignees truncated; drag handle touch area ≥44px; text readable |
| All | Hover effects; focus ring; keyboard navigable (Enter/Space); truncation on overflow |

---

## Phase 2B: Chat

### Contract: ChatPopup (🔴 HIGH PRIORITY)

| Viewport | Expected Behavior |
|----------|-------------------|
| mobile (375px) | Fixed fullscreen (inset-0); when virtual keyboard opens, chat input remains visible above keyboard via visualViewport resize handler; env(safe-area-inset-bottom) for iOS notch; resize handle hidden |
| tablet (768px+) | Floating window at bottom-right; resize handle visible; size constraints MIN_WIDTH=300, MIN_HEIGHT=350, MAX_WIDTH=800, MAX_HEIGHT=900 |
| All | z-[1000]; smooth open/close animation; proper close handling |

### Contract: TaskPreview / PlanPreview

| Viewport | Expected Behavior |
|----------|-------------------|
| mobile (375px) | max-w-[90vw]; content fits within viewport minus margins |
| tablet (768px+) | max-w-[500px] (TaskPreview) / max-w-[600px] (PlanPreview) |
| All | ml-11 for chat alignment; overflow-hidden; rounded border |

### Contract: ChatInterface History Popover

| Viewport | Expected Behavior |
|----------|-------------------|
| mobile (375px) | Positioned left-0 right-0 (full width); max-h-60; scrollable |
| tablet (768px+) | Positioned right-0; w-64 (256px) |
| All | z-20; border; backdrop blur; scroll on overflow |

### Contract: MentionInput

| Viewport | Expected Behavior |
|----------|-------------------|
| All | inputMode="text" attribute present; mobile keyboard shows standard text layout; w-full responsive; placeholder switches to mobile variant below sm: breakpoint |

### Contract: ChatToolbar

| Viewport | Expected Behavior |
|----------|-------------------|
| mobile (375px) | All buttons ≥44×44px (h-11 w-11) |
| tablet (768px+) | Buttons can be 32px (h-8 w-8) |
| All | Flex layout; proper spacing; focus-visible outlines |

---

## Phase 2C: Pipeline

### Contract: PipelineBoard

| Viewport | Expected Behavior |
|----------|-------------------|
| mobile (375px) | Stage min-width 12rem (192px); pipeline name text-base |
| tablet (640px+) | Stage min-width per calculation (14rem/20rem); pipeline name sm:text-lg |
| All | Responsive padding p-4 sm:p-5; overflow handling |

### Contract: PipelineFlowGraph

| Viewport | Expected Behavior |
|----------|-------------------|
| mobile (375px) | Touch scrollable and zoomable; responsive width via ResizeObserver; icon size adapts to available space |
| All | Responsive prop honored; smooth resize transitions |

---

## Phase 3: Modals & Forms

### Contract: All Modals (13 components)

| Viewport | Expected Behavior |
|----------|-------------------|
| mobile (375px) | max-h-[85vh]; internal scroll when content exceeds height; all form inputs w-full; content not hidden behind keyboard; tap-outside dismisses |
| All | Proper focus trapping; Escape key dismisses; ARIA dialog attributes |

### Contract: SettingsPage

| Viewport | Expected Behavior |
|----------|-------------------|
| mobile (375px) | Container padding p-4 (16px); all inputs full-width |
| tablet (768px+) | Container padding p-8 (32px); max-w-4xl centered |
| All | Vertical stacking; scrollable content |

---

## Phase 4: Polish & Accessibility

### Contract: Z-Index Centralization

| Requirement | Expected Behavior |
|-------------|-------------------|
| Token definition | All z-index values defined as CSS custom properties in `@theme` block |
| Component usage | No raw `z-[N]` in component files; replaced with `z-[var(--z-*)]` or Tailwind theme tokens |
| Documentation | Z-index map documented in data-model.md |

### Contract: Reduced Motion

| Requirement | Expected Behavior |
|-------------|-------------------|
| `prefers-reduced-motion: reduce` | All celestial animations disabled; no visual breakage; transitions reduced to instant |

### Contract: Touch Targets

| Requirement | Expected Behavior |
|-------------|-------------------|
| All interactive elements on mobile | Minimum 44×44 CSS pixel touch area (WCAG 2.2 SC 2.5.8) |

---

## Phase 5: E2E Test Coverage

### Contract: Test Files

| File | Assertions |
|------|-----------|
| `responsive-board.spec.ts` | Existing + scroll affordance visible, scroll-snap active, column heights responsive |
| `responsive-home.spec.ts` | Existing + sidebar collapse, touch target sizes |
| `responsive-settings.spec.ts` | Existing + modal scrollability, responsive padding |
| `responsive-pipeline.spec.ts` (NEW) | Stage widths at each viewport, pipeline name font scaling, flow graph touch |
| `responsive-agents.spec.ts` (NEW) | Agent card reflow, single-column on mobile |
| `responsive-chores.spec.ts` (NEW) | Chores grid gap scaling, card layout |
| `responsive-chat.spec.ts` (NEW) | Chat popup mobile fullscreen, keyboard handling, preview widths, toolbar touch targets |

### Contract: Viewport Matrix

| Viewport | Width | Height | Required In |
|----------|-------|--------|-------------|
| mobile | 375 | 667 | All test files |
| mobile-lg | 414 | 896 | All test files |
| tablet | 768 | 1024 | All test files |
| tablet-lg | 820 | 1180 | All test files |
| desktop | 1280 | 800 | All test files |
