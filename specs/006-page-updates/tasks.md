# Tasks: Page Updates

**Input**: Design documents from `/specs/006-page-updates/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Not explicitly requested — test tasks are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/frontend/src/`
- Backend pipeline presets: `solune/backend/src/services/pipelines/service.py`
- Frontend pages: `solune/frontend/src/pages/`
- Frontend components: `solune/frontend/src/components/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify environment, understand current state, no code changes

- [ ] T001 Verify frontend builds cleanly with `npm run build` in `solune/frontend/`
- [ ] T002 Verify backend lints cleanly with `uv run ruff check src/` in `solune/backend/`
- [ ] T003 [P] Review current pipeline preset definitions in `solune/backend/src/services/pipelines/service.py` (lines 78–310) to understand `_PRESET_DEFINITIONS` structure

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational blocking tasks — all user stories target independent page surfaces (Home Page, Pipeline Page, Agents Page) and can proceed directly after setup

**⚠️ NOTE**: There are no shared infrastructure changes required before user story work begins. Each story modifies a different page or component.

**Checkpoint**: Setup verified — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — Home Page: Add New Chat Panel Button Works (Priority: P1) 🎯 MVP

**Goal**: Fix the broken "Add New Chat Panel" button on the Home Page so clicking it creates a new chat panel.

**Independent Test**: Navigate to the Home Page, click the "Add New Chat Panel" button, and verify a new chat panel is created and displayed.

### Implementation for User Story 1

- [ ] T004 [US1] Debug `handleAddPanel` callback in `solune/frontend/src/components/chat/ChatPanelManager.tsx` (line 126) — trace why `createConversation` or `addPanel` fails and fix the root cause
- [ ] T005 [US1] Verify `createConversation` API call in `solune/frontend/src/hooks/useChatPanels.ts` returns a valid `conversation_id` and `addPanel` correctly updates panel state
- [ ] T006 [US1] Verify `POST /conversations` endpoint in `solune/backend/src/api/chat.py` responds correctly when called from the frontend
- [ ] T007 [US1] Validate the fix by clicking "Add New Chat Panel" button multiple times and confirming each click creates an additional panel without errors

**Checkpoint**: At this point, User Story 1 should be fully functional — the "Add New Chat Panel" button on the Home Page works correctly.

---

## Phase 4: User Story 2 — Pipeline Page: Built-in Saved Pipelines (Priority: P1)

**Goal**: Replace all existing built-in saved pipeline presets with exactly four predefined pipelines: "GitHub", "Spec Kit", "Default", and "App Builder", each with agents in a single "In progress" stage using Auto mode and Group 1.

**Independent Test**: Navigate to the Pipeline page, verify exactly four built-in saved pipelines are listed (GitHub, Spec Kit, Default, App Builder), and confirm each contains the correct agents.

### Implementation for User Story 2

- [ ] T008 [US2] Replace `_PRESET_DEFINITIONS` list in `solune/backend/src/services/pipelines/service.py` (lines 78–310) — remove all existing presets (spec-kit, github-copilot, easy, medium, hard, expert) and replace with four new presets:
  - "GitHub": single "In progress" stage with GitHub Copilot (Auto, Group 1)
  - "Spec Kit": single "In progress" stage with speckit.specify, speckit.plan, speckit.tasks, speckit.analyze, speckit.implement (all Auto, Group 1)
  - "Default": single "In progress" stage with speckit.specify, speckit.plan, speckit.tasks, speckit.analyze, speckit.implement, Quality Assurance, Tester, Linter, Copilot Review, Judge (all Auto, Group 1)
  - "App Builder": single "In progress" stage with speckit.specify, speckit.plan, speckit.tasks, speckit.analyze, speckit.implement, Architect, Quality Assurance, Tester, Linter, Copilot Review, Judge (all Auto, Group 1)
- [ ] T009 [US2] Update `seed_presets` method in `solune/backend/src/services/pipelines/service.py` (around line 615) if it references old preset IDs, ensuring it correctly seeds the four new presets
- [ ] T010 [US2] Verify `POST /{project_id}/seed-presets` endpoint in `solune/backend/src/api/pipelines.py` (line 225) works with the new presets
- [ ] T011 [US2] Verify the Pipeline page at `solune/frontend/src/components/pipeline/SavedWorkflowsList.tsx` correctly renders the four new presets with their agent configurations
- [ ] T012 [US2] Update any backend tests referencing old preset IDs (spec-kit, github-copilot, easy, medium, hard, expert) to reflect the new preset definitions
- [ ] T013 [US2] Run backend validation (`uv run ruff check src/ tests/` and `uv run pytest tests/unit/ -q`) from `solune/backend/` to confirm no regressions

**Checkpoint**: At this point, User Story 2 should be fully functional — the Pipeline page shows exactly four built-in saved pipelines with correct configurations.

---

## Phase 5: User Story 3 — Agents Page: Richer Agent Tiles for Awesome Copilot Browser (Priority: P2)

**Goal**: Restyle agent tiles in the "Browse Awesome Copilot Agents" section to be metadata-rich cards that can be clicked to expand and show more details, or link out to the Awesome Copilots website.

**Independent Test**: Navigate to the Agents page, view the "Browse Awesome Copilot Agents" section, verify each agent tile displays metadata (name, description, tags). Click a tile and verify it either expands or links to the Awesome Copilots website.

### Implementation for User Story 3

- [ ] T014 [P] [US3] Create a new `CatalogAgentCard` component in `solune/frontend/src/components/agents/CatalogAgentCard.tsx` that renders a metadata-rich tile with: agent name, description, tags/categories, and an expand/link-out interaction (modern card-based UI pattern with clear visual hierarchy)
- [ ] T015 [US3] Update the catalog agents grid in `solune/frontend/src/components/agents/AgentsPanel.tsx` (around lines 323–428, the "Browse Awesome Copilot Agents" section) to use `CatalogAgentCard` instead of the current simple tile rendering for catalog agents
- [ ] T016 [US3] Ensure catalog agent tile expand/link-out interaction works: either inline expansion revealing more detail, or opening the Awesome Copilots website URL in a new tab (choose best UX)
- [ ] T017 [US3] Verify the new tiles render correctly with accessible interaction affordances and responsive layout

**Checkpoint**: At this point, User Story 3 should be fully functional — catalog agent tiles are metadata-rich and interactive.

---

## Phase 6: User Story 4 — Agents Page: Section Reordering and Layout Cleanup (Priority: P2)

**Goal**: Reorder and clean up the Agents page layout: move "Agent PRs waiting on main" above "Browse Awesome Copilot Agents", remove the orbital map from the right side, remove the "Agent Archive" section, and relocate "Refresh agents" and "+ Add agent" buttons near "Curate agent rituals" and "Review assignments" buttons.

**Independent Test**: Navigate to the Agents page and verify: (1) "Agent PRs waiting on main" appears before "Browse Awesome Copilot Agents", (2) no orbital map on the right, (3) no "Agent Archive" section, (4) "Refresh agents" and "+ Add agent" buttons are near "Curate agent rituals" and "Review assignments".

### Implementation for User Story 4

- [ ] T018 [P] [US4] Remove the "Agent Archive" section (lines 279–306) from `solune/frontend/src/components/agents/AgentsPanel.tsx` — this includes the "Broader space for every active assistant" heading, the "Refresh models" button, and the "+ Add Agent" button in that section
- [ ] T019 [P] [US4] Remove the orbital map / "Column assignments" panel from the right side of `solune/frontend/src/pages/AgentsPage.tsx` (lines 141–242) — remove the entire `#agent-assignments` div and change the grid layout from `xl:grid-cols-[minmax(0,1fr)_22rem]` to a single column
- [ ] T020 [US4] Reorder sections in `solune/frontend/src/components/agents/AgentsPanel.tsx` so the "Agent PRs waiting on main" section (currently lines 487–561) renders ABOVE the "Browse Awesome Copilot Agents" section (currently lines 323–428)
- [ ] T021 [US4] Move "Refresh agents" button and "+ Add Agent" button into the `CompactPageHeader` actions area in `solune/frontend/src/pages/AgentsPage.tsx` (lines 104–113), positioned near the existing "Curate agent rituals" and "Review assignments" buttons
- [ ] T022 [US4] Update the "Review assignments" button link target in `solune/frontend/src/pages/AgentsPage.tsx` (line 110) since the `#agent-assignments` anchor target was removed — either remove this button or retarget it appropriately
- [ ] T023 [US4] Verify the Agents page layout has no visual artifacts, broken links, or empty gaps after the section removal and reordering

