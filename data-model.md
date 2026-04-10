# Data Model: Harden Phase 3 — Code Quality & Tech Debt

**Feature**: Harden Phase 3 | **Date**: 2026-04-10 | **Plan**: [plan.md](plan.md)

## Overview

Phase 3 is a hardening sprint — no new entities, tables, or schemas are introduced. This document captures the existing data structures affected by the refactoring workstreams.

## Affected Models

### 3.1 — GitHubProjectsService (DI Refactor)

**Entity**: `GitHubProjectsService` (class in `services/github_projects/service.py`)

| Attribute | Type | Role |
|-----------|------|------|
| `_inflight_graphql` | `dict[str, asyncio.Task]` | Request deduplication cache |
| `_rate_limit_*` | Various | Rate limit tracking state |

**State**: Singleton instance. Currently module-level (`github_projects_service`), also registered on `app.state.github_service`.

**Relationship**: Used by 27 files via direct import; should be accessed via `get_github_service()` accessor after refactor.

**Validation Rules**: No changes. The service is stateless in terms of persistent data; its in-memory caches are transient.

---

### 3.2 — Dependency Package Models

No data model changes. Package upgrades may introduce new type signatures or async patterns in:

- `azure-ai-inference` client models
- `agent-framework-*` session/agent models
- `github-copilot-sdk` / `copilot-sdk` authentication models
- `opentelemetry-instrumentation-*` span/metric models

These are external library types — any breaking changes will be surfaced by existing tests and type checking.

---

### 3.3 — Stryker Config (Frontend)

**Entity**: Stryker configuration object (JavaScript export)

| Field | Type | Before | After |
|-------|------|--------|-------|
| `mutate` | `string[]` | Hardcoded per file | Shard-selected via env var |
| `htmlReporter.fileName` | `string` | Hardcoded per file | Shard-selected via env var |

**State Transition**: 5 files → 1 file. Shard selection driven by `STRYKER_SHARD` env var.

---

### 3.4 — Chat Message Persistence (Verification Only)

**Entity**: `ChatMessage` (Pydantic model in `models/chat.py`)

| Field | Type | Role |
|-------|------|------|
| `session_id` | `UUID` | Links message to chat session |
| `sender_type` | `SenderType` | USER or ASSISTANT |
| `content` | `str` | Message text |

**Persistence Flow** (plan-mode, already correct):

```text
1. Request arrives at POST /messages/plan
2. get_chat_agent_service() → if fails, return 503 (no message persisted)
3. Create ChatMessage(sender_type=USER)
4. add_message() → persist to SQLite
5. Run plan agent → get response
6. add_message() → persist assistant response
```

No schema or model changes required.
