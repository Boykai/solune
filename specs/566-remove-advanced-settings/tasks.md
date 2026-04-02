# Tasks: Remove Advanced Settings from Settings Page

**Input**: Design documents from `/specs/566-remove-advanced-settings/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: No new tests required — this is a deletion/removal feature. Existing tests are updated to remove dead mocks per plan.md constitution check (Principle IV).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/frontend/src/` for frontend code, `solune/docs/` for documentation

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No project initialization needed — this is a removal feature in an existing codebase. Phase is empty.

*(No setup tasks — existing project structure is unchanged.)*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Edit SettingsPage to remove all AdvancedSettings references. This MUST be complete before deleting any component files, because the deleted files are still imported by SettingsPage until these edits are applied.

**⚠️ CRITICAL**: No file deletions (US2) can begin until this phase is complete — the project must compile after these edits.

- [ ] T001 Edit `solune/frontend/src/pages/SettingsPage.tsx` — remove the import of `AdvancedSettings` component
- [ ] T002 Edit `solune/frontend/src/pages/SettingsPage.tsx` — remove `useGlobalSettings` from the `useSettings` hook import (keep only `useUserSettings`)
- [ ] T003 Edit `solune/frontend/src/pages/SettingsPage.tsx` — remove the `GlobalSettingsUpdate` type import
- [ ] T004 Edit `solune/frontend/src/pages/SettingsPage.tsx` — remove the entire `useGlobalSettings()` hook call and its destructured variables (`globalSettings`, `globalLoading`, `updateGlobalSettings`, `isGlobalUpdating`)
- [ ] T005 Edit `solune/frontend/src/pages/SettingsPage.tsx` — remove `isGlobalUpdating` from the `useUnsavedChangesWarning(isUserUpdating || isGlobalUpdating)` call → `useUnsavedChangesWarning(isUserUpdating)`
- [ ] T006 Edit `solune/frontend/src/pages/SettingsPage.tsx` — remove the `handleGlobalSave` function definition
- [ ] T007 Edit `solune/frontend/src/pages/SettingsPage.tsx` — remove `globalLoading` from the loading condition → `if (userLoading)`
- [ ] T008 Edit `solune/frontend/src/pages/SettingsPage.tsx` — remove the global settings loading phase from `CelestialLoadingProgress`
- [ ] T009 Edit `solune/frontend/src/pages/SettingsPage.tsx` — remove the entire `<AdvancedSettings ... />` JSX block
- [ ] T010 Edit `solune/frontend/src/pages/SettingsPage.test.tsx` — remove the `useGlobalSettings` mock from the `vi.mock` block

**Checkpoint**: SettingsPage compiles cleanly (`npx tsc --noEmit`) and existing tests pass (`npm test`) with no references to AdvancedSettings or global settings.

---

## Phase 3: User Story 1 — Remove AdvancedSettings from SettingsPage (Priority: P1) 🎯 MVP

**Goal**: The Settings page renders only PrimarySettings, with no AdvancedSettings block and no global-settings-related code in SettingsPage.tsx.

**Independent Test**: Navigate to `/settings` in dev mode — only PrimarySettings renders, no console errors. Run `npx tsc --noEmit` and `npm test` — zero errors.

### Implementation for User Story 1

> All edits for US1 are captured in Phase 2 (Foundational) because they are blocking prerequisites. US1 is considered complete when Phase 2 finishes successfully.

*(No additional tasks — all US1 work is in Phase 2 above.)*

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. SettingsPage renders only PrimarySettings.

---

## Phase 4: User Story 2 — Delete Exclusively-Owned Component Files (Priority: P2)

**Goal**: All 11 files exclusively owned by AdvancedSettings and GlobalSettings are deleted from the repository. No dead code remains.

**Independent Test**: `ls solune/frontend/src/components/settings/` shows only retained files (PrimarySettings, SettingsSection, ProjectSettings, DynamicDropdown, McpSettings, SignalConnection, AIPreferences, and their tests). `npx tsc --noEmit` and `npm test` both pass.

### Implementation for User Story 2

- [ ] T011 [P] [US2] Delete `solune/frontend/src/components/settings/AdvancedSettings.tsx`
- [ ] T012 [P] [US2] Delete `solune/frontend/src/components/settings/DisplayPreferences.tsx`
- [ ] T013 [P] [US2] Delete `solune/frontend/src/components/settings/WorkflowDefaults.tsx`
- [ ] T014 [P] [US2] Delete `solune/frontend/src/components/settings/NotificationPreferences.tsx`
- [ ] T015 [P] [US2] Delete `solune/frontend/src/components/settings/GlobalSettings.tsx`
- [ ] T016 [P] [US2] Delete `solune/frontend/src/components/settings/AISettingsSection.tsx`
- [ ] T017 [P] [US2] Delete `solune/frontend/src/components/settings/DisplaySettings.tsx`
- [ ] T018 [P] [US2] Delete `solune/frontend/src/components/settings/WorkflowSettings.tsx`
- [ ] T019 [P] [US2] Delete `solune/frontend/src/components/settings/WorkflowSettings.test.tsx`
- [ ] T020 [P] [US2] Delete `solune/frontend/src/components/settings/NotificationSettings.tsx`
- [ ] T021 [P] [US2] Delete `solune/frontend/src/components/settings/globalSettingsSchema.ts`

