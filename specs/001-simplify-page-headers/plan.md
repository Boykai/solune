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

## Implementation Phases

### Phase 0 — Confirm baseline and shared contract

1. Verify the shared `CompactPageHeader` prop contract in `/home/runner/work/solune/solune/solune/frontend/src/components/common/CompactPageHeader.tsx` matches the spec (`eyebrow`, `title`, `description`, `badge`, `stats`, `actions`, `className`, and no `note` prop).
2. Confirm the existing component test coverage in `/home/runner/work/solune/solune/solune/frontend/src/components/common/CompactPageHeader.test.tsx` covers compact rendering, mobile stats toggle behavior, and clean omission of optional regions.
3. Audit the affected page files so each page’s current hero data can be mapped directly into the shared header props without changing page logic.

**Dependencies**: Feature spec, current component implementation, existing component tests.  
**Exit Criteria**: Shared header contract is validated and page-specific header inputs are known.

### Phase 1 — Finalize shared component behavior

1. Keep the compact header as the only shared page-header implementation for this rollout.
2. Ensure the component preserves the spec-required behavior:
   - compact desktop footprint (~80–100px target),
   - no decorative hero visuals,
   - single-line description with expand-on-hover behavior,
   - mobile stats hidden behind a toggle by default,
   - graceful omission of empty `badge`, `stats`, and `actions`.
3. Extend or adjust component tests only if a spec requirement is not already covered.

**Dependencies**: Phase 0 contract verification.  
**Exit Criteria**: Shared component behavior is fully aligned with `FR-001` through `FR-009`.

### Phase 2 — Migrate all six pages to the shared header

1. Replace page-specific hero usage in:
   - `/home/runner/work/solune/solune/solune/frontend/src/pages/ProjectsPage.tsx`
   - `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPage.tsx`
   - `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPipelinePage.tsx`
   - `/home/runner/work/solune/solune/solune/frontend/src/pages/ToolsPage.tsx`
   - `/home/runner/work/solune/solune/solune/frontend/src/pages/ChoresPage.tsx`
   - `/home/runner/work/solune/solune/solune/frontend/src/pages/HelpPage.tsx`
2. Map each page’s existing eyebrow/title/description/badge/stats/actions into `CompactPageHeader` props.
3. Remove any leftover `note`/“Current Ritual” wiring while preserving existing page actions, data fetching, filtering, and navigation behavior.
4. Update or keep page-level tests/mocks in place where pages explicitly reference the shared header component.

**Dependencies**: Phase 1 shared component behavior is stable.  
**Exit Criteria**: All six pages use the same header contract and preserve existing interactive behavior (`FR-012`).

### Phase 3 — Clean up dead hero code and scoped styles

1. Delete `CelestialCatalogHero` implementation and any dedicated tests only after all page migrations are complete.
2. Remove hero-specific selectors from `/home/runner/work/solune/solune/solune/frontend/src/index.css`.
3. Re-run code search before deleting shared-looking CSS classes to confirm `.moonwell`, `.hanging-stars`, and reusable `celestial-*` utilities are not orphaned by this feature.

**Dependencies**: Phase 2 complete so cleanup does not break active pages.  
**Exit Criteria**: No remaining `CelestialCatalogHero` references and no unsafe shared-style deletions.

### Phase 4 — Verification and smoke testing

1. Run frontend validation from `/home/runner/work/solune/solune/solune/frontend`:
   - `npm run test`
   - `npm run lint`
   - `npm run type-check`
2. Perform browser/manual verification across the six pages on desktop and a mobile viewport:
   - compact header visible,
   - stats chips inline on larger screens,
   - stats toggle on mobile,
   - actions still usable,
   - no decorative hero remnants.
3. Capture any regressions in component/page tests before implementation is considered complete.

**Dependencies**: Phases 1–3 complete.  
**Exit Criteria**: `SC-004` through `SC-008` satisfied with no regressions.

## Dependency Order

```text
Phase 0: Baseline + contract confirmation
  -> Phase 1: Shared component alignment
      -> Phase 2: Six-page migration
          -> Phase 3: Dead code / CSS cleanup
              -> Phase 4: Validation + smoke test
```

## Complexity Tracking

No constitution violations or extra complexity require justification for this planning phase.
