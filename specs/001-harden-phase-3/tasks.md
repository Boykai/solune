# Tasks: Harden Phase 3 — Code Quality & Tech Debt

**Input**: Design documents from `/specs/001-harden-phase-3/`
**Prerequisites**: spec.md (user stories with priorities)

**Tests**: Not explicitly requested in the feature specification. Test tasks are included only for US4 (verification-only story) where the spec explicitly requires test coverage confirmation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `solune/backend/src/`, `solune/backend/tests/`
- **Frontend**: `solune/frontend/src/`, `solune/frontend/`
- **CI**: `.github/workflows/`
- **Docs**: `solune/docs/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparation work — create the accessor pattern and verify current state before modifying consumers

- [ ] T001 Create a `get_github_service()` accessor function in `solune/backend/src/services/github_projects/__init__.py` that returns the registered `app.state.github_service` instance in request contexts and falls back to the module-level singleton in non-request contexts (background tasks, signal bridge, orchestrator)
- [ ] T002 Update `solune/backend/src/dependencies.py` to use the new `get_github_service()` accessor from the github_projects package instead of importing the module-level singleton directly
- [ ] T003 Verify the full backend test suite passes after accessor introduction (no consumer changes yet) by running `pytest` from `solune/backend/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No cross-story blocking prerequisites exist for this hardening feature. Each user story is independent — proceed directly to Phase 3.

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — Remove Module-Level Singletons (Priority: P1) 🎯 MVP

**Goal**: Migrate all 27 consumer files from direct `github_projects_service` singleton imports to the `get_github_service()` accessor, then remove both module-level singletons and their TODO markers.

**Independent Test**: Run the full backend test suite after removing the singletons. Zero regressions, zero remaining `TODO(018-codebase-audit-refactor)` markers, zero direct singleton imports outside the accessor's own fallback.

### Implementation for User Story 1

**API layer migration** (11 files — all use the singleton in request contexts where `app.state` is available):

- [ ] T004 [P] [US1] Migrate `solune/backend/src/api/board.py` from `from src.services.github_projects import github_projects_service` to use `get_github_service()` accessor
- [ ] T005 [P] [US1] Migrate `solune/backend/src/api/chores.py` from direct singleton import to use `get_github_service()` accessor
- [ ] T006 [P] [US1] Migrate `solune/backend/src/api/chat.py` (lines 420, 532, 1552, 1711) from direct singleton import to use `get_github_service()` accessor
- [ ] T007 [P] [US1] Migrate `solune/backend/src/api/webhooks.py` from direct singleton import to use `get_github_service()` accessor
- [ ] T008 [P] [US1] Migrate `solune/backend/src/api/workflow.py` from direct singleton import to use `get_github_service()` accessor
- [ ] T009 [P] [US1] Migrate `solune/backend/src/api/pipelines.py` from direct singleton import to use `get_github_service()` accessor
- [ ] T010 [P] [US1] Migrate `solune/backend/src/api/metadata.py` (lines 26, 40) from direct singleton import to use `get_github_service()` accessor
- [ ] T011 [P] [US1] Migrate `solune/backend/src/api/tasks.py` from direct singleton import to use `get_github_service()` accessor
- [ ] T012 [P] [US1] Migrate `solune/backend/src/api/projects.py` from direct singleton import to use `get_github_service()` accessor
- [ ] T013 [P] [US1] Migrate `solune/backend/src/api/agents.py` (lines 545, 568) from direct singleton import to use `get_github_service()` accessor
- [ ] T014 [P] [US1] Migrate `solune/backend/src/api/tools.py` from direct singleton import to use `get_github_service()` accessor

**Service layer migration** (8 files — mix of request and non-request contexts):

