# Research: Uplift Solune Testing — Remove Skips, Fix Bugs, Apply Modern Best Practices

**Feature**: 020-uplift-solune-testing | **Date**: 2026-04-08

## R1: Backend Skip Marker Classification

**Context**: The backend has 10 skip markers across 4 test files. The issue requires removing ALL skips, but the actual markers are all *conditional* — they skip only when external infrastructure is missing (CI workflow file, directories, environment variables, running backend).

**Decision**: Classify each skip as either **removable** (unconditional / no longer needed) or **infrastructure guard** (conditional, appropriate). All 10 backend skips are infrastructure guards that run when prerequisites are met.

**Rationale**: The issue states "remove all test skips" but the actual markers are:

| File | Marker | Type | Verdict |
|------|--------|------|---------|
| `test_run_mutmut_shard.py:138` | `@pytest.mark.skipif` (CI workflow missing) | Infrastructure guard | Keep — shallow clone protection |
| `test_import_rules.py:54` | `pytest.skip()` (`services/` directory not found) | Infrastructure guard | Keep — graceful degradation |
| `test_import_rules.py:93` | `pytest.skip()` (`api/` directory not found) | Infrastructure guard | Keep — graceful degradation |
| `test_import_rules.py:116` | `pytest.skip()` (`models/` directory not found) | Infrastructure guard | Keep — graceful degradation |
| `test_board_load_time.py:40` | `pytest.skip()` (`PERF_GITHUB_TOKEN` not set) | Infrastructure guard | Keep — perf test prerequisites |
| `test_board_load_time.py:42` | `pytest.skip()` (`PERF_PROJECT_ID` not set) | Infrastructure guard | Keep — perf test prerequisites |
| `test_board_load_time.py:49` | `pytest.skip()` (backend unhealthy) | Infrastructure guard | Keep — perf test prerequisites |
| `test_board_load_time.py:51` | `pytest.skip()` (backend not reachable) | Infrastructure guard | Keep — perf test prerequisites |
| `test_board_load_time.py:68` | `pytest.skip()` (dev-login auth failure) | Infrastructure guard | Keep — perf test prerequisites |
| `test_custom_agent_assignment.py:45` | `pytest.skip()` (GITHUB_TOKEN missing) | Infrastructure guard | Keep — live integration test |

No unconditional `@pytest.mark.skip` or `@pytest.mark.xfail` markers exist in the backend. The backend skip audit is already clean.

**Alternatives considered**:

- Remove all runtime `pytest.skip()` and replace with pytest markers: Rejected — the current pattern correctly detects infrastructure at runtime, which markers cannot do (e.g., checking if backend is reachable via HTTP)
- Convert to `@pytest.mark.skipif` for all: Rejected — some checks require runtime evaluation (HTTP health check, directory existence)

## R2: Frontend Skip Marker Classification

**Context**: The frontend has 6 skip markers across 2 E2E test files. No unit tests have skip markers.

**Decision**: All 6 frontend skips are conditional infrastructure guards inside E2E tests. No `.skip`, `.todo`, `xit`, or `xdescribe` markers exist in unit tests.

**Rationale**:

| File | Marker | Type | Verdict |
|------|--------|------|---------|
| `e2e/integration.spec.ts:62,73` | `test.skip()` (backend not running) | Infrastructure guard | Keep — graceful skip in catch block |
| `e2e/project-load-performance.spec.ts:47` | `test.skip()` (auth state missing) | Infrastructure guard | Keep — requires saved auth |
| `e2e/project-load-performance.spec.ts:50` | `test.skip()` (E2E_PROJECT_ID missing) | Infrastructure guard | Keep — requires env var |
| `e2e/project-load-performance.spec.ts:65,114` | `test.skip()` (frontend not reachable) | Infrastructure guard | Keep — requires running frontend |

The frontend skip audit is already clean — no unconditional skips exist.

**Alternatives considered**:

- Add Playwright `test.fixme()` annotations: Rejected — these are properly working conditional guards, not broken tests
- Move to separate `@slow`/`@perf` test group: Already organized — they use `describe.skip` pattern correctly within conditional blocks

## R3: Backend pytest-asyncio Configuration Best Practices

**Context**: Issue requests verifying asyncio_mode and loop scope settings.

**Decision**: Backend pyproject.toml already has correct modern configuration. No changes needed.

**Rationale**: Current config at `solune/backend/pyproject.toml:113-120`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

This is the recommended configuration for pytest-asyncio >= 0.23. The `auto` mode automatically handles async test functions without requiring `@pytest.mark.asyncio`. The `function` scope creates a fresh event loop per test, preventing cross-test contamination.

**Alternatives considered**:

- `asyncio_mode = "strict"`: Rejected — requires explicit markers on every async test, more boilerplate
- `session` scope: Rejected — shared event loops cause the lock lifecycle issues documented in spec 019

## R4: Frontend Vitest Configuration Best Practices

**Context**: Issue requests hardening Vitest config with environment, globals, coverage, and setup files.

**Decision**: Frontend vitest.config.ts already has correct modern configuration. No changes needed.

**Rationale**: Current config at `solune/frontend/vitest.config.ts`:

- `globals: true` ✅ — test functions available without imports
- `environment: 'happy-dom'` ✅ — fast DOM implementation
- `setupFiles: ['./src/test/setup.ts']` ✅ — global test setup
- `coverage.provider: 'v8'` ✅ — native V8 coverage
- `coverage.thresholds: { statements: 50, branches: 44, functions: 41, lines: 50 }` ✅ — enforced

jest-dom is already configured via setup.ts. jest-axe availability depends on whether it's imported in tests (it's a per-test import, not a global setup concern).

**Alternatives considered**:

