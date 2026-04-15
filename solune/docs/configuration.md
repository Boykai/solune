# Configuration

This document lists every environment variable currently read by `backend/src/config.py` plus the frontend API base URL used by Vite.

> **Quick start — the only 3 required variables:** `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `SESSION_SECRET_KEY`

All backend configuration is read from environment variables through `pydantic-settings`. Copy `.env.example` to `.env` and customize as needed.

## Environment Variables

### Required

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_CLIENT_ID` | — | GitHub OAuth application client ID |
| `GITHUB_CLIENT_SECRET` | — | GitHub OAuth application client secret |
| `SESSION_SECRET_KEY` | — | Random secret used to encrypt/sign session state |

### GitHub OAuth

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_REDIRECT_URI` | `http://localhost:8000/api/v1/auth/github/callback` | OAuth callback URL configured in the GitHub app |
| `FRONTEND_URL` | `http://localhost:5173` | Browser URL used for redirects and secure-cookie auto-detection |

> **Docker note:** When running via Docker Compose, set `GITHUB_REDIRECT_URI` to `http://localhost:5173/api/v1/auth/github/callback` because nginx proxies `/api/v1` to the backend. Without Docker, the default `localhost:8000` target is correct.

### AI Provider

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_PROVIDER` | `copilot` | LLM provider: `copilot` or `azure_openai` |
| `COPILOT_MODEL` | `gpt-4o` | Default GitHub Copilot model |
| `AZURE_OPENAI_ENDPOINT` | — | Azure OpenAI endpoint when using `azure_openai` |
| `AZURE_OPENAI_KEY` | — | Azure OpenAI API key (optional if managed identity is used) |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4` | Azure OpenAI deployment name |

### Defaults and routing

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_REPOSITORY` | — | Default repository in `owner/repo` format |
| `DEFAULT_PROJECT_ID` | — | Default GitHub Project V2 node ID |
| `DEFAULT_ASSIGNEE` | `""` | Default assignee for pipeline-created issues |

### Server and HTTP behavior

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Backend bind host |
| `PORT` | `8000` | Backend bind port |
| `DEBUG` | `false` | Enables development behavior and relaxes production validation |
| `ENABLE_DOCS` | `false` | Serve `/api/docs` and `/api/redoc` |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |

> **Docker note:** The Docker Compose file overrides this to `http://localhost:5173,http://localhost:80,http://frontend` to allow inter-container traffic. Local development only needs the default.
| `API_TIMEOUT_SECONDS` | `30` | Timeout for outbound API calls |

### Sessions and cookies

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_EXPIRE_HOURS` | `8` | Session TTL in hours |
| `SESSION_CLEANUP_INTERVAL` | `3600` | Expired-session cleanup interval in seconds |
| `COOKIE_SECURE` | `false` | Force `Secure` cookies (also auto-enabled for `https://` frontend URLs) |
| `COOKIE_MAX_AGE` | — | Explicit cookie max-age in seconds; unset means session cookie |

### Database and cache

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `/var/lib/solune/data/settings.db` | SQLite database path |
| `CACHE_TTL_SECONDS` | `300` | General in-memory cache TTL |
| `METADATA_CACHE_TTL_SECONDS` | `300` | Repository metadata cache TTL |

### Webhook and polling

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_WEBHOOK_SECRET` | — | Secret used to validate GitHub webhooks |
| `GITHUB_WEBHOOK_TOKEN` | — | PAT/classic token used for webhook follow-up actions |
| `COPILOT_POLLING_INTERVAL` | `60` | Polling interval in seconds (`0` disables polling) |

### Security and admin

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_GITHUB_USER_ID` | — | Numeric GitHub user ID for the Solune admin |
| `ENCRYPTION_KEY` | — | Fernet key used to encrypt GitHub tokens at rest |

### Signal integration

| Variable | Default | Description |
|----------|---------|-------------|
| `SIGNAL_API_URL` | `http://signal-api:8080` | URL of the Signal sidecar |
| `SIGNAL_PHONE_NUMBER` | — | Dedicated Signal phone number |
| `SIGNAL_WEBHOOK_SECRET` | — | Secret used to verify inbound Signal webhooks |

### Browser agent catalog

| Variable | Default | Description |
|----------|---------|-------------|
| `CATALOG_INDEX_URL` | `https://awesome-copilot.github.com/llms.txt` | Catalog index for the Browser Agents modal |
| `CATALOG_FETCH_TIMEOUT_SECONDS` | `15.0` | Timeout when fetching catalog or raw agent definitions |

