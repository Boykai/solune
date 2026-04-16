# Tasks: Remove Lint/Test Ignores & Fix Discovered Bugs

**Input**: Design documents from `/specs/003-remove-lint-ignores/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The specification explicitly mandates running all existing test suites at stricter settings and adding tests for discovered bugs (FR-034, SC-010). Test tasks are included where new coverage is required.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. User stories map to plan phases: US1=Backend, US2=Frontend, US3=E2E, US4=Infrastructure, US5=Policy, US6=Verification.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `solune/backend/src/`, `solune/backend/tests/`
- **Frontend**: `solune/frontend/src/`, `solune/frontend/e2e/`
- **Infrastructure**: `infra/modules/`
- **CI/Scripts**: `solune/scripts/`, `solune/.pre-commit-config.yaml`

---

## Phase 1: Setup

**Purpose**: Dedicated branch and workspace initialization

- [ ] T001 Create dedicated branch from `main` and verify clean working tree
- [ ] T002 Install backend dependencies: `cd solune/backend && uv sync --locked --extra dev`
- [ ] T003 [P] Install frontend dependencies: `cd solune/frontend && npm ci`

---

## Phase 2: Foundational — Baseline Capture

**Purpose**: Record current green state for all checks before any suppression changes. All user story work depends on this baseline.

**⚠️ CRITICAL**: No suppression removal can begin until baseline is captured and recorded.

- [ ] T004 Capture backend baseline: run `ruff check`, `ruff format --check`, `bandit -r src/ --skip B104,B608`, `pyright src`, `pytest --cov` in `solune/backend/` and record results
- [ ] T005 [P] Capture frontend baseline: run `npm run lint`, `npm run type-check`, `npm run type-check:test`, `npm run test:coverage`, `npm run build` in `solune/frontend/` and record results
- [ ] T006 [P] Capture E2E baseline: run `npx playwright test` in `solune/frontend/` and record results
- [ ] T007 [P] Capture infrastructure baseline: run `az bicep build --file main.bicep` in `infra/` and record results
- [ ] T008 Record baseline suppression counts per category (50 backend, 20+4 frontend, 6 E2E, 3 infra) as documented in `specs/003-remove-lint-ignores/research.md`

**Checkpoint**: Baseline recorded — suppression removal can now begin

---

## Phase 3: User Story 1 — Backend Suppression Cleanup (Priority: P1) 🎯 MVP

**Goal**: Remove all non-essential lint, type-check, and coverage suppressions from the backend, fix any bugs discovered, and tighten configuration strictness.

**Independent Test**: Run `ruff check src tests`, `pyright src`, `bandit -r src/ --skip B104`, `pytest --cov` in `solune/backend/` — all must pass at stricter settings with zero new unjustified suppressions.

### 1.1 — Bandit B608 Removal (HIGH PRIORITY — security)

- [ ] T009 [US1] Remove `B608` from Bandit `skips` list in `solune/backend/pyproject.toml`
- [ ] T010 [US1] Run `bandit -r src/ -ll -ii --skip B104` to identify all flagged SQL paths in `solune/backend/src/`
- [ ] T011 [US1] Audit and parameterize any unsafe SQL queries discovered by Bandit B608 removal in `solune/backend/src/`
- [ ] T012 [US1] Verify Bandit passes cleanly: `bandit -r src/ -ll -ii --skip B104` in `solune/backend/`

### 1.2 — Type Ignore Removal

- [ ] T013 [P] [US1] Replace `# type: ignore[reportGeneralTypeIssues]` in `solune/backend/src/services/agent_provider.py` with typed approach (TypedDict or `cast()`)
- [ ] T014 [P] [US1] Replace `# type: ignore[reportGeneralTypeIssues]` in `solune/backend/src/services/plan_agent_provider.py` with typed approach (TypedDict or `cast()`)
- [ ] T015 [P] [US1] Add `reason: intentional frozen dataclass mutation in pytest.raises(FrozenInstanceError) test` to 3 `# type: ignore[misc]` markers in `solune/backend/tests/unit/test_mcp_server/test_context.py`
- [ ] T016 [US1] Verify Pyright passes: `pyright src` in `solune/backend/`

### 1.3 — Noqa Removal

