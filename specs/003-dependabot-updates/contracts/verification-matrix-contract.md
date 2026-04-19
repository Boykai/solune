# Contract: Verification Matrix

## Purpose

Define the minimum verification commands required before a dependency update can be retained in the batch branch.

## Blocking verification profiles

### Backend-core (`pip` updates and any cross-cutting update that can affect backend builds)

Working directory: `solune/backend`

```text
uv lock                    # only when manifest changed and lockfile must be regenerated
uv sync --locked --extra dev
uv run pip-audit .
uv run ruff check src tests
uv run ruff format --check src tests
uv run bandit -r src/ -ll -ii --skip B104
uv run pyright src
uv run pyright -p pyrightconfig.tests.json
uv run pytest --cov=src --cov-report=term-missing --cov-report=xml --cov-report=html --durations=20 --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency
```

### Frontend-core (`npm` updates and any cross-cutting update that can affect frontend builds)

Working directory: `solune/frontend`

```text
npm install                # only when manifest changed and package-lock.json must be regenerated
npm ci
npm audit --audit-level=high
npm run lint
npm run type-check
npm run type-check:test
npm run test:coverage
npm run build
```

### Repo-cross-checks (required before retaining any successful candidate)

Working directory: repository root

```text
npx --yes markdownlint-cli@0.48.0 '*.md' 'specs/**/*.md' --config solune/.markdownlint.json
bash solune/scripts/check-suppressions.sh
./solune/scripts/generate-diagrams.sh --check
bash solune/scripts/validate-contracts.sh
docker build -t solune-backend ./solune/backend
docker build -t solune-frontend ./solune/frontend
trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed solune-backend
trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed solune-frontend
```

## Advisory verification profiles

These suites exist in CI but are currently non-blocking (`continue-on-error: true`), so they should be observed and recorded when run, but their failure alone does not force a skip:

```text
cd solune/backend && uv run pytest tests/property/ --timeout=120 -v
cd solune/backend && uv run pytest tests/fuzz/ --timeout=120 -v
cd solune/backend && uv run pytest tests/chaos/ --timeout=120 -v
cd solune/backend && uv run pytest tests/concurrency/ --timeout=120 -v
cd solune/frontend && npx playwright install --with-deps chromium
cd solune/frontend && npm run test:e2e -- --project=chromium
```

## Acceptance rules

- Any non-zero exit from a blocking verification command marks the candidate as `skipped`.
- A skipped candidate must record the package name, target version, and a one-line failure summary.
- For major bumps that fail because code changes would be required, the result must also record migration notes.
- Retained diffs must be limited to dependency-related files and generated artifacts implied by the verification commands.