- [ ] T015 [P] [US1] Migrate `solune/backend/src/services/agents/service.py` from direct singleton import to use `get_github_service()` accessor
- [ ] T016 [P] [US1] Migrate `solune/backend/src/services/agents/agent_mcp_sync.py` (lines 146, 274) from direct singleton import to use `get_github_service()` accessor
- [ ] T017 [P] [US1] Migrate `solune/backend/src/services/tools/service.py` (line 59) from direct singleton import to use `get_github_service()` accessor
- [ ] T018 [P] [US1] Migrate `solune/backend/src/services/metadata_service.py` (line 282) from direct singleton import to use `get_github_service()` accessor
- [ ] T019 [P] [US1] Migrate `solune/backend/src/services/github_commit_workflow.py` from direct singleton import to use `get_github_service()` accessor
- [ ] T020 [P] [US1] Migrate `solune/backend/src/services/agent_creator.py` from direct singleton import to use `get_github_service()` accessor
- [ ] T021 [P] [US1] Migrate `solune/backend/src/services/signal_chat.py` (lines 217, 368) from direct singleton import to use `get_github_service()` accessor
- [ ] T022 [P] [US1] Migrate `solune/backend/src/services/signal_bridge.py` (line 769) from direct singleton import to use `get_github_service()` accessor

**Background task / polling / orchestrator migration** (4 files — non-request contexts using accessor fallback):

- [ ] T023 [P] [US1] Migrate `solune/backend/src/services/copilot_polling/__init__.py` from direct singleton import to use `get_github_service()` accessor (fallback path)
- [ ] T024 [P] [US1] Migrate `solune/backend/src/services/copilot_polling/label_manager.py` (lines 68, 126, 152) from direct singleton import to use `get_github_service()` accessor (fallback path)
- [ ] T025 [P] [US1] Migrate `solune/backend/src/services/copilot_polling/recovery.py` (line 1097) from direct singleton import to use `get_github_service()` accessor (fallback path)
- [ ] T026 [P] [US1] Migrate `solune/backend/src/services/workflow_orchestrator/orchestrator.py` (line 2832) from direct singleton import to use `get_github_service()` accessor (fallback path)

**Core module migration** (3 files):

- [ ] T027 [P] [US1] Migrate `solune/backend/src/utils.py` (lines 242, 300) from direct singleton import to use `get_github_service()` accessor
- [ ] T028 [P] [US1] Migrate `solune/backend/src/constants.py` (line 309) from direct singleton import to use `get_github_service()` accessor
- [ ] T029 [P] [US1] Migrate `solune/backend/src/main.py` (line 594) to use `get_github_service()` accessor for `app.state` registration

**Singleton removal and cleanup**:

- [ ] T030 [US1] Remove module-level singleton `github_projects_service = GitHubProjectsService()` and the `TODO(018-codebase-audit-refactor)` comment block from `solune/backend/src/services/github_projects/service.py` (lines 479–493)
- [ ] T031 [US1] Remove `TODO(018-codebase-audit-refactor)` comment block from `solune/backend/src/services/github_projects/agents.py` (lines 399–412)
- [ ] T032 [US1] Update `solune/backend/src/services/github_projects/__init__.py` exports: remove `github_projects_service` from `__all__` and the re-export, export `get_github_service` instead
- [ ] T033 [US1] Verify zero occurrences of `TODO(018-codebase-audit-refactor)` remain in the codebase via `grep -r "TODO(018-codebase-audit-refactor)" solune/`
- [ ] T034 [US1] Verify zero direct `github_projects_service` singleton imports remain (outside the accessor definition) via `grep -rn "import github_projects_service" solune/backend/src/`
- [ ] T035 [US1] Run the full backend test suite to confirm no regressions after singleton removal

**Checkpoint**: User Story 1 complete — all consumers use the accessor, both singletons removed, full test suite passes

---

## Phase 4: User Story 2 — Upgrade Pre-Release Dependencies (Priority: P2)

**Goal**: Upgrade all 8 pre-release/beta dependencies to their latest available versions, including the Copilot SDK package rename from `github-copilot-sdk` to `copilot-sdk`.

**Independent Test**: Run the full backend test suite after each upgrade. Dependency resolver installs cleanly. All tests pass. All import paths updated for the Copilot SDK rename.

### Implementation for User Story 2

**Copilot SDK rename + upgrade** (highest risk — package name change):

