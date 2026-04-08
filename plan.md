# Implementation Plan: Uplift Solune Testing — Remove Skips, Fix Bugs, Apply Modern Best Practices

**Branch**: `020-uplift-solune-testing` | **Date**: 2026-04-08 | **Spec**: [#1149](https://github.com/Boykai/solune/issues/1149)
**Input**: Parent issue #1149 — Uplift Solune Testing: Remove Skips, Fix Bugs, Apply Modern Best Practices

## Summary

The Solune codebase has skipped tests in both backend (pytest) and frontend (Vitest/Playwright) suites. This plan systematically audits all skip markers, fixes test-runner infrastructure, resolves each skip by addressing the underlying cause, adds meaningful net-new coverage for critical untested paths, and validates that every suite and the CI pipeline is green.

**Key finding from research (Phase 0)**: All 16 skip markers (10 backend + 6 frontend) are *conditional infrastructure guards* that skip only when external prerequisites are missing (env vars, running services, auth state). Zero unconditional `@pytest.mark.skip`, `@pytest.mark.xfail`, `.todo`, `xit`, or `xdescribe` markers exist. The pytest and Vitest configurations already follow modern best practices. The primary actionable work is: (1) verify CI coverage enforcement (already at 75%), (2) add net-new tests for untested critical paths, and (3) validate the full suite.

## Technical Context

**Language/Version**: Python >=3.12 (backend), TypeScript 6.0 (frontend)
**Primary Dependencies**: FastAPI, pytest, pytest-asyncio, pytest-randomly, pytest-cov, Vitest 4.1.3, Playwright, React 19.2.0
**Storage**: SQLite via aiosqlite (existing — test isolation handled by spec 019)
**Testing**: pytest (backend), Vitest + Testing Library (frontend), Playwright (E2E)
**Target Platform**: Linux server (backend), Modern browsers (frontend)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: N/A — test infrastructure changes, no runtime impact
**Constraints**: Zero breaking changes to production code; all existing tests must continue passing; coverage thresholds maintained (backend >=75%, frontend >=50%)
**Scale/Scope**: 10 backend conditional skips across 4 files; 6 frontend conditional skips across 2 E2E files; ~12 new test functions for coverage gaps

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Parent issue #1149 provides 7-step implementation plan with detailed acceptance criteria |
| II. Template-Driven Workflow | ✅ PASS | Using canonical plan template; all artifacts in `specs/020-uplift-solune-testing/` |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan phase produces plan.md, research.md, data-model.md, quickstart.md, contracts/; handoff to tasks phase |
| IV. Test Optionality | ✅ PASS | This feature IS about testing — tests are the primary deliverable |
| V. Simplicity and DRY | ✅ PASS | Leverages existing infrastructure where already correct; adds only what's missing (new tests) |

**Gate Result**: ✅ ALL PASS — proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/020-uplift-solune-testing/
├── plan.md              # This file
├── research.md          # Phase 0: skip classification, infrastructure audit, coverage strategy
├── data-model.md        # Phase 1: skip inventory, config model, coverage targets
├── quickstart.md        # Phase 1: step-by-step developer guide
├── contracts/
│   ├── backend-testing.md   # Contract for backend test patterns and coverage
│   └── frontend-testing.md  # Contract for frontend test patterns and E2E skips
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── pyproject.toml                              # Step 2: verify existing fail_under = 75
│   ├── tests/
│   │   ├── conftest.py                             # Reference — expanded by spec 019
│   │   ├── unit/
│   │   │   ├── test_resolve_repository.py          # Step 6: NEW — resolve_repository() tests
│   │   │   ├── test_webhooks.py                    # Step 6: NEW/EXTEND — HMAC validation tests
│   │   │   ├── test_presets.py                     # Step 6: NEW — preset catalog tests
│   │   │   └── test_encryption.py                  # Step 6: NEW/EXTEND — Fernet roundtrip tests
│   │   ├── integration/
│   │   │   └── test_custom_agent_assignment.py     # Step 4: verified — conditional skip OK
│   │   ├── architecture/
│   │   │   └── test_import_rules.py                # Step 4: verified — conditional skip OK
│   │   ├── performance/
│   │   │   └── test_board_load_time.py             # Step 4: verified — conditional skip OK
│   │   └── unit/
│   │       └── test_run_mutmut_shard.py            # Step 4: verified — conditional skipif OK
│   └── src/
│       ├── utils.py                                # Step 6: resolve_repository() — test target
│       ├── api/webhooks.py                         # Step 6: HMAC validation — test target
│       ├── services/tools/presets.py               # Step 6: preset catalog — test target
│       ├── services/encryption.py                  # Step 6: Fernet encryption — test target
│       └── services/pipeline_state_store.py        # Step 6: restart survivability — test target
│
├── frontend/
│   ├── vitest.config.ts                            # Step 3: verified — already correct
│   ├── src/
│   │   ├── test/setup.ts                           # Step 3: verified — UUID stub, mocks present
│   │   ├── services/api.ts                         # Step 6: test target
│   │   ├── services/api.test.ts                    # Step 6: EXTEND — auth, retry tests
│   │   └── pages/                                  # Step 6: axe assertions in page tests
│   └── e2e/
│       ├── integration.spec.ts                     # Step 5: verified — conditional skip OK
│       └── project-load-performance.spec.ts        # Step 5: verified — conditional skip OK
│
└── CHANGELOG.md                                    # Step 7: add Fixed entries
```

**Structure Decision**: Web application (Option 2). Changes span `solune/backend/` (config, new tests) and `solune/frontend/` (possible new tests). No new directories required.

## Execution Phases (from Issue #1149)

### Step 1 — Audit All Skip Markers (DONE in Phase 0 Research)

**Status**: ✅ Complete — documented in `research.md` and `data-model.md`

**Findings**:

| Area | Skip Count | Unconditional | Conditional (Infrastructure) |
|------|-----------|---------------|------------------------------|
| Backend | 10 | 0 | 10 |
| Frontend Unit | 0 | 0 | 0 |
| Frontend E2E | 6 | 0 | 6 |
| **Total** | **16** | **0** | **16** |

useAuth.test.tsx has no skip markers. All 18 tests run fully. The `result.current.skip()` calls are test hook method invocations (onboarding skip), not test skip markers.

### Step 2 — Fix Backend pytest Infrastructure

| Step | Target | Action | Status |
|------|--------|--------|--------|
| 2.1 | `pyproject.toml` asyncio config | Verify `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "function"` | ✅ Already correct |
| 2.2 | `pyproject.toml` coverage | Verify existing `fail_under = 75` (exceeds issue #1149's 70% min) | ✅ Already correct |
| 2.3 | CI workflow | No change needed — `fail_under = 75` already enforced | ✅ Already correct |
| 2.4 | filterwarnings | Verify only intentional deprecation suppressions | ✅ Already correct |
| 2.5 | Loop fixtures in `tests/helpers/` | Verify no deprecated `loop` parameter usage | ✅ Already using modern patterns |

**Acceptance**: `pytest tests/` runs cleanly with zero asyncio warnings.

### Step 3 — Fix Frontend Vitest Infrastructure

| Step | Target | Action | Status |
|------|--------|--------|--------|
| 3.1 | `vitest.config.ts` environment | Verify `environment = 'happy-dom'` | ✅ Already correct |
| 3.2 | `vitest.config.ts` globals | Verify `globals = true` | ✅ Already correct |
| 3.3 | `vitest.config.ts` coverage | Verify `coverage.provider = 'v8'`, `statements >= 50` | ✅ Already correct |
| 3.4 | `vitest.config.ts` setupFiles | Verify points to `src/test/setup.ts` | ✅ Already correct |
| 3.5 | `src/test/setup.ts` | Verify jest-dom configured | ✅ Already correct |
| 3.6 | jest-axe | Per-test import — add to `package.json` if missing | ⚠️ Verify availability |
| 3.7 | `test.exclude` | Verify no accidental exclusions | ✅ Already correct |

**Acceptance**: `npm run test` runs without configuration warnings and jest-axe matchers available.

### Step 4 — Resolve Backend Skipped Tests

| Step | Target | Action | Status |
|------|--------|--------|--------|
| 4.1 | `test_run_mutmut_shard.py:138` | `@pytest.mark.skipif` for missing CI workflow — appropriate | ✅ No change |
| 4.2 | `test_import_rules.py:54,93,116` | `pytest.skip()` for missing directories — appropriate | ✅ No change |
| 4.3 | `test_board_load_time.py:40-71` | `pytest.skip()` for missing credentials/backend — appropriate | ✅ No change |
| 4.4 | `test_custom_agent_assignment.py:45` | `pytest.skip()` for missing GITHUB_TOKEN — appropriate | ✅ No change |

**Result**: Zero unconditional skips to remove. All skips are infrastructure guards.
**Acceptance**: Zero unconditional `@pytest.mark.skip` or `@pytest.mark.xfail` in backend tests.

### Step 5 — Resolve Frontend Skipped Tests and Verify useAuth.test.tsx

| Step | Target | Action | Status |
|------|--------|--------|--------|
| 5.1 | `integration.spec.ts:62,73` | `test.skip()` in catch block — appropriate | ✅ No change |
| 5.2 | `project-load-performance.spec.ts:47,50,65,114` | `test.skip()` for missing prereqs — appropriate | ✅ No change |
| 5.3 | `useAuth.test.tsx` | Verify all 18 tests pass with `--pool=forks` and `--pool=threads` | ⚠️ TODO |
| 5.4 | Frontend cleanup | Verify spec 019 mock restoration patterns are in place | ⚠️ Verify |

**Result**: Zero unconditional skips to remove. Verify useAuth stability.
**Acceptance**: Zero unconditional `.skip`/`xit`/`xdescribe` in frontend. useAuth passes reliably.

### Step 6 — Add Net-New Coverage for Critical Untested Paths

| Step | Target | Module | Test Count | Priority |
|------|--------|--------|-----------|----------|
| 6.1 | `resolve_repository()` | `src/utils.py:209` | 3+ tests | HIGH |
| 6.2 | HMAC webhook validation | `src/api/webhooks.py` | 3+ tests | HIGH |
| 6.3 | Preset catalog | `src/services/tools/presets.py` | 2+ tests | MEDIUM |
| 6.4 | Fernet encryption | `src/services/encryption.py` | 2+ tests | MEDIUM |
| 6.5 | Pipeline restart | `src/services/pipeline_state_store.py` | 2+ tests | MEDIUM |
| 6.6 | api.ts auth + retry | `frontend/src/services/api.ts` | 3+ tests | MEDIUM |
| 6.7 | axe accessibility | Multiple page components | 1+ per page | LOW |

**Test Design Principles**:

- Assert behavior, not implementation
- Happy path + at least one error/edge case
- Use existing test helpers from `tests/helpers/`
- Follow existing naming conventions

**Acceptance**: Coverage up >=10 percentage points from baseline in targeted modules; no new `.skip`.

### Step 7 — Validate Full Suite and Ensure CI Green

| Step | Command | Expected |
|------|---------|----------|
| 7.1 | `ruff check src/ tests/` | Zero lint errors |
| 7.2 | `ruff format --check src/ tests/` | Zero format violations |
| 7.3 | `pyright src/` | Zero type errors |
| 7.4 | `pytest tests/ --cov=src --cov-fail-under=75 -q` | All pass, coverage >=75% |
| 7.5 | `npm run lint` | Zero lint errors |
| 7.6 | `npm run type-check` | Zero type errors |
| 7.7 | `npm run test -- --pool=forks` | All pass |
| 7.8 | `npm run build` | Build succeeds |
| 7.9 | `npx playwright test --project=chromium` | Pass (with continue-on-error) |
| 7.10 | Update CHANGELOG.md | Fixed entries for bugs found |

**Acceptance**: All suites exit 0; CI green; zero unconditional skip markers remain.

## Design Decisions

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| Keep all 16 conditional skips as infrastructure guards | They correctly detect missing prerequisites at runtime; removing them would cause CI failures when infrastructure is absent | Force-remove: tests would fail without credentials. Replace with markers: can't evaluate HTTP health at decoration time. |
| Preserve existing `fail_under = 75` in pyproject.toml | Already exceeds issue #1149's 70% minimum; works both locally and in CI; developers see coverage failures before pushing | Lower to 70: would reduce existing quality bar. CI-only flag: developers wouldn't see failures locally until CI runs |
| Spec 019 handles test isolation; this spec handles skip removal and coverage | Separation of concerns — isolation (fixtures, state leaks) is a different problem from coverage and skip removal | Merge into one spec: too large, different acceptance criteria, different implementation teams |
| Per-test jest-axe import (not global setup) | Not all tests need axe; global setup would add unnecessary overhead | Global setup.ts: would slow down all tests with axe initialization |
| Coverage target 75% backend, 50% frontend | Backend already at 75% (exceeding issue #1149's 70% requirement); frontend at 50% — achievable without major refactoring | 80%+: too aggressive for initial enforcement, would block merges |

## Constitution Re-Check (Post Phase 1 Design)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Issue #1149 with 7 steps, detailed acceptance criteria for each |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates in `specs/020-uplift-solune-testing/` |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan phase complete; handoff to tasks phase for implementation |
| IV. Test Optionality | ✅ PASS | Testing IS the feature — tests are explicitly requested |
| V. Simplicity and DRY | ✅ PASS | Leverages existing correct configuration; adds only coverage threshold and new tests |

**Gate Result**: ✅ ALL PASS — proceed to tasks phase

## Complexity Tracking

> No violations — the plan leverages existing correct infrastructure and adds only what's missing.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | — | — |
