# API Reference

This document lists the HTTP, WebSocket, and SSE endpoints exposed by the Solune backend.

- **Base path**: `/api/v1`
- **Interactive docs**: enable `ENABLE_DOCS=true` and open `/api/docs`
- **Authentication**: unless noted otherwise, endpoints require an authenticated session cookie
- **Unauthenticated endpoints**: `/health`, `/auth/github`, `/auth/github/callback`, `/webhooks/github`, and `/auth/dev-login` when `DEBUG=true`

## Transport types

| Type | Meaning |
|------|---------|
| **HTTP** | Standard JSON request/response endpoints |
| **WS** | WebSocket endpoint |
| **SSE** | Server-Sent Events stream |

## Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Structured health check for Docker and load balancers |
| GET | `/ready` | Readiness probe for orchestration/hosting checks |
| GET | `/rate-limit/history` | Rate-limit time-series history |

## Authentication

| Method | Path | Description |
|--------|------|-------------|
| GET | `/auth/github` | Start the GitHub OAuth flow |
| GET | `/auth/github/callback` | Complete the GitHub OAuth callback and create a session |
| GET | `/auth/me` | Get the current authenticated user |
| POST | `/auth/logout` | Clear the current session |
| POST | `/auth/dev-login` | Dev-only PAT login when `DEBUG=true` |

## Projects

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects/create` | Create a standalone GitHub Project V2 |
| GET | `/projects` | List accessible GitHub Projects (`refresh=true` bypasses cache) |
| GET | `/projects/{project_id}` | Get project details including status columns |
| GET | `/projects/{project_id}/tasks` | Get project tasks/items |
| POST | `/projects/{project_id}/select` | Select the active project and start polling |
| WS | `/projects/{project_id}/subscribe` | WebSocket stream for project updates |
| GET | `/projects/{project_id}/events` | SSE fallback for real-time project events |

## Board

| Method | Path | Description |
|--------|------|-------------|
| GET | `/board/projects` | List projects that have board-compatible status fields |
| GET | `/board/projects/{project_id}` | Get board columns and items for a project |
| PATCH | `/board/projects/{project_id}/items/{item_id}/status` | Update a board item's status by name |

## Chat

### Conversations and messages

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat/conversations` | Create a new conversation for the current session |
| GET | `/chat/conversations` | List saved conversations for the current session |
| PATCH | `/chat/conversations/{conversation_id}` | Update a conversation title |
| DELETE | `/chat/conversations/{conversation_id}` | Delete a conversation |
| GET | `/chat/messages` | Get chat messages (supports pagination and optional `conversation_id`) |
| DELETE | `/chat/messages` | Clear chat history for the session or a specific conversation |
| POST | `/chat/messages` | Send a message and receive a standard JSON chat response |
| POST | `/chat/messages/stream` | Send a message and receive an SSE stream. Requires `ai_enhance=true` |
| POST | `/chat/upload` | Upload a file attachment for later chat use |

### Plan mode

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat/messages/plan` | Enter plan mode with a non-streaming response |
| POST | `/chat/messages/plan/stream` | Enter plan mode with streaming SSE + thinking events |
| GET | `/chat/plans/{plan_id}` | Retrieve a plan and all of its steps |
| PATCH | `/chat/plans/{plan_id}` | Update plan metadata (title and summary) |
| POST | `/chat/plans/{plan_id}/approve` | Approve a plan and launch it through the parent-issue pipeline flow |
| POST | `/chat/plans/{plan_id}/exit` | Exit plan mode and return to normal chat |
| GET | `/chat/plans/{plan_id}/history` | Get plan version history |
| POST | `/chat/plans/{plan_id}/steps` | Add a new plan step |
| PATCH | `/chat/plans/{plan_id}/steps/{step_id}` | Update a plan step |
| DELETE | `/chat/plans/{plan_id}/steps/{step_id}` | Delete a plan step |
| POST | `/chat/plans/{plan_id}/steps/reorder` | Reorder plan steps with DAG validation |
| POST | `/chat/plans/{plan_id}/steps/{step_id}/approve` | Approve or unapprove a single plan step |
| POST | `/chat/plans/{plan_id}/steps/{step_id}/feedback` | Submit feedback for plan refinement |
| GET | `/chat/plans/{plan_id}/export` | Export a plan as Markdown or GitHub issues |

### Proposals and streaming

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat/proposals/{proposal_id}/confirm` | Confirm an AI task proposal |
| DELETE | `/chat/proposals/{proposal_id}` | Cancel an AI task proposal |

