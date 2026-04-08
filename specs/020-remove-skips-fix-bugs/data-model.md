# Data Model: Uplift Solune Testing — Remove Skips, Fix Bugs, Apply Modern Best Practices

**Feature**: 020-remove-skips-fix-bugs | **Date**: 2026-04-08

## Overview

This feature is a test infrastructure uplift — there are no new data models, entities, or database schema changes. This document captures the structural inventory of skip markers, test fixture contracts, and mock patterns that inform the implementation.

## Entity: Skip Marker

Represents a test skip marker found during the audit phase.

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | `str` | Relative path from backend/frontend root |
| `line_number` | `int` | Line number in source file |
| `marker_type` | `enum` | One of: `pytest.mark.skip`, `pytest.mark.skipif`, `pytest.skip`, `test.skip` |
| `reason` | `str` | Human-readable reason for skip |
| `test_name` | `str` | Name of the skipped test function/method |
| `category` | `enum` | One of: `environment`, `path_bug`, `shallow_clone` |
| `resolution` | `enum` | One of: `marker_conversion`, `path_fix`, `fallback_logic`, `project_config` |

### Skip Marker Inventory

**Total**: 16 markers (10 backend, 6 frontend e2e, 0 frontend unit)

#### Backend Markers

```yaml
- file: tests/unit/test_run_mutmut_shard.py
  line: 138-142
  marker: pytest.mark.skipif
  reason: "CI workflow not found (shallow clone or missing file)"
  test: TestCIAlignment.test_workflow_matrix_matches_shards
  category: shallow_clone
  resolution: fallback_logic

- file: tests/integration/test_custom_agent_assignment.py
  line: 45
  marker: pytest.skip
  reason: "GITHUB_TOKEN is required for live custom agent assignment testing"
  test: test_custom_agent_assignment
  category: environment
  resolution: marker_conversion

- file: tests/architecture/test_import_rules.py
  line: 54
  marker: pytest.skip
  reason: "services/ directory not found"
  test: TestServicesBoundary.test_services_do_not_import_api
  category: path_bug
  resolution: path_fix

- file: tests/architecture/test_import_rules.py
  line: 93
  marker: pytest.skip
  reason: "api/ directory not found"
  test: TestApiBoundary.test_api_does_not_import_store_modules
  category: path_bug
  resolution: path_fix

- file: tests/architecture/test_import_rules.py
  line: 116
  marker: pytest.skip
  reason: "models/ directory not found"
  test: TestModelsBoundary.test_models_do_not_import_services
  category: path_bug
  resolution: path_fix

- file: tests/performance/test_board_load_time.py
  line: 40
  marker: pytest.skip
  reason: "PERF_GITHUB_TOKEN not set"
  test: _skip_if_missing_prereqs
  category: environment
  resolution: marker_conversion

- file: tests/performance/test_board_load_time.py
  line: 42
  marker: pytest.skip
  reason: "PERF_PROJECT_ID not set"
  test: _skip_if_missing_prereqs
  category: environment
  resolution: marker_conversion

- file: tests/performance/test_board_load_time.py
  line: 49
  marker: pytest.skip
  reason: "Backend unhealthy"
  test: _ensure_backend_running
  category: environment
  resolution: marker_conversion

- file: tests/performance/test_board_load_time.py
  line: 51
  marker: pytest.skip
  reason: "Backend not reachable"
  test: _ensure_backend_running
  category: environment
  resolution: marker_conversion

- file: tests/performance/test_board_load_time.py
  line: 68-71
  marker: pytest.skip
  reason: "Could not authenticate via dev-login"
  test: _create_session
  category: environment
  resolution: marker_conversion
```

#### Frontend E2E Markers

