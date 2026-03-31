# Quickstart: Solune MCP Server

**Feature**: 001-mcp-server | **Date**: 2026-03-31
**Audience**: Developers implementing or testing the MCP server feature

## Prerequisites

- Python ≥3.12
- Docker (for containerized development)
- A GitHub Personal Access Token (PAT) with `repo` and `read:org` scopes
- An MCP-compatible client (VS Code Copilot, Claude Desktop, MCP Inspector, or any MCP SDK client)

## 1. Enable the MCP Server

Add the following environment variables to your `.env` file or Docker Compose configuration:

```env
MCP_SERVER_ENABLED=true
MCP_SERVER_NAME=solune
```

The MCP server defaults to **disabled**. Setting `MCP_SERVER_ENABLED=true` mounts the MCP endpoint at `/api/v1/mcp` within the existing FastAPI application.

## 2. Install the MCP Dependency

The `mcp` Python SDK is required:

```bash
cd solune/backend
pip install "mcp>=1.26.0,<2"
```

Or via the project's dependency manager:

```bash
cd solune/backend
uv sync
```

## 3. Start the Server

```bash
cd solune/backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Or with Docker Compose:

```bash
docker-compose up --build
```

When the MCP server is enabled, you'll see a log line on startup:

```
INFO: MCP server mounted at /api/v1/mcp (name=solune)
```

## 4. Connect an MCP Client

### VS Code Copilot

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "solune": {
      "type": "http",
      "url": "http://localhost:8000/api/v1/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_GITHUB_PAT>"
      }
    }
  }
}
```

### Claude Desktop

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "solune": {
      "transport": "streamable-http",
      "url": "http://localhost:8000/api/v1/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_GITHUB_PAT>"
      }
    }
  }
}
```

### MCP Inspector

```bash
npx @modelcontextprotocol/inspector \
  --transport streamable-http \
  --url http://localhost:8000/api/v1/mcp \
  --header "Authorization: Bearer <YOUR_GITHUB_PAT>"
```

### Python MCP Client (SDK)

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client(
        url="http://localhost:8000/api/v1/mcp",
        headers={"Authorization": "Bearer <YOUR_GITHUB_PAT>"}
    ) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"  {tool.name}: {tool.description}")

            # Call a tool
            result = await session.call_tool("list_projects", arguments={})
            print(result)
```

## 5. Verify the Connection

### Auto-Discovery Endpoint

```bash
curl http://localhost:8000/api/v1/mcp/config
```

Expected response:

```json
{
  "server_name": "solune",
  "enabled": true,
  "url": "/api/v1/mcp",
  "transport": "streamable-http",
  "auth": {
    "type": "bearer",
    "description": "Provide a GitHub Personal Access Token (PAT) as a Bearer token."
  }
}
```

### Tool Discovery

Once connected, list available tools:

```
> list tools
  list_projects: List all GitHub projects accessible to the authenticated user
  get_project: Get detailed information about a specific GitHub project
  get_board: Get the full kanban board state for a project
  create_task: Create a new task with sub-issue generation
  launch_pipeline: Launch a development pipeline
  ... (22 tools total)
```

### Call a Tool

```
> call list_projects
{
  "projects": [
    {
      "project_id": "PVT_kwDOBx...",
      "name": "Solune Board",
      "url": "https://github.com/users/Boykai/projects/1"
    }
  ]
}
```

## 6. Feature Flag Behavior

| `MCP_SERVER_ENABLED` | Behavior |
|----------------------|----------|
| `false` (default)    | MCP endpoint not mounted. Requests to `/api/v1/mcp` return 404. |
| `true`               | MCP endpoint mounted. Tools, resources, and prompts available. |

## 7. Authentication Flow

1. Client sends `Authorization: Bearer <github_pat>` header
2. Server calls `GET https://api.github.com/user` with the token
3. On success: user identity (login, id) cached for 60 seconds
4. On failure: connection rejected with authentication error
5. Each tool call with a `project_id` validates user access to that project

## 8. Available Prompts

Ask your MCP client to use these guided workflows:

- **`create-project`** — Step-by-step project creation
- **`pipeline-status`** — Check all running pipelines
- **`daily-standup`** — Summarize recent activity across projects

## 9. Resource Subscriptions

Subscribe to real-time updates:

- `solune://projects/{project_id}/pipelines` — Pipeline state changes
- `solune://projects/{project_id}/board` — Board item movements
- `solune://projects/{project_id}/activity` — New activity events

## 10. Running Tests

```bash
# Unit tests for MCP server
cd solune/backend
pytest tests/unit/test_mcp_server/ -v

# Integration tests (requires running server)
pytest tests/integration/test_mcp_e2e.py -v

# All tests
pytest tests/ -v --timeout=30
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `404 on /api/v1/mcp` | Set `MCP_SERVER_ENABLED=true` and restart |
| `Authentication failed` | Verify your GitHub PAT has `repo` and `read:org` scopes |
| `Rate limited` | Wait 60 seconds. Max 10 verification attempts per minute per token |
| `Project access denied` | Ensure your GitHub account has access to the referenced project |
| `Tool not found` | Check tool name spelling. Use `list_tools` to see all available tools |
