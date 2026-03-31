# Research: Increase Backend Test Coverage & Fix Bugs

**Feature**: `002-backend-test-coverage` | **Date**: 2026-03-31

## Research Tasks

### R1: Async Test Patterns for FastAPI Endpoints

**Decision**: Use `pytest-asyncio` with `asyncio_mode = "auto"` (already configured in `pyproject.toml`). All new async test functions are automatically detected — no explicit `@pytest.mark.asyncio` decorator needed. For endpoint tests, use FastAPI's `TestClient` with `httpx.AsyncClient` via the existing `auth_client` fixture. For WebSocket tests, use `TestClient.websocket_connect()` context manager.

**Rationale**: The project already uses `asyncio_mode = "auto"` and has established patterns in existing test files. The `auth_client` fixture in `conftest.py` provides an authenticated async client with dependency overrides (mock session, mock database, mock settings). Following these patterns ensures consistency and avoids fixture conflicts.

**Alternatives considered**:
- Manual `@pytest.mark.asyncio` on each test: Rejected — redundant with auto mode already configured.
- `respx` for HTTP mocking: Rejected — the existing codebase uses `unittest.mock.AsyncMock` and `patch` consistently; adding a new library would violate the "no infrastructure refactoring" constraint.

---

### R2: Mocking aiosqlite Database Interactions

**Decision**: Use `MagicMock` (not `AsyncMock`) for `db.execute()` since aiosqlite returns a sync `_ContextManager` that supports both `await` and `async with`. The existing `mock_db` fixture in `conftest.py` provides a pre-configured mock. For cursor results, set `mock_cursor.fetchone.return_value` and `mock_cursor.fetchall.return_value` on the context manager.

**Rationale**: This is a verified pattern from `test_agent_tools.py` and other unit tests. aiosqlite's `execute()` returns a `_ContextManager` wrapping a cursor — it's not a pure coroutine. Using `AsyncMock` would cause type mismatches.

**Alternatives considered**:
- Real in-memory SQLite: Rejected — unit tests should isolate the code under test from database implementation. Integration tests (in `tests/e2e/`) already cover real database operations.
- `aiosqlite.connect(":memory:")`: Rejected — requires running migrations and adds setup complexity. The mocked approach is faster and more focused.

---

### R3: WebSocket Test Strategy for projects.py

**Decision**: Test WebSocket endpoints using FastAPI's `TestClient.websocket_connect()`. Mock the `connection_manager` singleton and all service calls (`github_projects_service.get_project_items()`, cache operations). Test scenarios: successful subscription with data push, stale revalidation counter triggering refresh, hash diffing detecting changes vs. no-op, and `WebSocketDisconnect` exception handling during cleanup.

**Rationale**: The `websocket_subscribe` endpoint in `projects.py` uses `connection_manager.connect()`, periodic `send_tasks()` calls, and `websocket.receive_json()` for keepalive. Testing requires mocking the WebSocket lifecycle methods and simulating the event loop. FastAPI's test client handles the WebSocket upgrade internally.

**Alternatives considered**:
- End-to-end WebSocket tests: Rejected — too slow and fragile for unit testing. The E2E suite already patches `_start_copilot_polling` and covers basic WebSocket connectivity.
- `websockets` library directly: Rejected — FastAPI's built-in test client provides sufficient WebSocket testing support.

---

### R4: CAS (Compare-and-Swap) Testing for Chores Service

**Decision**: Test CAS semantics in `update_chore_after_trigger()` by mocking `db.execute()` and verifying the `WHERE id = ? AND last_triggered_at = ?` clause. Simulate three scenarios: (1) NULL initial state (first trigger), (2) matching old value (successful update), (3) mismatched old value (double-fire prevention — `rowcount = 0`). Also test `clear_current_issue()` to verify it nullifies `current_issue_number` and `current_issue_node_id`.

