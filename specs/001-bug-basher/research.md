# Research: Bug Basher

**Feature**: 001-bug-basher | **Date**: 2026-04-17
**Input**: Technical Context from [plan.md](plan.md)

## Research Tasks

### R1: Existing Tooling for Automated Bug Detection

**Decision**: Use existing configured tools — no new tools required.

**Rationale**: The project already has comprehensive automated scanning configured in CI:

- **Backend security**: `bandit -r src/ -ll -ii --skip B104` (already in CI)
- **Backend linting**: `ruff check src tests` + `ruff format --check src tests` (already in CI)
- **Backend type-checking**: `pyright src` (strict mode, already in CI)
- **Backend testing**: `pytest --cov` with coverage enforcement (already in CI)
- **Backend dependency audit**: `pip-audit` (already in CI)
- **Frontend linting**: ESLint with react-hooks, jsx-a11y, and security plugins (already in CI)
- **Frontend type-checking**: `tsc --noEmit` (strict mode, already in CI)
- **Frontend testing**: vitest (already in CI)
- **Suppression guard**: `solune/scripts/check-suppressions.sh` requires `reason:` justification for lint suppressions (already in CI)

**Alternatives considered**:

- Adding `semgrep` for deeper static analysis — rejected because it would add a new dependency, which violates FR-008
- Adding `safety` for Python vulnerability scanning — rejected because `pip-audit` already covers this

### R2: Bug Bash Execution Order and Dependencies

**Decision**: Execute in strict priority order (P1→P5) with full test suite validation between phases.

**Rationale**: Security vulnerabilities (P1) have the highest impact and may affect how other bugs are evaluated. Fixing security issues first ensures that runtime error fixes (P2) and logic bug fixes (P3) don't inadvertently reintroduce security problems. Each phase's fixes are committed and validated before proceeding to the next phase.

**Alternatives considered**:

- Parallel execution of independent categories — rejected because bug fixes in one category can affect other categories (e.g., fixing a security input validation bug may resolve a related runtime error)
- Single-pass review across all categories simultaneously — rejected because it increases cognitive load and makes it harder to track which fixes address which category

### R3: Backend Architecture Boundaries for Safe Fixes

**Decision**: Respect existing module boundaries enforced by architecture tests.

**Rationale**: The project has explicit architecture tests in `tests/architecture/test_import_rules.py` and `tests/unit/test_module_boundaries.py` that enforce:

- API layer (`src/api/`) must NOT import `*_store` modules directly; must use `workflow_orchestrator` re-exports
- API layer must NOT reference private attributes (underscore-prefixed) in docstrings
- Pipeline state management must go through `workflow_orchestrator/__init__.py` re-exports

Any bug fix must respect these boundaries. Fixes that would require crossing these boundaries should be flagged as `TODO(bug-bash)` for human review.

**Alternatives considered**: None — architecture boundaries are non-negotiable per existing test enforcement

### R4: Frontend Coding Conventions for Safe Fixes

**Decision**: Follow established frontend conventions.

**Rationale**: The frontend has specific conventions that must be preserved:

- Lucide icons must be imported from `@/lib/icons` (re-export module), not directly from `lucide-react`
- `celestial-focus` class provides accessible focus ring styles
- ESLint config enforces react-hooks rules, jsx-a11y accessibility, and security patterns
- Suppressions require `reason:` justification per `check-suppressions.sh`

**Alternatives considered**: None — conventions are enforced by linting and must be followed

### R5: Test Infrastructure and Mock Patterns

**Decision**: Follow existing test patterns; beware of known mock pitfalls.

**Rationale**: Key findings about the test infrastructure:

- `task_registry.create_task` is used by `coalesced_fetch` (cache service) internally — mocking it globally affects cache behavior, causing 502 errors. Mocks must be scoped carefully.
- Async generator mocks should use class-based async iterators (not unreachable `yield` patterns) for proper error simulation
- Backend tests use `conftest.py` fixtures extensively
- Frontend tests use `@testing-library/react` with vitest

**Alternatives considered**: None — these are established patterns with known pitfalls documented in project memory

### R6: Handling Ambiguous Issues (TODO Pattern)

**Decision**: Use the `# TODO(bug-bash):` comment format specified in the feature spec.

**Rationale**: The spec requires that ambiguous or trade-off situations are NOT fixed directly but flagged with a specific comment format. The comment must include:

1. Description of the issue
2. Available options for resolution
3. Why a human decision is needed

For Python files, the comment format is:

```python
# TODO(bug-bash): <description>
# Options: (a) <option1>, (b) <option2>
# Needs human decision because: <reason>
```

For TypeScript files:

```typescript
// TODO(bug-bash): <description>
// Options: (a) <option1>, (b) <option2>
// Needs human decision because: <reason>
```

The suppression guard (`check-suppressions.sh`) checks for `reason:` in suppression comments. `TODO(bug-bash)` comments are not suppressions, so they won't trigger the guard — but any lint/type suppressions added as part of fixes must include the reason.

**Alternatives considered**: Using GitHub issue references instead of inline comments — rejected because the spec explicitly requires inline `TODO(bug-bash)` comments

### R7: Commit Strategy and Validation Loop

**Decision**: Batch fixes by category phase, with full validation between phases.

**Rationale**: Each phase (P1–P5) produces a batch of related fixes. Between phases:

1. Run full backend test suite: `uv run pytest --cov=src --cov-report=term-missing --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency`
2. Run full frontend test suite: `cd solune/frontend && npm run test`
3. Run backend linting: `uv run ruff check src tests && uv run ruff format --check src tests`
4. Run backend security scan: `uv run bandit -r src/ -ll -ii --skip B104`
5. Run backend type check: `uv run pyright src`
6. Run frontend linting: `cd solune/frontend && npm run lint`
7. Run frontend type check: `cd solune/frontend && npm run type-check`

If any check fails, iterate on the fix before proceeding.

**Alternatives considered**:

- Committing each individual fix separately — rejected because it creates excessive commit noise for what may be dozens of small fixes
- Single commit at the end — rejected because it makes it impossible to validate incrementally and risks cascading failures
