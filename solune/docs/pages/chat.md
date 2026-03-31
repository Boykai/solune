# Chat

The chat panel is Solune's conversational interface — a persistent floating panel available on every page. Use it to talk to AI agents, propose tasks and issues, upload files for context, and receive real-time streaming responses. The chat panel stays open as you navigate between pages so your conversation is never lost.

This guide covers every chat capability, from basic messaging to advanced features like pipeline selection and AI proposals.

## Sending Messages

Type a message in the input field and press **Enter** to send. To insert a new line without sending, press **Shift+Enter**.

**What you can do:**

- Send plain text messages up to **100,000 characters**
- Press **Enter** to send immediately
- Press **Shift+Enter** to add a new line
- Messages appear instantly in the chat while the AI processes a response

## AI Enhance

The **AI Enhance** toggle controls how the chat agent processes your messages. When enabled, the agent uses the full Microsoft Agent Framework with tool use, reasoning, and multi-turn conversation. When disabled, the agent returns metadata-only responses without invoking the Agent Framework.

| Mode | Behavior |
|------|----------|
| **On** (default) | Agent Framework — multi-turn reasoning, tool use, streaming responses |
| **Off** | Metadata-only — lightweight response without agent reasoning |

Your preference is saved in `localStorage` and restored automatically on your next visit.

**When to disable AI Enhance:**

- You want faster, lighter responses without tool invocation
- You are working on a task that does not need agent reasoning

## @Mention Pipeline Selection

Type **@** in the message input to select a pipeline for your message. An autocomplete dropdown appears with available pipelines. Select one to attach it as an inline token in your message.

**How it works:**

1. Type `@` anywhere in your message
2. An autocomplete dropdown appears after a short delay (150 ms debounce)
3. Up to 10 matching pipelines are shown — use arrow keys or click to select
4. The selected pipeline appears as an inline token in your message
5. Only **one pipeline** can be active per message — selecting a new one replaces the previous

The selected pipeline tells the AI which agent pipeline to use when processing your request.

## Voice Input

Click the **microphone button** in the chat toolbar to dictate messages using your voice.

**Requirements:**

- **HTTPS** — voice input requires a secure connection
- **Browser support** — uses the Web Speech API (available in most modern browsers)
- **Language** — recognition is set to `en-US`

**Recording states:**

| State | Description |
|-------|-------------|
| **Idle** | Microphone is not active |
| **Recording** | Microphone is listening — speak your message |
| **Processing** | Speech is being transcribed into text |

The transcribed text is inserted into the message input field, where you can review and edit it before sending.

## File Attachments

Attach files to your message for additional context. Drag files into the chat, paste them, or click the attach button.

**Limits:**

| Constraint | Value |
|------------|-------|
| Maximum files per message | 5 |
| Maximum file size | 10 MB per file |

**Allowed file types:** Images (png, jpg, jpeg, gif, webp, svg), documents (pdf, txt, md, csv, json, yaml, yml, vtt, srt), and archives (zip).

**Blocked file types:** Executables and scripts (exe, sh, bat, cmd, js, py, rb).

**Transcript auto-detection:** When you upload a `.vtt` or `.srt` subtitle file, Solune automatically detects it as a transcript and processes it accordingly.

## Chat History Navigation

Navigate through your previous messages using keyboard shortcuts, similar to a terminal shell.

**How it works:**

- Press **Arrow Up** to recall the previous message you sent
- Press **Arrow Down** to move forward through your message history
- The history buffer stores up to **100 messages** in memory
- History is kept in memory for the current session — it is not persisted across page reloads

This is useful for re-sending or editing a recent message without retyping it.

## Slash Commands

Type **/** in the message input to see available slash commands.

**Available commands:**

| Command | Description |
|---------|-------------|
| `/help` | Show available commands and usage tips |
| `/theme` | Toggle between light and dark mode |
| `/clear` | Clear the chat history |

### `#agent` Command

Use `#agent <description> #<status-name>` to create a custom GitHub agent inline from the chat. The command triggers an AI-generated preview, and you can refine the agent through natural language before confirming creation.

For example: `#agent code reviewer that checks for security issues #in-review`

The `#<status-name>` part maps to a column on your project board. Solune uses fuzzy matching, so `#in-review`, `#InReview`, and `#IN_REVIEW` all resolve to the same column.

## AI Proposals

When the AI agent determines that an action is appropriate, it sends a **proposal** — a structured preview you can review before confirming.

### Task Proposals

The agent may propose creating a new task (GitHub Issue). You see a structured preview with the proposed title, description, and metadata. Click **Confirm** to create the task or **Reject** to dismiss it.

### Issue Recommendations

The agent may recommend existing issues that are relevant to your conversation. Each recommendation includes a structured preview with issue metadata so you can quickly evaluate relevance.

### Status Changes

The agent may propose changing the status of an existing issue. Review the proposed status transition and confirm or reject it.

## Streaming Responses

When AI Enhance is on, responses stream in real time via the `POST /chat/messages/stream` SSE endpoint — you see tokens appear as the agent generates them, rather than waiting for the full response. The non-streaming `POST /chat/messages` endpoint returns a single JSON response.

**What you see during streaming:**

- **Text tokens** appear incrementally as the agent generates its response
- **Tool call indicators** show when the agent is invoking a tool (e.g., searching issues, creating a task)
- **Skeleton loading** displays a placeholder while the agent prepares its first token

Streaming uses the dedicated `POST /chat/messages/stream` endpoint with `ai_enhance=true`. When AI Enhance is off, the client uses the non-streaming `POST /chat/messages` endpoint and responses arrive as a single complete message.

## Markdown Rendering

AI responses are rendered as rich Markdown using GitHub Flavored Markdown (GFM).

**Supported features:**

- **Code blocks** with syntax highlighting and a **copy button**
- **Tables** rendered as formatted HTML tables
- **Links** rendered as clickable hyperlinks
- **Inline code**, bold, italic, and other standard Markdown formatting

## Message Types and Actions

Chat messages come in three types:

| Type | Description |
|------|-------------|
| **User** | Messages you send |
| **Assistant** | AI agent responses |
| **System** | System notifications and status updates |

**Message actions:**

- **Retry** — re-send a message to get a new AI response
- **Copy** — copy the message content to your clipboard
- **Clear** — clear the entire chat history
