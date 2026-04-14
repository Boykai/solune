# Tasks: Dependabot Updates

**Feature**: `006-dependabot-updates` | **Branch**: `006-dependabot-updates`
**Input**: Design documents from `/home/runner/work/solune/solune/specs/006-dependabot-updates/`
**Prerequisites**: `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`, `/home/runner/work/solune/solune/specs/006-dependabot-updates/spec.md`, `/home/runner/work/solune/solune/specs/006-dependabot-updates/data-model.md`, `/home/runner/work/solune/solune/specs/006-dependabot-updates/research.md`, `/home/runner/work/solune/solune/specs/006-dependabot-updates/quickstart.md`, `/home/runner/work/solune/solune/specs/006-dependabot-updates/contracts/dependabot-batch-update-contract.yaml`

**Tests**: Required as validation commands already defined in `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md` and `/home/runner/work/solune/solune/specs/006-dependabot-updates/quickstart.md`; do not add new automated test files for this feature.

**Organization**: Tasks are grouped by setup, foundational work, one P1 user story, and polish so the dependency batch can be executed and validated incrementally.

## Format: `- [ ] T### [P?] [US#?] Description with file path`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[US#]**: Required on user story phase tasks only
- **Paths**: Every task references exact absolute or repo-root-resolvable file paths

## Path Conventions

- **Backend manifest**: `solune/backend/pyproject.toml`
- **Backend lock**: `solune/backend/uv.lock`
- **Frontend manifest**: `solune/frontend/package.json`
- **Frontend lock**: `solune/frontend/package-lock.json`
- **Feature docs**: `specs/006-dependabot-updates/`

---

## Phase 1: Setup (Execution Baseline)

**Purpose**: Start from a clean default-branch baseline, confirm the planned update inventory, and capture the mutable files that this batch is allowed to touch.

- [ ] T001 Sync `/home/runner/work/solune/solune` to `origin/main` and create the working branch described in `/home/runner/work/solune/solune/specs/006-dependabot-updates/quickstart.md`
- [ ] T002 [P] Reconcile the open Dependabot inventory in `/home/runner/work/solune/solune/specs/006-dependabot-updates/research.md` with the live constraints in `solune/backend/pyproject.toml` and `solune/frontend/package.json`, including the `pytest` drift note
- [ ] T003 [P] Capture a clean starting diff for `solune/backend/pyproject.toml`, `solune/backend/uv.lock`, `solune/frontend/package.json`, and `solune/frontend/package-lock.json` before any dependency update is attempted

**Checkpoint**: The working branch is clean, the update queue matches the design artifacts, and the only mutable implementation files are confirmed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the one-update-at-a-time validation workflow and the applied/skipped reporting discipline before touching any dependency.

**⚠️ CRITICAL**: No package update work should begin until this phase is complete.

- [ ] T004 Prepare the backend update loop for `solune/backend/pyproject.toml` and `solune/backend/uv.lock` using the command set in `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`: `cd /home/runner/work/solune/solune/solune/backend && uv lock && uv sync --extra dev && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run pyright src/ && uv run pytest tests/unit/ -q`
- [ ] T005 [P] Prepare the frontend update loop for `solune/frontend/package.json` and `solune/frontend/package-lock.json` using the command set in `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`: `cd /home/runner/work/solune/solune/solune/frontend && npm install && npm run lint && npm run type-check && npm run test && npm run build`
- [ ] T006 [P] Establish the applied/skipped update inventory for `solune/backend/pyproject.toml`, `solune/backend/uv.lock`, `solune/frontend/package.json`, and `solune/frontend/package-lock.json` following `/home/runner/work/solune/solune/specs/006-dependabot-updates/contracts/dependabot-batch-update-contract.yaml` and `/home/runner/work/solune/solune/specs/006-dependabot-updates/quickstart.md`

**Checkpoint**: The backend and frontend verification loops are ready, and skip/applied reporting is defined before the first version bump.

---

## Phase 3: User Story 1 - Batch Apply Safe Dependency Updates (Priority: P1) 🎯 MVP

**Goal**: Apply every safe open Dependabot update into one accumulated branch, validate each update with the existing repository command matrix, and keep a complete applied/skipped inventory for the final PR.

