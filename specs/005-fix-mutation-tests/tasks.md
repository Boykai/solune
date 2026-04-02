# Tasks: Fix Mutation Testing Infrastructure

**Input**: Design documents from `/specs/005-fix-mutation-tests/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/shard-matrix.md ✅, quickstart.md ✅

**Tests**: Tests are in scope — mutation testing infrastructure IS the feature. Verification tasks confirm that infrastructure changes produce working mutation reports. No new mutation-killer tests from current broken reports.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/`, `solune/frontend/`
- **CI**: `.github/workflows/`
- **Docs**: `solune/docs/`, `solune/CHANGELOG.md`

---

## Phase 1: Setup

**Purpose**: Verify current broken state and confirm preconditions before making changes

- [x] T001 Verify `templates/` is absent from `[tool.mutmut].also_copy` in solune/backend/pyproject.toml
- [x] T002 [P] Confirm `api-and-middleware` shard is defined in solune/backend/scripts/run_mutmut_shard.py but missing from .github/workflows/mutation-testing.yml backend matrix
- [x] T003 [P] Confirm frontend mutation-testing.yml runs a single monolithic Stryker job (no sharding) in .github/workflows/mutation-testing.yml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The `also_copy` fix is the single change that unblocks all backend mutation work

**⚠️ CRITICAL**: Backend user stories US1 and US2 cannot produce valid results until this phase is complete

- [x] T004 Add `"templates/"` to the `also_copy` list in `[tool.mutmut]` section of solune/backend/pyproject.toml

**Checkpoint**: Backend mutmut workspace now includes `templates/app-templates/` — backend mutation shards can produce real results

---

## Phase 3: User Story 1 — Backend mutmut workspace parity (Priority: P1) 🎯 MVP

**Goal**: Every backend mutation shard completes successfully, producing real kill/survivor reports instead of collapsing into "not checked" noise caused by missing app-template assets.

**Independent Test**: Run `python scripts/run_mutmut_shard.py --shard app-and-data --max-children 1` from `backend/` and confirm no "Templates directory does not exist" warning appears; report contains real kills and survivors.

### Implementation for User Story 1

- [x] T005 [US1] Verify `registry.py` path resolution works inside mutmut workspace — run `uv run pytest tests/unit/test_agent_tools.py -v -k "template"` from solune/backend to confirm normal pytest passes with the also_copy fix
- [x] T006 [US1] Verify `template_files.py` path resolution is unaffected by the new also_copy entry — run `uv run pytest tests/unit/test_template_files.py -v` from solune/backend
- [x] T007 [US1] Run a single backend mutation shard to verify templates are copied into mutant workspace — execute `uv run python scripts/run_mutmut_shard.py --shard app-and-data --max-children 1` from solune/backend and confirm the template-directory warning disappears
- [x] T008 [US1] Verify mutmut results contain real kills/survivors (not "not checked") — run `uv run python -m mutmut results` from solune/backend after T007

**Checkpoint**: Backend mutation workspace parity is restored — app-template tests pass under both pytest and mutmut

---

## Phase 4: User Story 2 — Backend shard drift resolution (Priority: P1)

**Goal**: The CI mutation workflow runs the same set of shards defined in `run_mutmut_shard.py`, so no shards are silently skipped.

**Independent Test**: Compare the shard list in `run_mutmut_shard.py` against `mutation-testing.yml` matrix entries; they must match exactly (5 shards).

### Implementation for User Story 2

- [x] T009 [US2] Add `api-and-middleware` to the backend mutation matrix in .github/workflows/mutation-testing.yml so CI runs all 5 shards defined in solune/backend/scripts/run_mutmut_shard.py
- [x] T010 [US2] Add `api-and-middleware` artifact upload step (pattern: `backend-mutation-report-api-and-middleware`) in .github/workflows/mutation-testing.yml
- [x] T011 [US2] Validate that the backend matrix shard list in .github/workflows/mutation-testing.yml exactly matches `SHARDS.keys()` in solune/backend/scripts/run_mutmut_shard.py (5 of 5)

**Checkpoint**: CI backend mutation matrix matches the shard script — no shards silently skipped

---

## Phase 5: User Story 3 — Frontend mutation sharding (Priority: P2)

**Goal**: Frontend mutation testing is split into 4 CI shards so each finishes well under the 3-hour timeout and produces an individual report artifact.

**Independent Test**: Run `npx stryker run -c stryker-hooks-board.config.mjs` from `frontend/` and confirm it completes and produces a shard-specific report.

### Implementation for User Story 3

