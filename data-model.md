# Data Model: Multi-Chat App Page

**Feature**: Multi-Chat App Page | **Date**: 2026-04-11 | **Status**: Complete

## Entity: Conversation

A named container for a set of related chat messages within a user session. Each conversation corresponds to one chat panel on the AppPage.

### Fields

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `conversation_id` | TEXT (UUID) | PRIMARY KEY | `uuid4()` | Unique identifier |
| `session_id` | TEXT (UUID) | NOT NULL, FK → `user_sessions.session_id` | — | Owning user session |
| `title` | TEXT | NOT NULL | `'New Chat'` | User-editable conversation name |
| `created_at` | TEXT (ISO 8601) | — | `strftime('%Y-%m-%dT%H:%M:%fZ', 'now')` | Creation timestamp |
| `updated_at` | TEXT (ISO 8601) | — | `strftime('%Y-%m-%dT%H:%M:%fZ', 'now')` | Last modification timestamp |

### Relationships

| Related Entity | Cardinality | FK Location | Cascade |
|---------------|-------------|-------------|---------|
| `user_sessions` | N:1 | `conversations.session_id` | `ON DELETE CASCADE` |
| `chat_messages` | 1:N | `chat_messages.conversation_id` | `ON DELETE SET NULL` |
| `chat_proposals` | 1:N | `chat_proposals.conversation_id` | `ON DELETE SET NULL` |
| `chat_recommendations` | 1:N | `chat_recommendations.conversation_id` | `ON DELETE SET NULL` |

### Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| `idx_conversations_session_id` | `session_id` | List conversations by user session |
| `idx_conversations_updated_at` | `updated_at` | Sort by most recently active |

### Validation Rules

- `title` max length: 200 characters (enforced by Pydantic model)
- `session_id` must reference an existing `user_sessions` row
- `conversation_id` is a valid UUID v4 string

---

## Entity: ChatMessage (updated)

Existing entity with a new nullable `conversation_id` column.

### New Field

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `conversation_id` | TEXT (UUID) | NULLABLE, FK → `conversations.conversation_id` | `NULL` | Owning conversation (NULL for global/ChatPopup messages) |

### Index

| Index | Columns | Purpose |
|-------|---------|---------|
| `idx_chat_messages_conversation_id` | `conversation_id` | Filter messages by conversation |

### Backward Compatibility

- Existing rows retain `conversation_id = NULL`
- Queries without a `conversation_id` filter return all messages for the session (existing behavior)
- Queries with `WHERE conversation_id = ?` return only that conversation's messages

---

## Entity: ChatProposal (updated)

Existing entity with a new nullable `conversation_id` column.

### New Field

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `conversation_id` | TEXT (UUID) | NULLABLE, FK → `conversations.conversation_id` | `NULL` | Owning conversation |

### Index

| Index | Columns | Purpose |
|-------|---------|---------|
| `idx_chat_proposals_conversation_id` | `conversation_id` | Filter proposals by conversation |

---

## Entity: ChatRecommendation (updated)

Existing entity with a new nullable `conversation_id` column.

### New Field

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `conversation_id` | TEXT (UUID) | NULLABLE, FK → `conversations.conversation_id` | `NULL` | Owning conversation |

### Index

| Index | Columns | Purpose |
|-------|---------|---------|
| `idx_chat_recommendations_conversation_id` | `conversation_id` | Filter recommendations by conversation |

---

## Entity: PanelLayout (frontend only — localStorage)

Client-side representation of open chat panels, persisted to `localStorage`.

### Schema

```typescript
interface PanelLayout {
  version: 1;
  panels: PanelState[];
}

interface PanelState {
  panelId: string;           // Unique panel identifier (UUID)
  conversationId: string;    // FK to conversation_id
  widthPercent: number;      // Panel width as percentage of container (0-100)
}
```

### Validation Rules

- `version` must be `1` (future versions trigger migration logic)
- `panels` array must contain at least 1 element
- `widthPercent` values must sum to 100 (±1 for rounding)
- Each `panelId` must be unique
- Each `conversationId` should reference a valid conversation (stale references are pruned on load)

### State Transitions

```text
Initial Load:
  localStorage empty → create default panel (single, 100% width)
  localStorage has data → validate schema version → load panels → prune stale conversations

Add Panel:
  Create conversation (API) → add panel with widthPercent = 100/N → redistribute widths

Remove Panel:
  If last panel → prevent removal (minimum 1 panel)
  Otherwise → remove panel → redistribute widths → delete conversation if empty

Resize:
  Drag handle → update adjacent panel widthPercent values → persist to localStorage
```

---

## Entity Relationship Diagram

```text
┌──────────────┐     1:N      ┌─────────────────┐
│ user_sessions │────────────▶│  conversations    │
│              │              │                   │
│ session_id   │◀─────┐      │ conversation_id   │
└──────────────┘      │      │ session_id (FK)   │
                      │      │ title             │
                      │      │ created_at        │
                      │      │ updated_at        │
                      │      └─────────┬─────────┘
                      │                │
                      │         1:N    │  ON DELETE SET NULL
                      │                │
                      │    ┌───────────┴──────────────┐
                      │    │                          │
                ┌─────┴────┴──┐    ┌──────────────┐   ┌───────────────────┐
                │chat_messages│    │chat_proposals │   │chat_recommendations│
                │             │    │               │   │                   │
                │ message_id  │    │ proposal_id   │   │ recommendation_id │
                │ session_id  │    │ session_id    │   │ session_id        │
                │ conv_id(?)  │    │ conv_id(?)    │   │ conv_id(?)        │
                │ sender_type │    │ original_input│   │ data              │
                │ content     │    │ proposed_title│   │ status            │
                │ timestamp   │    │ status        │   │ created_at        │
                └─────────────┘    └──────────────┘   └───────────────────┘

Legend: (?) = nullable FK, ON DELETE SET NULL
```

---

## Pydantic Models (Backend)

### New Models

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

### Updated Models

```python
# Add to ChatMessage:
conversation_id: UUID | None = None

# Add to ChatMessageRequest:
conversation_id: UUID | None = None
```

---

## TypeScript Interfaces (Frontend)

### New Interfaces

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

### Updated Interfaces

```typescript
// Add to ChatMessage:
conversation_id?: string;

// Add to ChatMessageRequest:
conversation_id?: string;
```

---

## Zod Schemas (Frontend)

### New Schemas

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

### Updated Schemas

```typescript
// Add to ChatMessageSchema:
conversation_id: z.string().optional(),
```
