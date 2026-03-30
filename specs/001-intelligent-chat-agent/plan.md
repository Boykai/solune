# Implementation Plan: Intelligent Chat Agent (Microsoft Agent Framework)

**Branch**: `001-intelligent-chat-agent` | **Date**: 2026-03-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-intelligent-chat-agent/spec.md`

## Summary

Replace the hardcoded priority-dispatch cascade in `chat.py` with a Microsoft Agent Framework Agent that uses function tools for action selection, `AgentSession` for multi-turn memory, and middleware for logging/security. The agent reasons about user intent and selects the appropriate tool (task creation, issue recommendation, status change, transcript analysis, clarifying questions) instead of following a rigid if/elif chain. The REST API contract (`ChatMessage` schema) stays unchanged. A new SSE streaming endpoint provides progressive token delivery. The existing `AIAgentService` and `CompletionProvider` layers are deprecated (not deleted) with warnings for removal in v0.3.0.

## Technical Context

**Language/Version**: Python ≥3.12 (backend), TypeScript + React 18 (frontend)
**Primary Dependencies**: FastAPI 0.135+, Pydantic 2.12+, agent-framework-core (preview), agent-framework-azure-ai (preview), agent-framework-github-copilot (preview), sse-starlette (SSE support)
**Storage**: SQLite via aiosqlite 0.22+ (source of truth for conversation history, unchanged)
**Testing**: pytest + pytest-asyncio (backend), Vitest + React Testing Library (frontend)
**Target Platform**: Linux server (Docker), modern browsers (frontend)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: Streaming first token within 2 seconds; non-streaming responses comparable to current latency
**Constraints**: ChatMessage schema unchanged (backward-compatible); `ai_enhance=False` bypass preserved; SQLite remains canonical store
**Scale/Scope**: Single-tenant deployment; existing user base; 6 user stories (P1×2, P2×2, P3×2)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Specification-First** | ✅ PASS | `spec.md` contains 6 prioritized user stories (P1–P3) with Given-When-Then acceptance scenarios, edge cases, 21 functional requirements, and success criteria |
| **II. Template-Driven** | ✅ PASS | All artifacts follow canonical templates (`spec-template.md`, `plan-template.md`) |
| **III. Agent-Orchestrated** | ✅ PASS | Work is decomposed via speckit agents (specify → plan → tasks → implement) with clear handoffs |
| **IV. Test Optionality** | ✅ PASS | Tests are included as mandated by spec (FR requires existing tests to pass; new tests for agent tools and chat agent service are specified in Steps 10) |
| **V. Simplicity & DRY** | ✅ PASS | Agent replaces complex priority cascade with a single dispatch; tools reuse existing business logic; deprecate-don't-delete avoids premature cleanup |

**Pre-Design Gate**: PASSED — no violations. Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-intelligent-chat-agent/
├── plan.md              # This file
├── research.md          # Phase 0 output — technology decisions & research
├── data-model.md        # Phase 1 output — entity definitions & relationships
├── quickstart.md        # Phase 1 output — developer setup guide
├── contracts/           # Phase 1 output — API endpoint contracts
│   └── chat-api.yaml   # OpenAPI 3.1 spec for chat endpoints
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── api/
│   │   └── chat.py                    # MODIFY — replace dispatch cascade with agent call; add streaming endpoint
│   ├── services/
│   │   ├── agent_tools.py             # CREATE — @tool-decorated functions for agent actions
│   │   ├── agent_provider.py          # CREATE — factory for Copilot/Azure OpenAI agent backends
│   │   ├── chat_agent.py              # CREATE — ChatAgentService wrapping Agent + session management
│   │   ├── agent_middleware.py        # CREATE — logging & security middleware
│   │   ├── ai_agent.py               # DEPRECATE — add deprecation warnings, keep identify_target_task()
│   │   ├── completion_providers.py    # DEPRECATE — add deprecation warnings
│   │   └── signal_chat.py            # MODIFY — use ChatAgentService.run() instead of direct ai_service calls
│   ├── prompts/
│   │   ├── agent_instructions.py      # CREATE — single comprehensive agent system prompt
│   │   ├── task_generation.py         # DEPRECATE — add deprecation warnings
│   │   ├── issue_generation.py        # DEPRECATE — add deprecation warnings
│   │   └── transcript_analysis.py     # DEPRECATE — add deprecation warnings
│   ├── models/
│   │   └── chat.py                    # No schema changes (ChatMessage, ActionType unchanged)
│   └── config.py                      # MODIFY — add agent framework config settings
├── tests/
│   └── unit/
│       ├── test_agent_tools.py        # CREATE — tool function tests with mocked context
│       ├── test_chat_agent.py         # CREATE — ChatAgentService tests
│       └── test_api_chat.py           # MODIFY — update mock targets to chat_agent_service
└── pyproject.toml                     # MODIFY — add agent-framework packages, sse-starlette

solune/frontend/
├── src/
│   ├── services/
│   │   └── api.ts                     # MODIFY — add streaming endpoint support via ReadableStream
│   └── components/
│       └── chat/
│           └── ChatInterface.tsx      # MODIFY — progressive rendering with streaming fallback
└── package.json                       # No changes expected (no new npm dependencies)
```

**Structure Decision**: Existing web application structure (backend/ + frontend/ under `solune/`). All new backend files are placed in existing `src/services/` and `src/prompts/` directories following established patterns. No new top-level directories needed.

## Complexity Tracking

> No violations found in Constitution Check. No entries needed.
