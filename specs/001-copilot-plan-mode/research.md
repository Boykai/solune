# Research: Copilot-Style Planning Mode (v2)

**Branch**: `001-copilot-plan-mode` | **Date**: 2026-03-31 | **Spec**: [spec.md](spec.md)

## Research Tasks & Findings

### RT-01: Agent Session State for Mode Persistence

**Context**: FR-002 requires plan mode state to persist in the user's agent session so follow-up messages auto-route to the plan agent.

**Decision**: Store `is_plan_mode: bool` and `active_plan_id: str | None` in `AgentSession.state` dictionary.

**Rationale**: The existing `ChatAgentService` already injects runtime context into `agent_session.state` (keys: `project_name`, `project_id`, `available_tasks`, `available_statuses`, `github_token`, `session_id`, `pipeline_id`, `file_urls`). Adding two keys follows the established pattern with zero framework changes. The `run()` and `run_stream()` methods can check `agent_session.state.get("is_plan_mode")` before dispatching to either the standard agent or the plan-mode agent.

**Alternatives considered**:
- Separate `PlanSessionMapping` class — rejected: duplicates TTL/eviction logic and complicates the session lifecycle.
- Database-persisted mode flag — rejected: adds latency; the agent session is ephemeral and mode state should match its lifetime.
- URL query parameter on each request — rejected: leaks session state into the API surface; all follow-up routing should be implicit.

---

### RT-02: Plan Data Persistence (SQLite Schema)

**Context**: FR-003 requires plan records scoped to project/repo. FR-009/FR-010 require updating plans with GitHub issue data post-approval.

**Decision**: Create a `chat_plans` table with a companion `chat_plan_steps` table. Use migration `035_chat_plans.sql`.

**Rationale**: The existing persistence pattern uses `aiosqlite` with WAL mode, `aiosqlite.Row` factory, and the `transaction()` context manager for writes. The `chat_store.py` module already handles `chat_messages`, `chat_proposals`, and `chat_recommendations` with identical CRUD patterns. Plans require a parent-child relationship (Plan → PlanStep), which maps cleanly to two tables joined by `plan_id`. The latest migration is `034_phase8_recovery_log.sql`, so the next sequential number is 035.

**Alternatives considered**:
- Single table with JSON steps column — rejected: complicates individual step updates (issue number/URL after approval) and prevents step-level queries.
- Storing plans in `chat_messages.action_data` — rejected: plans are first-class entities with their own lifecycle; embedding them in messages would conflate message persistence with plan state management.
- Using a separate database file — rejected: adds connection management overhead and breaks the single-database design.

---

### RT-03: Plan Agent System Prompt Design

**Context**: Plan-mode requires a specialized system prompt with project/repo context (FR-001, FR-004, FR-014).

**Decision**: Create `backend/src/prompts/plan_instructions.py` with `build_plan_instructions(project_name, project_id, repo_owner, repo_name, available_statuses)`.

**Rationale**: The existing `agent_instructions.py` provides `build_system_instructions(project_name, available_statuses)` as the pattern. The plan prompt needs additional repo context (owner/name) and fundamentally different behavioral instructions (research → plan → refine cycle). Keeping it in a separate module follows the existing prompt organization (`agent_instructions.py`, `task_generation.py`, `issue_generation.py`, `transcript_analysis.py`).

**Alternatives considered**:
- Appending plan mode instructions to the existing `AGENT_SYSTEM_INSTRUCTIONS` — rejected: the plan agent has a completely different decision tree and toolset; mixing them would create ambiguity.
- Dynamic prompt switching within `build_system_instructions` based on a mode flag — rejected: violates single-responsibility; the function signature would bloat to accommodate all modes.

---

### RT-04: Read-Only Toolset for Plan Mode

**Context**: FR-014 mandates restricting the agent to read-only operations plus a plan-saving capability during plan mode.

**Decision**: Create `register_plan_tools()` in `agent_tools.py` that returns a restricted set: `get_project_context`, `get_pipeline_list`, and a new `save_plan` tool. The `save_plan` tool persists/updates the plan via `chat_store.py`.

**Rationale**: The existing `register_tools()` returns all 11 tools. Plan mode should not expose `create_task_proposal`, `update_task_status`, `create_project_issue`, `launch_pipeline`, or other write tools. The `@tool` decorator pattern makes it trivial to define a new `save_plan` function and register a subset. The `ChatAgentService` can conditionally use `register_plan_tools()` when `is_plan_mode` is set.

**Alternatives considered**:
- Runtime tool filtering (register all, strip at call time) — rejected: the agent LLM would still see the tool schemas and might attempt to call them, wasting tokens and causing errors.
- MCP-based plan tools — rejected: overengineered for a single save operation; MCP is designed for external service integrations.

---

### RT-05: SSE Thinking Events

**Context**: FR-006/FR-007 require real-time phase indicators during plan processing.

**Decision**: Emit a new `thinking` SSE event type: `{"event": "thinking", "data": {"phase": "researching"|"planning"|"refining", "detail": "..."}}` from `run_plan_stream()`.

**Rationale**: The existing SSE protocol emits `token`, `tool_call`, `tool_result`, `done`, and `error` events. Adding a `thinking` event type follows the same `{"event": ..., "data": ...}` structure. The `EventSourceResponse` in `chat.py` already handles arbitrary event dicts via `async def event_generator()`. The frontend SSE parser processes frames by checking `eventType` and can add a new branch for `thinking`.

**Alternatives considered**:
- Embedding thinking data in `token` events — rejected: would require the frontend to parse content for embedded JSON, mixing structured events with freeform text.
- WebSocket upgrade — rejected: the existing SSE infrastructure works well and WebSocket adds connection management complexity.
- Polling endpoint — rejected: defeats the purpose of real-time feedback.