**Checkpoint**: At this point, User Story 4 should be fully functional — Agents page layout is clean, reordered, and without removed sections.

---

## Phase 7: User Story 5 — Agents Page: Rename "Refresh Models" to "Refresh Agents" (Priority: P2)

**Goal**: Rename the "Refresh models" button to "Refresh agents" and ensure it refreshes the Awesome Copilot agents catalog from the actual source.

**Independent Test**: Navigate to the Agents page, locate the "Refresh agents" button, click it, and verify the catalog refreshes.

### Implementation for User Story 5

- [ ] T024 [US5] Rename "Refresh models" / "Refreshing models…" button text to "Refresh agents" / "Refreshing agents…" in `solune/frontend/src/components/agents/AgentsPanel.tsx` (line 297) — NOTE: if T018 already removed this button from the Agent Archive section, apply this rename to the relocated button from T021
- [ ] T025 [US5] Update the button's `onClick` handler to call `refetchCatalog` (from `useCatalogAgents` hook, line 68 of AgentsPanel.tsx) instead of or in addition to `refreshModels()` (from `useModels` hook, line 70) so it refreshes the Awesome Copilot agents catalog from the external source
- [ ] T026 [US5] Verify clicking "Refresh agents" triggers a catalog refresh and the agent tiles update with current data

