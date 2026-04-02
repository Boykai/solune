# Tasks: UI/UX Responsive & Mobile Review

**Input**: Design documents from `/specs/532-uiux-responsive-mobile-review/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/responsive-behavior.md ✅, quickstart.md ✅

**Tests**: Explicitly requested in Phase 5 of the specification (User Story 7 — Comprehensive Responsive Test Coverage). E2E test tasks are included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. 7 user stories extracted from spec.md (US1–US7).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/frontend/src/` for source, `solune/frontend/e2e/` for E2E tests

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Centralize z-index tokens and establish responsive foundation before component-level changes

- [ ] T001 Define z-index CSS custom property tokens in the `@theme` block of `solune/frontend/src/index.css` per the Z-Index Token Model: `--z-base: 0`, `--z-sticky: 10`, `--z-sidebar-backdrop: 40`, `--z-sidebar: 50`, `--z-modal-backdrop: 60`, `--z-modal: 70`, `--z-tour-overlay: 100`, `--z-tour-tooltip: 101`, `--z-agent-modal-base: 110`, `--z-agent-modal-top: 120`, `--z-agent-picker: 140`, `--z-chat: 1000`, `--z-chat-toggle: 1001`, `--z-command-backdrop: 9998`, `--z-command: 9999`, `--z-notification: 10000`
- [ ] T002 Add new viewport entries to `solune/frontend/e2e/viewports.ts`: iPhone XR (414×896) as `mobile-lg` and iPad Air (820×1180) as `tablet-lg`, preserving existing mobile (375×667), tablet (768×1024), and desktop (1280×800) entries

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Replace scattered z-index hard-coded values with centralized token references across all components — MUST complete before user story phases to avoid merge conflicts

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 [P] Replace `z-[40]` with `z-[var(--z-sidebar-backdrop)]` and `z-[50]` with `z-[var(--z-sidebar)]` in `solune/frontend/src/layout/Sidebar.tsx`
- [ ] T004 [P] Replace `z-[10000]` with `z-[var(--z-notification)]` in `solune/frontend/src/layout/NotificationBell.tsx`
- [ ] T005 [P] Replace `z-[9999]` with `z-[var(--z-command)]` and `z-[9998]` with `z-[var(--z-command-backdrop)]` in `solune/frontend/src/components/command-palette/CommandPalette.tsx`
- [ ] T006 [P] Replace `z-[1000]` with `z-[var(--z-chat)]` and `z-[1001]` with `z-[var(--z-chat-toggle)]` in `solune/frontend/src/components/chat/ChatPopup.tsx`
- [ ] T007 [P] Replace `z-[70]` with `z-[var(--z-modal)]` and `z-[60]` with `z-[var(--z-modal-backdrop)]` across all modal components in `solune/frontend/src/components/`
- [ ] T008 [P] Replace `z-[100]` with `z-[var(--z-tour-overlay)]` and `z-[101]` with `z-[var(--z-tour-tooltip)]` in tour/spotlight components in `solune/frontend/src/components/`
- [ ] T009 [P] Replace `z-[110]`/`z-[120]`/`z-[140]` with `z-[var(--z-agent-modal-base)]`/`z-[var(--z-agent-modal-top)]`/`z-[var(--z-agent-picker)]` in agent modal components in `solune/frontend/src/components/agents/`

**Checkpoint**: Z-index centralization complete — all components use token references. User story implementation can now begin in parallel.

---

## Phase 3: User Story 1 — Mobile Chat Usability (Priority: P1) 🎯 MVP

**Goal**: Fix the high-severity virtual keyboard overlap in ChatPopup and ensure all chat components are usable on a 375px mobile screen. Users can type and send messages with the virtual keyboard open, view task/plan previews without horizontal scroll, and use toolbar buttons with adequate touch targets.

**Independent Test**: Open chat on a 375px mobile device (or Chrome mobile emulation), tap the input field, verify the input stays visible above the keyboard. View a task/plan preview and verify it fits within the viewport. Tap each toolbar button and verify ≥44px touch targets.

### Implementation for User Story 1

