# Solune — Development Guidelines

Last updated: 2026-04-04

> Prefer repo discovery and canonical source files over copying version
> inventories into prompts or docs. Use official library documentation when
> external behavior matters.

## Canonical Sources

- Exact backend runtimes, dependencies, and coverage gates live in
  `solune/backend/pyproject.toml`.
- Exact frontend dependencies and runnable scripts live in
  `solune/frontend/package.json`.
- Required CI runtimes and validation gates live in
  `.github/workflows/ci.yml`.
- Product, setup, architecture, and testing guidance live in `README.md`,
  `solune/README.md`, and `solune/docs/`.
- The platform changelog for this repo is `solune/CHANGELOG.md`.

## Repository Shape

- Repo-root automation and deployment files live at the top level:
  `README.md`, `docker-compose.yml`, `azure.yaml`, `infra/`, and `.github/`.
- The product code lives under `solune/`:
  - `solune/backend/` — FastAPI backend, SQLite persistence, migrations, tests.
  - `solune/frontend/` — React frontend, unit tests, Playwright E2E.
  - `solune/docs/` — product documentation.
  - `solune/scripts/` — hooks, diagram generation, and validation scripts.
  - `solune/CHANGELOG.md` — user-facing release notes.
- `.github/agents/copilot-instructions.md` is the repo's custom instruction
  file even though it sits beside agent definitions.
- `.github/agents/*.agent.md` are custom agents,
  `.github/prompts/*.prompt.md` are prompt shortcuts, and
  `.github/agents/mcp.json` is the remote MCP configuration for GitHub-hosted
  agent sessions.
- `.vscode/mcp.json` is local IDE MCP configuration. Do not treat it as the
  remote GitHub agent MCP file.

## Stack Summary

- Backend: FastAPI, Pydantic v2, SQLite via `aiosqlite`, Microsoft Agent
  Framework, GitHub Copilot SDK, Azure AI/OpenAI fallbacks, WebSockets, and
  SSE streaming.
- Frontend: React 19, TypeScript strict mode, Vite 8, TanStack Query v5,
  Tailwind CSS 4, Radix UI primitives, React Hook Form, and Zod.
- Infrastructure: Docker Compose runs backend, frontend, and Signal sidecar
  locally; Azure deployment assets live under `infra/`.
- For exact versions, read the canonical files instead of extending this
  document with package-by-package snapshots.

## Backend Notes

- Most backend work happens in `solune/backend/src/api/`,
  `solune/backend/src/services/`, `solune/backend/src/models/`,
  `solune/backend/src/middleware/`, and
  `solune/backend/src/migrations/`.
- Use `resolve_repository()` from `solune/backend/src/utils.py` for
  owner/repo parsing instead of duplicating fallback logic.
- SQLite runs in WAL mode and migrations are applied automatically on startup
  from `solune/backend/src/migrations/`.
- Agent and pipeline execution logic is concentrated in `services/agents/`,
  `services/pipelines/`, `services/copilot_polling/`, and
  `services/workflow_orchestrator/`.
- Tool and MCP flows span `src/api/mcp.py`, `services/mcp_store.py`,
  `services/tools/presets.py`, `services/tools/service.py`, and
  `services/agents/service.py`.
- Keep `AsyncGenerator` annotations fully parameterized for Python 3.12
  compatibility, for example `AsyncGenerator[str, None]`.

## Frontend Notes

- Most frontend work happens in `solune/frontend/src/components/`, `pages/`,
  `hooks/`, `services/`, `context/`, and `lib/`.
- The API client lives in `solune/frontend/src/services/api.ts`.
- Tailwind uses the CSS-first v4 model in `solune/frontend/src/index.css`.
  Do not add `tailwind.config.js` or `postcss.config.js` unless the build
  model changes.
- Reuse shared Celestial theme utilities in
  `solune/frontend/src/index.css` instead of adding component-local animation
  systems or duplicating gradients.
- Prefer existing shared UI wrappers in
  `solune/frontend/src/components/ui/` before introducing new overlay,
  dialog, or form primitives.
- Frontend E2E tests live in `solune/frontend/e2e/`; component and hook tests
  live alongside source under `solune/frontend/src/`.

## Working Rules

- Prefer focused, minimal fixes over broad refactors unless the task
  explicitly requires structural change.
- Use conventional commit prefixes such as `feat:`, `fix:`, `docs:`,
  `refactor:`, `test:`, and `chore:`.
- Update `solune/CHANGELOG.md` for user-facing behavior changes, API changes,
  configuration changes, infra changes, and dependency changes with user
  impact.
- Do not add changelog entries for test-only, spec-only, or purely internal
  refactors with no user-visible effect.
- Prefer Context7 when you need current third-party library documentation and examples.

## Validation Expectations

- Backend local setup: `cd solune/backend`; if `.venv` exists, activate it.
  CI uses `uv sync --locked --extra dev` and `uv run`.
- Backend validation: `ruff check src tests`, `ruff format --check src tests`,
  `pyright src`, `pyright -p pyrightconfig.tests.json`, and the relevant
  `pytest` scope.
- Frontend validation: `cd solune/frontend && npm run lint && npm run
  type-check && npm run type-check:test && npm run test && npm run build`.
- Frontend E2E: `cd solune/frontend && npm run test:e2e`.
- Hook setup lives in `solune/scripts/setup-hooks.sh`; the staged-file
  pre-commit workflow lives in `solune/scripts/pre-commit`.
- CI uses Python 3.12 and Node 20, while local tooling and Docker images may
  target newer Python and Node versions. Account for that version skew when
  investigating failures.

## Agents And MCP

- The current custom-agent inventory lives in `.github/agents/`; inspect
  that directory instead of maintaining a duplicated list here.
- `.github/agents/mcp.json` currently exposes Context7, Azure MCP, and Bicep
  MCP to remote GitHub agents.
- If MCP is unavailable, fall back to file reads, code search, and local
  validation instead of blocking or inventing missing context.
- Agent definitions should continue to accept `$ARGUMENTS` in their
  markdown body so the invoking prompt can scope the task.