- [ ] T017 [P] [US1] Add `reason: FastAPI Depends() pattern — evaluated per-request, not at import time` to all 12 `# noqa: B008` markers in `solune/backend/src/api/chat.py`, `solune/backend/src/api/activity.py`, and `solune/backend/src/api/cleanup.py`
- [ ] T018 [P] [US1] Evaluate and fix `# noqa: B009` markers (getattr usage) in `solune/backend/tests/unit/test_run_mutmut_shard.py` — replace with direct attribute access if possible
- [ ] T019 [P] [US1] Evaluate and fix `# noqa: B010` markers (setattr on frozen models) in `solune/backend/tests/unit/test_polling_loop.py`, `test_label_classifier.py`, `test_transcript_detector.py`, and `test_agent_output.py` — use `object.__setattr__` or test helper if appropriate
- [ ] T020 [US1] Remove `# noqa: E402` by restructuring imports in `solune/backend/src/services/github_projects/__init__.py`
- [ ] T021 [P] [US1] Replace `# noqa: F401` with explicit `__all__` list in `solune/backend/src/models/chat.py`
- [ ] T022 [P] [US1] Replace `# noqa: F401` with explicit `__all__` list in `solune/backend/src/services/copilot_polling/__init__.py`
- [ ] T023 [P] [US1] Replace `# noqa: F401` in `solune/backend/tests/unit/test_build_smoke.py` with explicit `__all__` or direct usage
- [ ] T024 [US1] Evaluate PTH118/PTH119 usage in `solune/backend/src/api/chat.py` and migrate `os.path.basename`/`os.path.normpath` to `pathlib` equivalents where safe (preserve CodeQL sanitizer semantics)
- [ ] T025 [P] [US1] Add `reason: intentional Unicode test data` to `# noqa: RUF001` in `solune/backend/tests/unit/test_recommendation_models.py`
- [ ] T026 [US1] Verify Ruff passes: `ruff check src tests` in `solune/backend/`

### 1.4 — Pragma No Cover Removal

- [ ] T027 [P] [US1] Remove `# pragma: no cover` in `solune/backend/tests/unit/test_main.py` by adding test coverage for the `RuntimeError` branch
- [ ] T028 [P] [US1] Remove `# pragma: no cover` in `solune/backend/tests/unit/test_database.py` by adding test coverage for the `patched_execute` callback paths
- [ ] T029 [P] [US1] Evaluate `# pragma: no cover` in `solune/backend/tests/unit/test_chat_agent.py` — retain with `reason: yield makes function an async generator; unreachable by design` if dead code by design, or delete dead code
- [ ] T030 [US1] Verify coverage improvement: `pytest --cov=src --cov-report=term-missing` in `solune/backend/`

### 1.5 — Skipif Replacement

- [ ] T031 [US1] Replace `@pytest.mark.skipif(...)` in `solune/backend/tests/unit/test_run_mutmut_shard.py` with a fixture that ensures the CI workflow file exists or creates a minimal fixture
- [ ] T032 [US1] Verify the previously-skipped test runs successfully in `solune/backend/`

### 1.6 — Config Tightening

- [ ] T033 [US1] Remove `E501` from Ruff `ignore` list in `solune/backend/pyproject.toml` and fix any resulting long-line violations
- [ ] T034 [US1] Change `reportMissingImports` from `"warning"` to `"error"` in `solune/backend/pyproject.toml`
- [ ] T035 [US1] Dry-run `reportMissingTypeStubs = true` in `solune/backend/pyproject.toml` — if too many stubs needed, defer with documented reason and revert
- [ ] T036 [US1] Review coverage `exclude_lines` in `solune/backend/pyproject.toml` — keep `if TYPE_CHECKING:` and `if __name__ == .__main__.` (standard), remove any others
- [ ] T037 [US1] Run full backend verification: `ruff check src tests && ruff format --check src tests && bandit -r src/ -ll -ii --skip B104 && pyright src && pytest --cov=src --cov-report=term-missing` in `solune/backend/`

**Checkpoint**: Backend suppression cleanup complete — all backend checks pass at stricter settings

---

## Phase 4: User Story 2 — Frontend Suppression Cleanup (Priority: P1)

**Goal**: Remove all non-essential ESLint, TypeScript, and mutation-testing suppressions from the frontend, fix stale-closure bugs and accessibility violations.

**Independent Test**: Run `npm run lint -- --max-warnings=0`, `npm run type-check`, `npm run type-check:test`, `npm run test:coverage`, `npm run build` in `solune/frontend/` — all must pass.

### 2.1 — React Hooks Exhaustive Deps (6 instances)