**Independent Test**: Starting from the accumulated diffs in `solune/backend/pyproject.toml`, `solune/backend/uv.lock`, `solune/frontend/package.json`, and `solune/frontend/package-lock.json`, rerun the full backend and frontend validation commands from `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`; confirm the PR payload lists every applied update and every skipped update with a reason.

### Validation-Driven Implementation for User Story 1

- [ ] T007 [US1] Apply Dependabot PR #1732 for `pytest` in `solune/backend/pyproject.toml`, regenerate `solune/backend/uv.lock`, and run the full backend validation loop from `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`; if the update fails or needs non-dependency changes, revert the two backend files and record the skip reason
- [ ] T008 [US1] Apply Dependabot PR #1777 for `happy-dom` in `solune/frontend/package.json`, regenerate `solune/frontend/package-lock.json`, and run the full frontend validation loop from `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`; if the update fails or needs non-dependency changes, revert the two frontend files and record the skip reason
- [ ] T009 [US1] Apply Dependabot PR #1776 for `typescript-eslint` in `solune/frontend/package.json`, regenerate `solune/frontend/package-lock.json`, and run the full frontend validation loop from `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`; if the update fails or needs non-dependency changes, revert the two frontend files and record the skip reason
- [ ] T010 [US1] Apply Dependabot PR #1775 for `react-router-dom` in `solune/frontend/package.json`, regenerate `solune/frontend/package-lock.json`, and run the full frontend validation loop from `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`; if the update fails or needs non-dependency changes, revert the two frontend files and record the skip reason
- [ ] T011 [US1] Apply Dependabot PR #1688 for `pytest-cov` in `solune/backend/pyproject.toml`, regenerate `solune/backend/uv.lock`, and run the full backend validation loop from `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`; if the update fails or needs non-dependency changes, revert the two backend files and record the skip reason
- [ ] T012 [US1] Apply Dependabot PR #1695 for `freezegun` in `solune/backend/pyproject.toml`, regenerate `solune/backend/uv.lock`, and run the full backend validation loop from `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`; if the update fails or needs non-dependency changes, revert the two backend files and record the skip reason
- [ ] T013 [US1] Apply Dependabot PR #1694 for `pip-audit` in `solune/backend/pyproject.toml`, regenerate `solune/backend/uv.lock`, and run the full backend validation loop from `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`; if the update fails or needs non-dependency changes, revert the two backend files and record the skip reason
- [ ] T014 [US1] Apply Dependabot PR #1697 for `mutmut` in `solune/backend/pyproject.toml`, regenerate `solune/backend/uv.lock`, and run the full backend validation loop from `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`; if the update fails or needs non-dependency changes, revert the two backend files and record the skip reason
- [ ] T015 [US1] Apply Dependabot PR #1690 for `bandit` in `solune/backend/pyproject.toml`, regenerate `solune/backend/uv.lock`, and run the full backend validation loop from `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`; if the update fails or needs non-dependency changes, revert the two backend files and record the skip reason
- [ ] T016 [US1] Apply Dependabot PR #1699 for `@tanstack/react-query` in `solune/frontend/package.json`, regenerate `solune/frontend/package-lock.json`, and run the full frontend validation loop from `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`; if the update fails or needs non-dependency changes, revert the two frontend files and record the skip reason
- [ ] T017 [US1] Apply Dependabot PR #1692 for `pynacl` in `solune/backend/pyproject.toml`, regenerate `solune/backend/uv.lock`, and run the full backend validation loop from `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`; if the update fails or needs non-dependency changes, revert the two backend files and record the skip reason
- [ ] T018 [US1] Apply Dependabot PR #1696 for `uvicorn` in `solune/backend/pyproject.toml`, regenerate `solune/backend/uv.lock`, and run the full backend validation loop from `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`; if the update fails or needs non-dependency changes, revert the two backend files and record the skip reason
- [ ] T019 [US1] Apply Dependabot PR #1698 for `agent-framework-core` in `solune/backend/pyproject.toml`, regenerate `solune/backend/uv.lock`, and run the full backend validation loop from `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`; if the update fails or needs non-dependency changes, revert the two backend files and record the skip reason
- [ ] T020 [US1] Evaluate Dependabot PR #1693 for `pytest-randomly` in `solune/backend/pyproject.toml`, regenerate `solune/backend/uv.lock`, and accept it only if the full backend validation loop passes without any application, test, or configuration edits; otherwise revert the two backend files and record the major-version skip reason
- [ ] T021 [US1] Rerun the complete backend and frontend validation matrix against `solune/backend/pyproject.toml`, `solune/backend/uv.lock`, `solune/frontend/package.json`, and `solune/frontend/package-lock.json` after all accepted updates are staged together
- [ ] T022 [US1] Assemble the final `chore(deps): apply Dependabot batch update` applied/skipped checklist from the accepted diffs in `solune/backend/pyproject.toml`, `solune/backend/uv.lock`, `solune/frontend/package.json`, and `solune/frontend/package-lock.json` using `/home/runner/work/solune/solune/specs/006-dependabot-updates/contracts/dependabot-batch-update-contract.yaml`

