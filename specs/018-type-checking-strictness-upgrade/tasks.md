# Tasks: Type Checking Strictness Upgrade

**Input**: Design documents from `/specs/018-type-checking-strictness-upgrade/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: No new tests required per spec (Principle IV — Test Optionality). Existing tests must continue passing after every change.

**Organization**: Tasks are grouped by user story. US1 (backend source) is the MVP. US2 (backend tests) and US3 (frontend source) are independent P2 stories. US4 (frontend test casts) is P3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- All paths are relative to repository root (`solune/`)

## Path Conventions

- **Backend**: `solune/backend/src/`, `solune/backend/tests/`
- **Frontend**: `solune/frontend/src/`
- **Type stubs**: `solune/backend/src/typestubs/` (NEW)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create directory structure and configure pyright for type stubs

- [ ] T001 Create type stubs directory structure: `solune/backend/src/typestubs/copilot/generated/` and `solune/backend/src/typestubs/githubkit/`
- [ ] T002 [P] Add `stubPath = "src/typestubs"` to `[tool.pyright]` section in `solune/backend/pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No shared blockers — backend and frontend user stories are independent workstreams

**⚠️ NOTE**: Phase 1 (Setup) must complete before User Story 1 begins, since type stubs require the directory and pyright config. User Stories 3 and 4 (frontend) have no dependency on backend setup and can begin immediately — fully in parallel with Phase 1 and US1.

**Checkpoint**: Setup ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Backend Source Code Achieves Full Type Safety (Priority: P1) 🎯 MVP

**Goal**: Remove all 24 type suppression comments (15 `# type: ignore` + 9 `# pyright:` directives) from backend source files and resolve the underlying type issues. Fix at least one latent bug (missing `add()` method on `_NoOpInstrument`).

**Independent Test**: Run `cd solune/backend && uv run pyright src` with zero errors. Confirm `grep -rn "# type: ignore" src/` and `grep -rn "# pyright:" src/` return zero matches. All existing unit tests pass.

### Step 1: OTel Protocol Inheritance (4 suppressions)

- [ ] T003 [P] [US1] Add explicit protocol inheritance (`Tracer`, `Meter`, `SpanProcessor`) guarded by `TYPE_CHECKING`, add missing `add()` method to `_NoOpInstrument` (latent bug fix), and remove 4 `# type: ignore` comments in `solune/backend/src/services/otel_setup.py`

### Step 2: Pydantic Settings Construction (2 suppressions)

- [ ] T004 [P] [US1] Replace `Settings()` with `Settings.model_validate({})` and remove 2 `# type: ignore` in `solune/backend/src/config.py` and `solune/backend/src/main.py`

### Step 3: Copilot SDK Type Stubs (6 suppressions)

- [ ] T005 [P] [US1] Create copilot SDK type stubs (`__init__.pyi`, `types.pyi`, `generated/session_events.pyi`) in `solune/backend/src/typestubs/copilot/` per `specs/018-type-checking-strictness-upgrade/contracts/copilot-stubs.md`
- [ ] T006 [US1] Remove 6 `# type: ignore[reportMissingImports]` from copilot imports in `solune/backend/src/services/agent_provider.py`, `solune/backend/src/services/completion_providers.py`, and `solune/backend/src/services/plan_agent_provider.py`

### Step 4: reasoning_effort in Type Stubs (3 suppressions)

- [ ] T007 [US1] Include `reasoning_effort: str` directly in the copilot SDK `SessionConfig` stub and `agent_framework_github_copilot` `GitHubCopilotOptions` stub (no separate `ExtendedGitHubCopilotOptions` needed since we control the stubs). Remove 3 `# type: ignore[typeddict-unknown-key]` in `solune/backend/src/services/agent_provider.py`, `solune/backend/src/services/completion_providers.py`, and `solune/backend/src/services/plan_agent_provider.py`

### Step 5: slowapi + FastAPIInstrumentor Arg Types (2 suppressions)

- [ ] T008 [US1] Fix slowapi `RateLimitExceeded` handler signature (typed adapter or `cast()`) and resolve `FastAPIInstrumentor` arg-type after OTel protocol fix. Remove 2 `# type: ignore` in `solune/backend/src/main.py` and/or `solune/backend/src/services/otel_setup.py`

### Step 6: githubkit Type Stubs (9 suppressions)

