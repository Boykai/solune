# Tasks: Simplify Page Headers for Focused UI

**Input**: Design documents from `/specs/001-simplify-page-headers/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/compact-page-header-api.yaml, quickstart.md

**Tests**: Additional integration or e2e test tasks are not included since they were not explicitly requested in the feature specification. However, T002 creates `CompactPageHeader.test.tsx` to maintain coverage parity with the deleted `CelestialCatalogHero.test.tsx`.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. User stories US1 (compact header), US2 (stat chips), US5 (no decorations), and US6 (consistency) are addressed together by the component creation and page migration phases since they are inherently coupled — the compact header component satisfies all four simultaneously. US3 (description subtitle) and US4 (mobile stats toggle) are specific component behaviors implemented in Phase 2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/frontend/src/` prefix for all frontend files

---

## Phase 1: Setup

**Purpose**: No new project initialization needed — this is an in-place migration within an existing frontend application. Setup phase covers the new component creation that all subsequent phases depend on.

- [x] T001 Create `CompactPageHeader.tsx` component with props interface (`CompactPageHeaderStat`, `CompactPageHeaderProps`), single-row flexbox layout (eyebrow + title left, badge center, actions right), and `<header>` semantic element in `solune/frontend/src/components/common/CompactPageHeader.tsx`
- [x] T002 Create `CompactPageHeader.test.tsx` with render tests for all props, missing optional props, accessibility checks, and className forwarding in `solune/frontend/src/components/common/CompactPageHeader.test.tsx`

**Checkpoint**: CompactPageHeader component created and passes its own tests. Ready for page migration.

---

## Phase 2: Foundational — Component Behaviors (Blocking Prerequisites)

**Purpose**: Implement the specific interactive behaviors of CompactPageHeader that user stories US3 and US4 require. These MUST be complete before page migration so all pages get the full feature set.

**⚠️ CRITICAL**: These behaviors must be built into CompactPageHeader before any page starts using it.

- [x] T003 [US3] Implement description as single-line subtitle with `line-clamp-1` and `group-hover:line-clamp-none` expand-on-hover behavior in `solune/frontend/src/components/common/CompactPageHeader.tsx`
- [x] T004 [US4] Implement mobile stats toggle — hide stats behind a toggle button on viewports < 640px using `useState` hook and Tailwind responsive classes in `solune/frontend/src/components/common/CompactPageHeader.tsx`
- [x] T005 [US2] Implement stats as inline pill/chip elements with small text label and value, flex-wrap layout, and graceful omission when no stats provided in `solune/frontend/src/components/common/CompactPageHeader.tsx`

**Checkpoint**: CompactPageHeader fully implements all interactive behaviors (description truncation, mobile stats toggle, chip-style stats). Ready for page migration.

---

## Phase 3: User Story 1 — Compact Page Header Reclaims Vertical Space (Priority: P1) 🎯 MVP

**Goal**: Replace the large CelestialCatalogHero (~350–450px) with the compact CompactPageHeader (~80–100px) on all 6 pages, reclaiming significant vertical space. This phase also satisfies US2 (stat chips), US5 (no decorations), and US6 (consistency) since the new component inherently provides all of these.

**Independent Test**: Navigate to each of the six affected pages and verify that the header occupies approximately 80–100px of vertical space, all essential information (eyebrow, title, badge, actions) remains visible, and the primary content area starts higher on the page than before.

### Implementation for User Stories 1, 2, 5, 6 (Page Migration — all parallel)

- [x] T006 [P] [US1] Swap `CelestialCatalogHero` → `CompactPageHeader` import and JSX in `solune/frontend/src/pages/ProjectsPage.tsx` — remove `note` prop, remove `className="projects-catalog-hero"`
- [x] T007 [P] [US1] Swap `CelestialCatalogHero` → `CompactPageHeader` import and JSX in `solune/frontend/src/pages/AgentsPage.tsx` — remove `note` prop
- [x] T008 [P] [US1] Swap `CelestialCatalogHero` → `CompactPageHeader` import and JSX in `solune/frontend/src/pages/AgentsPipelinePage.tsx` — remove `note` prop, remove `className="projects-catalog-hero"`
- [x] T009 [P] [US1] Swap `CelestialCatalogHero` → `CompactPageHeader` import and JSX in `solune/frontend/src/pages/ToolsPage.tsx` — remove `note` prop
- [x] T010 [P] [US1] Swap `CelestialCatalogHero` → `CompactPageHeader` import and JSX in `solune/frontend/src/pages/ChoresPage.tsx` — remove `note` prop
- [x] T011 [P] [US1] Swap `CelestialCatalogHero` → `CompactPageHeader` import and JSX in `solune/frontend/src/pages/HelpPage.tsx` — update import (no `note` prop was used)

