# Tasks: Replace Built-in Pipeline Presets

**Input**: Specification from `/home/runner/work/solune/solune/specs/001-replace-pipeline-presets/spec.md`  
**Prerequisites**: `spec.md` is available; `plan.md` is missing, so this task list is derived from the spec plus repository evidence in the backend and frontend preset files.  
**Tests**: Backend and frontend verification tasks are required by the spec/issue and are included below.  
**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependency)
- **[Story]**: User story label for traceability (`[US1]`, `[US2]`, `[US3]`, `[US4]`, `[US5]`)
- Every task below uses exact repository file paths

## Path Conventions

- **Backend**: `/home/runner/work/solune/solune/solune/backend`
- **Frontend**: `/home/runner/work/solune/solune/solune/frontend`
- **Spec assets**: `/home/runner/work/solune/solune/specs/001-replace-pipeline-presets`
- **Status naming convention**: Keep backend workflow status `StatusNames.IN_PROGRESS` / `In Progress` distinct from the frontend preset stage label `In progress`; the case difference is intentional and should be preserved.

---

## Phase 1: Setup (Shared Verification Setup)

**Purpose**: Establish the current preset contract, baseline regressions, and source-of-truth files before editing.

- [ ] T001 Run baseline backend preset regression coverage for /home/runner/work/solune/solune/solune/backend/tests/unit/test_pipeline_config.py, /home/runner/work/solune/solune/solune/backend/tests/unit/test_agent_tools.py, /home/runner/work/solune/solune/solune/backend/tests/unit/test_config.py, and /home/runner/work/solune/solune/solune/backend/tests/unit/test_api_pipelines.py
- [ ] T002 [P] Run baseline frontend preset regression coverage for /home/runner/work/solune/solune/solune/frontend/src/data/preset-pipelines.test.ts and /home/runner/work/solune/solune/solune/frontend/src/components/pipeline/PresetBadge.test.tsx
- [ ] T003 [P] Compare the target four-preset contract in /home/runner/work/solune/solune/solune/frontend/src/data/preset-pipelines.ts against the legacy backend definitions in /home/runner/work/solune/solune/solune/backend/src/services/pipelines/service.py before refactoring

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared preset infrastructure that must be aligned before story-specific work starts.

**⚠️ CRITICAL**: Complete this phase before implementing any user story.

- [ ] T004 Replace the shared preset-building contract in /home/runner/work/solune/solune/solune/backend/src/services/pipelines/service.py so built-in presets are generated as single-stage sequential pipelines
- [ ] T005 [P] Update the shared difficulty-to-preset mapping and fallback preset in /home/runner/work/solune/solune/solune/backend/src/services/pipelines/pipeline_config.py to target github, spec-kit, default, and app-builder
- [ ] T006 [P] Update the shared agent-tool preset defaults and fallbacks in /home/runner/work/solune/solune/solune/backend/src/services/agent_tools.py to stop referencing github-copilot, easy, medium, hard, and expert
- [ ] T007 Update shared agent display-name and default-status registries in /home/runner/work/solune/solune/solune/backend/src/constants.py for the new four-preset contract

**Checkpoint**: The backend now has one consistent preset contract that user stories can build on.

---

## Phase 3: User Story 1 - Backend–Frontend Preset Alignment (Priority: P1) 🎯 MVP

**Goal**: Seed exactly the same four presets in the backend that the frontend already defines.

**Independent Test**: Seed presets for a fresh project and verify the API returns exactly `github`, `spec-kit`, `default`, and `app-builder`, each with one `In progress` stage and one sequential group whose agent order matches `/home/runner/work/solune/solune/solune/frontend/src/data/preset-pipelines.ts`.

### Tests for User Story 1

- [ ] T008 [P] [US1] Add seed-presets assertions in /home/runner/work/solune/solune/solune/backend/tests/unit/test_api_pipelines.py for exactly four preset IDs, names, and single-stage layouts
- [ ] T009 [P] [US1] Use /home/runner/work/solune/solune/solune/frontend/src/data/preset-pipelines.test.ts as the unchanged frontend contract regression for the four target presets

### Implementation for User Story 1

- [ ] T010 [US1] Rewrite `_PRESET_DEFINITIONS` in /home/runner/work/solune/solune/solune/backend/src/services/pipelines/service.py to contain only github, spec-kit, default, and app-builder with frontend-matching names, descriptions, and ordered agents
- [ ] T011 [US1] Update stage, group, and agent node payloads in /home/runner/work/solune/solune/solune/backend/src/services/pipelines/service.py so every built-in preset uses one `In progress` stage with one sequential execution group
- [ ] T012 [US1] Extend `seed_presets()` in /home/runner/work/solune/solune/solune/backend/src/services/pipelines/service.py to clean up stale system presets with preset IDs `github-copilot`, `easy`, `medium`, `hard`, and `expert`

