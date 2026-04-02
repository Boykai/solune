# Research: UI/UX Responsive & Mobile Review

**Feature**: 532-uiux-responsive-mobile-review | **Date**: 2026-04-02

## R-001: Virtual Keyboard Overlap Handling (HIGH Priority)

**Decision**: Use `visualViewport` API with `env(safe-area-inset-bottom)` CSS fallback.

**Rationale**: The `ChatPopup.tsx` uses `fixed inset-0` on mobile, which does not account for the virtual (soft) keyboard. When users tap the chat input, the keyboard slides up and obscures the input field. The `visualViewport` API (supported in all modern browsers including Safari 15+) provides `resize` and `scroll` events that report the actual visible area excluding the keyboard. Combined with `env(safe-area-inset-bottom)` for iOS safe area handling, this is the most reliable cross-browser approach.

**Alternatives Considered**:
- `window.innerHeight` polling: Unreliable on iOS Safari where `innerHeight` doesn't change when keyboard appears
- CSS `100dvh` (dynamic viewport height): Partially works but doesn't respond to keyboard events in real-time
- `position: sticky` instead of `fixed`: Breaks the fullscreen overlay pattern already in use
- Third-party library (e.g., `react-keyboard-aware`): Violates "no new libraries" constraint

**Implementation Pattern**:
```typescript
// In ChatPopup.tsx — mobile keyboard handling
useEffect(() => {
  if (!isMobile) return;
  const vv = window.visualViewport;
  if (!vv) return;

  const handleResize = () => {
    // Offset chat container bottom by keyboard height
    const keyboardHeight = window.innerHeight - vv.height;
    containerRef.current?.style.setProperty('padding-bottom', `${keyboardHeight}px`);
  };

  vv.addEventListener('resize', handleResize);
  return () => vv.removeEventListener('resize', handleResize);
}, [isMobile]);
```

---

## R-002: Z-Index Centralization Strategy

**Decision**: Define named z-index tokens in the Tailwind `@theme` block in `src/index.css`, then replace scattered `z-[N]` values with semantic token references.

**Rationale**: The codebase currently uses 12+ different z-index values spread across components: `z-[10000]`, `z-[9999]`, `z-[9998]`, `z-[1001]`, `z-[1000]`, `z-[140]`, `z-[120]`, `z-[110]`, `z-[101]`, `z-[100]`, `z-[70]`, `z-[60]`, `z-[50]`, `z-[40]`. Centralizing these into named tokens makes the stacking order explicit, prevents conflicts, and makes future changes safer.

**Alternatives Considered**:
- CSS custom properties only (no Tailwind tokens): Would require manual `style=` attributes, inconsistent with Tailwind-first approach
- Separate `z-index.ts` constants file: Would require importing and using `style=` instead of Tailwind classes
- Leave as-is: The scattered values already work, but maintaining stacking order is error-prone

**Proposed Token Map** (in `@theme` block):

| Token | Value | Components |
|-------|-------|-----------|
| `--z-base` | 0 | Default stacking |
| `--z-sidebar-backdrop` | 40 | Sidebar mobile backdrop |
| `--z-sidebar` | 50 | Sidebar panel |
| `--z-modal-backdrop` | 60 | Confirmation dialogs |
| `--z-modal` | 70 | Standard modals (chores, pipelines) |
| `--z-tour-overlay` | 100 | SpotlightOverlay |
| `--z-tour-tooltip` | 101 | SpotlightTooltip |
| `--z-agent-modal` | 110–140 | Agent modals (layered) |
| `--z-chat` | 1000 | ChatPopup |
| `--z-chat-toggle` | 1001 | Chat toggle button |
| `--z-command-backdrop` | 9998 | CommandPalette backdrop |
| `--z-command` | 9999 | CommandPalette dialog |
| `--z-notification` | 10000 | NotificationBell dropdown |

---

## R-003: Touch Target Sizing Standards

**Decision**: Apply 44×44px minimum touch targets on mobile using conditional Tailwind classes (`h-8 w-8 md:h-8 md:w-8` → `h-11 w-11 md:h-8 md:w-8`).

**Rationale**: WCAG 2.2 Success Criterion 2.5.8 requires a minimum 44×44 CSS pixel target size for pointer inputs. The current codebase has some buttons at 32px (`h-8 w-8`) which meets desktop standards but falls below mobile touch requirements. Using Tailwind's mobile-first approach, we set 44px as the default and optionally reduce to 32px on desktop where mouse precision allows it.

**Alternatives Considered**:
- Use `min-h-[44px] min-w-[44px]` universally: Would affect desktop layout where compact buttons are preferred
- Padding-based approach (`p-2` to increase hit area): Doesn't guarantee minimum size if content is smaller
- CSS `touch-action` manipulation: Doesn't address the target size issue itself

**Components Requiring Touch Target Updates**:
- TopBar.tsx: Help button (currently 36px → needs 44px on mobile)
- ChatToolbar.tsx: All toolbar buttons (currently `h-8 w-8` = 32px → needs `h-11 w-11` on mobile)
- IssueCard.tsx: Drag handles (verify ≥ 44px touch area)
- Breadcrumb.tsx: Navigation links (verify adequate spacing)

---

## R-004: Scroll-Snap and Scroll Affordance Patterns

**Decision**: Use CSS `scroll-snap-type: x mandatory` with `scroll-snap-align: start` on board columns, plus a gradient fade overlay to signal scrollable content.

**Rationale**: On mobile, horizontal board scrolling is the primary navigation pattern. Without scroll-snap, users may land between columns. Without a visual affordance (gradient fade), users may not realize content extends beyond the viewport. Both patterns are CSS-only and require no JavaScript.

**Alternatives Considered**:
- JavaScript-based scroll positioning: Over-engineered for this use case
- Pagination (arrows) instead of scrolling: Breaks the Kanban visual metaphor
- `scroll-snap-type: x proximity` (softer snapping): Less predictable UX on mobile

**Implementation Pattern**:
```css
/* ProjectBoard container */
.board-scroll-container {
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
}

/* Each column */
.board-column {
  scroll-snap-align: start;
}

/* Gradient affordance overlay (pseudo-element on container) */
.board-scroll-affordance::after {
  content: '';
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 2rem;
  background: linear-gradient(to right, transparent, var(--background));
  pointer-events: none;
}
```

---

## R-005: Responsive Padding & Spacing Strategy

**Decision**: Use Tailwind mobile-first responsive padding: `p-4 sm:p-5 md:p-8` for page containers, `gap-3 md:gap-5` for grid layouts.

**Rationale**: The current SettingsPage uses `p-8` (32px) on all viewports, which consumes 64px of horizontal space on a 375px screen (17% of viewport). Mobile-first responsive padding ensures comfortable spacing without wasting scarce mobile real estate.

**Alternatives Considered**:
- `clamp()` CSS function for fluid padding: More complex, harder to maintain, and inconsistent with Tailwind utility approach
- Single small padding everywhere: Looks cramped on desktop
- Container queries: Tailwind v4 supports them, but breakpoint prefixes are simpler and already used throughout

---

## R-006: Mobile Chat Size Constants

**Decision**: Make ChatPopup size constants mobile-aware by conditionally applying fullscreen on mobile (already implemented) and adjusting MIN_WIDTH/MIN_HEIGHT for edge cases.

**Rationale**: Current constants `MIN_HEIGHT=350`, `MAX_WIDTH=800` are desktop-oriented. On mobile, the chat already goes fullscreen via `fixed inset-0`, so these constants don't apply. However, the resize logic should be guarded so it doesn't interfere with the mobile layout. The existing `isMobile` check in the style attribute (`isMobile ? undefined : { width, height }`) already handles this correctly. The remaining fix is ensuring the initial animation and keyboard handling work correctly.

**Alternatives Considered**:
- Dynamic constants based on viewport: Over-engineering since mobile already uses fullscreen
- Separate mobile/desktop components: Violates DRY; the conditional rendering pattern is cleaner

---

## R-007: Message Preview Width Strategy

**Decision**: Replace fixed `max-w-[500px]`/`max-w-[600px]` with responsive `max-w-[90vw] md:max-w-[500px]`/`max-w-[90vw] md:max-w-[600px]`.

**Rationale**: On a 375px mobile screen, a `max-w-[500px]` container with `ml-11` (44px margin) effectively creates a 500px-wide element that overflows or forces horizontal scroll. Using `max-w-[90vw]` on mobile ensures the preview fits within the viewport while preserving the original desktop widths at `md:` breakpoint.