- [ ] T010 [US1] 🔴 Add `visualViewport` resize handler in `solune/frontend/src/components/chat/ChatPopup.tsx` to detect virtual keyboard open/close — when the keyboard is visible, set `padding-bottom` on the chat container equal to `window.innerHeight - visualViewport.height` so the input stays above the keyboard; add `env(safe-area-inset-bottom)` CSS for iOS safe area (FR-012, R-001)
- [ ] T011 [P] [US1] Guard chat size constants in `solune/frontend/src/components/chat/ChatPopup.tsx` — ensure `MIN_HEIGHT=350` and `MAX_WIDTH=800` do not interfere with mobile fullscreen layout by conditionally skipping resize constraints when `isMobile` is true (FR-013)
- [ ] T012 [P] [US1] Change `max-w-[500px]` to `max-w-[90vw] md:max-w-[500px]` in `solune/frontend/src/components/chat/TaskPreview.tsx` around line 26 so previews fit mobile viewport (FR-014)
- [ ] T013 [P] [US1] Change `max-w-[600px]` to `max-w-[90vw] md:max-w-[600px]` in `solune/frontend/src/components/chat/PlanPreview.tsx` around line 51 so previews fit mobile viewport (FR-014)
- [ ] T014 [P] [US1] Add responsive positioning to history popover in `solune/frontend/src/components/chat/ChatInterface.tsx` around line 704 — conditionally apply `left-0 right-0` on mobile instead of fixed `right-0 w-64` (FR-015)
- [ ] T015 [P] [US1] Add `inputMode="text"` attribute to the textarea/input in `solune/frontend/src/components/chat/MentionInput.tsx` around line 273 to present correct mobile keyboard layout (FR-016)
- [ ] T016 [P] [US1] Increase chat toolbar button touch targets from `h-8 w-8` (32px) to `h-11 w-11 md:h-8 md:w-8` (44px on mobile) in `solune/frontend/src/components/chat/ChatToolbar.tsx` (FR-017)

**Checkpoint**: Mobile chat is fully usable — virtual keyboard doesn't obscure input, previews fit viewport, toolbar buttons are touch-friendly. Can be validated independently at 375px.

---

## Phase 4: User Story 2 — Mobile Navigation & Layout Shell (Priority: P1)

**Goal**: Ensure sidebar, top bar, breadcrumbs, notifications, command palette, and rate-limit bar are all usable on a 375px mobile screen with adequate touch targets and no overflow.

**Independent Test**: Navigate through the app on a 375px viewport — open sidebar (verify overlay with backdrop dismiss and focus trap), tap Help button (verify ≥44px), view deep breadcrumbs (verify truncation), open notifications (verify no overflow), open command palette (verify full-width).

### Implementation for User Story 2

- [ ] T017 [P] [US2] Verify and fix sidebar mobile overlay in `solune/frontend/src/layout/Sidebar.tsx` — confirm animation smoothness, backdrop dismiss on tap, `aria-modal="true"` when open, and focus trapping within the overlay (FR-001)
- [ ] T018 [P] [US2] Increase Help button touch target in `solune/frontend/src/layout/TopBar.tsx` from ~36px to ≥44px on mobile by adding responsive classes `h-11 w-11 md:h-9 md:w-9` (FR-002)
- [ ] T019 [P] [US2] Add breadcrumb truncation and overflow handling in `solune/frontend/src/layout/Breadcrumb.tsx` — add container `max-w-full overflow-hidden` and per-segment `truncate` with `max-w-[120px] sm:max-w-[200px]` to prevent horizontal overflow at 375px (FR-003)
- [ ] T020 [P] [US2] Make notification dropdown viewport-aware in `solune/frontend/src/layout/NotificationBell.tsx` — change fixed `panelWidth=320` to `Math.min(320, window.innerWidth - 24)` so panel fits within 375px screen (FR-004)
- [ ] T021 [P] [US2] Verify command palette mobile usability in `solune/frontend/src/components/command-palette/CommandPalette.tsx` — confirm `w-full max-w-lg` works on mobile, results are scrollable, and keyboard shortcut badges are hidden below `sm:` breakpoint (FR-005)
- [ ] T022 [P] [US2] Verify rate-limit bar in `solune/frontend/src/layout/RateLimitBar.tsx` — confirm `hidden md:flex` does not push content below the fold and no layout shift occurs (FR-006)

**Checkpoint**: All navigation and layout shell elements are mobile-friendly at 375px — no overflow, adequate touch targets, proper overlay behavior.

---

## Phase 5: User Story 3 — Kanban Board Mobile Experience (Priority: P2)

**Goal**: Board columns are appropriately sized for mobile, horizontal scrolling is swipe-friendly with snap behavior, and a visual gradient signals off-screen content. Issue cards truncate gracefully.

