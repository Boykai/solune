# Implementation Plan: Simplify Page Headers for Focused UI

**Branch**: `001-simplify-page-headers` | **Date**: 2026-04-12 | **Spec**: `/home/runner/work/solune/solune/specs/001-simplify-page-headers/spec.md`  
**Input**: Feature specification from `/home/runner/work/solune/solune/specs/001-simplify-page-headers/spec.md`

## Summary

Replace the oversized catalog hero treatment on six Solune frontend pages with the existing compact `CompactPageHeader` pattern already present in `/home/runner/work/solune/solune/solune/frontend/src/components/common/CompactPageHeader.tsx`. The plan keeps the change frontend-only, preserves all existing page actions and data flows, documents safe CSS cleanup boundaries in `/home/runner/work/solune/solune/solune/frontend/src/index.css`, and relies on the established React/Vite/Tailwind/Vitest toolchain for regression coverage.

## Technical Context

**Language/Version**: TypeScript `~6.0.2` with React `19.2.x` JSX via Vite `8.0.x`  
**Primary Dependencies**: React 19, React Router 7, Vite 8, Tailwind CSS 4, TanStack React Query 5, Radix UI primitives, `clsx`, `tailwind-merge`  
**Storage**: N/A for this feature; header content comes from existing page/query state and no persistence model changes are required  
**Testing**: Vitest 4 + Testing Library + `jest-axe` for component/page coverage; ESLint 10; `tsc --noEmit`; Playwright available for optional browser verification  
**Target Platform**: Responsive browser-based frontend in `/home/runner/work/solune/solune/solune/frontend` for desktop and mobile web viewports  
**Project Type**: Web application, frontend-only change within a larger repository  
**Performance Goals**: Reduce header height from ~350–450px to ~80–100px on desktop, reclaim ~250–370px of visible content area, avoid horizontal overflow on mobile, and add no new runtime/network cost  
**Constraints**: No backend/API changes; preserve existing actions, navigation, filters, and content; remove decorative header visuals and `note`/“Current Ritual” usage; hide stats behind a mobile toggle by default; only delete CSS that is truly orphaned  
**Scale/Scope**: One shared header component contract, six affected page routes (Projects, Agents, Agents Pipeline, Tools, Chores, Help), page/component tests, and scoped stylesheet cleanup in `/home/runner/work/solune/solune/solune/frontend/src/index.css`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Gate Review

| Principle | Status | Evidence / Decision |
|-----------|--------|---------------------|
| I. Specification-First Development | PASS | `/home/runner/work/solune/solune/specs/001-simplify-page-headers/spec.md` already defines prioritized stories, independent tests, acceptance scenarios, requirements, and scope boundaries. |
| II. Template-Driven Workflow | PASS | This plan, plus `research.md`, `data-model.md`, `quickstart.md`, and `contracts/`, follows the required planning artifacts for `/speckit.plan`. |
| III. Agent-Orchestrated Execution | PASS | Planning used the setup script, repo evidence, and focused research to converge on a single shared-component rollout rather than ad hoc page-specific solutions. |
| IV. Test Optionality with Clarity | PASS | The constitution makes tests optional by default, but this spec explicitly requires regression confidence (`SC-004`, `SC-008`), so implementation must preserve/update Vitest/page coverage and pass lint/type-check validation. |
| V. Simplicity and DRY | PASS | The feature reuses one shared compact header component for all six pages, avoids new abstractions or backend work, and limits cleanup to dead hero-specific code. |

### Post-Design Re-check

| Check | Status | Notes |
|-------|--------|-------|
| All planning artifacts created before moving beyond design | PASS | `research.md`, `data-model.md`, `quickstart.md`, and `/contracts/compact-page-header-contract.yaml` are present under `/home/runner/work/solune/solune/specs/001-simplify-page-headers/`. |
| No unresolved clarifications remain | PASS | Technical context is resolved from repo evidence: the frontend stack, component/test files, affected pages, and shared CSS usage are all confirmed. |
| Complexity introduced without justification | PASS | No justified exceptions needed; the plan remains a straightforward shared-component migration and cleanup. |

## Project Structure

### Documentation (this feature)

```text
/home/runner/work/solune/solune/specs/001-simplify-page-headers/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    └── compact-page-header-contract.yaml
```

### Source Code (repository root)

```text
/home/runner/work/solune/solune/solune/frontend/
├── package.json
└── src/
    ├── components/
    │   └── common/
    │       ├── CompactPageHeader.tsx
    │       └── CompactPageHeader.test.tsx
    ├── pages/
    │   ├── ProjectsPage.tsx
    │   ├── AgentsPage.tsx
    │   ├── AgentsPipelinePage.tsx
    │   ├── ToolsPage.tsx
    │   ├── ChoresPage.tsx
    │   └── HelpPage.tsx
    ├── index.css
    └── test/
```

**Structure Decision**: Use the existing frontend web-app structure centered on `/home/runner/work/solune/solune/solune/frontend/src`. This feature touches a shared presentational component, six page containers, existing component/page tests, and one shared stylesheet; there is no need for backend, storage, or new package/module boundaries.

## Complexity Tracking

No constitution violations or extra complexity require justification for this planning phase.
