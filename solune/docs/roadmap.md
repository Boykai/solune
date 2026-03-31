# Solune Roadmap

> From chat-driven pipelines to a voice-first, agent-native DevOps platform.

---

## v0.2.0 — Intelligent Chat Agent (Microsoft Agent Framework)

Replace the current completion-based chat with a Microsoft Agent Framework agent that can reason, ask clarifying questions, use tools, and take autonomous action.

### Features

- ✅ **Agent Framework chat agent** — multi-turn conversations with memory, tool use, and decision-making
- ✅ **Clarifying questions** — agent asks 2-3 targeted questions before acting ("What tech stack?", "Need auth?", "Any integrations?")
- ✅ **Difficulty assessment** — agent evaluates request complexity and selects the appropriate pipeline preset automatically
- ✅ **Autonomous project creation** — agent creates GitHub parent issues, configures pipelines, and launches execution from a single chat message
- ✅ **Tool/skill extensibility** — register custom tools and skills the chat agent can invoke via MCP
- ✅ **Model flexibility** — swap underlying models (GPT-4o, Claude, Llama) without changing agent logic
- ✅ **Conversation history** — persistent multi-session memory so the agent remembers project context

### Why first

This is the foundation. Voice, MCP exposure, and autonomous app creation all depend on having an intelligent agent that can reason about requests and orchestrate tools — not just generate text. Today's `AIAgentService` uses direct completion calls; the Agent Framework gives it tool use, planning, and multi-step execution.

---

## v0.3.0 — Full Duplex Voice Chat

Add a Jarvis-like voice interface on both browser and Signal. Today Solune has `VoiceInputButton` with Web Speech API for transcription — this upgrades to full duplex conversation.

### Features

- **Browser voice chat** — full duplex audio via WebRTC with real-time speech-to-text and text-to-speech
- **Natural conversation** — interrupt, ask follow-ups, and have back-and-forth dialogue while the agent works
- **Voice-driven actions** — "Create a new app called Stockwise using React and Azure" triggers the full creation flow
- **Signal voice support** — send voice messages via Signal, receive spoken status updates and pipeline notifications
- **Live transcription** — real-time transcript displayed in chat alongside voice interaction
- **Push-to-talk & hands-free modes** — toggle between always-listening and push-to-talk in browser
- **Voice activity detection** — smart silence detection to know when you've finished speaking

### Depends on

v0.2.0 — voice is an input channel for the agent, not a separate system

---

## v0.4.0 — Solune MCP Server

Expose Solune's full capabilities as an MCP server so any AI agent — internal or external — can interact with the platform.

### Features

- **Solune MCP tools** — create projects, launch pipelines, check board status, manage apps, query activity
- **External agent access** — Copilot in VS Code, Claude, or any MCP-compatible agent can drive Solune
- **Internal agent access** — Solune's own chat agent uses the same MCP tools (single source of truth)
- **Auth-scoped access** — MCP connections inherit the user's GitHub OAuth permissions
- **Pipeline templates as tools** — "launch spec-kit pipeline for issue #42" as a single tool call
- **Status subscriptions** — agents can subscribe to pipeline progress events
- **Self-documenting** — MCP server exposes tool schemas so agents discover capabilities dynamically

### Use cases

- Ask Copilot in VS Code: "What's the status of my pipelines in Solune?"
- Have Claude create a Solune project and launch a pipeline from a spec document
- Chain Solune into a larger multi-agent workflow as a "DevOps tool"

---

## v0.5.0 — Autonomous App Builder

The dream: "Build me a stock app with AI using Microsoft tools" → agent asks 2-3 questions → creates everything → reports back.

### Features

- **End-to-end creation flow** — single prompt creates project, scaffolds app, configures pipeline, launches agents, reports completion
- **Smart scaffolding** — agent selects tech stack, structure, and deployment target based on the request
- **Pipeline auto-configuration** — difficulty assessment drives pipeline selection (simple = fewer agents, complex = full Spec Kit + parallel)
- **Progress reporting** — real-time updates via chat, voice, or Signal as agents work
- **Iteration support** — "Add authentication to Stockwise" triggers a targeted pipeline run on the existing app
- **Template library** — pre-built app templates (SaaS, API, CLI, dashboard) the agent can start from

### Depends on

v0.2.0 (agent reasoning), v0.3.0 (voice channel), v0.4.0 (MCP tools for self-driving)

---

## Ongoing — UX & Ecosystem

Woven into each release:

### MCP Ecosystem

- **Awesome MCP integration** — browse and install community MCP servers from within Solune
- **MCP marketplace UI** — search, preview, one-click install on the Tools page
- **OpenClaw integration** — expanded agent tool capabilities

### Agentic DevOps

- **Auto-retry with learning** — failed stages retry with adjusted prompts based on error analysis
- **PR merge automation** — configurable auto-merge when Copilot review passes
- **Multi-repo pipelines** — orchestrate across repositories from a single pipeline
- **Deployment pipelines** — extend beyond code into build, test, and deploy

### Developer Experience

- **Agent performance insights** — which agents produce the best code, which models are fastest
- **Custom pipeline templates** — share and import configurations
- **Mobile-responsive layout** — full functionality on tablet and phone

---

## Timeline

| Version | Theme | Target |
|---------|-------|--------|
| **v0.2.0** | Microsoft Agent Framework chat | ✅ Shipped |
| **v0.3.0** | Full duplex voice (browser + Signal) | Q3 2026 |
| **v0.4.0** | Solune MCP server | Q3 2026 |
| **v0.5.0** | Autonomous app builder | Q4 2026 |

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
   (unchanged)                       (unchanged — agents use it as a tool)

 Signal ──► Notifications only     Signal ──► Full voice + text interaction
```

The pipeline engine stays as-is. The Agent Framework wraps only the chat experience, giving it reasoning, tool use, and multi-turn conversation. Voice and MCP are channels into that same agent.
