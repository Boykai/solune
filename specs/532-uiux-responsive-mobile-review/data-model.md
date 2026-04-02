# Data Model: UI/UX Responsive & Mobile Review

**Feature**: 532-uiux-responsive-mobile-review | **Date**: 2026-04-02

> This feature is frontend-only with no database entities. This document defines the **component audit matrix** (entities under review), the **responsive breakpoint model** (shared state), and the **z-index token model** (centralized stacking).

## Component Audit Matrix

Each row represents a component requiring responsive review. Fields capture current state and target state.

### Entity: ComponentAudit

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier (e.g., `sidebar-mobile-overlay`) |
| component | string | React component file name (e.g., `Sidebar.tsx`) |
| path | string | Relative path from `solune/frontend/src/` |
| phase | enum | `1-layout` \| `2a-board` \| `2b-chat` \| `2c-pipeline` \| `2d-other` \| `3-modals` \| `4-polish` \| `5-tests` |
| severity | enum | `high` \| `medium` \| `low` \| `cosmetic` \| `verify-only` |
| current_behavior | string | Description of current responsive behavior |
| target_behavior | string | Description of desired responsive behavior |
| breakpoints_affected | string[] | Tailwind breakpoints involved (`sm`, `md`, `lg`, `xl`) |
| status | enum | `pending` \| `in-progress` \| `done` \| `verified` |
| depends_on | string[] | IDs of components that must be fixed first |

### Component Audit Instances

#### Phase 1: Layout & Navigation Shell

| ID | Component | Severity | Current | Target | Breakpoints | Depends On |
|----|-----------|----------|---------|--------|-------------|------------|
| `sidebar-overlay` | Sidebar.tsx | verify-only | Mobile overlay with z-40 backdrop, z-50 panel, backdrop click dismiss | Verify animation, focus trapping, aria-modal | — | — |
| `topbar-touch` | TopBar.tsx | medium | Help button ~36px | Help button ≥44px on mobile via `h-11 w-11 md:h-9 md:w-9` | md | — |
| `breadcrumb-truncate` | Breadcrumb.tsx | low | No overflow handling | Container max-width + per-segment truncation on narrow screens | sm, md | — |
| `notification-overflow` | NotificationBell.tsx | medium | Fixed panelWidth=320px, z-[10000] | Viewport-aware width `Math.min(320, innerWidth-24)`, z-index token | — | — |
| `command-palette` | CommandPalette.tsx | verify-only | w-full max-w-lg, z-[9999] | Verify full-width usability on mobile, z-index token | — | — |
| `ratelimit-bar` | RateLimitBar.tsx | verify-only | hidden md:flex | Verify no content push below fold | md | — |

#### Phase 2A: Board

| ID | Component | Severity | Current | Target | Breakpoints | Depends On |
|----|-----------|----------|---------|--------|-------------|------------|
| `board-column-height` | BoardColumn.tsx | medium | h-[72rem] xl:h-[95rem] | Add md: breakpoint: `h-[44rem] md:h-[72rem] xl:h-[95rem]` | md, xl | — |
| `board-column-skeleton` | BoardColumnSkeleton.tsx | low | Match BoardColumn | Mirror BoardColumn responsive heights | md, xl | board-column-height |
| `board-grid-width` | ProjectBoard.tsx | medium | minmax(min(16rem, 85vw), 1fr) | Reduce to `minmax(min(14rem, 85vw), 1fr)` on mobile when >2 columns | — | — |
| `board-scroll-affordance` | ProjectBoard.tsx | low | No visual scroll indicator | Gradient fade on right edge when overflow-x present | — | — |
| `board-scroll-snap` | ProjectBoard.tsx | low | No scroll snapping | scroll-snap-type: x mandatory on mobile | — | — |
| `issuecard-truncation` | IssueCard.tsx | verify-only | truncate max-w-[120px] labels | Verify text truncation, labels, drag handles at 375px | — | — |

#### Phase 2B: Chat

| ID | Component | Severity | Current | Target | Breakpoints | Depends On |
|----|-----------|----------|---------|--------|-------------|------------|
| `chat-keyboard` | ChatPopup.tsx | **high** | fixed inset-0 ignores soft keyboard | visualViewport resize handler + env(safe-area-inset-bottom) | — | — |
| `chat-size-constants` | ChatPopup.tsx | medium | MIN_HEIGHT=350, MAX_WIDTH=800 | Guard resize logic; mobile already fullscreen via isMobile check | — | — |
| `task-preview-width` | TaskPreview.tsx | medium | max-w-[500px] | max-w-[90vw] md:max-w-[500px] | md | — |
| `plan-preview-width` | PlanPreview.tsx | medium | max-w-[600px] | max-w-[90vw] md:max-w-[600px] | md | — |
| `chat-history-popover` | ChatInterface.tsx | low | absolute right-0 w-64 | Conditionally left-0 right-0 on mobile | — | — |
| `mention-input-mode` | MentionInput.tsx | low | No inputMode attribute | Add inputMode="text" | — | — |
| `chat-toolbar-touch` | ChatToolbar.tsx | medium | h-8 w-8 (32px) buttons | h-11 w-11 md:h-8 md:w-8 for mobile touch targets | md | — |

#### Phase 2C: Pipeline

| ID | Component | Severity | Current | Target | Breakpoints | Depends On |
|----|-----------|----------|---------|--------|-------------|------------|
| `pipeline-stage-width` | PipelineBoard.tsx | low | minmax(14rem/20rem, 1fr) | Reduce to minmax(12rem, 1fr) on mobile | sm | board-grid-width |
| `pipeline-name-font` | PipelineBoard.tsx | cosmetic | Implicit font size | text-base sm:text-lg | sm | — |
| `pipeline-flow-touch` | PipelineFlowGraph.tsx | verify-only | ResizeObserver responsive | Verify touch scroll/zoom at 375px | — | — |

#### Phase 2D: Other Pages

| ID | Component | Severity | Current | Target | Breakpoints | Depends On |
|----|-----------|----------|---------|--------|-------------|------------|
| `agents-panel-reflow` | AgentsPanel.tsx | verify-only | Card grid layout | Verify single-column reflow on mobile | — | — |
| `chores-grid-gap` | ChoresGrid.tsx | verify-only | gap styling | Verify gap-3 md:gap-5 scaling | md | — |
| `template-browser` | TemplateBrowser.tsx | verify-only | Template tiles | Verify tiles stack on mobile | — | — |
| `tool-selector-modal` | ToolSelectorModal.tsx | verify-only | Already responsive | Verify no overflow | — | — |
| `activity-timeline` | ActivityPage.tsx | verify-only | Timeline layout | Verify readability on narrow screens | — | — |
| `help-faq` | HelpPage.tsx | verify-only | FAQ accordion | Verify expansion without overflow | — | — |

#### Phase 3: Modals & Forms

| ID | Component | Severity | Current | Target | Breakpoints | Depends On |
|----|-----------|----------|---------|--------|-------------|------------|
| `modals-audit` | 13 modal components | medium | Varies | max-h-[85vh] scroll, tap-dismiss, full-width inputs, keyboard-safe | — | — |
| `settings-padding` | SettingsPage.tsx | medium | p-8 | p-4 md:p-8 | md | — |
| `validation-messages` | Various form components | low | Varies | Inline errors don't push content off-screen | — | — |

#### Phase 4: Polish & Accessibility

| ID | Component | Severity | Current | Target | Breakpoints | Depends On |
|----|-----------|----------|---------|--------|-------------|------------|
| `z-index-centralize` | index.css + all components | medium | Scattered z-[N] values | Centralized @theme tokens | — | — |
| `reduced-motion` | index.css | verify-only | prefers-reduced-motion block exists | Verify all celestial animations covered | — | — |
| `focus-management` | All interactive components | verify-only | focus-visible:ring-2 pattern | Verify rings + modal focus trapping both themes | — | — |
| `touch-target-sweep` | All interactive elements | medium | Mixed sizes | All ≥44×44px on mobile | — | topbar-touch, chat-toolbar-touch |
| `responsive-typography` | All text | verify-only | Tailwind type scale | No text clipping at 375px | — | — |
| `dark-mode-mobile` | All components | verify-only | Two themes | Both themes correct on all mobile viewports | — | — |
| `scroll-performance` | InfiniteScrollContainer | verify-only | Existing implementation | No jank on mobile | — | — |

