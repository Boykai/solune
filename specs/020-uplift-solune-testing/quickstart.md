# Quickstart: Uplift Solune Testing — Remove Skips, Fix Bugs, Apply Modern Best Practices

**Feature**: 020-uplift-solune-testing | **Date**: 2026-04-08

> Step-by-step developer guide for implementing the testing uplift. Each step is independently verifiable — run the validation command after completing each step.

## Prerequisites

```bash
# Backend setup
cd solune/backend
PATH=$HOME/.local/bin:$PATH uv sync --extra dev

# Frontend setup
cd solune/frontend
npm ci
```

## Validation Commands

```bash
# Backend: full test suite
cd solune/backend && PATH=$HOME/.local/bin:$PATH uv run pytest tests/ -x -q

# Backend: with coverage enforcement
cd solune/backend && PATH=$HOME/.local/bin:$PATH uv run pytest tests/ --cov=src --cov-fail-under=75 -q --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency

# Backend: lint + type check
cd solune/backend && PATH=$HOME/.local/bin:$PATH uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run pyright src/

# Frontend: unit tests
cd solune/frontend && npx vitest run --reporter=verbose

# Frontend: lint + type check + build
cd solune/frontend && npm run lint && npm run type-check && npm run build

# Frontend: E2E (requires running app)
cd solune/frontend && npx playwright test --project=chromium
```

---

## Step 1: Audit All Skip Markers

### 1.1: Run Backend Skip Audit

```bash
cd solune/backend
grep -rn "pytest.mark.skip\|pytest.mark.xfail\|pytest.skip\|skipIf\|unittest.skip" tests/
```

**Expected Result**: 10 matches — all conditional infrastructure guards. Zero unconditional skips.

### 1.2: Run Frontend Skip Audit

```bash
cd solune/frontend
grep -rn "test\.skip\|it\.skip\|describe\.skip\|\.todo\|xit\b\|xdescribe" src/ e2e/
```

**Expected Result**: 6 matches in E2E files. Zero matches in `src/` unit tests.

### 1.3: Document Inventory

Create `specs/020-uplift-solune-testing/data-model.md` with the complete inventory (already done in this plan).

**Verify**: All markers classified as infrastructure guards or marked for removal.

---

## Step 2: Fix Backend pytest Infrastructure

### 2.1: Verify Existing Configuration

```bash
cd solune/backend
grep -A5 "tool.pytest.ini_options" pyproject.toml
```

**Expected**: `asyncio_mode = "auto"` and `asyncio_default_fixture_loop_scope = "function"` already set.

### 2.2: Verify Existing Coverage Threshold

The backend already enforces `fail_under = 75` in `pyproject.toml` under `[tool.coverage.report]`, which exceeds issue #1149's 70% minimum. No changes needed.

```bash
cd solune/backend
grep "fail_under" pyproject.toml
```

**Expected**: `fail_under = 75` already set under `[tool.coverage.report]`.

### 2.3: Verify filterwarnings

```bash
cd solune/backend
grep -A10 "filterwarnings" pyproject.toml
```

Confirm only intentional deprecation suppressions are active.

**Verify**: `uv run pytest tests/ -x -q` — all tests pass, zero asyncio warnings.

---

## Step 3: Fix Frontend Vitest Infrastructure

### 3.1: Verify Existing Configuration

```bash
cd solune/frontend
cat vitest.config.ts
```

**Expected**: `globals: true`, `environment: 'happy-dom'`, `coverage.provider: 'v8'`, `setupFiles` pointing to setup.ts.

### 3.2: Verify jest-dom and jest-axe Availability

Check `src/test/setup.ts` for jest-dom import. For jest-axe, it's a per-test import:

```typescript
// In individual test files:
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);
```

### 3.3: Verify test.exclude Correctness

Ensure `test.exclude` in vitest.config.ts does not accidentally exclude unit test files.

**Verify**: `npm run test` — zero configuration warnings.

---

## Step 4: Resolve Backend Skipped Tests

### 4.1: Confirm No Unconditional Skips

From the audit (Step 1), all 10 backend skips are conditional infrastructure guards. No action needed.

### 4.2: Verify Modern Test Patterns

For any tests being refactored or added:

```python
# Use AsyncMock for async mocks
from unittest.mock import AsyncMock
mock_service = AsyncMock()

# Use httpx.AsyncClient for endpoint tests
from httpx import ASGITransport, AsyncClient
transport = ASGITransport(app=app)
async with AsyncClient(transport=transport, base_url="http://test") as client:
    response = await client.get("/api/health")
```

**Verify**: `uv run pytest tests/ -x -q` — all pass.

---

## Step 5: Resolve Frontend Skipped Tests

### 5.1: Confirm No Unconditional Skips

From the audit (Step 1), all 6 frontend skips are conditional E2E infrastructure guards. No action needed.

### 5.2: Verify useAuth.test.tsx Stability

```bash
cd solune/frontend
npx vitest run src/hooks/useAuth.test.tsx
npx vitest run --pool=forks src/hooks/useAuth.test.tsx
```

**Verify**: All 18 tests pass in both pool modes.

---

## Step 6: Add Net-New Coverage

### 6.1: Backend — resolve_repository()

Create `tests/unit/test_resolve_repository.py`:

- Test cache hit returns cached value
- Test GraphQL fallback when cache misses
- Test REST fallback when GraphQL fails
- Test error handling for all fallbacks

### 6.2: Backend — Webhook HMAC Validation

Create or extend `tests/unit/test_webhooks.py`:

- Test valid HMAC signature passes
- Test invalid HMAC signature returns 401
- Test missing X-Hub-Signature-256 header
- Test replay protection via `_processed_delivery_ids`

### 6.3: Backend — tools/presets.py

Create `tests/unit/test_presets.py`:

- Test preset catalog enumeration
- Test individual preset field validation

### 6.4: Backend — Fernet Encryption

Create or extend `tests/unit/test_encryption.py`:

- Test encrypt → decrypt roundtrip
- Test invalid key handling

### 6.5: Frontend — api.ts Coverage

Extend `src/services/api.test.ts`:

- Test authenticated request header
- Test retry on 401
- Test retry on network error

### 6.6: Frontend — axe Accessibility

Add to existing page component tests:

```typescript
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);

it('has no a11y violations', async () => {
  const { container } = render(<PageComponent />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

**Verify**: `uv run pytest tests/ --cov=src --cov-fail-under=75 -q` and `npm run test:coverage`.

---

## Step 7: Validate Full Suite and CI

### 7.1: Backend Full Validation

```bash
cd solune/backend
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run pyright src/
uv run pytest tests/ --cov=src --cov-fail-under=75 -q --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency
```

### 7.2: Frontend Full Validation

```bash
cd solune/frontend
npm run lint
npm run type-check
npm run test -- --pool=forks
npm run build
```

### 7.3: E2E Validation

```bash
cd solune/frontend
npx playwright test --project=chromium
```

### 7.4: Update CHANGELOG.md

Add `Fixed` entries under `[Unreleased]` for any production bugs discovered and fixed during the uplift.

### 7.5: Push and Verify CI

Push changes and confirm all CI jobs exit 0.
