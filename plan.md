# Implementation Plan: Reduce Broad-Except + Log + Continue Pattern

**Branch**: `002-reduce-broad-except` | **Date**: 2026-04-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-reduce-broad-except/spec.md`

## Summary

Drive two independent workstreams: (A) enable Ruff BLE001 to lint-enforce a ban on unjustified `except Exception` handlers, triage all ~568 existing violations into Narrow/Promote/Tagged buckets, and adopt a `# noqa: BLE001 — reason:` tag convention; (B) introduce a shared `best_effort` async helper in the GitHub-projects service layer to replace the ~50 repetitive "try → call → log → return fallback" wrappers concentrated in `pull_requests.py`, `projects.py`, `copilot.py`, and `issues.py`. Both workstreams are deliverable independently (FR-010).

## Technical Context

**Language/Version**: Python 3.13 (per `[tool.pyright] pythonVersion = "3.13"` in `solune/backend/pyproject.toml`)
**Primary Dependencies**: Ruff (linter, already in dev deps), githubkit (GitHub API client wrapping httpx), FastAPI/Starlette (web framework), aiosqlite (async SQLite)
**Storage**: N/A — lint configuration + code refactor. No schema changes.
**Testing**: pytest with `asyncio_mode = "auto"`. Existing test suite at `solune/backend/tests/` (unit, integration, e2e, property, fuzz, chaos, architecture). 75% coverage floor.
**Target Platform**: CI runs on `ubuntu-latest` via `.github/workflows/ci.yml`; local developer loop is `cd solune/backend && uv run ruff check`.
**Project Type**: Web application — `solune/backend/` (Python) + `solune/frontend/` (TypeScript). This feature touches the backend tree only.
**Performance Goals**: N/A — no runtime performance impact. Lint check time increase is negligible (BLE001 is a pattern-match rule with no import resolution).
**Constraints**: Zero production-behaviour changes (SC-006). Existing test suite must pass without regressions (FR-011). The two workstreams must be independently deliverable (FR-010).
**Scale/Scope**: ~568 `except Exception` handlers across ~87 files in `solune/backend/src/`. Top files: `pipeline.py` (47), `chat.py` (41), `orchestrator.py` (32), `app_service.py` (19), `main.py` (18). Domain-error helper targets ~50 handlers in `src/services/github_projects/` (pull_requests.py: 12, copilot.py: 14, issues.py: 15, projects.py: 11).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
|---|---|
| **I. Specification-First Development** | ✅ `spec.md` exists with prioritised P1–P4 user stories, Given-When-Then acceptance scenarios per story, explicit Independent Test sections, edge cases, and bounded scope (two workstreams, four user stories). |
| **II. Template-Driven Workflow** | ✅ `spec.md` and this `plan.md` follow `.specify/templates/`. No ad-hoc sections beyond the templates. |
| **III. Agent-Orchestrated Execution** | ✅ This artifact is the `/speckit.plan` output; it explicitly hands off to `/speckit.tasks` for task decomposition. |
| **IV. Test Optionality with Clarity** | ✅ Workstream A is a lint/config change validated by `ruff check` exit status. Workstream B introduces a helper that replaces existing behaviour 1:1 — validated by the existing test suite plus a targeted unit test for the helper itself. The spec does not mandate TDD. New tests are added only for the `best_effort` helper (novel code). |
| **V. Simplicity and DRY** | ✅ Workstream A uses an existing Ruff rule (BLE001) — no new tool. Workstream B extracts a single helper to eliminate ~50 duplicate try/except blocks (DRY improvement). The helper is intentionally narrow (GitHub-projects HTTP calls only) to avoid premature abstraction. |

**Result**: PASS — proceed to Phase 0. No entries in Complexity Tracking.

### Post-Design Re-check (after Phase 1 artifacts)

Re-evaluated after generating `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`. The `best_effort` helper is a single async function (not a class hierarchy). No new abstractions beyond what was specified. Lint enablement adds one line to `pyproject.toml`. All constraints still satisfied. **Result**: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/002-reduce-broad-except/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (configuration and code entities)
├── quickstart.md        # Phase 1 output (per-workstream verification recipes)
├── contracts/
│   ├── ruff-config-contract.md       # Required [tool.ruff.lint] state per workstream
│   ├── tag-convention-contract.md    # Format and placement rules for # noqa: BLE001
│   └── best-effort-helper-contract.md # API surface and behaviour of best_effort()
├── checklists/
│   └── requirements.md  # Created during /speckit.specify
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created here)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── pyproject.toml                          # [tool.ruff.lint] block at line 85 — add "BLE" to select
│   └── src/
│       ├── services/
│       │   ├── github_projects/
│       │   │   ├── service.py                  # _ServiceMixin base — host best_effort() helper
│       │   │   ├── pull_requests.py            # 12 except Exception → refactor to best_effort()
│       │   │   ├── projects.py                 # 11 except Exception → refactor to best_effort()
│       │   │   ├── copilot.py                  # 14 except Exception → refactor to best_effort()
│       │   │   └── issues.py                   # 15 except Exception → refactor to best_effort()
│       │   ├── copilot_polling/
│       │   │   ├── pipeline.py                 # 47 except Exception → triage (Narrow/Tagged)
│       │   │   ├── helpers.py                  # 16 except Exception → triage
│       │   │   └── recovery.py                 # 15 except Exception → triage
│       │   ├── workflow_orchestrator/
│       │   │   └── orchestrator.py             # 32 except Exception → triage
│       │   └── app_service.py                  # 19 except Exception → triage
│       ├── api/
│       │   └── chat.py                         # 41 except Exception → triage
│       ├── main.py                             # 18 except Exception → triage
│       └── exceptions.py                       # Existing exception hierarchy (unchanged)
└── docs/
    └── decisions/                              # ADR for tag convention (optional, per FR-005)
```

**Structure Decision**: Web-application backend. All source edits are confined to `solune/backend/`. Workstream A modifies `pyproject.toml` and every file containing `except Exception`. Workstream B adds `best_effort()` to the existing `service.py` mixin and refactors the four `github_projects/` service files. No new directories or packages are created.

## Complexity Tracking

> No constitutional violations to justify. Section intentionally empty.
