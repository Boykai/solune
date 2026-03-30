# Quickstart: Complete v0.2.0 — Intelligent Chat Agent

**Feature**: `001-intelligent-chat-agent` | **Date**: 2026-03-30

## Prerequisites

- Python >=3.12
- Docker & Docker Compose
- GitHub OAuth application configured (existing setup)
- `uv` package manager (for local development)

## Development Setup

### 1. Environment Variables

Add the new setting to your `.env` file (or environment):

```bash
# Existing settings (required)
AI_PROVIDER=copilot
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret

# New setting for v0.2.0 completion
CHAT_AUTO_CREATE_ENABLED=false    # Set to true to enable autonomous project creation
```

### 2. Run Backend Locally

```bash
cd solune/backend

# Install dependencies (includes agent-framework packages)
uv sync --prerelease=allow

# Run the development server
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Run via Docker Compose

```bash
docker compose build backend
docker compose up -d
```

## Implementation Order

### Phase 1: Difficulty Assessment & Pipeline Selection (P1)

Files to modify (can be done in parallel):

1. **`backend/src/services/agent_tools.py`** — Add `assess_difficulty` and `select_pipeline_preset` tools
2. **`backend/src/models/chat.py`** — Add `PIPELINE_LAUNCH` to `ActionType`
3. **`backend/src/config.py`** — Add `CHAT_AUTO_CREATE_ENABLED` setting
4. **`backend/src/prompts/agent_instructions.py`** — Add difficulty assessment workflow instructions
5. **`backend/tests/unit/test_agent_tools.py`** — Add tests for new tools

### Phase 2: Autonomous Project Creation (P2)

Files to modify (depends on Phase 1):

1. **`backend/src/services/agent_tools.py`** — Add `create_project_issue` and `launch_pipeline` tools
2. **`backend/src/services/chat_agent.py`** — Handle `pipeline_launch` action in response conversion
3. **`backend/src/prompts/agent_instructions.py`** — Add autonomous workflow instructions
4. **`backend/tests/unit/test_agent_tools.py`** — Add tests for creation tools
5. **`backend/tests/unit/test_chat_agent.py`** — Add test for pipeline_launch response

### Phase 3: MCP Tool Extensibility (P3)

Files to modify (can parallel with Phase 2):

1. **`backend/src/services/agent_tools.py`** — Add `load_mcp_tools()` function
2. **`backend/src/services/agent_provider.py`** — Accept `mcp_servers` parameter
3. **`backend/src/services/chat_agent.py`** — Wire MCP loading into agent creation
4. **`backend/tests/unit/test_agent_tools.py`** — Add tests for MCP loading

## Verification Commands

```bash
cd solune/backend

# Run unit tests for modified files
uv run pytest tests/unit/test_agent_tools.py tests/unit/test_chat_agent.py -x -v

# Lint and format check
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Type checking
uv run pyright src/services/agent_tools.py src/services/chat_agent.py src/models/chat.py

# Full test suite
uv run pytest --cov=src -x

# Docker build verification
docker compose build backend && docker compose up -d
```

## Key Patterns

### Adding a New Tool

```python
# In agent_tools.py
@tool
async def my_new_tool(
    context: FunctionInvocationContext,
    param1: str,
    param2: str,
) -> ToolResult:
    """Tool description shown to the LLM."""
    # Access session state
    project_name = context.session.state.get("project_name", "Unknown")

    # Do work...

    # Return structured result
    return ToolResult(
        content="Human-readable result",
        action_type="action_name",  # or None for informational
        action_data={"key": "value"},  # or None
    )
```

Then register in `register_tools()`:
```python
def register_tools() -> list:
    return [
        # ... existing tools ...
        my_new_tool,
    ]
```

### Difficulty → Preset Mapping

```python
DIFFICULTY_PRESET_MAP = {
    "XS": "github-copilot",
    "S": "easy",
    "M": "medium",
    "L": "hard",
    "XL": "expert",
}

# Usage: DIFFICULTY_PRESET_MAP.get(difficulty, "medium")
```

### Config Setting Pattern

```python
# In config.py Settings class
chat_auto_create_enabled: bool = False

# In tool code
from src.config import get_settings
settings = get_settings()
if not settings.chat_auto_create_enabled:
    return ToolResult(content="Auto-creation disabled...", action_type=None, action_data=None)
```

## End-to-End Test Scenarios

### Scenario 1: Auto-Create Enabled

1. Set `CHAT_AUTO_CREATE_ENABLED=true`
2. Send: "Build me a stock tracking app with React and Azure"
3. Agent asks clarifying questions (if needed)
4. Agent calls `assess_difficulty` → "M" (medium)
5. Agent calls `select_pipeline_preset` → "medium" preset
6. Agent asks "Shall I proceed?"
7. User confirms
8. Agent calls `create_project_issue` → GitHub issue created
9. Agent calls `launch_pipeline` → Pipeline launched
10. Agent reports: issue URL + pipeline status

### Scenario 2: Auto-Create Disabled (Default)

1. `CHAT_AUTO_CREATE_ENABLED=false` (default)
2. Send: "Build me a stock tracking app with React and Azure"
3. Agent calls `assess_difficulty` → "M" (medium)
4. Agent calls `select_pipeline_preset` → "medium" preset
5. Agent calls `create_project_issue` → Returns proposal (no issue created)
6. Agent presents: "Here's what I'd create: [details]. Enable autonomous creation or create manually."