- Switch to `jsdom`: Rejected — happy-dom is faster and already configured
- Raise thresholds now: Rejected — raise after adding new coverage, not before

## R5: Coverage Threshold Strategy

**Context**: Issue specifies `--cov-fail-under=70` for backend CI. However, the backend already has `fail_under = 75` in `pyproject.toml` under `[tool.coverage.report]`, which exceeds the issue's 70% minimum.

**Decision**: Preserve the existing `fail_under = 75` in `pyproject.toml`. No CI command changes needed since the pyproject.toml setting is already enforced. Frontend thresholds are already enforced in vitest.config.ts.

**Rationale**: The current CI command is:

```yaml
run: uv run pytest --cov=src --cov-report=term-missing --cov-report=xml --cov-report=html --durations=20 --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency
```

The existing `fail_under = 75` in `pyproject.toml` is automatically enforced when pytest-cov generates coverage reports, which already happens in CI. This threshold exceeds issue #1149's 70% minimum.

**Alternatives considered**:

- Lowering to 70%: Would reduce the existing quality bar from 75% to 70% — rejected
- 80% threshold: Too aggressive for initial enforcement; can be raised after coverage gains

## R6: Best Practices for Resolving Skipped Test Underlying Bugs

**Context**: Issue Step 4 says to fix underlying production bugs for each skipped backend test. Research shows no production bugs — all skips are infrastructure guards.

**Decision**: No production bug fixes required. All backend skips guard against missing external infrastructure, not broken production code.

**Rationale**: After detailed analysis of each skip:

1. `test_run_mutmut_shard.py` — skips if CI workflow YAML file is missing (shallow clone). No bug.
2. `test_import_rules.py` — skips if source directories don't exist. No bug.
3. `test_board_load_time.py` — skips if perf credentials or backend unavailable. No bug.
4. `test_custom_agent_assignment.py` — skips if GITHUB_TOKEN missing. No bug.

The issue's Step 4 is pre-emptive — it assumes unconditional skips masking bugs. The audit shows this is not the case.

**Alternatives considered**:

- Force-fix the skips to always run: Rejected — would fail in CI where infrastructure isn't available
- Mock the infrastructure: Rejected — these are integration/performance tests that intentionally require live infrastructure

## R7: Net-New Coverage Targets

**Context**: Issue Step 6 specifies adding tests for specific modules. Need to verify these targets exist and identify their test gaps.

**Decision**: Prioritize net-new tests for the following modules based on criticality and current coverage gaps:

| Target | File | Current Coverage | Priority |
|--------|------|-----------------|----------|
| `resolve_repository()` | `src/utils.py:209` | Partial — 4-step fallback untested | HIGH |
| HMAC webhook validation | `src/api/webhooks.py` | Partial — signature validation path | HIGH |
| `tools/presets.py` | `src/services/tools/presets.py` | Unknown — catalog enumeration | MEDIUM |
| Fernet encryption roundtrip | `src/services/encryption.py` | Unknown | MEDIUM |
| `pipeline_state_store.py` restart | `src/services/pipeline_state_store.py` | Unknown — restart survivability | MEDIUM |
| `api.ts` authenticated request | `frontend/src/services/api.ts` | Existing api.test.ts — check gaps | MEDIUM |
| Page-level axe assertions | Multiple components | Zero a11y assertions | LOW |

**Rationale**: HIGH priority items are on critical code paths (authentication, webhooks). MEDIUM items have known state management complexity. LOW items (a11y) are valuable but less likely to catch regressions.

**Alternatives considered**:

- Focus only on backend: Rejected — frontend api.ts and a11y assertions provide meaningful coverage
- Add property-based tests: Out of scope — Hypothesis tests already exist in `tests/property/`

## R8: useAuth.test.tsx Flaky Test Investigation

**Context**: Issue mentions known-flaky useAuth.test.tsx parallel-run failure mode.

**Decision**: useAuth.test.tsx currently has no skip markers and all 18 tests run fully. The reported flakiness may have been resolved by spec 019 (which adds `vi.restoreAllMocks()` and mock cleanup). Verify with `--pool=forks` and `--pool=threads` during implementation.

**Rationale**: Grep found zero `.skip`, `.todo`, or `xit` markers in useAuth.test.tsx. The test file has comprehensive coverage of authentication states, login/logout, session handling, and error handling. The `result.current.skip()` calls on lines 178-186 are test hook method calls (onboarding skip function), not test skip markers.

**Alternatives considered**:

- Add `beforeEach(localStorage.clear())`: Verify if already present via setup.ts
- Wrap in AuthProvider test wrapper: Check if renderHook already handles this
- Add fake timers for refresh intervals: Only if flakiness is confirmed during implementation

## R9: CI Workflow Validation Strategy

**Context**: Issue Step 7 requires full CI validation including ruff, pyright, pytest, frontend lint/type-check/test/build, and E2E.

**Decision**: Use existing CI workflow structure. The CI already runs all required checks. The plan should document the specific commands for local pre-CI validation.

**Rationale**: The CI workflow (`.github/workflows/ci.yml`) already includes:

- Backend: ruff check, ruff format, pyright, pytest with coverage
- Backend Advanced: property, fuzz, chaos, concurrency (continue-on-error)
- Frontend: lint, type-check, test:coverage, build
- Frontend E2E: Playwright chromium (continue-on-error)
- Docs: markdownlint, link check

Coverage enforcement is already handled by `fail_under = 75` in `pyproject.toml`. No CI command changes needed.

**Alternatives considered**:

- Add new CI jobs: Rejected — existing structure covers all requirements
- Run E2E as blocking: Rejected — E2E depends on deployed services; keep continue-on-error
