# Tasks: Fix Mutation Tests

**Input**: Design documents from `/specs/001-fix-mutation-tests/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED for this feature — FR-008 mandates deterministic assertions for survivor cleanup hooks, and SC-004 mandates an explicit test for the provider wrapper fix.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/`, `solune/frontend/`
- **CI workflows**: `.github/workflows/`
- **Documentation**: `solune/docs/`
- All paths relative to the repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No project initialization needed — this feature modifies existing infrastructure files across the monorepo.

No tasks. All changes are made to existing files in subsequent phases.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No separate foundational tasks. US1 (Phase 3) is the root backend blocker and serves as the foundational fix.

**⚠️ NOTE**: US1 must complete before US2 produces meaningful results. US3–US6 are frontend-scoped and can proceed independently of US1.

No tasks.

**Checkpoint**: Proceed directly to User Story phases.

---

## Phase 3: User Story 1 — Backend Mutation Shards Run Cleanly (Priority: P1) 🎯 MVP

**Goal**: Every backend mutation shard executes its full mutant set without aborting due to missing workspace files. The mutmut workspace includes the `templates/app-templates/` directory that `registry.py` resolves via `Path(__file__).resolve().parents[3]`.

**Independent Test**: Run each backend mutation shard locally with `python scripts/run_mutmut_shard.py --shard <name>`. Each completes without "not checked" aborts from missing assets and produces a survivor count per module.

### Implementation for User Story 1

- [ ] T001 [US1] Add `"../templates/"` to the `also_copy` list in the `[tool.mutmut]` section of `solune/backend/pyproject.toml` so that `solune/templates/app-templates/` is copied into the mutant workspace, preserving the relative path structure that `registry.py` and `template_files.py` resolve at runtime

**Details for T001**: The current `also_copy` list (lines 155–170 of `pyproject.toml`) contains entries for `src/` subdirectories. Append `"../templates/",` after the last entry. This fixes the root cause: `registry.py` resolves `Path(__file__).resolve().parents[3] / "templates" / "app-templates"` which, inside the mutant workspace, must find `templates/` at the correct relative position. The `../templates/` path is relative to `solune/backend/` (where `pyproject.toml` lives), pointing to `solune/templates/`.

**Checkpoint**: At this point, backend mutation shards should no longer abort on `test_agent_tools.py`. Verify by running: `cd solune/backend && uv run python -m pytest tests/unit/test_agent_tools.py -v -k "test_list_app_templates or test_get_app_template"`

---

## Phase 4: User Story 2 — Backend Shard–Workflow Alignment (Priority: P2)

**Goal**: The CI workflow runs exactly 5 backend mutation shards (matching the 5 defined in `run_mutmut_shard.py`), closing the coverage gap where the `api-and-middleware` shard was unintentionally omitted.

**Independent Test**: Compare the shard list in `.github/workflows/mutation-testing.yml` backend matrix against the `SHARDS` dictionary keys in `solune/backend/scripts/run_mutmut_shard.py`. Both must list: `auth-and-projects`, `orchestration`, `app-and-data`, `agents-and-integrations`, `api-and-middleware`.

### Implementation for User Story 2

- [ ] T002 [US2] Add `api-and-middleware` to the backend mutation shard matrix and configure its artifact upload step in `.github/workflows/mutation-testing.yml`

**Details for T002**: In the backend mutation job's `strategy.matrix.shard` array (currently lines 24–27), add `- api-and-middleware` after `- agents-and-integrations`. The artifact upload step already uses `${{ matrix.shard }}` in the artifact name, so no additional upload configuration is needed — the existing pattern automatically handles the new shard. Verify the shard name exactly matches the key `"api-and-middleware"` in the `SHARDS` dictionary of `solune/backend/scripts/run_mutmut_shard.py` (line 53).

**Checkpoint**: The CI workflow now defines 5 backend shard jobs. Verify with: `grep -A10 'matrix:' .github/workflows/mutation-testing.yml | head -15`

---

## Phase 5: User Story 3 — Frontend Mutation Sharding (Priority: P2)