**Checkpoint**: At this point, User Story 5 should be fully functional — button is correctly labeled and refreshes the agents catalog.

---

## Phase 8: User Story 6 — Agents Page: Fix "+ Add Agent" Viewport Positioning (Priority: P2)

**Goal**: Fix the "+ Add Agent" interaction so the resulting modal/panel appears within the browser viewport instead of below the viewable screen.

**Independent Test**: Click "+ Add Agent" from any scroll position on the Agents page and verify the resulting UI element is fully visible without manual scrolling.

### Implementation for User Story 6

- [ ] T027 [US6] Fix `AddAgentModal` positioning in `solune/frontend/src/components/agents/AddAgentModal.tsx` — ensure the modal/dialog uses fixed or viewport-relative positioning (e.g., `fixed inset-0` or centered overlay pattern) so it appears within the visible viewport regardless of scroll position
- [ ] T028 [US6] If the `handleOpenAddModal` callback (line 146 of AgentsPanel.tsx) or the modal's open trigger causes a scroll-down, add `scrollIntoView` or use a portal-based rendering approach to keep the modal in view
- [ ] T029 [US6] Verify the fix works from multiple scroll positions: top of page, middle of page, and bottom of page — the modal should always be visible

**Checkpoint**: At this point, User Story 6 should be fully functional — the "+ Add Agent" modal appears within the viewport.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, cleanup, and cross-cutting improvements

