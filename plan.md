# Implementation Plan: Agents Page UI Improvements

**Branch**: `003-agents-page-ui` | **Date**: 2026-04-16 | **Spec**: `/specs/003-agents-page-ui/spec.md`
**Input**: Feature specification from `/specs/003-agents-page-ui/spec.md`

## Summary

Apply a frontend-only UI refinement to the Agents experience: fix tall Add Agent modal viewport alignment, remove the Featured Agents spotlight section and its dead code, reorder Catalog Controls ahead of the Awesome Catalog, and add independent collapsible toggles for Pending Changes, Catalog Controls, and Awesome Catalog while preserving the current default-expanded UX.

## Technical Context

**Language/Version**: TypeScript 6.x, React 19.x, Vite 8.x  
**Primary Dependencies**: React, TanStack Query, Tailwind CSS utility classes, Vitest, React Testing Library  
**Storage**: N/A for this feature (no new persisted client or server state)  
**Testing**: `npm run type-check`, `npm run build`, `npm run test -- src/components/agents/__tests__/AgentsPanel.test.tsx src/components/agents/__tests__/AddAgentModal.test.tsx`  
**Target Platform**: Solune web frontend (`/solune/frontend`) in modern desktop browsers  
**Project Type**: Web application (frontend + backend monorepo, frontend-only change)  
**Performance Goals**: Preserve current render and query behavior; add only local boolean UI state and conditional rendering with no new network traffic  
**Constraints**: Keep Catalog Controls inside the existing loaded/non-error/has-agents guard, keep Awesome Catalog unconditional, default all new collapsible sections to expanded, use inline local state instead of a new abstraction, remove all Featured Agents-only code  
**Scale/Scope**: 2 production components (`AgentsPanel.tsx`, `AddAgentModal.tsx`), 2 focused frontend test files, icon export verification in `src/lib/icons.ts`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Gate | Pre-Research | Post-Design |
|---|---|---|
| I. Specification-First Development | PASS — plan is derived directly from the approved `spec.md` scenarios, requirements, and scope boundaries. | PASS — all artifacts map back to FR-001 through FR-011 and the three user stories. |
| II. Template-Driven Workflow | PASS — `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, and `contracts/` follow Speckit artifact expectations. | PASS — all required Phase 0/1 artifacts are generated in the feature directory. |
| III. Agent-Orchestrated Execution | PASS — this plan defines a clean handoff from planning to task generation and implementation. | PASS — research/design outputs now provide explicit inputs for `/speckit.tasks` and `/speckit.implement`. |
| IV. Test Optionality with Clarity | PASS — tests are required here because the specification explicitly calls for build/type-check and existing agent regression checks. | PASS — verification steps are scoped to existing frontend commands and focused tests only. |
| V. Simplicity and DRY | PASS — implementation uses one modal class change, removes dead UI code, and adds three local toggles instead of a new component abstraction. | PASS — no unjustified abstraction or persistence layer is introduced. |

**Gate Result**: PASS — no constitution violations identified; `Complexity Tracking` remains empty.

## Project Structure

### Documentation (this feature)

```text
specs/003-agents-page-ui/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── agents-page-ui.openapi.yaml
└── tasks.md              # Created later by /speckit.tasks
```

### Source Code (repository root)

```text
solune/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── agents/
│   │   │   │   ├── AddAgentModal.tsx
│   │   │   │   └── AgentsPanel.tsx
│   │   │   └── settings/
│   │   │       └── SettingsSection.tsx
│   │   ├── lib/
│   │   │   └── icons.ts
│   │   └── components/agents/__tests__/
│   │       ├── AddAgentModal.test.tsx
│   │       └── AgentsPanel.test.tsx
│   └── package.json
└── docs/
    └── agent-pipeline.md
```

**Structure Decision**: Keep the change entirely inside the existing frontend agents surface. Reuse the established collapsible-header interaction pattern from `SettingsSection.tsx`, validate icon availability through `src/lib/icons.ts`, and confine regression coverage to the existing AgentsPanel/AddAgentModal tests.

## Phase 0: Research Outline

1. Confirm the modal layout bug is solved by changing the overlay alignment from `items-center` to `items-start` while leaving the dialog `my-auto` centering in place.
2. Confirm `ChevronDown` already exists in the shared icon export and identify an existing collapsible-header interaction pattern to mirror.
3. Confirm the Featured Agents section is isolated enough to remove completely without changing agent loading, filtering, or catalog data contracts.
4. Confirm the real verification commands and existing focused tests for the agents UI.

## Phase 1: Design Plan

1. Define the UI state model for section collapse/expand behavior and modal viewport behavior.
2. Record a no-API-change contract artifact so downstream phases do not expect backend or schema work.
3. Write a quickstart that covers focused automated checks plus manual browser validation for modal alignment, section order, and collapse behavior.
4. Update agent context after the plan is finalized so later agents inherit the current frontend/testing stack.

## Phase 2: Implementation Planning Preview

1. Update `AddAgentModal.tsx` overlay alignment class and add/adjust focused coverage for modal shell expectations.
2. Remove Featured Agents markup, memoized spotlight data, and now-unused imports/derived values from `AgentsPanel.tsx`.
3. Reorder the loaded-state sections so Catalog Controls renders before Awesome Catalog without changing their respective guards.
4. Add `pendingCollapsed`, `catalogCollapsed`, and `awesomeCatalogCollapsed` state plus clickable chevrons and conditional section bodies.
5. Extend `AgentsPanel.test.tsx` to verify section order, section removal, and independent collapse toggles.
6. Run focused tests, `npm run type-check`, and `npm run build`, then perform a manual UI check with a screenshot.

## Complexity Tracking

No constitution exceptions or additional complexity are required for this feature.