**Independent Test**: Load a board with 3+ columns on a 375px viewport — verify columns are shorter (h-[44rem]), horizontal scroll snaps to column starts, gradient fade appears on the trailing edge, and issue card content truncates without breakage.

### Implementation for User Story 3

- [ ] T023 [P] [US3] Add responsive column heights in `solune/frontend/src/components/board/BoardColumn.tsx` around line 45 — change `h-[72rem] xl:h-[95rem]` to `h-[44rem] md:h-[72rem] xl:h-[95rem]` (FR-007)
- [ ] T024 [US3] Mirror responsive column heights in `solune/frontend/src/components/board/BoardColumnSkeleton.tsx` around line 11 — match the same responsive height pattern as BoardColumn (depends on T023)
- [ ] T025 [P] [US3] Reduce mobile grid column minimum width in `solune/frontend/src/components/board/ProjectBoard.tsx` around line 45 — change `minmax(min(16rem, 85vw), 1fr)` to `minmax(min(14rem, 85vw), 1fr)` on mobile to prevent forced horizontal overflow with >2 columns (FR-008)
- [ ] T026 [US3] Add scroll-snap behavior on mobile to the board grid container in `solune/frontend/src/components/board/ProjectBoard.tsx` — add `scroll-snap-type: x mandatory` on mobile and `scroll-snap-align: start` on each column child (FR-010)
- [ ] T027 [US3] Add gradient fade scroll affordance to `solune/frontend/src/components/board/ProjectBoard.tsx` — render a right-edge gradient overlay when horizontally scrollable content exists, using a scroll event listener or overflow detection (FR-009)
- [ ] T028 [P] [US3] Verify issue card truncation in `solune/frontend/src/components/board/IssueCard.tsx` — confirm text, labels, assignees, and drag handles render correctly at 375px without layout breakage; fix any overflow issues found (FR-011)

**Checkpoint**: Board is swipe-friendly on mobile with properly sized columns, snap scrolling, and visual scroll affordance.

---

## Phase 6: User Story 4 — Pipeline View on Mobile (Priority: P2)

**Goal**: Pipeline stages fit on a 375px screen with readable font sizes and the flow graph is navigable via touch gestures.

**Independent Test**: Load the pipeline view on a 375px viewport — verify stage containers fit without overflow, pipeline name text scales down, and the flow graph responds to pinch-to-zoom and swipe.

### Implementation for User Story 4

- [ ] T029 [P] [US4] Reduce pipeline stage minimum width on mobile in `solune/frontend/src/components/pipeline/PipelineBoard.tsx` around line 85 — adjust `minmax()` to use `12rem` minimum on mobile (FR-018)
- [ ] T030 [P] [US4] Scale pipeline name font size in `solune/frontend/src/components/pipeline/PipelineBoard.tsx` around line 139 — add `text-base sm:text-lg` responsive classes (FR-019)
- [ ] T031 [US4] Verify pipeline flow graph touch interaction in `solune/frontend/src/components/pipeline/PipelineFlowGraph.tsx` — confirm ReactFlow is scrollable and zoomable via touch gestures at 375px; fix any touch event handling issues found (FR-020)

**Checkpoint**: Pipeline view is readable and interactive on mobile.

---

## Phase 7: User Story 5 — Modals & Forms on Mobile (Priority: P2)

**Goal**: All 13 modals scroll correctly, dismiss on tap-outside, have full-width inputs, and form content is not hidden behind the keyboard. Settings page uses responsive padding.

**Independent Test**: Open each of the key modals (AddAgentModal, IssueDetailModal, AddChoreModal, CreateAppDialog, ToolSelectorModal) on a 375px viewport — verify internal scroll at 85vh, tap-outside dismiss, full-width inputs, and keyboard clearance.

### Implementation for User Story 5

- [ ] T032 [US5] Audit all 13 modal components for mobile behavior — for each modal, verify: `max-h-[85vh]` with internal scroll works, tap-outside dismisses, all form inputs are `w-full` on mobile, and content is not hidden behind the virtual keyboard; fix any issues found. Key modals: AddAgentModal, IssueDetailModal, AddChoreModal, CreateAppDialog, ToolSelectorModal in `solune/frontend/src/components/`  (FR-026, FR-027, FR-028, FR-029)
- [ ] T033 [P] [US5] Add responsive padding to settings page in `solune/frontend/src/pages/SettingsPage.tsx` around line 84 — change `p-8` to `p-4 md:p-8`; ensure all inputs are `w-full` on mobile (FR-030)
- [ ] T034 [P] [US5] Verify inline validation error messages across modal forms — ensure errors don't push content off-screen or cause horizontal overflow at 375px; fix any overflow issues found in form components (FR-031)