**Alternatives Considered**:
- `max-w-full`: Would make previews too wide on desktop
- `calc(100vw - 2rem)`: Works but `90vw` is simpler and provides consistent margins
- Remove `ml-11` on mobile: Would break the chat message alignment

---

## R-008: Existing Foundation Assessment

**Decision**: The existing responsive foundation is strong and requires augmentation, not replacement.

**Rationale**: The Feb 2026 UX audit (findings-log.md) found 0 critical issues and 1 minor issue. The Mar 2026 celestial theme audit added 14 animation classes with `prefers-reduced-motion` support. The codebase already uses:
- `useMediaQuery` hook in 3+ components
- Tailwind `sm:`, `md:`, `lg:`, `xl:` breakpoints throughout
- Mobile-first sidebar overlay with backdrop
- Fullscreen chat popup on mobile
- Portal-based dropdowns with dynamic viewport positioning
- 3 E2E responsive test files with viewport matrix
- `@axe-core/playwright` for accessibility testing

This plan extends the existing patterns rather than introducing new architectural approaches.

---

## R-009: @dnd-kit Touch Support

**Decision**: Verify existing @dnd-kit touch support; add explicit touch sensor configuration only if testing reveals issues.

**Rationale**: @dnd-kit v6+ includes built-in touch support via `PointerSensor` and `TouchSensor`. The existing board uses `useSortable` and `useDraggable` hooks which should work with touch out of the box. Real-device testing at 375px is needed to confirm. If touch drag fails, adding explicit `TouchSensor` with `activationConstraint: { delay: 250, tolerance: 5 }` prevents accidental drags while scrolling.

**Alternatives Considered**:
- Replace @dnd-kit with native HTML5 drag: HTML5 drag API has poor mobile support
- Add `react-beautiful-dnd`: Deprecated and no longer maintained
- Custom touch handling: Over-engineering when @dnd-kit already supports touch

---

## R-010: E2E Test Expansion Strategy

**Decision**: Add 4 new E2E spec files and 2 new viewport definitions, following existing patterns.

**Rationale**: The existing 3 test files (`responsive-home.spec.ts`, `responsive-board.spec.ts`, `responsive-settings.spec.ts`) establish a clear pattern: import `VIEWPORTS`, iterate over entries, test at each viewport. New tests follow this exact pattern. Adding iPhone XR (414×896) and iPad Air (820×1180) to `viewports.ts` increases coverage without breaking existing tests.

**New Viewport Coverage**:
| Device | Width | Height | Fills Gap |
|--------|-------|--------|-----------|
| iPhone XR | 414 | 896 | Tests between mobile (375) and tablet (768) |
| iPad Air | 820 | 1180 | Tests just above md: breakpoint (768) |

---

## R-011: Breadcrumb Truncation Strategy

**Decision**: Use Tailwind `truncate` with `max-w-[calc(100vw-8rem)]` on the breadcrumb container, plus individual segment truncation with `max-w-[8rem]` on narrow screens.

**Rationale**: Breadcrumbs can grow indefinitely with deep navigation paths. On 375px screens, even 3 segments may overflow. A container-level max-width prevents overall overflow, while per-segment truncation ensures each breadcrumb item degrades gracefully with ellipsis.

**Alternatives Considered**:
- Collapsing middle segments into `...` menu: More complex, requires additional UI component
- Hiding breadcrumbs on mobile: Loses navigation context
- Horizontal scrolling: Not standard breadcrumb UX

---

## R-012: PWA Support Decision

**Decision**: Defer PWA support (web app manifest + service worker). Out of scope for this review.

**Rationale**: The specification explicitly lists this as a "Further Consideration" and recommends deferring unless mobile is a primary target. This responsive review focuses on fixing existing gaps, not adding new capabilities. PWA can be a separate feature spec.

---

## R-013: Lighthouse CI Gate Decision

**Decision**: Defer Lighthouse CI gate. Document performance thresholds in verification criteria for manual testing.

**Rationale**: Adding a Lighthouse CI gate requires infrastructure changes (CI workflow modifications, performance budget configuration) that are out of scope for a frontend-only responsive review. The verification section specifies manual Lighthouse audits with thresholds (Performance ≥ 90, Accessibility ≥ 95) as acceptance criteria.
