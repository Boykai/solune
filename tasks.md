# Tasks: Simplify Page Headers for Focused UI

**Input**: Design documents from feature branch `copilot/speckitplan-create-compact-header`
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, research.md ✅, quickstart.md ✅, contracts/ ✅

**Tests**: Included — plan.md specifies creating `CompactPageHeader.test.tsx` to replace deleted `CelestialCatalogHero.test.tsx`.

**Organization**: Tasks are grouped by user story. US1–US4 are all implemented by the same `CompactPageHeader` component and share a single phase because the component cannot be decomposed per story. US6 (page migration) and US5 (dead code removal) each have their own phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/frontend/src/` for all frontend source files
- **Components**: `solune/frontend/src/components/common/`
- **Pages**: `solune/frontend/src/pages/`
- **Styles**: `solune/frontend/src/index.css`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new project initialization needed — this feature modifies an existing React/TypeScript frontend application. All tooling (Vitest, ESLint, TypeScript, Tailwind CSS 4) is already configured.

*No tasks in this phase.*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the `CompactPageHeader` component and its tests. This component is the single blocking prerequisite for ALL user stories — no page migration can begin until this component exists and passes its tests.

**⚠️ CRITICAL**: No user story work (page migrations, dead code removal) can begin until this phase is complete.

- [x] T001 Create `CompactPageHeader` component implementing compact single-row layout (~80–100px height) with eyebrow, title, description (line-clamp-1 with group-hover expand), badge (optional pill), stats (inline chips, hidden behind toggle on mobile < 640px), actions zone, and className forwarding using `cn()` utility in `solune/frontend/src/components/common/CompactPageHeader.tsx`
- [x] T002 [P] Create unit tests for `CompactPageHeader` covering: render with all props, render with minimal props (eyebrow + title + description only), badge omitted when undefined, stats omitted when empty array, stats chips render label and value, actions slot renders children, className forwarded to root `<header>` element, description has `line-clamp-1` class, accessibility (semantic `<header>` element, `<h2>` heading) in `solune/frontend/src/components/common/CompactPageHeader.test.tsx`

**Checkpoint**: `CompactPageHeader` renders correctly with all prop combinations. Tests pass with `npm test -- --reporter=verbose CompactPageHeader`. Page migration can now begin.

---

## Phase 3: US1 + US2 + US3 + US4 + US6 — Compact Header with Stats Chips, Subtitle, Mobile Toggle, and Consistent Experience (Priority: P1/P2)  🎯 MVP

**Goal**: Replace `CelestialCatalogHero` with `CompactPageHeader` on all six affected pages, delivering: compact height (US1), stats as inline chips (US2), single-line description with hover expand (US3), mobile stats toggle (US4), and consistent layout across pages (US6). All six page migrations can run in parallel since they modify different files.

**Independent Test**: Navigate to each of the six pages and verify: header height is ~80–100px, eyebrow/title/badge/actions are visible, stats appear as inline chips, description is a single truncated line that expands on hover, and on mobile viewport stats are hidden behind a toggle.

**User Stories Delivered**:

- **US1** (P1): Compact Page Header Reclaims Vertical Space — header height reduced from ~350–450px to ~80–100px
- **US2** (P1): Stats Displayed as Compact Inline Chips — stats rendered as pill/chip elements, not moonwell cards
- **US3** (P2): Description as Single-Line Subtitle — `line-clamp-1` with `group-hover:line-clamp-none`
- **US4** (P2): Stats Toggle on Mobile Viewports — stats hidden by default on `< 640px`, accessible via toggle
- **US6** (P1): Consistent Header Experience Across All Six Pages — same `CompactPageHeader` component on all pages

### Implementation

- [x] T003 [P] [US1] Swap `CelestialCatalogHero` → `CompactPageHeader` import, replace `<CelestialCatalogHero>` JSX with `<CompactPageHeader>`, remove `note` prop, remove `className="projects-catalog-hero"` in `solune/frontend/src/pages/ProjectsPage.tsx`
- [x] T004 [P] [US1] Swap `CelestialCatalogHero` → `CompactPageHeader` import, replace `<CelestialCatalogHero>` JSX with `<CompactPageHeader>`, remove `note` prop in `solune/frontend/src/pages/AgentsPage.tsx`
- [x] T005 [P] [US1] Swap `CelestialCatalogHero` → `CompactPageHeader` import, replace `<CelestialCatalogHero>` JSX with `<CompactPageHeader>`, remove `note` prop, remove `className="projects-catalog-hero"` in `solune/frontend/src/pages/AgentsPipelinePage.tsx`
- [x] T006 [P] [US1] Swap `CelestialCatalogHero` → `CompactPageHeader` import, replace `<CelestialCatalogHero>` JSX with `<CompactPageHeader>`, remove `note` prop in `solune/frontend/src/pages/ToolsPage.tsx`
- [x] T007 [P] [US1] Swap `CelestialCatalogHero` → `CompactPageHeader` import, replace `<CelestialCatalogHero>` JSX with `<CompactPageHeader>`, remove `note` prop in `solune/frontend/src/pages/ChoresPage.tsx`
- [x] T008 [P] [US1] Swap `CelestialCatalogHero` → `CompactPageHeader` import, replace `<CelestialCatalogHero>` JSX with `<CompactPageHeader>` (no `note` prop used) in `solune/frontend/src/pages/HelpPage.tsx`

**Checkpoint**: All six pages render with `CompactPageHeader`. No TypeScript errors. Existing page tests still pass. `npm test -- --reporter=verbose` shows no regressions.

---

## Phase 4: US5 — Decorative Elements Removed & Dead Code Cleanup (Priority: P3)

**Goal**: Delete the now-unused `CelestialCatalogHero` component, its tests, and remove orphaned CSS rules that were exclusively scoped to the hero component. Celestial theme decorations are preserved elsewhere (sidebar, login, global chrome).

**Independent Test**: Verify no references to `CelestialCatalogHero` remain in the codebase. Verify `index.css` no longer contains `.projects-catalog-hero .catalog-hero-*` rules. Verify retained CSS classes (`.moonwell`, `.hanging-stars`, `.celestial-*`) still exist and are used by other components. Build and lint pass cleanly.

### Implementation

- [x] T009 [P] [US5] Delete the old hero component file `solune/frontend/src/components/common/CelestialCatalogHero.tsx`
- [x] T010 [P] [US5] Delete the old hero test file `solune/frontend/src/components/common/CelestialCatalogHero.test.tsx`
- [x] T011 [US5] Remove orphaned `.dark .projects-catalog-hero .catalog-hero-*` CSS rules (lines ~432–489) from `solune/frontend/src/index.css` — retain `.moonwell` (30+ components), `.hanging-stars` (LoginPage), and all `.celestial-*` animation classes (Sidebar, AppLayout, CelestialLoader, etc.)

**Checkpoint**: Zero references to `CelestialCatalogHero` in codebase. No orphaned CSS. `npm test`, `npx eslint .`, and `npx tsc --noEmit` all pass.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final verification across all dimensions — tests, lint, types, and visual correctness.

- [x] T012 Run full frontend test suite to verify zero regressions: `cd solune/frontend && npx vitest run`
- [x] T013 [P] Run ESLint to verify no lint errors: `cd solune/frontend && npx eslint .`
- [x] T014 [P] Run TypeScript type check to verify no type errors: `cd solune/frontend && npx tsc --noEmit`
- [ ] T015 Visual smoke test on all 6 pages (`/projects`, `/agents`, `/agents/pipeline`, `/tools`, `/chores`, `/help`) — verify compact header renders correctly on desktop and mobile viewport

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No tasks — existing project
- **Foundational (Phase 2)**: No dependencies — can start immediately. **BLOCKS all page migrations.**
- **US1/US2/US3/US4/US6 — Page Migrations (Phase 3)**: Depends on Phase 2 completion (CompactPageHeader must exist)
- **US5 — Dead Code Removal (Phase 4)**: Depends on Phase 3 completion (all pages must be migrated before deleting the old component)
- **Polish (Phase 5)**: Depends on Phase 4 completion (all code changes must be complete before final verification)

### User Story Dependencies

- **US1** (P1): Compact header reclaims vertical space → Delivered by T001 (component) + T003–T008 (page migrations)
- **US2** (P1): Stats as inline chips → Delivered by T001 (component includes chip rendering)
- **US3** (P2): Description as subtitle → Delivered by T001 (component includes line-clamp-1)
- **US4** (P2): Mobile stats toggle → Delivered by T001 (component includes mobile toggle)
- **US5** (P3): Remove decorations → Delivered by T009–T011 (delete hero + CSS cleanup); depends on all pages being migrated first
- **US6** (P1): Consistent across pages → Delivered by T003–T008 (all pages use same CompactPageHeader)

### Within Each Phase

- T001 (component) must complete before T003–T008 (page migrations)
- T002 (tests) can run in parallel with T001 but should be validated after T001
- T003–T008 (page migrations) are all parallel — different files, no dependencies
- T009–T010 (file deletions) are parallel — different files
- T011 (CSS cleanup) can run in parallel with T009–T010
- T012–T014 (verification) run after all code changes are complete

### Parallel Opportunities

**Within Phase 2** (Foundational):

- T001 and T002 can be authored in parallel (different files)

**Within Phase 3** (Page Migrations — all 6 are parallel):

- T003 (`ProjectsPage.tsx`) ‖ T004 (`AgentsPage.tsx`) ‖ T005 (`AgentsPipelinePage.tsx`) ‖ T006 (`ToolsPage.tsx`) ‖ T007 (`ChoresPage.tsx`) ‖ T008 (`HelpPage.tsx`)

**Within Phase 4** (Dead Code Removal):

- T009 ‖ T010 ‖ T011 (all different files)

**Within Phase 5** (Verification):

- T013 (`eslint`) ‖ T014 (`tsc --noEmit`)

---

## Parallel Example: Phase 3 — Page Migrations

```bash
# All 6 page migration tasks can execute simultaneously (different files, no dependencies):
Task T003: "Swap hero → compact header in solune/frontend/src/pages/ProjectsPage.tsx"
Task T004: "Swap hero → compact header in solune/frontend/src/pages/AgentsPage.tsx"
Task T005: "Swap hero → compact header in solune/frontend/src/pages/AgentsPipelinePage.tsx"
Task T006: "Swap hero → compact header in solune/frontend/src/pages/ToolsPage.tsx"
Task T007: "Swap hero → compact header in solune/frontend/src/pages/ChoresPage.tsx"
Task T008: "Swap hero → compact header in solune/frontend/src/pages/HelpPage.tsx"
```

---

## Implementation Strategy

### MVP First (Phase 2 + Phase 3 Only)

1. Complete Phase 2: Create `CompactPageHeader` component + tests
2. Complete Phase 3: Replace hero in all 6 pages
3. **STOP and VALIDATE**: All pages render with compact header, all tests pass
4. Deploy/demo if ready — users already see the full benefit

### Incremental Delivery

1. Complete Phase 2 → Component ready, tested
2. Complete Phase 3 → All 6 pages migrated → Deploy/Demo (**MVP!** — delivers US1, US2, US3, US4, US6)
3. Complete Phase 4 → Dead code removed → Deploy/Demo (delivers US5, clean codebase)
4. Complete Phase 5 → Full verification → Final deployment

### Parallel Team Strategy

With multiple developers:

1. **Developer A**: T001 (CompactPageHeader component)
2. **Developer B**: T002 (CompactPageHeader tests) — in parallel with A
3. Once T001 is done, all developers can take page migration tasks:
   - Developer A: T003 (ProjectsPage) + T006 (ToolsPage)
   - Developer B: T004 (AgentsPage) + T007 (ChoresPage)
   - Developer C: T005 (AgentsPipelinePage) + T008 (HelpPage)
4. Once all pages migrated: T009–T011 (cleanup) — any developer
5. Final: T012–T015 (verification) — one developer runs all checks

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tasks** | 15 |
| **Phase 2 (Foundational)** | 2 tasks (component + tests) |
| **Phase 3 (Page Migrations)** | 6 tasks (all parallel) |
| **Phase 4 (Dead Code Removal)** | 3 tasks (all parallel) |
| **Phase 5 (Verification)** | 4 tasks |
| **Tasks per user story** | US1: 7 (T001, T003–T008), US2: 1 (T001), US3: 1 (T001), US4: 1 (T001), US5: 3 (T009–T011), US6: 6 (T003–T008) |
| **Parallel opportunities** | 6 page migrations in parallel; 3 cleanup tasks in parallel; 2 verification tasks in parallel |
| **Suggested MVP scope** | Phase 2 + Phase 3 (8 tasks — component creation + all 6 page migrations) |
| **Files created** | 2 (`CompactPageHeader.tsx`, `CompactPageHeader.test.tsx`) |
| **Files modified** | 7 (6 page files + `index.css`) |
| **Files deleted** | 2 (`CelestialCatalogHero.tsx`, `CelestialCatalogHero.test.tsx`) |
| **Net code change** | ~119 lines deleted, ~50 lines added (net reduction) |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- US1–US4 are all properties of the same `CompactPageHeader` component and cannot be decomposed into separate implementation phases — they share task T001
- US6 (consistency) is achieved by migrating all 6 pages with the same component — tasks T003–T008
- US5 (remove decorations) is achieved by deleting the old hero component after all pages are migrated — tasks T009–T011
- **DO NOT remove** `.moonwell`, `.hanging-stars`, or `.celestial-*` CSS classes — they are used by 30+ other components (see research.md R1 for full usage analysis)
- **DO remove** `.dark .projects-catalog-hero .catalog-hero-*` CSS rules — exclusively scoped to deleted hero component
- Commit after each task or logical group
- Stop at Phase 3 checkpoint to validate MVP independently
