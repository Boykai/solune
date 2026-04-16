# Tasks: Agents Page UI Improvements

**Input**: Design documents from `specs/003-agents-page-ui/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md, contracts/

**Tests**: Required for this feature because the specification and plan explicitly call for focused Vitest coverage plus `npm run type-check` and `npm run build`.

**Organization**: Tasks are grouped by user story so each change can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: Maps the task to a specific user story (`[US1]`, `[US2]`, `[US3]`)
- All implementation tasks include the exact file path to change

## Path Conventions

- Frontend app: `solune/frontend/`
- Agents UI components: `solune/frontend/src/components/agents/`
- Focused frontend tests: `solune/frontend/src/components/agents/__tests__/`
- Feature artifacts: `specs/003-agents-page-ui/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the frontend-only scope and prepare the focused regression harness before changing production code.

- [ ] T001 Confirm the frontend-only implementation scope against `specs/003-agents-page-ui/contracts/agents-page-ui.openapi.yaml` and keep feature changes limited to `solune/frontend/src/components/agents/`
- [ ] T002 [P] Prepare focused regression fixtures and render helpers in `solune/frontend/src/components/agents/__tests__/AgentsPanel.test.tsx` and `solune/frontend/src/components/agents/__tests__/AddAgentModal.test.tsx`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Verify the shared UI pattern and icon surface that the page-toggle work depends on.

**⚠️ CRITICAL**: Finish this phase before editing user-story behavior.

- [ ] T003 [P] Verify the collapsible header interaction pattern in `solune/frontend/src/components/settings/SettingsSection.tsx` and the `ChevronDown` export in `solune/frontend/src/lib/icons.ts` for reuse in `solune/frontend/src/components/agents/AgentsPanel.tsx`

**Checkpoint**: The implementation approach, icon surface, and test harness are aligned; user-story work can begin.

---

## Phase 3: User Story 1 - Add Agent Modal Is Fully Visible (Priority: P1) 🎯 MVP

**Goal**: Make the Add Agent modal reachable from the top in short and tall viewports without regressing centered presentation for short content.

**Independent Test**: Open `+ Add Agent` on the Agents page, confirm short content stays centered, then shrink the viewport and confirm the overlay scroll exposes the modal title and close button at the top.

### Tests for User Story 1

- [ ] T004 [P] [US1] Add viewport alignment regression coverage in `solune/frontend/src/components/agents/__tests__/AddAgentModal.test.tsx`

### Implementation for User Story 1

- [ ] T005 [P] [US1] Update the primary overlay alignment and scrolling classes in `solune/frontend/src/components/agents/AddAgentModal.tsx` so tall content starts at the top while short content keeps `my-auto` centering

**Checkpoint**: The Add Agent modal is fully reachable in tall viewports and still centered when content fits.

---

## Phase 4: User Story 2 - Reorganized Agents Page Layout (Priority: P1)

**Goal**: Remove Featured Agents, clean up its dead code, and render Catalog Controls before Awesome Catalog while preserving the existing guards.

**Independent Test**: Load the Agents page with agent data and verify the visible order is Quick Actions → Save Banner → Pending Changes → Catalog Controls → Awesome Catalog, with no Featured Agents section anywhere in the DOM.

### Tests for User Story 2

- [ ] T006 [US2] Add section-order, Featured Agents removal, and Catalog Controls guard coverage in `solune/frontend/src/components/agents/__tests__/AgentsPanel.test.tsx`

### Implementation for User Story 2

- [ ] T007 [US2] Remove the Featured Agents spotlight calculations, summary cards, and Featured Agents-only imports/state from `solune/frontend/src/components/agents/AgentsPanel.tsx`
- [ ] T008 [US2] Reorder the loaded-state layout so Catalog Controls renders before Awesome Catalog while keeping the existing guards in `solune/frontend/src/components/agents/AgentsPanel.tsx`

**Checkpoint**: The loaded Agents page uses the new section order and contains no leftover Featured Agents UI or dead code.

---

## Phase 5: User Story 3 - Collapsible Page Sections (Priority: P2)

**Goal**: Let users collapse and expand Pending Changes, Catalog Controls, and Awesome Catalog independently while keeping all sections expanded on initial load.

**Independent Test**: Click each section chevron on the Agents page and confirm only that section body hides/shows, the chevron reflects state, and a full refresh restores all three sections to expanded.

### Tests for User Story 3

- [ ] T009 [US3] Extend section interaction coverage for default-expanded state and independent collapse toggles in `solune/frontend/src/components/agents/__tests__/AgentsPanel.test.tsx`

### Implementation for User Story 3

