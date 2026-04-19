# Implementation Plan: Apply All Safe Dependabot Updates

**Branch**: `003-dependabot-updates` | **Date**: 2026-04-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-dependabot-updates/spec.md`

## Summary

Plan and execute a repository-wide Dependabot batching workflow for Boykai/solune that (1) discovers and prioritizes all open Dependabot PRs across the configured ecosystems, (2) applies one safe dependency update at a time with ecosystem-appropriate lockfile regeneration and repo verification, and (3) combines only the successful updates into a single PR. The current live repository state has zero open Dependabot-authored PRs, so the design must explicitly support a no-op completion path without creating an empty batch PR.

## Technical Context

**Language/Version**: Python `>=3.12` / Pyright `3.13` for `solune/backend`, TypeScript `~6.0.2` + Node.js `20` for `solune/frontend`, plus GitHub Actions YAML and Dockerfiles for infrastructure dependency updates  
**Primary Dependencies**: `uv`-managed backend dependencies in `solune/backend/pyproject.toml`, `npm`-managed frontend dependencies in `solune/frontend/package.json`, pinned GitHub Actions in `.github/workflows/*.yml`, Docker base images in `solune/backend/Dockerfile` and `solune/frontend/Dockerfile`, and Dependabot configuration in `.github/dependabot.yml`  
**Storage**: N/A for application data; the workflow mutates dependency manifests, lockfiles, workflow YAML, and Dockerfiles only  
**Testing**: Existing CI commands are the acceptance bar: backend `uv sync --locked --extra dev`, `pip-audit`, `ruff`, `bandit`, `pyright`, and `pytest`; frontend `npm ci`, `npm audit`, `eslint`, `tsc`, `vitest`, and `vite build`; repo-wide `bash solune/scripts/validate-contracts.sh`, Docker builds + Trivy, docs lint, and diagram validation  
**Target Platform**: GitHub Actions on `ubuntu-latest`, local verification in the repo checkout, and Docker image builds for backend/frontend  
**Project Type**: Web application monorepo with separate backend and frontend dependency graphs plus repo-level workflow/infrastructure dependencies  
**Performance Goals**: Evaluate every open Dependabot PR within one operator session, preserving existing runtime behavior and avoiding unnecessary repeated work by prioritizing isolated patch updates before overlapping or major updates  
**Constraints**: Apply updates in patch → minor → major order; regenerate `solune/backend/uv.lock` and `solune/frontend/package-lock.json` with ecosystem tooling rather than manual edits; do not change application/test logic; do not close or delete non-Dependabot branches; preserve repo-specific install constraints such as frontend `.npmrc` `legacy-peer-deps=true` and backend `uv` prerelease allowance  
**Scale/Scope**: Dependabot is configured for five update streams (pip, npm, docker for backend, docker for frontend, and GitHub Actions). The mutable dependency surfaces are concentrated in `.github/`, `solune/backend/`, and `solune/frontend/`. As of 2026-04-19, the live open-PR inventory contains no Dependabot-authored PRs, so the zero-update edge case is in-scope and must be handled cleanly

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
|---|---|
| **I. Specification-First Development** | ✅ `spec.md` exists for `003-dependabot-updates` with four prioritized user stories, independent test guidance, acceptance scenarios, edge cases, and measurable outcomes. |
| **II. Template-Driven Workflow** | ✅ This plan and the Phase 0/1 artifacts stay within the prescribed Speckit template structure: `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, and `contracts/`. |
| **III. Agent-Orchestrated Execution** | ✅ The workflow is decomposed into explicit phases: research, design/contracts, then later `/speckit.tasks` and implementation. GitHub discovery and CI inspection are treated as first-class workflow inputs rather than ad-hoc manual notes. |
| **IV. Test Optionality with Clarity** | ✅ No new automated tests are introduced by the planning phase. The implementation plan relies on the repository's existing CI/build/test commands as the verification contract for each dependency update. |
| **V. Simplicity and DRY** | ✅ The plan reuses existing manifests, lockfiles, CI commands, and Dependabot configuration. It avoids introducing a new update framework or custom dependency-management layer, and keeps overlap handling data-driven. |

**Result**: PASS — proceed to Phase 0. No constitutional violations require Complexity Tracking entries.

### Post-Design Re-check (after Phase 1 artifacts)

Re-checked after generating `research.md`, `data-model.md`, `quickstart.md`, and the `contracts/` documents. The design still uses only the repository's current dependency surfaces and verification commands, does not require new runtime APIs, and keeps the no-op / skipped-update paths explicit. **Result**: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/003-dependabot-updates/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── discovery-prioritization-contract.md
│   ├── verification-matrix-contract.md
│   └── batch-pr-report-contract.md
├── checklists/
│   └── requirements.md  # Created during /speckit.specify
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created here)
```

### Source Code (repository root)

```text
.github/
├── dependabot.yml                    # Ecosystem inventory and update roots
└── workflows/
    └── ci.yml                        # Canonical verification matrix

solune/
├── backend/
│   ├── Dockerfile                    # Python base image / uv binary pins
│   ├── pyproject.toml                # Backend dependency manifest
│   ├── uv.lock                       # Backend lockfile to regenerate with uv
│   └── tests/                        # Backend verification suite referenced by CI
├── frontend/
│   ├── .npmrc                        # legacy-peer-deps compatibility flag
│   ├── Dockerfile                    # Node/nginx base image pins
│   ├── package.json                  # Frontend dependency manifest
│   ├── package-lock.json             # Frontend lockfile to regenerate with npm
│   └── src/                          # Frontend code validated by type-check/tests/build
└── scripts/
    └── validate-contracts.sh         # Cross-stack OpenAPI/type generation validation
```

**Structure Decision**: The feature is operationally centered on repository metadata and dependency manifests rather than application logic. Implementation work will touch `.github/dependabot.yml` inputs, repo workflow files for GitHub Actions updates, backend/frontend manifests and lockfiles, and Dockerfiles for image-base bumps. Existing source trees and tests are verification targets, not design targets.

## Complexity Tracking

> No constitutional violations to justify. Section intentionally empty.
