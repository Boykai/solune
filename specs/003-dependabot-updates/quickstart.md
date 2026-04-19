# Quickstart: Executing the Dependabot Batch Update Plan

## 1. Confirm live inventory

1. Review `.github/dependabot.yml` to confirm the supported ecosystems and directories.
2. Query the repository's open pull requests and filter to `dependabot[bot]`.
3. If the filtered inventory is empty, record a no-op result and stop — do **not** create an empty batch PR.

## 2. Build the prioritized queue

1. For each open Dependabot PR, capture the dependency name, current version, target version, ecosystem, changed files, and source branch.
2. Classify the semver delta as `patch`, `minor`, `major`, or `unknown`.
3. Flag overlap when two PRs share a manifest, lockfile, workflow file, Dockerfile, or dependency graph.
4. Sort the queue as:
   1. isolated patch updates
   2. overlapping patch updates
   3. isolated minor updates
   4. overlapping minor updates
   5. isolated major updates
   6. overlapping major updates
   7. unknown-version updates

## 3. Prepare a clean baseline for each candidate

```text
git fetch origin main:refs/remotes/origin/main
git checkout main
git pull --ff-only origin main
git checkout -B dependabot-batch-work origin/main
```

For every subsequent candidate, start from the latest successful batch state (main + previously retained safe updates).

## 4. Apply a backend (`pip`) update

1. Apply the Dependabot manifest change to `solune/backend/pyproject.toml`.
2. Regenerate `solune/backend/uv.lock` with `uv lock`.
3. Run the backend verification profile:

```text
cd /home/runner/work/solune/solune/solune/backend
uv lock
uv sync --locked --extra dev
uv run pip-audit .
uv run ruff check src tests
uv run ruff format --check src tests
uv run bandit -r src/ -ll -ii --skip B104
uv run pyright src
uv run pyright -p pyrightconfig.tests.json
uv run pytest --cov=src --cov-report=term-missing --cov-report=xml --cov-report=html --durations=20 --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency
```

## 5. Apply a frontend (`npm`) update

1. Apply the Dependabot manifest change to `solune/frontend/package.json`.
2. Regenerate `solune/frontend/package-lock.json` with `npm install` (respecting `.npmrc`'s `legacy-peer-deps=true`).
3. Run the frontend verification profile:

```text
cd /home/runner/work/solune/solune/solune/frontend
npm install
npm ci
npm audit --audit-level=high
npm run lint
npm run type-check
npm run type-check:test
npm run test:coverage
npm run build
```

## 6. Apply GitHub Actions or Docker updates

- **GitHub Actions**: update the pinned action reference(s) in `.github/workflows/*.yml`, then run repo cross-checks plus the affected backend/frontend validation commands.
- **Docker**: update the base image tag(s) in `solune/backend/Dockerfile` or `solune/frontend/Dockerfile`, then run repo cross-checks and verify both Docker images still build and pass Trivy scans.

## 7. Run repo-wide cross-checks before retaining a candidate

```text
cd /home/runner/work/solune/solune
npx --yes markdownlint-cli@0.48.0 '*.md' 'specs/**/*.md' --config solune/.markdownlint.json
bash solune/scripts/check-suppressions.sh
./solune/scripts/generate-diagrams.sh --check
bash solune/scripts/validate-contracts.sh
docker build -t solune-backend ./solune/backend
docker build -t solune-frontend ./solune/frontend
trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed solune-backend
trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed solune-frontend
```

If any blocking step fails, revert that candidate, record the failure summary, and move to the next queued update.

## 8. Optional advisory suites

Run these when the affected dependency could reasonably impact long-tail or browser behavior. Record outcomes, but do not block the batch solely on their failure unless the repository policy changes.

```text
cd /home/runner/work/solune/solune/solune/backend && uv run pytest tests/property/ --timeout=120 -v
cd /home/runner/work/solune/solune/solune/backend && uv run pytest tests/fuzz/ --timeout=120 -v
cd /home/runner/work/solune/solune/solune/backend && uv run pytest tests/chaos/ --timeout=120 -v
cd /home/runner/work/solune/solune/solune/backend && uv run pytest tests/concurrency/ --timeout=120 -v
cd /home/runner/work/solune/solune/solune/frontend && npx playwright install --with-deps chromium
cd /home/runner/work/solune/solune/solune/frontend && npm run test:e2e -- --project=chromium
```

## 9. Create the combined PR report

Only after at least one update has passed:

1. Commit the retained dependency-only diff.
2. Create a PR titled `chore(deps): apply Dependabot batch update`.
3. Populate the PR description with:
   - a checklist of every applied update (`package old -> new`)
   - a skipped-updates section with one-line failure reasons
4. Close and delete only the Dependabot PRs/branches whose updates were successfully absorbed.

If no candidates succeed, stop with the recorded skip/no-op report and leave every Dependabot PR untouched.