```yaml
- file: e2e/project-load-performance.spec.ts
  line: 47
  marker: test.skip
  reason: "Auth state not found"
  test: beforeEach
  category: environment
  resolution: project_config

- file: e2e/project-load-performance.spec.ts
  line: 50
  marker: test.skip
  reason: "E2E_PROJECT_ID env var not set"
  test: beforeEach
  category: environment
  resolution: project_config

- file: e2e/project-load-performance.spec.ts
  line: 65
  marker: test.skip
  reason: "Frontend not reachable"
  test: board loads within 10s
  category: environment
  resolution: project_config

- file: e2e/project-load-performance.spec.ts
  line: 114
  marker: test.skip
  reason: "Frontend not reachable"
  test: project selection + board load
  category: environment
  resolution: project_config

- file: e2e/integration.spec.ts
  line: 62
  marker: test.skip
  reason: "Backend not running (CI)"
  test: should call health endpoint
  category: environment
  resolution: project_config

- file: e2e/integration.spec.ts
  line: 73
  marker: test.skip
  reason: "Backend not running (CI)"
  test: should handle 401 from auth endpoint
  category: environment
  resolution: project_config
```

## Entity: Test Fixture (Backend)

The central autouse fixture `_clear_test_caches` manages module-level state. No changes needed — already comprehensive (30+ clears, addressed in spec 019).

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Fixture function name |
| `scope` | `enum` | `function` (runs per test) |
| `autouse` | `bool` | `True` — applies to all tests automatically |
| `modules_cleared` | `list[str]` | Module paths whose globals are reset |

## Entity: Test Category (Backend)

Pytest markers define test categories for selective execution.

| Marker | Existing? | Default Behavior | Explicit Run |
|--------|-----------|-----------------|--------------|
| `integration` | ✅ Yes (defined in pyproject.toml) | Excluded via `addopts` | `-m integration` |
| `performance` | ✅ Yes (defined in pyproject.toml) | Excluded via `addopts` | `-m performance` |

### Configuration Change

```toml
# pyproject.toml [tool.pytest.ini_options]
# Add default exclusion of environment-dependent test categories
addopts = "-m 'not integration and not performance'"
```

This ensures `pytest tests/` by default runs only unit + architecture tests that don't require external services.

## Entity: Coverage Threshold

| Stack | Metric | Current | Target (Post-Uplift) |
|-------|--------|---------|---------------------|
| Backend | fail_under | 75% | 75% (maintain) |
| Frontend | statements | 50% | 70% (raise after Step 6) |
| Frontend | branches | 44% | 50% (raise after Step 6) |
| Frontend | functions | 41% | 50% (raise after Step 6) |
| Frontend | lines | 50% | 70% (raise after Step 6) |

## Relationships

```
Skip Marker ──resolves-via──→ Resolution Strategy
    │                              │
    ├── marker_conversion ────→ Test Category (pytest marker)
    ├── path_fix ─────────────→ Source code fix (test_import_rules.py)
    ├── fallback_logic ───────→ Source code fix (test_run_mutmut_shard.py)
    └── project_config ───────→ Playwright config (playwright.config.ts)

Test Category ──excludes-by-default──→ pytest addopts
Test Category ──runs-explicitly──→ CI pipeline job

Coverage Threshold ──raised-by──→ Step 6 (net-new tests)
```

## Validation Rules

1. **Zero unconditional skip markers**: After implementation, `grep -r "pytest.mark.skip\|pytest.skip\|@pytest.mark.xfail" solune/backend/tests/` returns zero results (excluding conditional e2e patterns)
2. **Test categories exclusive**: A test may have at most one category marker (`integration` OR `performance`, not both)
3. **Coverage non-regression**: Backend coverage must stay ≥75%; frontend must reach ≥70% statements
4. **No production code changes for skip removal**: Skip resolution must not modify `solune/backend/src/` or `solune/frontend/src/` production code (test infrastructure only)
5. **Exception**: Production bugs discovered during skip resolution (e.g., path resolution in `test_import_rules.py`) may require production fixes, documented in CHANGELOG.md

## State Transitions

No state machines in this feature. All changes are static configuration and test infrastructure.
