---

description: "Task list for UX Fixes — Scrolling, Agents Page, Chat Streaming, Auto Model"
---

# Tasks: UX Fixes — Scrolling, Agents Page, Chat Streaming, Auto Model

**Input**: Design documents from `/home/runner/work/solune/solune/specs/003-ux-fixes/`
**Prerequisites**: `/home/runner/work/solune/solune/specs/003-ux-fixes/plan.md`, `/home/runner/work/solune/solune/specs/003-ux-fixes/spec.md`, `/home/runner/work/solune/solune/specs/003-ux-fixes/research.md`, `/home/runner/work/solune/solune/specs/003-ux-fixes/data-model.md`, `/home/runner/work/solune/solune/specs/003-ux-fixes/contracts/ux-fixes.openapi.yaml`, `/home/runner/work/solune/solune/specs/003-ux-fixes/quickstart.md`

**Tests**: Regression coverage is required by `/home/runner/work/solune/solune/specs/003-ux-fixes/spec.md` and `/home/runner/work/solune/solune/specs/003-ux-fixes/plan.md`, so each user story includes targeted automated tests before implementation tasks.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label for story-specific phases only
- All implementation paths below use absolute repository paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the shared frontend contract surface needed by streaming and resolved-model UX work.

- [X] T001 Update shared chat and workflow response typings for `resolved_model` metadata in `/home/runner/work/solune/solune/solune/frontend/src/types/index.ts`
- [ ] T002 [P] Align SSE parsing and additive response handling for chat and pipeline payloads in `/home/runner/work/solune/solune/solune/frontend/src/services/api.ts` and `/home/runner/work/solune/solune/solune/frontend/src/services/api.test.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared backend contracts and catalog state semantics consumed by multiple stories.

**⚠️ CRITICAL**: Complete this phase before story work so later UI tasks can rely on stable payloads and import states.

- [ ] T003 Update additive resolved-model response schemas in `/home/runner/work/solune/solune/solune/backend/src/models/chat.py` and `/home/runner/work/solune/solune/solune/backend/src/models/workflow.py`
- [ ] T004 [P] Preserve inline-catalog status fields and response semantics in `/home/runner/work/solune/solune/solune/backend/src/models/agents.py` and `/home/runner/work/solune/solune/solune/backend/src/api/agents.py`

**Checkpoint**: Shared payload and catalog contracts are ready for user story implementation.

---

## Phase 3: User Story 1 - Smooth Page Scrolling (Priority: P1) 🎯 MVP

**Goal**: Ensure Settings, Agents, and Pipeline full-page views use a single vertical scroll owner with no nested scroll regions.

**Independent Test**: Open Settings, Agents, and Pipeline views with overflow and confirm each view shows only one vertical scrollbar in loading and ready states.

### Tests for User Story 1 ⚠️

- [X] T005 [P] [US1] Add single-scroll regression coverage for Settings loading and ready shells in `/home/runner/work/solune/solune/solune/frontend/src/pages/SettingsPage.test.tsx`
- [ ] T006 [P] [US1] Add single-scroll regression coverage for Agents and Pipeline shells in `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPage.test.tsx` and `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPipelinePage.test.tsx`

### Implementation for User Story 1

- [X] T007 [US1] Remove nested scroll ownership from loading and content wrappers in `/home/runner/work/solune/solune/solune/frontend/src/pages/SettingsPage.tsx`
- [ ] T008 [P] [US1] Align the Agents page shell to a single scroll owner in `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPage.tsx`
- [ ] T009 [P] [US1] Align the pipeline page shell to a single scroll owner in `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPipelinePage.tsx`

**Checkpoint**: User Story 1 is complete when all three affected pages scroll as one continuous surface.

---

## Phase 4: User Story 2 - Inline Agent Discovery (Priority: P2)

**Goal**: Replace modal-only agent browsing with an inline catalog section that supports search, import, and status visibility on the Agents page.

**Independent Test**: Visit the Agents page and confirm catalog tiles render inline, filter in real time, import successfully, and stay in the page scroll flow without opening a modal.

### Tests for User Story 2 ⚠️

- [ ] T010 [P] [US2] Add contract coverage for `/agents/{project_id}/catalog` and `/agents/{project_id}/import` in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_agents.py`
- [X] T011 [P] [US2] Expand inline catalog regression coverage for search, import, empty, and error states in `/home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/AgentsPanel.test.tsx`

