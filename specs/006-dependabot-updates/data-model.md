# Data Model: Dependabot Updates

**Feature**: Dependabot Updates | **Date**: 2026-04-14 | **Status**: Complete

## Entity: DependencyUpdate

Represents a single Dependabot PR and its processing outcome.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `pr_number` | `integer` | Required, unique | GitHub PR number |
| `package` | `string` | Required | Package name (e.g., `happy-dom`, `pytest`) |
| `ecosystem` | `enum` | `npm` or `pip` | Package ecosystem |
| `current_version` | `string` | Required | Version constraint before update |
| `target_version` | `string` | Required | Version constraint after update |
| `bump_type` | `enum` | `patch`, `minor`, `major` | Semantic version bump category |
| `dep_type` | `enum` | `runtime`, `dev` | Whether this is a runtime or dev dependency |
| `manifest_file` | `string` | Required | Path to manifest (e.g., `solune/frontend/package.json`) |
| `lock_file` | `string` | Required | Path to lock file (e.g., `solune/frontend/package-lock.json`) |
| `status` | `enum` | `pending`, `applied`, `skipped` | Processing outcome |
| `failure_reason` | `string` | Nullable | One-line failure summary if skipped |

### State Transitions

```text
pending → applied    (build + test pass)
pending → skipped    (build or test fails)
```

---

## Entity: UpdateBatch

Represents the collection of all updates processed in one execution.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `branch` | `string` | Required | Target branch for batch PR |
| `title` | `string` | Fixed: `chore(deps): apply Dependabot batch update` | PR title |
| `updates` | `DependencyUpdate[]` | Required | All updates processed |
| `applied_count` | `integer` | Computed | Number of successfully applied updates |
| `skipped_count` | `integer` | Computed | Number of skipped updates |

---

## Inventory: Current Updates (14 total)

### Tier 1 — Patch Bumps (4 updates)

| PR | Package | Ecosystem | Current → Target | Type |
|----|---------|-----------|-----------------|------|
| #1732 | pytest | pip | >=9.0.0 → >=9.0.3 | dev |
| #1777 | happy-dom | npm | 20.8.9 → 20.9.0 | dev |
| #1776 | typescript-eslint | npm | 8.58.1 → 8.58.2 | dev |
| #1775 | react-router-dom | npm | 7.14.0 → 7.14.1 | runtime |

### Tier 2 — Minor Bumps (9 updates)

| PR | Package | Ecosystem | Current → Target | Type |
|----|---------|-----------|-----------------|------|
| #1688 | pytest-cov | pip | >=7.0.0 → >=7.1.0 | dev |
| #1695 | freezegun | pip | >=1.4.0 → >=1.5.5 | dev |
| #1694 | pip-audit | pip | >=2.9.0 → >=2.10.0 | dev |
| #1697 | mutmut | pip | >=3.2.0 → >=3.5.0 | dev |
| #1690 | bandit | pip | >=1.8.0 → >=1.9.4 | dev |
| #1692 | pynacl | pip | >=1.5.0 → >=1.6.2 | runtime |
| #1696 | uvicorn | pip | >=0.42.0 → >=0.44.0 | runtime |
| #1698 | agent-framework-core | pip | >=1.0.0b1 → >=1.0.1 | runtime |
| #1699 | @tanstack/react-query | npm | 5.97.0 → 5.99.0 | runtime |

### Tier 3 — Major Bumps (1 update)

| PR | Package | Ecosystem | Current → Target | Type |
|----|---------|-----------|-----------------|------|
| #1693 | pytest-randomly | pip | >=3.16.0 → >=4.0.1 | dev |
