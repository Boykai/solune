# Implementation Plan: Fix Mutation Tests

**Branch**: `001-fix-mutation-tests` | **Date**: 2026-04-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-fix-mutation-tests/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Fix the mutation testing infrastructure for both backend and frontend. Backend mutation is blocked by a workspace parity bug: mutmut's `also_copy` in `pyproject.toml` omits the `templates/app-templates/` directory that `registry.py` resolves via `Path(__file__).resolve().parents[3]`, causing every backend shard to abort on `test_agent_tools.py`. Additionally, the CI workflow runs only four of the five defined backend shards (missing `api-and-middleware`). Frontend mutation is too large for a single 3-hour CI job (6,580+ mutants from 73 files), requiring sharding. Secondary fixes include a confirmed double-render bug in `test-utils.tsx`, missing focused mutation commands, and documentation drift.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.x (frontend)
**Primary Dependencies**: FastAPI, mutmut (backend mutation); React 18, Stryker v9.6.0, Vitest (frontend mutation)
**Storage**: N/A (infrastructure/CI changes only)
**Testing**: pytest (backend), Vitest + Stryker (frontend mutation), Playwright (frontend e2e)
**Target Platform**: GitHub Actions CI (Ubuntu runners)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: Each CI mutation shard completes within 3-hour time limit; focused commands complete in under 5 minutes
**Constraints**: 3-hour CI job time limit; weekly mutation schedule (Sundays 2 AM UTC); mutmut workspace must mirror all files needed by test suite
**Scale/Scope**: Backend: 5 shards covering `src/services/`, `src/api/`, `src/middleware/`, `src/utils.py`; Frontend: 6,580+ mutants from `src/hooks/**/*.ts` and `src/lib/**/*.ts` (73 source files), to be split into 3–4 shards

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First Development | ✅ PASS | `spec.md` contains 7 prioritized user stories with Given-When-Then acceptance scenarios, independent test criteria, and edge cases |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates in `.specify/templates/` |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan agent produces plan.md, research.md, data-model.md, contracts/, quickstart.md; tasks agent follows |
| IV. Test Optionality with Clarity | ✅ PASS | Tests are explicitly required by the specification (this feature *is* about mutation testing); new deterministic tests are mandated by FR-008 |
| V. Simplicity and DRY | ✅ PASS | Changes are surgical config/workflow edits plus targeted test additions; no new abstractions introduced. The test-utils fix (FR-007) *reduces* complexity by eliminating the double-render pattern |

**Gate Result**: All principles satisfied. No violations to justify. Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-fix-mutation-tests/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── pyproject.toml                          # mutmut also_copy config (FR-001, FR-002)
│   ├── scripts/
│   │   └── run_mutmut_shard.py                 # 5 shard definitions (FR-003)
│   ├── src/
│   │   ├── api/                                # api-and-middleware shard target
│   │   ├── middleware/                          # api-and-middleware shard target
│   │   ├── services/
│   │   │   ├── agents/
│   │   │   │   └── registry.py → template_files.py  # path resolution (FR-001, FR-002)
│   │   │   └── app_templates/
│   │   │       └── registry.py                 # resolves templates/ via parents[3]
│   │   └── utils.py                            # api-and-middleware shard target
│   └── tests/
│       └── unit/
│           └── test_agent_tools.py             # app-template tests (FR-001)
├── frontend/
│   ├── package.json                            # focused mutation commands (FR-006)
│   ├── stryker.config.mjs                      # Stryker base config (FR-004)
│   ├── src/
│   │   ├── hooks/
│   │   │   ├── useAdaptivePolling.ts           # survivor cleanup target (FR-008)
│   │   │   └── useBoardProjection.ts           # survivor cleanup target (FR-008)
│   │   ├── lib/                                # lib/utils shard target
│   │   └── test/
│   │       └── test-utils.tsx                  # double-render bug (FR-007)
│   └── reports/mutation/                        # per-shard report output (FR-005)
├── templates/
│   └── app-templates/                          # MISSING from mutmut workspace (FR-001 root cause)
├── docs/
│   └── testing.md                              # shard documentation (FR-009)
├── CHANGELOG.md                                # infrastructure change log (FR-010)
└── .github/
    └── workflows/
        └── mutation-testing.yml                # CI workflow (FR-003, FR-004, FR-005)
```

**Structure Decision**: Web application layout. All changes are within the existing `solune/` monorepo structure. No new top-level directories. Changes touch CI workflow, backend config, frontend config, test utilities, documentation, and a small number of test files.

## Constitution Check — Post-Design Re-Evaluation

*Re-check after Phase 1 design artifacts are complete.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First Development | ✅ PASS | All 7 user stories from spec.md are addressed by the plan. Research resolved all unknowns. Contracts formalize the cross-artifact invariants. |
| II. Template-Driven Workflow | ✅ PASS | plan.md, research.md, data-model.md, contracts/, quickstart.md all follow template structure. |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan phase complete. Output handed off for tasks phase. Agent context file updated via `update-agent-context.sh copilot`. |
| IV. Test Optionality with Clarity | ✅ PASS | New tests mandated by FR-008 (survivor cleanup). Test-utils fix (FR-007) is a bug fix, not a new test requirement. |
| V. Simplicity and DRY | ✅ PASS | No new abstractions. Frontend sharding uses CLI overrides instead of multiple config files. Backend fix is a single `also_copy` entry. Provider fix reduces complexity. |

**Post-Design Gate Result**: All principles satisfied. No new violations introduced during design phase. Ready for tasks phase.

## Complexity Tracking

> No constitution violations detected. Table left empty per template guidance.
