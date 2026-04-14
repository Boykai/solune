# Data Model: Dependabot Updates

**Feature**: Dependabot Updates | **Date**: 2026-04-14 | **Status**: Complete

## Entity: DependencyUpdate

Represents one open Dependabot PR under evaluation.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `pr_number` | `integer` | Required, unique | GitHub pull request number |
| `package_name` | `string` | Required | Package updated by Dependabot |
| `ecosystem` | `enum` | `npm`, `pip` | Package manager ecosystem |
| `dependency_type` | `enum` | `runtime`, `dev` | Runtime or development-only dependency |
| `current_version` | `string` | Required | Current version/constraint from the live default branch at execution time |
| `target_version` | `string` | Required | Version/constraint proposed by Dependabot |
| `bump_type` | `enum` | `patch`, `minor`, `major` | Semver risk tier |
| `manifest_path` | `string` | Required | Absolute manifest path to edit |
| `lock_path` | `string` | Required | Absolute lock file path to regenerate |
| `status` | `enum` | `pending`, `applied`, `skipped` | Outcome after evaluation |
| `failure_summary` | `string \| null` | Optional | One-line reason when an update is skipped |
| `notes` | `string \| null` | Optional | Extra risk notes (for example beta → stable or runtime critical) |

### State Transitions

```text
pending -> applied   (all required validation commands pass)
pending -> skipped   (validation fails or the update requires code/config migration)
```

---

## Entity: VerificationRun

Represents the command set executed to accept or reject a single dependency update.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `update_pr_number` | `integer` | Required | Foreign key to `DependencyUpdate.pr_number` |
| `commands` | `string[]` | Required, non-empty | Ordered validation commands that were run |
| `started_from_ref` | `string` | Required | Default-branch ref used as the baseline (for example `origin/main`) |
| `lock_regenerated` | `boolean` | Required | Whether the correct lock generator was executed |
| `result` | `enum` | `pass`, `fail` | Aggregate verification result |
| `failure_summary` | `string \| null` | Optional | First actionable failure line for skipped updates |

---

## Entity: BatchUpdatePlan

Represents the final combined PR payload after all candidate updates are evaluated.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `branch_name` | `string` | Required | Working branch for the combined update set |
| `pr_title` | `string` | Fixed | `chore(deps): apply Dependabot batch update` |
| `applied_updates` | `DependencyUpdate[]` | Required | Updates that passed validation |
| `skipped_updates` | `DependencyUpdate[]` | Required | Updates rejected with a recorded reason |
| `final_verification_commands` | `string[]` | Required | Full backend + frontend validation matrix rerun before PR creation |

---

## Inventory: Current Open Updates

### Patch Tier (4)

| PR | Package | Ecosystem | Dependency Type | Current → Target | Manifest Path | Lock Path |
|----|---------|-----------|-----------------|------------------|---------------|-----------|
| #1732 | `pytest` | `pip` | dev | `9.0.2` → `9.0.3`* | `/home/runner/work/solune/solune/solune/backend/pyproject.toml` | `/home/runner/work/solune/solune/solune/backend/uv.lock` |
| #1777 | `happy-dom` | `npm` | dev | `20.8.9` → `20.9.0` | `/home/runner/work/solune/solune/solune/frontend/package.json` | `/home/runner/work/solune/solune/solune/frontend/package-lock.json` |
| #1776 | `typescript-eslint` | `npm` | dev | `8.58.1` → `8.58.2` | `/home/runner/work/solune/solune/solune/frontend/package.json` | `/home/runner/work/solune/solune/solune/frontend/package-lock.json` |
| #1775 | `react-router-dom` | `npm` | runtime | `7.14.0` → `7.14.1` | `/home/runner/work/solune/solune/solune/frontend/package.json` | `/home/runner/work/solune/solune/solune/frontend/package-lock.json` |

\* Re-validate against `origin/main` before editing because the checked-out manifest currently shows `pytest>=9.0.0`.

### Minor Tier (9)

| PR | Package | Ecosystem | Dependency Type | Current → Target | Manifest Path | Lock Path |
|----|---------|-----------|-----------------|------------------|---------------|-----------|
| #1688 | `pytest-cov` | `pip` | dev | `>=7.0.0` → `>=7.1.0` | `/home/runner/work/solune/solune/solune/backend/pyproject.toml` | `/home/runner/work/solune/solune/solune/backend/uv.lock` |
| #1695 | `freezegun` | `pip` | dev | `>=1.4.0` → `>=1.5.5` | `/home/runner/work/solune/solune/solune/backend/pyproject.toml` | `/home/runner/work/solune/solune/solune/backend/uv.lock` |
| #1694 | `pip-audit` | `pip` | dev | `>=2.9.0` → `>=2.10.0` | `/home/runner/work/solune/solune/solune/backend/pyproject.toml` | `/home/runner/work/solune/solune/solune/backend/uv.lock` |
| #1697 | `mutmut` | `pip` | dev | `>=3.2.0` → `>=3.5.0` | `/home/runner/work/solune/solune/solune/backend/pyproject.toml` | `/home/runner/work/solune/solune/solune/backend/uv.lock` |
| #1690 | `bandit` | `pip` | dev | `>=1.8.0` → `>=1.9.4` | `/home/runner/work/solune/solune/solune/backend/pyproject.toml` | `/home/runner/work/solune/solune/solune/backend/uv.lock` |
| #1692 | `pynacl` | `pip` | runtime | `>=1.5.0,<2` → `>=1.6.2,<2` | `/home/runner/work/solune/solune/solune/backend/pyproject.toml` | `/home/runner/work/solune/solune/solune/backend/uv.lock` |
| #1696 | `uvicorn` | `pip` | runtime | `>=0.42.0,<1` → `>=0.44.0,<1` | `/home/runner/work/solune/solune/solune/backend/pyproject.toml` | `/home/runner/work/solune/solune/solune/backend/uv.lock` |
| #1698 | `agent-framework-core` | `pip` | runtime | `>=1.0.0b1` → `>=1.0.1` | `/home/runner/work/solune/solune/solune/backend/pyproject.toml` | `/home/runner/work/solune/solune/solune/backend/uv.lock` |
| #1699 | `@tanstack/react-query` | `npm` | runtime | `5.97.0` → `5.99.0` | `/home/runner/work/solune/solune/solune/frontend/package.json` | `/home/runner/work/solune/solune/solune/frontend/package-lock.json` |

### Major Tier (1)

| PR | Package | Ecosystem | Dependency Type | Current → Target | Manifest Path | Lock Path |
|----|---------|-----------|-----------------|------------------|---------------|-----------|
| #1693 | `pytest-randomly` | `pip` | dev | `>=3.16.0` → `>=4.0.1` | `/home/runner/work/solune/solune/solune/backend/pyproject.toml` | `/home/runner/work/solune/solune/solune/backend/uv.lock` |
