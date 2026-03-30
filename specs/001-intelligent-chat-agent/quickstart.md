# Quickstart: Intelligent Chat Agent (Microsoft Agent Framework)

**Feature**: 001-intelligent-chat-agent | **Date**: 2026-03-30

## Prerequisites

- Python ≥3.12
- Node.js ≥18 (for frontend)
- Docker & Docker Compose (for full deployment)
- GitHub OAuth application credentials (for Copilot provider)
- Azure OpenAI deployment (optional, for Azure provider)

## 1. Install Backend Dependencies

```bash
cd solune/backend

# Install updated dependencies (includes agent-framework packages)
pip install -e ".[dev]" --pre
```

The `--pre` flag is required because `agent-framework-core`, `agent-framework-azure-ai`, and `agent-framework-github-copilot` are in Release Candidate status.

### New Dependencies Added

| Package | Purpose |
|---------|---------|
| `agent-framework-core` | Core agent orchestration, tools, sessions, middleware |
| `agent-framework-azure-ai` | Azure OpenAI chat client for MAF |
| `agent-framework-github-copilot` | GitHub Copilot provider for MAF |
| `sse-starlette` | Server-Sent Events support for FastAPI streaming |

## 2. Configure Environment

Copy the example environment file and configure:

```bash
cp .env.example .env
```

### Required Environment Variables

```env
# Existing (unchanged)
AI_PROVIDER=copilot              # or "azure_openai"
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_secret

# For Azure OpenAI provider (if AI_PROVIDER=azure_openai)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_DEPLOYMENT=your_deployment_name

# New (optional, with defaults)
AGENT_SESSION_TTL_SECONDS=3600        # Agent session cache TTL (default: 1 hour)
AGENT_MAX_CONCURRENT_SESSIONS=100     # Max concurrent agent sessions
AGENT_STREAMING_ENABLED=true          # Enable SSE streaming endpoint
```

## 3. Run Backend

```bash
cd solune/backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 4. Run Frontend

```bash
cd solune/frontend
npm install
npm run dev
```

## 5. Run Tests

### Backend Tests

```bash
cd solune/backend

# Run all unit tests
pytest tests/unit/ -v

# Run only agent-related tests
pytest tests/unit/test_agent_tools.py tests/unit/test_chat_agent.py -v

# Run with coverage
pytest tests/unit/ --cov=src --cov-report=term-missing
```

### Frontend Tests

```bash
cd solune/frontend
npm run test
```

## 6. Docker Deployment

```bash
cd solune
docker compose up --build
```

Verify health:
```bash
curl http://localhost:8000/api/v1/health
```

## 7. Verify the Migration

### Test 1: Basic Chat (Non-Streaming)

```bash
curl -X POST http://localhost:8000/api/v1/chat/messages \
  -H "Content-Type: application/json" \
  -H "Cookie: session=<your_session_cookie>" \
  -d '{"content": "Create a task for adding dark mode support", "ai_enhance": true}'
```

Expected: Agent selects `create_task_proposal` tool and returns a `ChatMessage` with `action_type: "task_create"`.

### Test 2: Feature Request Detection

```bash
curl -X POST http://localhost:8000/api/v1/chat/messages \
  -H "Content-Type: application/json" \
  -H "Cookie: session=<your_session_cookie>" \
  -d '{"content": "I want a dark mode toggle in the settings page with system preference detection"}'
```

Expected: Agent selects `create_issue_recommendation` tool and returns `action_type: "issue_create"` with full `IssueRecommendation` data.

### Test 3: Streaming Response

```bash
curl -X POST http://localhost:8000/api/v1/chat/messages/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -H "Cookie: session=<your_session_cookie>" \
  -d '{"content": "Help me plan a new authentication feature"}' \
  --no-buffer
```

Expected: SSE events stream progressively with `event: token` containing text chunks, ending with `event: done`.

### Test 4: Clarifying Questions

```bash
curl -X POST http://localhost:8000/api/v1/chat/messages \
  -H "Content-Type: application/json" \
  -H "Cookie: session=<your_session_cookie>" \
  -d '{"content": "I need something for my project"}'
```

Expected: Agent recognizes ambiguity and asks 2–3 clarifying questions before taking action.

### Test 5: ai_enhance=False Bypass

```bash
curl -X POST http://localhost:8000/api/v1/chat/messages \
  -H "Content-Type: application/json" \
  -H "Cookie: session=<your_session_cookie>" \
  -d '{"content": "Fix login bug", "ai_enhance": false}'
```

Expected: Simple title-only task generation without agent invocation (preserves v0.1.x behavior).

### Test 6: Provider Switching

```bash
# Test with Copilot provider
AI_PROVIDER=copilot uvicorn src.main:app --port 8000

# Test with Azure OpenAI provider
AI_PROVIDER=azure_openai uvicorn src.main:app --port 8000
```

Both should produce equivalent results for the same chat messages.

## 8. Key Architecture Changes

### Before (v0.1.x)

```
User Message → chat.py priority cascade:
  Priority 0:   /agent command → AgentCreator
  Priority 0.5: Transcript detection → AIAgentService.analyze_transcript()
  Priority 1:   Feature request → AIAgentService.detect_feature_request_intent()
  Priority 2:   Status change → AIAgentService.parse_status_change_request()
  Priority 3:   Task generation → AIAgentService.generate_task()
```

### After (v0.2.0)

```
User Message → chat.py:
  If /agent command → AgentCreator (unchanged)
  If ai_enhance=False → simple generation (unchanged)
  Else → ChatAgentService.run(message, session_id, context)
    → Agent reasons about intent
    → Agent selects tool (create_task_proposal, create_issue_recommendation, etc.)
    → Tool executes with runtime context
    → Response converted to ChatMessage
```

## 9. Deprecation Notes

The following modules are deprecated in v0.2.0 and will be removed in v0.3.0:

| Module | Replacement | Notes |
|--------|-------------|-------|
| `src/services/ai_agent.py` | `src/services/chat_agent.py` + `src/services/agent_tools.py` | `identify_target_task()` preserved (no deprecation warning) |
| `src/services/completion_providers.py` | `src/services/agent_provider.py` | Provider factory handles both backends |
| `src/prompts/task_generation.py` | `src/prompts/agent_instructions.py` | Single unified prompt |
| `src/prompts/issue_generation.py` | `src/prompts/agent_instructions.py` | Single unified prompt |
| `src/prompts/transcript_analysis.py` | `src/prompts/agent_instructions.py` | Single unified prompt |

Calling deprecated methods will emit `DeprecationWarning`:
```
DeprecationWarning: AIAgentService.generate_task() is deprecated. Use ChatAgentService.run() instead. Will be removed in v0.3.0.
```

## 10. Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: agent_framework` | Run `pip install -e ".[dev]" --pre` — the `--pre` flag is required |
| Streaming endpoint returns 503 | Check `AGENT_STREAMING_ENABLED=true` in environment |
| Copilot provider fails with 401 | User needs to re-authenticate via GitHub OAuth; check token expiry |
| Agent selects wrong tool | Review system instructions in `src/prompts/agent_instructions.py`; check that tool descriptions are clear |
| Deprecation warnings in logs | Expected during transition; deprecated code still works |
| Session state lost between messages | Check `AGENT_SESSION_TTL_SECONDS` — sessions expire after TTL |
