# Quickstart: Simplify Page Headers for Focused UI

**Feature**: Simplify Page Headers | **Date**: 2026-04-11

> **Status note (2026-04-11):** The backend conversations and chat APIs are complete. The frontend multi-panel workflow is implemented, but the product surface is still being refined, so expect the UI details in this feature quickstart to evolve.

> **Status note (2026-04-11):** The backend conversations and chat APIs are complete. The frontend multi-panel workflow is implemented, but the product surface is still being refined, so expect the UI details in this feature quickstart to evolve.

## Prerequisites

- Node.js ≥18 with npm
- Git

## Setup

```bash
cd solune/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Implementation Steps

### Step 1: Create CompactPageHeader

Create `src/components/common/CompactPageHeader.tsx`.

Do **not** duplicate the full component implementation in this guide. `CompactPageHeader` has interactive/mobile behavior and styling details that can change over time, so the source file should remain the single source of truth:

- Source: [`src/components/common/CompactPageHeader.tsx`](solune/frontend/src/components/common/CompactPageHeader.tsx)
- Keep the existing production implementation, including any current hooks, icons, responsive stats behavior, and updated class names.

This quickstart focuses on where to use `CompactPageHeader`, rather than embedding a copy of the component that can drift from the real implementation.

### Step 2: Replace Hero in Each Page

For each of the 6 pages, make two changes:

1. **Change import**: `CelestialCatalogHero` → `CompactPageHeader`
2. **Drop `note` prop** (if present)
3. **Drop `className="projects-catalog-hero"`** (AgentsPipelinePage, ProjectsPage only)

Example for ProjectsPage.tsx:

```diff
- import { CelestialCatalogHero } from '@/components/common/CelestialCatalogHero';
+ import { CompactPageHeader } from '@/components/common/CompactPageHeader';

-      <CelestialCatalogHero
-        className="projects-catalog-hero"
+      <CompactPageHeader
         eyebrow="Mission Control"
         title="Every project, mapped and moving."
         description="..."
         badge={...}
-        note="..."
         stats={heroStats}
         actions={...}
       />
```

### Step 3: Delete Dead Code

```bash
# Delete the old hero component and its tests
rm src/components/common/CelestialCatalogHero.tsx
rm src/components/common/CelestialCatalogHero.test.tsx
```

### Step 4: Remove Orphaned CSS

Remove the `.dark .projects-catalog-hero .catalog-hero-*` block from `src/index.css` (lines ~432–489).

**DO NOT remove**: `.moonwell`, `.hanging-stars`, `.celestial-*` animations (used elsewhere).

## Run Tests

```bash
cd solune/frontend

# Run all frontend tests
npm test

# Run only the component test
npm test -- --reporter=verbose CompactPageHeader

# Run page-specific tests
npm test -- --reporter=verbose ProjectsPage
npm test -- --reporter=verbose AgentsPage
npm test -- --reporter=verbose AgentsPipelinePage
```

## Run Lint & Type Check

```bash
cd solune/frontend

# ESLint
npx eslint .

# TypeScript type check
npx tsc --noEmit
```

## Verify UI Behavior

1. **Navigate to each of the 6 pages**:
   - `/projects` — Projects page
   - `/agents` — Agents page
   - `/agents/pipeline` — Agents Pipeline page
   - `/tools` — Tools page
   - `/chores` — Chores page
   - `/help` — Help page

2. **Check compact header** on each page:
   - Header height is ~80–100px (not ~350–450px)
   - Eyebrow text, title, and badge are visible
   - Description shows as single line, expands on hover
   - Stats show as inline chips (not large moonwell cards)
   - Action buttons are accessible

3. **Check mobile viewport** (Chrome DevTools → 375px width):
   - Header remains compact
   - Stats are hidden (or behind a toggle)
   - Actions are still accessible

4. **Check no regressions**:
   - Sidebar celestial animations still work
   - LoginPage decorations (hanging-stars, celestial-float) still work
   - CelestialLoader animations still work
   - NotFoundPage and ErrorBoundary decorations still work

## Key Files Reference

### Create

| File | Purpose |
|------|---------|
| `src/components/common/CompactPageHeader.tsx` | New compact header component |
| `src/components/common/CompactPageHeader.test.tsx` | Tests for new component |

### Modify

| File | Changes |
|------|---------|
| `src/pages/ProjectsPage.tsx` | Swap import, remove `note` prop, remove `className="projects-catalog-hero"` |
| `src/pages/AgentsPage.tsx` | Swap import, remove `note` prop |
| `src/pages/AgentsPipelinePage.tsx` | Swap import, remove `note` prop, remove `className="projects-catalog-hero"` |
| `src/pages/ToolsPage.tsx` | Swap import, remove `note` prop |
| `src/pages/ChoresPage.tsx` | Swap import, remove `note` prop |
| `src/pages/HelpPage.tsx` | Swap import (no `note` used) |
| `src/index.css` | Remove `.dark .projects-catalog-hero .catalog-hero-*` rules |

### Delete

| File | Reason |
|------|--------|
| `src/components/common/CelestialCatalogHero.tsx` | Replaced by CompactPageHeader |
| `src/components/common/CelestialCatalogHero.test.tsx` | Tests for deleted component |

### Untouched

| File | Reason |
|------|--------|
| `src/layout/Sidebar.tsx` | Uses `celestial-orbit-spin` independently |
| `src/layout/AppLayout.tsx` | Uses `celestial-*` classes independently |
| `src/components/common/CelestialLoader.tsx` | Uses `celestial-orbit-spin` independently |
| `src/pages/LoginPage.tsx` | Uses `hanging-stars`, `celestial-float`, `celestial-pulse-glow` independently |
| All components using `.moonwell` | `.moonwell` CSS is retained |

## Troubleshooting

### Build fails with "Cannot find module CelestialCatalogHero"

Ensure all 6 pages have updated their imports from `CelestialCatalogHero` to `CompactPageHeader`.

### Tests fail referencing "Current Ritual"

The `CelestialCatalogHero.test.tsx` file should be deleted, not updated. The `CompactPageHeader.test.tsx` replaces it.

### Dark mode looks broken on ProjectsPage/AgentsPipelinePage

The `.dark .projects-catalog-hero` CSS overrides have been removed. Since `CompactPageHeader` doesn't use the `projects-catalog-hero` className, these overrides are no longer needed. Verify that `CompactPageHeader` renders correctly in both light and dark modes without special overrides.
