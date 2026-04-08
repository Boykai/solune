# Contract: Frontend Test Infrastructure & Coverage

**Feature**: 020-uplift-solune-testing | **Date**: 2026-04-08

## Purpose

Defines the contract for frontend test infrastructure, E2E skip handling, and test modernization patterns.

## Contract 1: Vitest Configuration

### Required State

`vitest.config.ts` MUST maintain these settings:

```typescript
test: {
  globals: true,                    // Test functions available without imports
  environment: 'happy-dom',         // Fast DOM implementation
  setupFiles: ['./src/test/setup.ts'], // Global test setup
  include: ['src/**/*.{test,spec}.{ts,tsx}'],
  coverage: {
    provider: 'v8',
    thresholds: {
      statements: 50,               // Minimum enforced
      branches: 44,
      functions: 41,
      lines: 50,
    },
  },
}
```

### Behavior

- `npm run test` MUST run with zero configuration warnings
- Coverage thresholds MUST be enforced on every `test:coverage` run
- `test.exclude` MUST NOT accidentally exclude unit test files

## Contract 2: Modern Frontend Test Patterns

### Applies To

All new frontend tests and any refactored existing tests.

### Rules

1. **User Interaction**: Use `userEvent.setup()` + `await user.click()` instead of `fireEvent`
2. **DOM Queries**: Use `screen.getByRole()`, `screen.getByText()` instead of `container.querySelector()`
3. **Mocking**: Use `vi.mock()` at module scope and `vi.mocked()` for typed access
4. **Cleanup**: Use `vi.restoreAllMocks()` in `afterEach` when using `vi.spyOn()`
5. **Timers**: Pair every `vi.useFakeTimers()` with `vi.useRealTimers()` in `afterEach`

### Example Pattern

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('@/services/api');

describe('MyComponent', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('handles user interaction', async () => {
    const user = userEvent.setup();
    render(<MyComponent />);

    await user.click(screen.getByRole('button', { name: 'Submit' }));
    expect(screen.getByText('Success')).toBeInTheDocument();
  });
});
```

## Contract 3: E2E Conditional Skip Pattern

### Applies To

All Playwright E2E tests that require infrastructure.

### Acceptable Pattern

Runtime `test.skip()` inside the test body or `beforeEach` with a clear message:

```typescript
test('integration test', async ({ page }) => {
  try {
    const response = await page.request.get('http://localhost:8000/health');
    // ... test logic
  } catch {
    test.skip(true, 'Backend not running');
  }
});
```

### Unacceptable Patterns

```typescript
// WRONG: Unconditional skip
test.skip('broken test', async ({ page }) => { ... });

// WRONG: Using describe.skip to hide broken tests
describe.skip('Feature X', () => { ... });

// WRONG: Using .todo without a plan to implement
test.todo('should handle edge case');
```

## Contract 4: useAuth.test.tsx Stability

### Applies To

`src/hooks/useAuth.test.tsx`

### Requirements

1. Tests MUST pass with `--pool=forks` (process isolation)
2. Tests MUST pass with `--pool=threads` (thread isolation)
3. `beforeEach` MUST include `localStorage.clear()` and `vi.clearAllMocks()`
4. `afterEach` MUST include `vi.restoreAllMocks()`
5. Renders MUST use AuthProvider test wrapper if hook requires context

### Verification

```bash
npm run test -- --pool=forks src/hooks/useAuth.test.tsx
npm run test -- --pool=threads src/hooks/useAuth.test.tsx
```

## Contract 5: Net-New Frontend Test Requirements

### Applies To

All new tests added in Step 6.

### Rules

1. Assert **behavior**, not implementation details
2. Cover **happy path** plus at least **one error/edge case**
3. Use existing helpers from `src/test/` directory
4. Follow existing test file naming: `{Component}.test.tsx` or `{hook}.test.ts`
5. Place test files adjacent to the source file

### Coverage Targets

| Module | Minimum New Tests | Required Scenarios |
|--------|------------------|--------------------|
| `services/api.ts` | 3 | Auth header, retry on 401, network error |
| Page components (axe) | 1 per page | `expect(await axe(container)).toHaveNoViolations()` |
| Zero-coverage hooks | 2 per hook | Happy path, error case |