### Agent Framework

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_SESSION_TTL_SECONDS` | `3600` | Idle Agent Framework session TTL |
| `AGENT_MAX_CONCURRENT_SESSIONS` | `100` | Max in-memory concurrent agent sessions |
| `AGENT_STREAMING_ENABLED` | `true` | Enable the chat streaming endpoint |
| `AGENT_COPILOT_TIMEOUT_SECONDS` | `120` | Timeout for Copilot SDK `send_and_wait` calls |
| `CHAT_AUTO_CREATE_ENABLED` | `true` | Allow chat-driven issue creation and pipeline launch |

### Observability and alerting

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_ENABLED` | `false` | Enable OpenTelemetry instrumentation |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP endpoint used by the `otel_endpoint` config field |

> **Docker note:** When the `observability` Docker Compose profile is active, the root `docker-compose.yml` overrides this to `http://jaeger:4317` to reach the Jaeger container.
| `OTEL_SERVICE_NAME` | `solune-backend` | Service name reported to OpenTelemetry |
| `SENTRY_DSN` | `""` | Sentry DSN; empty disables Sentry |
| `PIPELINE_STALL_ALERT_MINUTES` | `30` | Minutes before a stalled pipeline alerts |
| `AGENT_TIMEOUT_ALERT_MINUTES` | `15` | Minutes before an agent timeout alerts |
| `RATE_LIMIT_CRITICAL_THRESHOLD` | `20` | Remaining GitHub requests threshold for critical alerts |
| `ALERT_WEBHOOK_URL` | `""` | Optional webhook target for alert delivery |
| `ALERT_COOLDOWN_MINUTES` | `15` | Alert deduplication cooldown window |

### MCP server

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_SERVER_ENABLED` | `false` | Mount the Solune MCP server at `/api/v1/mcp` |
| `MCP_SERVER_NAME` | `solune` | Server name exposed in MCP metadata |

### Frontend (Vite)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `/api/v1` | Frontend API base URL |

## Production validation notes

When `DEBUG=false`, Solune additionally enforces:

- `ENCRYPTION_KEY` must be set
- `GITHUB_WEBHOOK_SECRET` must be set
- `SESSION_SECRET_KEY` must be at least 64 characters
- cookies must resolve to `Secure`
- `ADMIN_GITHUB_USER_ID` must be a positive integer
- `DATABASE_PATH` must be absolute (or `:memory:` in tests)

If `AI_PROVIDER=azure_openai`, `AZURE_OPENAI_ENDPOINT` must be present. `AZURE_OPENAI_KEY` is optional because the backend can fall back to managed identity / `az login`.

## Database schema

SQLite runs in WAL mode at `DATABASE_PATH`. Startup automatically applies migrations `023` through `044`.

### Migration files

| Migration | Purpose |
|-----------|---------|
| `023_consolidated_schema.sql` | Consolidated schema baseline replacing legacy `001–022` files |
| `024_apps.sql` | Apps tables and new-repo support |
| `025_performance_indexes.sql` | Performance indexes for common queries |
| `026_done_items_cache.sql` | Durable cache of Done-status board items |
| `027_pipeline_state_persistence.sql` | Pipeline run persistence and onboarding state |
| `028_queue_mode.sql` | Queue-mode toggle for project settings |
| `029_activity_events.sql` | Unified activity-event storage |
| `030_copilot_review_requests.sql` | Copilot review-request persistence |
| `031_auto_merge_and_pipeline_states.sql` | Auto-merge settings and concurrent state tracking |
| `032_phase8_mcp_version.sql` | MCP optimistic-concurrency version column |
| `033_phase8_collision_events.sql` | MCP collision audit table |
| `034_phase8_recovery_log.sql` | Recovery log auditing |
| `035_chat_plans.sql` | Chat plan records and step storage |
| `036_app_template_fields.sql` | Additional app template metadata |
| `037_agent_import.sql` | Imported-agent support |
| `038_reasoning_effort_columns.sql` | Reasoning-effort persistence |
| `039_user_scoped_configs.sql` | User-scoped config separation |
| `040_plan_versioning.sql` | Plan version history |
| `041_plan_step_status.sql` | Per-step plan approval status |
| `042_app_plan_orchestrations.sql` | Plan-driven app orchestration tracking |
| `043_plan_selected_pipeline.sql` | Selected pipeline persistence for plans |
| `044_conversations.sql` | Persisted chat conversations |

## Workflow settings

Workflow and pipeline mappings are stored in SQLite and can be managed through the pipeline UI, Settings UI, or `PUT /api/v1/workflow/config`.

---

## What's next?

- [Setup Guide](setup.md) — installation and local environment setup
- [Architecture](architecture.md) — service boundaries and runtime topology
- [Troubleshooting](troubleshooting.md) — common configuration mistakes and recovery steps
