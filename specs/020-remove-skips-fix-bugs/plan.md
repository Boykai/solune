# Implementation Plan: Uplift Solune Testing — Remove Skips, Fix Bugs, Apply Modern Best Practices

**Branch**: `copilot/remove-skips-fix-bugs` | **Date**: 2026-04-08 | **Spec**: [#1135](https://github.com/Boykai/solune/issues/1135)
**Input**: Parent issue #1135 — Uplift Solune Testing: Remove Skips, Fix Bugs, Apply Modern Best Practices

## Summary

The Solune codebase has 10 backend skip markers (across 4 files) and 6 frontend e2e skip conditions (across 2 files). This plan systematically audits every skip, resolves the root-cause bugs or infrastructure gaps, upgrades test-runner configuration to modern best practices, adds meaningful net-new coverage for critical untested paths, and validates a fully green CI build with zero skip markers remaining.

The work proceeds in seven layered phases: (1) audit, (2) backend pytest infrastructure, (3) frontend Vitest infrastructure, (4) resolve backend skips, (5) resolve frontend skips, (6) add net-new coverage, (7) full validation.

## Technical Context

**Language/Version**: Python ≥3.12 (backend), TypeScript 6.0 (frontend)
**Primary Dependencies**: FastAPI, pytest, pytest-asyncio, httpx, Vitest, React 19.2.0, Playwright
**Storage**: SQLite via aiosqlite (backend), localStorage (frontend)
**Testing**: pytest + pytest-asyncio (backend), Vitest + Testing Library + happy-dom (frontend), Playwright (e2e)
**Target Platform**: Linux server (backend), Modern browsers (frontend)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: N/A — test infrastructure change, no runtime impact
**Constraints**: Zero breaking changes to production code; all existing tests must continue passing; coverage thresholds maintained (≥75% backend, ≥50% frontend); coverage uplift ≥10pp from baseline
**Scale/Scope**: 10 backend skip markers across 4 files; 6 frontend e2e skip conditions across 2 files; 0 frontend unit test skips; targets services/copilot_polling/, services/workflow_orchestrator/, api/webhooks.py, services/signal_bridge.py, src/utils.py, services/pipeline_state_store.py, services/tools/presets.py, services/encryption.py

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Parent issue #1135 provides detailed 7-step implementation specification with acceptance criteria per step |
| II. Template-Driven Workflow | ✅ PASS | Using canonical plan template; all artifacts in `specs/020-remove-skips-fix-bugs/` |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan phase produces plan.md, research.md, data-model.md, quickstart.md, contracts/; handoff to tasks phase |
| IV. Test Optionality | ✅ PASS | This feature IS about test infrastructure — testing is the core deliverable |
| V. Simplicity and DRY | ✅ PASS | Leverages existing test helpers in `tests/helpers/`; uses existing fixtures; no new abstractions needed |

**Gate Result**: ✅ ALL PASS — proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/020-remove-skips-fix-bugs/
├── plan.md              # This file
├── research.md          # Phase 0: skip audit, asyncio patterns, Vitest best practices
├── data-model.md        # Phase 1: skip inventory, fixture/mock structures
├── quickstart.md        # Phase 1: step-by-step developer guide
├── contracts/
│   ├── backend-test-patterns.md   # Contract for modern pytest patterns
│   └── frontend-test-patterns.md  # Contract for modern Vitest patterns
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── pyproject.toml                              # Step 2: verify/update pytest config
│   ├── tests/
│   │   ├── conftest.py                             # Step 2: verify infrastructure fixtures
│   │   ├── helpers/
│   │   │   ├── assertions.py                       # Existing: reusable assertion helpers
│   │   │   └── factories.py                        # Existing: test data factories
│   │   ├── unit/
│   │   │   └── test_run_mutmut_shard.py            # Step 4: resolve skipif (line 138-142)
│   │   ├── integration/
│   │   │   └── test_custom_agent_assignment.py     # Step 4: resolve pytest.skip (line 45)
│   │   ├── architecture/
│   │   │   └── test_import_rules.py                # Step 4: resolve 3x pytest.skip (lines 54, 93, 116)
│   │   └── performance/
│   │       └── test_board_load_time.py             # Step 4: resolve 5x pytest.skip (lines 40-71)
│   └── src/
│       ├── utils.py                                # Step 6: add tests for resolve_repository()
│       ├── api/
│       │   └── webhooks.py                         # Step 6: add HMAC signature validation tests
│       └── services/
│           ├── copilot_polling/                     # Step 4/6: key test target area
│           ├── workflow_orchestrator/               # Step 4/6: key test target area
│           ├── signal_bridge.py                     # Step 4/6: key test target area
│           ├── pipeline_state_store.py              # Step 6: restart-survivability tests
│           ├── encryption.py                        # Step 6: Fernet roundtrip tests
│           └── tools/presets.py                     # Step 6: catalog enumeration tests
│
└── frontend/
    ├── vite.config.ts                               # Step 3: verify Vitest config
    ├── src/
    │   ├── test/setup.ts                            # Step 3: verify test setup
    │   ├── hooks/
    │   │   └── useAuth.test.tsx                     # Step 5: ensure parallel reliability
    │   └── services/
    │       └── api.ts                               # Step 6: add authenticated request tests
    └── e2e/
        ├── integration.spec.ts                      # Step 5: resolve 2x test.skip (lines 62, 73)
        └── project-load-performance.spec.ts         # Step 5: resolve 4x test.skip (lines 47-114)
```

**Structure Decision**: Web application (Option 2). This feature modifies test infrastructure across `solune/backend/tests/` and `solune/frontend/src/` and `solune/frontend/e2e/` — no new directories.

## Skip Marker Inventory

### Backend (10 markers, 4 files)

| # | File | Line | Marker | Reason | Test |
|---|------|------|--------|--------|------|
| 1 | `tests/unit/test_run_mutmut_shard.py` | 138-142 | `@pytest.mark.skipif()` | CI workflow not found (shallow clone) | `TestCIAlignment.test_workflow_matrix_matches_shards` |
| 2 | `tests/integration/test_custom_agent_assignment.py` | 45 | `pytest.skip()` | GITHUB_TOKEN required for live testing | `test_custom_agent_assignment` |
| 3 | `tests/architecture/test_import_rules.py` | 54 | `pytest.skip()` | services/ directory not found | `TestServicesBoundary.test_services_do_not_import_api` |
| 4 | `tests/architecture/test_import_rules.py` | 93 | `pytest.skip()` | api/ directory not found | `TestApiBoundary.test_api_does_not_import_store_modules` |
| 5 | `tests/architecture/test_import_rules.py` | 116 | `pytest.skip()` | models/ directory not found | `TestModelsBoundary.test_models_do_not_import_services` |
| 6 | `tests/performance/test_board_load_time.py` | 40 | `pytest.skip()` | PERF_GITHUB_TOKEN not set | `_skip_if_missing_prereqs` |
| 7 | `tests/performance/test_board_load_time.py` | 42 | `pytest.skip()` | PERF_PROJECT_ID not set | `_skip_if_missing_prereqs` |
| 8 | `tests/performance/test_board_load_time.py` | 49 | `pytest.skip()` | Backend unhealthy | `_ensure_backend_running` |
| 9 | `tests/performance/test_board_load_time.py` | 51 | `pytest.skip()` | Backend not reachable | `_ensure_backend_running` |
| 10 | `tests/performance/test_board_load_time.py` | 68-71 | `pytest.skip()` | Auth failed | `_create_session` |

### Frontend (6 markers, 2 e2e files)

| # | File | Line | Marker | Reason | Test |
|---|------|------|--------|--------|------|
| 1 | `e2e/project-load-performance.spec.ts` | 47 | `test.skip(true, '...')` | Auth state not found | beforeEach |
| 2 | `e2e/project-load-performance.spec.ts` | 50 | `test.skip(true, '...')` | E2E_PROJECT_ID not set | beforeEach |
| 3 | `e2e/project-load-performance.spec.ts` | 65 | `test.skip(true, '...')` | Frontend not reachable | board load test |
| 4 | `e2e/project-load-performance.spec.ts` | 114 | `test.skip(true, '...')` | Frontend not reachable | project selection test |
| 5 | `e2e/integration.spec.ts` | 62 | `test.skip()` | Backend not running (CI) | should call health endpoint |
| 6 | `e2e/integration.spec.ts` | 73 | `test.skip()` | Backend not running (CI) | should handle 401 |

### Frontend Unit Tests (0 markers)

No skip markers found in `solune/frontend/src/`. All unit tests including `useAuth.test.tsx` run fully.

## Execution Phases (from Issue #1135)

### Step 1 — Audit All Skipped Tests ✅ (completed in this plan)

The inventory above documents all 16 skip markers across backend and frontend. The `useAuth.test.tsx` file has no skip markers — all 18 test cases run. No `.todo()`, `xit()`, or `xdescribe()` patterns found in frontend.

**Acceptance**: Inventory documented in this plan and in `.specify/memory/test-skip-inventory.md`.

### Step 2 — Fix Backend Pytest Infrastructure

**Current State**: Already well-configured.

| Setting | Current Value | Target | Action |
|---------|--------------|--------|--------|
| `asyncio_mode` | `"auto"` | `"auto"` | ✅ Already set |
| `asyncio_default_fixture_loop_scope` | `"function"` | `"function"` | ✅ Already set |
| `coverage.report.fail_under` | `75` | `70` (issue says 70) | ⚠️ Already stricter at 75 — keep as-is |
| `filterwarnings` | Not set | Verify | Check for unintentional suppressions |
| Deprecated loop fixtures | Check conftest | Remove | Audit `tests/helpers/` conftest |

**Key Observation**: The existing `_clear_test_caches` fixture (conftest.py lines 245-388) already clears 30+ module-level caches. This was addressed in spec 019 (test-isolation-remediation). The infrastructure is solid.

**Acceptance**: pytest tests/ runs cleanly with zero asyncio warnings.

### Step 3 — Fix Frontend Vitest Infrastructure

**Current State**: Already well-configured.

| Setting | Current | Target | Action |
|---------|---------|--------|--------|
| `environment` | `happy-dom` | `happy-dom` | ✅ Already set |
| `globals` | `true` | `true` | ✅ Already set |
| `coverage.provider` | `v8` | `v8` | ✅ Already set |
| `coverage.thresholds.statements` | `50%` | `70%` (issue target) | 📝 Raise after adding coverage |
| `setupFiles` | `./src/test/setup.ts` | Present | ✅ Already set |
| `jest-axe` | Check | Available globally | Verify in setup.ts |

**Acceptance**: npm run test runs without configuration warnings and jest-axe matchers available globally.

### Step 4 — Resolve Backend Skipped Tests

Each skip marker needs a targeted resolution strategy:

| # | File | Strategy | Production Fix? |
|---|------|----------|-----------------|
| 1 | `test_run_mutmut_shard.py` | Replace `@pytest.mark.skipif` with a fallback that reads CI workflow from known path or defaults gracefully | No — test infra only |
| 2 | `test_custom_agent_assignment.py` | Convert conditional `pytest.skip()` to a proper `@pytest.mark.integration` marker that is excluded in unit-test runs but included in integration CI | No — test categorization |
| 3-5 | `test_import_rules.py` | Fix path resolution to use `src/` prefix or `Path(__file__).parent` relative navigation instead of failing on directory structure | No — test path bug |
| 6-10 | `test_board_load_time.py` | Convert conditional skips to `@pytest.mark.performance` marker (already defined) + ensure performance tests only run when explicitly selected | No — test categorization |

**Key Decision**: Conditional skips for environment-dependent tests (integration, performance) should use pytest markers + `addopts = -m "not integration and not performance"` in default config so they're excluded by default but runnable on demand. This removes the skip markers entirely.

**Acceptance**: Zero `@pytest.mark.skip`, `@pytest.mark.xfail`, or `pytest.skip()` calls in backend tests.

### Step 5 — Resolve Frontend Skipped Tests

| # | File | Strategy | Production Fix? |
|---|------|----------|-----------------|
| 1-4 | `project-load-performance.spec.ts` | Replace `test.skip(true, ...)` with Playwright `test.fixme()` annotations or conditional `test.describe.configure({ mode: 'serial' })` with proper prerequisite checks that report as "skipped" via Playwright's native mechanism | No — e2e infra |
| 5-6 | `integration.spec.ts` | Replace `test.skip()` inside tests with `test.describe.configure` or move to a separate project in `playwright.config.ts` that only runs when backend is available | No — e2e infra |

**Alternative Strategy**: Convert all conditional e2e skips to proper Playwright annotations:

- Use `test.skip(condition, reason)` (already using this pattern) — this is actually Playwright's recommended approach for conditional skipping
- The issue asks to remove ALL skip markers, so evaluate if these truly need removal or if conditional skips are acceptable for e2e tests requiring live services

**Resolution**: For e2e tests that require live backend/auth services, conditional skips are the correct pattern (Playwright docs recommend `test.skip()` for prerequisite checks). Document this as an accepted exception. For `integration.spec.ts`, move backend-dependent tests behind a proper Playwright project configuration.

**Frontend Unit Tests**: No action needed — zero skips found. The `useAuth.test.tsx` runs all 18 tests successfully with proper mocking.

**Acceptance**: All e2e conditional skips use Playwright's native annotation pattern; zero `.skip`/`xit`/`xdescribe` in unit tests (already met).

### Step 6 — Add Meaningful Coverage for Critical Untested Paths

**Backend Net-New Tests**:

| Target | File | Test Focus | Priority |
|--------|------|-----------|----------|
| `resolve_repository()` | `src/utils.py` | 4-step fallback chain: cache hit, project items, REST fallback, workflow config, default repo | HIGH |
| `pipeline_state_store.py` | `src/services/pipeline_state_store.py` | Restart survivability: write state, "restart" (reset in-memory), read back from SQLite | HIGH |
| `webhooks.py` HMAC | `src/api/webhooks.py` | HMAC signature validation: valid sig, invalid sig, missing header, replay attack | HIGH |
| `tools/presets.py` | `src/services/tools/presets.py` | Catalog enumeration: all presets returned, structure validated | MEDIUM |
| Fernet encryption | `src/services/encryption.py` | Roundtrip: encrypt → decrypt, invalid key, corrupted ciphertext | MEDIUM |

**Frontend Net-New Tests**:

| Target | File | Test Focus | Priority |
|--------|------|-----------|----------|
| `api.ts` authenticated requests | `src/services/api.ts` | Request helper with retry: success, 401 retry, network error | HIGH |
| Zero-coverage hooks | Various hooks | Basic render + behavior assertions | MEDIUM |
| Accessibility | Page-level components | At least one `axe` assertion per page component | MEDIUM |

**Acceptance**: Coverage up ≥10pp from baseline; no new `.skip`.

### Step 7 — Validate Full Test Suite and CI Green

**Backend Validation Matrix**:

```bash
ruff check src/ tests/
ruff format --check src/ tests/
pyright src/
pyright -p pyrightconfig.tests.json
pytest tests/ --cov=src --cov-fail-under=75 -q
```

**Frontend Validation Matrix**:

```bash
npm run lint
npm run type-check
npm run test -- --pool=forks
npm run build
```

**E2E Validation**:

```bash
npx playwright test --project=chromium
```

**Acceptance**: All suites exit 0; CI green; zero unconditional skip markers remaining.

## Design Decisions

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| Convert environment-dependent skips to pytest markers | Standard pytest pattern; excluded by default, runnable on demand; eliminates `pytest.skip()` calls | Leave as conditional skips: issue mandates zero skips |
| Keep e2e conditional skips as Playwright annotations | Playwright's `test.skip(condition, reason)` is the framework's native prerequisite-check pattern | Remove all: would make tests fail when services unavailable |
| Fix `test_import_rules.py` path resolution | Root cause is incorrect directory path assumption | Skip: doesn't fix the bug |
| Use `httpx.AsyncClient` with `ASGITransport` for endpoint tests | Modern async testing pattern; avoids lifespan issues with TestClient | `TestClient` with `with` blocks: deprecated pattern for async apps |
| Add `@pytest.mark.performance` to perf tests | Already defined marker; proper test categorization | Conditional skip: mandated to remove |
| Keep backend coverage at 75% (not lower to 70%) | Existing threshold is stricter; lowering would be regression | Lower to 70%: issue says 70, but existing is better |
| Add `jest-axe` a11y assertions in setup | Global availability via setupFiles; one assertion per page component minimum | Per-file imports: violates DRY |

## Constitution Re-Check (Post Phase 1 Design)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Issue #1135 serves as detailed specification with 7 steps and acceptance criteria |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates in `specs/020-remove-skips-fix-bugs/` |
| III. Agent-Orchestrated Execution | ✅ PASS | Single-responsibility plan phase output; handoff to tasks |
| IV. Test Optionality | ✅ PASS | Testing IS the feature — explicitly mandated |
| V. Simplicity and DRY | ✅ PASS | Uses existing fixtures/helpers; pytest markers are simplest categorization; no new abstractions |

**Gate Result**: ✅ ALL PASS — proceed to tasks phase

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Conditional e2e skips retained | E2e tests require live services; unconditional run would fail | Removing all skips: tests would error on missing backend/auth |

> This is an accepted exception documented in Step 5 — e2e conditional skips are Playwright's recommended pattern for prerequisite checks.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
