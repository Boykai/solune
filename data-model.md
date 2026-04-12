# Data Model: Simplify Page Headers for Focused UI

**Feature**: Simplify Page Headers | **Date**: 2026-04-12 | **Status**: Complete

## Entity: CompactPageHeaderStat

A single statistic displayed as an inline chip/pill in the compact page header.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `label` | `string` | Required, non-empty | Short uppercase label for the stat (e.g., "Board columns") |
| `value` | `string` | Required, non-empty | Display value for the stat (e.g., "12") |

### Usage

Stats are rendered as small pill/chip elements in a flex row. Each chip shows the label in small uppercase text and the value in slightly larger text.

---

## Entity: CompactPageHeaderProps

The full props interface for the `CompactPageHeader` component.

### Fields

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `eyebrow` | `string` | Required | — | Small uppercase label above the title (e.g., "Mission Control") |
| `title` | `string` | Required | — | Main heading text (e.g., "Every project, mapped and moving.") |
| `description` | `string` | Required | — | Subtitle text, single-line with line-clamp-1, expands on hover |
| `badge` | `string` | Optional | `undefined` | Badge text displayed as a pill (e.g., "owner/repo") |
| `stats` | `CompactPageHeaderStat[]` | Optional | `[]` | Array of stat objects rendered as inline chips |
| `actions` | `ReactNode` | Optional | `undefined` | Action buttons rendered in the right zone |
| `className` | `string` | Optional | `undefined` | Additional CSS classes forwarded to the root element |

### Prop Migration from CelestialCatalogHero

| CelestialCatalogHero Prop | CompactPageHeader Prop | Change |
|---------------------------|----------------------|--------|
| `eyebrow` | `eyebrow` | No change |
| `title` | `title` | No change |
| `description` | `description` | Demoted to single-line subtitle |
| `badge` | `badge` | No change |
| `note` | ❌ Removed | "Current Ritual" aside eliminated |
| `stats` | `stats` | Same interface; rendered as chips instead of moonwell cards |
| `actions` | `actions` | No change |
| `className` | `className` | No change |

---

## Component DOM Structure

### CelestialCatalogHero (BEFORE — to be deleted)

```text
<section>                              ← ~350–450px tall
  <div.catalog-hero-decor>             ← Decorative background (orbits, stars, beams)
    <div.catalog-hero-ambient-glow>
    <div.catalog-hero-orbit> × 3
    <div.catalog-hero-moon>
    <div.catalog-hero-star> × 2
    <div.catalog-hero-beam>
  </div>
  <div.grid>                           ← Two-column grid on LG
    <div>                              ← Left: Content
      <span.celestial-sigil> + <p.eyebrow>
      <span.badge> (optional)
      <h2.title>
      <p.description>
      <div.actions>
      <div.stats>                      ← Large moonwell cards
    </div>
    <div.catalog-hero-aside-wrap>      ← Right: Decorative aside panel (LG only, ~22rem)
      <div.hanging-stars>
      <div.catalog-hero-aside>
        <div> × 7 decorative elements
        <div.catalog-hero-note>        ← "Current Ritual" with note/description
      </div>
    </div>
  </div>
</section>
```

**DOM nodes**: ~25+ elements (decorative + content)

### CompactPageHeader (AFTER — to be created)

```text
<header>                               ← ~80–100px tall
  <div.flex>                           ← Single-row layout
    <div>                              ← Left: Content
      <div.flex>                       ← Eyebrow + badge row
        <p.eyebrow>
        <span.badge> (optional)
      </div>
      <h2.title>
      <p.description>                  ← line-clamp-1, expands on hover
    </div>
    <div>                              ← Right: Actions
      {actions}
    </div>
  </div>
  <div.stats>                          ← Stats row (chips)
    <span.chip> × N                    ← Inline pill/chip elements
  </div>
</header>
```

**DOM nodes**: ~8–12 elements (content only, no decorative)

---

## State Transitions

This feature has no state machine or data model changes. The only "state" is the mobile stats toggle:

```text
Mobile Stats Toggle:
  Initial → collapsed (stats hidden)
  User taps toggle → expanded (stats visible)
  User taps toggle again → collapsed
  Viewport resizes to ≥640px → stats always visible (toggle hidden)
```

---

## Page-Specific Prop Values

### ProjectsPage

```typescript
<CompactPageHeader
  eyebrow="Mission Control"
  title="Every project, mapped and moving."
  description="Live Kanban view of your GitHub Project..."
  badge={selectedProject ? `${selectedProject.owner_login}/${selectedProject.name}` : 'Awaiting project'}
  stats={heroStats}
  actions={<>...</>}
/>
```

### AgentsPage

```typescript
<CompactPageHeader
  eyebrow="Celestial Catalog"
  title="Shape your agent constellation."
  description="Browse repository agents in a broader catalog..."
  badge={repo ? `${repo.owner}/${repo.name}` : 'Awaiting repository'}
  stats={[
    { label: 'Board columns', value: String(columns.length) },
    { label: 'Assignments', value: String(assignedCount) },
    { label: 'Mapped states', value: String(Object.keys(agentConfig.localMappings).length) },
    { label: 'Project', value: selectedProject?.name ?? 'Unselected' },
  ]}
  actions={<>...</>}
/>
```

### AgentsPipelinePage

```typescript
<CompactPageHeader
  eyebrow="Constellation Flow"
  title="Orchestrate agents across every stage."
  description="Build custom pipelines that route issues through agents..."
  badge={selectedProject ? `${selectedProject.owner_login}/${selectedProject.name}` : 'Awaiting project'}
  stats={[...]}
  actions={<>...</>}
/>
```

### ToolsPage

```typescript
<CompactPageHeader
  eyebrow="Tool Forge"
  title="Equip your agents with MCP tools."
  description="Upload and manage MCP configurations..."
  badge={repo ? repo.name : 'Awaiting repository'}
  stats={[
    { label: 'Repository', value: repo ? repo.name : 'Unlinked' },
    { label: 'Project', value: selectedProject?.name ?? 'Unselected' },
  ]}
  actions={<>...</>}
/>
```

### ChoresPage

```typescript
<CompactPageHeader
  eyebrow="Ritual Maintenance"
  title="Turn upkeep into a visible rhythm."
  description="Organize recurring repository chores..."
  badge={repo ? `${repo.owner}/${repo.name}` : 'Awaiting repository'}
  stats={[
    { label: 'Board columns', value: String(boardData?.columns.length ?? 0) },
    { label: 'Project', value: selectedProject?.name ?? 'Unselected' },
    { label: 'Repository', value: repo ? repo.name : 'Unlinked' },
    { label: 'Automation mode', value: projectId ? 'Live' : 'Idle' },
  ]}
  actions={<>...</>}
/>
```

### HelpPage

```typescript
<CompactPageHeader
  eyebrow="// Guidance & support"
  title="Help Center"
  description="Everything you need to navigate your celestial workspace."
  actions={<Button onClick={restart} variant="outline" size="sm">...</Button>}
/>
```