- [ ] T030 [P] Run frontend linting and type checking: `npm run lint && npm run type-check` from `solune/frontend/`
- [ ] T031 [P] Run frontend tests: `npm run test` from `solune/frontend/`
- [ ] T032 [P] Run backend linting: `uv run ruff check src/ tests/` from `solune/backend/`
- [ ] T033 [P] Run backend tests: `uv run pytest tests/unit/ -q` from `solune/backend/`
- [ ] T034 Run frontend build: `npm run build` from `solune/frontend/`
- [ ] T035 Verify no previously working functionality is broken by visual inspection of Home Page, Pipeline Page, and Agents Page
- [ ] T036 Verify custom user-created pipelines are preserved alongside the new built-in presets (FR-008)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: No blocking prerequisites
- **User Stories (Phases 3–8)**: Can proceed in any order — all stories target different pages/components
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)** — Home Page chat panel button: Fully independent. Touches `ChatPanelManager.tsx`, `useChatPanels.ts`, and `chat.py`.
- **User Story 2 (P1)** — Pipeline presets: Fully independent. Touches `service.py` (backend) and `SavedWorkflowsList.tsx` (frontend).
- **User Story 3 (P2)** — Richer agent tiles: Independent. Touches `CatalogAgentCard.tsx` (new) and `AgentsPanel.tsx`.
- **User Story 4 (P2)** — Section reordering: Independent. Touches `AgentsPanel.tsx` and `AgentsPage.tsx`. **Should be done BEFORE or WITH US5 and US6** as it relocates buttons that US5 renames and US6 fixes.
- **User Story 5 (P2)** — Rename button: Depends on US4 for button relocation context. Touches `AgentsPanel.tsx`.
- **User Story 6 (P2)** — Viewport fix: Depends on US4 for button relocation context. Touches `AddAgentModal.tsx` and `AgentsPanel.tsx`.

### Within Each User Story

- Debug/investigation before code changes
- Code changes with incremental validation
- Visual verification after each change

### Parallel Opportunities

- **US1 and US2** can run fully in parallel (different pages, different files)
- **US3, US4, US5, US6** all touch the Agents page — US4 should go first, then US3/US5/US6 can follow
- Within US2: T008 (backend) and T011 (frontend) touch different files
- Within US4: T018 and T019 touch different files and can run in parallel
- All Polish phase tasks marked [P] can run in parallel

---

## Parallel Example: User Story 1 + User Story 2

```bash
# These two stories can run in complete parallel — different pages, different files:

# Developer A: User Story 1 (Home Page)
Task: "Debug handleAddPanel in ChatPanelManager.tsx"
Task: "Verify createConversation API in useChatPanels.ts"

# Developer B: User Story 2 (Pipeline Page)
Task: "Replace _PRESET_DEFINITIONS in service.py"
Task: "Update seed_presets in service.py"
```

## Parallel Example: User Story 4

```bash
# Within US4, these tasks touch different files:
Task: "Remove Agent Archive section from AgentsPanel.tsx"
Task: "Remove orbital map from AgentsPage.tsx"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup verification
2. Skip Phase 2: No foundational blockers
3. Complete Phase 3: User Story 1 — Fix chat panel button (P1 bug fix)
4. Complete Phase 4: User Story 2 — Replace pipeline presets (P1 feature)
5. **STOP and VALIDATE**: Both P1 stories should be independently functional
6. Deploy/demo if ready

### Incremental Delivery

1. Verify setup → Ready to go
2. Fix Home Page button (US1) → Test independently → MVP partial
3. Replace pipeline presets (US2) → Test independently → MVP complete
4. Richer agent tiles (US3) → Test independently → Enhanced
5. Section reorder + layout cleanup (US4) → Test independently → Cleaned up
6. Rename refresh button (US5) → Test independently → Polished
7. Fix add-agent viewport (US6) → Test independently → All bugs fixed
8. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Both start with Setup verification
2. Developer A: US1 (Home Page) + US3 (Agent tiles)
3. Developer B: US2 (Pipeline presets) + US4 (Layout cleanup)
4. After US4 completes: US5 (Rename button) + US6 (Viewport fix)
5. All developers: Polish phase

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- The original issue mentions "speckit.impliment" — this is a typo for "speckit.implement" (corrected in spec and tasks)
- Custom user pipelines must be preserved when replacing built-in presets (FR-008)
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