- [ ] T009 [P] [US1] Create githubkit type stub with `Response[T]` and `GitHub` class in `solune/backend/src/typestubs/githubkit/__init__.pyi` per `specs/018-type-checking-strictness-upgrade/contracts/githubkit-stubs.md`
- [ ] T010 [US1] Remove 8 file-level `# pyright: reportAttributeAccessIssue = false` directives from `solune/backend/src/services/github_projects/board.py`, `repository.py`, `branches.py`, `agents.py`, `projects.py`, `copilot.py`, `issues.py`, `pull_requests.py` and 1 inline `# pyright: ignore[reportAttributeAccessIssue]` from `solune/backend/src/services/completion_providers.py`. Fix any new pyright errors with proper type annotations.

**Checkpoint**: Backend source type safety achieved — `uv run pyright src` passes with 0 errors and 0 suppression comments. All existing tests pass.

---

## Phase 4: User Story 2 — Backend Tests Are Type-Checked (Priority: P2)

**Goal**: Remove all 15+ `# type: ignore` comments from backend test files and upgrade the test pyright configuration from `"off"` to `"standard"` strictness mode.

**Independent Test**: Run `cd solune/backend && uv run pyright -p pyrightconfig.tests.json` with zero errors. Confirm `grep -rn "# type: ignore" tests/` returns zero matches. All existing tests pass.

**Dependency**: Step 2 (US1) solution pattern (`Settings.model_validate({})`) is reused in Step 9.

### Step 7: Frozen Dataclass Mutations (4 suppressions)

- [ ] T011 [P] [US2] Replace `result.field = value` with `object.__setattr__(result, "field", value)` or `dataclasses.replace()` and remove 4 `# type: ignore` in `solune/backend/tests/unit/test_agent_output.py`, `solune/backend/tests/unit/test_polling_loop.py`, `solune/backend/tests/unit/test_label_classifier.py`, and `solune/backend/tests/unit/test_transcript_detector.py`

### Step 8: Mock Method/Attribute Overrides (3 suppressions)

- [ ] T012 [P] [US2] Replace direct mock method/attribute assignments with `patch.object()` or `MagicMock(spec=..., attr=...)` and remove 3 `# type: ignore` in `solune/backend/tests/concurrency/test_transaction_safety.py` and `solune/backend/tests/unit/test_api_board.py`

### Step 9: Pydantic Settings in Tests (6 suppressions)

- [ ] T013 [P] [US2] Replace `Settings()` with `Settings.model_validate({})` and remove 6 `# type: ignore` in `solune/backend/tests/integration/test_production_mode.py`

### Step 10: Remaining Test Ignores (3+ suppressions)

- [ ] T014 [P] [US2] Fix remaining test suppressions: investigate `int(raw_delay)` runtime safety in `solune/backend/tests/unit/test_human_delay.py`, add proper return annotation in `solune/backend/tests/unit/test_pipeline_state_store.py`, use `getattr()` for dynamic module attributes in `solune/backend/tests/unit/test_run_mutmut_shard.py`. Remove all remaining `# type: ignore` comments.

### Step 11: Upgrade Test Pyright Mode

- [ ] T015 [US2] Change `typeCheckingMode` from `"off"` to `"standard"` in `solune/backend/pyrightconfig.tests.json`, remove `reportInvalidTypeForm: "none"`, add `reportMissingTypeStubs: false` and `reportMissingImports: "warning"`, add `"src/typestubs"` to `extraPaths`. Fix any new pyright errors surfaced by the strictness upgrade.

**Checkpoint**: Backend tests type-checked under standard mode — `uv run pyright -p pyrightconfig.tests.json` passes with 0 errors. All tests pass.

---

## Phase 5: User Story 3 — Frontend Source Code Achieves Full Type Safety (Priority: P2)

**Goal**: Remove all 7 type assertion workarounds (2 `@ts-expect-error` + 2 `as any` + 2 `eslint-disable` + 1 `as unknown as`) from frontend source files and replace with properly typed alternatives.

**Independent Test**: Run `cd solune/frontend && npm run type-check && npm run lint` with zero errors. Confirm no `as any`, `@ts-expect-error`, or type-related `eslint-disable` directives remain in `src/` (excluding test files). All existing tests pass.

### Step 12: useVoiceInput.ts — SpeechRecognitionWindow Interface (2 suppressions)

- [ ] T016 [P] [US3] Declare `SpeechRecognitionWindow` interface extending `Window` with optional `SpeechRecognition` and `webkitSpeechRecognition` constructors. Replace `window as any` cast and remove `eslint-disable-next-line @typescript-eslint/no-explicit-any` in `solune/frontend/src/hooks/useVoiceInput.ts`

### Step 13: lazyWithRetry.ts — Proper Generic Constraint (2 suppressions)

