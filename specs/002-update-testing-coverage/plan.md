# Implementation Plan: Update Testing Coverage

**Branch**: `copilot/update-testing-coverage` | **Date**: 2026-04-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-update-testing-coverage/spec.md`

## Summary

Systematically improve test coverage across the Solune backend (Python/FastAPI) and frontend (React/TypeScript) codebases. The approach prioritizes files with the highest missing-line count and lowest coverage percentages first, uses modern pytest-asyncio and Testing Library patterns, raises coverage enforcement thresholds, audits e2e Playwright tests for staleness, and fixes bugs discovered during the process. This plan was informed by analysis of the existing `coverage.json` (backend: 79% line / 70% branch across 148 files) and the frontend vitest threshold configuration (50/44/41/50).

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript 6.0.2 (frontend)
**Primary Dependencies**: FastAPI 0.135+, React 19.2, Vite 8.0, Playwright 1.59
**Storage**: SQLite (aiosqlite) — no schema changes needed for this feature
**Testing**: pytest 9+ / pytest-asyncio / pytest-cov (backend), vitest 4.0 / @testing-library/react / Playwright (frontend)
**Target Platform**: Linux CI (GitHub Actions ubuntu-latest)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: Test suite completes in ≤10 min on CI (current baseline)
**Constraints**: No new testing frameworks; use only existing dependencies
**Scale/Scope**: 148 backend source files, ~186 frontend test files, 24 e2e spec files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate (Phase 0)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | spec.md created with prioritized user stories (US1-US5), acceptance criteria, and scope boundaries |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates from `.specify/templates/` |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan produced by speckit.plan agent; implementation delegated to speckit.implement |
| IV. Test Optionality with Clarity | ✅ PASS | Tests are the explicit subject of this feature — mandated by the feature specification |
| V. Simplicity and DRY | ✅ PASS | No new abstractions; tests target existing code using existing patterns |

### Post-Design Gate (Phase 1)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | research.md resolves all NEEDS CLARIFICATION items |
| II. Template-Driven Workflow | ✅ PASS | plan.md, research.md, data-model.md, contracts/, quickstart.md all generated |
| III. Agent-Orchestrated Execution | ✅ PASS | Clear handoff artifacts for speckit.tasks |
| IV. Test Optionality with Clarity | ✅ PASS | TDD not required for this feature; tests ARE the deliverable |
| V. Simplicity and DRY | ✅ PASS | No complexity violations identified |

## Project Structure

### Documentation (this feature)

```text
specs/002-update-testing-coverage/
├── spec.md                              # Feature specification
├── plan.md                              # This file (implementation plan)
├── research.md                          # Phase 0: coverage analysis and best practices
├── data-model.md                        # Phase 1: coverage target model and priority tiers
├── quickstart.md                        # Phase 1: commands and workflow guide
├── contracts/
│   ├── testing-standards.yaml           # Test quality and structure contracts
│   └── coverage-targets.yaml            # Coverage enforcement targets
└── tasks.md                             # Phase 2 output (NOT created by speckit.plan)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── api/              # 22 route modules (73.9% coverage — target: 82%)
│   │   ├── models/           # 26 model files (99.3% coverage — already excellent)
│   │   ├── services/         # 50+ service modules (60-93% coverage — primary target)
│   │   │   ├── agents/       # 3 files (60.8% — P1 priority)
│   │   │   ├── chores/       # 6 files (66.9% — P1 priority)
│   │   │   ├── copilot_polling/  # 12 files (78.2% — P2 priority)
│   │   │   ├── github_projects/  # 12 files (81.3% — P2 priority)
│   │   │   ├── workflow_orchestrator/ # 5 files (85.2% — P2 priority)
│   │   │   └── ...           # Other services (83.6%)
│   │   ├── middleware/       # 6 files (99.3% — already excellent)
│   │   └── migrations/       # Not covered by tests (excluded)
│   ├── tests/
│   │   ├── unit/             # 222 test files — primary expansion area
│   │   ├── integration/      # 15 test files
│   │   ├── e2e/              # 5 backend e2e test files
│   │   ├── property/         # 7 property-based test files
│   │   ├── chaos/            # 5 chaos engineering tests
│   │   ├── concurrency/      # 4 concurrency tests
│   │   ├── fuzz/             # 3 fuzz test files
│   │   ├── performance/      # 1 performance benchmark
│   │   └── architecture/     # 1 architecture compliance test
│   ├── pyproject.toml        # Coverage config (fail_under: 75 → 80)
│   └── coverage.json         # Current coverage report (1.6 MB)
├── frontend/
│   ├── src/
│   │   ├── components/       # 16 component directories with tests
│   │   ├── hooks/            # 60+ hooks with test files
│   │   ├── services/         # API clients and schemas
│   │   ├── lib/              # Utilities
│   │   └── test/             # Test utilities
│   ├── e2e/                  # 24 Playwright spec files
│   ├── vitest.config.ts      # Coverage thresholds (50/44/41/50 → 60/55/52/60)
│   └── playwright.config.ts  # E2E configuration
└── docs/                     # Documentation (no test changes)
```

**Structure Decision**: Existing web application structure (backend + frontend) used as-is. No structural changes needed — all work is within existing `tests/` directories and configuration files.

## Implementation Phases

### Phase 1: Backend Coverage — Tier 1 (P1, highest impact)

Focus on the 5 files with most missing lines and lowest coverage. Each file gets dedicated test additions targeting uncovered branches and error paths.

| # | Target File | Current | Target | Missing Lines | Approach |
|---|-------------|---------|--------|---------------|----------|
| 1 | `services/copilot_polling/pipeline.py` | 65.7% | 82% | 310 → ~180 | Add parametrized tests for pipeline state transitions, error recovery paths, and edge cases in async processing |
| 2 | `services/agents/service.py` | 47.4% | 72% | 281 → ~160 | Add tests for agent CRUD operations, validation failures, edge cases in agent configuration |
| 3 | `api/chat.py` | 59.6% | 78% | 275 → ~160 | Add API route tests using AsyncClient, test error responses, SSE streaming edge cases |
| 4 | `services/agent_creator.py` | 39.4% | 65% | 240 → ~140 | Add tests for creation workflows, template processing, validation rules |
| 5 | `api/projects.py` | 37.7% | 65% | 155 → ~90 | Add route tests for project CRUD, authorization checks, pagination |

**Estimated backend coverage gain**: +3-4 percentage points (79% → 83%)

### Phase 2: Backend Coverage — Tier 2 (P1-P2)

| # | Target File | Current | Target | Missing Lines | Approach |
|---|-------------|---------|--------|---------------|----------|
| 6 | `services/chores/service.py` | 51.3% | 72% | 154 → ~90 | Test chore scheduling, execution, error handling |
| 7 | `services/copilot_polling/recovery.py` | 64.3% | 80% | 138 → ~80 | Test recovery strategies, retry logic, failure modes |
| 8 | `workflow_orchestrator/orchestrator.py` | 79.8% | 88% | 136 → ~95 | Test complex orchestration flows, state transitions |
| 9 | `services/app_service.py` | 61.6% | 78% | 130 → ~85 | Test app lifecycle, installation, update logic |
| 10 | `services/signal_bridge.py` | 60.9% | 78% | 127 → ~75 | Test bridge communication, webhook dispatch |

**Estimated cumulative backend coverage**: ~85%

### Phase 3: Backend Coverage — Tier 3 + Branch Coverage (P2)

| # | Target File | Current | Target | Missing Lines |
|---|-------------|---------|--------|---------------|
| 11 | `api/pipelines.py` | 62.2% | 78% | 101 |
| 12 | `github_projects/board.py` | 63.0% | 78% | 91 |
| 13 | `main.py` | 68.2% | 80% | 89 |
| 14 | `api/board.py` | 64.5% | 78% | 85 |
| 15 | `copilot_polling/agent_output.py` | 73.0% | 83% | 80 |

Focus: Branch coverage improvement across all tiers. Target overall branch coverage from 70% to ≥78%.

### Phase 4: Frontend Coverage Improvement (P1-P2)

1. **Hooks coverage** — Identify hooks with lowest coverage; add renderHook tests for state transitions and error cases
2. **Service layer** — Add tests for API client functions, schema validation edge cases
3. **Component tests** — Target complex components (chat, pipeline, board) with user-centric Testing Library tests
4. **Raise thresholds** — Update `vitest.config.ts` thresholds from 50/44/41/50 to 60/55/52/60

### Phase 5: E2E Test Audit and Improvement (P2)

1. **Audit existing 24 Playwright specs** — Identify tests that are broken, flaky, or test removed features
2. **Remove stale e2e tests** — Delete specs for deprecated flows
3. **Strengthen core flows** — Ensure auth, chat, pipeline, board, and agent-creation e2e tests are robust
4. **Add accessibility assertions** — Use `@axe-core/playwright` in key e2e flows

### Phase 6: Test Quality and Cleanup (P2-P3)

1. **Identify and remove stale backend tests** — Find tests with no assertions, over-mocking, or testing dead code
2. **Identify and remove stale frontend tests** — Same analysis for vitest test files
3. **Raise backend fail_under** — Update `pyproject.toml` from `fail_under = 75` to `fail_under = 80`
4. **Bug fixes** — Resolve any bugs discovered during test writing (track in commits)

### Phase 7: Validation and CI Verification (P1)

1. **Run full backend test suite** — Verify ≥85% line coverage, ≥78% branch coverage
2. **Run full frontend test suite** — Verify new thresholds pass (60/55/52/60)
3. **Run e2e tests** — Verify all Playwright specs pass
4. **Run CI locally** — Simulate full CI pipeline (lint, type check, tests, coverage)

## Dependencies and Ordering

```
Phase 1 (Tier 1 backend) ─┐
Phase 2 (Tier 2 backend) ─┤
Phase 3 (Tier 3 backend) ─┼─→ Phase 6 (Cleanup) ─→ Phase 7 (Validation)
Phase 4 (Frontend) ───────┤
Phase 5 (E2E audit) ──────┘
```

- Phases 1-5 can be executed in parallel (independent file targets)
- Phase 6 depends on Phases 1-5 (need coverage data to identify truly stale tests)
- Phase 7 depends on all prior phases (final validation)

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| New tests increase CI time beyond 10min | Medium | Monitor `--durations=20` output; parallelize test execution if needed |
| Stale test removal reduces coverage | Low | Run coverage diff before/after each removal |
| Bug fixes introduce regressions | Medium | Each fix accompanied by a test; run full suite before merge |
| Frontend threshold increase breaks CI | Low | Validate locally before committing threshold changes |
| Flaky tests in new additions | Medium | Use `pytest-repeat` and flaky-detection workflow to validate stability |

## Complexity Tracking

> No constitution violations identified. All work follows existing patterns and tools.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| No new frameworks | Use existing pytest/vitest/Playwright | Constitution Principle V: Simplicity — existing tools are sufficient |
| Incremental thresholds | +10pp per metric (not +30pp) | Achievable without heroic effort; creates ratchet for future improvement |
| Parallel phases | Independent file targets | No shared state between test files; safe to parallelize |
