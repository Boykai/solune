# Quickstart: Dependabot Updates

**Feature**: Dependabot Updates | **Date**: 2026-04-14

## Prerequisites

- Git with access to `Boykai/solune`
- Node.js and npm for `/home/runner/work/solune/solune/solune/frontend`
- Python 3.12+ and `uv` for `/home/runner/work/solune/solune/solune/backend`
- A clean working tree before starting update execution

## 1. Sync the repository state

```bash
cd /home/runner/work/solune/solune
git fetch --unshallow origin || true
git fetch origin main:refs/remotes/origin/main
```

Create a fresh working branch from the current default branch before evaluating updates:

```bash
cd /home/runner/work/solune/solune
git checkout -b chore/deps-batch-update origin/main
```

## 2. Apply updates in the planned order

Use the update order from `/home/runner/work/solune/solune/specs/006-dependabot-updates/plan.md`:

1. Patch bumps
2. Minor dev-dependency bumps
3. Minor runtime bumps
4. Major bumps

Always apply **one package update at a time**.

### Backend workflow (`pip` / `uv`)

For each backend package in `/home/runner/work/solune/solune/solune/backend/pyproject.toml`:

```bash
cd /home/runner/work/solune/solune/solune/backend
# Edit one dependency version in pyproject.toml
uv lock
uv sync --extra dev
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run pyright src/
uv run pytest tests/unit/ -q
```

If any command fails:

1. Revert the manifest + lock change for that package
2. Record the package, target version, and a one-line failure summary
3. Move to the next update

### Frontend workflow (`npm`)

For each frontend package in `/home/runner/work/solune/solune/solune/frontend/package.json`:

```bash
cd /home/runner/work/solune/solune/solune/frontend
# Edit one dependency version in package.json
npm install
npm run lint
npm run type-check
npm run test
npm run build
```

If any command fails:

1. Revert the manifest + lock change for that package
2. Record the package, target version, and a one-line failure summary
3. Move to the next update

## 3. Re-sync before each next update

After every accepted or skipped update, refresh the default branch so the next evaluation starts from the latest dependency graph:

```bash
cd /home/runner/work/solune/solune
git fetch origin main:refs/remotes/origin/main
git rebase origin/main
```

If the working branch is intentionally kept as a single accumulation branch, only rebase after the current update has been fully accepted or reverted.

## 4. Final combined verification

After all safe updates are staged, rerun the full validation matrix.

### Backend

```bash
cd /home/runner/work/solune/solune/solune/backend
uv lock
uv sync --extra dev
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run pyright src/
uv run pytest tests/unit/ -q
```

### Frontend

```bash
cd /home/runner/work/solune/solune/solune/frontend
npm install
npm run lint
npm run type-check
npm run test
npm run build
```

## 5. Prepare the final PR payload

Create one PR titled `chore(deps): apply Dependabot batch update` and include:

- A checklist of every applied update (`package`, `old → new`)
- A skipped-updates section with the reason for every rejected update

Example outline:

```markdown
## Applied updates
- [x] pytest (`9.0.2` → `9.0.3`)
- [x] happy-dom (`20.8.9` → `20.9.0`)

## Skipped updates
- pytest-randomly (`>=3.16.0` → `>=4.0.1`) — requires plugin migration for failing test collection
```

## 6. Close superseded Dependabot PRs

After the combined PR is ready and each successful update is represented there, close only the Dependabot PRs whose changes were applied. Do not delete or force-push any unrelated branches.