- [ ] T010 [US3] Add `pendingCollapsed`, `catalogCollapsed`, and `awesomeCatalogCollapsed` local state plus clickable chevron headers in `solune/frontend/src/components/agents/AgentsPanel.tsx`
- [ ] T011 [US3] Conditionally render the Pending Changes, Catalog Controls, and Awesome Catalog bodies with independent `aria-expanded` and chevron rotation behavior in `solune/frontend/src/components/agents/AgentsPanel.tsx`

**Checkpoint**: All three target sections collapse and expand independently with default-expanded behavior preserved.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Run the requested validation steps and complete the manual regression checklist.

- [ ] T012 [P] Run `npm run test -- src/components/agents/__tests__/AgentsPanel.test.tsx src/components/agents/__tests__/AddAgentModal.test.tsx` using the scripts in `solune/frontend/package.json`
- [ ] T013 [P] Run `npm run type-check` and `npm run build` using the scripts in `solune/frontend/package.json`
- [ ] T014 Perform the manual regression checklist in `specs/003-agents-page-ui/quickstart.md` for modal viewport behavior, section order, Featured Agents removal, and section toggles

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; start immediately
- **Foundational (Phase 2)**: Depends on Phase 1; establishes the toggle pattern and icon surface
- **User Story 1 (Phase 3)**: Depends on Phase 2; independent from the AgentsPanel stories
- **User Story 2 (Phase 4)**: Depends on Phase 2; should land before US3 to reduce merge conflicts in `AgentsPanel.tsx`
- **User Story 3 (Phase 5)**: Depends on Phase 2 and is best applied after US2 because both tasks modify `solune/frontend/src/components/agents/AgentsPanel.tsx`
- **Polish (Phase 6)**: Depends on the desired user stories being complete

### User Story Dependencies

- **US1**: No dependency on other user stories after Phase 2
- **US2**: No functional dependency on US1 after Phase 2
- **US3**: Functionally independent after Phase 2, but recommended after US2 because the same component file is being reorganized

### Within Each User Story

- Write or update the story test task first and confirm it fails for the missing behavior
- Apply the implementation task(s) in the named production file
- Re-run focused validation for that story before moving on

### Parallel Opportunities

- **T002** and **T003** can run in parallel during setup/foundational review
- After Phase 2, **T004** and **T006** can run in parallel because they touch different test files
- **T005** can run in parallel with **T006** because `AddAgentModal.tsx` and `AgentsPanel.test.tsx` are separate files
- **T012** and **T013** can run in parallel after implementation is complete

---

## Parallel Example: P1 Story Test Preparation

```bash
# After Phase 2, prepare the US1 and US2 regression tests in parallel:
Task: "T004 [US1] Add viewport alignment regression coverage in solune/frontend/src/components/agents/__tests__/AddAgentModal.test.tsx"
Task: "T006 [US2] Add section-order, Featured Agents removal, and Catalog Controls guard coverage in solune/frontend/src/components/agents/__tests__/AgentsPanel.test.tsx"
```

## Parallel Example: User Story 2

```bash
# Once T006 is in place, US2 implementation can proceed while US1 code lands separately:
Task: "T005 [US1] Update overlay alignment in solune/frontend/src/components/agents/AddAgentModal.tsx"
Task: "T007 [US2] Remove Featured Agents-only logic from solune/frontend/src/components/agents/AgentsPanel.tsx"
```

## Parallel Example: User Story 3

```bash
# US3 test prep can begin while final US1/US2 validation runs:
Task: "T009 [US3] Extend collapse-toggle coverage in solune/frontend/src/components/agents/__tests__/AgentsPanel.test.tsx"
Task: "T012 Run focused agent UI tests using scripts in solune/frontend/package.json"
```

---

## Implementation Strategy

### MVP First (Fastest Unblock)

1. Complete Phase 1 and Phase 2
2. Complete Phase 3 (User Story 1)
3. Validate the Add Agent modal fix with focused tests and manual viewport checks
4. Ship if the immediate blocker is modal accessibility

### Incremental Delivery

1. Finish Setup + Foundational
2. Deliver US1 for the modal viewport bug fix
3. Deliver US2 for the section reorder and Featured Agents cleanup
4. Deliver US3 for collapsible sections
5. Run the full validation phase and manual quickstart checklist

### Parallel Team Strategy

1. One developer handles **US1** in `AddAgentModal.tsx`
2. One developer prepares **US2** tests in `AgentsPanel.test.tsx`
3. After US2 lands, the same `AgentsPanel.tsx` owner implements **US3** to avoid merge conflicts

---

## Notes

- `[P]` tasks are safe to parallelize because they touch different files or run as independent validation steps
- All user-story tasks map directly to the approved scope in `specs/003-agents-page-ui/spec.md`
- No backend, schema, or persistence work is required for this feature
- Use `specs/003-agents-page-ui/quickstart.md` as the final manual verification checklist
