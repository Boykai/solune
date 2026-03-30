# Research: 100% Test Coverage with Bug Fixes

**Feature**: `001-full-test-coverage` | **Date**: 2026-03-30

## Research Tasks

### R-001: DevContainer CI Tag Pinning

**Context**: The issue references `devcontainers/ci@v0.3` as an invalid tag.

**Decision**: Pin to a valid, stable tag from the `devcontainers/ci` GitHub Action repository. Use the latest release tag verified at build time.

**Rationale**: Floating or invalid tags cause non-reproducible CI builds. Pinning to a valid tag (or specific SHA) ensures deterministic CI behavior. The `@v0.3` tag either doesn't exist or was removed — verify against the repository's releases page.

**Alternatives considered**:
- Pin to SHA: More deterministic but harder to maintain and read in YAML.
- Use `@main`: Defeats the purpose of pinning — too volatile.
- **Chosen**: Pin to the latest valid semver tag from the action's releases.

---

### R-002: Exception Handling in `verify_project_access()`

**Context**: `dependencies.py` silently swallows exceptions in `verify_project_access()`, masking production failures.

**Decision**: Log the exception at WARNING level and re-raise as an `HTTPException(403)` with a descriptive message. This follows FastAPI's dependency injection error model.

**Rationale**: Silent exception swallowing violates the principle of fail-fast error handling. Production debugging requires visibility into access verification failures. Re-raising ensures the API returns a meaningful error to the client.

**Alternatives considered**:
- Log only (no re-raise): Would silently grant access on verification failure — security risk.
- Raise 500: Incorrect semantics — a failed access check is a 403, not a server error.
- **Chosen**: Log at WARNING + re-raise as HTTPException(403).

---

### R-003: Rate Limit Middleware Timeout

**Context**: `RateLimitKeyMiddleware` resolves user sessions with no timeout, potentially hanging indefinitely.

**Decision**: Add a configurable timeout (default: 5 seconds) using `asyncio.wait_for()` around session resolution. On timeout, fall back to IP-based rate limiting.

**Rationale**: Unbounded async operations in middleware risk blocking the entire request pipeline. A 5-second default balances session resolution latency against request responsiveness. IP-based fallback ensures rate limiting still functions.

**Alternatives considered**:
- Hard-coded timeout: Less flexible but simpler. Rejected because configuration may vary by deployment.
- Fail-open (no rate limit on timeout): Security risk — allows unlimited requests.
- **Chosen**: Configurable timeout with IP-based fallback.

---

### R-004: McpValidationError Field-Level Errors

**Context**: `McpValidationError` in `exceptions.py` doesn't include field-level error details.

**Decision**: Extend `McpValidationError` to accept an optional `field_errors: dict[str, list[str]]` parameter. Serialize this into the error response payload as a `details` or `field_errors` key.

**Rationale**: Field-level errors are essential for client-side form validation and API consumer debugging. Without them, callers must guess which field caused the validation failure.

**Alternatives considered**:
- String concatenation of all field errors: Loses structured data — hard for clients to parse.
- Pydantic ValidationError passthrough: Exposes internal model details — leaks implementation.
- **Chosen**: Structured `field_errors` dict following REST API error conventions.

---

### R-005: Backend Test Patterns for New Service Modules

**Context**: New test files needed for `agent_middleware.py`, `agent_provider.py`, `collision_resolver.py`.

**Decision**: Follow the established patterns in `tests/conftest.py`, `tests/helpers/factories.py`, and `tests/helpers/assertions.py`:
- Class-based test organization (`class TestAgentMiddleware:`)
- Shared fixtures from `conftest.py` (`mock_session`, `mock_db`, `mock_settings`, `client`)
- Factory functions for test data (`make_task()`, `make_chat_message()`)
- `AsyncMock` for async service dependencies
- `assert_api_success()` / `assert_api_error()` for HTTP response validation

**Rationale**: Consistency with 152 existing test files ensures maintainability and reduces cognitive load. The existing infrastructure (fixtures, factories, assertions) handles common patterns — no need to reinvent.

**Alternatives considered**:
- Function-based tests: Inconsistent with existing class-based organization.
- New test framework (e.g., ward, nox): Violates FR-035 (no new frameworks).
- **Chosen**: Mirror existing patterns exactly.

---

### R-006: Frontend Component Test Patterns

**Context**: ~56 untested frontend component files need test coverage.

