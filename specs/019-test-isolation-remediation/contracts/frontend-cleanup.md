# Contract: Frontend Test Cleanup Patterns

**Feature**: 019-test-isolation-remediation | **Date**: 2026-04-07

## Purpose

Defines the contracts for frontend test cleanup patterns to prevent state leaks between tests.

## Contract 1: Fake Timer Cleanup

### Applies To

Any test file that calls `vi.useFakeTimers()`.

### Rule

Every `vi.useFakeTimers()` in a `beforeEach` MUST have a matching `vi.useRealTimers()` in an `afterEach`:

```typescript
beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});
```

### Rationale

`vi.useFakeTimers()` replaces global `setTimeout`, `setInterval`, `Date.now()`, and other timer APIs. Without restoration, subsequent tests inherit fake timers, causing unpredictable failures.

### Affected Files

| File | Status Before | Fix |
|------|--------------|-----|
| `useFileUpload.test.ts` | ❌ Missing `afterEach` | Add `afterEach(() => { vi.useRealTimers(); })` |

## Contract 2: UUID Counter Reset

### Applies To

`src/test/setup.ts` — the global test setup file.

### Rule

The `_counter` variable used by the `crypto.randomUUID` stub MUST be reset to `0` before each test:

```typescript
let _counter = 0;

beforeEach(() => {
  _counter = 0;
});
```

### Rationale

Without reset, the counter increments globally across the test suite. This makes UUID values ordering-dependent — a test might get UUID `...000000000001` or `...000000000042` depending on which tests ran before it.

### Invariants

1. Each test starts with `_counter = 0`
2. The first `crypto.randomUUID()` call in any test returns `00000000-0000-4000-8000-000000000001`
3. UUID values are deterministic within a single test regardless of execution order

## Contract 3: Spy Restoration

### Applies To

Any test file that uses `vi.spyOn()`.

### Rule

Every test file that uses `vi.spyOn()` MUST include `afterEach(() => { vi.restoreAllMocks(); })`:

```typescript
afterEach(() => {
  vi.restoreAllMocks();
});
```

### Rationale

`vi.spyOn()` wraps a real function with a mock. Without `vi.restoreAllMocks()`:
- The original function remains wrapped in subsequent tests
- `vi.clearAllMocks()` only clears call history, not the spy wrapper
- `vi.resetAllMocks()` resets implementation but doesn't restore the original

### Affected Files

| File | Current Cleanup | Fix |
|------|----------------|-----|
| `TopBar.test.tsx` | `vi.clearAllMocks()` in beforeEach | Add `afterEach(() => { vi.restoreAllMocks(); })` |
| `AuthGate.test.tsx` | `vi.clearAllMocks()` in beforeEach | Add `afterEach(() => { vi.restoreAllMocks(); })` |
| `useAuth.test.tsx` | `vi.resetAllMocks()` in afterEach | Change to `vi.restoreAllMocks()` |
| `useAdaptivePolling.test.ts` | ✅ Already has `vi.restoreAllMocks()` | No change needed |

### Reference Implementation

`useAdaptivePolling.test.ts` already follows this contract correctly:

```typescript
beforeEach(() => {
  vi.spyOn(document, 'addEventListener');
  vi.spyOn(document, 'removeEventListener');
});

afterEach(() => {
  vi.restoreAllMocks();
});
```
