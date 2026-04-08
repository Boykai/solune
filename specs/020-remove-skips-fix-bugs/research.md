# Research: Uplift Solune Testing — Remove Skips, Fix Bugs, Apply Modern Best Practices

**Feature**: 020-remove-skips-fix-bugs | **Date**: 2026-04-08

## R1: Backend Skip Marker Categories and Resolution Patterns

### Decision: Categorize skips into three resolution strategies

**Rationale**: Not all skip markers are equal. Environment-dependent skips (need live services), path-resolution bugs, and shallow-clone limitations each require different remediation.

**Findings**:

1. **Environment-dependent skips (7 of 10)**: Tests in `test_custom_agent_assignment.py` and `test_board_load_time.py` skip because they require live GitHub tokens, running backend, or specific environment variables. These are properly guarded integration/performance tests.

2. **Path-resolution bugs (3 of 10)**: Tests in `test_import_rules.py` skip because directory paths resolve incorrectly (`services/`, `api/`, `models/` not found). The root cause is that the tests construct paths relative to the wrong base directory — they need to use `src/` prefix.

3. **Shallow-clone limitation (1 of 10)**: `test_run_mutmut_shard.py` skips when the CI workflow YAML is not available in a shallow clone.

**Resolution Strategy**:
- **Environment-dependent**: Convert `pytest.skip()` to proper `@pytest.mark.integration` or `@pytest.mark.performance` markers. Configure `addopts` to exclude these by default. Tests run when explicitly selected with `-m integration` or `-m performance`.
- **Path-resolution**: Fix the path construction to correctly locate `src/services/`, `src/api/`, `src/models/`. No production code change needed.
- **Shallow-clone**: Make the CI workflow file path configurable or fall back to a known default shard count when file is missing, so the test can still validate the sharding logic.

**Alternatives Considered**:
- Leave conditional skips as-is: Rejected — issue mandates zero skip markers
- Use `pytest.importorskip()`: Not applicable — skips are environment/path-based, not import-based
- Use `@pytest.mark.skipif` with env var checks: Still a skip marker — issue mandates removal

---

## R2: Frontend E2E Skip Pattern — Playwright Best Practices

### Decision: Retain Playwright's native `test.skip(condition, reason)` for prerequisite checks

**Rationale**: Playwright's documentation explicitly recommends `test.skip()` inside `beforeEach` or test body for conditional prerequisite validation. This is the framework's intended mechanism for tests that require live services.

**Findings**:

1. **Playwright's official documentation** (https://playwright.dev/docs/test-annotations) states:
   > "Use test.skip() when you need to conditionally skip based on some run-time condition."

2. All 6 frontend skip markers are in e2e tests that require:
   - Live backend running and healthy
   - Auth state saved from a prior setup step
   - Environment variables (E2E_PROJECT_ID, PERF_GITHUB_TOKEN)

3. These are **not** broken tests — they are correctly guarded prerequisites for tests that cannot run without infrastructure.

4. The `useAuth.test.tsx` file has **zero** skip markers and runs all 18 tests reliably.

**Resolution Strategy**:
- For `integration.spec.ts`: Move backend-dependent tests into a dedicated Playwright project configured in `playwright.config.ts` that only runs when backend is available. Remove `test.skip()` from test bodies.
- For `project-load-performance.spec.ts`: Convert conditional skips to Playwright project-level configuration with `test.describe.configure()` and prerequisite checks at the describe level.
- Document conditional e2e skips as accepted exceptions where live-service dependency makes unconditional execution impossible.

**Alternatives Considered**:
- Remove all skips unconditionally: Rejected — tests would fail when services unavailable
- Use `test.fixme()`: Rejected — semantically wrong (tests are not broken, they need prerequisites)
- Use separate test files per environment: Considered — viable but increases file count without benefit

---

## R3: Modern pytest Async Patterns

### Decision: Verify existing configuration meets best practices

**Rationale**: The codebase already uses `asyncio_mode = "auto"` and `asyncio_default_fixture_loop_scope = "function"`, which are the modern best practices for pytest-asyncio.

**Findings**:

1. **`asyncio_mode = "auto"`** (already set in `pyproject.toml` line 114): Automatically applies `@pytest.mark.asyncio` to all async test functions. No manual decoration needed.

2. **`asyncio_default_fixture_loop_scope = "function"`** (already set at line 115): Each test gets its own event loop, preventing cross-test contamination. This is the recommended setting.

3. **`_clear_test_caches` autouse fixture** (conftest.py lines 245-388): Already comprehensive — clears 30+ module-level caches. Addressed in spec 019.

