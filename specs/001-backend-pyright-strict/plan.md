# Implementation Plan: Tighten Backend Pyright (standard → strict, gradually)

**Branch**: `001-backend-pyright-strict` | **Date**: 2026-04-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-backend-pyright-strict/spec.md`

## Summary

Raise backend Pyright type-checking from `standard` to `strict` in four reviewable phases: (1) safety-net diagnostic settings + mirror to test config, (2) per-tree `strict = [...]` floor on `src/api`, `src/models`, `src/services/agents`, (3) global `typeCheckingMode = "strict"` with auditable `# pyright: basic — reason: …` pragmas on enumerated legacy modules and an ADR, (4) burn-down gate (pre-commit + CI) that refuses new pragmas inside the floor and prints the global pragma count. Each phase ships as its own PR; CI's existing `uv run pyright src` step picks up `pyproject.toml` changes automatically.

## Technical Context

**Language/Version**: Python 3.13 (per `[tool.pyright] pythonVersion = "3.13"` in `solune/backend/pyproject.toml`)
**Primary Dependencies**: Pyright (invoked via `uv run pyright`); FastAPI/Starlette (typing surface for `Depends()`); `aiosqlite` (typing surface for `Row`); `githubkit` and `agent_framework_github_copilot` (third-party libraries with partial type stubs in `solune/backend/src/typestubs/`)
**Storage**: N/A — tooling/configuration change. Touches `solune/backend/pyproject.toml` (`[tool.pyright]` block at line 119) and `solune/backend/pyrightconfig.tests.json`.
**Testing**: Validation is by `uv run pyright` exit status, `uv run pyright --outputjson | jq '.generalDiagnostics | length'`, and canary commits on a throwaway branch (per spec Acceptance Scenarios). No new pytest tests are added; tests config (`pyrightconfig.tests.json`) keeps `typeCheckingMode = "off"` per FR-011.
**Target Platform**: CI runs Pyright on `ubuntu-latest` via `.github/workflows/ci.yml` (lines 50–54: `uv run pyright src` and `uv run pyright -p pyrightconfig.tests.json`); local developer feedback loop is `cd solune/backend && uv run pyright`.
**Project Type**: Web application — `solune/backend/` (Python) + `solune/frontend/` (TypeScript). This feature touches the backend tree only.
**Performance Goals**: Local Pyright feedback-loop wall-clock MUST NOT increase by more than 25% between the pre-Phase-1 baseline and the post-Phase-3 state (SC-005). Strict mode marginally widens the analysis surface; baseline measurement is captured in Phase 0 research.
**Constraints**: `uv run pyright` MUST exit zero on the resulting branch at each phase boundary (FR-003). `pyrightconfig.tests.json typeCheckingMode` MUST remain `"off"` across all phases (FR-011). No `# pyright: off` allowed as a downgrade — only `# pyright: basic — reason: …` (FR-007). CI invokes Pyright with the positional `src` argument, so `[tool.pyright] include = ["src"]` is effectively redundant at runtime; `strict = [...]` still applies because Pyright resolves it relative to the project root.
**Scale/Scope**: Backend is ~80 modules under `solune/backend/src/` (api/, models/, services/ with ~50 sub-modules, middleware/, migrations/, prompts/, plus top-level `main.py`, `config.py`, `dependencies.py`, `utils.py`). The strict floor covers `src/api/` (~10 files), `src/models/` (small), and `src/services/agents/` (small subset of services/). Two pre-existing `# type: ignore[reportGeneralTypeIssues]` comments live at `src/services/agent_provider.py:501` and `src/services/plan_agent_provider.py:207`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
|---|---|
| **I. Specification-First Development** | ✅ `spec.md` exists with prioritized P1–P3 user stories, Given-When-Then acceptance scenarios per story, explicit Independent Test sections, edge cases, and bounded scope (4 phases, named trees only). |
| **II. Template-Driven Workflow** | ✅ `spec.md` and this `plan.md` follow `.specify/templates/`. No ad-hoc sections beyond the templates. |
| **III. Agent-Orchestrated Execution** | ✅ This artifact is the `/speckit.plan` output; it explicitly hands off to `/speckit.tasks` (the spec-kit workflow phase, separate from the four feature phases). |
| **IV. Test Optionality with Clarity** | ✅ Feature is a tooling/config change; validation is by Pyright exit status and canary diffs (per spec Acceptance Scenarios). No pytest test suite is added. The decision is recorded in the spec's Assumptions section and reaffirmed here: tests config keeps `typeCheckingMode = "off"` per FR-011. |
| **V. Simplicity and DRY** | ✅ Burn-down gate uses an existing tool (`grep`) per the spec's "no new tool added" decision. Per-file `# pyright: basic` is preferred over global `exclude` because it co-locates the debt with the code. The four-phase split is the simplest sequence that keeps each PR reviewable; the alternative (one mega-PR) was explicitly rejected in the spec. |

**Result**: PASS — proceed to Phase 0. No entries in Complexity Tracking.

### Post-Design Re-check (after Phase 1 artifacts)

Re-evaluated after generating `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`. No new abstractions, no new tools, no test suite added. Constraints still satisfied. **Result**: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/001-backend-pyright-strict/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (configuration entities)
├── quickstart.md        # Phase 1 output (per-phase verification recipes)
├── contracts/
│   ├── pyright-config-contract.md      # Required keys/values in [tool.pyright] per phase
│   ├── pragma-contract.md              # Format and placement rules for # pyright: basic
│   └── burn-down-gate-contract.md      # Pre-commit/CI gate inputs and exit semantics
├── checklists/
│   └── requirements.md  # Created during /speckit.specify
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created here)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── pyproject.toml                  # [tool.pyright] block at line 119 — primary edit target
│   ├── pyrightconfig.tests.json        # Mirror reportUnnecessaryTypeIgnoreComment; mode stays "off"
│   └── src/
│       ├── api/                        # Strict floor (Phase 2)
│       ├── models/                     # Strict floor (Phase 2)
│       ├── services/
│       │   ├── agents/                 # Strict floor (Phase 2)
│       │   ├── github_projects/        # Candidate Phase 3 # pyright: basic
│       │   ├── copilot_polling/        # Candidate Phase 3 # pyright: basic
│       │   ├── agent_provider.py       # Holds existing # type: ignore at line 501
│       │   ├── plan_agent_provider.py  # Holds existing # type: ignore at line 207
│       │   └── chat_agent.py           # Candidate Phase 3 # pyright: basic
│       ├── main.py                     # Candidate Phase 3 # pyright: basic
│       └── typestubs/                  # May be augmented in Phase 2 for githubkit/copilot
├── docs/
│   └── decisions/                      # Phase 3 ADR lands here
└── scripts/
    └── pre-commit                      # Phase 4 burn-down gate hook target

.github/workflows/
└── ci.yml                              # Phase 4 burn-down step + pragma-count print added
                                        # (Pyright steps already present at lines 50–54)
```

**Structure Decision**: Single web-application backend. All source edits are confined to `solune/backend/`; CI/pre-commit edits are in `.github/workflows/ci.yml` and `solune/scripts/pre-commit`; the Phase 3 ADR lives under `solune/docs/decisions/` (existing convention per workspace structure). No new directories are created.

## Complexity Tracking

> No constitutional violations to justify. Section intentionally empty.
