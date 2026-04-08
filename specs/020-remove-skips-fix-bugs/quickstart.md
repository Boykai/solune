# Quickstart: Uplift Solune Testing — Remove Skips, Fix Bugs, Apply Modern Best Practices

**Feature**: 020-remove-skips-fix-bugs | **Date**: 2026-04-08

## Prerequisites

- Python ≥3.12 with `uv` package manager
- Node.js ≥20 with npm
- Git repository cloned (not shallow — need full history for CI workflow tests)

## Step-by-Step Implementation Guide

### Step 1: Audit (Already Complete)

The audit is documented in `plan.md` → "Skip Marker Inventory" section and `data-model.md`.

**Verify**:
```bash
# Backend skip markers
cd solune/backend
grep -rn "pytest.mark.skip\|pytest.skip\|pytest.mark.xfail\|unittest.skip\|skipIf" tests/

# Frontend skip markers
cd solune/frontend
grep -rn "test\.skip\|it\.skip\|describe\.skip\|\.todo\|xit\|xdescribe" src/ e2e/
```

### Step 2: Fix Backend Pytest Infrastructure

**Current state**: Already well-configured. Verify only.

```bash
cd solune/backend

# Verify pytest config
grep -A 10 '\[tool.pytest.ini_options\]' pyproject.toml

# Run tests to check for asyncio warnings
uv run python -m pytest tests/unit/ -v --tb=short 2>&1 | grep -i "warning\|asyncio"

# Expected: zero asyncio deprecation warnings
```

**Add default marker exclusion** (if not present):
```toml
# pyproject.toml [tool.pytest.ini_options]
addopts = "-m 'not integration and not performance'"
```

### Step 3: Fix Frontend Vitest Infrastructure

**Current state**: Already well-configured. Verify and enhance.

```bash
cd solune/frontend

# Verify Vitest config
cat vitest.config.ts

# Run tests to check for warnings
npm run test 2>&1 | head -50

# Verify jest-axe availability
grep -r "jest-axe\|toHaveNoViolations" src/test/setup.ts
```

**If jest-axe not configured**, add to `src/test/setup.ts`:
```typescript
import { toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);
```

### Step 4: Resolve Backend Skip Markers

#### 4a: Fix `test_import_rules.py` (3 skips → 0)

Fix path resolution to use `src/` prefix:

```bash
cd solune/backend
# Verify the correct paths exist
ls -d src/services/ src/api/ src/models/
```

Edit `tests/architecture/test_import_rules.py` to resolve paths from `src/` instead of project root.

#### 4b: Fix `test_run_mutmut_shard.py` (1 skip → 0)

Add fallback logic when CI workflow file is missing:

```python
# Instead of skipif, provide a default shard count
CI_WORKFLOW = Path("../../.github/workflows/ci.yml")
if not CI_WORKFLOW.exists():
    CI_WORKFLOW = Path(__file__).parents[4] / ".github/workflows/ci.yml"
```

#### 4c: Convert `test_custom_agent_assignment.py` (1 skip → 0)

Replace `pytest.skip()` with `@pytest.mark.integration`:

```python
@pytest.mark.integration
async def test_custom_agent_assignment():
    # Remove the skip guard
    ...
```

#### 4d: Convert `test_board_load_time.py` (5 skips → 0)

Replace all `pytest.skip()` calls with `@pytest.mark.performance` on the test class:

```python
@pytest.mark.performance
class TestBoardLoadPerformance:
    # Remove all _skip_if_missing_prereqs and _ensure_backend_running skip calls
    ...
```

**Verify**:
```bash
# Default run excludes integration and performance
uv run python -m pytest tests/ -v --tb=short

# Explicit integration run
uv run python -m pytest tests/ -m integration -v --tb=short

# Verify zero skip markers
grep -rn "pytest.mark.skip\|pytest.skip\|pytest.mark.xfail" tests/
# Expected: zero results
```

### Step 5: Resolve Frontend E2E Skip Markers

#### 5a: Update `integration.spec.ts`

Move prerequisite checks to `beforeAll` or use Playwright project configuration:

```typescript
// Option A: Move to beforeAll with proper annotation
test.describe('backend integration', () => {
  test.beforeAll(async ({ request }) => {
    // Skip entire describe if backend unavailable
  });
});
```

#### 5b: Update `project-load-performance.spec.ts`

Similar approach — consolidate prerequisite checks.

**Verify**:
```bash
cd solune/frontend
# Verify unit tests pass
npm run test

# Verify e2e tests (if backend available)
npx playwright test --project=chromium
```

### Step 6: Add Net-New Coverage

#### Backend

```bash
cd solune/backend

# Create test files for new coverage
touch tests/unit/test_resolve_repository.py
touch tests/unit/test_pipeline_state_store.py
touch tests/unit/test_webhook_hmac.py
touch tests/unit/test_presets.py
touch tests/unit/test_encryption.py

# Run with coverage to see baseline
uv run python -m pytest tests/ --cov=src --cov-report=term-missing -q
```

#### Frontend

```bash
cd solune/frontend

# Create test files for new coverage
touch src/services/api.test.ts
touch src/hooks/useAuth.a11y.test.tsx

# Run with coverage to see baseline
npm run test:coverage
```

### Step 7: Full Validation

```bash
# Backend validation
cd solune/backend
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run pyright src/
uv run pyright -p pyrightconfig.tests.json
uv run python -m pytest tests/ --cov=src --cov-fail-under=75 -q

# Frontend validation
cd solune/frontend
npm run lint
npm run type-check
npm run test -- --pool=forks
npm run build

# E2E validation (if infrastructure available)
npx playwright test --project=chromium
```

### Verification Checklist

- [ ] Backend: zero `pytest.mark.skip`, `pytest.skip()`, `pytest.mark.xfail` in `tests/`
- [ ] Frontend: zero `test.skip`, `it.skip`, `describe.skip`, `.todo` in `src/`
- [ ] Frontend E2E: conditional skips use Playwright's native annotation pattern
- [ ] Backend: `pytest tests/` passes with zero asyncio warnings
- [ ] Frontend: `npm run test` passes with zero configuration warnings
- [ ] Backend: coverage ≥75%
- [ ] Frontend: coverage ≥70% statements (post-uplift target)
- [ ] All linters pass (ruff, eslint, pyright, tsc)
- [ ] CHANGELOG.md updated with Fixed entries for any production bugs