`POST /chat/messages/stream` returns an SSE stream with these event types:

| Event | Description |
|-------|-------------|
| `token` | Incremental assistant text |
| `tool_call` | Agent tool invocation metadata |
| `tool_result` | Tool result payload |
| `done` | Final `ChatMessage` JSON |
| `error` | Stream error payload |

> **Rate limit**: `POST /chat/messages` and `POST /chat/messages/stream` are both limited to **10 requests per minute** per user.

### File upload constraints

| Constraint | Value |
|------------|-------|
| Maximum files per message | 5 |
| Maximum file size | 10 MB per file |
| Allowed types | png, jpg, jpeg, gif, webp, svg, pdf, txt, md, csv, json, yaml, yml, vtt, srt, zip |
| Blocked types | exe, sh, bat, cmd, js, py, rb |
| Transcript auto-detection | `.vtt` and `.srt` files are automatically detected as transcripts |

## Tasks

| Method | Path | Description |
|--------|------|-------------|
| POST | `/tasks` | Create a new task in a GitHub Project |
| PATCH | `/tasks/{task_id}/status` | Update a task status |

## Chores

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chores/{project_id}/seed-presets` | Seed built-in chore presets for a project |
| POST | `/chores/evaluate-triggers` | Evaluate active chores for trigger conditions |
| GET | `/chores/{project_id}/templates` | List available chore templates from `.github/ISSUE_TEMPLATE/` |
| GET | `/chores/{project_id}/chore-names` | List all chore names for a project |
| GET | `/chores/{project_id}` | List chores for a project |
| POST | `/chores/{project_id}` | Create a chore |
| PATCH | `/chores/{project_id}/{chore_id}` | Update a chore |
| DELETE | `/chores/{project_id}/{chore_id}` | Delete a chore and close any associated issue |
| POST | `/chores/{project_id}/{chore_id}/trigger` | Trigger a chore run manually |
| POST | `/chores/{project_id}/chat` | Refine chore input through chat |
| PUT | `/chores/{project_id}/{chore_id}/inline-update` | Inline-edit a chore and open a PR |
| POST | `/chores/{project_id}/create-with-merge` | Create a chore with branch + PR + auto-merge flow |

## Cleanup

| Method | Path | Description |
|--------|------|-------------|
| POST | `/cleanup/preflight` | Preview branch/PR/item cleanup without mutating anything |
| POST | `/cleanup/execute` | Execute cleanup for branches, PRs, and orphaned issues |
| GET | `/cleanup/history` | Get cleanup audit history |

## Settings

| Method | Path | Description |
|--------|------|-------------|
| GET | `/settings/user` | Get the authenticated user's effective settings |
| PUT | `/settings/user` | Update user settings |
| GET | `/settings/global` | Get global settings |
| PUT | `/settings/global` | Update global settings (admin only) |
| GET | `/settings/project/{project_id}` | Get effective project settings |
| PUT | `/settings/project/{project_id}` | Update project settings |
| GET | `/settings/models/{provider}` | Fetch available models for a provider |

## MCP Settings

These endpoints live under `/settings` because MCP configurations are user-scoped settings data.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/settings/mcps` | List MCP configurations for the current user |
| POST | `/settings/mcps` | Create an MCP configuration |
| PUT | `/settings/mcps/{mcp_id}` | Update an MCP configuration with optimistic concurrency control |
| DELETE | `/settings/mcps/{mcp_id}` | Delete an MCP configuration |

## Workflow & legacy pipeline orchestration

