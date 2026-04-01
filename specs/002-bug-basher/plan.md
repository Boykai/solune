# Implementation Plan: Bug Basher — Full Codebase Review & Fix

**Branch**: `002-bug-basher` | **Date**: 2026-03-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-bug-basher/spec.md`

## Summary

Perform a comprehensive bug-bash code review of the entire Solune codebase (170 Python backend files, 446 TypeScript/TSX frontend files). Identify and fix bugs across five priority categories — security vulnerabilities, runtime errors, logic bugs, test gaps, and code quality issues. Each fix includes a regression test; ambiguous issues are flagged with `# TODO(bug-bash):` comments. The outcome is a fully green test suite, passing lint/format checks, and a single summary table of all findings.

## Technical Context

**Language/Version**: Python 3.12+ (backend, target 3.13 for type checking), TypeScript 6.0.2 (frontend)
**Primary Dependencies**: FastAPI 0.135+, Pydantic 2.12+, githubkit 0.14.6+, agent-framework 1.0.0b1+, React 19.2, Vite 8.0, TanStack Query 5.96
**Storage**: SQLite via aiosqlite 0.22+ (async), 14 migration files
**Testing**: pytest 9.0+ (backend, 225 test files across 9 categories), Vitest 4.0.18 (frontend, 178 test files), Playwright 1.58.2 (E2E)
**Target Platform**: Linux server (backend), browser SPA (frontend)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: N/A — bug bash focuses on correctness, not performance tuning
**Constraints**: No new dependencies, no architecture changes, no public API surface changes, minimal focused fixes only
**Scale/Scope**: ~170 Python source files, ~446 TypeScript/TSX source files, ~400 test files total

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Specification-First Development** | ✅ PASS | spec.md exists with 6 prioritized user stories, acceptance scenarios, and success criteria |
| **II. Template-Driven Workflow** | ✅ PASS | All artifacts follow canonical templates |
| **III. Agent-Orchestrated Execution** | ✅ PASS | Work decomposes into single-responsibility agents per bug category |
| **IV. Test Optionality with Clarity** | ✅ PASS | Tests are explicitly required by the spec (FR-003: regression test per fix) |
| **V. Simplicity and DRY** | ✅ PASS | Each fix must be minimal and focused (FR-013); no drive-by refactors |

