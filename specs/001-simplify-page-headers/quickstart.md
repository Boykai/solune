# Quickstart: Simplify Page Headers for Focused UI

**Feature**: `001-simplify-page-headers`  
**Date**: 2026-04-12

## Goal

Validate and implement the compact header rollout for the six affected frontend pages under `/home/runner/work/solune/solune/solune/frontend`.

## Prerequisites

- Node.js and npm available
- Dependencies installed for `/home/runner/work/solune/solune/solune/frontend`

## Working Directory

```bash
cd /home/runner/work/solune/solune/solune/frontend
```

## Key Files

- Shared component: `/home/runner/work/solune/solune/solune/frontend/src/components/common/CompactPageHeader.tsx`
- Shared tests: `/home/runner/work/solune/solune/solune/frontend/src/components/common/CompactPageHeader.test.tsx`
- Affected pages:
  - `/home/runner/work/solune/solune/solune/frontend/src/pages/ProjectsPage.tsx`
  - `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPage.tsx`
  - `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPipelinePage.tsx`
  - `/home/runner/work/solune/solune/solune/frontend/src/pages/ToolsPage.tsx`
  - `/home/runner/work/solune/solune/solune/frontend/src/pages/ChoresPage.tsx`
  - `/home/runner/work/solune/solune/solune/frontend/src/pages/HelpPage.tsx`
- Shared styles: `/home/runner/work/solune/solune/solune/frontend/src/index.css`

## Implementation Checklist

1. Confirm each affected page composes `CompactPageHeader` with the correct props.
2. Verify no page passes a `note` prop or expects a decorative aside.
3. Audit `/home/runner/work/solune/solune/solune/frontend/src/index.css` and remove only truly orphaned hero-specific selectors after confirming shared utility classes remain in use elsewhere.
4. Keep actions, page content, filters, and navigation unchanged below the header.

## Validation Commands

```bash
cd /home/runner/work/solune/solune/solune/frontend
npm run test
npm run lint
npm run type-check
```

## Optional Browser Verification

```bash
cd /home/runner/work/solune/solune/solune/frontend
npm run dev
```

Then manually verify:

1. Projects, Agents, Agents Pipeline, Tools, Chores, and Help show compact headers.
2. Desktop headers stay around the ~80–100px target range and reclaim vertical content space.
3. No decorative hero visuals or “Current Ritual” aside remain.
4. Stats appear as compact chips and are hidden behind a toggle on mobile.
5. Action buttons remain usable and existing flows still work.

## Completion Criteria

- Planning artifacts are in `/home/runner/work/solune/solune/specs/001-simplify-page-headers/`
- Shared header contract remains consistent across all six pages
- No unresolved clarifications remain in `plan.md`
