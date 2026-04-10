# Data Model: Harden Phase 2

**Feature**: Test Coverage Improvement
**Date**: 2026-04-10
**Input**: research.md, plan.md

## Overview

This feature is a test-only workstream with no runtime data model changes. The entities below
describe the test coverage tracking model used to measure progress and enforce thresholds.

## Entities

### CoverageThreshold

Represents a coverage threshold enforced by CI. Stored in configuration files, not a database.

| Field | Type | Source | Validation |
|---|---|---|---|
| metric | enum(statements, branches, functions, lines, fail_under) | Config | Required |
| current_value | float | Config file | 0–100 |
| target_value | float | Plan | 0–100, >= current_value |
| config_file | string | File system | Must exist |
| ecosystem | enum(backend, frontend) | Config | Required |

**Instances**:

| Ecosystem | Metric | Current | Target | Config File |
|---|---|---|---|---|
| backend | fail_under | 75 | 80 | solune/backend/pyproject.toml |
| frontend | statements | 50 | 60 | solune/frontend/vitest.config.ts |
| frontend | branches | 44 | 52 | solune/frontend/vitest.config.ts |
| frontend | functions | 41 | 50 | solune/frontend/vitest.config.ts |
| frontend | lines | 50 | 60 | solune/frontend/vitest.config.ts |

### UntestableFrontendComponent

Represents a frontend component identified as lacking test coverage.

| Field | Type | Validation |
|---|---|---|
| name | string | PascalCase or kebab-case |
| category | enum(chores, agents, tools, settings, ui, pipeline) | Required |
| file_path | string | Must exist under solune/frontend/src/components/ |
| test_status | enum(untested, partial, covered) | Required |
| priority | enum(P1, P2, P3) | Based on category ranking |

**Priority mapping**:
- P1: pipeline (16), chores (13) — highest gap count or user-critical
- P2: ui (13), agents (11) — shared primitives or core feature
- P3: tools (9), settings (7) — lower user traffic

### PropertyTestFile

Represents a property-based test file (existing or planned).

| Field | Type | Validation |
|---|---|---|
| name | string | Must follow `test_*.py` or `*.property.test.ts` pattern |
| ecosystem | enum(backend, frontend) | Required |
| framework | enum(hypothesis, fast-check) | Must match ecosystem |
| strategy_type | enum(round-trip, invariant, stateful, validation, idempotency) | Required |
| status | enum(existing, planned) | Required |

### E2EAccessibilitySpec

Represents an E2E spec file's accessibility testing status.

| Field | Type | Validation |
|---|---|---|
| spec_file | string | Must end in `.spec.ts` |
| has_axe_builder | boolean | Required |
| target_routes | string[] | At least one route |
| fixture_type | enum(unauthenticated, authenticated) | Required |
| wcag_tags | string[] | Default: wcag2a, wcag2aa, wcag21a, wcag21aa |

## Relationships

```text
CoverageThreshold ──< UntestableFrontendComponent
  (thresholds drive which components need tests)

PropertyTestFile ──< CoverageThreshold
  (property tests contribute to coverage metrics)

E2EAccessibilitySpec ──< No direct relationship to coverage
  (a11y is a quality gate, not a coverage metric)
```

## State Transitions

### Component Test Status

```text
untested → partial → covered
```

- **untested → partial**: Initial test file created with basic render/snapshot tests
- **partial → covered**: Full test suite with interactions, edge cases, and branch coverage

### Threshold Lifecycle

```text
current → tests_written → threshold_bumped → ci_enforced
```

- **current**: Existing threshold values in config files
- **tests_written**: All new test files merged and passing
- **threshold_bumped**: Config files updated with target values
- **ci_enforced**: CI validates new thresholds on every PR