### Implementation for User Story 2

- [X] T012 [US2] Refactor the inline Agents workspace view to render catalog tiles and retire the browse trigger in `/home/runner/work/solune/solune/solune/frontend/src/components/agents/AgentsPanel.tsx`
- [X] T013 [P] [US2] Extract reusable catalog rendering or retire modal-only behavior in `/home/runner/work/solune/solune/solune/frontend/src/components/agents/BrowseAgentsModal.tsx` and `/home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/BrowseAgentsModal.test.tsx`
- [ ] T014 [P] [US2] Adapt catalog fetch and import state handling for the inline experience in `/home/runner/work/solune/solune/solune/frontend/src/hooks/useAgents.ts`

**Checkpoint**: User Story 2 is complete when discovery, search, and import all happen inline on the Agents page.

---

## Phase 5: User Story 3 - Live Chat Streaming Display (Priority: P2)

**Goal**: Render streamed assistant tokens immediately, preserve partial content on errors, and auto-scroll only while the user stays near the bottom.

**Independent Test**: Send a chat message and confirm tokens appear progressively, auto-scroll follows until the user scrolls up, partial content survives an error, and the final message replaces the stream without duplication.

### Tests for User Story 3 ⚠️

- [ ] T015 [P] [US3] Extend SSE regression coverage for token, done, and error frames in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_chat.py`
- [X] T016 [P] [US3] Expand streaming UI regression coverage for incremental rendering, follow/pause scroll, and clean completion in `/home/runner/work/solune/solune/solune/frontend/src/components/chat/ChatInterface.test.tsx`

### Implementation for User Story 3

- [X] T017 [US3] Preserve streaming buffers, partial errors, and near-bottom follow state in `/home/runner/work/solune/solune/solune/frontend/src/hooks/useChat.ts`
- [X] T018 [P] [US3] Render transient assistant streaming state and viewport follow logic in `/home/runner/work/solune/solune/solune/frontend/src/components/chat/ChatInterface.tsx`
- [X] T019 [P] [US3] Add streaming and partial-error presentation that hands off cleanly to finalized messages in `/home/runner/work/solune/solune/solune/frontend/src/components/chat/MessageBubble.tsx`

**Checkpoint**: User Story 3 is complete when chat feels live from first token through final completion or error.

---

## Phase 6: User Story 4 - Auto Model Resolution Visibility (Priority: P3)

**Goal**: Surface which concrete model Auto selected for chat and pipeline actions, and show actionable guidance when Auto resolution fails.

**Independent Test**: Run chat and pipeline actions with Auto selected and confirm the resolved model name is shown on success and a manual-selection hint appears on failure.

### Tests for User Story 4 ⚠️

- [ ] T020 [P] [US4] Add backend regression coverage for Auto resolution success and failure guidance in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_model_fetcher.py` and `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_pipelines.py`
- [ ] T021 [P] [US4] Add frontend regression coverage for resolved Auto model labels in `/home/runner/work/solune/solune/solune/frontend/src/components/chat/MessageBubble.test.tsx` and `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPipelinePage.test.tsx`

### Implementation for User Story 4

