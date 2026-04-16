# Data Model: Remove Lint/Test Ignores & Fix Discovered Bugs

**Feature**: `003-remove-lint-ignores` | **Date**: 2026-04-16

## Overview

This feature does not introduce new persisted data models, API schemas, or database entities. It is a cross-cutting code quality cleanup that modifies existing source files and configuration. The "entities" below describe the conceptual objects tracked during the cleanup process.

## Entity: Suppression

A directive in source code or configuration that tells a static analysis tool to skip a specific check.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier: `{file_path}:{line_number}` |
| `file_path` | string | Absolute path to the file containing the suppression |
| `line_number` | integer | Line number of the suppression directive |
| `category` | enum | One of: `noqa`, `type-ignore`, `pragma-no-cover`, `pytest-skip`, `eslint-disable`, `ts-expect-error`, `bicep-disable`, `config-level` |
| `rule_code` | string | The specific rule being suppressed (e.g., `B008`, `react-hooks/exhaustive-deps`) |
| `scope` | enum | `inline` (single line/block), `file-wide`, or `global` (config-level) |
| `action` | enum | `remove` (fix the underlying issue), `retain` (keep with justification), `defer` (create follow-up issue) |
| `reason` | string \| null | Justification for retention, required when `action = retain` |
| `bug_discovered` | boolean | Whether removing the suppression revealed a latent bug |

### Validation Rules

- If `action = retain`, then `reason` MUST NOT be null
- If `bug_discovered = true`, the fix MUST be included in the same change set (or a follow-up issue created)
- After cleanup, all remaining suppressions with `action = retain` MUST have a `reason:` comment in the source code

### State Transitions

```text
IDENTIFIED → EVALUATED → { REMOVED | RETAINED (with reason) | DEFERRED (with issue link) }
```

## Entity: Baseline

A recorded snapshot of all check results taken before changes begin.

| Field | Type | Description |
|-------|------|-------------|
| `component` | enum | `backend`, `frontend`, `e2e`, `infra` |
| `check_type` | string | Name of the check (e.g., `ruff check`, `npm run lint`, `az bicep build`) |
| `result` | enum | `pass`, `fail` |
| `suppression_count` | integer | Number of suppressions at baseline |
| `coverage_pct` | float \| null | Code coverage percentage at baseline |
| `mutation_score` | float \| null | Mutation testing score at baseline |
| `captured_at` | datetime | Timestamp of baseline capture |

## Entity: CI Guard Rule

A pattern-matching rule used by the CI suppression guard.

| Field | Type | Description |
|-------|------|-------------|
| `language` | enum | `python`, `typescript`, `bicep` |
| `pattern` | regex | Regular expression matching the suppression syntax |
| `reason_pattern` | regex | Regular expression that validates the presence of a `reason:` or `--` justification |
| `exemptions` | string[] | File patterns exempt from the rule (e.g., generated files) |

### Known Suppression Patterns

| Language | Pattern | Example |
|----------|---------|---------|
| Python | `# noqa(?::\s*\w+)?` | `# noqa: B008` |
| Python | `# type:\s*ignore` | `# type: ignore[misc]` |
| Python | `# pragma:\s*no cover` | `# pragma: no cover` |
| Python | `@pytest\.mark\.skip` | `@pytest.mark.skipif(...)` |
| TypeScript | `eslint-disable` | `// eslint-disable-next-line react-hooks/exhaustive-deps` |
| TypeScript | `@ts-expect-error` | `// @ts-expect-error - reason` |
| TypeScript | `@ts-ignore` | `// @ts-ignore` |
| Bicep | `#disable-next-line` | `#disable-next-line outputs-should-not-contain-secrets` |

## Relationships

```text
Baseline 1:N Suppression (baseline contains many suppressions)
CI Guard Rule 1:N Suppression (each rule matches suppressions of its pattern)
Suppression N:1 File (many suppressions can exist in one file)
```

## No Schema Changes

This feature does not modify any:

- Database schemas or migrations
- API request/response models
- Frontend state management interfaces
- Infrastructure resource definitions

All changes are to source code, configuration files, and CI pipeline scripts.
