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

- **Backend changes:** validate with `ruff check`, `ruff format --check`, `pyright`, and relevant `pytest` coverage.
- **Frontend changes:** validate with `npm run lint`, `npm run type-check`, `npm run test`, and `npm run build`.
- **Pre-commit hook** (`scripts/pre-commit`): runs ruff format (auto-fix) + ruff lint (auto-fix) + pyright on staged Python files; ESLint (auto-fix) on staged frontend files.
- **Pre-push hook** (`scripts/setup-hooks.sh`): full backend + frontend test gates.
- **CI** (`.github/workflows/ci.yml`): backend uses Python 3.12; frontend uses Node 20. Docker images use Python 3.14 and Node 25. Keep local-vs-CI runtime differences in mind when debugging build or lint mismatches.
- A known flaky failure can occur in `frontend/src/hooks/useAuth.test.tsx` under full parallel runs — confirm isolated behavior before changing unrelated code.

## Frontend Pattern Notes
- Celestial theme animations and gradients are implemented via shared utility classes in `frontend/src/index.css` (for example, orbiting particles, glow effects, and parallax layers). Reuse these utilities instead of defining component-local `@keyframes` or duplicating animation logic.

## Custom Agents

All agents live in `.github/agents/`. The repository includes both **Spec Kit pipeline agents** and **utility agents**:

### Spec Kit Pipeline Agents
| Agent | Purpose |
|-------|---------|
| `speckit.specify` | Feature specification from issue description |
| `speckit.plan` | Implementation plan with research and data model |
| `speckit.tasks` | Actionable task list from spec + plan |
| `speckit.implement` | Code implementation from tasks |
| `speckit.clarify` | Identify underspecified areas in a spec |
| `speckit.analyze` | Cross-artifact consistency analysis |
| `speckit.checklist` | Custom checklist generation |
| `speckit.constitution` | Project constitution management |
| `speckit.taskstoissues` | Convert tasks to GitHub issues |

### Utility Agents
| Agent | Purpose |
|-------|---------|
| `architect` | Generates Azure IaC (Bicep), `azd` scaffolds, architecture diagrams, and deploy buttons. Always runs for new apps. |
| `archivist` | Updates documentation and README to match code changes |
| `designer` | Creates or refines design assets scoped to changes |
| `devops` | Diagnoses CI failures, resolves targeted pipeline issues, and helps restore broken checks |
| `judge` | Triages PR review comments and applies justified changes |
| `linter` | Runs linting, tests, CI steps, and resolves errors |
| `quality-assurance` | Scoped quality improvements and defect fixes |
| `tester` | Adds tests for changed behavior and improves testability |

### MCP Configuration
- `.github/agents/mcp.json` — Declares MCP servers available to remote GitHub Custom Agents (Context7 for documentation lookup, Azure MCP for resource schema lookups and Well-Architected Framework guidance, and Bicep MCP for Bicep best practices, resource type schemas, and Azure Verified Modules metadata).

### Agent Degradation Rules

When tools, context, or commands are unavailable, agents should degrade gracefully rather than fail silently or hallucinate:

- **MCP server fails to start**: Proceed without MCP-dependent context. Use file reads and search as fallback. Note the unavailability in output.
- **PR diff or branch info unavailable**: Fall back to local mode. Use `git diff` or `git log` to reconstruct the change set. If that also fails, ask the user to specify the scope.
- **Terminal commands fail repeatedly** (lint, test, build): Report the exact error output. Attempt the most common fix (missing dependencies → install, wrong directory → cd to correct path). After 2 failed retries, report the failure and continue with other phases rather than blocking entirely.
- **GitHub API unavailable**: If the agent cannot fetch PR metadata, review comments, or repo contents, switch to local file analysis and note the limitation.

### Agent Input Convention

All agent `.agent.md` files include a `$ARGUMENTS` block in their markdown body:

````markdown
## User Input

```text
$ARGUMENTS
```
````

`$ARGUMENTS` is replaced at invocation time with the user's input message. Agents must check this block before proceeding — it may scope the work to specific files, PRs, features, or constraints. New agents should include this block following the same pattern.

## MCP Presets

The Tools page exposes a **Preset Library** of built-in MCP server configurations. Presets are defined statically in `backend/src/services/tools/presets.py` and served via `GET /api/v1/tools/presets`.

| Preset | Type | Category | Description |
|--------|------|----------|-------------|
| GitHub MCP Server | HTTP | GitHub | Read-only GitHub MCP server |
| GitHub MCP Server (Full Access) | HTTP | GitHub | Full-access GitHub MCP server |
| Azure MCP | Local | Cloud | Azure-aware coding workflows |
| Sentry MCP | Local | Monitoring | Issue details and summaries |
| Cloudflare MCP | SSE | Cloud | Cloudflare docs and platform access |
| Azure DevOps MCP | Local | Cloud | Azure DevOps work items |
| Context7 | HTTP | Documentation | Up-to-date library docs and code examples |
| Code Graph Context | Local | Code Analysis | Code indexing, call chains, dead code detection |

## MCP Tool Usage Requirements

- Prefer Context7 when you need up-to-date library documentation and examples.
- Consider Code Graph Context for relationship-heavy codebase exploration when simple file/search reads are not enough.

Canonical versions live in `solune/backend/pyproject.toml`, `solune/frontend/package.json`, and `.github/workflows/ci.yml`. Prefer those files over copying long version snapshots into new docs or prompts.

## Active Technologies
- Python 3.11 (backend), TypeScript / React (frontend) + FastAPI, Pydantic (backend); React, Vite, Tailwind CSS, Radix UI, dnd-kit (frontend) (001-human-agent-delay-until-auto-merge)
- In-memory `PipelineState` dataclass (no database migration needed — `delay_seconds` stored in `PipelineAgentNode.config` dict) (001-human-agent-delay-until-auto-merge)
- Python 3.11 + FastAPI, httpx, pydantic, asyncio (770-auto-merge-devops-retry)
- PostgreSQL (via existing `chat_store`) + in-memory `BoundedDict` caches (770-auto-merge-devops-retry)

## Recent Changes
- 001-human-agent-delay-until-auto-merge: Added Python 3.11 (backend), TypeScript / React (frontend) + FastAPI, Pydantic (backend); React, Vite, Tailwind CSS, Radix UI, dnd-kit (frontend)