- [ ] T017 [P] [US3] Replace `ComponentType<any>` with `ComponentType<Record<string, unknown>>` or a properly constrained generic. Remove `eslint-disable` comment in `solune/frontend/src/lib/lazyWithRetry.ts`

### Step 14: api.ts — ThinkingEvent Type Guard (1 suppression)

- [ ] T018 [P] [US3] Add `isThinkingEvent(parsed: unknown): parsed is ThinkingEvent` type guard function and replace `parsed as unknown as ThinkingEvent` cast in `solune/frontend/src/services/api.ts`

### Step 15: test/setup.ts — Typed Shim Interfaces (2 suppressions)

- [ ] T019 [P] [US3] Declare typed shim interfaces (`CryptoShim`, `MockWebSocket`) and replace 2 `@ts-expect-error` comments with properly typed assignments in `solune/frontend/src/test/setup.ts`

**Checkpoint**: Frontend source type safety achieved — `npm run type-check` and `npm run lint` pass with 0 errors and 0 suppression directives in source files. All tests pass.

---

## Phase 6: User Story 4 — Frontend Test Type Casts Are Eliminated (Priority: P3)

**Goal**: Replace all 55 `as unknown as` casts across ~38 frontend test files with typed mock factory helpers or `satisfies Partial<T>` patterns.

**Independent Test**: Run `cd solune/frontend && npm run type-check:test && npm run test:coverage` with zero `as unknown as` casts remaining and all tests passing at current coverage levels.

### Step 16: Typed Mock Factory Helpers + Test Migration

- [ ] T020 [P] [US4] Create typed mock factory helpers (`mockFetchResponse<T>()`, `mockQueryResult<T>()`, etc.) in `solune/frontend/src/test/mockFactories.ts` covering the common `as unknown as` patterns across test files
- [ ] T021 [US4] Replace `as unknown as` casts with typed mock factories or `satisfies Partial<T>` across ~38 test files in `solune/frontend/src/hooks/__tests__/` and `solune/frontend/src/components/__tests__/`

**Checkpoint**: All frontend test casts eliminated — `npm run type-check:test` passes with zero `as unknown as` casts. All tests pass at current coverage.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and audit across all user stories

- [ ] T022 [P] Run full suppression audit: `grep` for remaining `# type: ignore`, `# pyright:`, `@ts-expect-error`, `as any`, `as unknown as`, `eslint-disable` across entire codebase — confirm zero matches
- [ ] T023 Run full validation suite per `specs/018-type-checking-strictness-upgrade/quickstart.md` Final Verification section: backend pyright (src + tests), pytest, ruff; frontend lint, type-check, build, test:coverage
- [ ] T024 [P] Run `specs/018-type-checking-strictness-upgrade/quickstart.md` step-by-step verification to confirm each step's independent validation passes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: No shared blockers — backend and frontend are independent
- **US1 — Backend Source (Phase 3)**: Depends on Setup (T001, T002) for type stubs directory and pyright config
- **US2 — Backend Tests (Phase 4)**: Depends on US1 Step 2 pattern (T004); Step 11 (T015) depends on Steps 7–10 (T011–T014)
- **US3 — Frontend Source (Phase 5)**: No dependency on backend phases — can start immediately or in parallel with US1
- **US4 — Frontend Tests (Phase 6)**: Depends on US3 completion (clean source baseline before migrating tests)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Setup — no dependencies on other stories. **This is the MVP.**
- **User Story 2 (P2)**: Reuses US1 Step 2 pattern (`Settings.model_validate({})`). Can start Steps 7, 8, 10 in parallel with US1; Step 9 (T013) reuses Step 2 (T004) pattern; Step 11 (T015) is the final gating task.
- **User Story 3 (P2)**: Fully independent of backend stories — can start immediately. All 4 tasks are parallel.
- **User Story 4 (P3)**: Depends on US3 completion. T021 depends on T020.

### Within Each User Story

- Steps within a story follow the dependency graph from `data-model.md`
- Tasks marked [P] within a step can run simultaneously
- Core infrastructure (stubs, config) before file-level fixes
- Each step's verification must pass before claiming the step complete

### Internal Task Dependencies (US1)

```
T001 (dirs) + T002 (config) ─── Setup complete
        │
        ├── T003 [P] (OTel protocols) ──────────────┐
        ├── T004 [P] (Settings) ────────────────────┤
        ├── T005 [P] (copilot stubs) → T006, T007   ├── T008 (slowapi — depends on T003 + T004)
        └── T009 [P] (githubkit stub) → T010        │
                                                     │
                                         US1 complete ✓
```