**Goal**: The single frontend mutation job (which times out at ~71% of 6,580+ mutants) is replaced with 4 parallel shard jobs, each completing within the 3-hour CI time limit and producing a separate artifact.

**Independent Test**: Trigger the frontend mutation workflow and verify: (1) 4 shard jobs run, (2) each completes within the time limit, (3) the union of shard globs covers all files from the original `stryker.config.mjs` `mutate` array, (4) each shard uploads a named artifact.

### Implementation for User Story 3

- [ ] T003 [US3] Replace the single frontend mutation job with a 4-shard matrix strategy using per-shard `--mutate` CLI overrides and per-shard artifact uploads in `.github/workflows/mutation-testing.yml`

**Details for T003**: In the frontend mutation job section of the workflow, replace the current single-run approach with a matrix strategy using `include` entries. Each entry specifies a `shard` name and `mutate` glob string. The Stryker command becomes `npx stryker run --mutate '${{ matrix.mutate }}'`. Use these exact shard definitions from the contracts:

```yaml
strategy:
  fail-fast: false
  matrix:
    include:
      - shard: board-polling-hooks
        mutate: "src/hooks/useAdaptivePolling.ts,src/hooks/useBoardProjection.ts,src/hooks/useBoard*.ts,src/hooks/*Poll*.ts,!src/**/*.test.ts,!src/**/*.property.test.ts"
      - shard: data-query-hooks
        mutate: "src/hooks/useQuery*.ts,src/hooks/useMutation*.ts,src/hooks/use*Data*.ts,src/hooks/use*Fetch*.ts,!src/**/*.test.ts,!src/**/*.property.test.ts"
      - shard: general-hooks
        mutate: "src/hooks/**/*.ts,!src/hooks/useAdaptivePolling.ts,!src/hooks/useBoardProjection.ts,!src/hooks/useBoard*.ts,!src/hooks/*Poll*.ts,!src/hooks/useQuery*.ts,!src/hooks/useMutation*.ts,!src/hooks/use*Data*.ts,!src/hooks/use*Fetch*.ts,!src/**/*.test.ts,!src/**/*.property.test.ts"
      - shard: lib-utils
        mutate: "src/lib/**/*.ts,!src/**/*.test.ts,!src/**/*.property.test.ts"
```

Update the artifact upload step to use `stryker-report-${{ matrix.shard }}` as the artifact name and upload from `solune/frontend/reports/mutation/`. The base `stryker.config.mjs` remains unchanged — the `--mutate` CLI flag overrides the config-level `mutate` array while preserving reporters, thresholds, and other shared settings.

**Checkpoint**: The frontend mutation section of the workflow now defines 4 shard jobs. Each shard's glob excludes test files. The `general-hooks` shard explicitly excludes files covered by `board-polling-hooks` and `data-query-hooks` to prevent overlap.

**⚠️ Sync Coupling**: The `general-hooks` shard's exclusion list mirrors the inclusion globs of `board-polling-hooks` and `data-query-hooks`. If any shard's globs change, the `general-hooks` exclusions must be updated to match. T011 (Polish) validates this alignment.

---

## Phase 6: User Story 4 — Developer-Facing Focused Mutation Commands (Priority: P3)

**Goal**: Developers can target a single file or shard area for mutation testing without running the full suite, reducing the local feedback loop from hours to minutes.

**Independent Test**: Run `cd solune/frontend && npm run test:mutate:lib -- --dryRunOnly` and verify it completes successfully, targeting only `src/lib/**/*.ts` files.

### Implementation for User Story 4

- [ ] T004 [P] [US4] Add per-shard and single-file focused mutation npm scripts to `solune/frontend/package.json`

**Details for T004**: In the `"scripts"` section of `package.json`, after the existing `"test:mutate": "stryker run"` entry, add these scripts. The shard globs must exactly match the CI workflow matrix globs from T003:

