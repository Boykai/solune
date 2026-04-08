# Contract: Backend Test Infrastructure & Coverage

**Feature**: 020-uplift-solune-testing | **Date**: 2026-04-08

## Purpose

Defines the contract for backend test infrastructure configuration, coverage enforcement, and test modernization patterns.

## Contract 1: Coverage Enforcement

### Current State

The CI command runs pytest with coverage reporting, and `pyproject.toml` already enforces a minimum threshold of 75%:

```yaml
run: uv run pytest --cov=src --cov-report=term-missing --cov-report=xml --cov-report=html --durations=20 --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency
```

```toml
[tool.coverage.report]
fail_under = 75
```

### Required State

Preserve the existing `fail_under = 75` in `pyproject.toml`, which already exceeds issue #1149's 70% minimum. No changes needed.

### Behavior

- CI MUST fail if backend coverage drops below 75% (the existing threshold)
- The threshold applies to line coverage across `src/`
- Tests in `tests/property`, `tests/fuzz`, `tests/chaos`, `tests/concurrency` are excluded from the main CI run

## Contract 2: Modern Async Test Patterns

### Applies To

All new backend tests and any refactored existing tests.

### Rules

1. **Fixtures**: Use `@pytest_asyncio.fixture(scope="function")` for async fixtures
2. **Mocking**: Use `AsyncMock` (not `MagicMock`) for coroutine mocks
3. **HTTP Client**: Use `httpx.AsyncClient` with `ASGITransport` for endpoint tests
4. **Event Loop**: Rely on `asyncio_mode = "auto"` — do not use deprecated `@pytest.mark.asyncio`

### Example Pattern

```python
import pytest
from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient
from src.main import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

async def test_endpoint(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200
```

## Contract 3: Conditional Skip Pattern (Infrastructure Guards)

### Applies To

Tests that require external infrastructure (tokens, running services, specific files).

### Acceptable Pattern

Runtime `pytest.skip()` inside the test body with a clear message:

```python
def test_live_integration():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        pytest.skip("GITHUB_TOKEN is required for live testing")
    # ... test with live infrastructure
```

### Unacceptable Patterns

```python
# WRONG: Unconditional skip hiding a bug
@pytest.mark.skip(reason="TODO: fix this")
def test_broken_feature():
    ...

# WRONG: xfail hiding a known production bug
@pytest.mark.xfail(reason="Known bug in webhook handler")
def test_webhook_validation():
    ...
```

## Contract 4: Net-New Backend Test Requirements

### Applies To

All new tests added in Step 6.

### Rules

1. Assert **behavior**, not implementation details
2. Cover **happy path** plus at least **one error/edge case**
3. Use existing helpers from `tests/helpers/`
4. Follow existing test file naming: `test_{module_name}.py`
5. Place in appropriate directory: `tests/unit/`, `tests/integration/`, etc.
6. All async tests MUST use `async def` with `AsyncMock`

### Coverage Targets

| Module | Minimum New Tests | Required Scenarios |
|--------|------------------|--------------------|
| `utils.py:resolve_repository()` | 3 | Cache hit, fallback chain, error handling |
| `api/webhooks.py` HMAC | 3 | Valid signature, invalid signature, missing header |
| `services/tools/presets.py` | 2 | Catalog listing, individual preset retrieval |
| `services/encryption.py` Fernet | 2 | Encrypt-decrypt roundtrip, invalid key error |
| `services/pipeline_state_store.py` | 2 | Persist and recover state, lock re-init |
