# Research: Bug Basher — Full Codebase Review & Fix

**Feature**: 002-bug-basher
**Created**: 2026-03-31
**Status**: Complete

## Research Tasks

### 1. Existing Security Tooling in the Codebase

**Decision**: Leverage the existing `bandit` (static security analysis) and `pip-audit` (dependency vulnerability audit) already configured as dev dependencies, plus `ruff` security-adjacent rules (B — flake8-bugbear) for the backend. Frontend uses `eslint-plugin-security` and `npm audit`.

**Rationale**: The project already has security scanning integrated into CI (`.github/workflows/ci.yml`). Using existing tools avoids adding new dependencies (FR-011 constraint) and ensures findings align with what CI already enforces.

**Alternatives considered**:
- Adding `safety` or `semgrep` — rejected per FR-011 (no new dependencies)
- Manual-only review — rejected as insufficient for consistent coverage

---

### 2. Test Framework Patterns and Conventions

**Decision**: Backend regression tests follow the existing pytest conventions: `tests/unit/test_*.py` files using `pytest-asyncio` auto mode, `AsyncMock`/`MagicMock` from `unittest.mock`, and fixtures from `conftest.py`. Frontend tests use Vitest with `@testing-library/react`.

**Rationale**: The codebase has 225 existing backend test files and 178 frontend test files with well-established patterns. Regression tests must be indistinguishable from existing tests in style and structure (FR-012).

**Key patterns observed**:
- Backend: `async def test_*` with `@pytest.mark.asyncio` (auto mode), fixtures like `mock_db`, `mock_github_service`, `client`
- PEP 695 type parameter syntax (`class Foo[T]:`) enforced by ruff UP046/UP047
- Line length: 100 characters
- Import sorting: isort via ruff `I` rules
- Frontend: `describe`/`it` blocks, `render()` with `@testing-library/react`, `vi.fn()` for mocks

**Alternatives considered**:
- Creating a separate test directory for bug-bash tests — rejected to maintain co-location with existing tests
- Using property-based tests for all regression tests — rejected as overkill for targeted bug fixes

---

### 3. Code Review Strategy for Large Codebases

**Decision**: Review files in priority order (security → runtime → logic → test quality → code quality) using a systematic file-by-file approach. Focus first on high-risk areas identified in the plan (workflow orchestrator, copilot polling, agents service, middleware, encryption, auth).

**Rationale**: The codebase has ~616 source files. Reviewing by risk priority ensures the most impactful bugs are found first. The high-risk areas were identified based on: file size (complexity proxy), security sensitivity, external API interaction, and concurrent state management.

**Alternatives considered**:
- Random sampling approach — rejected as it misses systematic patterns
- Coverage-driven approach (review least-tested code first) — rejected because coverage data alone doesn't indicate bug probability
- Tool-only approach (rely solely on bandit/ruff) — rejected as insufficient for logic bugs and test quality issues

---

### 4. Commit and Summary Strategy

**Decision**: Each bug fix is a separate, focused commit with a structured message. Ambiguous issues get `# TODO(bug-bash):` comments. A final summary table consolidates all findings.

**Rationale**: The spec explicitly requires minimal, focused fixes (FR-013), clear commit messages (FR-004), and a single summary table (FR-009). Separate commits enable easy revert of individual fixes if needed.

**Commit message format**:
```
fix(category): Brief description

What: [bug description]
Why: [why it's a bug]
How: [fix approach]
Test: [regression test description]
```

**Alternatives considered**:
- Batch commits per file — rejected as it makes individual fixes harder to revert
- Squash all into one commit — rejected as it loses traceability

---

### 5. Security Review Patterns for Python/FastAPI Applications

**Decision**: Focus security review on the OWASP Top 10 categories relevant to this stack: injection (SQL/command), broken authentication, sensitive data exposure, security misconfiguration, and insufficient logging.

**Rationale**: The application handles OAuth tokens, session management, encryption, and GitHub API integration — all high-value security targets. The middleware stack (auth, CSRF, CSP, rate limiting) is security-critical.