```json
"test:mutate:file": "stryker run --mutate",
"test:mutate:hooks-board": "stryker run --mutate 'src/hooks/useAdaptivePolling.ts,src/hooks/useBoardProjection.ts,src/hooks/useBoard*.ts,src/hooks/*Poll*.ts,!src/**/*.test.ts,!src/**/*.property.test.ts'",
"test:mutate:hooks-data": "stryker run --mutate 'src/hooks/useQuery*.ts,src/hooks/useMutation*.ts,src/hooks/use*Data*.ts,src/hooks/use*Fetch*.ts,!src/**/*.test.ts,!src/**/*.property.test.ts'",
"test:mutate:hooks-general": "stryker run --mutate 'src/hooks/**/*.ts,!src/hooks/useAdaptivePolling.ts,!src/hooks/useBoardProjection.ts,!src/hooks/useBoard*.ts,!src/hooks/*Poll*.ts,!src/hooks/useQuery*.ts,!src/hooks/useMutation*.ts,!src/hooks/use*Data*.ts,!src/hooks/use*Fetch*.ts,!src/**/*.test.ts,!src/**/*.property.test.ts'",
"test:mutate:lib": "stryker run --mutate 'src/lib/**/*.ts,!src/**/*.test.ts,!src/**/*.property.test.ts'"
```

The `test:mutate:file` command accepts a file path argument via `--` (e.g., `npm run test:mutate:file -- 'src/hooks/useAdaptivePolling.ts'`). Backend focused runs already use `python scripts/run_mutmut_shard.py --shard <name>` — no new backend tooling needed, only documentation (covered in US7).

**⚠️ Sync Coupling**: The shard globs in these npm scripts must exactly match the corresponding CI workflow matrix globs from T003. If the CI shard definitions change, these scripts must be updated in lockstep. T011 (Polish) does not currently validate this — consider adding a comment in `package.json` referencing the CI workflow as the source of truth.

**Checkpoint**: `npm run` in the frontend directory shows all new mutation scripts. Each shard script uses the same base `stryker.config.mjs`.

---

## Phase 7: User Story 5 — Frontend Test-Utils Provider Bug Fix (Priority: P3)

**Goal**: The `renderWithProviders` function nests all providers correctly so that `{children}` is rendered exactly once in the DOM, fixing the confirmed double-render bug.

**Independent Test**: Render a component with `renderWithProviders` and assert it appears exactly once in the DOM.

### Tests for User Story 5

- [ ] T006 [US5] Add test asserting `renderWithProviders` renders children exactly once (not twice) in `solune/frontend/src/test/test-utils.test.tsx`

**Details for T006**: Create a new test file. Import `renderWithProviders` and `screen` from `@/test/test-utils`. Render a simple `<div data-testid="child">Hello</div>` component using `renderWithProviders`. Assert that `screen.getAllByTestId('child')` returns exactly 1 element (not 2). This test should FAIL before T005 is applied (confirming the double-render bug) and PASS after.

### Implementation for User Story 5

- [ ] T005 [P] [US5] Fix double-render provider nesting bug in the `Wrapper` function inside `renderWithProviders` in `solune/frontend/src/test/test-utils.tsx`

**Details for T005**: In the `Wrapper` function (around line 58), the current code renders `{children}` twice as siblings:

```tsx
// BROKEN — children rendered twice
<QueryClientProvider client={queryClient}>
  <ConfirmationDialogProvider>{children}</ConfirmationDialogProvider>
  <TooltipProvider delayDuration={0}>{children}</TooltipProvider>
</QueryClientProvider>
```

Fix by properly nesting providers so `{children}` appears exactly once:

```tsx
// FIXED — children rendered once
<QueryClientProvider client={queryClient}>
  <ConfirmationDialogProvider>
    <TooltipProvider delayDuration={0}>
      {children}
    </TooltipProvider>
  </ConfirmationDialogProvider>
</QueryClientProvider>
```

Provider order (outermost to innermost): `QueryClientProvider` → `ConfirmationDialogProvider` → `TooltipProvider`. After the fix, `grep -c '{children}' solune/frontend/src/test/test-utils.tsx` should return exactly 1 for the `Wrapper` function.

**Checkpoint**: The test from T006 passes. Run the full frontend test suite (`cd solune/frontend && npm test`) to verify no regressions from tests that may have accidentally relied on double-render behavior.

---

## Phase 8: User Story 6 — Mutation Survivor Cleanup for Key Frontend Hooks (Priority: P3)

