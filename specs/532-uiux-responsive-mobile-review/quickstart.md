# Quickstart: UI/UX Responsive & Mobile Review

**Feature**: 532-uiux-responsive-mobile-review | **Date**: 2026-04-02

## Prerequisites

- Node.js ≥ 20 (matches project requirement)
- npm (comes with Node.js)
- Chrome or Chromium (for Playwright E2E tests)

## Setup

```bash
# From repository root
cd solune/frontend
npm install

# Install Playwright browsers (if not already installed)
npx playwright install chromium
```

## Development Workflow

### 1. Start Dev Server

```bash
cd solune/frontend
npm run dev
# Opens at http://localhost:5173
```

### 2. Test Responsive Changes

**Browser DevTools approach** (fastest iteration):
1. Open Chrome DevTools (F12)
2. Toggle Device Toolbar (Ctrl+Shift+M)
3. Select viewport presets:
   - **iPhone SE**: 375×667 (mobile baseline)
   - **iPhone XR**: 414×896 (mobile-lg)
   - **iPad**: 768×1024 (tablet baseline)
   - **iPad Air**: 820×1180 (tablet-lg)
   - **Laptop**: 1280×800 (desktop baseline)
4. Test each page: `/`, `/projects`, `/pipeline`, `/settings`, `/agents`, `/chores`

**Virtual keyboard testing**:
1. In Chrome DevTools, toggle "Show Device Frame"
2. Click the chat input on mobile viewport
3. Verify input remains visible above the virtual keyboard
4. Or test on real iOS/Android device via local network

### 3. Run Existing Tests

```bash
# Unit tests
cd solune/frontend
npm run test

# Type checking
npm run type-check

# Lint
npm run lint

# E2E responsive tests (existing)
npm run test:e2e -- --grep "responsive"

# Single E2E file
npx playwright test e2e/responsive-board.spec.ts
```

### 4. Key Files to Modify

#### Phase 1: Layout Shell (start here)

| File | Change | Priority |
|------|--------|----------|
| `src/layout/TopBar.tsx` | Help button size: add responsive touch target classes | Medium |
| `src/layout/Breadcrumb.tsx` | Add truncation + overflow handling | Low |
| `src/layout/NotificationBell.tsx` | Viewport-aware panel width, z-index token | Medium |
| `src/layout/Sidebar.tsx` | Verify-only: animation, focus trap, aria-modal | Verify |
| `src/components/command-palette/CommandPalette.tsx` | Verify-only: mobile usability | Verify |
| `src/layout/RateLimitBar.tsx` | Verify-only: no content push | Verify |

#### Phase 2B: Chat (🔴 highest priority item)

| File | Change | Priority |
|------|--------|----------|
| `src/components/chat/ChatPopup.tsx:190` | **Virtual keyboard fix**: Add visualViewport handler | **HIGH** |
| `src/components/chat/TaskPreview.tsx:26` | `max-w-[500px]` → `max-w-[90vw] md:max-w-[500px]` | Medium |
| `src/components/chat/PlanPreview.tsx:51` | `max-w-[600px]` → `max-w-[90vw] md:max-w-[600px]` | Medium |
| `src/components/chat/ChatInterface.tsx:704` | History popover mobile positioning | Low |
| `src/components/chat/MentionInput.tsx:273` | Add `inputMode="text"` | Low |
| `src/components/chat/ChatToolbar.tsx` | Button sizes 32→44px on mobile | Medium |

#### Phase 2A: Board

| File | Change | Priority |
|------|--------|----------|
| `src/components/board/BoardColumn.tsx:45` | Add `h-[44rem] md:h-[72rem]` responsive heights | Medium |
| `src/components/board/BoardColumnSkeleton.tsx:11` | Mirror BoardColumn heights | Low |
| `src/components/board/ProjectBoard.tsx:45` | Scroll-snap, scroll affordance, mobile grid width | Medium |

#### Phase 4: Polish

| File | Change | Priority |
|------|--------|----------|
| `src/index.css` | Centralize z-index values into @theme tokens | Medium |

### 5. Responsive Pattern Reference

**Existing pattern — useMediaQuery**:
```tsx
import { useMediaQuery } from '@/hooks/useMediaQuery';

// In component:
const isMobile = useMediaQuery('(max-width: 767px)');
```

**Existing pattern — Tailwind mobile-first**:
```tsx
// Default = mobile, md: = tablet+
className="h-11 w-11 md:h-8 md:w-8"  // 44px mobile, 32px desktop
className="p-4 md:p-8"                 // 16px mobile, 32px desktop
className="max-w-[90vw] md:max-w-[500px]"  // viewport-relative on mobile
className="hidden md:flex"              // hidden mobile, flex desktop
```

**Existing pattern — Tailwind max-* breakpoints (v4)**:
```tsx
// max-sm: applies BELOW 640px (mobile only)
className="max-sm:hidden"  // hidden on mobile
className="hidden max-sm:inline"  // shown only on mobile
```

**New pattern — z-index tokens** (after Phase 4):
```css
/* In @theme block of index.css */
@theme {
  --z-modal: 70;
  --z-chat: 1000;
  --z-notification: 10000;
}

/* In components — replace z-[70] with: */
className="z-[var(--z-modal)]"
```

### 6. Verification Checklist

Before submitting, verify at each viewport (375, 414, 768, 820, 1280):

- [ ] No horizontal overflow (document.body.scrollWidth ≤ window.innerWidth)
- [ ] No clipped interactive elements
- [ ] All buttons/links ≥ 44×44px on mobile viewports
- [ ] Chat input visible above virtual keyboard
- [ ] Dark mode renders correctly
- [ ] `prefers-reduced-motion: reduce` — no animations, no visual breakage
- [ ] Existing E2E tests pass: `npm run test:e2e`
- [ ] New E2E tests pass
- [ ] Type check passes: `npm run type-check`
- [ ] Lint passes: `npm run lint`

### 7. Lighthouse Audit

```bash
# Run Lighthouse CLI (install if needed: npm i -g lighthouse)
lighthouse http://localhost:5173 --preset=desktop --output=json
lighthouse http://localhost:5173 --preset=perf --emulated-form-factor=mobile --output=json

# Key pages to audit:
# /                  (home)
# /projects          (board)
# /pipeline          (pipeline builder)
# /settings          (settings)
```

**Thresholds**: Performance ≥ 90, Accessibility ≥ 95 on mobile.