**Key areas for security review**:
- `services/encryption.py` — key management, Fernet usage, error handling
- `services/github_auth.py` — OAuth flow, token exchange, redirect URI validation
- `services/session_store.py` — session persistence, token encryption at rest
- `middleware/` — auth bypass possibilities, CSRF token validation, CSP headers
- `config.py` — insecure defaults, secret handling
- `api/auth.py` — token endpoints, session creation
- `services/mcp_server/auth.py` — MCP authentication, rate limiting
- `logging_utils.py` — verify sensitive data redaction coverage
- Exception handlers in `main.py` — ensure error messages don't leak internals

**Alternatives considered**:
- Full SAST scan with external tools — rejected per FR-011 (no new dependencies); existing bandit covers static analysis
- Penetration testing approach — out of scope for code review

---

### 6. Runtime Error Patterns in Async Python

**Decision**: Focus runtime error review on: unhandled exceptions in async code paths, missing `await` keywords, resource cleanup in `async with`/`try-finally`, connection pool exhaustion, and `None` propagation through async chains.

**Rationale**: The backend is async-first (FastAPI + aiosqlite + httpx). Common async pitfalls include: forgotten `await` (returns coroutine instead of result), unhandled `CancelledError`, file/connection handle leaks when exceptions bypass `finally` blocks, and race conditions in shared state.

**Key areas for runtime review**:
- `services/database.py` — connection lifecycle, migration execution
- `services/cache.py` — TTL expiry, bounded collection overflow
- `services/copilot_polling/` — retry logic, timeout handling, external API failures
- `services/workflow_orchestrator/` — concurrent state updates, group transitions
- `services/websocket.py` — connection cleanup on disconnect
- All `httpx` usage — timeout configuration, response body consumption

**Alternatives considered**:
- Adding runtime monitoring (e.g., `aiomonitor`) — rejected per FR-011
- Static analysis only — insufficient for detecting race conditions

---

### 7. Frontend Review Strategy

**Decision**: Apply the same five-category review to frontend code, focusing on: XSS via `dangerouslySetInnerHTML`, unvalidated API responses, missing error boundaries, stale closure bugs in hooks, and unhandled promise rejections.

**Rationale**: The frontend uses React 19.2 with TanStack Query for data fetching and Zod for schema validation. Common React bugs include: stale closures in `useEffect`/`useCallback`, missing dependency arrays, unhandled loading/error states, and unsafe HTML rendering.

**Key areas for frontend review**:
- API client services — error handling, response validation
- Form handling — input sanitization, validation bypass
- Route guards — authentication state checks
- WebSocket integration — reconnection logic, message parsing
- Component lifecycle — cleanup in `useEffect`, memory leaks

**Alternatives considered**:
- Skipping frontend (focus on backend only) — rejected as spec requires "every file in the repository" (FR-001)
- Using React DevTools profiling — out of scope for code review

---

### 8. Test Quality Assessment Methodology

**Decision**: Assess test quality by checking for: assertions that always pass (e.g., `assert True`, `assert mock.called` without verifying call args), `MagicMock` objects leaking into production-like paths (e.g., database file paths), incomplete mock isolation, and missing edge case coverage.

**Rationale**: The spec explicitly calls out mock leaks and false-positive assertions (User Story 4). The codebase uses `MagicMock` extensively; improper mock scoping can mask real bugs.

**Detection patterns**:
- `assert mock_*.called` without `assert_called_with()` — weak assertion
- `MagicMock()` used as file path or URL — mock leak
- `try/except` in tests that catch too broadly — swallows real failures
- Tests with no assertions — empty tests inflate coverage
- `@pytest.mark.skip` or `@pytest.mark.xfail` without justification — hidden debt

**Alternatives considered**:
- Mutation testing with `mutmut` to find weak tests — complementary but already configured; run separately from bug bash
- Coverage-only approach — insufficient for detecting false positives

## Resolution Summary

All research tasks resolved. No NEEDS CLARIFICATION items remain. The bug bash can proceed with:

1. Existing security tools (bandit, pip-audit, ruff, eslint-plugin-security)
2. Existing test patterns (pytest + Vitest conventions)
3. Priority-ordered file-by-file review strategy
4. Structured commit and summary reporting
5. Focus areas identified by risk analysis