**Checkpoint**: All modals and forms are usable on mobile with proper scrolling, dismissal, and input sizing.

---

## Phase 8: User Story 6 — Visual Consistency & Accessibility Polish (Priority: P3)

**Goal**: Verify and fix reduced motion handling, focus management, touch target compliance, responsive typography, dark mode rendering, and scroll performance.

**Independent Test**: Enable `prefers-reduced-motion: reduce` and verify no animations; toggle dark mode on mobile and check text readability; tab through interactive elements and verify focus rings in both themes; verify all interactive elements ≥44×44px on mobile.

### Implementation for User Story 6

- [ ] T035 [P] [US6] Verify reduced motion handling in `solune/frontend/src/index.css` — confirm all celestial animations are wrapped in `prefers-reduced-motion: no-preference` or disabled under `prefers-reduced-motion: reduce`; fix any animations that still run (FR-033)
- [ ] T036 [P] [US6] Verify focus-visible ring indicators in both light and dark themes — check all interactive elements show `focus-visible:ring-2` (or equivalent) and modal focus trapping works in both themes; fix any missing indicators (FR-034)
- [ ] T037 [P] [US6] Perform touch target sweep across all interactive elements — verify every button, link, and drag handle is ≥44×44px on mobile viewports; fix any undersized targets not already addressed in US1 (chat toolbar) and US2 (top bar) (FR-035)
- [ ] T038 [P] [US6] Verify responsive typography at 375px — check no text is clipped or overflows the viewport on any page; fix any truncation or overflow issues (FR-036)
- [ ] T039 [P] [US6] Verify dark mode rendering on mobile — toggle both themes on 375px, 768px, and 1280px viewports and confirm all text is readable with adequate contrast and no visual misalignment (FR-037)
- [ ] T040 [P] [US6] Verify scroll performance of `InfiniteScrollContainer` on mobile — check for jank or frame drops during scroll on a mobile viewport; fix any performance issues (FR-038)

**Checkpoint**: Accessibility and visual polish complete — reduced motion respected, focus visible, touch targets compliant, themes consistent.

---

## Phase 9: User Story 7 — Comprehensive Responsive Test Coverage (Priority: P3)

**Goal**: Expand existing E2E responsive tests and create new test files covering all major surfaces at the full viewport matrix. Add visual regression screenshots.

**Independent Test**: Run `npm run test:e2e` from `solune/frontend/` — all responsive test specs (existing expanded + 4 new files) pass at all five viewport dimensions.

### Implementation for User Story 7

- [ ] T041 [P] [US7] Expand `solune/frontend/e2e/responsive-board.spec.ts` — add assertions for scroll affordance visibility, scroll-snap behavior, and column height responsiveness at mobile/tablet/desktop viewports (FR-039)
- [ ] T042 [P] [US7] Expand `solune/frontend/e2e/responsive-home.spec.ts` — add assertions for sidebar collapse behavior, touch target sizes on top bar, and breadcrumb truncation (FR-039)
- [ ] T043 [P] [US7] Expand `solune/frontend/e2e/responsive-settings.spec.ts` — add assertions for modal scrollability, responsive padding values, and full-width inputs on mobile (FR-039)
- [ ] T044 [P] [US7] Create `solune/frontend/e2e/responsive-pipeline.spec.ts` — test pipeline stage widths at each viewport, pipeline name font scaling, and flow graph touch interaction (FR-040)
- [ ] T045 [P] [US7] Create `solune/frontend/e2e/responsive-agents.spec.ts` — test agent card reflow to single-column layout on mobile viewports (FR-040)
- [ ] T046 [P] [US7] Create `solune/frontend/e2e/responsive-chores.spec.ts` — test chores grid gap scaling and card layout at mobile/tablet viewports (FR-040)
- [ ] T047 [P] [US7] Create `solune/frontend/e2e/responsive-chat.spec.ts` — test chat popup mobile fullscreen, virtual keyboard handling, preview widths, history popover positioning, and toolbar touch targets (FR-040)
- [ ] T048 [US7] Add visual regression screenshots in the new and expanded E2E test files — capture Playwright screenshots for key mobile layouts (375px) to detect future regressions (FR-042)

**Checkpoint**: Full E2E responsive test coverage — 3 expanded files + 4 new files, all passing at 5 viewports.

