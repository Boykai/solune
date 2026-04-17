# Implementation Plan: Bug Basher

**Branch**: `001-bug-basher` | **Date**: 2026-04-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-bug-basher/spec.md`

## Summary

Perform a comprehensive bug bash code review of the entire Solune codebase — a web application with a Python/FastAPI backend (~183 source files) and a React/TypeScript frontend (~541 source files). The review audits every file across five bug categories in priority order: (1) security vulnerabilities, (2) runtime errors, (3) logic bugs, (4) test gaps, and (5) code quality issues. Each obvious bug is fixed with a minimal change and at least one regression test; ambiguous issues are flagged with `TODO(bug-bash)` comments for human review. The approach is systematic, file-by-file, validating the full test suite after each batch of fixes.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x / ES2022 (frontend)
**Primary Dependencies**: FastAPI, Pydantic, githubkit, httpx, aiosqlite, cryptography (backend); React 18, Vite, Radix UI, dnd-kit, Zustand (frontend)
**Storage**: SQLite via aiosqlite (backend), browser localStorage/sessionStorage (frontend)
**Testing**: pytest with pytest-asyncio, pytest-cov, hypothesis (backend); vitest with @testing-library/react (frontend)
**Linting**: ruff, bandit, pyright (backend); ESLint with react-hooks/jsx-a11y/security plugins, Prettier, TypeScript strict mode (frontend)
**Target Platform**: Linux server (backend), modern browsers (frontend)
**Project Type**: Web application (backend + frontend in `solune/` monorepo subdirectory)
**Performance Goals**: N/A — bug bash does not introduce new features; existing performance characteristics must be preserved
**Constraints**: No new dependencies, no public API changes, no architecture changes, minimal focused fixes only
**Scale/Scope**: ~183 backend Python source files, ~260 backend test files, ~541 frontend TypeScript source files; full repository audit

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Specification-First Development** | ✅ PASS | `spec.md` exists with 5 prioritized user stories (P1–P5), Given-When-Then acceptance scenarios, and clear scope boundaries |
| **II. Template-Driven Workflow** | ✅ PASS | All artifacts follow canonical templates from `.specify/templates/` |
| **III. Agent-Orchestrated Execution** | ✅ PASS | Bug bash decomposes into single-responsibility phases: security audit → runtime audit → logic audit → test quality → code quality |
| **IV. Test Optionality with Clarity** | ✅ PASS | Tests are **explicitly required** by the feature spec (FR-003: each bug fix MUST include at least one regression test). This is not optional — it is mandated by the specification |
| **V. Simplicity and DRY** | ✅ PASS | Each fix is minimal and focused; no drive-by refactors per constraint. YAGNI enforced by "do not change architecture or public API surface" |

**Gate Result**: ✅ ALL GATES PASS — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-bug-basher/
├── plan.md              # This file
├── research.md          # Phase 0: audit methodology and tooling research
├── data-model.md        # Phase 1: bug report entity model
├── quickstart.md        # Phase 1: quick-start guide for executing the bug bash
├── contracts/           # Phase 1: review checklist contracts per category
│   ├── security-checklist.md
│   ├── runtime-checklist.md
│   ├── logic-checklist.md
│   ├── test-quality-checklist.md
│   └── code-quality-checklist.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── api/              # API route handlers (auth, board, chat, projects, etc.)
│   │   ├── middleware/        # CSP, CSRF, rate limiting, admin guard, request ID
│   │   ├── models/           # Pydantic models
│   │   ├── services/         # Business logic (chat_agent, pipelines, github_projects, etc.)
│   │   ├── migrations/       # Database migrations
│   │   ├── config.py         # Application configuration
│   │   ├── constants.py      # Shared constants
│   │   ├── main.py           # FastAPI application entry point
│   │   └── utils.py          # Shared utilities
│   └── tests/
│       ├── unit/             # Unit tests (~260 files)
│       ├── integration/      # Integration tests
│       ├── architecture/     # Import boundary tests
│       ├── property/         # Hypothesis property-based tests
│       ├── fuzz/             # Fuzz tests
│       ├── chaos/            # Chaos tests
│       ├── concurrency/      # Concurrency tests
│       └── conftest.py       # Shared fixtures
├── frontend/
│   ├── src/
│   │   ├── components/       # UI components (agents, board, chat, settings, etc.)
│   │   ├── hooks/            # Custom React hooks
│   │   ├── services/         # API client services
│   │   ├── lib/              # Shared utilities and re-exports (icons, commands)
│   │   ├── context/          # React context providers
│   │   ├── pages/            # Page-level components
│   │   ├── types/            # TypeScript type definitions
│   │   └── utils/            # Frontend utilities
│   └── e2e/                  # Playwright end-to-end tests
├── scripts/                  # Build/validation scripts (check-suppressions.sh, etc.)
└── docs/                     # Project documentation
```