- [x] T012 [P] [US3] Create solune/frontend/stryker-hooks-board.config.mjs extending base config with mutate globs for board/polling hooks: `src/hooks/useAdaptivePolling.ts`, `src/hooks/useBoardProjection.ts`, `src/hooks/useBoardRefresh.ts`, `src/hooks/useProjectBoard.ts`, `src/hooks/useRealTimeSync.ts`
- [x] T013 [P] [US3] Create solune/frontend/stryker-hooks-data.config.mjs extending base config with mutate globs for data/query hooks: `src/hooks/useProjects.ts`, `src/hooks/useChat.ts`, `src/hooks/useChatHistory.ts`, `src/hooks/useCommands.ts`, `src/hooks/useWorkflow.ts`, `src/hooks/useSettingsForm.ts`, `src/hooks/useAuth.ts`
- [x] T014 [P] [US3] Create solune/frontend/stryker-hooks-general.config.mjs extending base config with mutate glob `src/hooks/**/*.ts` minus board and data hooks (using negation patterns), excluding test files
- [x] T015 [P] [US3] Create solune/frontend/stryker-lib.config.mjs extending base config with mutate globs for `src/lib/**/*.ts`, excluding test and property test files
- [x] T016 [US3] Add frontend mutation shard matrix (hooks-board, hooks-data, hooks-general, lib) to .github/workflows/mutation-testing.yml with per-shard config file selection and artifact upload
- [x] T017 [US3] Verify union of all 4 shard mutate globs equals the original `stryker.config.mjs` mutate scope (`src/hooks/**/*.ts` + `src/lib/**/*.ts` minus test files)

**Checkpoint**: Frontend mutation is sharded into 4 parallel CI jobs — each producing its own report artifact

---

## Phase 6: User Story 4 — Frontend test-utils bug fix (Priority: P2)

**Goal**: `renderWithProviders()` in `test-utils.tsx` nests providers correctly instead of rendering `children` twice.

**Independent Test**: Inspect that `Wrapper` in `renderWithProviders` renders `children` exactly once, nested inside all providers.

### Implementation for User Story 4

- [x] T018 [US4] Fix `renderWithProviders()` in solune/frontend/src/test/test-utils.tsx — nest `TooltipProvider` inside `ConfirmationDialogProvider` so `{children}` is rendered exactly once instead of twice as sibling branches
- [x] T019 [US4] Run existing frontend test suite (`npm test` from solune/frontend) to confirm no regressions from the provider nesting fix

**Checkpoint**: `renderWithProviders()` renders components exactly once — existing tests pass

---

## Phase 7: User Story 5 — Developer-facing mutation commands and documentation (Priority: P3)

**Goal**: Developers have focused mutation commands in `package.json` and documentation in `testing.md` so local reproduction does not require re-running all 6,580 mutants or all backend modules.

**Independent Test**: Confirm `npm run test:mutate:hooks-board` resolves to `stryker run -c stryker-hooks-board.config.mjs` in `package.json`.

### Implementation for User Story 5

- [x] T020 [P] [US5] Add focused mutation scripts to solune/frontend/package.json: `test:mutate:hooks-board`, `test:mutate:hooks-data`, `test:mutate:hooks-general`, `test:mutate:lib` — each running `stryker run -c stryker-<shard>.config.mjs`
- [x] T021 [P] [US5] Update backend mutation section in solune/docs/testing.md to list all 5 shards (auth-and-projects, orchestration, app-and-data, agents-and-integrations, api-and-middleware) with run commands
- [x] T022 [P] [US5] Update frontend mutation section in solune/docs/testing.md to list all 4 Stryker shards with focused `npm run test:mutate:<shard>` commands and direct `npx stryker run` examples
- [x] T023 [US5] Add entries under `[Unreleased]` in solune/CHANGELOG.md for: backend mutmut workspace parity fix, 5th backend shard addition, frontend Stryker sharding, focused mutation commands, test-utils double-render fix

**Checkpoint**: Documentation and package.json reflect the complete shard layout and focused commands

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cross-cutting improvements

