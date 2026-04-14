# Implementation Plan: Dependabot Updates

**Branch**: `006-dependabot-updates` | **Date**: 2026-04-14 | **Spec**: [/home/runner/work/solune/solune/specs/006-dependabot-updates/spec.md](/home/runner/work/solune/solune/specs/006-dependabot-updates/spec.md)
**Input**: Feature specification from `/home/runner/work/solune/solune/specs/006-dependabot-updates/spec.md`

## Summary

Prepare the execution plan for applying all safe open Dependabot updates in `/home/runner/work/solune/solune`. The current inventory contains 14 open Dependabot pull requests across the Python/uv backend and npm frontend. Execution will group updates by ecosystem, prioritize them by semver risk (patch → minor → major), validate every accepted change with the repository's existing lint/type-check/test/build commands, and combine only successful updates into one PR titled `chore(deps): apply Dependabot batch update`. Any update that requires application code changes or fails verification will be skipped and documented.

## Technical Context

**Language/Version**: Python `>=3.12` in `/home/runner/work/solune/solune/solune/backend/pyproject.toml`; TypeScript `~6.0.2` and React `^19.2.5` in `/home/runner/work/solune/solune/solune/frontend/package.json`
**Primary Dependencies**: `uv` + `pytest`/`ruff`/`pyright` for backend verification; `npm` + `eslint`/`vitest`/`vite` for frontend verification; GitHub Dependabot PR metadata for update discovery
**Storage**: N/A — only dependency manifests and lock files change (`/home/runner/work/solune/solune/solune/backend/pyproject.toml`, `/home/runner/work/solune/solune/solune/backend/uv.lock`, `/home/runner/work/solune/solune/solune/frontend/package.json`, `/home/runner/work/solune/solune/solune/frontend/package-lock.json`)
**Testing**: Backend: `uv run ruff check src/ tests/`, `uv run ruff format --check src/ tests/`, `uv run pyright src/`, `uv run pytest tests/unit/ -q`; Frontend: `npm run lint`, `npm run type-check`, `npm run test`, `npm run build`
**Target Platform**: GitHub repository maintenance workflow on the default branch (`origin/main`) with one combined dependency PR
**Project Type**: Dependency-maintenance / release-hygiene workflow spanning existing backend and frontend projects
**Performance Goals**: Minimize CI churn and rollback effort by applying one dependency update at a time, keeping every validation cycle attributable to a single package change
**Constraints**: No application/test/config code changes beyond dependency version updates; regenerate lock files with native tools only; rebase each change on the latest default branch state; skip any major/runtime bump that needs migration work; retain one combined PR with applied and skipped update reporting
**Scale/Scope**: 14 open Dependabot PRs, 2 ecosystems, 4 mutable dependency files, and one final batch PR

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Specification-First Development**: PASS — `/home/runner/work/solune/solune/specs/006-dependabot-updates/spec.md` captures the required workflow, constraints, and success criteria.
- **II. Template-Driven Workflow**: PASS — This plan and its companion artifacts stay in `/home/runner/work/solune/solune/specs/006-dependabot-updates/` and follow the canonical Speckit structure.
- **III. Agent-Orchestrated Execution**: PASS — The work is decomposed into discovery, prioritization, per-update verification, and batch-PR closure steps with explicit handoffs captured in this plan.
- **IV. Test Optionality with Clarity**: PASS — No new tests are introduced; only the repository's existing verification commands are used as acceptance gates.
- **V. Simplicity and DRY**: PASS — The plan reuses existing manifests, lock generators, CI-aligned commands, and GitHub PR metadata with no new automation surface.

**Post-Phase-1 Re-check**: PASS — Phase 0 research resolved the only planning ambiguity (current manifest drift versus Dependabot PR titles for `pytest`), and Phase 1 artifacts remain within the existing repo/tooling model.

## Project Structure

### Documentation (this feature)

```text
/home/runner/work/solune/solune/specs/006-dependabot-updates/
├── plan.md              # This file
├── research.md          # Phase 0 output — inventory, overlap, and verification decisions
├── data-model.md        # Phase 1 output — dependency-update entities and execution metadata
├── quickstart.md        # Phase 1 output — operator runbook for executing the batch safely
├── contracts/
│   └── dependabot-batch-update.openapi.yaml
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Files (touched during implementation)

```text
/home/runner/work/solune/solune/
├── .github/workflows/ci.yml                  # Existing CI expectations referenced by the plan
└── solune/
    ├── backend/
    │   ├── pyproject.toml                    # Python dependency constraints
    │   └── uv.lock                           # Regenerated with `uv lock`
    └── frontend/
        ├── package.json                      # npm dependency constraints
        └── package-lock.json                 # Regenerated with `npm install`