**Structure Decision**: Existing web application structure with `solune/backend/` (Python/FastAPI) and `solune/frontend/` (React/TypeScript/Vite). The bug bash operates across both subsystems. No structural changes are made — all fixes are in-place within the existing directory layout.

## Execution Strategy

### Phase 1: Security Vulnerabilities (P1)

**Scope**: All files under `solune/backend/src/` and `solune/frontend/src/`

**Approach**:

1. **Automated scanning**: Run `bandit -r src/ -ll -ii` (backend), ESLint security plugin (frontend)
2. **Manual audit checklist**:
   - Authentication/authorization bypasses in `api/auth.py`, middleware files
   - Injection risks in database queries (`services/database.py`, any raw SQL)
   - Secrets/tokens in code or config (grep for API keys, tokens, passwords)
   - Input validation gaps in API endpoints
   - CSP/CSRF middleware correctness
   - Cryptographic implementation in `services/encryption.py`
   - Rate limiting effectiveness in `middleware/rate_limit.py`
3. **Fix pattern**: Minimal patch + regression test per finding
4. **Validation**: Full `pytest` + `ruff check` + `bandit` pass

### Phase 2: Runtime Errors (P2)

**Scope**: All Python and TypeScript source files

**Approach**:

1. **Automated scanning**: `pyright` strict mode (backend), `tsc --noEmit` (frontend)
2. **Manual audit checklist**:
   - Unhandled exceptions in async code paths (missing try/except in `async def`)
   - Resource leaks: unclosed database connections, file handles, HTTP clients
   - Race conditions in concurrent operations (task registry, polling loops)
   - Null/None references without guards
   - Missing imports
   - Type errors caught by runtime but not by static analysis
3. **Fix pattern**: Add error handling + resource cleanup + regression test
4. **Validation**: Full test suite + type-check pass

### Phase 3: Logic Bugs (P3)

**Scope**: Business logic in services, API handlers, React hooks, state management

**Approach**:

1. **Manual audit checklist**:
   - State transitions in workflow orchestrator and pipeline services
   - Off-by-one errors in pagination (`services/pagination.py`)
   - Incorrect API call patterns in GitHub integration services
   - Data inconsistencies between frontend state and backend responses
   - Broken control flow in polling loops and agent tracking
   - Incorrect return values in service functions
2. **Fix pattern**: Correct logic + boundary-case regression test
3. **Validation**: Full test suite pass

### Phase 4: Test Quality (P4)

**Scope**: All test files under `solune/backend/tests/` and `solune/frontend/src/__tests__/`

**Approach**:

1. **Coverage analysis**: Run `pytest --cov` and identify untested code paths
2. **Manual audit checklist**:
   - Tests that pass for the wrong reason (e.g., mocking out the code under test)
   - Mock leaks (MagicMock objects leaking into production paths like database file paths)
   - Assertions that never fail (always-true conditions, `assert True`)
   - Missing edge case coverage for error paths
   - Tests that don't actually test the behavior described in their name
3. **Fix pattern**: Replace weak assertions + add meaningful coverage
4. **Validation**: Coverage delta report + full suite pass

### Phase 5: Code Quality (P5)

**Scope**: Entire codebase

**Approach**:

1. **Automated scanning**: `ruff check` with extended rules, ESLint
2. **Manual audit checklist**:
   - Dead code and unreachable branches
   - Duplicated logic across modules
   - Hardcoded values that should be configurable
   - Missing error messages (bare `except:`, empty `catch`)
   - Silent failures (swallowed exceptions)
3. **Fix pattern**: Remove dead code / consolidate duplication + verify tests pass
4. **Validation**: Full test suite + lint pass

### Cross-Cutting Validation

After all phases complete:

1. Run full backend test suite: `uv run pytest --cov=src --cov-report=term-missing`
2. Run full frontend test suite: `npm run test`
3. Run all linters: `ruff check`, `ruff format --check`, `bandit`, `pyright`, `eslint`, `tsc`
4. Run suppression guard: `solune/scripts/check-suppressions.sh`
5. Produce final summary table with all findings

## Complexity Tracking

> No constitution violations identified. All principles are satisfied by the bug bash approach.