**Checkpoint**: All 6 pages render with the compact header. No TypeScript errors. No references to CelestialCatalogHero in page files. User Stories 1, 2, 5, and 6 are all satisfied.

---

## Phase 4: User Story 3 — Description as Single-Line Subtitle (Priority: P2)

**Goal**: Verify that the description renders as a single-line subtitle across all pages, truncating with ellipsis when long, and expanding on hover to show the full text.

**Independent Test**: Navigate to a page with a description, verify the description is visible as a single truncated line, hover over it, and verify the full text becomes visible.

### Implementation for User Story 3

- [x] T012 [US3] Verify description rendering on all 6 pages — confirm `line-clamp-1` truncation and `group-hover:line-clamp-none` expand behavior works with each page's description text (integration verification, no code changes expected)

**Checkpoint**: Description subtitle behavior confirmed on all pages. US3 satisfied.

---

## Phase 5: User Story 4 — Stats Toggle on Mobile Viewports (Priority: P2)

**Goal**: Verify that stats are hidden by default on mobile viewports and accessible via a toggle control across all stats-bearing pages.

**Independent Test**: View any stats-bearing page on a mobile viewport, verify stats are hidden by default, activate the toggle, and verify stats become visible.

### Implementation for User Story 4

- [x] T013 [US4] Verify mobile stats toggle on all stats-bearing pages (Projects, Agents, AgentsPipeline, Tools, Chores) at < 640px viewport — confirm stats hidden by default, toggle reveals them, and Help page (no stats) shows no toggle (integration verification, no code changes expected)

**Checkpoint**: Mobile stats toggle behavior confirmed on all applicable pages. US4 satisfied.

---

## Phase 6: Clean Up Dead Code

**Purpose**: Remove the old CelestialCatalogHero component and its exclusively-used CSS now that all pages are migrated.

- [x] T014 [P] Delete `solune/frontend/src/components/common/CelestialCatalogHero.tsx` (old hero component, ~119 lines)
- [x] T015 [P] Delete `solune/frontend/src/components/common/CelestialCatalogHero.test.tsx` (old hero tests, ~110 lines)
- [x] T016 Remove orphaned `.dark .projects-catalog-hero .catalog-hero-*` CSS rules (lines ~432–489) from `solune/frontend/src/index.css` — retain `.moonwell`, `.hanging-stars`, and all `.celestial-*` animation classes

**Checkpoint**: No references to `CelestialCatalogHero` remain in the codebase. No orphaned CSS. Net code reduction: ~229 lines deleted.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final verification across all user stories and cleanup

- [x] T017 Run `npx vitest run` in `solune/frontend/` — all frontend tests pass with zero failures
- [x] T018 [P] Run `npx eslint .` in `solune/frontend/` — no lint errors
- [x] T019 [P] Run `npx tsc --noEmit` in `solune/frontend/` — no type errors
- [x] T020 Visual smoke test on all 6 pages in desktop viewport — compact headers render correctly with all props
- [x] T021 Visual smoke test on all 6 pages in mobile viewport (375px width) — headers remain compact, stats hidden behind toggle
- [x] T022 Verify no regressions in sidebar celestial animations, LoginPage decorations, CelestialLoader, NotFoundPage, and ErrorBoundary decorations

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on T001 (component file exists) — builds behaviors into CompactPageHeader
- **User Story 1/2/5/6 (Phase 3)**: Depends on Phase 2 completion — all page migrations are parallel
- **User Story 3 (Phase 4)**: Depends on Phase 3 — verification of description behavior on live pages (can run in parallel with Phase 5)
- **User Story 4 (Phase 5)**: Depends on Phase 3 — verification of mobile toggle on live pages (can run in parallel with Phase 4)
- **Clean Up (Phase 6)**: Depends on Phases 3, 4, 5 — all pages migrated before deleting old component
- **Polish (Phase 7)**: Depends on Phase 6 — full verification after all changes complete

### User Story Dependencies