- [ ] T022 [US4] Populate resolved-model metadata for chat and pipeline responses in `/home/runner/work/solune/solune/solune/backend/src/api/chat.py`, `/home/runner/work/solune/solune/solune/backend/src/api/pipelines.py`, and `/home/runner/work/solune/solune/solune/backend/src/services/model_fetcher.py`
- [ ] T023 [P] [US4] Surface resolved Auto model labels in `/home/runner/work/solune/solune/solune/frontend/src/components/pipeline/ModelSelector.tsx` and `/home/runner/work/solune/solune/solune/frontend/src/components/settings/PrimarySettings.tsx`
- [ ] T024 [P] [US4] Show resolved-model metadata and Auto failure guidance in chat message rendering within `/home/runner/work/solune/solune/solune/frontend/src/components/chat/MessageBubble.tsx` and `/home/runner/work/solune/solune/solune/frontend/src/components/chat/ChatInterface.tsx`

**Checkpoint**: User Story 4 is complete when Auto behavior is both transparent and actionable in chat and pipeline flows.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all UX-fix surfaces.

- [ ] T025 [P] Run the targeted frontend regression commands documented in `/home/runner/work/solune/solune/specs/003-ux-fixes/quickstart.md`
- [ ] T026 [P] Run the targeted backend regression commands documented in `/home/runner/work/solune/solune/specs/003-ux-fixes/quickstart.md`
- [ ] T027 Validate the end-to-end manual UX scenarios in `/home/runner/work/solune/solune/specs/003-ux-fixes/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Starts immediately; prepares shared frontend contracts.
- **Foundational (Phase 2)**: Depends on Phase 1; stabilizes backend payloads and agent import semantics used by later UI work.
- **User Story 1 (Phase 3)**: Depends on Phase 2; delivers the MVP single-scroll shell fixes.
- **User Story 2 (Phase 4)**: Depends on Phase 2 and benefits from User Story 1 shell alignment on `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPage.tsx`.
- **User Story 3 (Phase 5)**: Depends on Phase 2; uses the shared stream parsing from `/home/runner/work/solune/solune/solune/frontend/src/services/api.ts`.
- **User Story 4 (Phase 6)**: Depends on Phase 2 and builds on chat rendering from User Story 3 for resolved-model display in chat.
- **Polish (Phase 7)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: No dependency on other user stories after Phase 2.
- **US2 (P2)**: Independent after Phase 2, but should land after US1 so the inline catalog inherits the corrected page shell.
- **US3 (P2)**: Independent after Phase 2.
- **US4 (P3)**: Depends on shared models from Phase 2 and should follow US3 for final chat metadata rendering.

### Within Each User Story

- Execute test tasks first and confirm they fail before implementation.
- Update shared data/contracts before UI surfaces that consume them.
- Complete same-file tasks sequentially when a later task depends on an earlier refactor.
- Validate each story independently before moving to the next priority.

### Parallel Opportunities

- **Setup**: T002 can run in parallel after T001 is underway if typings are agreed.
- **Foundational**: T003 and T004 touch separate backend domains and can run in parallel.
- **US1**: T005 and T006 can run together; T008 and T009 can run together after T007 establishes the shell pattern.
- **US2**: T010 and T011 can run together; T013 and T014 can run together after T012 defines the inline catalog structure.
- **US3**: T015 and T016 can run together; T018 and T019 can run together after T017 exposes stream state.
- **US4**: T020 and T021 can run together; T023 and T024 can run together after T022 emits resolved-model metadata.
- **Polish**: T025 and T026 can run in parallel before T027 manual verification.

---

## Parallel Example: User Story 1

```bash
# Launch US1 regression coverage together
Task: "T005 Add single-scroll regression coverage for /home/runner/work/solune/solune/solune/frontend/src/pages/SettingsPage.test.tsx"
Task: "T006 Add single-scroll regression coverage for /home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPage.test.tsx and /home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPipelinePage.test.tsx"

# After the Settings shell pattern is set, align the other page shells together
Task: "T008 Align /home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPage.tsx to a single scroll owner"
Task: "T009 Align /home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPipelinePage.tsx to a single scroll owner"
```

## Parallel Example: User Story 2

```bash
# Write catalog/import regression coverage together
Task: "T010 Add contract coverage in /home/runner/work/solune/solune/solune/backend/tests/unit/test_api_agents.py"
Task: "T011 Expand inline catalog coverage in /home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/AgentsPanel.test.tsx"

