# Research: Dependabot Updates

**Feature**: Dependabot Updates | **Date**: 2026-04-14 | **Status**: Complete

## R1: Open Dependabot PR Inventory

**Decision**: Use the repository's current open Dependabot PR list as the canonical update backlog: 14 PRs total, split into 10 backend (`pip`/`uv`) updates and 4 frontend (`npm`) updates.

**Rationale**: GitHub PR search for `author:app/dependabot is:open repo:Boykai/solune` returned these open PRs:

### Frontend (`npm`) — 4 PRs

| PR | Package | Current | Target | Bump | Dependency Type |
|----|---------|---------|--------|------|-----------------|
| #1777 | `happy-dom` | `20.8.9` | `20.9.0` | Patch | dev |
| #1776 | `typescript-eslint` | `8.58.1` | `8.58.2` | Patch | dev |
| #1775 | `react-router-dom` | `7.14.0` | `7.14.1` | Patch | runtime |
| #1699 | `@tanstack/react-query` | `5.97.0` | `5.99.0` | Minor | runtime |

### Backend (`pip` / `uv`) — 10 PRs

| PR | Package | Current | Target | Bump | Dependency Type |
|----|---------|---------|--------|------|-----------------|
| #1732 | `pytest` | `9.0.2` | `9.0.3` | Patch | dev |
| #1688 | `pytest-cov` | `>=7.0.0` | `>=7.1.0` | Minor | dev |
| #1695 | `freezegun` | `>=1.4.0` | `>=1.5.5` | Minor | dev |
| #1694 | `pip-audit` | `>=2.9.0` | `>=2.10.0` | Minor | dev |
| #1697 | `mutmut` | `>=3.2.0` | `>=3.5.0` | Minor | dev |
| #1690 | `bandit` | `>=1.8.0` | `>=1.9.4` | Minor | dev |
| #1692 | `pynacl` | `>=1.5.0,<2` | `>=1.6.2,<2` | Minor | runtime |
| #1696 | `uvicorn` | `>=0.42.0,<1` | `>=0.44.0,<1` | Minor | runtime |
| #1698 | `agent-framework-core` | `>=1.0.0b1` | `>=1.0.1` | Minor (beta → stable) | runtime |
| #1693 | `pytest-randomly` | `>=3.16.0` | `>=4.0.1` | Major | dev |

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| Derive the list only from local manifests | Misses which updates are currently open and safe to evaluate |
| Batch packages by hand without PR metadata | Loses the authoritative package/version mapping supplied by Dependabot |

---

## R2: Branch Drift and Overlap Analysis

**Decision**: Treat Dependabot PR metadata as the discovery source, but re-validate the current manifest state from `origin/main` immediately before each update is applied.

**Rationale**: The local checkout still shows `pytest>=9.0.0` in `/home/runner/work/solune/solune/solune/backend/pyproject.toml`, while PR #1732 advertises `9.0.2 → 9.0.3`. That mismatch means at least one Dependabot PR title may be based on a newer default-branch snapshot than the current checkout. The plan therefore requires a fresh default-branch sync before every edit.

No overlapping package constraints were found in the open PR set:

- Every PR targets a distinct package.
- Backend and frontend updates live in separate manifests.
- No PR pair attempts to modify the same package or lock file entry directly.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| Assume the checked-out branch matches default branch exactly | Already disproven by the `pytest` version drift |
| Merge multiple updates per ecosystem before validation | Makes failures harder to attribute and raises rollback cost |

---

## R3: Verification Command Set

**Decision**: Reuse the repository's existing frontend and backend validation commands as the acceptance gate for every update.

**Rationale**: `/home/runner/work/solune/solune/solune/backend/pyproject.toml` and `/home/runner/work/solune/solune/solune/frontend/package.json` define the repo-native toolchain. Those commands align with stored repository validation practice and cover the relevant failure modes for dependency upgrades.

### Backend verification

```bash
cd /home/runner/work/solune/solune/solune/backend
uv lock
uv sync --extra dev
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run pyright src/
uv run pytest tests/unit/ -q
```

### Frontend verification

```bash
cd /home/runner/work/solune/solune/solune/frontend
npm install
npm run lint
npm run type-check
npm run test
npm run build
```

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| Run only unit tests | Misses type, lint, and build regressions introduced by dependency changes |
| Trust CI without local verification | Violates the issue's explicit apply-and-verify workflow |

---

## R4: Lock File Regeneration Strategy

**Decision**: Regenerate lock files with ecosystem-native tools after every accepted manifest change.

**Rationale**: The issue explicitly forbids manual lock-file edits. The correct regeneration commands are:

- Backend: `uv lock` followed by `uv sync --extra dev`
- Frontend: `npm install`

These commands update `/home/runner/work/solune/solune/solune/backend/uv.lock` and `/home/runner/work/solune/solune/solune/frontend/package-lock.json` in a reproducible way.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| Manual lock-file editing | Explicitly prohibited and prone to invalid resolutions |
| Delay lock regeneration until all manifest edits are complete | Creates multi-package resolution noise and makes failures harder to isolate |

---

## R5: High-Risk Update Handling

**Decision**: Apply extra scrutiny to runtime dependency bumps and to the lone major update (`pytest-randomly`).

**Rationale**:

- `pynacl` affects crypto behavior.
- `uvicorn` affects backend serving/runtime behavior.
- `agent-framework-core` moves from beta to stable and could change typing/import contracts.
- `pytest-randomly` is a major version bump and may require plugin/config migration.

Each of these should still follow the same one-update-at-a-time workflow, but any failure that implies application-code changes becomes a skip reason instead of a migration task for this batch.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| Treat all updates as equally safe | Ignores the issue's required patch/minor/major prioritization |
| Preemptively skip every major or runtime bump | Overly conservative; the issue asks to apply every safe update |

---

## R6: Batch PR Reporting Strategy

**Decision**: Keep a running applied/skipped inventory throughout execution and use it to assemble one final PR description.

**Rationale**: The final PR must include:

1. A checklist of every successfully applied update (`package`, `old → new`)
2. A skipped-updates section with the reason for each skipped package

Maintaining that inventory as each update is evaluated avoids reconstructing state from git history afterward.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| Rebuild the applied/skipped list from commits at the end | Fragile if multiple updates are reverted or re-tried |
| Open one PR per successful update | Conflicts with the issue requirement to combine safe updates into one PR |
