# Contract: Frontend Test Patterns — Modern Vitest Best Practices

**Feature**: 020-remove-skips-fix-bugs | **Date**: 2026-04-08

## Overview

Defines the standard patterns for frontend tests after the skip-removal uplift. All new and modified tests must follow these patterns.

## Pattern 1: E2E Prerequisite Checks (Playwright)

### Before (test.skip in body)

```typescript
// ❌ Anti-pattern: skip inside test body
test('should call health endpoint', async ({ request }) => {
  test.skip(); // Backend not running (CI) — skip gracefully
  const response = await request.get('/api/health');
  expect(response.ok()).toBeTruthy();
});
```

### After (project-level configuration)

```typescript
// playwright.config.ts
// ✅ Correct: separate project for backend-dependent tests
export default defineConfig({
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      testMatch: /.*(?<!integration|performance)\.spec\.ts$/,
    },
    {
      name: 'integration',
      use: { ...devices['Desktop Chrome'] },
      testMatch: /integration\.spec\.ts$/,
      // Only runs when explicitly selected: npx playwright test --project=integration
    },
    {
      name: 'performance',
      use: { ...devices['Desktop Chrome'] },
      testMatch: /performance\.spec\.ts$/,
      // Only runs when explicitly selected: npx playwright test --project=performance
    },
  ],
});
```

### Alternative: Conditional describe with annotation

```typescript
// ✅ Acceptable: Playwright's native prerequisite pattern
test.describe('backend integration', () => {
  test.beforeEach(async ({ request }) => {
    try {
      const health = await request.get('http://localhost:8000/api/health');
      test.skip(!health.ok(), 'Backend not running');
    } catch {
      test.skip(true, 'Backend not reachable');
    }
  });

  test('should call health endpoint', async ({ request }) => {
    // No skip here — handled in beforeEach
    const response = await request.get('/api/health');
    expect(response.ok()).toBeTruthy();
  });
});
```

## Pattern 2: Unit Test User Interactions

### Before (fireEvent)

```typescript
// ❌ Anti-pattern: fireEvent doesn't simulate real user behavior
fireEvent.click(screen.getByRole('button', { name: /submit/i }));
```

### After (userEvent)

```typescript
// ✅ Correct: userEvent simulates real user behavior
const user = userEvent.setup();
await user.click(screen.getByRole('button', { name: /submit/i }));
```

## Pattern 3: Screen Queries

### Before (container queries)

```typescript
// ❌ Anti-pattern: container.querySelector is brittle
const { container } = render(<MyComponent />);
const button = container.querySelector('.submit-btn');
```

### After (screen queries)

```typescript
// ✅ Correct: screen queries are accessible and resilient
render(<MyComponent />);
const button = screen.getByRole('button', { name: /submit/i });
```

## Pattern 4: Module-Level Mocking

### Standard mock pattern

```typescript
// ✅ Correct: vi.mock at module scope with factory
vi.mock('@/services/api', () => ({
  fetchData: vi.fn(),
  postData: vi.fn(),
}));

// ✅ Correct: typed mock access
import { fetchData } from '@/services/api';
const mockFetchData = vi.mocked(fetchData);

beforeEach(() => {
  vi.clearAllMocks();
});
```

## Pattern 5: Test Cleanup

### Required cleanup patterns

```typescript
// ✅ Correct: always clean up in afterEach
afterEach(() => {
  vi.restoreAllMocks();
});

// ✅ Correct: restore real timers if fake timers used
afterEach(() => {
  vi.useRealTimers();
});

// ✅ Correct: clear storage
beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});
```

## Pattern 6: Hook Testing with Providers

### Standard hook test

```typescript
// ✅ Correct: wrap in necessary providers
import { renderHook, waitFor } from '@testing-library/react';

function createWrapper() {
  return ({ children }: { children: React.ReactNode }) => (
    <AuthProvider>{children}</AuthProvider>
  );
}

it('should return authenticated user', async () => {
  mockFetchUser.mockResolvedValue({ id: '1', name: 'Test' });

  const { result } = renderHook(() => useAuth(), {
    wrapper: createWrapper(),
  });

  await waitFor(() => {
    expect(result.current.user).toEqual({ id: '1', name: 'Test' });
  });
});
```

## Pattern 7: Accessibility Testing with jest-axe

### Standard a11y assertion

```typescript
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

it('should have no accessibility violations', async () => {
  const { container } = render(<PageComponent />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

### Setup file configuration (if not already present)

```typescript
// src/test/setup.ts
import 'jest-axe/extend-expect';
// OR
import { toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);
```

## Pattern 8: Parallel-Safe Tests

### useAuth.test.tsx reliability pattern

```typescript
// ✅ Correct: isolated state per test
beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});
```

### Verification command

```bash
# Test with forks pool (process isolation)
npm run test -- --pool=forks

# Test with threads pool (thread isolation)
npm run test -- --pool=threads

# Both should pass for parallel-safe tests
```