4. **Coverage threshold**: Set at 75% (stricter than the issue's 70% request). Keep existing threshold.

5. **No deprecated loop fixtures** found in `tests/helpers/`.

**Resolution Strategy**:
- No changes needed to pytest infrastructure
- Verify `filterwarnings` configuration if present
- Confirm zero asyncio deprecation warnings in test output

**Alternatives Considered**:
- Lower coverage to 70%: Rejected — existing 75% is stricter and better
- Add `pytest-randomly`: Already addressed in spec 019 (test-isolation-remediation)
- Change to `session`-scoped event loop: Rejected — function scope prevents contamination

---

## R4: Modern Vitest Patterns for Frontend Tests

### Decision: Verify existing configuration and add jest-axe if missing

**Rationale**: The Vitest configuration is already well-set with happy-dom, globals, v8 coverage, and setup files.

**Findings**:

1. **`environment: 'happy-dom'`** (already set): Lighter than jsdom, sufficient for Testing Library.

2. **`globals: true`** (already set): `describe`, `it`, `expect`, `vi` available without imports.

3. **`coverage.provider: 'v8'`** (already set): Native V8 coverage, faster than Istanbul.

4. **Coverage thresholds**: Currently 50% statements, 44% branches, 41% functions, 50% lines. Issue targets 70% statements — will need to raise after adding coverage.

5. **`setupFiles: './src/test/setup.ts'`** (already set): Contains global mocks for crypto.randomUUID, WebSocket, window.location, window.history.

6. **`@testing-library/jest-dom/vitest`**: Already imported in setup.ts.

7. **`jest-axe`**: Need to verify if configured in setup.ts for global availability.

**Resolution Strategy**:
- Verify jest-axe is configured in `src/test/setup.ts`
- If not present, add `jest-axe` import and `expect.extend(toHaveNoViolations)` to setup
- Raise coverage thresholds to 70% after Step 6 adds net-new coverage
- No other infrastructure changes needed

**Alternatives Considered**:
- Switch to jsdom: Rejected — happy-dom is faster and already working
- Use istanbul coverage: Rejected — v8 is native and faster
- Remove globals: Rejected — already set and working; would require adding imports everywhere

---

## R5: httpx.AsyncClient with ASGITransport — Modern Endpoint Testing

### Decision: Use httpx.AsyncClient with ASGITransport for new endpoint tests in Step 6

**Rationale**: This is the modern pattern for testing async FastAPI applications. The existing `client` fixture in conftest.py already uses this pattern.

**Findings**:

1. The existing `client` fixture creates an async httpx client with the FastAPI app
2. New endpoint tests (HMAC webhook validation, etc.) should use the same pattern
3. `ASGITransport` avoids lifespan issues that occur with Starlette's `TestClient` in async contexts

**Resolution Strategy**:
- Use existing `client` fixture for new endpoint tests
- For HMAC webhook tests: craft requests with custom headers and body, assert signature validation
- Pattern: `async with httpx.AsyncClient(transport=ASGITransport(app=app)) as client:`

**Alternatives Considered**:
- Starlette TestClient: Rejected — synchronous, has lifespan issues with async apps
- requests library: Rejected — synchronous, not suitable for async testing

---

## R6: Net-New Coverage Targets — Best Practices

### Decision: Focus on behavior assertions, not implementation details

**Rationale**: Tests should assert observable behavior (output, side effects, state changes) rather than internal implementation (mock call counts, argument matching).

**Findings**:

1. **`resolve_repository()`** in `src/utils.py`: 4-step fallback chain is critical business logic. Tests should verify each fallback step returns correct (owner, repo) tuple.

2. **`pipeline_state_store.py` restart survivability**: Write state → reset in-memory cache → read back from SQLite. Tests verify durability, not internal cache mechanics.

3. **`webhooks.py` HMAC validation**: Security-critical. Tests must cover valid signature, invalid signature, missing header, and tampered body.

4. **`tools/presets.py` catalog**: Enumeration test ensures all presets are present and structurally valid.

5. **Fernet encryption** roundtrip: Encrypt → decrypt → assert equality. Also test invalid key and corrupted ciphertext error paths.

6. **Frontend `api.ts`**: Authenticated request helper with retry. Test success, 401 retry, network error.

**Resolution Strategy**:
- Each test covers happy path + one error/edge case minimum
- Use existing helpers from `tests/helpers/assertions.py` and `tests/helpers/factories.py`
- Assert behavior (return values, raised exceptions) not implementation (mock internals)

**Alternatives Considered**:
- Snapshot testing: Rejected — brittle, doesn't test behavior
- Property-based testing (Hypothesis): Considered — good for utils but overkill for this scope
- Full integration tests: Considered — too heavy; unit tests with mocks are sufficient for these paths