**Goal**: Targeted mutation-killing tests close confirmed survivor gaps in `useAdaptivePolling` (tier transitions, visibility polls) and `useBoardProjection` (expansion ranges, batch sizes), adding deterministic assertions for behavioral edge cases.

**Independent Test**: Run `npm run test:mutate:hooks-board` (from US4) scoped to each hook file and verify the survivor count drops compared to the pre-fix baseline.

### Tests for User Story 6 (mandated by FR-008)

- [ ] T007 [P] [US6] Create deterministic tests for `useAdaptivePolling` covering tier transition boundaries, failure backoff thresholds, and visibility-triggered immediate poll behavior in `solune/frontend/src/hooks/useAdaptivePolling.test.ts`

**Details for T007**: Create a new test file. The `useAdaptivePolling` hook (in `solune/frontend/src/hooks/useAdaptivePolling.ts`, ~7.9 KB) manages adaptive polling with tier-based intervals. Tests must cover:

1. **Tier transition boundaries**: Assert exact interval values at each tier boundary (e.g., transitioning from fast to normal to slow polling based on activity thresholds). Test both upward and downward transitions.
2. **Failure backoff thresholds**: Assert that consecutive failures increase the polling interval and that recovery resets it. Test boundary values for the failure counter.
3. **Visibility-triggered immediate poll**: Assert that when `document.visibilityState` changes to `'visible'`, an immediate poll fires (not waiting for the next interval). Use `vi.spyOn(document, 'visibilityState', 'get')` and dispatch `visibilitychange` events.

Use `renderHook` from `@testing-library/react`, `vi.useFakeTimers()` for time control, and wrap in `QueryClientProvider` if the hook depends on React Query. Each test must make deterministic assertions on specific numeric boundaries (not just "greater than" or "less than").

- [ ] T008 [P] [US6] Create deterministic tests for `useBoardProjection` covering projection expansion ranges, batch size boundaries, and intersection observer cleanup in `solune/frontend/src/hooks/useBoardProjection.test.ts`

**Details for T008**: Create a new test file. The `useBoardProjection` hook (in `solune/frontend/src/hooks/useBoardProjection.ts`, ~8.0 KB) manages lazy-loading board content with intersection observers. Tests must cover:

1. **Projection expansion ranges**: Assert the exact viewport expansion factor and that items outside the expanded range are not projected. Test boundary items at the edge of the expansion window.
2. **Batch size boundaries**: Assert that batch loading respects the configured batch size. Test with exactly `batchSize`, `batchSize + 1`, and `batchSize - 1` items to kill boundary mutants.
3. **Intersection observer cleanup**: Assert that the `IntersectionObserver` is disconnected on unmount. Mock `IntersectionObserver` globally and verify `disconnect()` is called when the hook's component unmounts.

Use `renderHook` from `@testing-library/react`, mock `IntersectionObserver` with `vi.fn()`, and use `act()` to trigger observer callbacks. Each assertion must target a specific numeric value or exact function call to kill surviving mutants.

**Checkpoint**: Both test files pass with `npm test`. Survivor counts for these hooks decrease when running focused mutation tests.

---

## Phase 9: User Story 7 — Documentation and Changelog Updates (Priority: P3)

**Goal**: Testing documentation and changelog accurately describe the new shard layout, focused commands, and infrastructure fixes so developers can onboard without confusion.

**Independent Test**: Read `solune/docs/testing.md` and verify it documents all 5 backend shards, all 4 frontend shards, and focused mutation commands. Read `solune/CHANGELOG.md` and verify the infrastructure changes are listed under `[Unreleased]`.

### Implementation for User Story 7

- [ ] T009 [P] [US7] Update the mutation testing section to document all 5 backend shards, 4 frontend shards, focused mutation commands with examples, and the workspace parity fix in `solune/docs/testing.md`

**Details for T009**: The existing "Mutation Testing" section (around line 38) documents only 4 backend shards and has no frontend shard information. Updates required:

