# Research: Add Authenticated E2E Tests for Core Application

**Feature**: `001-authenticated-e2e-tests` | **Date**: 2026-03-30

## R1: Session Bootstrapping Strategy for E2E Tests

**Question**: How should E2E tests authenticate without requiring real GitHub OAuth credentials?

**Decision**: Use the dev-login endpoint (`POST /api/v1/auth/dev-login`) with a mocked `create_session_from_token` method on `GitHubAuthService`.

**Rationale**:
- The dev-login endpoint exists specifically for development/testing scenarios (guarded by `DEBUG=true`)
- It exercises the real cookie/session flow: `create_session_from_token()` → `save_session()` → `_set_session_cookie()`
- Mocking only `create_session_from_token` (which calls the GitHub API to verify the PAT) keeps all internal session machinery real: cookie issuance, session store CRUD, encryption, expiry checks
- The existing `test_api_e2e.py` already demonstrates this pattern with `patch.object(github_auth_service, "create_session_from_token", ...)`

**Alternatives Considered**:
1. **Direct session injection via `app.dependency_overrides[get_session_dep]`**: Rejected because it bypasses the entire auth middleware, cookie handling, and session store — defeating the purpose of E2E testing
2. **Real GitHub PAT in CI secrets**: Rejected because it introduces network dependency, token rotation burden, and rate limiting risk in CI
3. **Custom test auth middleware**: Rejected per Constitution Principle V (Simplicity) — the dev-login endpoint already provides the needed functionality

## R2: Database Strategy for E2E Tests

**Question**: How should the database be provisioned for E2E tests?

**Decision**: Use a real in-memory SQLite database (`:memory:`) with all migrations applied via `_apply_migrations()`.

**Rationale**:
- The existing `conftest.py` already implements `_apply_migrations(db)` which reads all `.sql` files from `src/migrations/` and executes them in sorted order
- In-memory SQLite provides real SQL execution (INSERT, SELECT, UPDATE, DELETE) including session store operations (save, get, delete, purge)
- Session encryption/decryption via `EncryptionService` runs against real data
- Each test gets a fresh database via the `mock_db` fixture pattern (function scope), ensuring isolation

**Alternatives Considered**:
1. **Shared persistent SQLite file**: Rejected because it introduces test ordering dependencies and cleanup complexity
2. **Mocked database**: Rejected because it would not test real SQL behavior (e.g., migration correctness, foreign key constraints, session expiry queries)
3. **PostgreSQL test container**: Rejected as overkill — the application uses SQLite in all environments, and in-memory SQLite provides sufficient fidelity

## R3: External Service Mocking Boundaries

**Question**: Which services should be mocked vs. kept real in E2E tests?

**Decision**: Mock external network-dependent services; keep all internal application services real.

| Service | Strategy | Justification |
|---------|----------|---------------|
| `GitHubAuthService.create_session_from_token` | **Mock** | Calls GitHub API to verify PAT |
| `GitHubAuthService.get_session` | **Real** | Reads from local SQLite session store |
| `GitHubProjectsService` | **Mock** | Calls GitHub GraphQL API |
| `ChatAgentService` / `AIAgentService` | **Mock** | Calls external AI model APIs |
| `ConnectionManager` (WebSocket) | **Mock** | Requires active WebSocket connections |
| Session store (`save_session`, `get_session`, `delete_session`) | **Real** | Local SQLite CRUD |
| `EncryptionService` | **Real** | Local cryptography, no network |
| Auth middleware (`get_current_session`) | **Real** | Cookie validation + session lookup |
| CSRF/CSP/Rate-limit middleware | **Real** | Tests should exercise middleware stack |

**Rationale**: The goal of E2E tests is to verify application flow correctness through real internal machinery. Mocking is limited to the network boundary where services call external APIs (GitHub, AI providers). This maximizes the "end-to-end" nature of tests while maintaining offline execution capability.

**Alternatives Considered**:
1. **Mock everything except the endpoint handler**: Rejected — this would be equivalent to unit tests with extra steps
2. **No mocking (fully integrated)**: Rejected — requires real GitHub credentials and AI API keys, making CI unreliable

## R4: Test File Organization

**Question**: Where should authenticated E2E tests live in the test hierarchy?

**Decision**: Create a new `tests/e2e/` directory with a dedicated `conftest.py` and per-domain test files.

