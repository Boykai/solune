# Implementation Plan: Multi-Chat App Page

**Branch**: `copilot/speckit-plan-multi-chat-app-page` | **Date**: 2026-04-11 | **Spec**: [#1323](https://github.com/Boykai/solune/issues/1323)
**Input**: Parent issue #1323 — Transform AppPage (/) into multi-chat experience with side-by-side resizable panels and full backend conversation support.

## Summary

Transform the AppPage from a navigational landing page into a multi-conversation chat experience. Users open side-by-side resizable chat panels, each backed by an independent conversation. The backend adds a `conversations` table, a nullable `conversation_id` column on existing chat tables, and full CRUD endpoints. The existing `ChatPopup` on other pages is untouched—messages without a `conversation_id` continue to work as before.

| Phase | Scope | Key Output |
|-------|-------|------------|
| 1 | Backend — Conversation model, migration, CRUD, agent isolation | Migration `044_conversations.sql`, updated models/store/api/agent |
| 2 | Frontend — Types, schemas, API client | Updated `types/index.ts`, `schemas/chat.ts`, `services/api.ts` |
| 3 | Frontend — State management hooks | New `useConversations.ts`, `useChatPanels.ts`; updated `useChat.ts` |
| 4 | Frontend — AppPage UI components | New `ChatPanel.tsx`, `ChatPanelManager.tsx`; rewritten `AppPage.tsx` |
| 5 | Testing & verification | Updated `AppPage.test.tsx`, new component/hook tests, backend tests |

## Technical Context

**Language/Version**: Python ≥3.12 / TypeScript 5.x (pyright targets 3.13)
**Primary Dependencies**: FastAPI + aiosqlite + Pydantic v2 (backend); React 18 + @tanstack/react-query 5 + Zod 4 + Tailwind CSS 4 (frontend)
**Storage**: SQLite via aiosqlite — new `conversations` table; nullable `conversation_id` FK on `chat_messages`, `chat_proposals`, `chat_recommendations`
**Testing**: pytest with `asyncio_mode=auto` (backend, coverage ≥80%); Vitest (frontend, statements ≥60%)
**Target Platform**: Linux server (containerized backend), SPA in modern browsers (frontend)
**Project Type**: Web application (Python backend + TypeScript frontend)
**Performance Goals**: No measurable latency increase on existing endpoints; SSE streaming per-conversation
**Constraints**: Backward-compatible — `conversation_id` nullable everywhere; `ChatPopup` untouched; no breaking API changes
**Scale/Scope**: 1 migration, 4 backend files modified, 6 frontend files modified, 4 frontend files created

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Feature fully specified in parent issue #1323 with phases, decisions, and verification criteria |
| II. Template-Driven Workflow | ✅ PASS | This plan follows `plan-template.md`; supplementary artifacts generated per workflow |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan agent produces plan; implement agent will execute phased tasks |
| IV. Test Optionality | ✅ PASS | Tests explicitly requested in spec Phase 5; included for backend CRUD and frontend components |
| V. Simplicity and DRY | ✅ PASS | Reuses existing `ChatInterface` and `ChatPopup`; no new abstractions beyond `useChatPanels` for panel state |

**Gate Result**: PASS — no violations. Proceed to Phase 0.

### Post-Design Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | All design artifacts trace back to issue requirements |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates |
| III. Agent-Orchestrated Execution | ✅ PASS | Clear phase boundaries with explicit handoffs |
| IV. Test Optionality | ✅ PASS | Tests scoped to new behavior; existing tests preserved |
| V. Simplicity and DRY | ✅ PASS | No unnecessary abstractions; panel state is the minimum new complexity |

**Post-Design Gate Result**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
plan.md              # This file (speckit.plan output)
research.md          # Phase 0 output (technical decisions)
data-model.md        # Phase 1 output (entity definitions)
quickstart.md        # Phase 1 output (developer guide)
contracts/           # Phase 1 output (API specifications)
├── conversations-api.yaml
└── messages-api-updates.yaml
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── models/
│   │   └── chat.py                        # Add Conversation, ConversationCreateRequest, etc.
│   ├── services/
│   │   ├── chat_store.py                  # Add conversation CRUD; update message methods
│   │   └── chat_agent.py                  # Change session key to session_id:conversation_id
│   ├── api/
│   │   └── chat.py                        # Add conversation endpoints; update message endpoints
│   └── migrations/
│       └── 044_conversations.sql          # New conversations table + ALTER existing tables
└── tests/
    └── unit/
        ├── test_chat_store.py             # Conversation CRUD + message filtering tests
        └── test_chat_api.py               # Endpoint tests

solune/frontend/
├── src/
│   ├── types/
│   │   └── index.ts                       # Add Conversation interface
│   ├── services/
│   │   ├── schemas/
│   │   │   └── chat.ts                    # Add Conversation schemas
│   │   └── api.ts                         # Add conversationApi namespace
│   ├── hooks/
│   │   ├── useChat.ts                     # Accept optional conversationId
│   │   ├── useConversations.ts            # NEW: React Query conversation CRUD
│   │   └── useChatPanels.ts              # NEW: Panel layout state
│   ├── components/
│   │   └── chat/
│   │       ├── ChatPanel.tsx              # NEW: Single conversation panel
│   │       └── ChatPanelManager.tsx       # NEW: Multi-panel container
│   └── pages/
│       ├── AppPage.tsx                    # Rewrite: marketing → ChatPanelManager
│       └── AppPage.test.tsx               # Update tests for new layout
└── src/__tests__/
    ├── ChatPanel.test.tsx                 # NEW
    ├── ChatPanelManager.test.tsx          # NEW
    └── useConversations.test.ts           # NEW
```

**Structure Decision**: Existing web application structure (Option 2). Changes span both `solune/backend/` and `solune/frontend/`. No new top-level directories; all new files follow existing organizational patterns.

## Complexity Tracking

> No Constitution Check violations — this section is intentionally empty.

---

## Phase 0: Research

### R1: Nullable Foreign Key Strategy for Backward Compatibility

**Decision**: Add `conversation_id TEXT DEFAULT NULL` to `chat_messages`, `chat_proposals`, and `chat_recommendations` via `ALTER TABLE`. No `NOT NULL` constraint.

**Rationale**: Existing rows have no conversation context (they belong to `ChatPopup` on non-AppPage routes). Making the column nullable preserves all existing data and behavior. The `ChatPopup` never sends a `conversation_id`, so its messages continue to work without modification. Queries that filter by `conversation_id` use `WHERE conversation_id = ?` for scoped results, while `ChatPopup` queries omit the filter (or use `WHERE conversation_id IS NULL`).

**Alternatives considered**:
- `NOT NULL DEFAULT ''` with empty string sentinel: Requires backfilling existing rows; creates ambiguity between "no conversation" and "empty string".
- Separate `conversation_messages` join table: Over-normalized for SQLite; adds query complexity without benefit.
- Migration to assign all existing messages to a default conversation: Breaks the "ChatPopup untouched" decision; unnecessary complexity.

### R2: Agent Session Key Strategy

**Decision**: Change `AgentSessionMapping` key from `session_id` to `{session_id}:{conversation_id}` (colon-separated composite key). When `conversation_id` is `None`, use the key `{session_id}:_` (underscore sentinel).

**Rationale**: Each conversation needs its own independent agent context so chat history and tool state don't leak between simultaneous conversations. The existing `AgentSessionMapping` already uses string keys and supports TTL-based eviction. The composite key format is simple, reversible, and doesn't conflict with UUID characters.

**Alternatives considered**:
- Nested dict (`dict[str, dict[str, AgentSession]]`): Requires reworking eviction and TTL logic in `AgentSessionMapping`.
- Tuple key `(session_id, conversation_id)`: Works but the existing implementation is string-based; conversion would require API changes.
- Separate `AgentSessionMapping` per conversation: Memory overhead; harder to manage TTL globally.

### R3: Panel Layout Persistence Strategy

**Decision**: Persist panel layout (panel IDs, conversation IDs, width percentages) to `localStorage` under key `solune:chat-panels`. Use JSON serialization with a schema version field for future migration.

**Rationale**: Panel layout is ephemeral UI state—no server persistence needed. `localStorage` survives page refreshes (per the spec's verification criteria) and is synchronous (no loading states needed). A schema version field allows graceful degradation if the format changes in a future release.

**Alternatives considered**:
- `sessionStorage`: Doesn't survive tab close; spec requires restoration on browser refresh.
- Server-side persistence: Over-engineered for UI layout; adds latency and a new endpoint.
- URL state (query params): Clutters the URL; doesn't scale to complex layouts.

### R4: Multi-Panel Resize Implementation

**Decision**: Use CSS flexbox with percentage-based widths and native `mousedown`/`mousemove`/`mouseup` event handlers for resize. No external drag library.

**Rationale**: The resize interaction is constrained to horizontal dragging between panels—simpler than general drag-and-drop. The existing `ChatPopup` already implements resize with native events (lines 153–204 of `ChatPopup.tsx`). Using the same pattern keeps the codebase consistent. `requestAnimationFrame` gating prevents excessive re-renders during drag.

**Alternatives considered**:
- `@dnd-kit` (already a dependency): Designed for sortable lists and drag-and-drop; resize handles are an anti-pattern in dnd-kit.
- `react-resizable-panels`: New dependency; adds bundle size for a single use case.
- CSS `resize` property: Only works on individual elements; can't synchronize adjacent panel widths.

### R5: Mobile Panel Display Strategy

**Decision**: On viewports below 768px, display panels as tabs (one at a time) with a horizontal tab bar. The active tab shows the full `ChatPanel`; inactive panels remain mounted but hidden (`display: none`).

**Rationale**: Side-by-side panels don't fit on mobile screens (spec's 320px minimum per panel). Tab switching preserves conversation state (React Query cache, scroll position) without unmounting. The tab bar uses minimal vertical space and follows mobile chat app conventions (e.g., Slack's channel switching).

**Alternatives considered**:
- Swipe navigation: Requires gesture handling; conflicts with horizontal scrolling in message content.
- Accordion/collapsible panels: Unusual for chat UIs; poor mobile UX.
- Force single panel on mobile: Simplest but removes multi-chat capability entirely on mobile.

---

## Phase 1: Design & Contracts

### 1.1 — Migration `044_conversations.sql`

New `conversations` table and schema extensions. See `data-model.md` for full entity definitions.

```sql
-- New conversations table
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT 'New Chat',
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at);