1. **Backend shards table**: Add a table listing all 5 shards with their module scopes:
   - `auth-and-projects`: `github_auth.py`, `completion_providers.py`, `model_fetcher.py`, `github_projects/`
   - `orchestration`: `workflow_orchestrator/`, `pipelines/`, `copilot_polling/`, `task_registry.py`, `pipeline_state_store.py`, `agent_tracking.py`
   - `app-and-data`: `app_service.py`, `guard_service.py`, `metadata_service.py`, `cache.py`, `database.py`, `done_items_store.py`, `chat_store.py`, `session_store.py`, `settings_store.py`, `mcp_store.py`, `cleanup_service.py`, `encryption.py`, `websocket.py`
   - `agents-and-integrations`: `ai_agent.py`, `agent_creator.py`, `github_commit_workflow.py`, `signal_bridge.py`, `signal_chat.py`, `signal_delivery.py`, `tools/`, `agents/`, `chores/`
   - `api-and-middleware`: `api/`, `middleware/`, `utils.py`

2. **Frontend shards section**: Add a new subsection documenting the 4 frontend shards (`board-polling-hooks`, `data-query-hooks`, `general-hooks`, `lib-utils`) with their mutate globs.

3. **Focused mutation commands**: Document per-shard npm scripts and the single-file command with examples:
   ```bash
   # Run mutations for a specific frontend shard
   cd solune/frontend && npm run test:mutate:hooks-board
   
   # Run mutations for a single file
   cd solune/frontend && npm run test:mutate:file -- 'src/hooks/useAdaptivePolling.ts'
   
   # Run a specific backend shard locally
   cd solune/backend && python scripts/run_mutmut_shard.py --shard api-and-middleware
   ```

4. **Quick Commands table**: Update the mutation entries to reference shard commands.

- [ ] T010 [P] [US7] Add mutation testing infrastructure changes entry under the `[Unreleased]` heading in `solune/CHANGELOG.md`

**Details for T010**: Add a new entry under the existing `## [Unreleased]` heading (line 5) with a `### Fixed` or `### Changed` subsection. Include:

- **Fixed**: Backend mutation workspace now includes `templates/` directory (all shards complete without missing-asset aborts)
- **Fixed**: Frontend test-utils `renderWithProviders` renders children exactly once (provider nesting bug)
- **Changed**: Backend CI mutation workflow runs all 5 defined shards (added `api-and-middleware`)
- **Changed**: Frontend mutation testing split into 4 CI shards (`board-polling-hooks`, `data-query-hooks`, `general-hooks`, `lib-utils`) to complete within the 3-hour time limit
- **Added**: Focused mutation commands in `package.json` for per-shard and single-file frontend mutation testing
- **Added**: Deterministic tests for `useAdaptivePolling` and `useBoardProjection` survivor gaps

**Checkpoint**: Documentation accurately reflects the final state of all configuration changes. No shard name discrepancies between docs and CI workflow.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Verification that all cross-artifact invariants hold and quality checks pass.

- [ ] T011 [P] Verify shard name parity: confirm the backend shard list in `.github/workflows/mutation-testing.yml` matches the `SHARDS` dictionary keys in `solune/backend/scripts/run_mutmut_shard.py` and the shard documentation in `solune/docs/testing.md` — all three sources must list identical shard names
- [ ] T012 [P] Run quickstart.md verification checklist from `specs/001-fix-mutation-tests/quickstart.md` — execute each verification command and confirm expected results

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Empty — no project initialization needed
- **Foundational (Phase 2)**: Empty — US1 serves as the root backend blocker
- **US1 (Phase 3)**: No dependencies — can start immediately. **ROOT BLOCKER for backend mutation results**
- **US2 (Phase 4)**: Depends on US1 (backend workspace must be fixed for shard runs to be meaningful)
- **US3 (Phase 5)**: No dependency on US1/US2 (frontend-scoped). Can start in parallel with Phase 3
- **US4 (Phase 6)**: Depends on US3 (shard glob definitions must be finalized before adding npm scripts)
- **US5 (Phase 7)**: No dependencies on other stories. Can start in parallel with any phase
- **US6 (Phase 8)**: Benefits from US5 (correct test environment) and US4 (focused commands for verification)
- **US7 (Phase 9)**: Depends on US2, US3, US4 (needs final shard layout and commands for accurate documentation)
- **Polish (Phase 10)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Independent — start immediately
- **US2 (P2)**: Depends on US1 (both modify backend mutation infrastructure)
- **US3 (P2)**: Independent of backend stories — can proceed in parallel with US1/US2
- **US4 (P3)**: Depends on US3 (needs shard definitions for npm scripts)
- **US5 (P3)**: Independent — can proceed at any time
- **US6 (P3)**: Best after US5 (correct test environment), benefits from US4 (focused verification)
- **US7 (P3)**: After US2 + US3 + US4 (documents their outputs)