---

### RT-06: Plan → GitHub Issues Service

**Context**: FR-008, FR-009, FR-010, FR-018 require creating a parent issue + sub-issues on approval.

**Decision**: Create `backend/src/services/plan_issue_service.py` with `create_plan_issues(access_token, plan, owner, repo)` that: (1) creates the parent issue with title, summary, and checklist body; (2) creates sub-issues per step with dependency references; (3) updates the plan record with issue numbers/URLs.

**Rationale**: The existing `create_project_issue` tool in `agent_tools.py` already calls the GitHub Issues API via `githubkit`. The plan issue service follows the same pattern but orchestrates multiple sequential API calls. The service layer (not the agent tool) handles this because approval is a user-initiated action (via API endpoint), not an agent decision.

**Alternatives considered**:
- Creating all issues in parallel — rejected: sub-issues need to reference the parent issue number in their body, and cross-references between steps require sequential creation.
- Using GitHub Projects API instead of Issues API — rejected: the spec explicitly requires issues; the pipeline system handles project board integration separately.
- Background job queue — rejected: adds infrastructure complexity; sequential issue creation for up to 20 steps (SC-004: within 60 seconds) is well within synchronous API call bounds.

---

### RT-07: Frontend Plan Types and SSE Extensions

**Context**: Plan and ThinkingEvent types needed in `types/index.ts`; SSE parser in `api.ts` needs `thinking` event handling.

**Decision**: Add `PlanStatus`, `Plan`, `PlanStep`, `ThinkingEvent`, and `ThinkingPhase` types to `index.ts`. Add `PLAN_CREATE` to the `ActionType` union. Extend `sendMessageStream` with an `onThinking` callback parameter.

**Rationale**: The existing type system uses string literal unions for enums (`SenderType`, `ActionType`, `ProposalStatus`) and interfaces for data models. The SSE parser uses callbacks (`onToken`, `onDone`, `onError`); adding `onThinking` follows the same pattern. The `processFrame` switch logic extends cleanly.

**Alternatives considered**:
- Separate types file for plan types — rejected: all chat-related types live in `types/index.ts`; splitting would break the convention.
- Generic event callback instead of typed `onThinking` — rejected: loses type safety and requires consumers to parse event types manually.

---

### RT-08: Frontend Components (PlanPreview, ThinkingIndicator)

**Context**: FR-007, FR-012, FR-013, FR-016, FR-017 require rich UI components for plan display and thinking indicators.

**Decision**: Create `PlanPreview.tsx` and `ThinkingIndicator.tsx` in `components/chat/`. Wire `PlanPreview` into `MessageBubble.tsx` (renders when `action_type === 'plan_create'`). Wire `ThinkingIndicator` into `ChatInterface.tsx` (replaces bounce dots when `thinkingPhase` is set). Create `usePlan.ts` hook for plan state management.

**Rationale**: The existing chat components follow a clear pattern: `TaskPreview`, `StatusChangePreview`, `IssueRecommendationPreview` all render conditionally in the message list based on `action_type`. The `ChatInterface.tsx` manages all preview state via props. Adding `PlanPreview` follows this established pattern exactly.

**Alternatives considered**:
- Full-page plan view (not in chat) — rejected: the spec requires plans to appear in-chat as preview cards.
- Modal-based plan display — rejected: modals block chat interaction; the spec requires iterative refinement via follow-up messages while the plan is visible.
- Zustand/Redux for plan state — rejected: the existing app uses React Query + component state; introducing a new state library for one feature is unnecessary.

---

### RT-09: Plan Mode API Endpoints

**Context**: The spec requires route `/plan`, plus plan management endpoints (GET, PATCH, approve, exit).

**Decision**: Add endpoints to `backend/src/api/chat.py`:
- `POST /messages/plan` — enter plan mode (triggers `run_plan()`)
- `POST /messages/plan/stream` — enter plan mode with SSE streaming
- `GET /plans/{plan_id}` — retrieve a specific plan
- `PATCH /plans/{plan_id}` — update plan metadata
- `POST /plans/{plan_id}/approve` — approve and create GitHub issues
- `POST /plans/{plan_id}/exit` — exit plan mode

**Rationale**: The existing chat API lives in `api/chat.py` with the FastAPI router prefix `/api/v1/chat`. Adding plan endpoints under this router keeps the API surface consistent. The `/messages/plan` path mirrors the existing `/messages` and `/messages/stream` pattern. Plan lifecycle endpoints (`/plans/{id}/...`) are resource-oriented REST.

**Alternatives considered**:
- Separate `api/plans.py` router — viable but rejected for v1: plan mode is tightly coupled to chat sessions; colocation improves discoverability and shares auth dependencies.
- Using the existing `/messages` endpoint with a `/plan` prefix detection — rejected: mixing command parsing into the message handler adds complexity; explicit endpoints are clearer.

---

### RT-10: Dependency Management & Testing Strategy

**Context**: No new external dependencies are needed. All functionality builds on existing libraries.

**Decision**: No new pip or npm packages required.

**Rationale**: 
- **Backend**: `aiosqlite`, `githubkit`, `sse-starlette`, `agent-framework-*`, and `pydantic` already cover all needs (database, GitHub API, SSE, agent orchestration, data validation).
- **Frontend**: `react`, `@tanstack/react-query`, `lucide-react` (icons), `tailwindcss`, and existing UI primitives cover all component and state management needs.
- **Testing**: `pytest` + `pytest-asyncio` (backend), `vitest` + `@testing-library/react` (frontend) are already set up.

**Alternatives considered**: N/A — no gaps in the dependency graph.