## Responsive Breakpoint Model

Shared breakpoint definitions used across all components.

| Token | Pixels | Tailwind Prefix | Usage |
|-------|--------|-----------------|-------|
| mobile | 0–639px | (default / `max-sm:`) | Base mobile styles, touch targets 44px |
| sm | 640px+ | `sm:` | Small tablets, keyboard shortcuts visible |
| md | 768px+ | `md:` | **Primary breakpoint**: tablet layout, desktop-like features |
| lg | 1024px+ | `lg:` | Desktop layout adjustments |
| xl | 1280px+ | `xl:` | Large desktop, expanded board columns |

**Convention**: Use mobile-first approach. Default styles target mobile; `md:` is the primary override point. `useMediaQuery('(max-width: 767px)')` for JS-level mobile detection.

## Z-Index Token Model

Centralized z-index stacking context tokens for `@theme` block in `src/index.css`.

| Token | Value | Layer | Components |
|-------|-------|-------|-----------|
| `--z-base` | 0 | Ground | Default element stacking |
| `--z-sticky` | 10 | Sticky | Sticky headers, floating elements |
| `--z-sidebar-backdrop` | 40 | Overlay | Sidebar mobile backdrop |
| `--z-sidebar` | 50 | Overlay | Sidebar panel on mobile |
| `--z-modal-backdrop` | 60 | Modal | Confirmation dialog backdrops |
| `--z-modal` | 70 | Modal | Standard modals (chores, pipelines, issue detail) |
| `--z-tour-overlay` | 100 | Tour | SpotlightOverlay backdrop |
| `--z-tour-tooltip` | 101 | Tour | SpotlightTooltip content |
| `--z-agent-modal-base` | 110 | Agent | AddAgentModal base layer |
| `--z-agent-modal-top` | 120 | Agent | AddAgentModal top layer |
| `--z-agent-picker` | 140 | Agent | AgentIconPickerModal |
| `--z-chat` | 1000 | Chat | ChatPopup panel |
| `--z-chat-toggle` | 1001 | Chat | Chat toggle button |
| `--z-command-backdrop` | 9998 | Command | CommandPalette backdrop |
| `--z-command` | 9999 | Command | CommandPalette dialog |
| `--z-notification` | 10000 | Notification | NotificationBell dropdown |
| `--z-install-confirm` | 10010 | Install | InstallConfirmDialog (highest) |

**Validation Rules**:
- Each z-index value must be unique
- Values must increase as you go "up" the stacking layers
- Components must reference tokens, not raw numbers
- New components must be assigned an existing or new token

## Dependency Graph

```text
Phase 1 (Layout Shell)
  ├── sidebar-overlay
  ├── topbar-touch
  ├── breadcrumb-truncate
  ├── notification-overflow
  ├── command-palette
  └── ratelimit-bar

Phase 2A (Board)          Phase 2B (Chat)
  ├── board-column-height    ├── chat-keyboard (HIGH)
  ├── board-column-skeleton  ├── chat-size-constants
  │   └── depends: board-    ├── task-preview-width
  │       column-height      ├── plan-preview-width
  ├── board-grid-width       ├── chat-history-popover
  ├── board-scroll-affordance├── mention-input-mode
  ├── board-scroll-snap      └── chat-toolbar-touch
  └── issuecard-truncation

Phase 2C (Pipeline)       Phase 2D (Other Pages)
  ├── pipeline-stage-width   ├── agents-panel-reflow
  │   └── depends: board-    ├── chores-grid-gap
  │       grid-width         ├── template-browser
  ├── pipeline-name-font     ├── tool-selector-modal
  └── pipeline-flow-touch    ├── activity-timeline
                             └── help-faq

Phase 3 (Modals)
  ├── modals-audit
  ├── settings-padding
  └── validation-messages

Phase 4 (Polish)
  ├── z-index-centralize
  ├── reduced-motion
  ├── focus-management
  ├── touch-target-sweep
  │   └── depends: topbar-touch, chat-toolbar-touch
  ├── responsive-typography
  ├── dark-mode-mobile
  └── scroll-performance
```

**Parallel Execution**: Phases 2A and 2B are independent and can run in parallel. Phase 2C depends on 2A patterns (board grid). Phase 2D is independent of 2A–2C.
