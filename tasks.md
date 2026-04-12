# Tasks: Simplify Page Headers for Focused UI

**Feature**: `001-simplify-page-headers` | **Branch**: `001-simplify-page-headers`
**Input**: Design documents from `specs/001-simplify-page-headers/`
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, research.md ✅, quickstart.md ✅, contracts/compact-page-header-contract.yaml ✅

**Tests**: Included — spec.md SC-004 and SC-008 require regression-free test, lint, and type-check passes. Regression-validation test tasks are included in each user story phase and in the final polish phase.

**Organization**: Tasks are grouped by user story in priority order from spec.md (P1 → P2 → P3). Each phase is independently testable. Setup/foundational/polish phases carry no story label; user story phases carry [US#] labels.

## Format: `- [ ] T### [P?] [US#?] Description with file path`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[US#]**: User story this task belongs to — required on all user story phase tasks
- **No [US#]**: Setup, Foundational, and Polish phases only
- Include exact absolute or repo-root-resolvable file paths in every task description

## Path Conventions

- **Frontend root**: `solune/frontend`
- **Component**: `solune/frontend/src/components/common/CompactPageHeader.tsx`
- **Component tests**: `solune/frontend/src/components/common/CompactPageHeader.test.tsx`
- **Pages**: `solune/frontend/src/pages/{Page}Page.tsx`
- **Global stylesheet**: `solune/frontend/src/index.css`
- **Validation**: `cd solune/frontend && npm run {test|lint|type-check}`

---

## Phase 1: Setup (Baseline Audit)

**Purpose**: Inventory the existing component contract, current hero usage on each page, and capture the pre-migration test baseline. No code changes are made in this phase; it provides the ground truth that makes all subsequent phases specific and safe.

- [ ] T001 Audit `solune/frontend/src/components/common/CompactPageHeader.tsx` against `specs/001-simplify-page-headers/contracts/compact-page-header-contract.yaml` — confirm props (eyebrow, title, description, badge, stats, actions, className), no `note` prop, stat chip type (`CompactPageHeaderStat`), and mobile toggle presence
- [ ] T002 [P] Audit all six page files for current `CelestialCatalogHero` usage so T008–T013 have exact prop mappings for `solune/frontend/src/pages/ProjectsPage.tsx`, `solune/frontend/src/pages/AgentsPage.tsx`, `solune/frontend/src/pages/AgentsPipelinePage.tsx`, `solune/frontend/src/pages/ToolsPage.tsx`, `solune/frontend/src/pages/ChoresPage.tsx`, and `solune/frontend/src/pages/HelpPage.tsx`
- [ ] T003 [P] Locate `CelestialCatalogHero` source and test files — search `solune/frontend/src/components/` to confirm exact deletion paths before Phase 8
- [ ] T004 Run baseline test suite to capture pre-migration green state: `cd solune/frontend && npm run test`

**Checkpoint**: Audit complete — component contract confirmed, hero prop shapes per page documented, CelestialCatalogHero file paths noted, baseline tests green.

---

## Phase 2: Foundational (Component Implementation and Testing)

**Purpose**: Ensure `CompactPageHeader.tsx` fully satisfies FR-001 through FR-009 and has test coverage for all spec-required behaviors. This is the single blocking prerequisite for all user story phases.

**⚠️ CRITICAL**: No user story work (page migrations, dead code removal) can begin until this phase is complete and its tests pass.

- [ ] T005 Update `solune/frontend/src/components/common/CompactPageHeader.tsx` to establish the shared compact-header foundation: compact desktop layout (~80–100px), no decorative hero elements, badge/actions collapse cleanly when absent, no `note` prop accepted, and `className` forwarded to the root `<header>` via `cn()`
- [ ] T006 Update `solune/frontend/src/components/common/CompactPageHeader.test.tsx` to cover the shared compact-header foundation: minimal props render (eyebrow + title + description), badge absent renders no badge element, actions slot renders children, no decorative hero markup is present, and `className` forwards to the root element
- [ ] T007 Run tests to confirm CompactPageHeader baseline meets spec: `cd solune/frontend && npm run test`

**Checkpoint**: `CompactPageHeader` meets full spec contract. All component tests pass. Page migrations can now begin.

---

## Phase 3: User Story 1 — Compact Page Header Replaces Oversized Hero (Priority: P1) 🎯 MVP

**Goal**: Replace `CelestialCatalogHero` with `CompactPageHeader` on all six affected pages, reducing header height from ~350–450px to ~80–100px and eliminating all decorative hero elements (orbits, stars, beams, moonwell cards, "Current Ritual" aside).

**Independent Test**: Navigate to any of the 6 affected pages. Confirm: (1) header occupies ~80–100px, (2) eyebrow, title, badge (if provided), and action buttons appear in a single row, (3) no decorative hero elements visible, (4) no `note`/"Current Ritual" aside present.

- [ ] T008 [P] [US1] Replace `CelestialCatalogHero` with `CompactPageHeader` in `solune/frontend/src/pages/ProjectsPage.tsx`: update import, map eyebrow/title/description/badge (project badge)/stats (heroStats array)/actions (two anchor actions) to `CompactPageHeader` props, remove all `note` and hero-class props
- [ ] T009 [P] [US1] Replace `CelestialCatalogHero` with `CompactPageHeader` in `solune/frontend/src/pages/AgentsPage.tsx`: update import, map eyebrow/title/description/badge (repo badge)/stats (four stat chips from board query)/actions (two anchor actions) to `CompactPageHeader` props, remove `note` prop
- [ ] T010 [P] [US1] Replace `CelestialCatalogHero` with `CompactPageHeader` in `solune/frontend/src/pages/AgentsPipelinePage.tsx`: update import, map eyebrow/title/description/badge (project badge)/stats (pipeline-related stats)/actions (two actions: editor + saved-workflow entry) to `CompactPageHeader` props, remove `note` prop
- [ ] T011 [P] [US1] Replace `CelestialCatalogHero` with `CompactPageHeader` in `solune/frontend/src/pages/ToolsPage.tsx`: update import, map eyebrow/title/description/badge (repo badge)/stats (repository + project stats)/actions (three action buttons) to `CompactPageHeader` props, remove `note` prop
- [ ] T012 [P] [US1] Replace `CelestialCatalogHero` with `CompactPageHeader` in `solune/frontend/src/pages/ChoresPage.tsx`: update import, map eyebrow/title/description/badge (repo badge)/stats (four stat chips from board/workflow query)/actions (two actions) to `CompactPageHeader` props, remove `note` prop
- [ ] T013 [P] [US1] Replace `CelestialCatalogHero` with `CompactPageHeader` in `solune/frontend/src/pages/HelpPage.tsx`: update import, map eyebrow/title/description/actions (one action) to `CompactPageHeader` props — omit `stats` and `badge` entirely (data-model confirms HelpPage has no stats), remove `note` prop
- [ ] T014 [US1] Review and update page-level header tests in `solune/frontend/src/pages/ProjectsPage.test.tsx`, `solune/frontend/src/pages/AgentsPage.test.tsx`, `solune/frontend/src/pages/AgentsPipelinePage.test.tsx`, `solune/frontend/src/pages/ToolsPage.test.tsx`, `solune/frontend/src/pages/ChoresPage.test.tsx`, and `solune/frontend/src/pages/HelpPage.test.tsx` so `CompactPageHeader` assertions and mocked actions match the migrated page props
- [ ] T015 [US1] Run regression tests to confirm US1 delivery with no regressions: `cd solune/frontend && npm run test`

**Checkpoint**: All six pages render compact headers. No TypeScript errors. No test regressions. US1 is independently demonstrable.

---

## Phase 4: User Story 2 — Stats Displayed as Compact Chips (Priority: P1)

**Goal**: Confirm stats render as small pill/chip elements inline within the header on each page that provides stats data — not as large moonwell cards. HelpPage (no stats) must render cleanly with no empty placeholder space.

**Independent Test**: Navigate to the Projects page. Confirm each stat (e.g., "Board columns", "Project") appears as a compact pill with a label and value. No stat spans full card height. Navigate to HelpPage and confirm no stat rail or empty region is visible.

- [ ] T016 [US2] Update stat chip markup in `solune/frontend/src/components/common/CompactPageHeader.tsx` so each `CompactPageHeaderStat` renders as a visually-distinct pill showing both `label` and `value`, chips stay inline on desktop, and the stats container does not render when `stats` is undefined or empty
- [ ] T017 [US2] Add stat chip regression tests to `solune/frontend/src/components/common/CompactPageHeader.test.tsx`: (1) three-chip scenario — verify each chip shows its label and value text, (2) HelpPage scenario — pass no `stats` prop and assert the stats container is absent from the DOM, (3) single chip scenario — verify no layout overflow
- [ ] T018 [US2] Run tests to confirm US2 stat chip behavior: `cd solune/frontend && npm run test`

**Checkpoint**: Stat chips render correctly on stats-bearing pages; HelpPage renders cleanly with no stat region. US2 independently verifiable.

---

## Phase 5: User Story 6 — Existing Functionality Preserved (Priority: P1)

**Goal**: Confirm that replacing the hero header has introduced zero regressions — all action buttons, page navigation, content filters, and data display below the header work identically to the pre-migration behavior.

**Independent Test**: On each of the 6 pages, click every action button in the header and confirm it triggers the same behavior as before (navigation, modal open, filter toggle, etc.). Use all page-level filters and verify content below the header is unaffected.

- [ ] T019 [US6] Verify action button handlers and routing are unchanged in `solune/frontend/src/pages/ProjectsPage.tsx` and `solune/frontend/src/pages/AgentsPage.tsx` after migration — confirm no `onClick`, `href`, or `to` prop was altered during the hero swap
- [ ] T020 [P] [US6] Verify action button handlers and routing are unchanged in `solune/frontend/src/pages/AgentsPipelinePage.tsx`, `solune/frontend/src/pages/ToolsPage.tsx`, `solune/frontend/src/pages/ChoresPage.tsx`, and `solune/frontend/src/pages/HelpPage.tsx` after migration
- [ ] T021 [US6] Add actions-slot regression tests to `solune/frontend/src/components/common/CompactPageHeader.test.tsx`: verify that `actions` children render and that simulated click events on action children propagate correctly (no swallowed events)
- [ ] T022 [US6] Run full regression test suite: `cd solune/frontend && npm run test`
- [ ] T023 [US6] Run lint and type-check to confirm no new errors introduced by page migrations: `cd solune/frontend && npm run lint && npm run type-check`

**Checkpoint**: All existing functionality preserved. SC-004 (tests pass), SC-005 (actions work), SC-008 (lint/types clean) are satisfied. US6 independently verifiable.

---

## Phase 6: User Story 3 — Description Shown as Single-Line Subtitle (Priority: P2)

**Goal**: Confirm the page description renders as a truncated single-line subtitle by default, with the full text revealed when the user hovers over it. No description causes the header to grow beyond its compact height.

**Independent Test**: Navigate to any page with a long description. Confirm the description is truncated with an ellipsis on initial render (one visible line). Hover over the description and confirm the full text expands. The header must not jump to a taller height on page load.

- [ ] T024 [US3] Update the description element in `solune/frontend/src/components/common/CompactPageHeader.tsx` to use Tailwind `line-clamp-1` by default, `group-hover:line-clamp-none` (or equivalent) for expand-on-hover, and a parent `group` class for hover propagation
- [ ] T025 [US3] Confirm all six page description strings are passed as the `description` prop to `CompactPageHeader` in their respective page files (`solune/frontend/src/pages/ProjectsPage.tsx` through `HelpPage.tsx`) and that none apply additional container styles overriding truncation behavior
- [ ] T026 [US3] Add description truncation regression tests to `solune/frontend/src/components/common/CompactPageHeader.test.tsx`: assert the description element has the `line-clamp-1` CSS class, assert the parent container has the `group` class, assert long description text is present in the DOM (truncation is CSS-only, not text-slicing)
- [ ] T027 [US3] Run tests to confirm US3 subtitle behavior: `cd solune/frontend && npm run test`

**Checkpoint**: Description single-line truncation verified via CSS class assertions. Hover-expand behavior confirmed in markup. US3 independently verifiable.

---

## Phase 7: User Story 4 — Mobile-Friendly Header Layout (Priority: P2)

**Goal**: Confirm the compact header adapts gracefully to mobile viewports (≤768px): elements stack or wrap without horizontal overflow, stats are hidden behind an accessible toggle by default, and action buttons remain visible and tappable.

**Independent Test**: Open any affected page at ≤768px viewport width. Confirm: (1) no horizontal scrollbar, (2) stats section is not visible on initial load, (3) a toggle control is present, (4) clicking the toggle reveals the stats section, (5) action buttons are accessible and tappable.

- [ ] T028 [US4] Update responsive Tailwind classes in `solune/frontend/src/components/common/CompactPageHeader.tsx` so stats stay hidden below the mobile breakpoint by default, the stats toggle renders only when `stats` are present at narrow widths, and action buttons remain visible on mobile
- [ ] T029 [US4] Verify the stats mobile toggle button in `solune/frontend/src/components/common/CompactPageHeader.tsx` is accessible: it must have `aria-expanded` attribute reflecting the open/closed disclosure state and `aria-controls` referencing the stats region ID, with a descriptive label (e.g., "Show stats" / "Hide stats")
- [ ] T030 [US4] Add mobile behavior regression tests to `solune/frontend/src/components/common/CompactPageHeader.test.tsx`: (1) stats container has `hidden` class or is absent from rendered output on initial render when stats are provided, (2) clicking the toggle button causes the stats container to become visible, (3) action buttons are present in the DOM regardless of stats toggle state
- [ ] T031 [US4] Run tests to confirm US4 mobile behavior: `cd solune/frontend && npm run test`

**Checkpoint**: Mobile layout confirmed via class and DOM assertions. Stats toggle accessibility verified. US4 independently verifiable.

---

## Phase 8: User Story 5 — Dead Code and Orphaned Styles Removed (Priority: P3)

**Goal**: Delete the `CelestialCatalogHero` component and its test file now that all six pages have migrated, then remove only the CSS selectors in `index.css` that are exclusively scoped to the deleted hero. Shared celestial utilities must be preserved.

**Independent Test**: Search the codebase for `CelestialCatalogHero` — zero references should remain. Search `index.css` for `catalog-hero-` — no orphaned selectors should remain. Run `npm run test && npm run lint && npm run type-check` — all pass. Confirm `.moonwell`, `.hanging-stars`, and `.celestial-*` classes still exist in `index.css`.

- [ ] T032 [US5] Confirm zero `CelestialCatalogHero` references remain after Phase 3 migration: `grep -r "CelestialCatalogHero" solune/frontend/src` — output must be empty before proceeding to deletions
- [ ] T033 [P] [US5] Delete the legacy hero component file `solune/frontend/src/components/common/CelestialCatalogHero.tsx` if it still exists after T032 confirms no remaining imports
- [ ] T034 [P] [US5] Delete the legacy hero test file `solune/frontend/src/components/common/CelestialCatalogHero.test.tsx` if it still exists after T032 confirms no remaining imports
- [ ] T035 [US5] Audit `solune/frontend/src/index.css` for selectors exclusively scoped to the deleted hero: search for `catalog-hero-`, `projects-catalog-hero`, and any hero-specific animation keyframe names appearing only in hero-related rule blocks
- [ ] T036 [US5] Remove orphaned hero-specific CSS rules from `solune/frontend/src/index.css` — remove `catalog-hero-*` selector blocks and `projects-catalog-hero` namespace rules; **DO NOT remove** `.moonwell` (used by 30+ components), `.hanging-stars` (used by LoginPage), or `.celestial-*` animation classes (used by CelestialLoader, Sidebar, AppLayout, and other components per specs/001-simplify-page-headers/research.md §R3)
- [ ] T037 [US5] Confirm preserved shared CSS classes still exist in `solune/frontend/src/index.css` after cleanup: `grep -n "moonwell\|hanging-stars\|celestial-" solune/frontend/src/index.css` — all three must still appear
- [ ] T038 [US5] Run full regression suite after dead code removal: `cd solune/frontend && npm run test && npm run lint && npm run type-check`

**Checkpoint**: Zero `CelestialCatalogHero` references remain. Hero-specific CSS removed. Shared celestial classes preserved. SC-007 (zero references) and SC-008 (lint/types clean) satisfied. US5 independently verifiable.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Final regression gate across tests, lint, and types; browser smoke test across all 6 pages on both desktop and mobile viewports; confirm all success criteria from spec.md are met.

- [ ] T039 Run complete frontend test suite as final regression gate (SC-004): `cd solune/frontend && npm run test`
- [ ] T040 [P] Run final ESLint check — zero new errors (SC-008): `cd solune/frontend && npm run lint`
- [ ] T041 [P] Run final TypeScript type-check — zero new errors (SC-008): `cd solune/frontend && npm run type-check`
- [ ] T042 [P] Confirm zero remaining `CelestialCatalogHero` or `catalog-hero` references as final cleanup check (SC-007): `grep -r "CelestialCatalogHero\|catalog-hero" solune/frontend/src`
- [ ] T043 Browser smoke test — start dev server (`cd solune/frontend && npm run dev`) and manually verify on desktop viewport: all 6 pages (`/projects`, `/agents`, `/agents/pipeline`, `/tools`, `/chores`, `/help`) show compact header (~80–100px), no decorative hero elements, stats as chips, description truncated (SC-001 through SC-003)
- [ ] T044 Browser smoke test on mobile viewport (≤768px) using the dev server from `solune/frontend` across `/projects`, `/agents`, `/agents/pipeline`, `/tools`, `/chores`, and `/help`: verify stats hidden behind toggle, action buttons accessible, no horizontal overflow, and header adapts without layout breaking (SC-006)

**Checkpoint**: All SC-001 through SC-008 satisfied. Feature complete.

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 (Setup / Baseline Audit)          — no dependencies; start immediately
  └─> Phase 2 (Foundational)              — BLOCKS all user story phases
        └─> Phase 3 (US1, P1)             — 6 page migrations; all parallel
              └─> Phase 4 (US2, P1)       — stat chip verification; pages must be stable
                    └─> Phase 5 (US6, P1) — regression gate; US1 + US2 must be complete
                          └─> Phase 6 (US3, P2) — description behavior; component stable
                                └─> Phase 7 (US4, P2) — mobile behavior; component stable
                                      └─> Phase 8 (US5, P3) — dead code removal; ALL pages migrated
                                            └─> Final Phase (Polish)
```

### User Story Dependencies

| Story | Priority | Depends On | Can Start After |
|-------|----------|------------|-----------------|
| US1 | P1 | Phase 2 (component ready) | T007 passes |
| US2 | P1 | US1 complete (pages migrated) | T015 passes |
| US6 | P1 | US1 + US2 complete | T018 passes |
| US3 | P2 | US6 complete | T023 passes |
| US4 | P2 | US3 complete | T027 passes |
| US5 | P3 | US1 complete (all 6 pages migrated) | T015 passes |

### Within Each Phase

- Phase 3 tasks T008–T013: all parallel (different page files, no inter-dependencies)
- Phase 8 tasks T033–T034: parallel (different files)
- Final Phase T040–T042: parallel (independent validation commands)
- All regression-run tasks (T004, T007, T015, T018, T022, T027, T031, T038, T039) are sequential within their phase

---

## Parallel Execution Examples Per Story

### Phase 3 — US1: All 6 Page Migrations

```bash
# All 6 migration tasks execute simultaneously (different files, no blocking dependency):
Task T008: "Migrate ProjectsPage.tsx — eyebrow/title/description/badge/heroStats/2 actions"
Task T009: "Migrate AgentsPage.tsx — eyebrow/title/description/repoBadge/4 stat chips/2 actions"
Task T010: "Migrate AgentsPipelinePage.tsx — eyebrow/title/description/projectBadge/pipeline stats/2 actions"
Task T011: "Migrate ToolsPage.tsx — eyebrow/title/description/repoBadge/repo+project stats/3 actions"
Task T012: "Migrate ChoresPage.tsx — eyebrow/title/description/repoBadge/4 stat chips/2 actions"
Task T013: "Migrate HelpPage.tsx — eyebrow/title/description/1 action (no stats, no badge)"
```

### Phase 5 — US6: Verify Action Handlers Across Pages

```bash
# T019 and T020 can run in parallel (different page sets):
Task T019: "Verify ProjectsPage.tsx and AgentsPage.tsx action handlers unchanged"
Task T020: "Verify AgentsPipelinePage.tsx, ToolsPage.tsx, ChoresPage.tsx, HelpPage.tsx action handlers unchanged"
```

### Phase 8 — US5: Dead Code Deletion

```bash
# T033 and T034 run simultaneously (different files):
Task T033: "Delete solune/frontend/src/components/common/CelestialCatalogHero.tsx"
Task T034: "Delete solune/frontend/src/components/common/CelestialCatalogHero.test.tsx"
```

### Final Phase — Validation

```bash
# T040, T041, T042 run simultaneously (independent commands):
Task T040: "npm run lint"
Task T041: "npm run type-check"
Task T042: "grep -r 'CelestialCatalogHero|catalog-hero' solune/frontend/src"
```

---

## Independent Test Criteria Per Story

| Story | How to Verify Independently |
|-------|----------------------------|
| **US1** | Navigate to any of the 6 pages; confirm header ~80–100px, single-row layout, no decorative hero elements, no "Current Ritual" aside |
| **US2** | Navigate to Projects or Agents page; confirm each stat renders as a pill chip with label + value; navigate to HelpPage and confirm no stat rail |
| **US6** | Click every action button on each of the 6 pages; confirm behavior identical to pre-migration; run `npm run test` and confirm zero regressions |
| **US3** | Navigate to any page with a long description; confirm one-line truncation with ellipsis; hover over description; confirm full text expands |
| **US4** | View any affected page at ≤768px viewport; confirm stats hidden on load, toggle shows stats, action buttons visible and tappable, no horizontal overflow |
| **US5** | Run `grep -r "CelestialCatalogHero" solune/frontend/src` → zero results; run `grep "catalog-hero" solune/frontend/src/index.css` → zero results; run `npm run test && npm run lint && npm run type-check` → all pass |

---

## Implementation Strategy

### MVP First (Phases 1–3, US1 only)

1. Complete Phase 1: Baseline audit (T001–T004)
2. Complete Phase 2: Align `CompactPageHeader` component (T005–T007)
3. Complete Phase 3: Migrate all 6 pages (T008–T015)
4. **STOP and VALIDATE**: All 6 pages show compact header, `npm run test` passes
5. Deploy/demo — users immediately see the full vertical-space benefit (US1 delivered)

### Incremental Delivery

1. Phases 1–2 → Component ready, baseline green
2. Phase 3 → 6 pages migrated → **MVP!** (US1 delivered; US2/US3/US4 are component-level behaviors already present)
3. Phase 4 → Stat chip behavior locked in (US2)
4. Phase 5 → Regression gate confirmed (US6)
5. Phases 6–7 → Description and mobile behavior verified (US3, US4)
6. Phase 8 → Codebase cleaned (US5)
7. Final Phase → All SC-001 through SC-008 confirmed

### Parallel Team Strategy

With multiple developers after Phase 2 completes:

- **Developer A**: T008 (ProjectsPage) + T011 (ToolsPage)
- **Developer B**: T009 (AgentsPage) + T012 (ChoresPage)
- **Developer C**: T010 (AgentsPipelinePage) + T013 (HelpPage)

Then any developer continues with T014 → T015 (regression check), followed by sequential US2 → US6 → US3 → US4 verification phases, and finally the US5 cleanup phase.

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tasks** | 44 |
| **Phase 1 (Setup)** | 4 tasks (T001–T004) |
| **Phase 2 (Foundational)** | 3 tasks (T005–T007) |
| **Phase 3 (US1 — P1)** | 8 tasks (T008–T015) |
| **Phase 4 (US2 — P1)** | 3 tasks (T016–T018) |
| **Phase 5 (US6 — P1)** | 5 tasks (T019–T023) |
| **Phase 6 (US3 — P2)** | 4 tasks (T024–T027) |
| **Phase 7 (US4 — P2)** | 4 tasks (T028–T031) |
| **Phase 8 (US5 — P3)** | 7 tasks (T032–T038) |
| **Final Phase (Polish)** | 6 tasks (T039–T044) |
| **Tasks per user story** | US1: 8 · US2: 3 · US6: 5 · US3: 4 · US4: 4 · US5: 7 |
| **Regression-validation test tasks** | 12 explicit validation task lines (some lines run multiple commands): T004, T007, T015, T018, T022, T023, T027, T031, T038, T039, T040, T041 |
| **Parallel opportunities** | 6-way page migration (Phase 3); 2-way verification (Phase 5); 2-way deletion (Phase 8); 3-way final validation (Final Phase) |
| **Suggested MVP scope** | Phases 1–3 (15 tasks: audit + component alignment + all 6 page migrations) |
| **Independent test criteria** | Defined per user story in the table above |
| **Format validation** | ✅ All 44 task lines follow `- [ ] T### [P?] [US#?] Description with file path`; setup/foundational/polish tasks carry no [US#]; user story tasks carry the correct [US1]–[US6] labels; no completed checkboxes; no sample template text remaining |

---

## Notes

- **[P] marker**: Present only on tasks that touch different files with no unmet dependencies at time of execution
- **[US#] label**: Required on all user story phase tasks; absent from setup, foundational, and polish phases
- **CSS safety rule (specs/001-simplify-page-headers/research.md §R3)**: DO NOT remove `.moonwell`, `.hanging-stars`, or `.celestial-*` animation classes — confirmed shared across 30+ components; remove only `catalog-hero-*` and `projects-catalog-hero` namespace rules
- **HelpPage special case**: Omit `stats` and `badge` props entirely — data-model confirms HelpPage has no stats; header must render cleanly without placeholder space
- **`note` prop**: No page should pass a `note` prop; it is not in the component contract (compact-page-header-contract.yaml) and must be removed during Phase 3 migration
- **Phase 8 gate**: Do not delete `CelestialCatalogHero` files (T033–T034) until T032 confirms zero references — all 6 page migrations must be complete first
- **Regression-validation rationale**: Tests are required (not optional) for this feature because spec.md SC-004 and SC-008 explicitly mandate zero regression on `npm run test`, `npm run lint`, and `npm run type-check`
- Commit after each task or logical group to keep diffs reviewable
- Stop at Phase 3 checkpoint to validate MVP independently before continuing
