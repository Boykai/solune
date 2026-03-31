# Implementation Plan: Solune MCP Server

**Branch**: `001-mcp-server` | **Date**: 2026-03-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-mcp-server/spec.md`

## Summary

Expose Solune's capabilities as an MCP (Model Context Protocol) server using the `mcp` Python SDK's `FastMCP` class, mounted directly into the existing FastAPI app at `/api/v1/mcp` via Starlette ASGI mount. The server uses Streamable HTTP transport (the MCP-recommended production transport) with GitHub PAT token verification for authentication. The same backend service layer that powers the REST API and internal `@tool` functions becomes the shared implementation — single source of truth. This enables external AI agents (VS Code Copilot, Claude Desktop, custom MCP clients) to discover and invoke Solune's project management, pipeline orchestration, and agent tools via the standard MCP protocol.

## Technical Context

**Language/Version**: Python ≥3.12 (targets 3.13 for ruff/pyright, 3.14-slim in Docker)
**Primary Dependencies**: FastAPI ≥0.135.0, mcp ≥1.26.0 (new), httpx ≥0.28.0, pydantic ≥2.12.0, aiosqlite ≥0.22.0
**Storage**: SQLite via aiosqlite (existing `settings.db`; pipeline states, MCP configs, session data)
**Testing**: pytest with pytest-asyncio (asyncio_mode="auto"), pytest-cov (75% threshold), ruff + pyright for linting
**Target Platform**: Linux server (Docker, 3.14-slim base image)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: MCP tool call round-trip <5 seconds end-to-end (SC-001); resource subscription notifications within 2 seconds of data change (SC-006)
**Constraints**: In-process mount (no separate server), shared DB/services with existing FastAPI app, token cache TTL 60s
**Scale/Scope**: ~22 MCP tools (12 Tier 1 + 10 Tier 2), 3 resource templates, 3 prompt templates, ~10 new source files, ~6 new test files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate (Phase 0 Entry)

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Specification-First | ✅ PASS | `spec.md` exists with 6 prioritized user stories (P1–P3), Given-When-Then acceptance scenarios, edge cases, 39 functional requirements, and 10 success criteria |
| II. Template-Driven Workflow | ✅ PASS | Plan follows canonical `plan-template.md`; spec follows spec template. All artifacts use standard structure |
| III. Agent-Orchestrated Execution | ✅ PASS | Work decomposed via speckit agents (specify → plan → tasks → implement). Single-responsibility maintained |
| IV. Test Optionality | ✅ PASS | Spec does not mandate TDD. Tests are planned as Phase 9 (unit + integration) per issue description but are not required by spec. Will include tests for auth and core tools per best practice |
| V. Simplicity and DRY | ✅ PASS | MCP tools delegate to existing service layer — no business logic duplication. Single source of truth pattern explicitly required (FR-038, FR-039) |

**Gate Result**: ✅ ALL PASS — proceed to Phase 0 research.

### Post-Design Gate (Phase 1 Exit) — Re-evaluated

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Specification-First | ✅ PASS | All design artifacts trace back to spec user stories and functional requirements |
| II. Template-Driven Workflow | ✅ PASS | Plan, research, data-model, contracts, quickstart all follow template structure |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan designed for task decomposition by `/speckit.tasks` agent |
| IV. Test Optionality | ✅ PASS | Tests planned for auth (security-critical) and core tools (correctness-critical) — justified, not mandated globally |
| V. Simplicity and DRY | ✅ PASS | All tools delegate to existing services. New abstractions limited to MCP server wrapper, auth verifier, and context dataclass — all justified by the MCP SDK integration requirements |

**Gate Result**: ✅ ALL PASS — ready for `/speckit.tasks`.

## Project Structure

### Documentation (this feature)

```text
specs/001-mcp-server/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── mcp-tools.yaml   # MCP tool schemas (OpenAPI-style)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── config.py                          # + mcp_server_enabled, mcp_server_name settings
│   ├── main.py                            # + MCP server mount, session manager lifespan
│   └── services/
│       └── mcp_server/                    # NEW: MCP server package
│           ├── __init__.py                # Exports: create_mcp_server(), get_mcp_app()
│           ├── server.py                  # FastMCP instance creation + tool registration
│           ├── auth.py                    # GitHubTokenVerifier — PAT verification + caching
│           ├── context.py                 # McpContext dataclass — per-request auth context
│           ├── resources.py               # MCP resource templates (pipelines, board, activity)
│           ├── prompts.py                 # MCP prompt templates (create-project, etc.)
│           └── tools/                     # MCP tool modules by domain
│               ├── __init__.py
│               ├── projects.py            # list_projects, get_project, get_board, get_project_tasks
│               ├── tasks.py               # create_task, create_issue
│               ├── pipelines.py           # list_pipelines, launch_pipeline, get_pipeline_states, retry_pipeline
│               ├── activity.py            # get_activity, update_item_status
│               ├── agents.py              # list_agents, create_agent
│               ├── apps.py                # list_apps, get_app_status, create_app
│               ├── chores.py              # list_chores, trigger_chore
│               └── chat.py                # send_chat_message, get_metadata, cleanup_preflight
├── tests/
│   ├── unit/
│   │   └── test_mcp_server/              # NEW: MCP server unit tests
│   │       ├── __init__.py
│   │       ├── test_auth.py              # Token verification, caching, rate limiting
│   │       ├── test_tools_projects.py    # Project/board tools (mock services)
│   │       └── test_tools_pipelines.py   # Pipeline tools (mock services)
│   └── integration/
│       └── test_mcp_e2e.py               # MCP client↔server lifecycle
├── pyproject.toml                         # + mcp>=1.26.0,<2 dependency
└── .vscode/mcp.json                       # + Solune MCP server entry for local dev
```

**Structure Decision**: Existing web application structure (`solune/backend/` + `solune/frontend/`). New code lives entirely within `solune/backend/src/services/mcp_server/` as a self-contained package. Only `config.py` and `main.py` are modified in the existing codebase. All MCP tools delegate to existing services — no modifications to the service layer itself.

## Complexity Tracking

> No constitution violations. All complexity is justified by the MCP SDK integration requirements.

| Decision | Justification | Simpler Alternative Rejected Because |
|----------|--------------|-------------------------------------|
| New `mcp_server/` package (10 files) | MCP SDK requires dedicated server instance, auth verifier, tool registration, resources, and prompts | Inlining into existing api/ would violate separation of concerns and make the feature flag toggle complex |
| Token caching (dict with TTL) | FR-007 requires 60s cache to avoid per-request GitHub API calls | No caching would cause 1 GitHub API call per tool invocation — unacceptable latency and rate limit risk |
| Per-tool project access validation | FR-008 requires access scoping on every project-scoped tool | Global middleware cannot inspect tool parameters to extract project_id |
