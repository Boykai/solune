# Quickstart: Bug Basher — Full Codebase Review & Fix

**Feature**: 002-bug-basher
**Date**: 2026-03-31
**Prerequisites**: [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

## Overview

This feature performs a comprehensive bug bash code review of the entire Solune codebase. The review audits every file across five prioritized bug categories, fixes obvious bugs with regression tests, and flags ambiguous issues with `# TODO(bug-bash):` comments. The deliverable is a clean codebase with all tests passing plus a summary report documenting every finding.

## Review Process

### Step 1: Establish Baseline

Before making any changes, confirm the existing test suite and linting pass:

```bash
# Backend — from solune/backend/
uv sync --locked --extra dev
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
uv run pyright src
pytest tests/unit/

# Frontend — from solune/frontend/
npm ci
npm run lint
npm run test
```

All checks must pass before the review begins. Pre-existing failures are out of scope.

### Step 2: Review by Risk Tier

Review files in the order defined by research.md RT-005:

**Tier 1 — Critical (security-first)**:
1. `src/config.py` — Settings validation, encryption keys
2. `src/api/auth.py` — OAuth flow, session management
3. `src/api/webhooks.py` — Webhook verification, external input
4. `src/services/encryption.py` — Encryption key management
5. `src/dependencies.py` — Dependency injection, startup validation
6. `src/main.py` — FastAPI app setup, CORS, middleware

**Tier 2 — High (complex modules)**:
- `src/services/copilot_polling/pipeline.py` (3,403 LOC)
- `src/services/workflow_orchestrator/orchestrator.py` (2,747 LOC)
- `src/api/chat.py` (2,335 LOC)
- All modules > 1,000 LOC

**Tier 3 — Standard**:
- All remaining modules in their directory order

### Step 3: For Each File — Single-Pass Review

Within each file, check all five categories:

1. **Security** (P1): Auth bypasses, injection risks, exposed secrets, insecure defaults, input validation gaps
2. **Runtime** (P2): Unhandled exceptions, race conditions, null references, type errors, resource leaks
3. **Logic** (P3): Wrong state transitions, off-by-one errors, incorrect return values, data inconsistencies
4. **Test Quality** (P4): Untested paths, tests passing for wrong reason, mock leaks, assertions that never fail
5. **Code Quality** (P5): Dead code, unreachable branches, duplicated logic, hardcoded values, silent failures

### Step 4: For Each Bug Found — Fix or Flag

**If the bug is clear and the fix is obvious**:
1. Fix the bug in the source file (minimal, focused change)
2. Update any existing tests affected by the fix
3. Add at least one new regression test
4. Run the validation gate (Step 5)
5. Commit with a descriptive message

**If the bug is ambiguous** (see criteria in contracts/bug-bash-review.yaml):
1. Add a `# TODO(bug-bash):` comment at the relevant line
2. The comment must describe: the issue, the options, and why it needs human judgment
3. Record the finding for the summary report

### Step 5: Validation Gate (per fix)

After each fix, verify:

```bash
# Backend validation
cd solune/backend
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
uv run pyright src
pytest tests/unit/ -v --tb=short

# Frontend validation (if frontend files changed)
cd solune/frontend
npm run lint
npm run test
```

Do NOT commit if any check fails. Iterate on the fix until green.

### Step 6: Generate Summary Report

After all files are reviewed, produce a summary table:

```markdown
| # | File | Line(s) | Category | Description | Status |
|---|------|---------|----------|-------------|--------|
| 1 | `path/to/file.py` | 42-45 | Security | Description of bug | ✅ Fixed |
| 2 | `path/to/file.py` | 100 | Logic | Description of ambiguity | ⚠️ Flagged (TODO) |
```

**Validation**:
- Every ✅ Fixed entry has a passing regression test
- Every ⚠️ Flagged entry has a `# TODO(bug-bash):` comment in source
- Files with no findings are NOT in the table

## Files Modified

This feature modifies existing files only — no new modules or services are created.

**Expected changes**:
- Bug fixes scattered across `solune/backend/src/` and `solune/frontend/src/`
- New regression tests in `solune/backend/tests/unit/` and alongside frontend components
- `# TODO(bug-bash):` comments in source files for flagged items

**No changes expected to**:
- `pyproject.toml` or `package.json` (no new dependencies)
- Module directory structure (no architectural changes)
- Public API surface (endpoint signatures, response schemas)

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Single-pass per module (not per category) | More efficient; avoids re-reading the same file 5 times |
| Risk-tiered review order | Security-critical and complex modules get priority attention |
| Regression tests in existing test dirs | Preserves existing test organization (FR-012) |
| TODO comments for ambiguity | Prevents well-intentioned but potentially harmful changes (FR-005) |
| Incremental validation per fix | Catches issues early; avoids cascading failures from multiple changes |
| Summary report as markdown table | Matches spec requirement (FR-009); version-controlled and auditable |

## Verification

After all fixes are applied, run the full validation suite:

```bash
# Full backend validation
cd solune/backend
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
uv run pyright src
pytest tests/unit/ -v

# Full frontend validation
cd solune/frontend
npm run lint
npm run test

# Optional: extended test suites
cd solune/backend
pytest tests/integration/ -v
pytest tests/e2e/ -v
```

All checks must pass (FR-006, FR-007). If any fail, iterate on the failing fix until green (FR-008).