**Checkpoint**: User Story 1 is complete when backend seeding matches the frontend preset catalog exactly.

---

## Phase 4: User Story 2 - Difficulty-Based Preset Selection (Priority: P1)

**Goal**: Map every assessed difficulty to one of the four supported preset IDs and fall back to `default`.

**Independent Test**: Call the difficulty mapping helpers for `XS`, `S`, `M`, `L`, `XL`, empty, and unknown inputs and verify the results are `github`, `github`, `spec-kit`, `default`, `app-builder`, `default`, and `default`.

### Tests for User Story 2

- [ ] T013 [P] [US2] Update difficulty-map unit coverage in /home/runner/work/solune/solune/solune/backend/tests/unit/test_pipeline_config.py for XS/S→github, M→spec-kit, L→default, XL→app-builder, and fallback→default
- [ ] T014 [P] [US2] Update agent-tool difficulty selection coverage in /home/runner/work/solune/solune/solune/backend/tests/unit/test_agent_tools.py for assess_difficulty, select_pipeline_preset, create_project_issue, and launch_pipeline to expect the new preset IDs

### Implementation for User Story 2

- [ ] T015 [US2] Replace the legacy `DIFFICULTY_PRESET_MAP` and `"medium"` fallback in /home/runner/work/solune/solune/solune/backend/src/services/pipelines/pipeline_config.py with the new four-preset mapping
- [ ] T016 [US2] Replace legacy `DIFFICULTY_PRESET_MAP` values and `"medium"` session fallbacks in /home/runner/work/solune/solune/solune/backend/src/services/agent_tools.py with github, spec-kit, default, and app-builder
- [ ] T017 [US2] Update preset lookup and renamed GitHub preset expectations in /home/runner/work/solune/solune/solune/backend/tests/unit/test_api_pipelines.py so API-driven pipeline launches no longer query legacy preset IDs

**Checkpoint**: User Story 2 is complete when all automated preset-selection paths resolve only valid new preset IDs.

---

## Phase 5: User Story 3 - Agent Display Names and Default Mappings (Priority: P2)

**Goal**: Ensure every agent used by the four presets has a friendly display name. Align the fallback agent mapping to the backend workflow status constant `StatusNames.IN_PROGRESS` (value `In Progress`) while keeping the seeded preset stage label exactly `In progress` to match the frontend contract.

**Independent Test**:
- Every agent slug appearing in the four preset definitions has a non-empty entry in `AGENT_DISPLAY_NAMES`.
- `DEFAULT_AGENT_MAPPINGS` contains exactly one backend workflow status entry for `StatusNames.IN_PROGRESS` (value `In Progress`).
- That `StatusNames.IN_PROGRESS` mapping matches the `default` preset agent list even though the preset stage label remains the frontend-defined `In progress`.

### Tests for User Story 3

- [ ] T018 [P] [US3] Add agent display-name completeness and single-status default-mapping assertions in /home/runner/work/solune/solune/solune/backend/tests/unit/test_config.py

### Implementation for User Story 3

- [ ] T019 [US3] Add missing human-readable display names for architect, quality-assurance, tester, linter, and judge in /home/runner/work/solune/solune/solune/backend/src/constants.py
- [ ] T020 [US3] Simplify `DEFAULT_AGENT_MAPPINGS` in /home/runner/work/solune/solune/solune/backend/src/constants.py to a single `StatusNames.IN_PROGRESS` entry matching the `default` preset agent order
- [ ] T021 [US3] Update seeded preset agent display names in /home/runner/work/solune/solune/solune/backend/src/services/pipelines/service.py to use the same friendly labels exposed by /home/runner/work/solune/solune/solune/backend/src/constants.py

**Checkpoint**: User Story 3 is complete when every preset agent renders with a friendly name and the default mapping is reduced to one `In Progress` bucket.

---

## Phase 6: User Story 4 - Backward Compatibility for Customized Pipelines (Priority: P2)

**Goal**: Remove obsolete system presets without deleting or mutating customized pipelines derived from those presets.

**Independent Test**: Seed old preset rows plus a customized `is_preset=0` copy, rerun seeding, and verify the custom pipeline remains unchanged while obsolete system presets are removed or refreshed.