- [ ] T036 [US2] Update `solune/backend/pyproject.toml` line 16: replace `"github-copilot-sdk>=0.1.30,<1"` with `"copilot-sdk>=1.0.17"` and update the comment on line 15
- [ ] T037 [US2] Search for and update all Python import references to the old Copilot SDK package name. Check files: `solune/backend/src/services/completion_providers.py` (lines 66–67, 152, 176–179), `solune/backend/src/services/plan_agent_provider.py` (line 189), `solune/backend/src/services/agent_provider.py` (line 198), `solune/backend/src/typestubs/copilot/__init__.pyi`
- [ ] T038 [US2] Regenerate the lock file (`uv lock` or equivalent) to resolve the Copilot SDK rename cleanly
- [ ] T039 [US2] Run the backend test suite to verify no import errors or regressions from the Copilot SDK upgrade

**Azure AI Inference upgrade**:

- [ ] T040 [P] [US2] Update `solune/backend/pyproject.toml` line 19: upgrade `"azure-ai-inference>=1.0.0b9,<2"` to the latest available version
- [ ] T041 [US2] Run the backend test suite to verify no regressions from the Azure AI Inference upgrade

**Agent Framework upgrades** (3 packages):

- [ ] T042 [P] [US2] Update `solune/backend/pyproject.toml` lines 21–23: upgrade all three `agent-framework-*` packages from `>=1.0.0b1` to the latest available versions (`agent-framework-core`, `agent-framework-azure-ai`, `agent-framework-github-copilot`)
- [ ] T043 [US2] Run the backend test suite to verify no regressions from the Agent Framework upgrades

**OpenTelemetry instrumentation upgrades** (3 packages):

- [ ] T044 [P] [US2] Update `solune/backend/pyproject.toml` lines 40–42: upgrade all three `opentelemetry-instrumentation-*` packages from `>=0.54b0,<1` to the latest available versions and update the comment on lines 72–73
- [ ] T045 [US2] Run the backend test suite to verify no regressions from the OpenTelemetry upgrades

**Final validation**:

- [ ] T046 [US2] Regenerate the lock file and verify clean dependency resolution with no conflicts
- [ ] T047 [US2] Run the full backend test suite (unit + integration) to verify all 8 dependency upgrades together

**Checkpoint**: User Story 2 complete — all 8 pre-release dependencies upgraded, Copilot SDK renamed, all tests pass

---

## Phase 5: User Story 3 — Consolidate Stryker Mutation Configs (Priority: P3)

**Goal**: Replace the 4 separate Stryker shard config files with a single unified configuration that supports shard selection via environment variable, preserving per-shard report paths.

**Independent Test**: Run Stryker with each shard selection and verify mutation targets and report paths match the original per-config behavior. Run without shard selection and verify all targets are included.

### Implementation for User Story 3

- [ ] T048 [US3] Create a unified `solune/frontend/stryker.config.mjs` that replaces the base config with shard-aware logic: read `STRYKER_SHARD` env var, define shard map (`hooks-board`, `hooks-data`, `hooks-general`, `lib`) with their mutate globs and report paths, default to full run when no shard specified
- [ ] T049 [US3] Verify the unified config produces the same mutation targets for shard `hooks-board` as `solune/frontend/stryker-hooks-board.config.mjs` (mutate: `useAdaptivePolling`, `useBoardProjection`, `useBoardRefresh`, `useProjectBoard`, `useRealTimeSync`; report: `reports/mutation/hooks-board/`)
- [ ] T050 [US3] Verify the unified config produces the same mutation targets for shard `hooks-data` as `solune/frontend/stryker-hooks-data.config.mjs` (mutate: `useProjects`, `useChat`, `useChatHistory`, `useCommands`, `useWorkflow`, `useSettingsForm`, `useAuth`; report: `reports/mutation/hooks-data/`)
- [ ] T051 [US3] Verify the unified config produces the same mutation targets for shard `hooks-general` as `solune/frontend/stryker-hooks-general.config.mjs` (mutate: all hooks except board/data shards; report: `reports/mutation/hooks-general/`)
- [ ] T052 [US3] Verify the unified config produces the same mutation targets for shard `lib` as `solune/frontend/stryker-lib.config.mjs` (mutate: `src/lib/**/*.ts`; report: `reports/mutation/lib/`)
- [ ] T053 [US3] Remove the 4 individual shard config files: `solune/frontend/stryker-hooks-board.config.mjs`, `solune/frontend/stryker-hooks-data.config.mjs`, `solune/frontend/stryker-hooks-general.config.mjs`, `solune/frontend/stryker-lib.config.mjs`
- [ ] T054 [US3] Update `solune/frontend/package.json` scripts (lines 27–31): replace individual shard scripts with a single `test:mutate` script that accepts shard via `STRYKER_SHARD` env var (e.g., `STRYKER_SHARD=hooks-board npx stryker run`)
- [ ] T055 [US3] Update `.github/workflows/mutation-testing.yml` (line 93): change from `npx stryker run -c stryker-${{ matrix.shard }}.config.mjs` to `STRYKER_SHARD=${{ matrix.shard }} npx stryker run` (keep the matrix strategy and shard names unchanged)
- [ ] T056 [US3] Update `solune/docs/testing.md` Stryker section: document the unified config, `STRYKER_SHARD` env var usage, and remove references to individual shard config files

