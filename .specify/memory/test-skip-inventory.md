# Test Skip Marker Inventory

**Date**: 2026-04-08
**Feature**: Uplift Solune Testing (#1149)
**Branch**: `020-uplift-solune-testing`

## Summary

| Area | Total Markers | Unconditional | Conditional (Infrastructure Guard) |
|------|--------------|---------------|-----------------------------------|
| Backend | 10 | 0 | 10 |
| Frontend Unit | 0 | 0 | 0 |
| Frontend E2E | 6 | 0 | 6 |
| **Total** | **16** | **0** | **16** |

## Backend Skip Markers

| # | File | Line | Marker | Reason | Classification |
|---|------|------|--------|--------|---------------|
| 1 | `tests/unit/test_run_mutmut_shard.py` | 138 | `@pytest.mark.skipif` | CI workflow YAML not found (shallow clone) | ✅ Conditional — file-existence guard |
| 2 | `tests/architecture/test_import_rules.py` | 54 | `pytest.skip()` | `services/` directory not found | ✅ Conditional — directory-existence guard |
| 3 | `tests/architecture/test_import_rules.py` | 93 | `pytest.skip()` | `api/` directory not found | ✅ Conditional — directory-existence guard |
| 4 | `tests/architecture/test_import_rules.py` | 116 | `pytest.skip()` | `models/` directory not found | ✅ Conditional — directory-existence guard |
| 5 | `tests/integration/test_custom_agent_assignment.py` | 45 | `pytest.skip()` | `GITHUB_TOKEN` env var not set | ✅ Conditional — env-var guard |
| 6 | `tests/performance/test_board_load_time.py` | 40 | `pytest.skip()` | `PERF_GITHUB_TOKEN` not set | ✅ Conditional — env-var guard |
| 7 | `tests/performance/test_board_load_time.py` | 42 | `pytest.skip()` | `PERF_PROJECT_ID` not set | ✅ Conditional — env-var guard |
| 8 | `tests/performance/test_board_load_time.py` | 49 | `pytest.skip()` | Backend unhealthy (HTTP status) | ✅ Conditional — service-health guard |
| 9 | `tests/performance/test_board_load_time.py` | 51 | `pytest.skip()` | Backend not reachable (ConnectError) | ✅ Conditional — service-health guard |
| 10 | `tests/performance/test_board_load_time.py` | 68 | `pytest.skip()` | Could not authenticate via dev-login | ✅ Conditional — auth-state guard |

## Frontend E2E Skip Markers

| # | File | Line | Marker | Reason | Classification |
|---|------|------|--------|--------|---------------|
| 1 | `e2e/integration.spec.ts` | 62 | `test.skip()` | Backend not running (catch block) | ✅ Conditional — service-health guard |
| 2 | `e2e/integration.spec.ts` | 73 | `test.skip()` | Backend not running (catch block) | ✅ Conditional — service-health guard |
| 3 | `e2e/project-load-performance.spec.ts` | 47 | `test.skip(true, ...)` | Auth state not found | ✅ Conditional — auth-state guard |
| 4 | `e2e/project-load-performance.spec.ts` | 50 | `test.skip(true, ...)` | `E2E_PROJECT_ID` not set | ✅ Conditional — env-var guard |
| 5 | `e2e/project-load-performance.spec.ts` | 65 | `test.skip(true, ...)` | Frontend not reachable | ✅ Conditional — service-health guard |
| 6 | `e2e/project-load-performance.spec.ts` | 114 | `test.skip(true, ...)` | Frontend not reachable | ✅ Conditional — service-health guard |

## Frontend Unit Tests — useAuth.test.tsx

`useAuth.test.tsx` has **zero** skip markers. All 18 tests run fully.
The `result.current.skip()` calls found in the file are hook method invocations
(onboarding skip action), not test-framework skip markers.

## Verdict

All 16 skip markers are **conditional infrastructure guards** that skip only when
external prerequisites (env vars, running services, auth state, file presence) are
missing. **Zero unconditional** `@pytest.mark.skip`, `@pytest.mark.xfail`, `.todo`,
`xit`, or `xdescribe` markers exist in the codebase.

**Action**: Keep all 16 markers as-is. They correctly protect test execution from
infrastructure absence and are not masking bugs.