### Tests for User Story 4

- [ ] T022 [US4] Add reseeding regression coverage in /home/runner/work/solune/solune/solune/backend/tests/unit/test_api_pipelines.py proving stale `is_preset=1` legacy presets are cleaned up while `is_preset=0` customized pipelines remain untouched
- [ ] T023 [US4] Add repeated-seeding and stale-assignment regression coverage in /home/runner/work/solune/solune/solune/backend/tests/unit/test_api_pipelines.py for duplicate-prevention and removed preset fallback behavior

### Implementation for User Story 4

- [ ] T024 [US4] Scope preset cleanup inside `seed_presets()` in /home/runner/work/solune/solune/solune/backend/src/services/pipelines/service.py to delete only obsolete system-managed rows and preserve customized pipelines
- [ ] T025 [US4] Update preset-assignment fallback handling in /home/runner/work/solune/solune/solune/backend/src/services/pipelines/service.py so removed preset IDs are cleared or remapped safely during reseeding and assignment lookup

**Checkpoint**: User Story 4 is complete when legacy preset cleanup is lossless for user-owned pipeline configurations.

---

## Phase 7: User Story 5 - Frontend Remains Aligned (Priority: P3)

**Goal**: Keep the frontend preset source-of-truth unchanged while any preset-facing UI labels still match the four surviving preset IDs.

**Independent Test**: Run the existing frontend preset data tests unchanged and verify badge rendering works for `github`, `spec-kit`, `default`, and `app-builder` without reintroducing legacy preset IDs.

### Tests for User Story 5

- [ ] T026 [P] [US5] Re-run the unchanged frontend preset contract coverage in /home/runner/work/solune/solune/solune/frontend/src/data/preset-pipelines.test.ts after the backend preset refactor
- [ ] T027 [P] [US5] Update badge rendering coverage in /home/runner/work/solune/solune/solune/frontend/src/components/pipeline/PresetBadge.test.tsx for github, spec-kit, default, and app-builder while preserving unknown-preset fallback assertions

### Implementation for User Story 5

- [ ] T028 [US5] Remove legacy preset badge mappings from /home/runner/work/solune/solune/solune/frontend/src/components/pipeline/PresetBadge.tsx and keep only labels for github, spec-kit, default, and app-builder
- [ ] T029 [US5] Verify /home/runner/work/solune/solune/solune/frontend/src/data/preset-pipelines.ts remains unchanged and is still the backend parity contract for the four preset definitions

**Checkpoint**: User Story 5 is complete when the frontend preset data stays intact and UI preset labels reflect the same four IDs as the backend.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final regression, cleanup, and comment/documentation alignment across backend and frontend.

- [ ] T030 [P] Run focused backend verification in /home/runner/work/solune/solune/solune/backend/tests/unit/test_pipeline_config.py, /home/runner/work/solune/solune/solune/backend/tests/unit/test_agent_tools.py, /home/runner/work/solune/solune/solune/backend/tests/unit/test_config.py, and /home/runner/work/solune/solune/solune/backend/tests/unit/test_api_pipelines.py
- [ ] T031 [P] Run focused frontend verification in /home/runner/work/solune/solune/solune/frontend/src/data/preset-pipelines.test.ts and /home/runner/work/solune/solune/solune/frontend/src/components/pipeline/PresetBadge.test.tsx
- [ ] T032 Update stale inline comments and docstrings that still describe six legacy presets in /home/runner/work/solune/solune/solune/backend/src/services/pipelines/service.py and /home/runner/work/solune/solune/solune/backend/src/services/agent_tools.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies; can start immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1 and blocks all story work.
- **Phase 3 (US1)**: Depends on Phase 2; establishes the new four-preset contract and is the MVP.
- **Phase 4 (US2)**: Depends on Phase 3 because difficulty mappings must point at the finalized preset IDs.
- **Phase 5 (US3)**: Depends on Phase 3 because display-name coverage is defined by the finalized preset agent lists.
- **Phase 6 (US4)**: Depends on Phase 3 because backward-compatibility cleanup operates on the new preset catalog.
- **Phase 7 (US5)**: Depends on Phase 3; can run after the backend-supported preset IDs stabilize.
- **Phase 8 (Polish)**: Depends on completion of all desired user stories.

### User Story Dependencies

- **US1**: No story dependency after Foundational; this is the MVP and source-of-truth backend alignment step.
- **US2**: Uses the preset IDs introduced by US1.
- **US3**: Uses the agent lists finalized by US1.
- **US4**: Extends US1 seeding behavior to preserve customized pipelines during cleanup.
- **US5**: Verifies frontend alignment after US1 and can overlap with late US3/US4 validation.

### Within Each User Story

- Write/update the listed tests before changing implementation.
- Update backend preset definitions before changing drift cleanup or fallback logic.
- Keep frontend preset data file unchanged unless a failing regression proves otherwise.
- Finish each story’s independent test before moving to the next delivery checkpoint.

### Parallel Opportunities

- **Setup**: T002 and T003 can run in parallel with T001.
- **Foundational**: T005 and T006 can run in parallel after T004 starts the shared contract refactor.
- **US1**: T008 and T009 can run in parallel.
- **US2**: T013 and T014 can run in parallel.
- **US3**: T018 can run while implementation planning for T019-T021 is prepared.
- **US4**: No safe same-story parallel edits until the new reseeding tests in T022 and T023 finish because they both touch /home/runner/work/solune/solune/solune/backend/tests/unit/test_api_pipelines.py.
- **US5**: T026 and T027 can run in parallel.
- **Polish**: T030 and T031 can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Run backend and frontend alignment regressions in parallel:
Task: "T008 Add seed-presets assertions in /home/runner/work/solune/solune/solune/backend/tests/unit/test_api_pipelines.py"
Task: "T009 Use /home/runner/work/solune/solune/solune/frontend/src/data/preset-pipelines.test.ts as the unchanged frontend contract regression"
```

## Parallel Example: User Story 2

```bash
# Update difficulty-oriented test suites together:
Task: "T013 Update difficulty-map unit coverage in /home/runner/work/solune/solune/solune/backend/tests/unit/test_pipeline_config.py"
Task: "T014 Update agent-tool difficulty selection coverage in /home/runner/work/solune/solune/solune/backend/tests/unit/test_agent_tools.py"
```

## Execution Example: User Story 4 (Sequential)

```bash
# T022 and T023 are test tasks in the same file and must finish before implementation starts:
Task: "Finish T022 and T023 in /home/runner/work/solune/solune/solune/backend/tests/unit/test_api_pipelines.py"
Task: "Only after those tests are in place, start T024 and T025 in /home/runner/work/solune/solune/solune/backend/src/services/pipelines/service.py"
```

## Parallel Example: User Story 3

```bash
# Run config assertions while preparing constants changes:
Task: "T018 Add config assertions in /home/runner/work/solune/solune/solune/backend/tests/unit/test_config.py"
Task: "T019 Add missing display names in /home/runner/work/solune/solune/solune/backend/src/constants.py"
```

## Parallel Example: User Story 5

```bash
# Validate data and badge coverage together:
Task: "T026 Re-run /home/runner/work/solune/solune/solune/frontend/src/data/preset-pipelines.test.ts"
Task: "T027 Update /home/runner/work/solune/solune/solune/frontend/src/components/pipeline/PresetBadge.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1.
4. Validate that backend seeding now matches `/home/runner/work/solune/solune/solune/frontend/src/data/preset-pipelines.ts`.
5. Stop and demo the four-preset alignment before expanding scope.

### Incremental Delivery

1. Finish Setup + Foundational to remove legacy preset assumptions.
2. Deliver **US1** to establish the four-preset backend/frontend contract.
3. Deliver **US2** so automated difficulty selection points at the new preset IDs.
4. Deliver **US3** to expose friendly agent names and the single-status default mapping.
5. Deliver **US4** to prove reseeding is safe for customized pipelines.
6. Deliver **US5** to confirm frontend alignment and badge rendering after backend changes.
7. Run Phase 8 polish and focused regression suites.

### Parallel Team Strategy

1. One developer completes Phase 1 and Phase 2.
2. After US1 lands, split follow-up work:
   - Developer A: US2 difficulty mapping updates
   - Developer B: US3 display-name/default-mapping updates
   - Developer C: US4 backward-compatibility reseeding updates
   - Developer D: US5 frontend badge/regression verification
3. Rejoin for Phase 8 regression and cleanup.

---

## Notes

- `plan.md` was not available in `/home/runner/work/solune/solune/specs/001-replace-pipeline-presets`, so these tasks assume the current repository layout and existing preset-related test files are the implementation surface.
- The frontend preset data file `/home/runner/work/solune/solune/solune/frontend/src/data/preset-pipelines.ts` is treated as the contract for preset IDs, names, descriptions, stage shape, and agent ordering.
- The suggested MVP scope is **User Story 1** only.
