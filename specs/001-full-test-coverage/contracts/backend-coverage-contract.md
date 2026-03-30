# Backend Coverage Contract

**Feature**: `001-full-test-coverage` | **Date**: 2026-03-30

## Purpose

This contract defines the verification criteria for backend test coverage at each phase boundary. All metrics are measured using `pytest-cov` with branch coverage enabled.

## Verification Commands

```bash
# Run tests with coverage (CI-equivalent)
cd solune/backend
uv run pytest --cov=src --cov-branch --cov-report=term-missing \
  --ignore=tests/property --ignore=tests/fuzz \
  --ignore=tests/chaos --ignore=tests/concurrency

# Mutation testing
uv run mutmut run
uv run mutmut results
```

## Phase Contracts

### Phase 1: Green Baseline

| Metric | Requirement | Verification |
|--------|-------------|--------------|
| Test suite status | All tests pass | `uv run pytest` exit code 0 |
| Known bugs | All 4 bug fixes applied | Manual review + specific test cases |
| CI pipeline | No configuration errors | CI workflow completes successfully |

**Acceptance command**: `uv run pytest` — exit code 0, zero failures.

### Phase 2: Untested Services (78% → ~85%)

| Metric | Minimum | Verification |
|--------|---------|--------------|
| Line coverage | ≥85% | `pytest --cov=src` reports ≥85% |
| Branch coverage | ≥80% | `pytest --cov-branch` reports ≥80% |
| New test files | 6+ created | `test_agent_middleware.py`, `test_agent_provider.py`, `test_collision_resolver.py`, etc. |
| Module coverage | 100% per new module | Each of `agent_middleware`, `agent_provider`, `collision_resolver` at 100% |
| Mutation score (new modules) | ≥80% killed | `mutmut results` for new service modules |

**Acceptance command**: `uv run pytest --cov=src --cov-branch --cov-fail-under=85`

### Phase 3: Branch Coverage Blitz (85% → ~95%)

| Metric | Minimum | Verification |
|--------|---------|--------------|
| Line coverage | ≥95% | `pytest --cov=src` reports ≥95% |
| Branch coverage | ≥90% | `pytest --cov-branch` reports ≥90% |
| Per-file branch coverage | ≥90% | No file in `coverage.json` below 90% branch |
| Integration tests | Cache, encryption, MCP store, template I/O | Tests exist and pass |
| Property tests | Pydantic roundtrip, URL parsing, labels | Hypothesis tests pass |
| Migration tests | Rollback + corruption | `test_migrations.py` extended |
| Mutation score (services) | ≥85% killed | `mutmut results` on `src/services/` |

**Acceptance command**: `uv run pytest --cov=src --cov-branch --cov-fail-under=95`

### Phase 6: Final Backend Threshold

| Metric | Requirement | Verification |
|--------|-------------|--------------|
| Line coverage | 100% | `pytest --cov-fail-under=100` exit code 0 |
| Branch coverage | 100% | `pytest --cov-branch` 100% |
| fail_under config | 100 | `pyproject.toml [tool.coverage.report].fail_under = 100` |
| mutmut scope | `src/` (all) | `pyproject.toml [tool.mutmut].paths_to_mutate = ["src/"]` |
| Mutation score (all src) | ≥85% killed | `mutmut results` |

**Acceptance command**: `uv run pytest --cov=src --cov-branch --cov-fail-under=100`

## Exclusion Policy

Lines excluded from coverage measurement:

| Pattern | Reason |
|---------|--------|
| `# pragma: no cover` | Explicitly marked unreachable/defensive code (requires justification comment) |
| `if TYPE_CHECKING:` | Type-only imports, never executed at runtime |
| `if __name__ == "__main__":` | Script entry point, not part of library API |

Each `# pragma: no cover` usage MUST include a comment explaining why the code is unreachable.
