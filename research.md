# Research: Simplify Page Headers for Focused UI

**Feature**: Simplify Page Headers | **Date**: 2026-04-12 | **Status**: Complete

## R1: CSS Class Removal Safety Analysis

**Decision**: Remove only `.dark .projects-catalog-hero .catalog-hero-*` scoped CSS rules from `index.css` (lines ~432–489). Retain all `celestial-*` animation classes, `.moonwell`, and `.hanging-stars`.

**Rationale**: A thorough codebase search reveals that many CSS classes used within `CelestialCatalogHero` are shared with other components throughout the application. Only the `.projects-catalog-hero`-scoped dark mode overrides are exclusive to the hero component.

**Shared class usage (RETAIN)**:

| CSS Class | Components Using It (Outside CelestialCatalogHero) |
|-----------|---------------------------------------------------|
| `moonwell` | AgentCard, AgentIconCatalog, AgentsPanel (6×), ToolCard, ToolsPanel, GitHubMcpConfigGenerator (2×), ChoresSpotlight (2×), PipelineSelector, ChoresToolbar (3×), ActivityPage, AgentsPipelinePage, FeaturedRitualsPanel, ChoreCard, ProjectIssueLaunchPanel, FeatureGuideCard, SavedWorkflowsList (2×), PipelineAnalytics (4×), PipelineStagesOverview, PipelineToolbar |
| `hanging-stars` | LoginPage.tsx (line 65) |
| `celestial-orbit-spin` | Sidebar.tsx, AppLayout.tsx, CelestialLoader.tsx, LoginPage.tsx, AnimatedBackground.tsx |
| `celestial-orbit-spin-reverse` | Same components as `celestial-orbit-spin` |
| `celestial-twinkle` | CelestialLoadingProgress.tsx, ProjectSelectionEmptyState.tsx, AppLayout.tsx |
| `celestial-float` | LoginPage.tsx, NotFoundPage.tsx, App.tsx, ErrorBoundary.tsx |
| `celestial-pulse-glow` | NotificationBell.tsx, LoginPage.tsx, Sidebar.tsx, AppLayout.tsx, CelestialLoader.tsx, TourProgress.tsx |

**Exclusive to hero (REMOVE)**:

| CSS Rule | Location in index.css |
|----------|-----------------------|
| `.dark .projects-catalog-hero.section-aurora` | Line ~432 |
| `.dark .projects-catalog-hero .catalog-hero-decor` | Line ~448 |
| `.dark .projects-catalog-hero .catalog-hero-ambient-glow` | Line ~452 |
| `.dark .projects-catalog-hero .catalog-hero-orbit` | Line ~457 |
| `.dark .projects-catalog-hero .catalog-hero-moon` | Line ~461 |
| `.dark .projects-catalog-hero .catalog-hero-aside-moon` | Line ~462 |
| `.dark .projects-catalog-hero .catalog-hero-aside` | Line ~468 |
| `.dark .projects-catalog-hero .catalog-hero-aside-sun` | Line ~475 |
| `.dark .projects-catalog-hero .catalog-hero-aside-orbit-*` | Lines ~479–481 |
| `.dark .projects-catalog-hero .catalog-hero-aside-core` | Line ~481 |
| `.dark .projects-catalog-hero .catalog-hero-note` | Line ~485 |

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Remove all celestial animation CSS | Breaks 15+ components that use `celestial-*` classes for sidebar, loading, login, error, and background animations |
| Remove `moonwell` CSS class | Breaks 30+ UI elements across agents, tools, chores, pipeline, and board components |
| Remove `hanging-stars` CSS | Breaks decorative stars in LoginPage |
| Keep all hero CSS "just in case" | Leaves ~60 lines of dead CSS; contradicts simplicity principle |

---

## R2: CompactPageHeader Component Architecture

**Decision**: Create a single `CompactPageHeader.tsx` component with a responsive flexbox layout. Use a `<header>` semantic element. Stats render as inline pill/chip elements. Description uses `line-clamp-1` with `group-hover:line-clamp-none` for expand-on-hover.

**Rationale**: The replacement component needs to:

1. Accept the same props as `CelestialCatalogHero` minus `note` (which is dropped per issue decision)
2. Use a single-row layout (~80–100px height vs ~350–450px)
3. Render stats as small chips instead of large moonwell cards
4. Have no decorative elements (orbits, stars, beams)

The `<header>` element is more semantically correct than the current `<section>` for page headers. The `cn()` utility from `@/lib/utils` is used for conditional className merging, consistent with all other components in the codebase.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Keep `<section>` element | `<header>` is more semantically appropriate for page headings; improves accessibility |
| Use CSS Grid instead of Flexbox | Over-engineered for a simple three-zone layout; flexbox handles the single-row case naturally |
| Use a UI library card component | Adds dependency on shadcn Card; a simple `<header>` with Tailwind is sufficient |
| Create separate mobile and desktop header components | Violates DRY; responsive Tailwind classes handle both layouts in one component |

---

## R3: Stats Display Strategy

**Decision**: Stats render as inline chips/pills on desktop (always visible) and are hidden behind a toggle on mobile (< 640px). The toggle is a simple button that expands/collapses the stats row.

**Rationale**: The issue recommends "Stats on mobile: always visible or collapsible? Recommend hidden behind a toggle on mobile to avoid crowding." Desktop viewports have sufficient width for 2–4 stat chips. Mobile viewports (< 640px) would crowd the header if stats are always visible.

The implementation uses:

- Desktop: `flex flex-wrap gap-2` for inline chips, always visible
- Mobile: `hidden sm:flex` by default, toggled with a `useState` hook and a small icon button

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Always visible on mobile | Crowds header on phones; pushes actions below fold |
| Stats removed on mobile entirely | Loses information; no recovery path |
| Horizontal scrollable row on mobile | Touch-scroll conflicts with page scroll; poor discoverability |
| Separate stats tooltip on mobile | Non-standard UX; requires precise tap target |

---

## R4: Description Display Strategy

**Decision**: Description renders as a single-line subtitle with `line-clamp-1`. On hover, the description expands to show full text via `group-hover:line-clamp-none`. On mobile, the description also truncates with an expand tap.

**Rationale**: The issue states "Description demoted to a single-line subtitle (line-clamp-1, expands on hover)." This keeps the header compact while preserving full description accessibility. The `group` + `group-hover` Tailwind pattern is standard and requires no JavaScript for the desktop hover interaction.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Always show full description | Increases header height beyond 100px target on pages with long descriptions |
| Tooltip for description | Less discoverable; requires explicit hover/click interaction |
| Remove description entirely | Loses context for new users; description provides useful page context |
| Two-line truncation (line-clamp-2) | Still variable height; single-line is more predictable |

---

## R5: Rollout Strategy

**Decision**: Big-bang rollout — replace `CelestialCatalogHero` with `CompactPageHeader` on all 6 pages in a single PR. Delete `CelestialCatalogHero.tsx` after migration.

**Rationale**: The issue recommends "big-bang — all 6 pages share the same component, replacement is prop-compatible." All 6 pages use the exact same component with the same prop interface. The new component accepts a subset of the same props (minus `note`). There is no data model change, no backend change, and no gradual migration benefit.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Gradual rollout (1 page per PR) | Adds 5 extra PRs; both components coexist with no benefit; more merge conflicts |
| Feature flag (show old/new header) | Over-engineered for a visual-only, non-data change; adds dead code |
| A/B test | No metrics infrastructure for header comparison; visual preference is already decided |