**Rationale**: CAS is the critical concurrency safety mechanism in the chores service. The `WHERE last_triggered_at = ?` condition prevents double-firing when multiple evaluators run concurrently. Testing all three states (NULL, match, mismatch) ensures the SQL WHERE clause is correct and the `rowcount` check works properly.

**Alternatives considered**:
- Actual concurrent test with threading: Rejected — unit tests should verify the SQL logic, not the database engine's atomicity. Concurrent behavior is covered by the CAS WHERE clause itself.
- Property-based testing with Hypothesis: Rejected — the state space is small (3 scenarios) and deterministic testing is sufficient.

---

### R5: SQL Injection Defense Testing for update_chore_fields()

**Decision**: Test the column whitelist in `update_chore_fields()` by verifying that only columns in `_CHORE_UPDATABLE_COLUMNS` are accepted. Submit column names containing SQL injection payloads (e.g., `"name; DROP TABLE chores"`, `"1=1 OR name"`) and verify they are rejected before reaching `db.execute()`. Also test boolean-to-integer conversion for `enabled` and `auto_merge` fields.

**Rationale**: The `update_chore_fields()` function dynamically constructs `UPDATE chores SET {col} = ?` SQL, making the column name whitelist the primary defense against SQL injection. This is explicitly called out in the spec (FR-016) and parent issue.

**Alternatives considered**:
- Using parameterized queries for column names: Not possible in SQLite — column names cannot be parameterized, hence the whitelist approach.
- Regex-based column name validation: Rejected by the codebase — the whitelist is simpler and more secure.

---

### R6: AI Service Failure Mocking in Agent Creator

**Decision**: Mock `get_ai_agent_service()` to return an `AsyncMock` that raises specific exceptions. Test scenarios: `generate_agent_config()` raises `Exception("AI service timeout")`, `edit_agent_config()` returns malformed response (missing expected fields), and tools response is a string instead of a list. Verify the system returns user-facing error messages without exposing internal details.

**Rationale**: The agent creator's 8-step pipeline depends on AI services for configuration generation and editing. Failure at any step must be handled gracefully — partial resources should be cleaned up and the user should receive actionable feedback. The existing `TestExceptionPaths` class in `test_agent_creator.py` provides a pattern for these tests.

**Alternatives considered**:
- Using `side_effect` with specific exception types: Adopted — this is the standard `unittest.mock` pattern for simulating failures.
- Mocking at the HTTP level: Rejected — the AI service is accessed through internal Python functions, not HTTP calls from the test perspective.

---

### R7: Parallel Test Execution Strategy

**Decision**: Phases 3/4 and 4/5 can be implemented in parallel since they modify independent test files (`test_agent_creator.py` and `test_agents_service.py` for Phase 3/4; `test_agents_service.py` and `test_chores_service.py` for Phase 4/5). Each test file is self-contained with its own fixtures and mocks. No shared mutable state between test modules.

**Rationale**: The parent issue explicitly states "Phase 4 — parallel with Phase 3" and "Phase 5 — parallel with Phase 4." The test files target different source modules and have no cross-dependencies.

**Alternatives considered**:
- Sequential execution only: Rejected — unnecessarily slow. The modules are independent.
- `pytest-xdist` parallel runner: Not needed at the planning level — this is about implementation ordering, not test runner parallelism.

---

### R8: Coverage Measurement Strategy

**Decision**: Use `pytest-cov` with per-file coverage reporting: `python -m pytest --cov=src.api.projects --cov=src.services.agent_creator --cov=src.services.agents.service --cov=src.services.chores.service --cov-report=term-missing tests/unit/`. Compare results against baseline measurements (37.7%, 39.4%, 47.4%, 51.3%).

**Rationale**: The project already has `pytest-cov` configured with `fail_under = 75%`. Per-file reporting allows tracking individual module improvement without running the full coverage suite (which includes all source files).

**Alternatives considered**:
- `coverage.py` directly: Rejected — `pytest-cov` is already configured and integrated.
- Branch coverage instead of line coverage: Worth considering but not mandated by the spec. Line coverage is the baseline metric.
