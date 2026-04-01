# Quickstart: Bug Basher — Full Codebase Review & Fix

**Feature**: 002-bug-basher
**Created**: 2026-03-31

## Prerequisites

1. Repository cloned locally
2. Backend environment set up:
   ```bash
   cd solune/backend
   uv sync --locked --extra dev
   ```
3. Frontend environment set up:
   ```bash
   cd solune/frontend
   npm ci
   ```

## Step 1: Establish Baseline

Verify the existing test suite and lint checks pass before making any changes:

```bash
# Backend
cd solune/backend
uv run ruff check src tests
uv run ruff format --check src tests
uv run pyright src
uv run pytest tests/unit/ -x --timeout=120

# Frontend
cd solune/frontend
npm run lint
npm run test
npm run build
```

If any pre-existing failures exist, document them as out-of-scope.

## Step 2: Security Review (P1)

Review files in priority order for security vulnerabilities:

```bash
# Run static security analysis first
cd solune/backend
uv run bandit -r src -f json -o /tmp/bandit-report.json
uv run pip-audit

# Review high-risk files manually:
# - src/middleware/ (auth, CSRF, CSP)
# - src/services/encryption.py
# - src/services/github_auth.py
# - src/services/session_store.py
# - src/api/auth.py
# - src/services/mcp_server/auth.py
# - src/config.py (insecure defaults)
# - src/logging_utils.py (sensitive data redaction)
```

For each finding:
- **Clear bug**: Fix → update affected tests → add regression test → commit
- **Ambiguous**: Add `TODO(bug-bash):` comment using the file's native comment syntax → commit

Validate after each batch:
```bash
uv run pytest tests/unit/ -x
uv run ruff check src tests
```

## Step 3: Runtime Error Review (P2)

Focus on async patterns, resource management, and exception handling:

```bash
# Review high-risk files:
# - src/services/database.py (connection lifecycle)
# - src/services/cache.py (TTL, bounded collections)
# - src/services/copilot_polling/ (retry logic, timeouts)
# - src/services/workflow_orchestrator/ (concurrent state)
# - src/services/websocket.py (connection cleanup)
# - All httpx usage (timeout config, response handling)
```

## Step 4: Logic Bug Review (P3)

Focus on state transitions, boundary conditions, and return values:

```bash
# Review high-risk files:
# - src/services/workflow_orchestrator/models.py (state machine)
# - src/services/workflow_orchestrator/transitions.py
# - src/services/copilot_polling/pipeline.py (agent completion loop)
# - src/services/agents/service.py (lifecycle management)
# - src/services/pipelines/service.py (CRUD operations)
```

## Step 5: Test Quality Review (P4)

Audit existing tests for quality issues:

```bash
# Search for weak assertions
cd solune/backend
grep -rn "assert True" tests/
grep -rn "assert mock.*\.called$" tests/
grep -rn "MagicMock()" tests/ | grep -v "mock_\|Mock\|patch"

# Check for tests with no assertions
# Check for overly broad try/except in tests
# Check for mock objects leaking into production-like paths
```

## Step 6: Code Quality Review (P5)

Clean up dead code, duplication, and silent failures:

```bash
# Run ruff with extended rules
cd solune/backend
uv run ruff check src --select=ALL --diff

# Review for:
# - Unused imports (F401)
# - Unreachable code (dead branches after return/raise)
# - Duplicated logic across modules
# - Hardcoded values that should be configurable
# - Silent failures (bare except, pass in except)
```

## Step 7: Generate Summary Report

After all fixes are applied:

```bash
# Final validation
cd solune/backend
uv run ruff check src tests
uv run ruff format --check src tests
uv run pyright src
uv run bandit -r src
uv run pytest --cov=src --cov-report=term-missing \
  --ignore=tests/property --ignore=tests/fuzz \
  --ignore=tests/chaos --ignore=tests/concurrency

cd solune/frontend
npm run lint
npm run test
npm run build
```

Generate the summary table with all findings:

```markdown
| # | File | Line(s) | Category | Description | Status |
|---|------|---------|----------|-------------|--------|
| ... | ... | ... | ... | ... | ... |
```

## Validation Checklist

- [ ] All files in the repository audited
- [ ] Every "Fixed" finding has a regression test
- [ ] Full backend test suite passes (zero failures)
- [ ] Full frontend test suite passes (zero failures)
- [ ] All lint/format checks pass
- [ ] Type checks pass (pyright, tsc)
- [ ] Security scan passes (bandit)
- [ ] No new dependencies added
- [ ] No architecture or API surface changes
- [ ] Summary table complete (every fix and flag represented)
- [ ] Every "Flagged" finding has a `TODO(bug-bash)` comment in source