### Internal Task Dependencies (US2)

```
T011 [P] (frozen dataclass) ──┐
T012 [P] (mock overrides)    ├── T015 (pyright "standard" — depends on all T011–T014)
T013 [P] (Settings tests)  ──┤
T014 [P] (remaining tests) ──┘
                               │
                    US2 complete ✓
```

### Parallel Opportunities

- **Setup**: T001 and T002 can run in parallel
- **US1**: T003, T004, T005, T009 can all run in parallel (different files). After stubs: T006 → T007 sequential. After protocols + settings: T008 sequential.
- **US2**: T011, T012, T013, T014 can all run in parallel (different test files). T015 sequential after all.
- **US3**: All 4 tasks (T016–T019) can run fully in parallel (different files)
- **US4**: T020 first (new file), then T021 (migration)
- **Cross-story**: US1 and US3 can run fully in parallel (backend vs frontend). US2 can partially overlap with US1.

---

## Parallel Example: User Story 1

```bash
# Launch all independent Step 1/2/3/6 tasks together:
Task T003: "OTel protocol inheritance in solune/backend/src/services/otel_setup.py"
Task T004: "Settings.model_validate({}) in solune/backend/src/config.py and main.py"
Task T005: "Copilot SDK stubs in solune/backend/src/typestubs/copilot/"
Task T009: "githubkit stub in solune/backend/src/typestubs/githubkit/__init__.pyi"

# After stubs are created, remove suppression comments:
Task T006: "Remove copilot import ignores in agent_provider.py, completion_providers.py, plan_agent_provider.py"
Task T010: "Remove githubkit pyright directives in github_projects/*.py and completion_providers.py"

# After imports are clean, add extended types:
Task T007: "ExtendedGitHubCopilotOptions in agent_provider.py, completion_providers.py, plan_agent_provider.py"

# After protocols + settings are fixed:
Task T008: "slowapi + FastAPIInstrumentor in main.py and otel_setup.py"
```

## Parallel Example: User Story 3

```bash
# All 4 frontend source tasks can run simultaneously:
Task T016: "SpeechRecognitionWindow in solune/frontend/src/hooks/useVoiceInput.ts"
Task T017: "Generic constraint in solune/frontend/src/lib/lazyWithRetry.ts"
Task T018: "ThinkingEvent type guard in solune/frontend/src/services/api.ts"
Task T019: "Typed shims in solune/frontend/src/test/setup.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 3: User Story 1 — Backend Source (T003–T010)
3. **STOP and VALIDATE**: Run `uv run pyright src` — must be 0 errors, 0 suppressions
4. All existing tests must still pass
5. Deploy/demo: Backend source code is now fully type-safe

### Incremental Delivery

1. Complete Setup → Infrastructure ready
2. Add User Story 1 (backend source) → Test independently → **MVP!** (24 suppressions removed)
3. Add User Story 2 (backend tests) → Test independently → Backend fully type-safe (15+ more suppressions removed, pyright upgraded to standard)
4. Add User Story 3 (frontend source) → Test independently → Frontend source type-safe (7 suppressions removed)
5. Add User Story 4 (frontend tests) → Test independently → All suppressions eliminated (55 casts removed)
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup together (Phase 1)
2. Once Setup is done:
   - **Developer A**: User Story 1 (backend source — P1 MVP)
   - **Developer B**: User Story 3 (frontend source — P2, fully independent)
3. After US1 completes:
   - **Developer A**: User Story 2 (backend tests — P2, depends on US1 patterns)
4. After US3 completes:
   - **Developer B**: User Story 4 (frontend tests — P3, depends on US3)
5. Stories complete and integrate independently

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tasks** | 24 |
| **Setup tasks** | 2 (T001–T002) |
| **US1 tasks (P1 — MVP)** | 8 (T003–T010) |
| **US2 tasks (P2)** | 5 (T011–T015) |
| **US3 tasks (P2)** | 4 (T016–T019) |
| **US4 tasks (P3)** | 2 (T020–T021) |
| **Polish tasks** | 3 (T022–T024) |
| **Parallel opportunities** | 14 tasks marked [P] |
| **Suppressions resolved** | ~104 total (24 backend source + 15+ backend test + 7 frontend source + 55 frontend test) |
| **Latent bugs fixed** | ≥1 (missing `add()` on `_NoOpInstrument`) |
| **MVP scope** | Setup + User Story 1 = 10 tasks |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- No new tests are added (per spec) — existing tests must continue passing
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- All type stubs are intentionally minimal — only imported symbols are stubbed