**Checkpoint**: All 11 files deleted. `npx tsc --noEmit` passes with zero type errors. `npm test` passes. User Stories 1 AND 2 both work independently.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation updates to reflect the simplified Settings page.

- [ ] T022 Edit `solune/docs/pages/settings.md` — remove the "Advanced Settings" subsection and any references to display, workflow, notification, and global settings specific to the deleted components

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Empty — no project initialization needed
- **Foundational (Phase 2)**: No dependencies — can start immediately. BLOCKS all file deletions (US2)
- **User Story 1 (Phase 3)**: Satisfied by Phase 2 completion — no additional tasks
- **User Story 2 (Phase 4)**: Depends on Phase 2 (Foundational) completion — imports must be removed before files are deleted
- **Polish (Phase 5)**: Can run in parallel with Phase 4 — documentation is independent of code deletions

### User Story Dependencies

- **User Story 1 (P1)**: Implemented as foundational edits in Phase 2 — no dependencies on US2
- **User Story 2 (P2)**: Depends on US1 completion (Phase 2) — files cannot be deleted while still imported

### Within Each User Story

- US1: All edits target `SettingsPage.tsx` (single file, sequential edits) + one edit to `SettingsPage.test.tsx`
- US2: All deletions are independent files — all marked [P] for parallel execution

### Parallel Opportunities

- All Phase 2 edits to `SettingsPage.tsx` (T001–T009) must be sequential (same file)
- T010 (`SettingsPage.test.tsx`) can run in parallel with T001–T009 (different file)
- All Phase 4 deletions (T011–T021) can run in parallel (independent files, no dependencies between them)
- T022 (docs) can run in parallel with Phase 4 deletions

---

## Parallel Example: User Story 2

```bash
# Launch all file deletions for User Story 2 together (all [P]):
Task: "Delete solune/frontend/src/components/settings/AdvancedSettings.tsx"
Task: "Delete solune/frontend/src/components/settings/DisplayPreferences.tsx"
Task: "Delete solune/frontend/src/components/settings/WorkflowDefaults.tsx"
Task: "Delete solune/frontend/src/components/settings/NotificationPreferences.tsx"
Task: "Delete solune/frontend/src/components/settings/GlobalSettings.tsx"
Task: "Delete solune/frontend/src/components/settings/AISettingsSection.tsx"
Task: "Delete solune/frontend/src/components/settings/DisplaySettings.tsx"
Task: "Delete solune/frontend/src/components/settings/WorkflowSettings.tsx"
Task: "Delete solune/frontend/src/components/settings/WorkflowSettings.test.tsx"
Task: "Delete solune/frontend/src/components/settings/NotificationSettings.tsx"
Task: "Delete solune/frontend/src/components/settings/globalSettingsSchema.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (edit SettingsPage.tsx + SettingsPage.test.tsx)
2. **STOP and VALIDATE**: `npx tsc --noEmit` and `npm test` pass. Navigate to `/settings` — only PrimarySettings renders.
3. Deploy/demo if ready — Settings page is functional without AdvancedSettings.

### Incremental Delivery

1. Complete Phase 2 (Foundational) → SettingsPage no longer references AdvancedSettings (US1 complete, MVP!)
2. Complete Phase 4 (US2) → Dead code deleted → `tsc` and tests pass
3. Complete Phase 5 (Polish) → Documentation updated
4. Each phase adds cleanup value without breaking previous work

### Parallel Team Strategy

With multiple developers:

1. Developer A: Phase 2 edits (T001–T010) — blocking, do first
2. Once Phase 2 is done:
   - Developer A: Phase 4 file deletions (T011–T021, all parallel)
   - Developer B: Phase 5 documentation update (T022, independent)
3. All work integrates cleanly — no cross-dependencies after Phase 2

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Phase 2 tasks are NOT marked [P] because T001–T009 all edit the same file (`SettingsPage.tsx`)
- T010 edits a different file (`SettingsPage.test.tsx`) but is sequenced after T001–T009 for logical clarity
- No new tests needed — existing tests are updated to remove stale mocks (per constitution check)
- Commit after each phase to create clean rollback points
- Stop at any checkpoint to validate independently
