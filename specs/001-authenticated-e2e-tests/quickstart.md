# Quickstart: Add Authenticated E2E Tests for Core Application

**Feature**: `001-authenticated-e2e-tests` | **Date**: 2026-03-30

## Prerequisites

- Python 3.12+
- `uv` package manager installed
- Repository cloned and backend dependencies installed

```bash
cd solune/backend
uv sync --all-extras
```

## Running the E2E Tests

### Run all authenticated E2E tests

```bash
cd solune/backend
uv run pytest tests/e2e/ -v
```

### Run a specific E2E test file

```bash
cd solune/backend
uv run pytest tests/e2e/test_auth_flow.py -v
uv run pytest tests/e2e/test_projects_flow.py -v
uv run pytest tests/e2e/test_chat_flow.py -v
uv run pytest tests/e2e/test_pipeline_flow.py -v
uv run pytest tests/e2e/test_board_flow.py -v
```

### Run full test suite (verify no regressions)

```bash
cd solune/backend
uv run pytest tests/ -v
```

## Writing a New E2E Test

### 1. Use the `auth_client` fixture

The `auth_client` fixture (defined in `tests/e2e/conftest.py`) provides an `httpx.AsyncClient` with a valid session cookie. All requests made through this client are authenticated.

```python
import pytest

@pytest.mark.anyio
async def test_my_authenticated_flow(auth_client):
    # auth_client already has a valid session cookie
    response = await auth_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["github_username"] == "testuser"
```

### 2. Use the `unauthenticated_client` fixture for 401 tests

```python
@pytest.mark.anyio
async def test_requires_auth(unauthenticated_client):
    response = await unauthenticated_client.get("/api/v1/auth/me")
    assert response.status_code == 401
```

### 3. Mock GitHub API responses for project operations

```python
@pytest.mark.anyio
async def test_list_projects(auth_client, mock_github_projects_service):
    mock_github_projects_service.list_user_projects.return_value = [
        # Return mock project data
    ]
    response = await auth_client.get("/api/v1/projects")
    assert response.status_code == 200
```

### 4. Access the test database directly

```python
@pytest.mark.anyio
async def test_session_persisted(auth_client, test_db):
    # Verify session was stored in DB
    from src.services.session_store import get_session
    sessions = await test_db.execute("SELECT * FROM user_sessions")
    rows = await sessions.fetchall()
    assert len(rows) == 1
```

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Auth method | Dev-login endpoint with mocked `create_session_from_token` | Exercises real cookie/session flow |
| Database | Real in-memory SQLite with migrations | Tests real SQL, real session store |
| Mocked services | GitHub API, AI agents, WebSocket | Network-dependent; keep internal services real |
| Test isolation | Fresh app + DB per test | No shared state; each test is independent |
| Test location | `tests/e2e/` directory | Clear separation from unit/integration tests |

## Frontend Authenticated E2E (Phase 2)

### Run frontend authenticated E2E tests

```bash
cd solune/frontend
npx playwright test e2e/authenticated-flows.spec.ts
```

### Extending the fixture

The `authenticated-fixtures.ts` file extends the existing `fixtures.ts` pattern:

```typescript
import { test } from './authenticated-fixtures';

test('dashboard shows user projects', async ({ page }) => {
  await page.goto('http://localhost:5173');
  // /api/v1/auth/me returns 200 with mock user
  // /api/v1/projects returns mock project list
  await expect(page).toContainText('Test Project');
});
```

## Verification Checklist

- [ ] `cd solune/backend && uv run pytest tests/e2e/ -v` — all E2E tests pass
- [ ] `cd solune/backend && uv run pytest tests/ -v` — no regressions
- [ ] `cd solune/frontend && npx playwright test e2e/authenticated-flows.spec.ts` — frontend tests pass (Phase 2)
- [ ] Each test completes within 5 seconds
- [ ] No network calls to external services during test execution
