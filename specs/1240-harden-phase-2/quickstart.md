# Quickstart: Harden Phase 2

**Feature**: Test Coverage Improvement
**Date**: 2026-04-10

## Prerequisites

- Python 3.13 with pip
- Node.js 22+ with npm
- Git

## Setup

```bash
# Clone and navigate
git clone https://github.com/Boykai/solune.git
cd solune

# Backend setup
cd solune/backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Frontend setup
cd ../frontend
npm install
```

## Running Tests

### Backend

```bash
cd solune/backend

# Run all tests with coverage report
pytest --cov=src --cov-report=term-missing

# Run only property tests
pytest tests/property/ -v

# Run tests for a specific module
pytest tests/unit/test_middleware_request_id.py -v

# Check coverage against current threshold (75%)
pytest --cov=src --cov-fail-under=75
```

### Frontend

```bash
cd solune/frontend

# Run all unit tests with coverage
npx vitest run --coverage

# Run tests for a specific component
npx vitest run src/components/chores/__tests__/ChoreCard.test.tsx

# Run property tests only
npx vitest run --testPathPattern="property"

# Watch mode for development
npx vitest --watch
```

### E2E Tests

```bash
cd solune/frontend

# Install Playwright browsers (first time only)
npx playwright install

# Run all E2E tests
npx playwright test

# Run a specific E2E spec
npx playwright test e2e/auth.spec.ts

# Run with UI mode for debugging
npx playwright test --ui
```

## Workstream-Specific Guides

### WS 2.1 — Backend Coverage (75% → 80%)

**Find low-coverage files**:

```bash
cd solune/backend
pytest --cov=src --cov-report=term-missing | sort -t% -k4 -n | head -30
```

**Add tests**: Follow existing patterns in `tests/unit/`. Example structure:

```python
# tests/unit/test_middleware_request_id.py
import pytest
from src.middleware.request_id import RequestIdMiddleware

class TestRequestIdMiddleware:
    async def test_adds_request_id_header(self):
        # Test the happy path
        ...

    async def test_preserves_existing_request_id(self):
        # Test edge case
        ...
```

**Bump threshold**: After all tests pass, update `pyproject.toml`:

```toml
[tool.coverage.report]
fail_under = 80
```

### WS 2.2 — Frontend Coverage (statements 50→60%)

**Find untested components**:

```bash
cd solune/frontend
npx vitest run --coverage 2>&1 | grep "0.00" | head -30
```

**Add tests**: Follow existing patterns. Import from `@/test/test-utils`:

```tsx
// src/components/chores/__tests__/ChoreCard.test.tsx
import { render, screen } from '@/test/test-utils';
import { ChoreCard } from '../ChoreCard';

describe('ChoreCard', () => {
  it('renders chore title', () => {
    render(<ChoreCard chore={mockChore} />);
    expect(screen.getByText('Daily standup')).toBeInTheDocument();
  });
});
```

**Bump thresholds**: After all tests pass, update `vitest.config.ts`:

```typescript
thresholds: {
  statements: 60,
  branches: 52,
  functions: 50,
  lines: 60,
},
```

### WS 2.3 — Property-Based Testing

**Backend (Hypothesis)**:

```python
# tests/property/test_api_model_roundtrips.py
from hypothesis import given
from hypothesis import strategies as st
from src.models.some_model import SomeModel

@given(st.builds(SomeModel))
def test_model_roundtrip(model):
    """Model → dict → Model produces identical object."""
    assert SomeModel(**model.model_dump()) == model
```

**Frontend (fast-check)**:

```typescript
// src/lib/apiTypes.property.test.ts
import { test } from '@fast-check/vitest';
import fc from 'fast-check';

test.prop([fc.record({ id: fc.string(), name: fc.string() })])(
  'API type round-trips through JSON',
  ([data]) => {
    expect(JSON.parse(JSON.stringify(data))).toEqual(data);
  },
);
```

### WS 2.4 — Axe-Core E2E Accessibility

**Add a11y test to any E2E spec**:

```typescript
import AxeBuilder from '@axe-core/playwright';

test('should pass accessibility audit', async ({ page }) => {
  await page.goto('/target-route');
  // Wait for content to stabilize
  await page.waitForLoadState('networkidle');

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  expect(results.violations).toEqual([]);
});
```

## CI Integration

All tests run in GitHub Actions CI:

| Job | Command | Threshold |
|---|---|---|
| Backend | `pytest --cov=src --cov-fail-under=80` | 80% (target) |
| Frontend | `npx vitest run --coverage` | 60/52/50/60 (target) |
| Frontend E2E | `npx playwright test` | All specs pass |
| Backend Advanced | `pytest tests/property/ tests/fuzz/` | All pass (continue-on-error) |

## Validation Checklist

Before submitting a PR for any workstream:

- [ ] All existing tests still pass (`pytest` / `npx vitest run`)
- [ ] New tests pass individually and in full suite
- [ ] Coverage meets or exceeds the target threshold
- [ ] No TypeScript compilation errors (`npx tsc --noEmit`)
- [ ] No Python type errors (`pyright`)
- [ ] E2E tests pass with mocked API (`npx playwright test`)