**Rationale**:
- The existing test hierarchy uses `tests/unit/`, `tests/integration/`, `tests/architecture/`, etc. — each with a clear scope
- `tests/test_api_e2e.py` exists but tests unauthenticated single-request scenarios — it's a different testing pattern
- A dedicated `tests/e2e/` directory clearly signals "multi-request authenticated flow tests" vs. the existing patterns
- The `conftest.py` in `tests/e2e/` inherits from the parent `tests/conftest.py` (pytest's fixture discovery), allowing reuse of `make_mock_github_service` and `_apply_migrations`
- Per-domain test files (`test_auth_flow.py`, `test_projects_flow.py`, etc.) map directly to user stories in the spec

**Alternatives Considered**:
1. **Add to existing `tests/integration/`**: Rejected because integration tests (e.g., `test_full_workflow.py`) use a different pattern (`_build_full_app()` with selective router inclusion) — the E2E tests use `create_app()` with the full middleware stack
2. **Add to existing `test_api_e2e.py`**: Rejected because it would mix unauthenticated and authenticated patterns in one file, making it unwieldy
3. **Per-story test files in `tests/unit/`**: Rejected because these tests are explicitly not unit tests — they exercise multiple endpoints across multiple requests

## R5: Authenticated Client Fixture Design

**Question**: How should the authenticated test client fixture be structured?

**Decision**: Provide an `auth_client` async fixture that returns an `httpx.AsyncClient` with a valid session cookie already set, ready for authenticated requests.

**Fixture Flow**:
1. Create a fresh `FastAPI` app via `create_app()`
2. Create an in-memory SQLite database with migrations applied
3. Override `get_db` to return the test database
4. Override `get_github_service` to return a mocked `GitHubProjectsService`
5. Override `get_chat_agent_service` / `get_ai_agent_service` with mocked services
6. Override `get_connection_manager` with a mocked `ConnectionManager`
7. Patch `github_auth_service.create_session_from_token` to return a `UserSession` without calling the GitHub API
8. Create an `httpx.AsyncClient` with `ASGITransport` wrapping the app
9. Call `POST /api/v1/auth/dev-login` with a test token
10. The client now holds the session cookie from the response — all subsequent requests are authenticated

**Rationale**:
- This exercises the full request pipeline: middleware → routing → auth dependency → handler → response
- Cookie persistence across requests verifies real session handling
- The fixture is reusable across all E2E test files via pytest's fixture scoping
- Tests can make additional assertions about the session state by querying the database directly

**Alternatives Considered**:
1. **Manually setting cookies via `client.cookies.set()`**: Rejected because it bypasses the cookie-setting logic in the auth endpoint (e.g., `httponly`, `secure`, `samesite` flags)
2. **Per-test authentication**: Rejected because it adds boilerplate to every test; the fixture pattern is DRY
3. **Session-scoped fixture**: Rejected because it violates FR-011 (test isolation) — each test must have a fresh app and database

## R6: Frontend Authenticated E2E Extension

**Question**: How should the frontend authenticated E2E fixtures be structured?

**Decision**: Create `authenticated-fixtures.ts` extending the existing `fixtures.ts` pattern with authenticated route mocks.

**Pattern**:
```typescript
// authenticated-fixtures.ts
export const test = base.extend({
  page: async ({ page }, use) => {
    await page.route('**/api/**', (route) => {
      const url = new URL(route.request().url());
      
      // /auth/me → 200 with mock user (authenticated)
      if (url.pathname.includes('/auth/me')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ github_username: 'testuser', ... }),
        });
      }
      
      // /projects → realistic project list
      // /board/projects/{id} → realistic board data
      // /chat/messages → realistic chat history
      // ... other endpoints return realistic mock data
    });
    await use(page);
  },
});
```

**Rationale**:
- Follows the existing pattern in `fixtures.ts` (Playwright `test.extend()` with `page.route()` interception)
- No backend required — frontend E2E tests run against mocked API responses
- Realistic mock data shapes validate that the frontend correctly handles authenticated API response structures

**Alternatives Considered**:
1. **Running a real backend in CI**: Rejected — adds CI complexity, database setup, and test flakiness from network issues
2. **MSW (Mock Service Worker)**: Rejected — the existing pattern uses Playwright's built-in route interception, which is simpler and already established

## R7: CSRF and Rate Limiting in E2E Tests

**Question**: How should CSRF protection and rate limiting be handled in E2E tests?

**Decision**: CSRF middleware is bypassed in test mode (env `TESTING=1`), and rate limiting is disabled via the same flag. The E2E tests exercise the middleware stack but benefit from these test-mode relaxations.

**Rationale**:
- The existing `conftest.py` sets `os.environ["TESTING"] = "1"` which disables rate limiting middleware
- CSRF validation checks for the `TESTING` env var and skips validation when set
- This is the established pattern used by all existing tests
- Testing CSRF/rate-limit behavior is out of scope for authenticated flow E2E tests (those are covered by dedicated middleware tests)

**Alternatives Considered**:
1. **Include CSRF token in E2E requests**: Rejected as out of scope — CSRF middleware has its own unit tests, and adding CSRF token management would add complexity without testing authenticated flows
2. **Disable all middleware**: Rejected — keeping middleware active (except CSRF/rate-limit) ensures the E2E tests exercise the real request pipeline
