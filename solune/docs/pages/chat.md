# Chat

Solune has **two chat surfaces**, not a standalone `/chat` page:

1. **Floating `ChatPopup`** — available from the bottom-right corner on every authenticated page
2. **Full-screen `ChatPanelManager` on `/`** — the dashboard experience with multiple concurrent conversations

Both surfaces use the same chat backend, streaming pipeline, proposals, uploads, and slash-command system. The main difference is scope: the floating popup is conversation-unaware, while the dashboard supports explicit conversation records and multi-panel work.

## Where Chat Lives

| Surface | Route / Location | Behavior |
|---------|------------------|----------|
| **ChatPopup** | All authenticated pages | Single floating panel, persistent across navigation, no `conversation_id` |
| **ChatPanelManager** | `/` (`AppPage`) | Full-height workspace with one or more independent conversation panels |

There is currently **no dedicated `/chat` route** in the React router.

## Multi-Conversation Dashboard Chat

The dashboard chat experience is powered by `ChatPanelManager`, `ChatPanel`, `useConversations`, and `useChatPanels`.

### What it supports

- Creating new conversations with `POST /api/v1/chat/conversations`
- Opening multiple panels at once on desktop
- Editing conversation titles inline
- Resizing desktop panels with drag handles
- Switching to tabbed chat panels on mobile
- Restoring the panel layout from `localStorage`

### Conversation model

- Each panel is tied to a persisted `conversation_id`
- Messages, plans, and approvals stay scoped to that conversation
- Closing a panel deletes that conversation from the dashboard workspace
- The last panel cannot be removed, so the page always has an active chat surface

## Floating Chat Popup

`ChatPopup` stays available across the rest of the app layout.

### What it supports

- Persistent open/close state while navigating pages
- Drag-to-resize on desktop
- Full-screen presentation on mobile
- The same streaming, upload, slash-command, and proposal workflows used by the dashboard

### Important limitation

The popup remains **conversation-unaware**. Its messages are sent without a `conversation_id`, so it should be treated as a lightweight global helper rather than a multi-chat workspace.

## Sending Messages

Type a message and press **Enter** to send. Use **Shift+Enter** for a newline.

**What you can do:**

- Send plain-text prompts up to **100,000 characters**
- Work in a specific dashboard conversation or the global popup session
- Reuse the same message composer features in both chat surfaces

## AI Enhance

The **AI Enhance** toggle controls how the chat agent handles your message.

| Mode | Behavior |
|------|----------|
| **On** (default) | Agent Framework reasoning, tool use, streaming responses, multi-turn conversation |
| **Off** | Metadata-only response without Agent Framework execution |

Your preference is saved locally and restored on the next visit.

## Pipeline Selection with `@mention`

Type **@** in the message input to attach one pipeline to the current message.

1. Type `@`
2. Pick a pipeline from the autocomplete list
3. Send the message with that pipeline selection attached

Only **one pipeline** can be active per message; selecting another replaces the previous one.

## Voice Input

Click the microphone in the toolbar to dictate text with the Web Speech API.

| State | Description |
|-------|-------------|
| **Idle** | Microphone inactive |
| **Recording** | Browser is listening |
| **Processing** | Speech is being transcribed |

Voice input requires **HTTPS** in supported browsers and inserts the transcript into the composer before sending.

## File Attachments

Use the attach button, drag-and-drop, or paste to add files for extra context.

| Constraint | Value |
|------------|-------|
| Maximum files per message | 5 |
| Maximum file size | 10 MB per file |
| Allowed types | png, jpg, jpeg, gif, webp, svg, pdf, txt, md, csv, json, yaml, yml, vtt, srt, zip |
| Blocked types | exe, sh, bat, cmd, js, py, rb |
| Transcript auto-detection | `.vtt` and `.srt` uploads are treated as transcripts |

## Proposals, Plans, and Streaming

Both chat surfaces support:

- **Streaming SSE responses** through `POST /api/v1/chat/messages/stream`
- **Task proposals**, **issue recommendations**, and **status-change proposals**
- **Plan mode** for structured app planning, including step approval and export endpoints
- **Markdown rendering** with code blocks, tables, inline formatting, and links

Streaming emits `token`, `tool_call`, `tool_result`, `done`, and `error` events.

## Keyboard and Message Utilities

- **Arrow Up / Arrow Down** — cycle through recent prompts
- **/** — open the slash-command menu (`/help`, `/theme`, `/clear`, and other registered commands)
- **Retry / Copy / Clear** — available from the chat UI where supported