**Decision**: Follow the established patterns:
- Use `renderWithProviders()` from `src/test/test-utils.tsx` for consistent provider wrapping
- Include `expectNoA11yViolations()` in every component test
- Use `@testing-library/react` queries (`getByRole`, `getByText`, `findByText`)
- Use `@testing-library/user-event` for interaction simulation
- Use `vi.mock()` for service/hook mocking
- Co-locate test files with source files (e.g., `AgentCard.test.tsx` next to `AgentCard.tsx`)

**Rationale**: 165 existing test files follow these patterns. Consistency ensures any developer can navigate and maintain the test suite.

**Alternatives considered**:
- Enzyme: Deprecated, not compatible with React 18+.
- Separate `__tests__/` directories: Inconsistent with co-located test file pattern.
- **Chosen**: Co-located tests using Testing Library + jest-axe.

---

### R-007: Mutation Testing Expansion Strategy

**Context**: Backend mutmut covers only `src/services/`; frontend Stryker covers only `src/hooks/**/*.ts` and `src/lib/**/*.ts`.

**Decision**: Expand incrementally in Phase 6 after full coverage safety net is in place:
1. Backend: Change `paths_to_mutate` from `["src/services/"]` to `["src/"]` in `pyproject.toml`
2. Frontend: Add `src/components/**/*.tsx` and `src/pages/**/*.tsx` to `mutateFiles` in `stryker.config.mjs`
3. Start with soft thresholds (no `break` value in Stryker); harden after first successful run

**Rationale**: Mutation testing on uncovered code wastes CI time. Expanding after coverage ensures mutants are meaningful. Incremental expansion reduces blast radius if mutation testing reveals unexpected issues.

**Alternatives considered**:
- Expand mutation testing in parallel with coverage work: Risks flaky CI during development.
- Skip mutation testing entirely: Misses weak assertions that inflate coverage without value.
- **Chosen**: Phase 6 incremental expansion with soft thresholds first.

---

### R-008: Singleton Refactor Strategy

**Context**: `github_projects/service.py` and `agents.py` use module-level singletons (TODO debt), making them hard to test in isolation.

**Decision**: Defer refactor to Phase 6. In earlier phases, use test-time monkey-patching or `importlib.reload()` to work around singleton state. In Phase 6, refactor to dependency injection (constructor parameters with default factory functions).

**Rationale**: Refactoring singletons without a coverage safety net risks introducing regressions. The test-wrap-first approach (Phases 2–3) builds the safety net; Phase 6 performs the refactor with confidence.

**Alternatives considered**:
- Refactor singletons first: Higher risk — no coverage safety net to catch regressions.
- Leave singletons permanently: Accumulates technical debt; tests remain fragile.
- **Chosen**: Test-wrap first, refactor in Phase 6 with full coverage protection.

---

### R-009: Coverage Regression Guard

**Context**: Need CI to fail on any coverage decrease after 100% is achieved.

**Decision**: Use existing tools:
- Backend: Set `fail_under = 100` in `pyproject.toml` `[tool.coverage.report]`
- Frontend: Set all thresholds to `100` in `vitest.config.ts` coverage configuration
- Both tools already fail the build when thresholds are not met

**Rationale**: The simplest approach uses built-in features of pytest-cov and Vitest. No custom scripts or additional CI steps needed.

**Alternatives considered**:
- Custom diff-based guard (compare coverage reports between commits): Over-engineered for this use case.
- Codecov/Coveralls GitHub integration: External dependency, adds complexity.
- **Chosen**: Built-in threshold enforcement in pytest-cov and Vitest.

---

### R-010: Handling Unreachable Code and Coverage Exclusions

**Context**: Some code paths may be legitimately unreachable (defensive assertions, `TYPE_CHECKING` blocks, platform-specific branches).

**Decision**: Use existing exclusion mechanisms:
- Backend: `# pragma: no cover` inline, plus existing `exclude_lines` in `pyproject.toml` (`if TYPE_CHECKING:`, `if __name__ == "__main__"`)
- Frontend: Vitest coverage `exclude` patterns for `src/test/**`, `src/main.tsx`, `src/vite-env.d.ts`
- Each exclusion must have a comment explaining why the code is unreachable

**Rationale**: Exclusion markers are standard in Python and TypeScript coverage tooling. Requiring justification comments prevents abuse.

**Alternatives considered**:
- Remove unreachable code: May break defensive programming patterns.
- Accept <100% for specific files: Undermines the 100% threshold goal.
- **Chosen**: Justified exclusion markers with existing tooling.
