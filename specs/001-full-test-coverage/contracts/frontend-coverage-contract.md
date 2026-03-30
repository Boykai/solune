# Frontend Coverage Contract

**Feature**: `001-full-test-coverage` | **Date**: 2026-03-30

## Purpose

This contract defines the verification criteria for frontend test coverage at each phase boundary. All metrics are measured using Vitest with v8 coverage provider.

## Verification Commands

```bash
# Run tests with coverage (CI-equivalent)
cd solune/frontend
npm run test:coverage

# Accessibility validation
npm run test:a11y

# Mutation testing
npm run test:mutate

# E2E tests
npm run test:e2e

# Type check
npm run type-check

# Lint
npm run lint
```

## Phase Contracts

### Phase 1: Green Baseline

| Metric | Requirement | Verification |
|--------|-------------|--------------|
| Test suite status | All tests pass | `npm run test` exit code 0 |
| Build status | Build succeeds | `npm run build` exit code 0 |
| Lint status | No lint errors | `npm run lint` exit code 0 |
| Type check status | No type errors | `npm run type-check` exit code 0 |

**Acceptance command**: `npm run lint && npm run type-check && npm run test && npm run build` — all exit code 0.

### Phase 4: Component Coverage Sprint (50% → ~80%)

| Metric | Minimum | Verification |
|--------|---------|--------------|
| Statement coverage | ≥80% | `npm run test:coverage` reports ≥80% |
| Branch coverage | ≥80% | `npm run test:coverage` reports ≥80% |
| Function coverage | ≥80% | `npm run test:coverage` reports ≥80% |
| Line coverage | ≥80% | `npm run test:coverage` reports ≥80% |
| A11y validation | All pass | `npm run test:a11y` exit code 0 |
| New test files | ~100 created | All untested components have test files |
| Agent components | 100% per component | 10 component tests created |
| Board components | 100% per component | ~20 component tests created |
| Settings components | 100% per component | ~12 component tests created |
| Pipeline components | 100% per component | ~15 component tests created |
| Missing hooks | 100% per hook | 4 hook tests created |
| Missing pages | 100% per page | ActivityPage.test.tsx created |

**Acceptance command**: `npm run test:coverage` — all metrics ≥80%.

**Test pattern contract** (every component test MUST include):

```typescript
import { renderWithProviders } from '@/test/test-utils';
import { axe } from 'jest-axe';

describe('ComponentName', () => {
  it('renders without crashing', () => {
    const { container } = renderWithProviders(<ComponentName />);
    expect(container).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = renderWithProviders(<ComponentName />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  // ... additional behavior tests
});
```

### Phase 5: Branch & Edge Case Coverage (80% → 100%)

| Metric | Requirement | Verification |
|--------|-------------|--------------|
| Statement coverage | 100% | `npm run test:coverage` reports 100% |
| Branch coverage | 100% | `npm run test:coverage` reports 100% |
| Function coverage | 100% | `npm run test:coverage` reports 100% |
| Line coverage | 100% | `npm run test:coverage` reports 100% |
| Error states | All components | Every component tested in error state |
| Loading states | All components | Every component tested in loading state |
| Empty states | All components | Every component tested in empty state |
| Negative paths | All API interactions | 401, 403, 404, 500 error responses tested |
| App routing | 100% | Route matching, lazy loading, error boundaries tested |
| E2E tests | All pass | `npm run test:e2e` exit code 0 |
| Mutation score (hooks+lib) | ≥80% killed | `npm run test:mutate` reports ≥80% |

**Acceptance command**: `npm run test:coverage` — all metrics at 100%.

### Phase 6: Final Frontend Threshold

| Metric | Requirement | Verification |
|--------|-------------|--------------|
| All coverage metrics | 100% | `npm run test:coverage` at 100% thresholds |
| vitest.config.ts thresholds | 100/100/100/100 | Config file verified |
| Stryker scope | Includes components + pages | `stryker.config.mjs` verified |
| Mutation score (expanded) | ≥80% killed | `npm run test:mutate` |

**Acceptance command**: `npm run test:coverage` — thresholds enforced at 100%.

## Exclusion Policy

Files excluded from coverage measurement:

| Pattern | Reason |
|---------|--------|
| `src/test/**` | Test infrastructure — not production code |
| `src/main.tsx` | Application entry point — trivial bootstrap |
| `src/vite-env.d.ts` | Type declaration file — no runtime code |

Additional exclusions require team review and documented justification in the PR description.