---

## Phase 10: Other Pages Verification (Priority: P2)

**Goal**: Verify remaining pages (agents, chores, templates, tool selector, activity, help) render correctly on mobile. These are verify-and-fix tasks from the plan's Phase 2D that map to functional requirements FR-021 through FR-025.

**Independent Test**: Load each page on a 375px viewport and verify no overflow, proper reflow, and readable content.

### Implementation for Other Pages Verification

- [ ] T049 [P] Verify agent card reflow in `solune/frontend/src/components/agents/AgentsPanel.tsx` — confirm cards reflow to single-column on mobile (FR-021)
- [ ] T050 [P] Verify chores grid scaling in `solune/frontend/src/components/chores/ChoresGrid.tsx` — confirm `gap-3 md:gap-5` or equivalent responsive gap styling works (FR-022)
- [ ] T051 [P] Verify template tiles stacking in template browser component — confirm tiles stack vertically on mobile (FR-023)
- [ ] T052 [P] Verify activity timeline readability in `solune/frontend/src/pages/ActivityPage.tsx` — confirm readable on narrow screens without clipping (FR-024)
- [ ] T053 [P] Verify help FAQ accordion in `solune/frontend/src/pages/HelpPage.tsx` — confirm expansion without horizontal overflow (FR-025)
- [ ] T054 [P] Verify ToolSelectorModal in `solune/frontend/src/components/` — confirm no overflow on mobile (already responsive, verify only)

**Checkpoint**: All secondary pages verified on mobile — no overflow or layout issues.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, and cleanup across all stories

- [ ] T055 Run full viewport verification at 375×667, 414×896, 768×1024, 820×1180, and 1280×800 — confirm no horizontal overflow on any page (`document.body.scrollWidth <= window.innerWidth`)
- [ ] T056 Run virtual keyboard overlay test via Chrome mobile emulation — verify chat input stays visible when keyboard opens
- [ ] T057 Run dark mode sweep — toggle themes on each mobile viewport, verify all text readable and no visual misalignment
- [ ] T058 Run `npm run type-check` from `solune/frontend/` — confirm no TypeScript errors
- [ ] T059 Run `npm run lint` from `solune/frontend/` — confirm no linting errors
- [ ] T060 Run `npm run test:e2e` from `solune/frontend/` — confirm all existing + new responsive specs pass
- [ ] T061 Run quickstart.md validation — follow verification checklist from `specs/532-uiux-responsive-mobile-review/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (T001 z-index tokens must exist before T003–T009 can reference them) — **BLOCKS all user stories**
- **User Story 1 — Chat (Phase 3)**: Depends on Foundational (Phase 2) completion — can start as soon as z-index tokens are in place
- **User Story 2 — Navigation (Phase 4)**: Depends on Foundational (Phase 2) — **can run in parallel with Phase 3**
- **User Story 3 — Board (Phase 5)**: Depends on Foundational (Phase 2) — **can run in parallel with Phases 3 & 4**
- **User Story 4 — Pipeline (Phase 6)**: Depends on User Story 3 / Phase 5 (Board) for board grid patterns applied to pipeline — should run after Phase 5
- **User Story 5 — Modals (Phase 7)**: Depends on Foundational (Phase 2) — **can run in parallel with Phases 3–5**
- **User Story 6 — Polish (Phase 8)**: Depends on all implementation phases (3–7) being complete
- **User Story 7 — Tests (Phase 9)**: Depends on all implementation phases (3–8) being complete plus T002 (viewport definitions)
- **Other Pages (Phase 10)**: Depends on Foundational (Phase 2) — **can run in parallel with Phases 3–7**; no story label (cross-cutting verification)
- **Polish & Cross-Cutting (Phase 11)**: Depends on all previous phases being complete

### User Story Dependencies

- **User Story 1 (P1)** — Mobile Chat: Can start after Foundational (Phase 2). No dependency on other stories. **MVP delivery target.**
- **User Story 2 (P1)** — Navigation Shell: Can start after Foundational (Phase 2). Independent of US1.
- **User Story 3 (P2)** — Board: Can start after Foundational (Phase 2). Independent of US1/US2.
- **User Story 4 (P2)** — Pipeline: Depends on US3 for board grid pattern (T025) → pipeline stage width (T029).
- **User Story 5 (P2)** — Modals: Can start after Foundational (Phase 2). Independent of US1–US4.
- **User Story 6 (P3)** — Polish: Depends on US1–US5 completion (touch targets from US1/US2 feed into sweep).
- **User Story 7 (P3)** — Tests: Depends on all implementation stories (US1–US6) being complete.

### Within Each User Story

- Implementation tasks may be parallelized where marked [P]
- Core fix first (e.g., virtual keyboard), then supporting changes
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 2**: All foundational z-index replacement tasks (T003–T009) can run in parallel — different files
- **Phases 3 + 4 + 5 + 7 + 10**: Can all start in parallel once Phase 2 is complete
- **Within US1**: T011–T016 can all run in parallel (different files); T010 is the critical-path task
- **Within US2**: T017–T022 can all run in parallel (different files)
- **Within US3**: T023, T025, T028 in parallel; T024 depends on T023; T026–T027 depend on T025
- **Within US7**: T041–T047 can all run in parallel (different test files)

---

## Parallel Example: User Story 1 — Mobile Chat

```bash
# Critical path task (must complete first):
Task T010: "Add visualViewport resize handler in ChatPopup.tsx"