- [x] T024 [P] Validate shard-matrix.md contract — confirm `also_copy` includes `templates/`, backend CI matrix has 5 entries, frontend CI matrix has 4 entries, all artifact names follow the naming pattern per specs/005-fix-mutation-tests/contracts/shard-matrix.md
- [x] T025 [P] Run backend lint gates: `ruff check src tests && ruff format --check src tests && pyright src` from solune/backend
- [x] T026 [P] Run frontend lint and type-check gates: `npm run lint && npm run type-check && npm run type-check:test` from solune/frontend
- [x] T027 Run quickstart.md validation — execute the backend and frontend verification commands from specs/005-fix-mutation-tests/quickstart.md to confirm end-to-end workflow
- [x] T028 Final review: confirm no mutation threshold lowering, no permanent scope reduction, and all CI shard jobs are expected to upload artifacts

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — verification only, can start immediately
- **Foundational (Phase 2)**: Depends on Setup — the single `also_copy` fix that unblocks backend mutation
- **US1 (Phase 3)**: Depends on Foundational (Phase 2) — validates the workspace parity fix
- **US2 (Phase 4)**: Depends on Foundational (Phase 2) — can run in parallel with US1
- **US3 (Phase 5)**: No backend dependency — can start after Setup (Phase 1)
- **US4 (Phase 6)**: No backend dependency — can start after Setup (Phase 1)
- **US5 (Phase 7)**: Depends on US2 and US3 being finalized (needs final shard lists for docs)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

```text
Phase 1 (Setup)
    │
Phase 2 (Foundational: also_copy fix)
    ├──── Phase 3: US1 (backend parity validation) ─────┐
    ├──── Phase 4: US2 (backend shard drift) ────────────┤
    │                                                    ├── Phase 7: US5 (docs & commands)
Phase 1 ──── Phase 5: US3 (frontend sharding) ──────────┤        │
    │                                                    │        v
    └──── Phase 6: US4 (test-utils fix) ─────────────────┘   Phase 8 (Polish)
```

### Within Each User Story

- Verification tasks confirm the fix before moving to next story
- Configuration changes (pyproject.toml, workflow YAML, Stryker configs) before validation
- Infrastructure changes before documentation
- All changes validated before marking story complete

### Parallel Opportunities

- **Phase 1**: T002 and T003 can run in parallel (independent verification)
- **Phase 3–4**: US1 and US2 can run in parallel after Phase 2 (different files)
- **Phase 5**: T012, T013, T014, T015 can all run in parallel (independent config files)
- **Phase 5–6**: US3 and US4 can run in parallel (frontend sharding vs test-utils fix)
- **Phase 7**: T020, T021, T022 can run in parallel (different files)
- **Phase 8**: T024, T025, T026 can run in parallel (independent validation)

---

## Parallel Example: User Story 3

```bash
# Launch all Stryker shard configs in parallel (different files, no dependencies):
Task T012: "Create stryker-hooks-board.config.mjs"
Task T013: "Create stryker-hooks-data.config.mjs"
Task T014: "Create stryker-hooks-general.config.mjs"
Task T015: "Create stryker-lib.config.mjs"

# Then sequential: add CI matrix that references these configs
Task T016: "Add frontend mutation shard matrix to mutation-testing.yml"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verify current broken state)
2. Complete Phase 2: Foundational (`also_copy` fix in pyproject.toml)
3. Complete Phase 3: US1 (validate workspace parity)
4. **STOP and VALIDATE**: Run `test_agent_tools.py` under pytest and then run a mutmut shard — confirm template warning gone and real kills/survivors appear
5. This single fix unblocks all backend mutation work

### Incremental Delivery

1. Phase 1 + Phase 2 → Backend workspace parity fix applied
2. Add US1 → Validate fix locally → Backend mutation produces real results (MVP!)
3. Add US2 → CI runs all 5 backend shards → Backend CI complete
4. Add US3 → Frontend split into 4 shards → Frontend CI shards run
5. Add US4 → test-utils fix → Frontend test correctness improved
6. Add US5 → Docs and commands → Developer experience complete
7. Phase 8 → Final validation → All gates pass

### Parallel Team Strategy

With multiple developers:

1. Everyone: Complete Setup + Foundational together (1 line change)
2. Once Foundational is done:
   - Developer A: US1 (backend validation) + US2 (shard drift)
   - Developer B: US3 (frontend sharding) + US4 (test-utils fix)
3. After US1–US4: Developer A or B completes US5 (docs)
4. Final: Polish phase validation

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tasks** | 28 |
| **US1 tasks** | 4 (T005–T008) |
| **US2 tasks** | 3 (T009–T011) |
| **US3 tasks** | 6 (T012–T017) |
| **US4 tasks** | 2 (T018–T019) |
| **US5 tasks** | 4 (T020–T023) |
| **Setup tasks** | 3 (T001–T003) |
| **Foundational tasks** | 1 (T004) |
| **Polish tasks** | 5 (T024–T028) |
| **Parallel opportunities** | 6 groups (14 tasks parallelizable) |
| **MVP scope** | Phase 1 + Phase 2 + US1 (T001–T008) |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Tests are verification-focused (run existing tests in mutation context), not new mutation-killer test authoring
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- The `also_copy` fix (T004) is the single highest-leverage change — it unblocks all backend mutation work