| Method | Path | Description |
|--------|------|-------------|
| POST | `/workflow/recommendations/{recommendation_id}/confirm` | Confirm an issue recommendation |
| POST | `/workflow/recommendations/{recommendation_id}/reject` | Reject an issue recommendation |
| POST | `/workflow/pipeline/{issue_number}/retry` | Retry a failed or stalled agent assignment |
| GET | `/workflow/config` | Get workflow configuration |
| PUT | `/workflow/config` | Update workflow configuration |
| GET | `/workflow/agents` | List available agents for the selected repository |
| GET | `/workflow/transitions` | Get workflow transition history |
| GET | `/workflow/pipeline-states` | Get all active pipeline states |
| GET | `/workflow/pipeline-states/{issue_number}` | Get pipeline state for a specific issue |
| POST | `/workflow/notify/in-review` | Send an In Review notification |
| GET | `/workflow/polling/status` | Get polling service status |
| POST | `/workflow/polling/check-issue/{issue_number}` | Manually check one issue for completion |
| POST | `/workflow/polling/start` | Start background polling |
| POST | `/workflow/polling/stop` | Stop background polling |
| POST | `/workflow/polling/check-all` | Check all In Progress issues |

## Signal

| Method | Path | Description |
|--------|------|-------------|
| GET | `/signal/connection` | Get Signal connection status |
| POST | `/signal/connection/link` | Generate a Signal linking QR code |
| GET | `/signal/connection/link/status` | Poll the link completion state |
| DELETE | `/signal/connection` | Disconnect Signal and purge linked state |
| GET | `/signal/preferences` | Get Signal notification preferences |
| PUT | `/signal/preferences` | Update Signal notification preferences |
| GET | `/signal/banners` | List active conflict banners |
| POST | `/signal/banners/{banner_id}/dismiss` | Dismiss a conflict banner |
| POST | `/signal/webhook/inbound` | Receive inbound Signal webhook traffic |

## Agents

| Method | Path | Description |
|--------|------|-------------|
| GET | `/agents/{project_id}` | List agents merged from SQLite + `.github/agents/` |
| GET | `/agents/{project_id}/pending` | List pending agent PR work |
| DELETE | `/agents/{project_id}/pending` | Purge stale pending agent rows |
| PATCH | `/agents/{project_id}/bulk-model` | Bulk-update default models for active agents |
| GET | `/agents/{project_id}/catalog` | Browse catalog agents from Awesome Copilot |
| POST | `/agents/{project_id}/import` | Import a catalog agent into the project |
| POST | `/agents/{project_id}/{agent_id}/install` | Install an imported agent into the repository |
| POST | `/agents/{project_id}` | Create a new custom agent |
| PATCH | `/agents/{project_id}/{agent_id}` | Update an existing custom agent |
| DELETE | `/agents/{project_id}/{agent_id}` | Delete an agent through a PR-backed flow |
| POST | `/agents/{project_id}/chat` | Refine agent content through chat |
| POST | `/agents/{project_id}/sync-mcps` | Synchronize MCP config across agent files |
| GET | `/agents/{project_id}/{agent_id}/tools` | List MCP tools assigned to an agent |
| PUT | `/agents/{project_id}/{agent_id}/tools` | Replace MCP tools assigned to an agent |

## Pipelines

| Method | Path | Description |
|--------|------|-------------|
| GET | `/pipelines/{project_id}` | List pipeline configurations |
| POST | `/pipelines/{project_id}/seed-presets` | Seed preset pipeline configs |
| GET | `/pipelines/{project_id}/assignment` | Get the active pipeline assignment |
| PUT | `/pipelines/{project_id}/assignment` | Set the active pipeline assignment |
| POST | `/pipelines/{project_id}/launch` | Create an issue from pasted content and launch a pipeline |
| POST | `/pipelines/{project_id}` | Create a pipeline configuration |
| GET | `/pipelines/{project_id}/{pipeline_id}` | Get one pipeline configuration |
| PUT | `/pipelines/{project_id}/{pipeline_id}` | Update a pipeline configuration |
| DELETE | `/pipelines/{project_id}/{pipeline_id}` | Delete a pipeline configuration |
| POST | `/pipelines/{pipeline_id}/runs` | Create and start a pipeline run |
| GET | `/pipelines/{pipeline_id}/runs` | List pipeline runs |
| GET | `/pipelines/{pipeline_id}/runs/{run_id}` | Get full state for a pipeline run |
| POST | `/pipelines/{pipeline_id}/runs/{run_id}/cancel` | Cancel a run |
| POST | `/pipelines/{pipeline_id}/runs/{run_id}/recover` | Recover and resume a run |
| GET | `/pipelines/{pipeline_id}/groups` | List stage groups for a pipeline |
| PUT | `/pipelines/{pipeline_id}/groups` | Create or replace stage groups atomically |