# Split modal retirement from hook updates once inline layout is defined
Task: "T013 Extract or retire modal-only behavior in /home/runner/work/solune/solune/solune/frontend/src/components/agents/BrowseAgentsModal.tsx"
Task: "T014 Adapt inline catalog state handling in /home/runner/work/solune/solune/solune/frontend/src/hooks/useAgents.ts"
```

## Parallel Example: User Story 3

```bash
# Add streaming backend/frontend regression coverage together
Task: "T015 Extend SSE regression coverage in /home/runner/work/solune/solune/solune/backend/tests/unit/test_api_chat.py"
Task: "T016 Expand streaming UI coverage in /home/runner/work/solune/solune/solune/frontend/src/components/chat/ChatInterface.test.tsx"

# Consume exposed stream state in parallel after hook changes land
Task: "T018 Render transient stream state in /home/runner/work/solune/solune/solune/frontend/src/components/chat/ChatInterface.tsx"
Task: "T019 Add streaming/error presentation in /home/runner/work/solune/solune/solune/frontend/src/components/chat/MessageBubble.tsx"
```

## Parallel Example: User Story 4

```bash
# Cover Auto-resolution regressions together
Task: "T020 Add Auto-resolution backend coverage in /home/runner/work/solune/solune/solune/backend/tests/unit/test_model_fetcher.py and /home/runner/work/solune/solune/solune/backend/tests/unit/test_api_pipelines.py"
Task: "T021 Add Auto-resolution frontend coverage in /home/runner/work/solune/solune/solune/frontend/src/components/chat/MessageBubble.test.tsx and /home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPipelinePage.test.tsx"

# Surface resolved-model UI in parallel after backend metadata is emitted
Task: "T023 Surface resolved Auto model labels in /home/runner/work/solune/solune/solune/frontend/src/components/pipeline/ModelSelector.tsx and /home/runner/work/solune/solune/solune/frontend/src/components/settings/PrimarySettings.tsx"
Task: "T024 Show resolved-model metadata in /home/runner/work/solune/solune/solune/frontend/src/components/chat/MessageBubble.tsx and /home/runner/work/solune/solune/solune/frontend/src/components/chat/ChatInterface.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2 to stabilize shared contracts.
2. Complete Phase 3 (US1) to eliminate the most visible scrolling regression.
3. Validate `/home/runner/work/solune/solune/solune/frontend/src/pages/SettingsPage.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPage.tsx`, and `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPipelinePage.tsx` against the independent test criteria.
4. Demo the single-scroll shell fix before taking on the P2 UX improvements.

### Incremental Delivery

1. **Foundation**: Finish T001-T004.
2. **MVP**: Deliver US1 with T005-T009.
3. **Discovery**: Deliver US2 with T010-T014.
4. **Streaming**: Deliver US3 with T015-T019.
5. **Transparency**: Deliver US4 with T020-T024.
6. **Finalize**: Run T025-T027 for regression and manual verification.

### Parallel Team Strategy

1. One developer completes Phase 1-2 shared contract work.
2. After Phase 2:
   - Developer A handles US1 shell fixes.
   - Developer B handles US2 inline catalog work.
   - Developer C handles US3 streaming behavior.
3. Once US3 backend/frontend message flow is stable, Developer C or D completes US4 resolved-model visibility.
4. The team closes with shared regression and quickstart validation.

---

## Notes

- All tasks use absolute repository paths to stay executable without additional path discovery.
- `[P]` markers only appear on tasks that can proceed without conflicting edits to the same incomplete file set.
- User stories remain independently testable per `/home/runner/work/solune/solune/specs/003-ux-fixes/spec.md`.
- The smallest implementation sequence is US1 first, then US2 and US3, then US4, followed by polish.
