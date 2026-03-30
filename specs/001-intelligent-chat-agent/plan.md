# Implementation Plan: Complete v0.2.0 — Intelligent Chat Agent

**Branch**: `001-intelligent-chat-agent` | **Date**: 2026-03-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-intelligent-chat-agent/spec.md`

## Summary

Complete the remaining v0.2.0 features for the Intelligent Chat Agent built on the Microsoft Agent Framework. The existing infrastructure includes a working `ChatAgentService` with `GitHubCopilotAgent`, 7 registered `@tool` functions, SQLite-backed session management, and streaming SSE responses. This plan adds 4 new agent tools (difficulty assessment, pipeline preset selection, project issue creation, pipeline launch), wires them into existing services (`PipelineService`, `GitHubProjectsService`), adds an opt-in autonomous creation config, handles the new `PIPELINE_LAUNCH` action type, and lays the MCP tool extensibility foundation by dynamically loading project-configured MCP servers into the agent runtime.

## Technical Context

**Language/Version**: Python >=3.12
**Primary Dependencies**: FastAPI >=0.135.0, agent-framework-core >=1.0.0b1, agent-framework-github-copilot >=1.0.0b1, pydantic >=2.12.0, aiosqlite >=0.22.0, githubkit >=0.14.6, sse-starlette >=3.0.0
**Storage**: SQLite via aiosqlite (settings.db — sessions, pipeline configs, MCP tool configs)
**Testing**: pytest >=9.0.0, pytest-asyncio >=1.3.0, ruff >=0.15.0 (lint/format), pyright >=1.1.408 (type check)
**Target Platform**: Linux server (Docker container, `docker-compose.yml`)
**Project Type**: Web application (backend + frontend monorepo)
**Performance Goals**: MCP tool loading adds <2s to agent initialization (SC-006); full assess→select→create→launch workflow completes <5 minutes (SC-001)
**Constraints**: SSE streaming must support 4+ sequential tool calls; autonomous creation opt-in (default disabled); no changes to pipeline engine or GitHub API layer
**Scale/Scope**: 90+ existing tests, 7 existing agent tools → 11 tools, 4 ActionType values → 5

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Specification-First Development — ✅ PASS

Feature spec (`spec.md`) contains prioritized user stories (P1: Difficulty Assessment, P2: Autonomous Creation, P3: MCP Extensibility) with Given-When-Then acceptance scenarios, clear scope boundaries, and independent testing criteria.

### II. Template-Driven Workflow — ✅ PASS

All artifacts follow canonical templates from `.specify/templates/`. This plan follows `plan-template.md`. Generated artifacts (research.md, data-model.md, contracts/, quickstart.md) follow standard formats.

### III. Agent-Orchestrated Execution — ✅ PASS

Workflow decomposes into single-responsibility phases: specify → plan → tasks → implement. Each agent operates on well-defined inputs (previous phase artifacts) and produces specific outputs.

### IV. Test Optionality with Clarity — ✅ PASS

Unit tests are included because: (1) the feature spec explicitly requires tests in the verification section, (2) the parent issue specifies unit tests for all new tools and response handling, and (3) existing test infrastructure covers all modified files. Tests follow existing patterns in `test_agent_tools.py` and `test_chat_agent.py`.

### V. Simplicity and DRY — ✅ PASS

All 4 new tools reuse existing services (`PipelineService.get_presets()`, `GitHubProjectsService.create_issue()`, pipeline launch logic). No new abstractions introduced — tools follow the established `@tool` → `ToolResult` pattern. Difficulty-to-preset mapping is a simple deterministic dict. MCP loading converts existing `McpToolConfig` model to agent-compatible format.

## Project Structure

### Documentation (this feature)

```text
specs/001-intelligent-chat-agent/
├── plan.md              # This file
├── research.md          # Phase 0 output — resolved technical decisions
├── data-model.md        # Phase 1 output — entity definitions
├── quickstart.md        # Phase 1 output — getting started guide
├── contracts/           # Phase 1 output — API contracts for new tools
│   └── tool-contracts.yaml
└── tasks.md             # Phase 2 output (created by /speckit.tasks — NOT this phase)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   └── chat.py                          # No changes (reuses existing endpoints)
│   │   ├── models/
│   │   │   ├── chat.py                          # + PIPELINE_LAUNCH ActionType
│   │   │   └── tools.py                         # Existing McpToolConfig (no changes)
│   │   ├── prompts/
│   │   │   └── agent_instructions.py            # + Difficulty workflow + autonomous instructions
│   │   ├── services/
│   │   │   ├── agent_tools.py                   # + 4 new tools + load_mcp_tools()
│   │   │   ├── agent_provider.py                # + mcp_servers parameter
│   │   │   ├── chat_agent.py                    # + pipeline_launch handling + MCP wiring
│   │   │   ├── pipelines/
│   │   │   │   └── service.py                   # No changes (reuse get_presets())
│   │   │   └── github_projects/
│   │   │       └── issues.py                    # No changes (reuse create_issue())
│   │   └── config.py                            # + CHAT_AUTO_CREATE_ENABLED setting
│   └── tests/
│       └── unit/
│           ├── test_agent_tools.py              # + Tests for 4 new tools + MCP loading
│           └── test_chat_agent.py               # + Tests for pipeline_launch response
└── frontend/                                    # No changes (existing chat UI handles actions)
```

**Structure Decision**: Web application layout. Changes are backend-only — 8 files modified, 0 files created (all changes extend existing files). Frontend requires no changes because the existing chat UI already handles action_type/action_data responses generically.

## Constitution Check — Post-Design Re-evaluation

*Re-evaluated after Phase 1 design artifacts (research.md, data-model.md, contracts/, quickstart.md) are complete.*

### I. Specification-First Development — ✅ PASS (unchanged)

All design artifacts trace back to spec.md user stories and acceptance scenarios. Tool contracts map to functional requirements (FR-001 through FR-013).

### II. Template-Driven Workflow — ✅ PASS (unchanged)

All artifacts follow canonical templates. plan.md follows plan-template.md structure. Contracts use YAML schema format.

### III. Agent-Orchestrated Execution — ✅ PASS (unchanged)

Phase boundaries are clear: plan (this phase) → tasks (next phase) → implement. Artifacts are immutable once handed off.

### IV. Test Optionality with Clarity — ✅ PASS (unchanged)

Tests are required per spec verification section. Test patterns are documented in quickstart.md and follow existing test infrastructure in test_agent_tools.py and test_chat_agent.py.

### V. Simplicity and DRY — ✅ PASS (confirmed)

Post-design review confirms: 4 new tools follow the exact same `@tool` → `ToolResult` pattern as 7 existing tools. Difficulty mapping is a 5-entry dict. MCP loading is a query + dict conversion. No new abstractions, no new patterns, no unnecessary complexity.

## Complexity Tracking

> No constitution violations identified. All changes follow existing patterns (DRY), reuse existing services (YAGNI), and stay within the established architecture.