- **User Story 1 (P1)**: Core story — addressed by Phase 1 + 2 + 3 (component creation + page migration)
- **User Story 2 (P1)**: Inherently satisfied by CompactPageHeader's chip-style stats (Phase 2 T005 + Phase 3)
- **User Story 3 (P2)**: Behavior built in Phase 2 (T003), verified in Phase 4 (T012)
- **User Story 4 (P2)**: Behavior built in Phase 2 (T004), verified in Phase 5 (T013)
- **User Story 5 (P3)**: Inherently satisfied — CompactPageHeader has no decorative elements
- **User Story 6 (P1)**: Inherently satisfied — all 6 pages use the same CompactPageHeader component

### Within Each Phase

- Component file (T001) must exist before behaviors (T003–T005) are added
- Component tests (T002) should be written alongside or immediately after T001
- All behaviors (Phase 2) must be complete before page migration (Phase 3)
- All page migrations (Phase 3) must be complete before dead code cleanup (Phase 6)
- Dead code cleanup (Phase 6) must be complete before final verification (Phase 7)

### Parallel Opportunities

- All Phase 3 page migration tasks (T006–T011) can run in parallel — different files, no dependencies
- Phase 4 (T012) and Phase 5 (T013) can run in parallel — independent verifications
- Phase 6 deletions (T014, T015) can run in parallel — different files
- Phase 7 lint (T018) and type check (T019) can run in parallel

---

## Parallel Example: Phase 3 (Page Migration)

```bash
# Launch all 6 page migrations together (all touch different files):
Task T006: "Swap hero → CompactPageHeader in solune/frontend/src/pages/ProjectsPage.tsx"
Task T007: "Swap hero → CompactPageHeader in solune/frontend/src/pages/AgentsPage.tsx"
Task T008: "Swap hero → CompactPageHeader in solune/frontend/src/pages/AgentsPipelinePage.tsx"
Task T009: "Swap hero → CompactPageHeader in solune/frontend/src/pages/ToolsPage.tsx"
Task T010: "Swap hero → CompactPageHeader in solune/frontend/src/pages/ChoresPage.tsx"
Task T011: "Swap hero → CompactPageHeader in solune/frontend/src/pages/HelpPage.tsx"
```

---

## Implementation Strategy

### MVP First (Phase 1 + 2 + 3 Only)

1. Complete Phase 1: Create CompactPageHeader component + tests
2. Complete Phase 2: Add description subtitle, mobile stats toggle, chip-style stats
3. Complete Phase 3: Migrate all 6 pages (big-bang rollout)
4. **STOP and VALIDATE**: Run `npx vitest run`, `npx tsc --noEmit`, visual smoke test
5. At this point, User Stories 1, 2, 5, and 6 are fully functional

### Incremental Delivery

1. Phase 1 + 2 → Component ready with all behaviors
2. Phase 3 → All pages migrated → Run tests → **MVP complete** (US1, US2, US5, US6)
3. Phase 4 → Verify US3 (description subtitle) on live pages
4. Phase 5 → Verify US4 (mobile stats toggle) on live pages
5. Phase 6 → Delete old component + orphaned CSS → Clean codebase
6. Phase 7 → Full verification suite → **Feature complete**

### Single Developer Strategy

Since this is a frontend-only change with no backend dependencies, a single developer can complete all phases sequentially:

1. Create component (T001–T002) → ~30 min
2. Add behaviors (T003–T005) → ~20 min
3. Migrate all 6 pages (T006–T011) → ~30 min (boilerplate swaps)
4. Verify behaviors (T012–T013) → ~15 min
5. Delete dead code (T014–T016) → ~10 min
6. Full verification (T017–T022) → ~20 min

**Estimated total**: ~2–3 hours for complete feature delivery

---

## Notes

- [P] tasks = different files, no dependencies between them
- [Story] label maps task to specific user story for traceability
- US1/US2/US5/US6 are addressed together because CompactPageHeader inherently satisfies all four — creating separate phases for each would be artificial
- US3 and US4 have dedicated verification phases because they involve specific interactive behaviors that need explicit validation
- The `note` prop is the only prop dropped during migration; all other props are unchanged
- CSS cleanup is conservative: only `.projects-catalog-hero`-scoped rules are removed; `.moonwell` (30+ components), `.hanging-stars` (LoginPage), and all `.celestial-*` animations (Sidebar, AppLayout, etc.) are retained
- No new dependencies are added; component uses existing React, Tailwind CSS, and `cn()` utility