```

**Structure Decision**: No new production code or directories are introduced. Execution touches only the existing dependency manifests/lock files above, while planning artifacts stay isolated under `/home/runner/work/solune/solune/specs/006-dependabot-updates/`.

## Phase Execution Plan

### Phase 0 — Research & Discovery

**Goal**: Resolve planning unknowns before any dependency changes are attempted.

1. Enumerate all open Dependabot PRs in `Boykai/solune` and group them by ecosystem.
2. Capture current → target version deltas from PR titles/diffs.
3. Compare PR data against the checked-out manifests to catch branch drift before execution.
4. Confirm repository-native verification commands for backend and frontend.
5. Record overlap analysis and lock-file regeneration strategy.

**Outputs**: `/home/runner/work/solune/solune/specs/006-dependabot-updates/research.md`

### Phase 1 — Design & Operator Handoff

**Goal**: Turn the discovered inventory into an execution-ready handoff.

1. Model the units of work (`DependencyUpdate`, `VerificationRun`, `BatchUpdatePlan`).
2. Encode the operator workflow in an OpenAPI contract for discovery, evaluation, skip reporting, and batch PR assembly.
3. Produce an execution quickstart that uses absolute repository paths and repo-native commands.
4. Refresh agent context from the completed plan.

**Outputs**: `/home/runner/work/solune/solune/specs/006-dependabot-updates/data-model.md`, `/home/runner/work/solune/solune/specs/006-dependabot-updates/contracts/dependabot-batch-update.openapi.yaml`, `/home/runner/work/solune/solune/specs/006-dependabot-updates/quickstart.md`

### Phase 2 — Execution Plan for the Follow-on Implementer

**Goal**: Define the exact order in which dependency updates should be applied.

#### 2.1 Discovery Baseline

| Ecosystem | Open PRs | Notes |
|-----------|----------|-------|
| pip / uv | 10 | Backend runtime + dev dependencies in `/home/runner/work/solune/solune/solune/backend/pyproject.toml` |
| npm | 4 | Frontend runtime + dev dependencies in `/home/runner/work/solune/solune/solune/frontend/package.json` |

#### 2.2 Prioritized Application Order

1. **Patch bumps first** — `pytest`, `happy-dom`, `typescript-eslint`, `react-router-dom`
2. **Minor dev-dependency bumps** — `pytest-cov`, `freezegun`, `pip-audit`, `mutmut`, `bandit`
3. **Minor runtime bumps** — `pynacl`, `uvicorn`, `agent-framework-core`, `@tanstack/react-query`
4. **Major bumps last** — `pytest-randomly`

Within each tier, execute updates that do not overlap first. Current research found no overlapping package constraints, so ordering is driven by ecosystem batching and runtime risk.

#### 2.3 Per-Update Workflow

1. Refresh the default branch (`origin/main`) and start from a clean branch state.
2. Apply **one** Dependabot change to the appropriate manifest.
3. Regenerate the matching lock file with the ecosystem-native tool.
4. Run the ecosystem's existing install + lint + type-check + test + build commands.
5. If verification passes, keep the manifest/lock diff staged for the final batch commit.
6. If verification fails, revert that update and append a skipped-update note with the package, target version, and one-line failure summary.
7. Re-sync from the latest default branch before evaluating the next update.

#### 2.4 Validation Matrix

| Area | Command | When |
|------|---------|------|
| Backend lock refresh | `cd /home/runner/work/solune/solune/solune/backend && uv lock && uv sync --extra dev` | After each backend manifest edit |
| Backend lint | `cd /home/runner/work/solune/solune/solune/backend && uv run ruff check src/ tests/` | Every backend update |
| Backend format check | `cd /home/runner/work/solune/solune/solune/backend && uv run ruff format --check src/ tests/` | Every backend update |
| Backend types | `cd /home/runner/work/solune/solune/solune/backend && uv run pyright src/` | Every backend update |
| Backend tests | `cd /home/runner/work/solune/solune/solune/backend && uv run pytest tests/unit/ -q` | Every backend update |
| Frontend lock refresh | `cd /home/runner/work/solune/solune/solune/frontend && npm install` | After each frontend manifest edit |
| Frontend lint | `cd /home/runner/work/solune/solune/solune/frontend && npm run lint` | Every frontend update |
| Frontend types | `cd /home/runner/work/solune/solune/solune/frontend && npm run type-check` | Every frontend update |
| Frontend tests | `cd /home/runner/work/solune/solune/solune/frontend && npm run test` | Every frontend update |
| Frontend build | `cd /home/runner/work/solune/solune/solune/frontend && npm run build` | Every frontend update |
| Final combined verification | Run the full backend matrix and the full frontend matrix again after all successful updates are staged | Before creating the batch PR |

#### 2.5 Risk Notes

| Package | Risk | Mitigation |
|---------|------|------------|
| `pytest` | Dependabot title shows `9.0.2 → 9.0.3` while the current checkout still shows `>=9.0.0` | Refresh from `origin/main` before applying; use the live manifest diff as the source of truth |
| `pynacl` | Runtime crypto dependency | Treat any crypto-related test failure as a skip condition |
| `uvicorn` | Runtime server dependency | Watch for startup/type-check regressions and skip if behavior changes require code edits |
| `agent-framework-core` | Beta → stable transition | Prioritize `pyright` and unit-test results before accepting |
| `pytest-randomly` | Major bump | Inspect release notes first and skip if plugin/config migration is needed |

## Decisions

| Decision | Rationale |
|----------|-----------|
| Process one dependency at a time | Keeps failures attributable to a single package and simplifies rollback |
| Re-check the default branch before every update | Prevents stale Dependabot branches or title drift from producing incorrect version edits |
| Use the repo's full validation commands, not tests alone | Dependency updates can break lint, typing, or build steps even when unit tests pass |
| Keep successful updates in one final PR | Matches the issue requirements and preserves a single review surface |
| Skip rather than patch around breaking major/runtime bumps | The issue explicitly disallows application-code migrations as part of this dependency batch |

## Complexity Tracking

> No constitution violations found. No complexity justification is required.