# Then launch all supporting tasks in parallel (different files):
Task T011: "Guard chat size constants in ChatPopup.tsx"         # same file as T010, run after
Task T012: "Change max-w in TaskPreview.tsx"                    # parallel
Task T013: "Change max-w in PlanPreview.tsx"                    # parallel
Task T014: "Add responsive positioning in ChatInterface.tsx"    # parallel
Task T015: "Add inputMode='text' in MentionInput.tsx"           # parallel
Task T016: "Increase toolbar touch targets in ChatToolbar.tsx"  # parallel
```

## Parallel Example: Foundational Phase

```bash
# All z-index replacement tasks in parallel (different files):
Task T003: "Replace z-index values in Sidebar.tsx"
Task T004: "Replace z-index values in NotificationBell.tsx"
Task T005: "Replace z-index values in CommandPalette.tsx"
Task T006: "Replace z-index values in ChatPopup.tsx"
Task T007: "Replace z-index values in modal components"
Task T008: "Replace z-index values in tour/spotlight components"
Task T009: "Replace z-index values in agent modal components"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (z-index tokens + viewport definitions)
2. Complete Phase 2: Foundational (z-index replacement across all components)
3. Complete Phase 3: User Story 1 — Mobile Chat (🔴 highest severity fix)
4. **STOP and VALIDATE**: Test chat on 375px mobile — keyboard doesn't hide input, previews fit, toolbar buttons ≥44px
5. Deploy/demo if ready — immediate value for all mobile chat users

### Incremental Delivery

1. Complete Setup + Foundational → z-index centralization done, foundation ready
2. Add **User Story 1** (Chat) → Test independently → **Deploy/Demo (MVP!)**
3. Add **User Story 2** (Navigation) → Test independently → Deploy/Demo — all navigation mobile-friendly
4. Add **User Story 3** (Board) → Test independently → Deploy/Demo — board swipe-friendly
5. Add **User Story 4** (Pipeline) + **User Story 5** (Modals) → Test independently → Deploy/Demo — all major surfaces done
6. Add **User Story 6** (Polish) → Verify accessibility and visual consistency
7. Add **User Story 7** (Tests) → Full E2E regression coverage
8. Final validation (Phase 11) → All viewports, all themes, all pages
9. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (Phases 1–2)
2. Once Foundational is done:
   - Developer A: User Story 1 (Chat — critical path)
   - Developer B: User Story 2 (Navigation)
   - Developer C: User Story 3 (Board)
3. After initial stories complete:
   - Developer A: User Story 4 (Pipeline — depends on Board patterns)
   - Developer B: User Story 5 (Modals)
   - Developer C: Other Pages Verification (Phase 10)
4. Then:
   - Developer A: User Story 6 (Polish — needs all impl done)
   - Developer B+C: User Story 7 (Tests — needs all impl done, highly parallelizable)
5. Everyone: Final validation (Phase 11)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- The 🔴 marker on T010 indicates the highest-severity fix (virtual keyboard overlap)
- Verify-only tasks (Sidebar, CommandPalette, RateLimitBar, IssueCard, etc.) should still produce code changes if issues are discovered during verification
- All responsive changes follow the existing mobile-first pattern: default = mobile, `md:` = tablet+
- The `useMediaQuery('(max-width: 767px)')` hook is used for JS-level mobile detection — no new hooks needed
- No new libraries — all fixes use Tailwind responsive prefixes and existing utilities
