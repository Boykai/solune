# Tasks: Dependabot Updates

**Feature**: `006-dependabot-updates` | **Branch**: `006-dependabot-updates`
**Input**: Design artifacts for `/home/runner/work/solune/solune/specs/006-dependabot-updates/` sourced from the issue plan and parent issue Boykai/solune#1810
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, research.md ✅, quickstart.md ✅, contracts/dependabot-batch-update-contract.yaml ✅

**Tests**: No new tests are added. Every update task reruns the existing validation commands defined in `/home/runner/work/solune/solune/.github/workflows/ci.yml` against `/home/runner/work/solune/solune/solune/backend/pyproject.toml`, `/home/runner/work/solune/solune/solune/backend/uv.lock`, `/home/runner/work/solune/solune/solune/frontend/package.json`, and `/home/runner/work/solune/solune/solune/frontend/package-lock.json`.

**Organization**: Tasks are grouped by workflow-oriented user stories so each increment can be executed and verified independently while preserving the required patch → minor → major ordering.

## Format: `- [ ] T### [P?] [US#?] Description with file path`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[US#]**: Required on all user-story-phase tasks
- **No [US#]**: Setup, Foundational, and Polish phases only
- Every task includes exact absolute file paths

## Path Conventions

- **Repository root**: `/home/runner/work/solune/solune`
- **Backend manifest**: `/home/runner/work/solune/solune/solune/backend/pyproject.toml`
- **Backend lockfile**: `/home/runner/work/solune/solune/solune/backend/uv.lock`
- **Frontend manifest**: `/home/runner/work/solune/solune/solune/frontend/package.json`
- **Frontend lockfile**: `/home/runner/work/solune/solune/solune/frontend/package-lock.json`
- **CI validation source**: `/home/runner/work/solune/solune/.github/workflows/ci.yml`

---

## Phase 1: Setup (Discovery & Inventory)

**Purpose**: Build the exact Dependabot update inventory and confirm the files/commands that each later task will touch.

- [ ] T001 Cross-check every open Dependabot PR from Boykai/solune#1810 against `/home/runner/work/solune/solune/solune/backend/pyproject.toml` and `/home/runner/work/solune/solune/solune/frontend/package.json`, recording the package name, current version, target version, ecosystem, and PR number for all 14 updates
- [ ] T002 [P] Verify the backend regeneration and validation commands in `/home/runner/work/solune/solune/.github/workflows/ci.yml` match the current dependency workflow for `/home/runner/work/solune/solune/solune/backend/pyproject.toml` and `/home/runner/work/solune/solune/solune/backend/uv.lock`
- [ ] T003 [P] Verify the frontend regeneration and validation commands in `/home/runner/work/solune/solune/.github/workflows/ci.yml` match the current dependency workflow for `/home/runner/work/solune/solune/solune/frontend/package.json` and `/home/runner/work/solune/solune/solune/frontend/package-lock.json`
- [ ] T004 Detect overlap risk before editing by comparing the affected dependency ranges in `/home/runner/work/solune/solune/solune/backend/pyproject.toml`, `/home/runner/work/solune/solune/solune/backend/uv.lock`, `/home/runner/work/solune/solune/solune/frontend/package.json`, and `/home/runner/work/solune/solune/solune/frontend/package-lock.json`, then order the queue as patch → minor dev → minor runtime → major

**Checkpoint**: The full 14-update inventory is known, validation commands are confirmed, and the execution order is fixed.

---

## Phase 2: Foundational (Blocking Validation Baseline)

**Purpose**: Prove the repository is green before any dependency edits and establish the revert/replay workflow required by the issue.

**⚠️ CRITICAL**: Do not start any update task until both ecosystems have a known-good baseline and the revert procedure is defined.

- [ ] T005 [P] Run the backend baseline validation sequence from `/home/runner/work/solune/solune/solune/backend/pyproject.toml` and `/home/runner/work/solune/solune/solune/backend/uv.lock` using the commands in `/home/runner/work/solune/solune/.github/workflows/ci.yml` (`uv sync --locked --extra dev`, `uv run pip-audit .`, `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run bandit -r src/ -ll -ii --skip B104,B608`, `uv run pyright src`, `uv run pyright -p pyrightconfig.tests.json`, `uv run pytest --cov=src --cov-report=term-missing --cov-report=xml --cov-report=html --durations=20 --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency`)
- [ ] T006 [P] Run the frontend baseline validation sequence from `/home/runner/work/solune/solune/solune/frontend/package.json` and `/home/runner/work/solune/solune/solune/frontend/package-lock.json` using the commands in `/home/runner/work/solune/solune/.github/workflows/ci.yml` (`npm ci`, `npm audit --audit-level=high`, `npm run lint`, `npm run type-check`, `npm run type-check:test`, `npm run test:coverage`, `npm run build`)
- [ ] T007 Establish the failure-handling loop for `/home/runner/work/solune/solune/solune/backend/pyproject.toml`, `/home/runner/work/solune/solune/solune/backend/uv.lock`, `/home/runner/work/solune/solune/solune/frontend/package.json`, and `/home/runner/work/solune/solune/solune/frontend/package-lock.json`: after every failed validation, revert that single update completely; after every successful validation, replay the surviving change from the latest default-branch state before starting the next update

**Checkpoint**: Both ecosystems pass their pre-update baseline, and the issue-required revert/replay workflow is ready.

---

## Phase 3: User Story 1 - Apply Patch Updates Safely (Priority: P1) 🎯 MVP

**Goal**: Apply the four patch-level Dependabot updates with the lowest risk, keeping only updates that pass the existing validation suite without code changes.

**Independent Test**: Starting from the latest default branch, apply each patch update one at a time to its manifest and lockfile, rerun the existing validation commands, and confirm that only green updates remain in the final manifest/lockfile state.

- [ ] T008 [US1] Update `pytest` from `>=9.0.0` to `>=9.0.3` in `/home/runner/work/solune/solune/solune/backend/pyproject.toml`, regenerate `/home/runner/work/solune/solune/solune/backend/uv.lock` with `uv lock`, and rerun the backend validation sequence from `/home/runner/work/solune/solune/.github/workflows/ci.yml`
- [ ] T009 [US1] Update `happy-dom` from `^20.8.9` to `^20.9.0` in `/home/runner/work/solune/solune/solune/frontend/package.json`, regenerate `/home/runner/work/solune/solune/solune/frontend/package-lock.json` with `npm install`, and rerun the frontend validation sequence from `/home/runner/work/solune/solune/.github/workflows/ci.yml`
- [ ] T010 [US1] Update `typescript-eslint` from `^8.58.1` to `^8.58.2` in `/home/runner/work/solune/solune/solune/frontend/package.json`, regenerate `/home/runner/work/solune/solune/solune/frontend/package-lock.json` with `npm install`, and rerun the frontend validation sequence from `/home/runner/work/solune/solune/.github/workflows/ci.yml`
- [ ] T011 [US1] Update `react-router-dom` from `^7.14.0` to `^7.14.1` in `/home/runner/work/solune/solune/solune/frontend/package.json`, regenerate `/home/runner/work/solune/solune/solune/frontend/package-lock.json` with `npm install`, and rerun the frontend validation sequence from `/home/runner/work/solune/solune/.github/workflows/ci.yml`
- [ ] T012 [US1] Record every patch-tier failure against the affected file pair (`/home/runner/work/solune/solune/solune/backend/pyproject.toml` + `/home/runner/work/solune/solune/solune/backend/uv.lock` or `/home/runner/work/solune/solune/solune/frontend/package.json` + `/home/runner/work/solune/solune/solune/frontend/package-lock.json`) with a one-line summary before moving to the minor tiers

**Checkpoint**: All safe patch bumps are retained; any failing patch bumps are reverted and documented.

---

## Phase 4: User Story 2 - Apply Minor Dev-Dependency Updates Safely (Priority: P2)

**Goal**: Apply the five minor dev-dependency updates that affect development and CI tooling without changing application code.

**Independent Test**: Starting from the patch-green state, apply each dev-only minor update to `/home/runner/work/solune/solune/solune/backend/pyproject.toml` and `/home/runner/work/solune/solune/solune/backend/uv.lock` one at a time, rerun the backend validation suite after each change, and retain only the updates that remain green.

- [ ] T013 [US2] Update `pytest-cov` from `>=7.0.0` to `>=7.1.0` in `/home/runner/work/solune/solune/solune/backend/pyproject.toml`, regenerate `/home/runner/work/solune/solune/solune/backend/uv.lock`, and rerun the backend validation sequence from `/home/runner/work/solune/solune/.github/workflows/ci.yml`
- [ ] T014 [US2] Update `freezegun` from `>=1.4.0` to `>=1.5.5` in `/home/runner/work/solune/solune/solune/backend/pyproject.toml`, regenerate `/home/runner/work/solune/solune/solune/backend/uv.lock`, and rerun the backend validation sequence from `/home/runner/work/solune/solune/.github/workflows/ci.yml`
- [ ] T015 [US2] Update `pip-audit` from `>=2.9.0` to `>=2.10.0` in `/home/runner/work/solune/solune/solune/backend/pyproject.toml`, regenerate `/home/runner/work/solune/solune/solune/backend/uv.lock`, and rerun the backend validation sequence from `/home/runner/work/solune/solune/.github/workflows/ci.yml`
- [ ] T016 [US2] Update `mutmut` from `>=3.2.0` to `>=3.5.0` in `/home/runner/work/solune/solune/solune/backend/pyproject.toml`, regenerate `/home/runner/work/solune/solune/solune/backend/uv.lock`, and rerun the backend validation sequence from `/home/runner/work/solune/solune/.github/workflows/ci.yml`
- [ ] T017 [US2] Update `bandit` from `>=1.8.0` to `>=1.9.4` in `/home/runner/work/solune/solune/solune/backend/pyproject.toml`, regenerate `/home/runner/work/solune/solune/solune/backend/uv.lock`, and rerun the backend validation sequence from `/home/runner/work/solune/solune/.github/workflows/ci.yml`
- [ ] T018 [US2] Record every skipped dev-minor update with its failure summary while restoring `/home/runner/work/solune/solune/solune/backend/pyproject.toml` and `/home/runner/work/solune/solune/solune/backend/uv.lock` to the last green state before starting the runtime-minor tier

**Checkpoint**: All safe backend dev-tooling bumps are retained; any failing dev-only minor bumps are reverted and documented.

---

## Phase 5: User Story 3 - Apply Minor Runtime Updates Safely (Priority: P2)

**Goal**: Apply the four minor runtime dependency updates with extra scrutiny for import, startup, crypto, and data-fetching behavior.

**Independent Test**: Starting from the last green dev-minor state, apply each runtime update one at a time, regenerate the matching lockfile, rerun the existing validation suite for that ecosystem, and retain only updates that pass without code changes.

- [ ] T019 [US3] Update `pynacl` from `>=1.5.0` to `>=1.6.2` in `/home/runner/work/solune/solune/solune/backend/pyproject.toml`, regenerate `/home/runner/work/solune/solune/solune/backend/uv.lock`, and rerun the backend validation sequence with extra attention to crypto-related test failures
- [ ] T020 [US3] Update `uvicorn` from `>=0.42.0` to `>=0.44.0` in `/home/runner/work/solune/solune/solune/backend/pyproject.toml`, regenerate `/home/runner/work/solune/solune/solune/backend/uv.lock`, and rerun the backend validation sequence with extra attention to startup and typing failures
- [ ] T021 [US3] Update `agent-framework-core` from `>=1.0.0b1` to `>=1.0.1` in `/home/runner/work/solune/solune/solune/backend/pyproject.toml`, regenerate `/home/runner/work/solune/solune/solune/backend/uv.lock`, and rerun the backend validation sequence with extra attention to import and type-stub failures
- [ ] T022 [US3] Update `@tanstack/react-query` from `^5.97.0` to `^5.99.0` in `/home/runner/work/solune/solune/solune/frontend/package.json`, regenerate `/home/runner/work/solune/solune/solune/frontend/package-lock.json`, and rerun the frontend validation sequence from `/home/runner/work/solune/solune/.github/workflows/ci.yml`
- [ ] T023 [US3] Record every skipped runtime-minor update against the affected manifest/lockfile pair (`/home/runner/work/solune/solune/solune/backend/pyproject.toml` + `/home/runner/work/solune/solune/solune/backend/uv.lock` or `/home/runner/work/solune/solune/solune/frontend/package.json` + `/home/runner/work/solune/solune/solune/frontend/package-lock.json`) before the major-version review begins

**Checkpoint**: All safe runtime minor bumps are retained; any runtime bump that needs code changes is reverted and documented.

---

## Phase 6: User Story 4 - Evaluate the Major Update Without Code Changes (Priority: P3)

**Goal**: Inspect the sole major-version update and keep it only if the manifest + lockfile change passes the existing backend validation suite without any application or test-code edits.

**Independent Test**: Review the major-version changelog, compare it to the current backend pytest configuration, attempt the update once in isolation, and confirm that the final backend manifest/lockfile state either contains the upgrade cleanly or leaves it reverted with a migration note.

- [ ] T024 [US4] Review `pytest-randomly` 4.x breaking changes against the current backend test configuration in `/home/runner/work/solune/solune/solune/backend/pyproject.toml` and the backend CI commands in `/home/runner/work/solune/solune/.github/workflows/ci.yml` to decide whether a manifest-only trial is safe
- [ ] T025 [US4] If T024 shows a manifest-only trial is safe, update `pytest-randomly` from `>=3.16.0` to `>=4.0.1` in `/home/runner/work/solune/solune/solune/backend/pyproject.toml`, regenerate `/home/runner/work/solune/solune/solune/backend/uv.lock`, and rerun the full backend validation sequence; otherwise leave both files unchanged and mark the update as skipped with the required migration note
- [ ] T026 [US4] Revert `/home/runner/work/solune/solune/solune/backend/pyproject.toml` and `/home/runner/work/solune/solune/solune/backend/uv.lock` to the last green state if T025 fails any validation because `pytest-randomly` 4.x needs application, test, or configuration changes beyond the dependency bump itself

**Checkpoint**: The only major bump is either safely retained or explicitly skipped with a concrete migration reason.

---

## Phase 7: User Story 5 - Assemble the Single Batch PR and Close Superseded Dependabot PRs (Priority: P3)

**Goal**: Validate the final dependency state, prepare the required combined PR checklist, and close only the Dependabot PRs represented by the successful batch.

**Independent Test**: From the final manifest and lockfiles, produce one batch PR description that lists every applied update and every skipped update with a reason, then confirm that only the Dependabot PRs represented in the retained file diffs are closed.

- [ ] T027 [P] [US5] Run the final backend validation sequence from `/home/runner/work/solune/solune/.github/workflows/ci.yml` against the retained contents of `/home/runner/work/solune/solune/solune/backend/pyproject.toml` and `/home/runner/work/solune/solune/solune/backend/uv.lock`
- [ ] T028 [P] [US5] Run the final frontend validation sequence from `/home/runner/work/solune/solune/.github/workflows/ci.yml` against the retained contents of `/home/runner/work/solune/solune/solune/frontend/package.json` and `/home/runner/work/solune/solune/solune/frontend/package-lock.json`
- [ ] T029 [US5] Draft the batch PR description from the final diffs in `/home/runner/work/solune/solune/solune/backend/pyproject.toml`, `/home/runner/work/solune/solune/solune/backend/uv.lock`, `/home/runner/work/solune/solune/solune/frontend/package.json`, and `/home/runner/work/solune/solune/solune/frontend/package-lock.json`, including an applied-updates checklist and a skipped-updates section with one-line failure summaries
- [ ] T030 [US5] Close only the Dependabot PRs whose updates are present in the final retained state of `/home/runner/work/solune/solune/solune/backend/pyproject.toml`, `/home/runner/work/solune/solune/solune/backend/uv.lock`, `/home/runner/work/solune/solune/solune/frontend/package.json`, and `/home/runner/work/solune/solune/solune/frontend/package-lock.json`, then delete only those Dependabot remote branches

**Checkpoint**: One combined PR is ready with the required checklist/skip reporting, and only superseded Dependabot PRs are targeted for closure.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Confirm that the final batch respects the issue constraints and only contains allowed dependency-file changes.

- [ ] T031 Confirm the final git diff only changes `/home/runner/work/solune/solune/solune/backend/pyproject.toml`, `/home/runner/work/solune/solune/solune/backend/uv.lock`, `/home/runner/work/solune/solune/solune/frontend/package.json`, and `/home/runner/work/solune/solune/solune/frontend/package-lock.json` unless PR metadata updates are explicitly required by the hosting workflow
- [ ] T032 Verify `/home/runner/work/solune/solune/solune/backend/uv.lock` and `/home/runner/work/solune/solune/solune/frontend/package-lock.json` were regenerated by `uv lock` and `npm install`/`npm ci`, not hand-edited, before opening the final `chore(deps): apply Dependabot batch update` pull request

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 (Setup / Discovery)              -> no dependencies
Phase 2 (Foundational / Baseline)        -> depends on Phase 1; blocks all update work
Phase 3 (US1 / Patch updates)            -> depends on Phase 2
Phase 4 (US2 / Minor dev updates)        -> depends on US1 completion
Phase 5 (US3 / Minor runtime updates)    -> depends on US2 completion
Phase 6 (US4 / Major update review)      -> depends on US3 completion
Phase 7 (US5 / Batch PR assembly)        -> depends on US1, US2, US3, and US4
Final Phase (Polish)                     -> depends on all user stories
```

### User Story Dependencies

- **US1 (P1)**: Starts after baseline validation (T005-T007) and establishes the MVP by applying the lowest-risk patch bumps
- **US2 (P2)**: Starts after US1 because the backend dev-tooling minors must build on the latest green patch state in `/home/runner/work/solune/solune/solune/backend/pyproject.toml` and `/home/runner/work/solune/solune/solune/backend/uv.lock`
- **US3 (P2)**: Starts after US2 so runtime changes are tested on top of the surviving backend/frontend minor-dev state
- **US4 (P3)**: Starts after US3 because the major bump must be evaluated against the last fully green dependency set
- **US5 (P3)**: Starts only after all retained updates are known so the single PR checklist and PR closures match the final manifest/lockfile diffs exactly

### Within Each User Story

- Apply one dependency update at a time
- Regenerate the affected lockfile immediately after each manifest edit
- Run the existing validation suite before keeping the change
- Revert failed updates completely before continuing
- Replay successful updates from the latest default-branch state before the next task

### Parallel Opportunities

- T002 and T003 can run in parallel during setup
- T005 and T006 can run in parallel during the baseline phase
- T027 and T028 can run in parallel during final validation
- Update tasks inside US1-US4 intentionally stay sequential because they mutate shared manifest/lockfile state and must be validated in isolation

---

## Parallel Execution Examples Per User Story

### Setup / Foundational Parallel Work

```text
- T002 Verify backend commands in /home/runner/work/solune/solune/.github/workflows/ci.yml against /home/runner/work/solune/solune/solune/backend/pyproject.toml and /home/runner/work/solune/solune/solune/backend/uv.lock
- T003 Verify frontend commands in /home/runner/work/solune/solune/.github/workflows/ci.yml against /home/runner/work/solune/solune/solune/frontend/package.json and /home/runner/work/solune/solune/solune/frontend/package-lock.json
```

### User Story 1 - Patch Updates

```text
No safe parallel execution inside US1: T008-T011 must run one at a time because each update changes a manifest/lockfile pair that must be validated and either kept or fully reverted before the next patch bump starts.
```

### User Story 2 - Minor Dev Updates

```text
No safe parallel execution inside US2: T013-T017 all touch /home/runner/work/solune/solune/solune/backend/pyproject.toml and /home/runner/work/solune/solune/solune/backend/uv.lock, so each update must be isolated.
```

### User Story 3 - Minor Runtime Updates

```text
No safe parallel execution inside US3: T019-T023 must remain serial because runtime dependency validation has to identify exactly which single update caused any failure.
```

### User Story 4 - Major Update Review

```text
No safe parallel execution inside US4: the major-version review and trial update for /home/runner/work/solune/solune/solune/backend/pyproject.toml and /home/runner/work/solune/solune/solune/backend/uv.lock must stay isolated.
```

### User Story 5 - Batch PR Assembly

```text
- T027 Run final backend validation on /home/runner/work/solune/solune/solune/backend/pyproject.toml and /home/runner/work/solune/solune/solune/backend/uv.lock
- T028 Run final frontend validation on /home/runner/work/solune/solune/solune/frontend/package.json and /home/runner/work/solune/solune/solune/frontend/package-lock.json
```

---

## Implementation Strategy

### MVP First (Patch Updates Only)

1. Complete Phase 1 (discovery and validation-command audit)
2. Complete Phase 2 (baseline validation and revert workflow)
3. Complete Phase 3 (US1 patch updates)
4. Stop and validate the retained patch-only manifest/lockfile state before moving to higher-risk tiers

### Incremental Delivery

1. Discovery + baseline first
2. Apply all safe patch bumps and keep only green changes
3. Layer in minor dev bumps, then minor runtime bumps, retaining only green changes
4. Evaluate the lone major bump last and skip it if it needs code/config changes
5. Assemble one final PR from the surviving manifest/lockfile diffs

### Parallel Team Strategy

1. One engineer can handle T002 while another handles T003
2. One engineer can run T005 while another runs T006
3. Once all updates are retained, backend and frontend final validation (T027-T028) can run in parallel before the PR description is drafted

---

## Notes

- Keep the final change set limited to dependency manifests and regenerated lockfiles
- Do not hand-edit `/home/runner/work/solune/solune/solune/backend/uv.lock` or `/home/runner/work/solune/solune/solune/frontend/package-lock.json`
- Do not apply any update that requires application code, test code, or unrelated configuration changes
- If an update fails, capture the package, target version, and one-line failure reason before continuing
