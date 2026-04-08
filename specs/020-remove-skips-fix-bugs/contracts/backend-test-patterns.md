# Contract: Backend Test Patterns — Modern pytest Best Practices

**Feature**: 020-remove-skips-fix-bugs | **Date**: 2026-04-08

## Overview

Defines the standard patterns for backend tests after the skip-removal uplift. All new and modified tests must follow these patterns.

## Pattern 1: Environment-Dependent Test Categorization

### Before (skip-based)

```python
# ❌ Anti-pattern: conditional skip inside test body
def test_custom_agent_assignment():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        pytest.skip("GITHUB_TOKEN is required for live testing")
    # ... test logic ...
```

### After (marker-based)

```python
# ✅ Correct: pytest marker excludes by default, runs explicitly
@pytest.mark.integration
async def test_custom_agent_assignment(mock_settings):
    """Test custom agent assignment with live GitHub API."""
    # No skip logic — marker handles exclusion
    # ... test logic ...
```

### Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "integration: marks tests as integration tests (require external services)",
    "performance: marks tests as performance tests (require running backend + credentials)",
]
# Default: exclude integration and performance tests
addopts = "-m 'not integration and not performance'"
```

### Execution

```bash
# Default: unit + architecture tests only
pytest tests/

# Explicit: include integration tests
pytest tests/ -m integration

# Explicit: include performance tests
pytest tests/ -m performance

# All tests including integration and performance
pytest tests/ -m ""
```

## Pattern 2: Async Test Functions

### Standard async test

```python
# ✅ Correct: no decorator needed with asyncio_mode = "auto"
async def test_resolve_repository(client, mock_settings):
    """Test the resolve_repository fallback chain."""
    response = await client.get("/api/v1/repository")
    assert response.status_code == 200
```

### Async fixtures

```python
# ✅ Correct: function-scoped async fixture
@pytest_asyncio.fixture(scope="function")
async def mock_db():
    """Provide in-memory SQLite database."""
    async with aiosqlite.connect(":memory:") as db:
        yield db
```

## Pattern 3: Mock Patterns

### AsyncMock for coroutines

```python
# ✅ Correct: AsyncMock for async functions
mock_service = AsyncMock()
mock_service.fetch_data.return_value = {"key": "value"}

# ❌ Anti-pattern: MagicMock for async functions
mock_service = MagicMock()  # Will not properly await
```

### Typed mock access

```python
# ✅ Correct: patch with AsyncMock spec
with patch("src.services.github_auth.GitHubAuthService", spec=True) as mock_auth:
    mock_auth.return_value.validate_token = AsyncMock(return_value=True)
```

## Pattern 4: Endpoint Testing with httpx

### Standard endpoint test

```python
# ✅ Correct: use existing client fixture
async def test_webhook_hmac_validation(client):
    """Test HMAC signature validation on webhook endpoint."""
    payload = b'{"action": "opened"}'
    secret = "test-webhook-secret"
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    response = await client.post(
        "/api/webhooks/github",
        content=payload,
        headers={
            "X-Hub-Signature-256": f"sha256={signature}",
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "test-delivery-id",
        },
    )
    assert response.status_code == 200
```

## Pattern 5: Path-Resolution Fix for Architecture Tests

### Before (broken path)

```python
# ❌ Bug: looks for "services/" relative to tests/, not src/
services_dir = Path(__file__).parent.parent.parent / "services"
if not services_dir.is_dir():
    pytest.skip("services/ directory not found")
```

### After (correct path)

```python
# ✅ Correct: navigate to src/services/ from test file
SRC_DIR = Path(__file__).parent.parent.parent / "src"

class TestServicesBoundary:
    def test_services_do_not_import_api(self):
        services_dir = SRC_DIR / "services"
        assert services_dir.is_dir(), f"Expected {services_dir} to exist"
        # ... import analysis logic ...
```

## Pattern 6: Assertion Helpers

Use existing helpers from `tests/helpers/assertions.py`:

```python
from tests.helpers.assertions import (
    assert_api_success,
    assert_api_error,
    assert_json_structure,
    assert_json_values,
)

async def test_endpoint_success(client):
    response = await client.get("/api/health")
    data = assert_api_success(response)
    assert_json_structure(data, {"status", "version"})

async def test_endpoint_error(client):
    response = await client.get("/api/nonexistent")
    assert_api_error(response, status_code=404)
```

## Pattern 7: Test Data Factories

Use existing factories from `tests/helpers/factories.py`:

```python
from tests.helpers.factories import make_user_session, make_task

async def test_task_creation(client, mock_db):
    session = make_user_session(role="admin")
    task = make_task(title="Test Task", assignee=session.username)
    # ... test logic ...
```
