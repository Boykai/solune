# Data Model: 100% Test Coverage with Bug Fixes

**Feature**: `001-full-test-coverage` | **Date**: 2026-03-30

## Overview

This feature does not introduce new persistent data models. It modifies test infrastructure, configuration, and a small number of bug fixes in existing code. The "data model" for this feature is the **coverage data model** — the structure of coverage metrics, thresholds, and verification contracts that govern the test coverage campaign.

## Coverage Metrics Model

### Backend Coverage State

| Field | Type | Current Value | Target Value | Source |
|-------|------|--------------|--------------|--------|
| `line_coverage` | float (%) | 78 | 100 | `pytest --cov` output |
| `branch_coverage` | float (%) | 69 | 100 | `pytest --cov-branch` output |
| `fail_under` | int (%) | 75 | 100 | `pyproject.toml [tool.coverage.report]` |
| `test_file_count` | int | 202 | ~250+ (all modules covered) | `tests/` directory |
| `mutmut_kill_rate` | float (%) | — | ≥85 | `mutmut results` output |
| `mutmut_scope` | list[str] | `["src/services/"]` | `["src/"]` | `pyproject.toml [tool.mutmut]` |

### Frontend Coverage State

| Field | Type | Current Value | Target Value | Source |
|-------|------|--------------|--------------|--------|
| `statement_coverage` | float (%) | 50 | 100 | `vitest --coverage` output |
| `branch_coverage` | float (%) | 44 | 100 | `vitest --coverage` output |
| `function_coverage` | float (%) | 41 | 100 | `vitest --coverage` output |
| `line_coverage` | float (%) | 50 | 100 | `vitest --coverage` output |
| `test_file_count` | int | 165 | ~265 (all source files covered) | `src/` directory |
| `stryker_kill_rate` | float (%) | — | ≥80 | `stryker run` output |
| `stryker_scope` | list[str] | `["src/hooks/**/*.ts", "src/lib/**/*.ts"]` | + `src/components/**/*.tsx`, `src/pages/**/*.tsx` | `stryker.config.mjs` |

## Bug Fix Entities

### BugFix: DevContainer CI Tag

| Attribute | Value |
|-----------|-------|
| File | `.devcontainer/devcontainer.json` (or CI workflow referencing it) |
| Current | `devcontainers/ci@v0.3` (invalid/non-existent tag) |
| Fix | Pin to valid release tag |
| Validation | CI pipeline completes without devcontainer configuration errors |

### BugFix: Silent Exception in `verify_project_access()`

| Attribute | Value |
|-----------|-------|
| File | `solune/backend/src/api/dependencies.py` |
| Function | `verify_project_access()` |
| Current | Bare `except` or overly broad handler that silently swallows exceptions |
| Fix | Log at WARNING level + re-raise as `HTTPException(status_code=403)` |
| Validation | Test exercises the exception path and asserts error is propagated |

### BugFix: Rate Limit Middleware Timeout

| Attribute | Value |
|-----------|-------|
| File | `solune/backend/src/middleware/rate_limit.py` |
| Class | `RateLimitKeyMiddleware` |
| Current | Session resolution has no timeout bound |
| Fix | Wrap with `asyncio.wait_for(timeout=settings.rate_limit_timeout)`, fallback to IP-based key |
| Validation | Test simulates slow session resolution and asserts timeout behavior |

### BugFix: McpValidationError Field-Level Errors

| Attribute | Value |
|-----------|-------|
| File | `solune/backend/src/exceptions.py` |
| Class | `McpValidationError` |
| Current | No field-level error details in exception payload |
| Fix | Add `field_errors: dict[str, list[str]]` parameter; include in serialized response |
| Validation | Test creates McpValidationError with field errors and asserts they appear in response |

## Phase Dependency Graph

```text
Phase 1 (Bug Fixes)
    ├──→ Phase 2 (Backend Untested Services)
    │        └──→ Phase 3 (Backend Branch Blitz)
    │                                           ╲
    └──→ Phase 4 (Frontend Components)           ╲
             └──→ Phase 5 (Frontend Branches)     ╲
                                                   ↘
                                              Phase 6 (Hardening)
```

**Parallel execution**: Phases 3 and 4 are independent and can run simultaneously.

## Test Infrastructure Entities (No Changes)

The following existing test infrastructure entities are used as-is — no modifications required:

### Backend Test Infrastructure

| Entity | Location | Purpose |
|--------|----------|---------|
| `conftest.py` | `tests/conftest.py` | Shared fixtures (mock_session, mock_db, mock_settings, client) |
| `factories.py` | `tests/helpers/factories.py` | 14+ factory functions for test data |
| `assertions.py` | `tests/helpers/assertions.py` | `assert_api_success()`, `assert_api_error()` |

### Frontend Test Infrastructure

| Entity | Location | Purpose |
|--------|----------|---------|
| `setup.ts` | `src/test/setup.ts` | Vitest setup: polyfills, WebSocket mock |
| `test-utils.tsx` | `src/test/test-utils.tsx` | `renderWithProviders()` with QueryClient, Confirmation, Tooltip |
| `a11y-helpers` | `jest-axe` integration | `expectNoA11yViolations()` via jest-axe |

## Configuration Changes

### `pyproject.toml` (Phase 6)

```toml
# Before
[tool.coverage.report]
fail_under = 75

[tool.mutmut]
paths_to_mutate = ["src/services/"]

# After
[tool.coverage.report]
fail_under = 100

[tool.mutmut]
paths_to_mutate = ["src/"]
```

### `vitest.config.ts` (Phase 6)

```typescript
// Before
thresholds: {
  statements: 50,
  branches: 44,
  functions: 41,
  lines: 50,
}

// After
thresholds: {
  statements: 100,
  branches: 100,
  functions: 100,
  lines: 100,
}
```

### `stryker.config.mjs` (Phase 6)

```javascript
// Before
mutate: [
  'src/hooks/**/*.ts',
  'src/lib/**/*.ts',
  '!src/**/*.test.ts',
]

// After
mutate: [
  'src/hooks/**/*.ts',
  'src/lib/**/*.ts',
  'src/components/**/*.tsx',
  'src/pages/**/*.tsx',
  '!src/**/*.test.ts',
  '!src/**/*.property.test.ts',
]
```