**Checkpoint**: All safe updates are accumulated, every rejected update has a recorded reason, and the combined branch passes the full validation matrix.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Final review and release hygiene for the combined dependency batch.

- [ ] T023 Review the final diffs in `solune/backend/pyproject.toml`, `solune/backend/uv.lock`, `solune/frontend/package.json`, and `solune/frontend/package-lock.json` to confirm no application, test, or config edits slipped into the dependency-only batch
- [ ] T024 [P] Cross-check the applied/skipped summary against `/home/runner/work/solune/solune/specs/006-dependabot-updates/research.md`, `/home/runner/work/solune/solune/specs/006-dependabot-updates/quickstart.md`, and the final diffs in `solune/backend/pyproject.toml`, `solune/backend/uv.lock`, `solune/frontend/package.json`, and `solune/frontend/package-lock.json`
- [ ] T025 Open the combined PR for the validated diffs in `solune/backend/pyproject.toml`, `solune/backend/uv.lock`, `solune/frontend/package.json`, and `solune/frontend/package-lock.json`, then close only the superseded Dependabot PRs whose exact updates are represented there

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 and blocks all package-update execution
- **User Story 1 (Phase 3)**: Depends on Phase 2
- **Polish (Phase 4)**: Depends on Phase 3

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Phase 2 and delivers the full MVP by itself

### Within User Story 1

- Execute tasks in semver order: patch (`T007`-`T010`) → minor dev (`T011`-`T015`) → minor runtime (`T016`-`T019`) → major (`T020`)
- Treat each package task as one-update-at-a-time work: edit manifest, regenerate lock, run the matching validation loop, keep or revert
- Run `T021` only after every package has been accepted or skipped
- Run `T022` only after `T021` passes

### Parallel Opportunities

- `T002` and `T003` can run in parallel during setup
- `T004`, `T005`, and `T006` can run in parallel during foundational work
- `T023` and `T024` can run in parallel after the combined validation succeeds
- **Do not parallelize `T007`-`T020`**; the feature plan requires one dependency update at a time for attributable validation and rollback

---

## Parallel Example: User Story 1

```bash
# Parallel preparation before package execution:
Task: "T004 Prepare the backend update loop for solune/backend/pyproject.toml and solune/backend/uv.lock"
Task: "T005 Prepare the frontend update loop for solune/frontend/package.json and solune/frontend/package-lock.json"
Task: "T006 Establish the applied/skipped update inventory for the four mutable dependency files"

# Serial package execution required after preparation:
Task: "T007 Apply pytest update"
Task: "T008 Apply happy-dom update"
Task: "..."
Task: "T020 Evaluate pytest-randomly update"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Execute Phase 3 in semver order, one dependency at a time
4. Run the combined validation in `T021`
5. Prepare the final PR payload in `T022`

### Incremental Delivery

1. Apply and validate all patch updates first
2. Continue with minor dev updates
3. Continue with minor runtime updates
4. Evaluate the major update last and skip it if it needs migration work
5. Finish with final combined validation and PR assembly

### Parallel Team Strategy

1. One maintainer handles `T004` while another handles `T005`/`T006`
2. After Phase 2, assign a single owner to `T007`-`T020` so the accumulation branch stays serialized
3. Split `T023` and `T024` across reviewers before `T025`

---

## Notes

- `[P]` tasks are limited to preparation and review work because package application is intentionally serialized
- Every user story task references the mutable dependency files it changes or validates
- No new production code, test files, or config files should be added for this feature
- Root `tasks.md` and `specs/006-dependabot-updates/tasks.md` must stay identical
