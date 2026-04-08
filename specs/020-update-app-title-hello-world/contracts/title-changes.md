# Contract: Title Text Changes

**Feature**: 020-update-app-title-hello-world | **Date**: 2026-04-08

## Contract Definition

This contract defines the exact text replacements required across all files to update the app title from "Solune" to "Hello World".

### Preconditions

- All target files exist at their specified paths
- The old text values match exactly (line numbers may shift if other changes are merged first)

### Postconditions

- Browser tab displays "Hello World" on all pages
- Sidebar brand heading shows "Hello World" when expanded
- Login page heading shows "Hello World"
- All unit tests pass with updated assertions
- All e2e tests pass with updated assertions
- No other functional behavior is changed

### Invariants

- The Sidebar brand text is only visible when `isCollapsed === false` (existing behavior, unchanged)
- The LoginPage heading is only visible to unauthenticated users (existing behavior, unchanged)
- The `<title>` tag applies to all pages in the SPA (existing behavior, unchanged)

### Change Specifications

#### C1: HTML Title Tag

```html
<!-- Before -->
<title>Solune</title>

<!-- After -->
<title>Hello World</title>
```

**File**: `solune/frontend/index.html`
**Acceptance**: `document.title === "Hello World"` in browser console

#### C2: Sidebar Brand Text

```tsx
// Before
<span className="block text-lg font-display font-medium tracking-[0.08em] text-foreground">
  Solune
</span>

// After
<span className="block text-lg font-display font-medium tracking-[0.08em] text-foreground">
  Hello World
</span>
```

**File**: `solune/frontend/src/layout/Sidebar.tsx`
**Acceptance**: Sidebar shows "Hello World" when expanded, nothing when collapsed

#### C3: Login Page Heading

```tsx
// Before
<h2 className="mb-2 text-4xl font-display font-medium tracking-[0.08em] text-foreground">
  Solune
</h2>

// After
<h2 className="mb-2 text-4xl font-display font-medium tracking-[0.08em] text-foreground">
  Hello World
</h2>
```

**File**: `solune/frontend/src/pages/LoginPage.tsx`
**Acceptance**: Login page shows "Hello World" heading
