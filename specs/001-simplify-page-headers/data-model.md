# Data Model: Simplify Page Headers for Focused UI

**Feature**: `001-simplify-page-headers`  
**Date**: 2026-04-12  
**Status**: Complete

## Overview

This feature does not add backend entities or persistence tables. Its design surface is a reusable frontend component contract plus page-level prop composition.

## Entity: `CompactPageHeaderProps`

Reusable page-header props consumed by `/home/runner/work/solune/solune/solune/frontend/src/components/common/CompactPageHeader.tsx`.

| Field | Type | Required | Validation / Rules | Notes |
|------|------|----------|--------------------|-------|
| `eyebrow` | `string` | Yes | Non-empty display label | Small uppercase context label shown above/beside the title. |
| `title` | `string` | Yes | Non-empty display heading | Primary page heading. |
| `description` | `string` | Yes | Rendered as a single truncated line; full text available on hover/expand behavior | Subtitle text beneath the title. |
| `badge` | `string \| undefined` | No | Omit entirely when unavailable | Center/inline badge text such as repository/project status. |
| `stats` | `CompactPageHeaderStat[] \| undefined` | No | Empty or omitted collection must not leave empty visual space | Inline stat chips on desktop; mobile toggle when present. |
| `actions` | `ReactNode \| undefined` | No | Actions must remain interactive and preserve prior behavior | Right-side action buttons/links. |
| `className` | `string \| undefined` | No | Optional style extension only | No `note` prop is allowed. |

## Entity: `CompactPageHeaderStat`

Individual stat chip model used in the header.

| Field | Type | Required | Validation / Rules | Notes |
|------|------|----------|--------------------|-------|
| `label` | `string` | Yes | Short, non-empty label | Examples: `Board columns`, `Project`, `Repository`. |
| `value` | `string` | Yes | Non-empty display value; may be truncated visually | Derived from existing page data/query state. |

## Relationship Model

```text
Page Route
  └── builds CompactPageHeaderProps
        ├── optional badge
        ├── optional stats[] -> CompactPageHeaderStat
        └── optional actions ReactNode
```

## Affected Page Mappings

| Page | Header Data Shape | Notes |
|------|-------------------|-------|
| `ProjectsPage` | Eyebrow, title, description, project badge, computed `heroStats`, two anchor actions | Primary board surface; must preserve board toolbar/actions below the header. |
| `AgentsPage` | Eyebrow, title, description, repo badge, four stat chips, two anchor actions | Stats include board columns, assignments, mapped states, and selected project. |
| `AgentsPipelinePage` | Eyebrow, title, description, project badge, pipeline-related stats, two actions | Must preserve editor and saved-workflow entry points. |
| `ToolsPage` | Eyebrow, title, description, repo badge, repository/project stats, three actions | Header remains compact even with multiple action buttons. |
| `ChoresPage` | Eyebrow, title, description, repo badge, four stat chips, two actions | Uses board and workflow-derived repository context. |
| `HelpPage` | Eyebrow, title, description, one action, no stats required | Must render cleanly when badge/stats are absent. |

## Validation Rules Derived from the Spec

1. Header must render without decorative hero elements.
2. Description is single-line by default and should not expand page height permanently.
3. Missing `badge`, `stats`, or `actions` must collapse cleanly with no placeholder chrome.
4. Mobile behavior must keep actions accessible and hide stats by default behind a toggle.
5. `note`/“Current Ritual” content is not part of the component model.

## State Transitions

### Mobile stats disclosure

```text
closed (default on mobile when stats exist)
  └── user activates stats toggle
      -> open
open
  └── user activates stats toggle
      -> closed
desktop/tablet wide layout
  └── stats shown inline without disclosure control
```

### Responsive layout modes

```text
desktop/wide
  -> single-row or wrapped compact layout with visible stats chips
mobile/narrow
  -> stacked/wrapped compact layout with accessible actions and hidden-by-default stats
```