**Checkpoint**: User Story 3 complete — single unified Stryker config, 4 shard configs removed, CI updated, docs updated

---

## Phase 6: User Story 4 — Verify Plan-Mode Chat History Fix (Priority: P4)

**Goal**: Confirm the existing fix is in place (user messages persisted only after `get_chat_agent_service()` succeeds) and ensure test coverage prevents regression. No code changes expected — verification and test coverage only.

**Independent Test**: Simulate plan-mode requests where the service is unavailable and verify no messages are persisted. Simulate successful requests and verify messages are persisted after service confirmation.

### Implementation for User Story 4

- [ ] T057 [P] [US4] Verify non-streaming endpoint in `solune/backend/src/api/chat.py` (lines 2010–2024): confirm `get_chat_agent_service()` is called before `add_message()` and that a 503 response is returned without persisting when the service is unavailable
- [ ] T058 [P] [US4] Verify streaming endpoint in `solune/backend/src/api/chat.py` (lines 2083–2097): confirm `get_chat_agent_service()` is called before `add_message()` and that a 503 response is returned without persisting when the service is unavailable
- [ ] T059 [US4] Confirm or add a test in `solune/backend/tests/` that mocks `get_chat_agent_service()` to raise an exception for the non-streaming plan endpoint and asserts no call to `add_message` / `chat_store.save_message` occurs
- [ ] T060 [US4] Confirm or add a test in `solune/backend/tests/` that mocks `get_chat_agent_service()` to raise an exception for the streaming plan endpoint and asserts no call to `add_message` / `chat_store.save_message` occurs
- [ ] T061 [US4] Confirm or add a test that verifies the happy path: when `get_chat_agent_service()` succeeds, the user message IS persisted to chat history after the service check

**Checkpoint**: User Story 4 complete — fix verified in place, regression test coverage confirmed for both endpoints

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup and validation across all user stories

