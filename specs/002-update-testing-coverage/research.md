# Research: Update Testing Coverage

**Feature**: 002-update-testing-coverage | **Date**: 2026-04-04

## R1: Current Backend Coverage Gaps

### Decision: Prioritize by composite impact score (missing lines × inverse coverage)

### Rationale
Files with both low coverage AND high line counts represent the greatest risk. A composite ranking (missing lines weighted by how low coverage is) ensures we target files that yield the maximum coverage uplift per test written.

### Findings

**Backend Overall**: 79% line coverage, 70% branch coverage (148 files tracked)

**Coverage Distribution**:
| Bracket | Files |
|---------|-------|
| 80-100% | 118 |
| 60-80% | 23 |
| 40-60% | 5 |
| 20-40% | 2 |

**Top 15 Files by Missing Lines (highest impact)**:

| File | Coverage | Lines | Missing | Branch Cov |
|------|----------|-------|---------|------------|
| `copilot_polling/pipeline.py` | 65.7% | 1007 | 310 | 57.8% |
| `agents/service.py` | 47.4% | 562 | 281 | 39.3% |
| `api/chat.py` | 59.6% | 741 | 275 | 47.5% |
| `agent_creator.py` | 39.4% | 397 | 240 | 38.8% |
| `api/projects.py` | 37.7% | 263 | 155 | 26.8% |
| `chores/service.py` | 51.3% | 344 | 154 | 39.7% |
| `copilot_polling/recovery.py` | 64.3% | 415 | 138 | 57.4% |
| `workflow_orchestrator/orchestrator.py` | 79.8% | 800 | 136 | 71.4% |
| `app_service.py` | 61.6% | 379 | 130 | 51.3% |
| `signal_bridge.py` | 60.9% | 343 | 127 | 56.6% |
| `api/pipelines.py` | 62.2% | 313 | 101 | 41.7% |
| `github_projects/board.py` | 63.0% | 269 | 91 | 56.6% |
| `main.py` | 68.2% | 324 | 89 | 50.0% |
| `api/board.py` | 64.5% | 247 | 85 | 62.1% |
| `copilot_polling/agent_output.py` | 73.0% | 339 | 80 | 66.3% |

**Coverage by Service Area**:

| Area | Files | Lines | Missing | Coverage |
|------|-------|-------|---------|----------|
| API Routes | 22 | 3608 | 943 | 73.9% |
| Agents | 3 | 729 | 286 | 60.8% |
| Chores | 6 | 537 | 178 | 66.9% |
| Copilot Polling | 12 | 3471 | 756 | 78.2% |
| GitHub Projects | 12 | 1976 | 369 | 81.3% |
| Models | 26 | 1532 | 10 | 99.3% |
| Middleware | 6 | 140 | 1 | 99.3% |
| Tools | 3 | 479 | 32 | 93.3% |
| Pipelines | 2 | 164 | 15 | 90.9% |
| Workflow Orchestrator | 5 | 1244 | 184 | 85.2% |
| Other Services | 37 | 5465 | 895 | 83.6% |

### Alternatives Considered
- **Alphabetical ordering**: Rejected — doesn't prioritize impact
- **Coverage % only**: Rejected — small files with 0% coverage are low impact
- **Random sampling**: Rejected — no strategic value

---

## R2: Current Frontend Coverage Gaps

### Decision: Raise vitest thresholds incrementally from 50/44/41/50 to 60/55/52/60

### Rationale
The current thresholds are low (41% functions). Raising them by ~10pp across the board is achievable without rewriting the test suite, and creates a ratchet that prevents regression. The largest gaps are in hooks and service modules.

### Findings

**Current Vitest Thresholds**: statements=50%, branches=44%, functions=41%, lines=50%

**Frontend Test Distribution** (186 unit test files):
- Hooks: 60+ test files (largest category)
- Components: Spread across 16 directories
- Services: 6 schema/API test files
- Utilities/lib: 17 test files

**E2E Tests**: 24 Playwright spec files covering auth, responsive layouts, integration, settings, agent creation, board navigation, MCP config, performance, error recovery.

### Alternatives Considered
- **Jump to 80% thresholds**: Rejected — too aggressive, would require massive test additions
- **Keep current thresholds**: Rejected — does not enforce improvement
- **Per-file thresholds**: Rejected — vitest v8 coverage doesn't support per-file thresholds natively

---

## R3: Modern Testing Best Practices for FastAPI + React

### Decision: Apply pytest-asyncio patterns for backend, Testing Library best practices for frontend

