# Feature Specification: Fix Mutation Testing Infrastructure

**Feature Branch**: `005-fix-mutation-tests`
**Created**: 2026-04-02
**Status**: Draft
**Input**: GitHub Issue #518 — Backend mutation blocked by infrastructure bug; frontend mutation too large for single job

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Backend mutmut workspace parity (Priority: P1)

A developer runs backend mutation testing and every shard completes successfully, producing real kill/survivor reports instead of collapsing into "not checked" noise caused by missing app-template assets.

**Why this priority**: Every backend shard currently aborts on the same app-template test failure, making all existing mutation reports meaningless. This must be fixed before any mutation analysis is actionable.

**Independent Test**: Run `python scripts/run_mutmut_shard.py --shard app-and-data --max-children 1` from `backend/` and confirm no "Templates directory does not exist" warning appears; report contains real kills and survivors.

**Acceptance Scenarios**:

1. **Given** pyproject.toml `[tool.mutmut].also_copy` does NOT include `templates/`, **When** mutmut creates the mutant workspace, **Then** `registry.py` fails to find `templates/app-templates/` and `test_agent_tools.py` tests abort.
2. **Given** pyproject.toml `[tool.mutmut].also_copy` includes `templates/`, **When** mutmut creates the mutant workspace, **Then** `registry.py` resolves `templates/app-templates/` correctly and `test_agent_tools.py` tests pass under mutation.
3. **Given** the `templates/` directory is copied, **When** `template_files.py` resolves its workspace root, **Then** path resolution still works correctly (no regression from the new also_copy entry).

---

### User Story 2 — Backend shard drift resolution (Priority: P1)

The CI mutation workflow runs the same set of shards defined in `run_mutmut_shard.py`, so no shards are silently skipped.

**Why this priority**: `run_mutmut_shard.py` defines 5 shards but `mutation-testing.yml` only runs 4, hiding the `api-and-middleware` shard from CI entirely.

**Independent Test**: Compare the shard list in `run_mutmut_shard.py` against `mutation-testing.yml` matrix entries; they must match exactly.

**Acceptance Scenarios**:

1. **Given** `run_mutmut_shard.py` defines `api-and-middleware`, **When** the mutation workflow runs, **Then** a CI job for `api-and-middleware` is created and publishes an artifact.
2. **Given** `testing.md` documents backend mutation CI, **When** the shard list changes, **Then** `testing.md` reflects all five shards.

---

### User Story 3 — Frontend mutation sharding (Priority: P2)

Frontend mutation testing is split into 3–4 CI shards so each finishes well under the 3-hour timeout and produces an individual report artifact.

**Why this priority**: The current monolithic frontend mutation run produces 6,580 mutants from 73 files, times out at ~71%, and yields an unusable report. Sharding makes results actionable.

**Independent Test**: Run each Stryker shard locally with `npx stryker run -c stryker-<shard>.config.mjs` and confirm each completes under 90 minutes.

**Acceptance Scenarios**:

1. **Given** `stryker.config.mjs` covers all hooks and lib, **When** frontend mutation CI runs, **Then** 4 shard jobs each upload separate report artifacts.
2. **Given** developer-facing `package.json` commands for focused mutation, **When** a developer runs `npm run test:mutate:hooks-board`, **Then** only board/polling hook mutants are generated.

---

### User Story 4 — Frontend test-utils bug fix (Priority: P2)

`renderWithProviders()` in `test-utils.tsx` nests providers correctly instead of rendering `children` twice.

**Why this priority**: The double-render bug affects both correctness and test runtime across the entire frontend test suite.

**Independent Test**: Inspect that `Wrapper` in `renderWithProviders` renders `children` exactly once, nested inside all providers.

**Acceptance Scenarios**:

1. **Given** the current `Wrapper` renders `{children}` inside both `ConfirmationDialogProvider` and `TooltipProvider`, **When** `renderWithProviders(<Comp />)` is called, **Then** `<Comp />` appears twice in the DOM.
2. **Given** the fixed `Wrapper` nests `TooltipProvider` inside `ConfirmationDialogProvider` (or vice versa), **When** `renderWithProviders(<Comp />)` is called, **Then** `<Comp />` appears exactly once.

---

### User Story 5 — Developer-facing mutation commands and documentation (Priority: P3)

Developers have focused mutation commands in `package.json` and documentation in `testing.md` so local reproduction does not require re-running all 6,580 mutants or all backend modules.

**Why this priority**: Without focused commands, developers cannot efficiently iterate on specific survivor-heavy files.

**Independent Test**: Run `npm run test:mutate:hooks-board` and confirm it only mutates the expected glob scope.

**Acceptance Scenarios**:

1. **Given** new `package.json` scripts exist, **When** `npm run test:mutate:hooks-board` is run, **Then** Stryker mutates only `src/hooks/useAdaptivePolling.ts`, `src/hooks/useBoardProjection.ts`, and related board/polling hooks.
2. **Given** `testing.md` is updated, **When** a developer reads the mutation testing section, **Then** they find instructions for each shard and focused local commands.
3. **Given** `CHANGELOG.md` exists, **When** the infrastructure changes are complete, **Then** entries under `[Unreleased]` describe the new shard layout, commands, and bug fixes.

---

### Edge Cases

- What happens when mutmut runs with a shard whose paths don't exist? → `run_mutmut_shard.py` raises a `RuntimeError` during `paths_to_mutate` replacement.
- What if Stryker shard config references files that have been moved? → The shard produces 0 mutants, which is a clear signal to update the config.
- What if `templates/` directory is empty? → `registry.py` logs a warning and returns empty; tests that depend on templates fail cleanly.

## Requirements *(mandatory)*

### Functional Requirements

1. `pyproject.toml` `[tool.mutmut].also_copy` MUST include `templates/` so app-template assets are present in the mutant workspace.
2. `mutation-testing.yml` backend matrix MUST include all shards defined in `run_mutmut_shard.py` (currently 5).
3. Frontend mutation testing MUST be split into 3–4 CI shards in `mutation-testing.yml`.
4. `package.json` MUST include focused mutation commands for each frontend shard area.
5. `test-utils.tsx` `renderWithProviders()` MUST render `children` exactly once with all providers nested.
6. `testing.md` MUST document the new shard layout and focused commands.
7. `CHANGELOG.md` MUST reflect all infrastructure changes under `[Unreleased]`.

### Non-Functional Requirements

1. Each frontend mutation shard MUST complete well under the 3-hour CI timeout.
2. Backend mutation shards MUST produce real kill/survivor reports after the parity fix.
3. No mutation threshold lowering or permanent scope reduction is permitted.

## Scope

### In Scope

- Backend mutmut workspace parity (`pyproject.toml` `also_copy`)
- Backend shard drift fix (`mutation-testing.yml` + `run_mutmut_shard.py` alignment)
- Frontend Stryker sharding (config + workflow)
- Frontend `test-utils.tsx` double-render bug fix
- Developer-facing focused mutation commands
- Documentation updates (`testing.md`, `CHANGELOG.md`)
- Backend bugs found during mutation hardening (path-dependent failures, real behavioral issues)

### Out of Scope

- Writing mutation-killer tests from current (broken) reports
- Tuning property-test breadth (deferred until shard reports available)
- Lowering thresholds or permanently shrinking scope
- Survivor-specific test authoring (blocked until shards produce actionable data)
