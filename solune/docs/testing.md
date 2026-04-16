# Testing

Solune uses layered testing across the FastAPI backend and React frontend. The repository currently contains **200+ backend unit test files**, **240+ Python test files overall**, **260+ frontend unit/property test files**, and **19 Playwright specs**.

## Quick Commands

| What | Command |
|------|---------|
| Backend tests | `cd backend && pytest tests/ -v` |
| Frontend unit tests | `cd frontend && npm test` |
| Frontend E2E | `cd frontend && npm run test:e2e` |
| Backend coverage | `cd backend && pytest tests/ --cov=src` |
| Frontend coverage | `cd frontend && npm run test:coverage` |
| Backend mutation | `cd backend && mutmut run` |
| Frontend mutation | `cd frontend && npx stryker run` |

## Overview

| Tool | Scope | Notes |
|------|-------|-------|
| `pytest` + `pytest-asyncio` | Backend unit, integration, concurrency, property, fuzz, chaos, performance, e2e | Primary backend test runner |
| `Vitest` + React Testing Library | Frontend unit and component tests | Co-located `*.test.ts(x)` coverage across components, hooks, and utilities |
| `fast-check` / Hypothesis | Property-based testing | Input invariants, schema drift, and malformed payload coverage |
| Playwright | Browser end-to-end and responsive UI coverage | Includes route, settings, chat, agent, MCP, and pipeline scenarios |
| `mutmut` / Stryker | Mutation testing | Focused local runs plus dedicated CI workflows |

## Backend Tests

```bash
cd backend
source .venv/bin/activate

# Run everything
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Focused suites
pytest tests/unit/test_api_chat.py -v
pytest tests/fuzz/test_api_input_fuzz.py -q
pytest tests/chaos/test_background_loops.py -q
```

### Backend test layout

```text
backend/tests/
├── architecture/   # Structural and module-boundary checks
├── chaos/          # Fault injection and long-running failure scenarios
├── concurrency/    # Race conditions and shared-state behavior
├── e2e/            # API-level end-to-end coverage
├── fuzz/           # Invalid payload and parser hardening tests
├── helpers/        # Shared test helpers/utilities
├── integration/    # Multi-service / persistence integration tests
├── performance/    # Performance-focused regression checks
├── property/       # Hypothesis/property-based suites
└── unit/           # Isolated route, model, store, and service tests
```

### Backend coverage focus

The unit suite covers the main product domains rather than a small fixed list of files. Expect tests around:

- API routers (`test_api_*.py`)
- Stores and persistence (`test_chat_store.py`, `test_session_store.py`, `test_settings_store.py`, etc.)
- GitHub integration and orchestration (`test_github_*`, `test_workflow_*`, `test_polling_*`)
- Agent/chat flows (`test_agent_*`, `test_chat_*`, `test_signal_*`)
- Operational concerns (`test_rate_limiting.py`, `test_config*.py`, `test_logging_utils.py`, `test_database.py`)

## Frontend Tests

```bash
cd frontend

# Run all unit tests
npm test

# Watch mode
npm run test:watch

# Coverage
npm run test:coverage

# Focused property-based suite
npm test -- src/utils/formatTime.property.test.ts
```

### Frontend unit coverage

Frontend tests are co-located with the code they validate:

- **Components** — chat, board, apps, settings, agents, chores, tools, common UI, and primitives
- **Hooks** — auth, chat, conversations, projects, workflows, activity, pipelines, settings, and utilities
- **Libraries / utilities** — command handlers, config generators, formatters, migrations, and helpers
- **Documentation guards** — `src/docs/documentationLinks.test.ts` verifies markdown link integrity and key doc assertions

## Frontend E2E (Playwright)

```bash
cd frontend

npm run test:e2e
npm run test:e2e:headed
npm run test:e2e:ui
npm run test:e2e:report
```

### Current Playwright coverage

`frontend/e2e/` includes specs for:

- authentication and protected routes
- board navigation and project loading
- chat interaction and responsive chat behavior
- agent creation and responsive agents layout
- chores and responsive chores layout
- settings and MCP tool configuration flows
- pipeline monitoring and responsive pipeline layout
- integration and generic UI smoke coverage
- snapshot-backed responsive regression checks

