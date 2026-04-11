# Quickstart: Simplify Page Headers for Focused UI

**Feature**: Simplify Page Headers | **Date**: 2026-04-11

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

Create `src/components/common/CompactPageHeader.tsx`:

```typescript
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface CompactPageHeaderStat {
  label: string;
  value: string;
}

interface CompactPageHeaderProps {
  eyebrow: string;
  title: string;
  description: string;
  badge?: string;
  stats?: CompactPageHeaderStat[];
  actions?: ReactNode;
  className?: string;
}

export function CompactPageHeader({
  eyebrow,
  title,
  description,
  badge,
  stats = [],
  actions,
  className,
}: CompactPageHeaderProps) {
  return (
    <header className={cn('rounded-2xl border border-border/70 bg-background/35 px-5 py-4 backdrop-blur-sm sm:px-6', className)}>
      <div className="group flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs uppercase tracking-[0.25em] text-primary/85">{eyebrow}</p>
            {badge && (
              <span className="rounded-full border border-primary/25 bg-primary/10 px-2.5 py-0.5 text-[11px] uppercase tracking-[0.18em] text-primary">
                {badge}
              </span>
            )}
          </div>
          <h2 className="mt-1.5 text-xl font-semibold leading-tight tracking-tight text-foreground sm:text-2xl">
            {title}
          </h2>
          <p className="mt-1 line-clamp-1 text-sm leading-relaxed text-muted-foreground group-hover:line-clamp-none">
            {description}
          </p>
        </div>
        {actions && (
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {actions}
          </div>
        )}
      </div>
      {stats.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {stats.map((stat) => (
            <span
              key={stat.label}
              className="inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-muted/50 px-2.5 py-1 text-xs"
            >
              <span className="text-muted-foreground">{stat.label}</span>
              <span className="font-medium text-foreground">{stat.value}</span>
            </span>
          ))}
        </div>
      )}
    </header>
  );
}
```

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
