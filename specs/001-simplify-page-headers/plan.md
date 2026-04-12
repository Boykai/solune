# Implementation Plan: Simplify Page Headers for Focused UI

**Branch**: `copilot/speckit-plan-simplify-page-headers` | **Date**: 2026-04-12 | **Spec**: [#1483](https://github.com/Boykai/solune/issues/1483)
**Input**: Parent issue #1483 — Replace CelestialCatalogHero hero sections (~20% viewport, ~350–450px) with compact single-row page headers across 6 pages.

## Summary

Replace the large `CelestialCatalogHero` component (~350–450px tall) with a new `CompactPageHeader` component (~80–100px tall) across all 6 pages that use it. The compact header uses a single-row layout: eyebrow + title on the left, badge in the center, action buttons on the right. Stats are rendered as small pill/chip elements instead of large moonwell cards. All decorative celestial elements (orbits, stars, beams, "Current Ritual" aside) are removed from page headers. After migration, `CelestialCatalogHero.tsx` is deleted and orphaned CSS exclusively used by the hero component is removed.

| Phase | Scope | Key Output |
|-------|-------|------------|
| 1 | New compact header component | `CompactPageHeader.tsx` in `components/common/` |
| 2 | Replace hero in 6 pages (parallel) | Updated `ProjectsPage`, `AgentsPage`, `AgentsPipelinePage`, `ToolsPage`, `ChoresPage`, `HelpPage` |
| 3 | Clean up dead code | Delete `CelestialCatalogHero.tsx`, remove orphaned `catalog-hero-*` / `.projects-catalog-hero` CSS from `index.css` |
| 4 | Verification | `vitest run`, `eslint`, `tsc --noEmit`, visual smoke test |

## Technical Context

**Language/Version**: TypeScript 5.x (React 18)
**Primary Dependencies**: React 18 + Tailwind CSS 4 + `cn()` utility from `@/lib/utils`
**Storage**: N/A (frontend-only change)
**Testing**: Vitest (statements ≥60%, branches ≥52%, functions ≥50%)
**Target Platform**: SPA in modern browsers (desktop + mobile)
**Project Type**: Web application (frontend-only change)
**Performance Goals**: Reclaim ~270–370px of vertical space per page; no new dependencies; reduced DOM node count per page
**Constraints**: Prop-compatible replacement (same props minus `note`); theme preserved in sidebar/global chrome; `moonwell` CSS class retained (used by 30+ other components); `celestial-*` animation classes retained (used by Sidebar, AppLayout, LoginPage, CelestialLoader, etc.); `hanging-stars` retained (used by LoginPage)
**Scale/Scope**: 1 component created, 6 pages modified, 1 component + 1 test file deleted, 1 CSS file cleaned up

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Feature fully specified in parent issue #1483 with phases, file list, and explicit decisions |
| II. Template-Driven Workflow | ✅ PASS | This plan follows `plan-template.md`; supplementary artifacts generated per workflow |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan agent produces plan; implement agent will execute phased tasks |
| IV. Test Optionality | ✅ PASS | Tests included for the new component; existing CelestialCatalogHero tests replaced with CompactPageHeader tests |
| V. Simplicity and DRY | ✅ PASS | Single shared component replaces single shared component; net code reduction (~119 lines deleted, ~50 lines added); no new abstractions |

**Gate Result**: PASS — no violations. Proceed to Phase 0.

### Post-Design Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | All design artifacts trace back to parent issue requirements |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates |
| III. Agent-Orchestrated Execution | ✅ PASS | Clear phase boundaries; Phases 1–3 sequential, Phase 2 pages are parallel |
| IV. Test Optionality | ✅ PASS | New component tested; hero tests replaced with header tests |
| V. Simplicity and DRY | ✅ PASS | CompactPageHeader is simpler (fewer lines, no decorative DOM, no aside panel); no new dependencies |

**Post-Design Gate Result**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
plan.md              # This file (speckit.plan output)
research.md          # Phase 0 output (technical decisions)
data-model.md        # Phase 1 output (component interface definitions)
quickstart.md        # Phase 1 output (developer guide)
contracts/           # Phase 1 output (component API spec)
└── compact-page-header-api.yaml
```

### Source Code (repository root)

```text
solune/frontend/src/
├── components/common/
│   ├── CompactPageHeader.tsx              # CREATE — new compact header component
│   ├── CompactPageHeader.test.tsx         # CREATE — tests for new component
│   ├── CelestialCatalogHero.tsx           # DELETE after Phase 2
│   └── CelestialCatalogHero.test.tsx      # DELETE after Phase 2
├── pages/
│   ├── ProjectsPage.tsx                   # MODIFY — swap CelestialCatalogHero → CompactPageHeader
│   ├── AgentsPage.tsx                     # MODIFY — same
│   ├── AgentsPipelinePage.tsx             # MODIFY — same
│   ├── ToolsPage.tsx                      # MODIFY — same
│   ├── ChoresPage.tsx                     # MODIFY — same
│   └── HelpPage.tsx                       # MODIFY — same
└── index.css                              # MODIFY — remove orphaned .projects-catalog-hero and catalog-hero-* CSS rules
```

**Structure Decision**: Frontend-only change. All files in `solune/frontend/src/`. New component follows existing pattern in `components/common/`. No new directories.

## Complexity Tracking

> No Constitution Check violations — this section is intentionally empty.

---

## Phase 0: Research

### R1: CSS Class Removal Safety Analysis

**Decision**: Remove only `catalog-hero-*` scoped CSS rules from `index.css` (the `.dark .projects-catalog-hero .catalog-hero-*` block, lines ~432–489). Retain all `celestial-*` animation classes, `moonwell`, and `hanging-stars`.

**Rationale**: Codebase analysis reveals that the following classes are referenced outside `CelestialCatalogHero.tsx` and **CANNOT** be safely removed:

| CSS Class | Used Outside Hero By |
|-----------|---------------------|
| `moonwell` | AgentCard, AgentIconCatalog, AgentsPanel, ToolCard, ToolsPanel, ChoresSpotlight, PipelineSelector, PipelineAnalytics, PipelineToolbar, ChoresToolbar, ChoreCard, ProjectIssueLaunchPanel, FeatureGuideCard, SavedWorkflowsList, ActivityPage, GitHubMcpConfigGenerator, AgentsPipelinePage (30+ references) |
| `hanging-stars` | LoginPage.tsx (line 65) |
| `celestial-orbit-spin` | Sidebar, AppLayout, CelestialLoader, LoginPage, AnimatedBackground |
| `celestial-twinkle` | CelestialLoadingProgress, ProjectSelectionEmptyState, AppLayout |
| `celestial-float` | LoginPage, NotFoundPage, App.tsx, ErrorBoundary |
| `celestial-pulse-glow` | NotificationBell, LoginPage, Sidebar, AppLayout, CelestialLoader, TourProgress |

Only the `.dark .projects-catalog-hero .catalog-hero-*` override block (lines 432–489 of `index.css`) is exclusively scoped to `CelestialCatalogHero` via the `projects-catalog-hero` className applied only in `ProjectsPage.tsx` and `AgentsPipelinePage.tsx`.

**Alternatives considered**:

- Remove all celestial animation CSS: Breaks 15+ other components that use these classes.
- Remove `moonwell` CSS: Breaks 30+ components across the application.
- Remove `hanging-stars`: Breaks LoginPage decorative elements.

### R2: CompactPageHeader Component Design

**Decision**: Single-row flexbox layout with three zones: left (eyebrow + title + description), center (badge), right (actions). Stats rendered as inline chip/pill elements beneath the title row. No decorative elements.

**Rationale**: The issue specifies: "Single-row layout: eyebrow + title on left, badge center, action buttons right" and "Stats rendered as small pill/chip elements". Height target is 80–100px. The `note` prop is dropped (the "Current Ritual" aside consumed ~22rem on LG screens and duplicated the description).

**Alternatives considered**:

- Two-row layout (title row + stats row): Exceeds 100px height target on pages with many stats.
- Description as tooltip only: Reduces discoverability; issue recommends "single-line subtitle with line-clamp-1 and expand on hover".
- Keep moonwell cards for stats: Contradicts the issue's decision to use inline chips.

### R3: Stats on Mobile Strategy

**Decision**: Hide stats behind a toggle on mobile viewports (< 640px) to avoid crowding the compact header. On desktop, stats are always visible as inline chips.

**Rationale**: The issue states "Stats on mobile: always visible or collapsible? Recommend hidden behind a toggle on mobile to avoid crowding." Following this recommendation keeps the header compact on mobile while preserving full information access.

**Alternatives considered**:

- Always visible on mobile: Crowds the header on small screens; may push actions below the fold.
- Remove stats on mobile entirely: Loses information without recovery path.
- Collapsible accordion: Over-engineered for 2–4 stat chips.

### R4: Rollout Strategy

**Decision**: Big-bang rollout — replace all 6 pages simultaneously in a single PR.

**Rationale**: The issue states "Recommend big-bang — all 6 pages share the same component, replacement is prop-compatible." Since `CompactPageHeader` accepts a superset of props (minus `note`), all pages can be migrated in one pass. Gradual rollout would require maintaining both components temporarily with no benefit.

**Alternatives considered**:

- Gradual rollout (one page at a time): Adds unnecessary complexity; both components would coexist temporarily.
- Feature flag: Over-engineered for a visual-only change with no data model impact.

---

## Phase 1: Design & Contracts

### 1.1 — CompactPageHeader Props Interface

```typescript
interface CompactPageHeaderStat {
  label: string;
  value: string;
}

interface CompactPageHeaderProps {
  eyebrow: string;          // Small uppercase label above title
  title: string;            // Main heading text
  description: string;      // Subtitle (line-clamp-1, expands on hover)
  badge?: string;           // Optional badge in center zone
  stats?: CompactPageHeaderStat[];  // Inline chip/pill stats
  actions?: ReactNode;      // Action buttons in right zone
  className?: string;       // Additional CSS classes
}
```

**Prop changes from CelestialCatalogHero**:

- ❌ `note` — removed (duplicated description in aside panel)
- All other props retained with same types

### 1.2 — CompactPageHeader Layout

```text
┌─────────────────────────────────────────────────────────────┐
│  ⬡ EYEBROW  [badge]                          [Action] [Act]│
│  Title Text Here                                            │
│  Description as single-line subtitle...                     │
│  [stat chip] [stat chip] [stat chip]                        │
└─────────────────────────────────────────────────────────────┘
```

- **Container**: `<header>` element, border + rounded + backdrop-blur (matches existing page shell style)
- **Height**: ~80–100px (responsive, content-driven)
- **Left zone**: Eyebrow (uppercase, primary color) + title (text-2xl) + description (text-sm, line-clamp-1, expands on hover via group-hover:line-clamp-none)
- **Center zone**: Badge as pill (same style as current hero badge)
- **Right zone**: Actions (flexbox row)
- **Stats row**: Inline chips below the title/description area, small pill styling

### 1.3 — Page Migration Mapping

Each page drops `note` and changes the import. No other prop changes needed.

| Page | Current Import | Line | Props to Drop |
|------|---------------|------|---------------|
| `ProjectsPage.tsx` | `CelestialCatalogHero` | 33, 323 | `note` |
| `AgentsPage.tsx` | `CelestialCatalogHero` | 16, 93 | `note` |
| `AgentsPipelinePage.tsx` | `CelestialCatalogHero` | 27, 107 | `note`, `className="projects-catalog-hero"` |
| `ToolsPage.tsx` | `CelestialCatalogHero` | 10, 32 | `note` |
| `ChoresPage.tsx` | `CelestialCatalogHero` | 14, 83 | `note` |
| `HelpPage.tsx` | `CelestialCatalogHero` | 7, 138 | (no `note` used) |

### 1.4 — CSS Cleanup Scope

Lines to remove from `index.css`:

```css
/* Lines ~432–489: .dark .projects-catalog-hero overrides */
.dark .projects-catalog-hero.section-aurora { ... }
.dark .projects-catalog-hero .catalog-hero-decor { ... }
.dark .projects-catalog-hero .catalog-hero-ambient-glow { ... }
.dark .projects-catalog-hero .catalog-hero-orbit { ... }
.dark .projects-catalog-hero .catalog-hero-moon, ...
.dark .projects-catalog-hero .catalog-hero-aside { ... }
.dark .projects-catalog-hero .catalog-hero-aside-sun { ... }
.dark .projects-catalog-hero .catalog-hero-aside-orbit-outer, ...
.dark .projects-catalog-hero .catalog-hero-note { ... }
```

**NOT removed** (still referenced elsewhere):

- `.moonwell` (lines ~593–607)
- `.hanging-stars` (lines ~1547–1590)
- `.celestial-twinkle`, `.celestial-pulse-glow`, `.celestial-orbit-spin`, `.celestial-float` (lines ~1647–1700)
- All `@keyframes` for celestial animations

---

## Execution Phases

### Phase 1: Create CompactPageHeader Component

| # | Task | File | Action |
|---|------|------|--------|
| 1.1 | Create component | `components/common/CompactPageHeader.tsx` | New compact header with single-row layout |
| 1.2 | Create tests | `components/common/CompactPageHeader.test.tsx` | Render tests, prop forwarding, accessibility |

**Acceptance**: Component renders correctly with all props. Tests pass. Height is ~80–100px.

### Phase 2: Replace Hero in 6 Pages (parallel)

| # | Task | File | Action |
|---|------|------|--------|
| 2.1 | Update import + JSX | `pages/ProjectsPage.tsx` | Swap `CelestialCatalogHero` → `CompactPageHeader`, drop `note` |
| 2.2 | Update import + JSX | `pages/AgentsPage.tsx` | Same |
| 2.3 | Update import + JSX | `pages/AgentsPipelinePage.tsx` | Same, also drop `className="projects-catalog-hero"` |
| 2.4 | Update import + JSX | `pages/ToolsPage.tsx` | Same |
| 2.5 | Update import + JSX | `pages/ChoresPage.tsx` | Same |
| 2.6 | Update import + JSX | `pages/HelpPage.tsx` | Same (no `note` to drop) |

**Acceptance**: All 6 pages render with compact header. No TypeScript errors. Existing page tests still pass.

### Phase 3: Clean Up Dead Code

| # | Task | File | Action |
|---|------|------|--------|
| 3.1 | Delete component | `components/common/CelestialCatalogHero.tsx` | Remove file (119 lines) |
| 3.2 | Delete test file | `components/common/CelestialCatalogHero.test.tsx` | Remove file (110 lines) |
| 3.3 | Remove orphaned CSS | `index.css` | Remove `.dark .projects-catalog-hero .catalog-hero-*` rules (lines ~432–489) |

**Acceptance**: No references to `CelestialCatalogHero` in codebase. No orphaned CSS. Build and lint pass.

### Phase 4: Verification

| # | Task | Command | Expected |
|---|------|---------|----------|
| 4.1 | Frontend tests | `npx vitest run` | All tests pass |
| 4.2 | Lint check | `npx eslint .` | No errors |
| 4.3 | Type check | `npx tsc --noEmit` | No errors |
| 4.4 | Visual smoke test | Docker + browser on all 6 pages | Compact headers render correctly |
| 4.5 | Mobile viewport test | Chrome DevTools responsive mode | Stats hidden behind toggle; header stays compact |

**Acceptance**: Zero test failures, zero lint errors, zero type errors. All 6 pages visually correct.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Removing CSS used elsewhere | Low | High | Verified: only `catalog-hero-*` scoped rules are removed; all shared classes retained |
| Pages depend on hero's large height for layout | Low | Medium | Compact header is content-driven height; page content flows normally below it |
| `note` prop removal breaks TypeScript | Very Low | Low | `note` was optional in CelestialCatalogHeroProps; CompactPageHeader simply omits it |
| Existing page tests reference CelestialCatalogHero internals | Low | Medium | Tests reference text content, not component internals; text content is preserved |
| Mobile stats toggle adds complexity | Low | Low | Simple `useState` toggle with Tailwind responsive classes |

## Dependencies

```text
Phase 1 (Component)
  1.1 create CompactPageHeader ──→ 1.2 create tests

Phase 2 (Page Migration) ── depends on Phase 1
  1.1 CompactPageHeader ──→ 2.1 ProjectsPage
                         ──→ 2.2 AgentsPage        (all parallel)
                         ──→ 2.3 AgentsPipelinePage
                         ──→ 2.4 ToolsPage
                         ──→ 2.5 ChoresPage
                         ──→ 2.6 HelpPage

Phase 3 (Cleanup) ── depends on Phase 2 (all pages migrated)
  2.1–2.6 done ──→ 3.1 delete CelestialCatalogHero.tsx
               ──→ 3.2 delete CelestialCatalogHero.test.tsx
               ──→ 3.3 remove orphaned CSS

Phase 4 (Verification) ── depends on Phase 3
  3.1–3.3 done ──→ 4.1–4.5 full verification
```

## Decisions Log

| Decision | Rationale |
|----------|-----------|
| Drop `note` prop | Duplicated page description; consumed ~22rem on LG screens; "Current Ritual" aside removed per issue |
| Keep `moonwell` CSS | Used by 30+ other components (AgentCard, ToolCard, PipelineAnalytics, etc.) |
| Keep `celestial-*` animations | Used by Sidebar, AppLayout, CelestialLoader, LoginPage, AnimatedBackground, etc. |
| Keep `hanging-stars` CSS | Used by LoginPage.tsx (line 65) |
| Remove `catalog-hero-*` CSS | Only used within CelestialCatalogHero (orphaned after deletion) |
| Big-bang rollout | All 6 pages share same component; prop-compatible replacement; no benefit to gradual rollout |
| Description as line-clamp-1 subtitle | Per issue recommendation; expands on hover for full text |
| Stats as inline chips | Per issue recommendation; replaces large moonwell cards |
| Mobile stats behind toggle | Per issue recommendation; avoids crowding compact header on small viewports |
| Use `<header>` element | More semantic than `<section>` for page headers; improves accessibility |