- [ ] T062 [P] Run the full backend test suite to confirm all changes from US1–US4 work together with no regressions
- [ ] T063 [P] Run the full frontend build (`npm run build` in `solune/frontend/`) to confirm Stryker config changes don't affect the build
- [ ] T064 [P] Update `solune/docs/testing.md` if any mutation testing commands or shard references need correction after US3
- [ ] T065 Run a final codebase audit: zero `TODO(018-codebase-audit-refactor)` markers, zero direct singleton imports, all 8 dependencies upgraded, single Stryker config
- [ ] T066 Verify the full CI pipeline configuration is consistent (`.github/workflows/ci.yml` and `.github/workflows/mutation-testing.yml`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: No blocking prerequisites for this hardening feature
- **User Story 1 (Phase 3)**: Depends on Phase 1 (accessor creation) — BLOCKS Phase 7 audit
- **User Story 2 (Phase 4)**: No dependencies on other stories — can start after Phase 1
- **User Story 3 (Phase 5)**: No dependencies on other stories — can start immediately
- **User Story 4 (Phase 6)**: No dependencies on other stories — can start immediately
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Phase 1 (T001–T003 — accessor must exist before consumers migrate). No dependencies on other stories.
- **User Story 2 (P2)**: Fully independent. Can start immediately. No dependencies on US1, US3, or US4.
- **User Story 3 (P3)**: Fully independent. Can start immediately. No dependencies on US1, US2, or US4.
- **User Story 4 (P4)**: Fully independent. Can start immediately. No dependencies on US1, US2, or US3.

### Within Each User Story

- **US1**: Accessor creation (T001) → Consumer migration (T004–T029, all [P]) → Singleton removal (T030–T032) → Verification (T033–T035)
- **US2**: Copilot SDK rename (T036–T039, sequential due to risk) → Azure AI + Agent Framework + OTel (T040–T045, partially parallel) → Final validation (T046–T047)
- **US3**: Unified config (T048) → Per-shard verification (T049–T052, all sequential) → File removal + CI update (T053–T056)
- **US4**: Code verification (T057–T058, parallel) → Test coverage (T059–T061)

### Parallel Opportunities

- **Cross-story parallelism**: US1, US2, US3, and US4 can all be worked on in parallel by different developers (after Phase 1 is complete for US1)
- **Within US1**: All 27 consumer migration tasks (T004–T029) are marked [P] — they touch different files and can run in parallel
- **Within US2**: Azure AI (T040), Agent Framework (T042), and OTel (T044) upgrades can be done in parallel (different dependency lines)
- **Within US4**: Code verification tasks (T057–T058) can run in parallel

---

## Parallel Example: User Story 1

```text
# Step 1: Create accessor (must complete first)
Task T001: Create get_github_service() accessor in __init__.py

# Step 2: Migrate all 27 consumers in parallel (all [P], different files):
Task T004: Migrate board.py
Task T005: Migrate chores.py
Task T006: Migrate chat.py
Task T007: Migrate webhooks.py
Task T008: Migrate workflow.py
  ... (T009–T029 all parallel)

# Step 3: Remove singletons (after all consumers migrated):
Task T030: Remove singleton from service.py
Task T031: Remove TODO from agents.py
Task T032: Update __init__.py exports
```

## Parallel Example: User Story 2

```text
# Step 1: Copilot SDK rename (highest risk, do first):
Task T036: Update pyproject.toml
Task T037: Update import references
Task T038: Regenerate lock file
Task T039: Test

# Step 2: Remaining upgrades in parallel:
Task T040: Azure AI Inference upgrade
Task T042: Agent Framework upgrades (3 packages)
Task T044: OpenTelemetry upgrades (3 packages)

# Step 3: Final validation:
Task T046: Regenerate lock file
Task T047: Full test suite
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Create accessor pattern (T001–T003)
2. Complete Phase 3: Migrate all consumers, remove singletons (T004–T035)
3. **STOP and VALIDATE**: Run full test suite, verify zero TODOs, zero direct imports
4. This delivers the highest-value code-quality improvement

### Incremental Delivery

1. Setup (T001–T003) → Accessor pattern ready
2. User Story 1 (T004–T035) → Singletons removed → Validate (MVP!)
3. User Story 2 (T036–T047) → Dependencies upgraded → Validate
4. User Story 3 (T048–T056) → Stryker consolidated → Validate
5. User Story 4 (T057–T061) → Chat history fix verified → Validate
6. Polish (T062–T066) → Final cross-cutting validation
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Developer A: User Story 1 (requires Phase 1 first, then 27 parallel migrations)
2. Developer B: User Story 2 (independent, start immediately)
3. Developer C: User Story 3 (independent, start immediately)
4. Developer D: User Story 4 (independent, start immediately)
5. Stories complete and integrate independently
6. Final Polish phase after all stories merge

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- US1 has the most tasks (35) because it touches 27 consumer files — but all migrations are mechanical and parallelizable
- US2 should be done incrementally (one package at a time) to isolate breakage
- US3 is a developer-experience improvement — no runtime behavior changes
- US4 is verification-only — the fix is already in place
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