- [ ] T038 [P] [US2] Fix `react-hooks/exhaustive-deps` suppression in `solune/frontend/src/components/chat/ChatInterface.tsx` — add missing dependencies or use `useCallback` for stable reference
- [ ] T039 [P] [US2] Fix `react-hooks/exhaustive-deps` suppression in `solune/frontend/src/components/agents/AgentChatFlow.tsx` — replace empty `[]` dep with proper dependencies or wrap in `useCallback`
- [ ] T040 [P] [US2] Fix `react-hooks/exhaustive-deps` suppression in `solune/frontend/src/components/chores/ChoreChatFlow.tsx` — replace empty `[]` dep with proper dependencies or wrap in `useCallback`
- [ ] T041 [P] [US2] Fix `react-hooks/exhaustive-deps` suppression in `solune/frontend/src/components/pipeline/ModelSelector.tsx` — add missing ref dependencies or restructure `useMemo`
- [ ] T042 [P] [US2] Fix `react-hooks/exhaustive-deps` suppression in `solune/frontend/src/components/tools/UploadMcpModal.tsx` — add missing dependencies to the effect
- [ ] T043 [P] [US2] Evaluate `react-hooks/exhaustive-deps` suppression in `solune/frontend/src/hooks/useRealTimeSync.ts` — retain with updated `reason:` if justification is still valid, otherwise fix

### 2.2 — No Explicit Any (2 instances)

- [ ] T044 [P] [US2] Replace `@typescript-eslint/no-explicit-any` in `solune/frontend/src/hooks/useVoiceInput.ts` with typed `SpeechRecognition` / `webkitSpeechRecognition` interface
- [ ] T045 [P] [US2] Replace `@typescript-eslint/no-explicit-any` in `solune/frontend/src/lib/lazyWithRetry.ts` with proper generic bound (e.g., `ComponentType<Record<string, unknown>>`)

### 2.3 — Set State in Effect

- [ ] T046 [US2] Refactor `react-hooks/set-state-in-effect` suppression in `solune/frontend/src/hooks/useChatPanels.ts` — use lazy state initialization (`useState(() => ...)`) or `useRef` + sync update instead of `setState` inside `useEffect`

### 2.4 — JSX A11y (8 instances)

- [ ] T047 [P] [US2] Fix `jsx-a11y` autoFocus suppression in `solune/frontend/src/components/chores/AddChoreModal.tsx` — replace `autoFocus` with imperative `useRef` + `useEffect(() => ref.current?.focus())` pattern
- [ ] T048 [P] [US2] Fix `jsx-a11y` autoFocus suppression in `solune/frontend/src/components/board/AddAgentPopover.tsx` — replace `autoFocus` with imperative focus handling
- [ ] T049 [P] [US2] Fix `jsx-a11y` click-on-non-interactive suppression in `solune/frontend/src/components/agents/AgentIconPickerModal.tsx` — convert to `<button>` or add `onKeyDown` handler (Enter/Space)
- [ ] T050 [P] [US2] Fix 2 `jsx-a11y` click-on-non-interactive suppressions in `solune/frontend/src/components/board/AgentPresetSelector.tsx` — convert to `<button>` or add keyboard handlers
- [ ] T051 [P] [US2] Fix 3 `jsx-a11y` click-on-non-interactive suppressions in `solune/frontend/src/components/agents/AddAgentModal.tsx` — convert to `<button>` or add keyboard handlers

### 2.5 — TS Expect Error (2 instances)

- [ ] T052 [P] [US2] Replace `@ts-expect-error` crypto shim in `solune/frontend/src/test/setup.ts` with typed partial: `globalThis.crypto = {} as Crypto`
- [ ] T053 [P] [US2] Replace `@ts-expect-error` WebSocket mock in `solune/frontend/src/test/setup.ts` with proper `MockWebSocket` implementing the `WebSocket` interface

### 2.6 — Rules of Hooks Disable

- [ ] T054 [US2] Remove file-wide `/* eslint-disable react-hooks/rules-of-hooks */` in `solune/frontend/e2e/fixtures.ts` by renaming helper functions so they do not start with `use` prefix (Playwright fixtures are not React hooks)

### 2.7 — Stryker Config

- [ ] T055 [US2] Change `ignoreStatic: true` to `ignoreStatic: false` in `solune/frontend/stryker.config.mjs`
- [ ] T056 [US2] Run `npm run test:mutation` in `solune/frontend/`, identify surviving mutants, and close gaps by adding or improving tests

### 2.8 — TSConfig Test Strictness