**Gate result: PASS** — No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/002-bug-basher/
├── plan.md              # This file (speckit.plan output)
├── research.md          # Phase 0: review methodology and tooling research
├── data-model.md        # Phase 1: bug finding entities and relationships
├── quickstart.md        # Phase 1: how to execute the bug bash
├── contracts/           # Phase 1: review process contracts (checklist schemas)
│   └── review-process.yaml
├── checklists/
│   └── requirements.md  # Pre-existing quality checklist
└── tasks.md             # Phase 2 output (speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── api/              # 21 REST endpoint modules
│   │   ├── middleware/        # 5 middleware modules (auth, CSRF, CSP, rate limit, request ID)
│   │   ├── migrations/        # 14 SQLite migration files
│   │   ├── models/            # 27 Pydantic model modules
│   │   ├── prompts/           # 6 AI prompt definition modules
│   │   ├── services/          # 40+ service modules + 9 subdirectories
│   │   │   ├── agents/        # Agent lifecycle, MCP sync
│   │   │   ├── chores/        # Background chore execution
│   │   │   ├── copilot_polling/  # GitHub Copilot polling
│   │   │   ├── github_projects/  # GitHub Projects API integration
│   │   │   ├── mcp_server/    # Model Context Protocol server
│   │   │   ├── pipelines/     # Pipeline CRUD and execution
│   │   │   ├── tools/         # Tool/action implementations
│   │   │   └── workflow_orchestrator/  # Pipeline state machine
│   │   ├── main.py            # App setup, lifespan, middleware stack
│   │   ├── config.py          # Settings (Pydantic)
│   │   ├── constants.py       # Enums, magic strings, version
│   │   ├── dependencies.py    # DI helpers, session resolution
│   │   ├── exceptions.py      # Error hierarchy
│   │   ├── logging_utils.py   # Centralized logging, sanitization
│   │   ├── utils.py           # BoundedDict, helpers
│   │   └── protocols.py       # Protocol/interface definitions
│   └── tests/
│       ├── unit/              # 166 files — primary test suite
│       ├── integration/       # 14 files — multi-component flows
│       ├── property/          # 7 files — Hypothesis property tests
│       ├── concurrency/       # 4 files — race condition tests
│       ├── fuzz/              # 3 files — input mutation tests
│       ├── chaos/             # 5 files — fault injection tests
│       ├── e2e/               # 5 files — end-to-end workflows
│       ├── performance/       # 1 file — timing/load tests
│       └── architecture/      # 1 file — import rule enforcement
├── frontend/
│   ├── src/
│   │   ├── components/        # React UI components
│   │   ├── pages/             # Route page components
│   │   ├── services/          # API client services
│   │   ├── hooks/             # Custom React hooks
│   │   ├── lib/               # Shared utilities
│   │   └── types/             # TypeScript type definitions
│   └── e2e/                   # Playwright E2E tests
├── scripts/                   # Build/CI helper scripts
├── docs/                      # Documentation and architecture diagrams
└── docker-compose.yml         # Local dev orchestration
```

**Structure Decision**: Existing web application structure (backend + frontend) is preserved as-is. The bug bash operates across both projects but makes no structural changes.

## Execution Strategy

### Phase Ordering by Bug Category (Priority)

The bug bash follows the priority order from the spec. Each phase can be parallelized across files within a category but categories are reviewed in order:

| Phase | Category | Priority | Scope | Estimated Files |
|-------|----------|----------|-------|-----------------|
| 1 | Security vulnerabilities | P1 | Auth, encryption, input validation, secrets, middleware | ~30 files |
| 2 | Runtime errors | P2 | Exception handling, resource management, async patterns | ~80 files |
| 3 | Logic bugs | P3 | State transitions, API calls, boundary conditions, return values | ~100 files |
| 4 | Test gaps & quality | P4 | Mock isolation, assertion quality, coverage gaps | ~225 test files |
| 5 | Code quality | P5 | Dead code, duplication, silent failures, hardcoded values | All files |

### High-Risk Areas (Prioritize Review)

Based on codebase analysis, these areas have the highest bug probability:

| Area | Risk | Reason |
|------|------|--------|
| `services/workflow_orchestrator/` | HIGH | Complex state machine (114K lines), concurrent state updates |
| `services/copilot_polling/` | HIGH | External API integration, retry logic, race conditions |
| `services/agents/service.py` | HIGH | Large service (69K lines), agent lifecycle management |
| `middleware/` | HIGH | Auth, CSRF, CSP — security-critical path |
| `services/encryption.py` | HIGH | Cryptographic operations, key management |
| `services/github_auth.py` | HIGH | OAuth flow, token handling |
| `services/session_store.py` | HIGH | Session persistence, encrypted tokens |
| `api/auth.py` | HIGH | Authentication endpoints, token exchange |
| `services/database.py` | MEDIUM | Connection lifecycle, migration execution |
| `services/cache.py` | MEDIUM | TTL management, bounded collections |
| `config.py` | MEDIUM | Environment variable parsing, defaults |
| `main.py` | MEDIUM | Middleware ordering, exception handlers |

### Validation Pipeline

After each fix batch, the following checks must pass:

```bash
# Backend validation (in solune/backend/)
uv run ruff check src tests          # Lint
uv run ruff format --check src tests  # Format
uv run pyright src                     # Type check
uv run pytest tests/unit/ -x          # Unit tests (fast feedback)
uv run pytest --cov=src \
  --ignore=tests/property \
  --ignore=tests/fuzz \
  --ignore=tests/chaos \
  --ignore=tests/concurrency          # Full CI test suite

# Frontend validation (in solune/frontend/)
npm run lint                           # ESLint
npm run typecheck                      # TypeScript
npm run test                           # Vitest unit tests
npm run build                          # Production build

# Security-specific (backend)
uv run bandit -r src                   # Static security analysis
uv run pip-audit                       # Dependency vulnerabilities
```

### Commit Strategy

Each commit addresses one bug or a tightly related group of bugs:

```
fix(category): Brief description of the bug

What: [describe the bug]
Why: [explain why it's a bug]
How: [explain the fix]
Test: [describe the regression test added]
```

### Output Format

Final summary table per the spec:

| # | File | Line(s) | Category | Description | Status |
|---|------|---------|----------|-------------|--------|
| N | `path/to/file.py` | NN-NN | Category | Description | ✅ Fixed / ⚠️ Flagged |

## Constitution Check — Post-Design Re-evaluation

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Specification-First Development** | ✅ PASS | spec.md complete, plan artifacts generated from spec |
| **II. Template-Driven Workflow** | ✅ PASS | plan.md, research.md, data-model.md, contracts/, quickstart.md all follow templates |
| **III. Agent-Orchestrated Execution** | ✅ PASS | Plan decomposes into 5 review phases + validation + reporting, each suitable for agent execution |
| **IV. Test Optionality with Clarity** | ✅ PASS | Tests explicitly required by spec (FR-003); regression test per fix is mandated |
| **V. Simplicity and DRY** | ✅ PASS | No new abstractions introduced; fixes are minimal and focused per FR-013 |

**Post-design gate result: PASS** — No violations. Plan ready for `speckit.tasks`.

## Complexity Tracking

> No constitution violations detected. No complexity justifications needed.