## Mutation Testing

### Backend mutation (`mutmut`)

```bash
cd backend
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m mutmut run
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m mutmut results
```

Backend mutation shards:

| Shard | Scope |
|-------|-------|
| `auth-and-projects` | GitHub auth, completion providers, model metadata, `github_projects/` |
| `orchestration` | `workflow_orchestrator/`, `pipelines/`, `copilot_polling/`, registry/state helpers |
| `app-and-data` | apps, metadata, caches, DB/stores, cleanup, encryption, websocket |
| `agents-and-integrations` | agent creation, signals, tools, chores, integrations |
| `api-and-middleware` | `src/api/`, `src/middleware/`, `src/utils.py` |

### Frontend mutation (Stryker)

```bash
cd frontend
npx stryker run
npm run test:mutate:hooks-board
npm run test:mutate:hooks-data
npm run test:mutate:hooks-general
npm run test:mutate:lib
```

## CI Gates

- Backend CI runs pytest, coverage reporting, contract generation, and targeted quality checks.
- Frontend CI runs ESLint, type-checking, Vitest coverage thresholds, and Playwright.
- Dedicated workflows cover mutation testing and flaky/performance-oriented checks.
- The suppression guard (`scripts/check-suppressions.sh`) can be run locally or in CI to enforce the [Suppression Policy](#suppression-policy).

## Code Quality Commands

### Backend

```bash
cd backend
source .venv/bin/activate
ruff check src/ tests/
pyright
```

### Frontend

```bash
cd frontend
npm run lint
npm run type-check
npm run build
```

---

## Suppression Policy

Any lint, type-check, test-skip, coverage, or mutation suppression that remains in the codebase **must** carry a `reason:` justification (either inline or on the preceding line). This applies to:

- `# noqa`, `# type: ignore`, `# pragma: no cover`, `# nosec` (Python / Ruff / Bandit)
- `eslint-disable`, `@ts-expect-error`, `@ts-ignore` (TypeScript / ESLint)
- `#disable-next-line` (Bicep)
- `@pytest.mark.skipif`, `test.skip()` (test skips)

**Allowed suppression patterns** (each must include a reason):

| Pattern | Typical reason |
|---------|---------------|
| `# noqa: B008` | FastAPI `Depends()` / `Body()` / `File()` — evaluated per-request, not at import time |
| `# noqa: B010` | Intentional frozen dataclass mutation test; `setattr` required to trigger `FrozenInstanceError` |
| `# noqa: PTH119` | CodeQL-recognised path sanitizer; `pathlib.PurePath.name` not recognised by CodeQL |
| `# type: ignore[...]` | SDK `TypedDict` preview field not yet declared in stubs |
| `eslint-disable react-hooks/exhaustive-deps` | Mount-only effect or intentionally omitted dependency with stable ref |
| `eslint-disable react-hooks/rules-of-hooks` | Playwright `use` callback parameter triggers false positive |
| `eslint-disable react-hooks/set-state-in-effect` | Initialization pattern; async ID not available at first render |
| `eslint-disable jsx-a11y/no-autofocus` | Modal/popover input should receive focus on open |
| `eslint-disable jsx-a11y/click-events-have-key-events` | Modal dialog `stopPropagation` pattern; parent backdrop handles keyboard dismiss |
| `eslint-disable @typescript-eslint/no-explicit-any` | `React.ComponentType<any>` — framework-standard generic bound |
| `#disable-next-line outputs-should-not-contain-secrets` | Bicep cross-module secret passing consumed as `secureParam` downstream |

**CI guard**: Run `./solune/scripts/check-suppressions.sh` from the repository root to verify all suppressions carry a `reason:` marker. The script scans Python, TypeScript, JavaScript, and Bicep files.

Suppressions without a `reason:` marker should be addressed in the next change that touches the file.

---

## What's next?

- [API Reference](api-reference.md) — endpoints covered by the test suite
- [Architecture](architecture.md) — understand the services those tests exercise
- [Troubleshooting](troubleshooting.md) — common causes of failing local runs