- [ ] T057 [US2] Change `noUnusedLocals` and `noUnusedParameters` to `true` in `solune/frontend/tsconfig.test.json`
- [ ] T058 [US2] Fix all unused variable/parameter errors revealed by tsconfig strictness (prefix with `_` or remove) across `solune/frontend/src/` test files

### 2.9 — ESLint Config Audit

- [ ] T059 [US2] Audit `solune/frontend/eslint.config.js` — evaluate rules set to `warn` or `off` and promote appropriate ones to `error` (document reason for keeping `security/detect-object-injection: 'off'`)
- [ ] T060 [US2] Fix all lint issues revealed by ESLint rule promotion in `solune/frontend/src/`
- [ ] T061 [US2] Run full frontend verification: `npm run lint -- --max-warnings=0 && npm run type-check && npm run type-check:test && npm run test:coverage && npm run build` in `solune/frontend/`

**Checkpoint**: Frontend suppression cleanup complete — all frontend checks pass at stricter settings

---

## Phase 5: User Story 3 — E2E Test Skip Cleanup (Priority: P2)

**Goal**: Replace dynamic `test.skip()` calls with structured environment-based test wiring so tests are transparently included or excluded by configuration.

**Independent Test**: Run Playwright test suite and verify correct tests run based on configuration rather than runtime skip checks.

### 3.1 — Replace Dynamic Skips

- [ ] T062 [P] [US3] Replace 2 dynamic `test.skip()` calls in `solune/frontend/e2e/integration.spec.ts` with Playwright project configuration that conditionally includes integration tests based on backend availability
- [ ] T063 [P] [US3] Replace 4 dynamic `test.skip()` calls in `solune/frontend/e2e/project-load-performance.spec.ts` with tag-driven filtering or dedicated Playwright project with `testMatch` and prerequisites

### 3.2 — Document Playwright Config

- [ ] T064 [US3] Add explanatory comment for `testIgnore: ['**/save-auth-state.ts']` in `solune/frontend/playwright.config.ts` — `reason: auth state setup utility, not a test`
- [ ] T065 [US3] Verify `forbidOnly` comment in `solune/frontend/playwright.config.ts` is sufficient — add `reason:` if needed
- [ ] T066 [US3] Verify E2E test suite runs correctly with new configuration

**Checkpoint**: E2E test skip cleanup complete — tests run or skip based on explicit configuration

---

## Phase 6: User Story 4 — Infrastructure Suppression Cleanup (Priority: P2)

**Goal**: Review Bicep secret-output suppressions and add documented justification for each retained suppression.

**Independent Test**: Run `az bicep build --file main.bicep` in `infra/` — must compile without errors. All remaining suppressions must have documented reasons.

### 4.1 — Bicep Secret Output Review

- [ ] T067 [P] [US4] Add `reason: Log Analytics shared key required directly by Container Apps Environment — Key Vault reference not supported` to `#disable-next-line` in `infra/modules/monitoring.bicep`
- [ ] T068 [P] [US4] Add `reason: Azure OpenAI access key passed to Key Vault in parent module` to `#disable-next-line` in `infra/modules/openai.bicep`
- [ ] T069 [P] [US4] Add `reason: Storage account key required for Azure Files volume mount configuration` to `#disable-next-line` in `infra/modules/storage.bicep`

### 4.2 — Verify Infrastructure

- [ ] T070 [US4] Verify infrastructure builds: `az bicep build --file main.bicep` in `infra/`

**Checkpoint**: Infrastructure suppression cleanup complete — all Bicep suppressions documented and builds pass

---

## Phase 7: User Story 5 — Suppression Policy and CI Guard (Priority: P3)

**Goal**: Create a CI guard that prevents new suppressions without a reason and add a policy document explaining suppression standards.

**Independent Test**: Introduce a suppression without a `reason:` marker in a test file and verify the CI guard fails the build.

### 5.1 — Create CI Suppression Guard

- [ ] T071 [US5] Create `solune/scripts/check-suppressions.sh` — shell script that scans changed files for suppression patterns (Python: `# noqa`, `# type: ignore`, `# pragma: no cover`; TypeScript: `eslint-disable`, `@ts-expect-error`, `@ts-ignore`; Bicep: `#disable-next-line`) and exits non-zero if any lack a `reason:` marker (per contract in `specs/003-remove-lint-ignores/contracts/suppression-guard.openapi.yaml`)
- [ ] T072 [US5] Integrate suppression guard as a pre-commit hook in `solune/.pre-commit-config.yaml` or as a CI step in `.github/workflows/ci.yml`
- [ ] T073 [US5] Test the guard by introducing an unjustified suppression in a temp file and verifying the guard correctly fails

