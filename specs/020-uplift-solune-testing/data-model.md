# Data Model: Uplift Solune Testing — Remove Skips, Fix Bugs, Apply Modern Best Practices

**Feature**: 020-uplift-solune-testing | **Date**: 2026-04-08

> This feature modifies test infrastructure and adds tests, not runtime data models. This document defines the **test skip inventory**, **infrastructure configuration model**, and **coverage target inventory**.

## Backend Test Skip Inventory

### Entity: Conditional Skip Markers (Infrastructure Guards)

All 8 backend skips are conditional runtime guards. No unconditional `@pytest.mark.skip` or `@pytest.mark.xfail` exist.

| # | File | Line | Marker | Condition | Category |
|---|------|------|--------|-----------|----------|
| 1 | `tests/unit/test_run_mutmut_shard.py` | 138 | `@pytest.mark.skipif` | CI workflow YAML not found | Architecture |
| 2 | `tests/architecture/test_import_rules.py` | 54 | `pytest.skip()` | `services/` directory not found | Architecture |
| 3 | `tests/architecture/test_import_rules.py` | 93 | `pytest.skip()` | `api/` directory not found | Architecture |
| 4 | `tests/architecture/test_import_rules.py` | 116 | `pytest.skip()` | `models/` directory not found | Architecture |
| 5 | `tests/performance/test_board_load_time.py` | 40 | `pytest.skip()` | `PERF_GITHUB_TOKEN` not set | Performance |
| 6 | `tests/performance/test_board_load_time.py` | 42 | `pytest.skip()` | `PERF_PROJECT_ID` not set | Performance |
| 7 | `tests/performance/test_board_load_time.py` | 49-71 | `pytest.skip()` | Backend unhealthy / not reachable | Performance |
| 8 | `tests/integration/test_custom_agent_assignment.py` | 45 | `pytest.skip()` | `GITHUB_TOKEN` not set | Integration |

**Verdict**: All 8 are appropriate infrastructure guards. Zero removals needed.

## Frontend Test Skip Inventory

### Entity: Conditional Skip Markers (E2E Infrastructure Guards)

All 6 frontend skips are in E2E test files. Zero unit test skips exist.

| # | File | Line | Marker | Condition | Category |
|---|------|------|--------|-----------|----------|
| 1 | `e2e/integration.spec.ts` | 62 | `test.skip()` | Backend API unreachable (catch) | E2E Integration |
| 2 | `e2e/integration.spec.ts` | 73 | `test.skip()` | Backend API unreachable (catch) | E2E Integration |
| 3 | `e2e/project-load-performance.spec.ts` | 47 | `test.skip()` | Auth state file not found | E2E Performance |
| 4 | `e2e/project-load-performance.spec.ts` | 50 | `test.skip()` | `E2E_PROJECT_ID` not set | E2E Performance |
| 5 | `e2e/project-load-performance.spec.ts` | 65 | `test.skip()` | Frontend not reachable | E2E Performance |
| 6 | `e2e/project-load-performance.spec.ts` | 114 | `test.skip()` | Frontend not reachable | E2E Performance |

**Verdict**: All 6 are appropriate infrastructure guards. Zero removals needed.

## Backend Infrastructure Configuration

### Entity: pytest Configuration (`pyproject.toml`)

| Setting | Current Value | Required Value | Status |
|---------|--------------|----------------|--------|
| `asyncio_mode` | `"auto"` | `"auto"` | ✅ Correct |
| `asyncio_default_fixture_loop_scope` | `"function"` | `"function"` | ✅ Correct |
| `testpaths` | `["tests"]` | `["tests"]` | ✅ Correct |
| `markers` | integration, performance | integration, performance | ✅ Correct |
| `pytest-randomly` | `>=3.16.0` in dev deps | `>=3.16.0` | ✅ Already installed |

### Entity: Coverage Configuration

| Setting | Current Value | Required Value | Status |
|---------|--------------|----------------|--------|
| Backend CI `--cov-fail-under` | Not set | `70` | ⚠️ Needs adding |
| Backend `[tool.coverage.report]` | Exists | Add `fail_under = 70` | ⚠️ Option B |
| Frontend `thresholds.statements` | `50` | `50` (min) | ✅ Correct |
| Frontend `thresholds.branches` | `44` | `44` | ✅ Correct |
| Frontend `thresholds.functions` | `41` | `41` | ✅ Correct |
| Frontend `thresholds.lines` | `50` | `50` | ✅ Correct |