-- Add nullable conversation_id to existing tables
ALTER TABLE chat_messages ADD COLUMN conversation_id TEXT DEFAULT NULL
    REFERENCES conversations(conversation_id) ON DELETE SET NULL;
ALTER TABLE chat_proposals ADD COLUMN conversation_id TEXT DEFAULT NULL
    REFERENCES conversations(conversation_id) ON DELETE SET NULL;
ALTER TABLE chat_recommendations ADD COLUMN conversation_id TEXT DEFAULT NULL
    REFERENCES conversations(conversation_id) ON DELETE SET NULL;

-- Indexes for filtering by conversation_id
CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id ON chat_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_proposals_conversation_id ON chat_proposals(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_recommendations_conversation_id ON chat_recommendations(conversation_id);
```

### 1.2 — Backend Models

Add to `models/chat.py`:

```python
class Conversation(BaseModel):
    conversation_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    title: str = "New Chat"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConversationCreateRequest(BaseModel):
    title: str = Field(default="New Chat", max_length=200)

class ConversationUpdateRequest(BaseModel):
    title: str = Field(max_length=200)

class ConversationsListResponse(BaseModel):
    conversations: list[Conversation]
```

Add `conversation_id: UUID | None = None` to `ChatMessage` and `ChatMessageRequest`.

### 1.3 — Backend Store Methods

Add to `services/chat_store.py`:

| Method | Signature | SQL |
|--------|-----------|-----|
| `save_conversation()` | `async def save_conversation(db, session_id, conversation_id, title)` | `INSERT OR REPLACE INTO conversations` |
| `get_conversations()` | `async def get_conversations(db, session_id)` | `SELECT ... WHERE session_id = ? ORDER BY updated_at DESC` |
| `get_conversation_by_id()` | `async def get_conversation_by_id(db, conversation_id)` | `SELECT ... WHERE conversation_id = ?` |
| `update_conversation()` | `async def update_conversation(db, conversation_id, title)` | `UPDATE conversations SET title = ?, updated_at = ?` |
| `delete_conversation()` | `async def delete_conversation(db, conversation_id)` | `DELETE FROM conversations WHERE conversation_id = ?` |

Update existing methods to accept optional `conversation_id` parameter:

| Method | Change |
|--------|--------|
| `save_message()` | Add `conversation_id=None` param; include in INSERT |
| `get_messages()` | Add `conversation_id=None` param; append `AND conversation_id = ?` when present |
| `count_messages()` | Add `conversation_id=None` param; same filter logic |
| `clear_messages()` | Add `conversation_id=None` param; scope DELETE to conversation when present |

### 1.4 — Backend API Endpoints

New conversation endpoints in `api/chat.py`:

| Endpoint | Method | Request Body | Response |
|----------|--------|-------------|----------|
| `/conversations` | POST | `ConversationCreateRequest` | `Conversation` (201) |
| `/conversations` | GET | — | `ConversationsListResponse` |
| `/conversations/{id}` | PATCH | `ConversationUpdateRequest` | `Conversation` |
| `/conversations/{id}` | DELETE | — | `{"message": "..."}` |

Updated existing endpoints — add optional `conversation_id` query param:

| Endpoint | Change |
|----------|--------|
| `GET /messages` | Accept `?conversation_id=` query param |
| `POST /messages` | Accept `conversation_id` in request body |
| `POST /messages/stream` | Accept `conversation_id` in request body |
| `DELETE /messages` | Accept `?conversation_id=` query param |

See `contracts/conversations-api.yaml` and `contracts/messages-api-updates.yaml` for full OpenAPI specs.

### 1.5 — Agent Session Isolation

Change `ChatAgentService` and `AgentSessionMapping`:

```python
# Current: key = str(session_id)
# New: key = f"{session_id}:{conversation_id}" or f"{session_id}:_" when None

def _agent_key(session_id: UUID, conversation_id: UUID | None = None) -> str:
    return f"{session_id}:{conversation_id}" if conversation_id else f"{session_id}:_"
```

Update `run()` and `run_stream()` in `ChatAgentService` to accept optional `conversation_id` and pass the composite key to `_session_mapping.get_or_create()`.

### 1.6 — Frontend Types & Schemas

Add to `types/index.ts`:

```typescript
export interface Conversation {
  conversation_id: string;
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationsListResponse {
  conversations: Conversation[];
}
```

Add `conversation_id?: string` to `ChatMessage` and `ChatMessageRequest`.

Add Zod schemas in `services/schemas/chat.ts`:

```typescript
export const ConversationSchema = z.object({
  conversation_id: z.string(),
  session_id: z.string(),
  title: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const ConversationsListResponseSchema = z.object({
  conversations: z.array(ConversationSchema),
});
```

Update `ChatMessageSchema` to include `conversation_id: z.string().optional()`.

### 1.7 — Frontend API Client

Add `conversationApi` namespace to `services/api.ts`:

```typescript
export const conversationApi = {
  create: (data: { title?: string }) => apiRequest<Conversation>('/chat/conversations', { method: 'POST', body: data }),
  list: () => apiRequest<ConversationsListResponse>('/chat/conversations'),
  update: (id: string, data: { title: string }) => apiRequest<Conversation>(`/chat/conversations/${id}`, { method: 'PATCH', body: data }),
  delete: (id: string) => apiRequest<{ message: string }>(`/chat/conversations/${id}`, { method: 'DELETE' }),
};
```

Update `chatApi.getMessages()`, `sendMessage()`, `sendMessageStream()`, `clearMessages()` to accept optional `conversationId` parameter.

### 1.8 — Frontend State Hooks

**`useConversations.ts`** — React Query hook wrapping `conversationApi`:

- `useQuery(['conversations'])` for list
- `useMutation` for create/update/delete with `queryClient.invalidateQueries(['conversations'])`

**`useChat.ts`** updates:

- Accept optional `conversationId` parameter
- Query key: `['chat', 'messages', conversationId ?? 'global']`
- Pass `conversationId` to all API calls

**`useChatPanels.ts`** — Local state hook:

- `panels: Array<{ panelId: string; conversationId: string; widthPercent: number }>`
- Methods: `addPanel()`, `removePanel(panelId)`, `resizePanel(panelId, widthPercent)`, `setConversation(panelId, conversationId)`
- Default: single panel at 100% width
- Persist to `localStorage` under `solune:chat-panels`
- Schema version for future migrations

### 1.9 — Frontend UI Components

**`ChatPanel.tsx`** — Standalone panel for one conversation:

- Props: `conversationId`, `onClose`, `onTitleChange`
- Owns `useChat(conversationId)` + `usePlan()` instances
- Panel header: editable title + close button
- Body: `<ChatInterface>` with all existing functionality

**`ChatPanelManager.tsx`** — Multi-panel container:

- Uses `useChatPanels()` + `useConversations()`
- Flexbox side-by-side layout
- Draggable resize handles between panels
- "Add Chat" button creates new conversation + panel
- Min-width constraint: 320px per panel
- Mobile (< 768px): tab-based switching

**`AppPage.tsx`** rewrite:

- Replace marketing content with `<ChatPanelManager />`
- Full viewport height: `h-[calc(100vh-<header-height>)]`

---

## Execution Phases

### Phase 1: Backend — Conversation Model & Migration

| # | Task | File | Action |
|---|------|------|--------|
| 1.1 | Create migration | `migrations/044_conversations.sql` | New `conversations` table + ALTER existing tables |
| 1.2 | Add models | `models/chat.py` | `Conversation`, `ConversationCreateRequest`, `ConversationUpdateRequest`, `ConversationsListResponse` |
| 1.3 | Add store methods | `services/chat_store.py` | Conversation CRUD + update existing methods for `conversation_id` |
| 1.4 | Add API endpoints | `api/chat.py` | Conversation CRUD endpoints + update message endpoints |
| 1.5 | Update agent keying | `services/chat_agent.py` | Composite `session_id:conversation_id` key |

**Acceptance**: All existing backend tests pass. New conversation endpoints return correct responses. Messages without `conversation_id` continue to work.

### Phase 2: Frontend — Types, API Client, Schemas

| # | Task | File | Action |
|---|------|------|--------|
| 2.1 | Add types | `types/index.ts` | `Conversation` interface, optional `conversation_id` on messages |
| 2.2 | Add schemas | `services/schemas/chat.ts` | Zod schemas for `Conversation`, update `ChatMessageSchema` |
| 2.3 | Add API client | `services/api.ts` | `conversationApi` namespace, update `chatApi` methods |

**Acceptance**: TypeScript compiles. Zod schemas validate correctly. API methods accept optional `conversationId`.

### Phase 3: Frontend — State Management

| # | Task | File | Action |
|---|------|------|--------|
| 3.1 | Create hook | `hooks/useConversations.ts` | React Query wrapper for conversation CRUD |
| 3.2 | Update hook | `hooks/useChat.ts` | Accept `conversationId`, update query keys |
| 3.3 | Create hook | `hooks/useChatPanels.ts` | Panel layout state with localStorage persistence |

**Acceptance**: Hooks compile. `useChat` with `conversationId` caches independently per conversation. Panel state persists across refresh.

### Phase 4: Frontend — AppPage UI Components

| # | Task | File | Action |
|---|------|------|--------|
| 4.1 | Create component | `components/chat/ChatPanel.tsx` | Standalone panel wrapping ChatInterface |
| 4.2 | Create component | `components/chat/ChatPanelManager.tsx` | Multi-panel container with resize |
| 4.3 | Rewrite page | `pages/AppPage.tsx` | Replace marketing content with ChatPanelManager |

**Acceptance**: AppPage renders one chat panel by default. "Add Chat" adds a second panel. Resize works. Mobile shows tabs.

### Phase 5: Testing & Verification

| # | Task | File | Action |
|---|------|------|--------|
| 5.1 | Update tests | `pages/AppPage.test.tsx` | Tests for new chat layout |
| 5.2 | Add backend tests | `tests/unit/test_chat_store.py` | Conversation CRUD, message filtering |
| 5.3 | Add frontend tests | `ChatPanel.test.tsx` | Panel render, close, title edit |
| 5.4 | Add frontend tests | `ChatPanelManager.test.tsx` | Add panel, remove panel, resize |
| 5.5 | Add frontend tests | `useConversations.test.ts` | Hook CRUD operations |

**Acceptance**: All existing tests pass. New tests cover conversation lifecycle and panel management.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SQLite ALTER TABLE performance on large `chat_messages` | Low | Medium | ALTER ADD COLUMN is O(1) in SQLite (no table rewrite) |
| Agent session key change breaks existing sessions | Low | Low | Existing sessions expire via TTL (3600s); new key format only affects new requests |
| localStorage quota exceeded | Very Low | Low | Panel layout is ~500 bytes; well within 5MB quota |
| Concurrent resize events cause layout jank | Low | Medium | `requestAnimationFrame` gating (same pattern as ChatPopup) |
| Mobile tab switching loses scroll position | Low | Low | Panels stay mounted (`display: none`); scroll position preserved |

## Dependencies

```text
Phase 1 (Backend)
  1.1 migration ──→ 1.2 models ──→ 1.3 store ──→ 1.4 API
                                                    ↘ 1.5 agent keying

Phase 2 (Frontend Types) ── depends on Phase 1 API contract
  2.1 types ──→ 2.2 schemas ──→ 2.3 API client

Phase 3 (State) ── depends on Phase 2
  2.3 API client ──→ 3.1 useConversations
  2.3 API client ──→ 3.2 useChat update
  (independent)  ──→ 3.3 useChatPanels

Phase 4 (UI) ── depends on Phase 3
  3.1 + 3.2 + 3.3 ──→ 4.1 ChatPanel ──→ 4.2 ChatPanelManager ──→ 4.3 AppPage

Phase 5 (Tests) ── depends on Phase 4
  All phases ──→ 5.1–5.5
```

## Decisions Log

| Decision | Rationale |
|----------|-----------|
| `conversation_id` nullable everywhere | Backward compat: existing ChatPopup messages work without it |
| Agent key `session_id:conversation_id` | No cross-talk between simultaneous chats; simple string key |
| ChatPopup untouched | Scopes the change; popup is not conversation-aware by design |
| AppPage welcome content removed | Quick-links already in sidebar navigation |
| Mobile panels as tabs | Side-by-side doesn't fit; tabs are familiar from mobile chat apps |
| localStorage for panel layout | Survives refresh; no server persistence needed for UI state |
| No external resize library | Native events match existing ChatPopup pattern; minimal new code |