### 5.2 — Review Ignore Files

- [ ] T074 [P] [US5] Review `.gitignore` for stale entries — remove any that no longer apply
- [ ] T075 [P] [US5] Review `.prettierignore` for stale entries — remove any that no longer apply
- [ ] T076 [P] [US5] Confirm no `.eslintignore` or `.ruffignore` files exist that conflict with current configuration

### 5.3 — Policy Documentation

- [ ] T077 [US5] Add suppression policy note to `solune/docs/` explaining: all remaining suppressions must carry a `reason:` justification, the CI guard enforces this, and how to add a justified suppression

**Checkpoint**: Policy and CI guard in place — new unjustified suppressions will be blocked

---

## Phase 8: User Story 6 — Final Verification and Baseline Comparison (Priority: P3)

**Goal**: Run the full verification suite and compare post-cleanup results against the Phase 2 baseline to confirm no regressions and measurable improvement.

**Independent Test**: Compare post-cleanup check results against recorded baseline — all results must be equal to or better.

- [ ] T078 [US6] Run full backend regression at stricter settings: `ruff check src tests && ruff format --check src tests && bandit -r src/ -ll -ii --skip B104 && pyright src && pytest --cov=src --cov-report=term-missing` in `solune/backend/`
- [ ] T079 [P] [US6] Run full frontend regression: `npm run lint -- --max-warnings=0 && npm run type-check && npm run type-check:test && npm run test:coverage && npm run build` in `solune/frontend/`
- [ ] T080 [P] [US6] Run mutation testing regression: `npm run test:mutation` with `ignoreStatic: false` in `solune/frontend/`
- [ ] T081 [P] [US6] Run E2E regression: `npx playwright test` in `solune/frontend/`
- [ ] T082 [P] [US6] Run infrastructure build verification: `az bicep build --file main.bicep` in `infra/`
- [ ] T083 [US6] Compare post-cleanup results against Phase 2 baseline — verify all results equal or improved
- [ ] T084 [US6] Verify all remaining suppressions carry `reason:` justification — 100% compliance (SC-002)
- [ ] T085 [US6] Verify total suppression count reduced by at least 80% compared to baseline (SC-001)

**Checkpoint**: Full verification complete — cleanup is validated against baseline

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements that affect multiple user stories and cross-cutting quality checks

