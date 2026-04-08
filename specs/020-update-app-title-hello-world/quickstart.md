# Quickstart: Update App Title to "Hello World"

**Feature**: 020-update-app-title-hello-world | **Date**: 2026-04-08

## Prerequisites

- Node.js (version matching `solune/frontend/.nvmrc` or `package.json` engines)
- Repository cloned and on the feature branch

## Step-by-Step Implementation

### Step 1: Update the HTML Title Tag

**File**: `solune/frontend/index.html` (line 7)

Replace:
```html
<title>Solune</title>
```
With:
```html
<title>Hello World</title>
```

### Step 2: Update the Sidebar Brand Text

**File**: `solune/frontend/src/layout/Sidebar.tsx` (line 97)

Replace the text content `Solune` with `Hello World` inside the brand `<span>`.

### Step 3: Update the Login Page Heading

**File**: `solune/frontend/src/pages/LoginPage.tsx` (line 102)

Replace the text content `Solune` with `Hello World` inside the `<h2>` element.

### Step 4: Update Unit Test Assertions

**File**: `solune/frontend/src/layout/Sidebar.test.tsx`

- Line 36: Change `'Solune'` to `'Hello World'` in `getByText()`
- Line 41: Change `'Solune'` to `'Hello World'` in `queryByText()`

### Step 5: Update E2E Test Assertions

**Files**:
- `solune/frontend/e2e/auth.spec.ts` (line 8): Change `'Solune'` to `'Hello World'`
- `solune/frontend/e2e/ui.spec.ts` (lines 47, 71): Change `'Solune'` to `'Hello World'`
- `solune/frontend/e2e/integration.spec.ts` (line 82): Change `'Solune'` to `'Hello World'`
- `solune/frontend/e2e/protected-routes.spec.ts` (line 12): Change `'Solune'` to `'Hello World'`

## Verification

### Run Unit Tests

```bash
cd solune/frontend
npx vitest run src/layout/Sidebar.test.tsx
```

Expected: All tests pass with "Hello World" assertions.

### Visual Verification

1. Start the frontend dev server: `npm run dev` from `solune/frontend/`
2. Open browser to the login page — confirm "Hello World" heading
3. Log in — confirm sidebar brand shows "Hello World"
4. Check browser tab — confirm it shows "Hello World"

### Grep Verification

```bash
# Confirm no remaining app-title "Solune" in the three target files:
grep -n "Solune" solune/frontend/index.html
grep -n "Solune" solune/frontend/src/layout/Sidebar.tsx
grep -n "Solune" solune/frontend/src/pages/LoginPage.tsx
```

Expected: Only comments/JSDoc should remain (if any), not rendered text.