## Frontend Infrastructure Configuration

### Entity: Vitest Configuration (`vitest.config.ts`)

| Setting | Current Value | Required Value | Status |
|---------|--------------|----------------|--------|
| `globals` | `true` | `true` | ✅ Correct |
| `environment` | `'happy-dom'` | `'happy-dom'` | ✅ Correct |
| `setupFiles` | `['./src/test/setup.ts']` | `['./src/test/setup.ts']` | ✅ Correct |
| `coverage.provider` | `'v8'` | `'v8'` | ✅ Correct |
| `include` | `['src/**/*.{test,spec}.{ts,tsx}']` | Pattern covering all tests | ✅ Correct |

### Entity: Test Setup (`src/test/setup.ts`)

| Feature | Current Status | Required | Notes |
|---------|---------------|----------|-------|
| `crypto.randomUUID` stub | ✅ Present | ✅ Present | Deterministic UUIDs |
| WebSocket mock | ✅ Present | ✅ Present | Mock WebSocket implementation |
| `window.location` mock | ✅ Present | ✅ Present | Controlled navigation |
| `window.history` mock | ✅ Present | ✅ Present | Controlled history |
| jest-dom matchers | ✅ Present | ✅ Present | Via setup.ts imports |
| jest-axe matchers | ❓ Per-test | Per-test import | Not a global setup concern |

## Net-New Coverage Targets

### Entity: Backend Coverage Targets

| Module | Function/Path | Current Coverage | Test Strategy |
|--------|--------------|-----------------|---------------|
| `src/utils.py:209` | `resolve_repository()` | Partial | Test 4-step fallback: cache hit, GraphQL, REST, workflow config, default settings. Mock `githubkit` and `httpx` calls. |
| `src/api/webhooks.py` | HMAC signature validation | Partial | Test valid signature, invalid signature, missing header, replay protection via `_processed_delivery_ids`. |
| `src/services/tools/presets.py` | Preset catalog enumeration | Unknown | Test `_PRESETS` tuple iteration, validate McpPresetResponse fields, test filtering. |
| `src/services/encryption.py` | Fernet encryption roundtrip | Unknown | Test encrypt → decrypt roundtrip, invalid key handling, token expiration. |
| `src/services/pipeline_state_store.py` | Restart survivability | Unknown | Test SQLite persistence, state recovery after simulated restart, lock re-initialization. |

### Entity: Frontend Coverage Targets

| Module | Function/Path | Current Coverage | Test Strategy |
|--------|--------------|-----------------|---------------|
| `src/services/api.ts` | Authenticated request + retry | Existing `api.test.ts` | Verify retry on 401, retry on network error, correct auth header attachment. |
| Page components | axe accessibility | Zero | Add `expect(await axe(container)).toHaveNoViolations()` to at least one render test per page component. |
| Hooks with zero coverage | TBD during implementation | Zero | Identify hooks without test files, add basic happy path + error tests. |

## Test Infrastructure Dependencies

### Entity: Dependency Graph

```text
Step 1 (Audit)
├── Produces: test-skip-inventory.md (this document)
│
Step 2 (Backend Infra) ←── Step 1
├── Depends on: Audit results
├── Changes: pyproject.toml (coverage threshold), CI workflow
│
Step 3 (Frontend Infra) ←── Step 1
├── Depends on: Audit results
├── Changes: vitest.config.ts (if needed), setup.ts (if needed)
│
Step 4 (Backend Skips) ←── Step 2
├── Depends on: Infrastructure fixes
├── Changes: Test files (remove unconditional skips — none found)
│
Step 5 (Frontend Skips) ←── Step 3
├── Depends on: Infrastructure fixes
├── Changes: Test files (remove unconditional skips — none found)
│
Step 6 (New Coverage) ←── Steps 4, 5
├── Depends on: All skips resolved, infrastructure stable
├── Changes: New test files for coverage gaps
│
Step 7 (Validation) ←── Step 6
├── Depends on: All changes complete
├── Changes: CHANGELOG.md, CI verification
```