### Within Each User Story

- Tests (T006, T007, T008) should be written to FAIL before implementation, then PASS after
- T005 (provider fix) must be applied before T006 (provider test) is verified as passing
- T007 and T008 (hook tests) are independent of each other and can run in parallel
- T009 and T010 (docs and changelog) are independent of each other and can run in parallel

### Parallel Opportunities

- **Cross-story**: US1 + US3 + US5 can all start simultaneously (different files, no dependencies)
- **Within US6**: T007 and T008 target different files — fully parallel
- **Within US7**: T009 (testing.md) and T010 (CHANGELOG.md) target different files — fully parallel
- **Within Polish**: T011 and T012 are read-only verification — fully parallel

### ⚠️ Serialization Constraint

T002 (US2) and T003 (US3) both modify `.github/workflows/mutation-testing.yml`. They MUST be applied sequentially (T002 before T003) to avoid merge conflicts in the same file.

---

## Parallel Example: Maximum Concurrency

```text
# Wave 1 — Start immediately (2 parallel tracks):
Track A: T001 [US1] Backend pyproject.toml fix
Track B: T005 [US5] Provider nesting fix in test-utils.tsx

# Wave 2 — After Wave 1 (serialized workflow edits, parallel with other files):
Track A: T002 [US2] Add api-and-middleware to mutation-testing.yml  ← MUST be before T003
Track B: T004 [US4] Add focused mutation scripts to package.json
Track C: T006 [US5] Add provider test in test-utils.test.tsx

# Wave 3 — After T002 completes (same file as T002, serialized):
Track A: T003 [US3] Frontend sharding in mutation-testing.yml  ← after T002 (same file)
Track B: T007 [US6] useAdaptivePolling tests  } parallel
Track C: T008 [US6] useBoardProjection tests  } parallel

# Wave 4 — After Wave 3 completes:
Track A: T009 [US7] Update testing.md  } parallel
Track B: T010 [US7] Update CHANGELOG.md  } parallel

# Wave 5 — Final verification:
Track A: T011 Shard parity check  } parallel
Track B: T012 Quickstart verification  } parallel
```

---

## Parallel Example: Sequential (Single Developer)

```text
# Follow priority order P1 → P2 → P3:
T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001: Backend workspace parity fix
2. **STOP and VALIDATE**: Run backend mutation shards — they should no longer abort
3. This single change unblocks all backend mutation reporting

### Incremental Delivery

1. T001 (US1) → Backend shards produce valid reports (MVP!)
2. T002 (US2) → All 5 backend shards covered in CI
3. T003 (US3) → Frontend shards complete within time limits
4. T004 (US4) → Developers have focused mutation commands
5. T005–T006 (US5) → Test environment correctness fix
6. T007–T008 (US6) → Survivor gaps closed with deterministic tests
7. T009–T010 (US7) → Documentation reflects reality
8. T011–T012 (Polish) → Cross-artifact invariants verified

### Parallel Team Strategy

With multiple developers:

1. **Developer A** (backend track): T001 → T002 → T009 (backend docs section)
2. **Developer B** (frontend CI track): T003 → T004 → T009 (frontend docs section)
3. **Developer C** (frontend quality track): T005 → T006 → T007 → T008
4. All reconvene for T010, T011, T012

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests (T006, T007, T008) should fail before their implementation counterparts are applied
- Commit after each task or logical group
- Stop at any checkpoint to validate the story independently
- The `stryker.config.mjs` base config is NOT modified — all shard-level overrides use `--mutate` CLI flags
- The `run_mutmut_shard.py` script already defines all 5 shards — no code changes needed there
- No mutation threshold is lowered and no source file is removed from scope (FR-011)