### Rationale
The codebase already uses modern tools (pytest-asyncio, vitest, Testing Library, Playwright). Best practices focus on test quality, not tool changes.

### Findings

**Backend Best Practices (Python/FastAPI)**:
1. **Async-first test patterns**: Use `pytest-asyncio` auto mode (already configured) with `httpx.AsyncClient` for API tests
2. **Fixture isolation**: Each test gets its own async event loop (function scope — already configured)
3. **Arrange-Act-Assert (AAA)**: Clear separation in each test function
4. **Branch coverage focus**: Use `branch = true` in coverage config (already enabled)
5. **Parametrized tests**: Use `@pytest.mark.parametrize` for error paths, edge cases
6. **Thin mocks**: Mock at service boundaries, not internal implementation details
7. **Integration test anti-patterns**: Avoid testing implementation details; test behaviors and contracts

**Frontend Best Practices (React/Vitest)**:
1. **Testing Library queries**: Prefer `getByRole`, `getByLabelText` over `getByTestId`
2. **User-centric testing**: Use `@testing-library/user-event` for realistic interaction simulation
3. **Hook testing**: Use `renderHook` from `@testing-library/react` with wrapper providers
4. **Avoid implementation details**: Don't test component internals, state shapes, or render counts
5. **Accessibility testing**: Use `jest-axe` (already installed) in component tests
6. **MSW for API mocking**: If not using it, consider for service layer tests (evaluate current approach first)

**E2E Best Practices (Playwright)**:
1. **Page Object Model**: Encapsulate page interactions in reusable classes
2. **Fixture-based setup**: Use Playwright fixtures for auth state, test data
3. **Visual regression**: Snapshot testing for UI components (already configured for Chromium baseline)
4. **Network interception**: Use `page.route()` for deterministic API responses
5. **Accessibility audits**: Use `@axe-core/playwright` (already installed) in e2e flows

### Alternatives Considered
- **Switch to pytest-bdd**: Rejected — adds complexity without benefit for this codebase
- **Switch to Cypress**: Rejected — Playwright is already well-integrated and more capable
- **Add Storybook tests**: Rejected — out of scope; mutation testing already covers component edge cases

---

## R4: Stale/Bad Test Identification Strategy

### Decision: Use a multi-signal approach to identify removable tests

### Rationale
Removing bad tests requires careful analysis to avoid losing genuine coverage. Multiple signals reduce false positives.

### Findings

**Signals for stale/bad tests**:
1. **No assertions**: Tests that only call code without verifying behavior (`assert` count = 0)
2. **Duplicated coverage**: Multiple tests exercising the exact same code path
3. **Testing removed features**: Tests importing deleted modules or using deprecated APIs
4. **Flaky tests**: Tests identified by the flaky-detection workflow (runs weekly)
5. **Over-mocked tests**: Tests where every dependency is mocked, testing nothing real
6. **Snapshot-only tests**: Tests that only compare snapshots without behavioral assertions

**Recommended Approach**:
- Run `grep -rn "def test_" tests/ | wc -l` to count total test functions
- Run coverage in "missing" mode to identify tests that contribute no unique coverage
- Review tests flagged by mutation testing (mutmut) as "survived" — these may be weak tests
- Check for tests with empty bodies or only `pass`/`skip` markers

### Alternatives Considered
- **Remove all tests below certain coverage contribution**: Rejected — too aggressive, some low-contribution tests serve as documentation
- **Automated deletion**: Rejected — requires human judgment for edge cases

---

## R5: Bug Discovery and Resolution Strategy

### Decision: Fix bugs inline during test-writing; track in plan.md Complexity Tracking section

### Rationale
Bugs found during testing should be fixed immediately alongside the test that discovered them. This prevents test debt and ensures the fix is verified by the new test.

### Findings

**Common bug categories discovered during coverage increase**:
1. **Unhandled edge cases**: Missing `None`/empty checks in service functions
2. **Error path defects**: Exception handlers that swallow errors or return wrong types
3. **Race conditions**: Async operations without proper locking (covered by concurrency tests)
4. **Configuration drift**: Code paths that assume environment variables exist without defaults
5. **Dead code**: Unreachable branches that should be removed

**Resolution Protocol**:
- Bug discovered → add failing test → fix the bug → verify test passes
- Document in commit message: `fix: {description} (discovered during coverage improvement)`
- If bug is complex (>30 min fix), create a separate issue and skip the test with a TODO comment