- [ ] T086 Fix any bugs discovered during suppression removal that were deferred (FR-034) — create follow-up issues for genuinely large fixes
- [ ] T087 Final suppression audit: confirm every retained suppression has a `reason:` comment in source code
- [ ] T088 Run `specs/003-remove-lint-ignores/quickstart.md` full regression validation end-to-end
- [ ] T089 Document any deferred items (e.g., `reportMissingTypeStubs`) with justification

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational / Baseline (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 Backend (Phase 3)**: Depends on Phase 2 baseline capture
- **US2 Frontend (Phase 4)**: Depends on Phase 2 baseline capture — can run in parallel with US1
- **US3 E2E (Phase 5)**: Depends on Phase 2 — can run in parallel with US1/US2
- **US4 Infrastructure (Phase 6)**: Depends on Phase 2 — can run in parallel with US1/US2/US3
- **US5 Policy (Phase 7)**: Depends on US1–US4 completion (guard must scan clean codebase)
- **US6 Verification (Phase 8)**: Depends on US1–US5 completion (final regression)
- **Polish (Phase 9)**: Depends on US6 verification completion

### User Story Dependencies

- **US1 (Backend, P1)**: Independent after baseline — no dependencies on other stories
- **US2 (Frontend, P1)**: Independent after baseline — no dependencies on other stories
- **US3 (E2E, P2)**: Independent after baseline — no dependencies on other stories
- **US4 (Infrastructure, P2)**: Independent after baseline — no dependencies on other stories
- **US5 (Policy, P3)**: Depends on US1–US4 (suppression guard scans cleaned files)
- **US6 (Verification, P3)**: Depends on US1–US5 (final comparison against baseline)

### Within Each User Story

- Config changes before code changes
- Security-critical items first (Bandit B608, SQL parameterization)
- Type/lint fixes before coverage/test fixes
- Verification at the end of each story phase
- Story complete before starting dependent stories

### Parallel Opportunities

- **Phase 2**: T005, T006, T007 can run in parallel with T004
- **Phase 3 (US1)**: T013, T014, T015 can run in parallel; T017–T025 can run in parallel (different files); T027–T029 can run in parallel
- **Phase 4 (US2)**: T038–T043 can all run in parallel (different component files); T044–T045 parallel; T047–T053 parallel
- **Phase 5 (US3)**: T062, T063 can run in parallel
- **Phase 6 (US4)**: T067, T068, T069 can all run in parallel (different Bicep modules)
- **Phase 7 (US5)**: T074, T075, T076 can run in parallel
- **Phase 8 (US6)**: T079, T080, T081, T082 can run in parallel
- **Cross-story**: US1, US2, US3, US4 can all run in parallel after Phase 2

---

## Parallel Example: User Story 1 — Backend

```bash
# Launch type-ignore fixes in parallel (different service files):
Task T013: "Replace type:ignore in solune/backend/src/services/agent_provider.py"
Task T014: "Replace type:ignore in solune/backend/src/services/plan_agent_provider.py"
Task T015: "Add reason to type:ignore in solune/backend/tests/unit/test_mcp_server/test_context.py"

# Launch noqa fixes in parallel (different files):
Task T017: "Add reason to B008 markers in solune/backend/src/api/ files"
Task T018: "Fix B009 markers in solune/backend/tests/unit/test_run_mutmut_shard.py"
Task T019: "Fix B010 markers in solune/backend/tests/unit/ test files"
Task T021: "Replace F401 with __all__ in solune/backend/src/models/chat.py"
Task T022: "Replace F401 with __all__ in solune/backend/src/services/copilot_polling/__init__.py"
```

## Parallel Example: User Story 2 — Frontend

```bash
# Launch exhaustive-deps fixes in parallel (different component files):
Task T038: "Fix exhaustive-deps in ChatInterface.tsx"
Task T039: "Fix exhaustive-deps in AgentChatFlow.tsx"
Task T040: "Fix exhaustive-deps in ChoreChatFlow.tsx"
Task T041: "Fix exhaustive-deps in ModelSelector.tsx"
Task T042: "Fix exhaustive-deps in UploadMcpModal.tsx"

# Launch jsx-a11y fixes in parallel (different component files):
Task T047: "Fix autoFocus in AddChoreModal.tsx"
Task T048: "Fix autoFocus in AddAgentPopover.tsx"
Task T049: "Fix click-on-non-interactive in AgentIconPickerModal.tsx"
Task T050: "Fix click-on-non-interactive in AgentPresetSelector.tsx"
Task T051: "Fix click-on-non-interactive in AddAgentModal.tsx"
```

## Parallel Example: Cross-Story Parallelism

```bash
# After Phase 2 baseline, all four cleanup stories can start simultaneously:
Developer A → US1 (Backend): Phases 3 tasks T009–T037
Developer B → US2 (Frontend): Phase 4 tasks T038–T061
Developer C → US3 (E2E): Phase 5 tasks T062–T066
Developer D → US4 (Infrastructure): Phase 6 tasks T067–T070
```

---

## Implementation Strategy

### MVP First (User Story 1 — Backend Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Baseline Capture (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 — Backend Suppression Cleanup
4. **STOP and VALIDATE**: Run full backend verification independently
5. This alone addresses the highest-risk area (Bandit B608 security, type errors)

### Incremental Delivery

1. Setup + Baseline → Foundation ready
2. Add US1 (Backend) → Test independently → Security risk addressed (MVP!)
3. Add US2 (Frontend) → Test independently → Stale-closure and accessibility bugs fixed
4. Add US3 (E2E) → Test independently → Test matrix transparent
5. Add US4 (Infrastructure) → Test independently → Secret outputs documented
6. Add US5 (Policy) → Test guard → Ongoing compliance enforced
7. Add US6 (Verification) → Compare baseline → Cleanup validated
8. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers after Phase 2:

- **Developer A**: US1 (Backend) — highest security priority
- **Developer B**: US2 (Frontend) — highest quality priority
- **Developer C**: US3 (E2E) + US4 (Infra) — lower priority, smaller scope
- **Developer D**: US5 (Policy) after A+B+C complete → US6 (Verification)

---

## Notes

- [P] tasks = different files, no dependencies on other tasks in the same phase
- [USn] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **Key Risk**: T009–T012 (Bandit B608) may reveal SQL injection paths — treat as high priority security fix
- **Key Risk**: T038–T043 (exhaustive-deps) may change runtime behavior — verify each fix does not introduce new stale-closure bugs
- **Key Risk**: T055–T056 (Stryker ignoreStatic) may reveal many surviving mutants — close highest-impact gaps first
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
