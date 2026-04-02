# Documentation Owners

> **Internal document** — This file is for project maintainers. It defines documentation ownership and review cadences. If you're looking for user-facing documentation, see the [main README](../README.md).

Each doc file has a designated owner responsible for keeping it accurate. Owners must review relevant PRs and perform the weekly staleness sweep on their files.

| File | Owner | Key Things to Verify |
|------|-------|----------------------|
| `docs/setup.md` | Infra / DX lead | Prerequisites, Codespaces flow, env var list, Docker Compose steps |
| `docs/configuration.md` | Backend lead | All env vars, types, defaults, and validation rules |
| `docs/api-reference.md` | Backend lead | All routes, methods, params, auth requirements, and response shapes |
| `docs/architecture.md` | Tech lead | Service diagram, data flow, WebSocket flow, AI provider list |
| `docs/agent-pipeline.md` | Backend lead | Workflow orchestrator modules, Copilot polling, task/issue generation |
| `docs/custom-agents-best-practices.md` | Backend lead | Agent authoring patterns, extension points |
| `docs/signal-integration.md` | Backend lead | Signal sidecar setup, webhook flow, delivery logic |
| `docs/testing.md` | QA / full-stack lead | Test commands, coverage targets, Playwright setup, CI behavior |
| `docs/troubleshooting.md` | Rotating (whoever fixed the bug documents the fix) | Common errors and resolutions — remove fixed issues, add new ones |
| `docs/project-structure.md` | Full-stack lead | Directory layout — update after any structural refactor |
| `docs/checklists/weekly-sweep.md` | Rotating dev | Weekly staleness sweep checklist — API, config, setup accuracy |
| `docs/checklists/monthly-review.md` | Tech lead | Monthly full documentation review checklist |
| `docs/checklists/quarterly-audit.md` | Tech lead | Quarterly architecture audit checklist |
| `docs/decisions/` | Tech lead | ADRs — one per significant architectural decision |
| `frontend/docs/findings-log.md` | Frontend lead | Component findings and decisions log |
| `docs/.last-refresh` | Rotating dev | Bi-weekly refresh baseline (date, SHA, updated docs) |
| `docs/.change-manifest.md` | Rotating dev | Change manifest compiled during each refresh cycle |

## Review Cadence

| Cadence | Scope | Owner |
|---------|-------|-------|
| Every PR | Files changed by the PR | PR author |
| Weekly (~30 min) | `api-reference.md`, `configuration.md`, `setup.md` | Rotating dev |
| Bi-weekly (~3–4 hours) | Full documentation refresh cycle (detect changes, prioritize, rewrite) | Rotating dev |
| Monthly (~2–3 hours) | All `docs/` files | Tech lead sign-off |
| Quarterly (~half day) | `architecture.md`, `docs/decisions/` | Tech lead |

## Doc-to-Source Mapping

> Used during the Librarian refresh process (Phase 4) to verify each documentation file against its source of truth. See [`specs/003-librarian/quickstart.md`](../../specs/003-librarian/quickstart.md) for execution guidance.

| Doc File | Source Type | Source Paths | Diff Method |
|----------|-------------|--------------|-------------|
| `docs/api-reference.md` | Routes | `backend/src/api/*.py` | List `@router.*` decorators → compare to documented endpoints |
| `docs/configuration.md` | Config schema | `backend/src/config.py`, `.env.example` | Extract config keys (`os.getenv`, `Settings.*`) → compare to doc |
| `docs/architecture.md` | Module structure | `backend/src/`, `docker-compose.yml` | List top-level modules + deployment topology → compare to doc |
| `docs/setup.md` | Dependency manifest | `backend/pyproject.toml`, `frontend/package.json`, `backend/Dockerfile`, `frontend/Dockerfile` | Run setup steps from scratch → note any failures or drift |
| `docs/pages/*.md` | Feature code | `frontend/src/pages/*.tsx` | Walk each page in running app → compare to doc |
| `docs/agent-pipeline.md` | Feature code | `backend/src/services/workflow_orchestrator/` | Trace pipeline execution flow → compare to doc |
| `docs/signal-integration.md` | Feature code | `backend/src/services/signal_bridge.py` | Review Signal integration implementation → compare to doc |
| `docs/testing.md` | Module structure | `tests/`, `../.github/workflows/ci.yml` | List test commands + coverage targets → compare to doc |
| `docs/troubleshooting.md` | Bug fixes | Recent closed issues, `git log` | Review recent fixes → update entries, prune resolved |
| `docs/project-structure.md` | Module structure | Repository filesystem | `tree` output → compare to doc directory map |
| `README.md` | All types | All sources | Holistic review against running application |