## Tools

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tools/presets` | List built-in MCP tool presets |
| GET | `/tools/{project_id}` | List tool configurations for a project |
| POST | `/tools/{project_id}` | Create/upload a tool configuration |
| GET | `/tools/{project_id}/repo-config` | Read repository MCP config files |
| PUT | `/tools/{project_id}/repo-config/{server_name}` | Update a repository MCP server entry |
| DELETE | `/tools/{project_id}/repo-config/{server_name}` | Delete a repository MCP server entry |
| GET | `/tools/{project_id}/{tool_id}` | Get one tool configuration |
| PUT | `/tools/{project_id}/{tool_id}` | Update a tool configuration |
| POST | `/tools/{project_id}/{tool_id}/sync` | Sync a tool configuration from its remote source |
| DELETE | `/tools/{project_id}/{tool_id}` | Delete a tool configuration |

## Metadata

| Method | Path | Description |
|--------|------|-------------|
| GET | `/metadata/{owner}/{repo}` | Get cached repository metadata |
| POST | `/metadata/{owner}/{repo}/refresh` | Force-refresh repository metadata |

## Onboarding

| Method | Path | Description |
|--------|------|-------------|
| GET | `/onboarding/state` | Get onboarding tour state |
| PUT | `/onboarding/state` | Update onboarding tour state |

## Templates

| Method | Path | Description |
|--------|------|-------------|
| GET | `/templates` | List available app templates |
| GET | `/templates/{template_id}` | Get detailed app template metadata and manifest |

## Apps

| Method | Path | Description |
|--------|------|-------------|
| GET | `/apps/owners` | List owners where the current user can create repos |
| GET | `/apps` | List managed apps |
| POST | `/apps` | Create a new app |
| GET | `/apps/{app_name}` | Get app details |
| PUT | `/apps/{app_name}` | Update app metadata |
| GET | `/apps/{app_name}/assets` | Get the app's GitHub asset inventory |
| DELETE | `/apps/{app_name}` | Delete an app (`force=true` performs full asset cleanup) |
| POST | `/apps/{app_name}/start` | Start an app |
| POST | `/apps/{app_name}/stop` | Stop an app |
| GET | `/apps/{app_name}/status` | Get the current app status |
| POST | `/apps/import` | Import an existing GitHub repo as an app |
| POST | `/apps/{app_name}/build` | Trigger a full app build from a template |
| POST | `/apps/{app_name}/iterate` | Launch an iteration flow for an existing app |
| POST | `/apps/create-with-plan` | Start plan-driven, multi-phase app creation |
| GET | `/apps/{app_name}/plan-status` | Poll the plan-orchestration status for an app |

## Activity

| Method | Path | Description |
|--------|------|-------------|
| GET | `/activity` | Get the project-scoped activity feed |
| GET | `/activity/stats` | Get aggregated activity statistics |
| GET | `/activity/{entity_type}/{entity_id}` | Get activity history for a specific entity |

## Webhooks

| Method | Path | Description |
|--------|------|-------------|
| POST | `/webhooks/github` | Handle inbound GitHub webhook events |

---

## What's Next?

- [Architecture](architecture.md) — understand how the frontend, backend, and sidecar interact
- [Configuration](configuration.md) — review environment variables and operational settings
- [Troubleshooting](troubleshooting.md) — common API/runtime issues and their fixes
