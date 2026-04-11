# Quickstart: Multi-Chat App Page

**Feature**: Multi-Chat App Page | **Date**: 2026-04-11

> **Status note (2026-04-11):** The backend conversations and chat APIs are complete. The frontend multi-panel workflow is implemented, but the product surface is still being refined, so expect the UI details in this feature quickstart to evolve.

## Prerequisites

- Python ≥3.12 with virtual environment
- Node.js ≥18 with npm
- SQLite (bundled with Python)
- Git

## Backend Setup

```bash
cd solune/backend

# Install dependencies
pip install -e ".[dev]"

# Run migrations (applies 044_conversations.sql automatically on startup)
# Migrations are applied via the startup hook in src/database.py
python -c "from src.database import run_migrations; import asyncio; asyncio.run(run_migrations())"
```

### Verify Migration

```bash
# Check that the conversations table exists
sqlite3 data/solune.db ".schema conversations"

# Expected output:
# CREATE TABLE conversations (
#     conversation_id TEXT PRIMARY KEY,
#     session_id TEXT NOT NULL,
#     title TEXT NOT NULL DEFAULT 'New Chat',
#     created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
#     updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
#     FOREIGN KEY (session_id) REFERENCES user_sessions(session_id) ON DELETE CASCADE
# );

# Check that conversation_id was added to chat_messages
sqlite3 data/solune.db "PRAGMA table_info(chat_messages);" | grep conversation_id
```

### Run Backend Tests

```bash
cd solune/backend

# Run conversation-specific tests
python -m pytest tests/unit/test_chat_store.py -k "conversation" -v

# Run all chat API tests
python -m pytest tests/unit/test_api_chat.py -v

# Run full backend test suite (ensure no regressions)
python -m pytest tests/unit/ -q --timeout=120
```

### Test Conversation Endpoints Manually

```bash
# Start the backend server
cd solune/backend && uvicorn src.main:app --reload --port 8000

# Create a conversation (requires valid session cookie)
curl -X POST http://localhost:8000/api/v1/chat/conversations \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Conversation"}' \
  -b "session_id=YOUR_SESSION_ID"

# List conversations
curl http://localhost:8000/api/v1/chat/conversations \
  -b "session_id=YOUR_SESSION_ID"

# Send a message to a specific conversation
curl -X POST http://localhost:8000/api/v1/chat/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello!", "conversation_id": "CONVERSATION_ID"}' \
  -b "session_id=YOUR_SESSION_ID"

# Get messages for a specific conversation
curl "http://localhost:8000/api/v1/chat/messages?conversation_id=CONVERSATION_ID" \
  -b "session_id=YOUR_SESSION_ID"

# Update conversation title
curl -X PATCH http://localhost:8000/api/v1/chat/conversations/CONVERSATION_ID \
  -H "Content-Type: application/json" \
  -d '{"title": "Renamed Chat"}' \
  -b "session_id=YOUR_SESSION_ID"

# Delete conversation
curl -X DELETE http://localhost:8000/api/v1/chat/conversations/CONVERSATION_ID \
  -b "session_id=YOUR_SESSION_ID"
```

## Frontend Setup

```bash
cd solune/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Run Frontend Tests

```bash
cd solune/frontend

# Run conversation-related tests
npm test -- --reporter=verbose useConversations
npm test -- --reporter=verbose ChatPanel
npm test -- --reporter=verbose ChatPanelManager
npm test -- --reporter=verbose AppPage

# Run full frontend test suite
npm test
```

### Verify UI Behavior

1. **Navigate to AppPage** (`/`)
   - Should see a single chat panel (full width)
   - Panel header shows "New Chat" title

2. **Send a message**
   - Type in the input and press Enter
   - Message appears in the panel; streaming response follows

3. **Add a second panel**
   - Click "Add Chat" button
   - Second panel appears side-by-side
   - Both panels are resizable via the drag handle between them

4. **Resize panels**
   - Hover over the border between panels (cursor changes to `col-resize`)
   - Drag to resize; panels respect 320px minimum width

5. **Edit conversation title**
   - Click the title in the panel header
   - Type a new title and press Enter or blur

6. **Close a panel**
   - Click the close (×) button in the panel header
   - Panel is removed; remaining panels redistribute width
   - Cannot close the last panel

7. **Mobile behavior** (resize browser to < 768px)
   - Panels switch to tab view
   - One panel visible at a time
   - Tab bar at top shows conversation titles

8. **Persistence**
   - Open multiple panels with different conversations
   - Refresh the browser
   - Same panels and conversations should be restored from localStorage

9. **ChatPopup on other pages**
   - Navigate to `/projects` or `/agents`
   - ChatPopup (floating bottom-right) continues to work independently
   - ChatPopup messages are NOT scoped to any conversation

## Key Files Reference

### Backend (modify)

| File | Changes |
|------|---------|
| `src/migrations/044_conversations.sql` | NEW: Create conversations table + ALTER existing tables |
| `src/models/chat.py` | Add Conversation models; add conversation_id to ChatMessage/Request |
| `src/services/chat_store.py` | Add conversation CRUD; update message methods for conversation_id filter |
| `src/api/chat.py` | Add conversation endpoints; update message endpoints |
| `src/services/chat_agent.py` | Change session key to `session_id:conversation_id` |

### Frontend (modify)

| File | Changes |
|------|---------|
| `src/types/index.ts` | Add Conversation interface; add conversation_id to ChatMessage/Request |
| `src/services/schemas/chat.ts` | Add Conversation Zod schemas; update ChatMessageSchema |
| `src/services/api.ts` | Add conversationApi namespace; update chatApi methods |
| `src/hooks/useChat.ts` | Accept conversationId param; update query keys |
| `src/pages/AppPage.tsx` | Rewrite: marketing → ChatPanelManager |

### Frontend (create)

| File | Purpose |
|------|---------|
| `src/hooks/useConversations.ts` | React Query hook for conversation CRUD |
| `src/hooks/useChatPanels.ts` | Panel layout state with localStorage persistence |
| `src/components/chat/ChatPanel.tsx` | Standalone panel wrapping ChatInterface |
| `src/components/chat/ChatPanelManager.tsx` | Multi-panel container with resize |

### Untouched

| File | Reason |
|------|--------|
| `AppLayout.tsx` | Layout wrapper — no changes needed |
| `ChatPopup.tsx` | Floating popup — stays conversation-unaware |
| `ChatInterface.tsx` | Reused as-is inside ChatPanel |

## Troubleshooting

### Migration fails with "table conversations already exists"

The migration uses `CREATE TABLE IF NOT EXISTS`, so this shouldn't happen. If it does, check that `044_conversations.sql` was not applied twice.

### Messages don't filter by conversation_id

Verify that:

1. The migration added the `conversation_id` column to `chat_messages`
2. The API endpoint passes `conversation_id` to the store method
3. The frontend sends `conversationId` in the request

### Panel layout doesn't persist

Check `localStorage` in browser DevTools:

```javascript
JSON.parse(localStorage.getItem('solune:chat-panels'))
```

### Resize handle not visible

The handle is a thin (4–8px) vertical bar between panels. Ensure:

1. Multiple panels are open
2. Container has sufficient width for both panels (≥640px)
