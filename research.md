# Research: Multi-Chat App Page

**Feature**: Multi-Chat App Page | **Date**: 2026-04-11 | **Status**: Complete

## R1: Nullable Foreign Key Strategy for Backward Compatibility

**Decision**: Add `conversation_id TEXT DEFAULT NULL` to `chat_messages`, `chat_proposals`, and `chat_recommendations` via `ALTER TABLE`. No `NOT NULL` constraint.

**Rationale**: Existing rows have no conversation context — they belong to `ChatPopup` on non-AppPage routes. Making the column nullable preserves all existing data and behavior without backfilling. The `ChatPopup` never sends a `conversation_id`, so its messages continue to work unchanged. Queries that filter by `conversation_id` use `WHERE conversation_id = ?` for scoped results, while global queries (ChatPopup) omit the filter entirely.

SQLite's `ALTER TABLE ... ADD COLUMN` with a `DEFAULT NULL` is an O(1) metadata-only operation — it does not rewrite the table. This means the migration is safe to run on databases with millions of messages.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| `NOT NULL DEFAULT ''` (empty string sentinel) | Requires backfilling all existing rows; creates ambiguity between "no conversation" and "empty string"; non-standard FK pattern |
| Separate `conversation_messages` join table | Over-normalized for SQLite; adds query complexity and JOIN overhead without tangible benefit for this use case |
| Backfill existing messages into a default conversation | Breaks the "ChatPopup untouched" decision; adds migration complexity; unnecessary since ChatPopup works independently |
| Add `conversation_id` only to new tables | Prevents filtering existing message types by conversation; breaks the spec requirement of scoping proposals and recommendations |

---

## R2: Agent Session Key Strategy

**Decision**: Change `AgentSessionMapping` key from `session_id` (string) to `{session_id}:{conversation_id}` (colon-separated composite key). When `conversation_id` is `None`, use the key `{session_id}:_` (underscore sentinel).

**Rationale**: Each conversation needs its own independent agent context so chat history and tool state don't leak between simultaneous conversations. The existing `AgentSessionMapping` already uses string keys and supports TTL-based eviction with LRU semantics. The composite key format is:

- **Simple**: A string concatenation with a known delimiter
- **Reversible**: Can be split on `:` to recover components (UUIDs don't contain colons)
- **Non-conflicting**: Colons are not valid UUID characters, and `_` is distinct from any UUID
- **Backward-compatible**: Existing sessions expire via TTL (3600s); new key format only applies to new requests

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Nested dict (`dict[str, dict[str, AgentSession]]`) | Requires reworking the eviction and TTL logic throughout `AgentSessionMapping`; increases complexity |
| Tuple key `(session_id, conversation_id)` | Existing implementation is string-based; tuple keys require changes to serialization, comparison, and hashing patterns |
| Separate `AgentSessionMapping` per conversation | Memory overhead from multiple mapping instances; harder to manage TTL and capacity globally |
| Keep single session per user, reset context on conversation switch | Breaks the "independent agent context" requirement; loses state when switching back |

---

## R3: Panel Layout Persistence Strategy

**Decision**: Persist panel layout to `localStorage` under key `solune:chat-panels`. Format is a JSON object with a `version` field for future schema migration.

```typescript
interface PanelLayout {
  version: 1;
  panels: Array<{
    panelId: string;
    conversationId: string;
    widthPercent: number;
  }>;
}
```

**Rationale**: Panel layout is ephemeral UI state — no server persistence needed. `localStorage` survives page refreshes (meeting the spec's "browser refresh restores previously open panels" requirement) and is synchronous (no loading states during initial render). A `version` field enables graceful migration if the schema changes in future releases (e.g., adding panel order, scroll position, or collapsed state).

The `solune:` prefix namespaces the key to avoid collisions with other apps on the same domain, consistent with typical localStorage conventions.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| `sessionStorage` | Doesn't survive tab close or browser restart; violates the "browser refresh restores panels" requirement |
| Server-side persistence (new endpoint) | Over-engineered for UI layout; adds latency on every resize; requires new backend model/migration |
| URL query parameters | Clutters the URL; doesn't scale to complex layouts; creates ugly shareable URLs |
| IndexedDB | Overkill for ~500 bytes of JSON; async API adds unnecessary complexity |
| React state only (no persistence) | Loses layout on refresh; violates spec requirement |

---

## R4: Multi-Panel Resize Implementation

**Decision**: Use CSS flexbox with percentage-based widths and native `mousedown`/`mousemove`/`mouseup` event handlers for resize handles. No external drag library.

**Rationale**: The resize interaction is constrained to horizontal dragging between adjacent panels — much simpler than general drag-and-drop. The existing `ChatPopup` component (lines 153–204 of `ChatPopup.tsx`) already implements resize with native mouse events and `requestAnimationFrame` gating. Using the same pattern:

- Keeps the codebase consistent (developers already understand the pattern)
- Avoids a new dependency for a single use case
- Provides direct control over performance characteristics

The handle renders as a thin vertical bar (4–8px wide) between panels with a `cursor: col-resize` style. During drag:

1. `mousedown` on handle → capture start position and panel widths
2. `mousemove` (window-level) → calculate delta, update panel `widthPercent` values
3. `mouseup` (window-level) → commit final widths to state, persist to localStorage
4. `requestAnimationFrame` gating ensures at most one state update per frame

Touch events (`touchstart`/`touchmove`/`touchend`) follow the same pattern for tablet support, though on mobile (< 768px) the tab interface replaces side-by-side panels entirely.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| `@dnd-kit` (existing dependency) | Designed for sortable lists and pick-up/put-down interactions; resize handles are an anti-pattern in dnd-kit's API |
| `react-resizable-panels` (new dep) | Adds ~15KB to bundle for a single use case; the native approach is <100 lines |
| CSS `resize` property | Only works on individual elements; cannot synchronize adjacent panel widths or enforce constraints |
| CSS Grid with `grid-template-columns` | Possible but less intuitive for dynamic resize; percentage updates require CSS variable manipulation |

---

## R5: Mobile Panel Display Strategy

**Decision**: On viewports below 768px, display panels as tabs with a horizontal tab bar at the top of the chat area. The active tab shows the full `ChatPanel`; inactive panels remain mounted but hidden via `display: none`.

**Rationale**: Side-by-side panels don't fit on mobile screens — the spec mandates a 320px minimum width per panel, which means only one panel fits on most phones. Tab switching:

- Preserves conversation state (React Query cache, streaming state, scroll position) without unmounting
- Uses minimal vertical space (single row of tab buttons)
- Follows familiar mobile chat app conventions (Slack, Discord, Telegram all use channel/conversation switching)
- Supports the "Add Chat" button as a `+` tab

The active tab is highlighted with a bottom border and bolder text. Tab labels show the conversation title (truncated to 15 characters).

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Horizontal swipe navigation | Requires gesture handling library; conflicts with horizontal scrolling in markdown code blocks within messages |
| Accordion/collapsible panels | Unusual UX for chat interfaces; poor discoverability on mobile |
| Force single panel on mobile | Simplest but entirely removes multi-chat capability on mobile; reduces feature value |
| Bottom navigation bar | Conflicts with mobile browser chrome (bottom toolbar); less space-efficient than top tabs |

---

## R6: Conversation Title Auto-Generation

**Decision**: Default title is "New Chat". The title can be manually edited via the panel header. No auto-generation from first message content in Phase 1.

**Rationale**: Auto-generating titles from message content (e.g., using the first user message or an AI summary) adds complexity to the initial implementation:

- Requires an additional API call or background job after the first message
- Introduces timing issues (title appears after a delay)
- May produce poor titles from short or ambiguous first messages

Manual editing via an inline input in the panel header is simpler and gives users direct control. Auto-generation can be added in a future iteration as an enhancement.

**Alternatives considered**:

| Alternative | Why Rejected (for Phase 1) |
|-------------|---------------------------|
| AI-generated title after first message | Adds latency and a background task; can be a follow-up feature |
| First message truncated as title | Poor titles from short messages ("hi", "help"); requires cleanup logic |
| Timestamp-based title ("Chat 2026-04-11 10:30") | Not human-friendly; doesn't convey conversation topic |

---

## R7: Conversation Deletion Cascade Behavior

**Decision**: When a conversation is deleted, its `conversation_id` references in `chat_messages`, `chat_proposals`, and `chat_recommendations` are set to `NULL` via `ON DELETE SET NULL`. Messages are not deleted — they become "orphaned" (associated with the session but no conversation).

**Rationale**: Cascading deletes (`ON DELETE CASCADE` from conversations to messages) would permanently destroy message history. Setting to `NULL` preserves the messages in the database while removing the conversation container. This is safer and allows recovery. The orphaned messages are invisible in the UI (no conversation to display them in) but remain queryable for analytics or debugging.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| `ON DELETE CASCADE` (delete messages too) | Permanently destroys message history; no recovery possible |
| Soft delete (add `deleted_at` column) | Over-engineered for Phase 1; adds query complexity with `WHERE deleted_at IS NULL` filters |
| Prevent deletion if messages exist | Poor UX; users should be able to clean up conversations freely |
