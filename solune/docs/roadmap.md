# Solune Roadmap

> From chat-driven pipelines to a voice-first, agent-native DevOps platform.
>
> **Planning note:** `v0.2.0` reflects the features currently shipped in the repository. `v0.3.0` through `v0.5.0` remain aspirational planning targets rather than committed delivery dates.

---

## v0.2.0 — Intelligent Chat Agent (current)

The current release focuses on the Microsoft Agent Framework chat experience and the workflows that hang off it.

### Shipped in the repository

- ✅ **Agent Framework chat agent** — multi-turn conversations with memory, tool use, and decision-making
- ✅ **Clarifying questions** — the agent can gather follow-up details before acting
- ✅ **Difficulty assessment** — prompts can drive different pipeline choices and planning flows
- ✅ **Autonomous project creation hooks** — chat and app flows can create parent issues and launch pipelines
- ✅ **Tool / skill extensibility** — project-scoped MCP tools are available to the chat agent
- ✅ **Model flexibility** — providers and models are configurable
- ✅ **Conversation history** — persisted chat history and dashboard conversations
- ✅ **Streaming responses** — AI Enhance conversations stream tokens, tool calls, and results in real time
- ✅ **File uploads** — up to 5 files (10 MB each), including transcript-aware `.vtt` / `.srt` uploads
- ✅ **@mention pipeline selection** — one active pipeline can be attached inline per message
- ✅ **AI Enhance toggle** — switch between Agent Framework reasoning and lightweight metadata-only replies
- ✅ **Chat history navigation** — shell-style Arrow Up / Down prompt recall
- ✅ **Markdown rendering** — assistant replies support GFM, tables, links, and copyable code blocks

### Partially shipped / still evolving

- 🟡 **Dashboard multi-chat workspace** — shipped behind `AppPage`, but the UX is still actively being refined
- 🟡 **App-builder orchestration** — plan-driven app creation APIs and orchestration tables exist, but the end-to-end product flow is still growing
- 🟡 **Voice input** — browser transcription exists today, but full duplex voice is not yet delivered

---

## v0.3.0 — Full Duplex Voice Chat (aspirational)

Expand from browser transcription into a true two-way voice conversation system.

### Target capabilities

- **Browser voice chat** — full duplex audio via WebRTC with real-time speech-to-text and text-to-speech
- **Natural conversation** — interrupt, ask follow-ups, and continue while the agent works
- **Voice-driven actions** — prompt complex creation flows by speaking them
- **Signal voice support** — send and receive voice-driven updates through Signal
- **Live transcription** — visible transcript alongside the conversation
- **Push-to-talk & hands-free modes** — multiple browser interaction modes
- **Voice activity detection** — silence detection for turn-taking

Depends on: **v0.2.0** chat agent foundation.

---

## v0.4.0 — Solune MCP Server (aspirational)

Expose Solune as an MCP server so internal and external agents can interact with the platform through the same tool layer.

### Target capabilities

- **Solune MCP tools** — create projects, launch pipelines, query status, manage apps, inspect activity
- **External agent access** — VS Code Copilot, Claude, or any MCP-compatible agent can drive Solune
- **Internal agent access** — Solune chat reuses the same MCP tool contracts
- **Auth-scoped access** — user permissions flow through the MCP connection
- **Pipeline templates as tools** — higher-level single-call actions
- **Status subscriptions** — pipeline/event subscriptions for agents
- **Self-documenting schemas** — tools advertise their contracts dynamically

---

## v0.5.0 — Autonomous App Builder (aspirational)

Turn Solune into a prompt-to-application system that can plan, scaffold, and report progress through one conversation.

### Target capabilities

- **End-to-end creation flow** — one prompt creates a project, scaffolds an app, configures a pipeline, and launches execution
- **Smart scaffolding** — stack and structure selected from the prompt context
- **Pipeline auto-configuration** — difficulty drives the depth of automation used
- **Progress reporting** — chat, voice, or Signal updates during execution
- **Iteration support** — follow-up prompts target an existing app
- **Template library** — reusable starting points for common app categories

Depends on: `v0.2.0` (agent reasoning), `v0.3.0` (voice), and `v0.4.0` (MCP exposure).

---

## Ongoing — UX & Ecosystem

Themes that continue across releases:

### MCP ecosystem

- Awesome MCP integration and browsing
- MCP marketplace / install UI on the Tools page
- Expanded custom-agent tool interoperability

### Agentic DevOps

- Auto-retry with learning
- PR merge automation
- Multi-repo pipeline coordination
- Deploy-time automation after code generation

### Developer experience

- Agent performance insights
- Shareable pipeline templates
- Improved tablet / phone usability

---

## Timeline

| Version | Theme | Target |
|---------|-------|--------|
| **v0.2.0** | Microsoft Agent Framework chat | ✅ Shipped |
| **v0.3.0** | Full duplex voice (browser + Signal) | Aspirational |
| **v0.4.0** | Solune MCP server | Aspirational |
| **v0.5.0** | Autonomous app builder | Aspirational |

---

## Architecture Evolution

```text
v0.2.0 (current)                  v0.5.0 (target)
─────────────────                 ─────────────────────────────────

Voice/Chat ──► Agent Framework    Voice/Chat ──► Agent Framework
                 │                                  │
                 ├── Tools & Skills                 ├── Tools & Skills
                 └── MCP Servers (project)          ├── MCP Servers (external)
                                                    ├── Solune MCP (self-driving)
                                                    └── Pipeline Engine

Pipeline Engine ──► GitHub        Pipeline Engine ──► GitHub
  (current automation)              (agents use it as a tool)

Signal ──► Notifications + text   Signal ──► Full voice + text interaction
```
