# Data Model: MCP Catalog on Tools Page

**Feature**: MCP Catalog on Tools Page | **Date**: 2026-04-15 | **Status**: Complete

## Entity: CatalogInstallConfig

Normalized transport-specific installation instructions for one upstream MCP server.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `transport` | `string` | Required; expected values: `http`, `sse`, `stdio`, `local`; unsupported values are rejected at import time | Transport type used to determine how the server maps into `mcp.json` |
| `url` | `string \| null` | Required for `http` and `sse`; omitted otherwise | Remote MCP endpoint URL |
| `command` | `string \| null` | Required for `stdio` and `local`; omitted otherwise | Executable command for local/server-process transports |
| `args` | `string[]` | Defaults to `[]` | Command arguments for `stdio`/`local` transports |
| `env` | `Record<string, unknown>` | Defaults to `{}` | Optional environment variables preserved during import |
| `headers` | `Record<string, unknown>` | Defaults to `{}`; used only for remote transports | Optional request headers for remote transports |
| `tools` | `string[]` | Defaults to `[]` | Optional explicit tool exposure list provided by the upstream catalog |

### Validation Rules

- `transport` is normalized from explicit upstream values or inferred from `url`/`command` when absent.
- Remote transports (`http`, `sse`) require `url`.
- Local transports (`stdio`, `local`) require `command`.
- Unsupported transports fail import with a validation error rather than being partially mapped.

---

## Entity: CatalogMcpServer

One normalized MCP server surfaced from the external catalog to the Solune UI.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | `string` | Required; unique within catalog response | Stable catalog identifier, falling back to a slugified name when missing upstream |
| `name` | `string` | Required; non-empty | Display name shown on the card and used as the imported tool name |
| `description` | `string` | Required; defaults to `name` when upstream description is missing | Summary text shown in the browse grid and reused for the imported tool |
| `repo_url` | `string \| null` | Optional; must be sanitized HTTPS before surfacing | External repository link rendered on the card |
| `category` | `string \| null` | Optional; may fall back to the first upstream tag | Category used for browse filtering and card labeling |
| `server_type` | `string` | Required; derived from supported transport or treated as `remote` for display | Badge value that drives Local/Remote presentation |
| `install_config` | `CatalogInstallConfig` | Required | Normalized install instructions used for import |
| `quality_score` | `string \| null` | Optional | Glama quality score (for example `A`, `B`, `C`, or a numeric string) |
| `already_installed` | `boolean` | Required; derived field | Whether the current project already has a matching imported MCP tool |

### Derived / Computed Behavior

- `id` falls back to a slugified version of `name` when the upstream payload omits an ID.
- `category` prefers an explicit upstream category and otherwise falls back to the first tag.
- `already_installed` is computed by comparing normalized existing tool names against the normalized catalog name.

### Relationships

- One `CatalogMcpServer` can produce at most one imported `McpToolConfig` per project.
- `CatalogMcpServer.install_config` is the source material for the imported tool's `config_content`.

---

## Entity: ImportCatalogMcpRequest

Minimal request payload used to import a selected catalog entry.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `catalog_server_id` | `string` | Required; minimum length 1 | Identifies the selected catalog entry to import |

### Validation Rules

- The ID must match a server present in the current catalog result set used by the backend import flow.
- Missing or unknown IDs return a not-found error.
- Requests for already-installed servers return a conflict error.

---

## Existing Entity Reused: McpToolConfig

Imported catalog entries are persisted as ordinary `McpToolConfig` records rather than a new catalog-specific model.

### Imported Field Mapping

| `CatalogMcpServer` source | `McpToolConfig` target | Notes |
|---------------------------|------------------------|-------|
| `name` | `name` | Preserved as the user-visible tool name |
| `description` | `description` | Preserved for the tool archive |
| `install_config` | `config_content` | Converted into a standard `mcpServers` JSON snippet |
| derived slug from `name` | `mcpServers` key | Used as the canonical server key inside the JSON snippet |
| existing repo sync flow | repository `mcp.json` | No new sync path is introduced |

### Config Shapes Produced During Import

```json
{
  "mcpServers": {
    "github-mcp": {
      "type": "http",
      "url": "https://example.com/mcp"
    }
  }
}
```

```json
{
  "mcpServers": {
    "context7": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@context7/mcp-server"]
    }
  }
}
```

```json
{
  "mcpServers": {
    "example-sse": {
      "type": "sse",
      "url": "https://example.com/events"
    }
  }
}
```

---

## State Transitions

```text
Upstream payload fetched
  -> normalized into CatalogMcpServer
  -> marked already_installed true/false using current project tool names
  -> rendered in Tools page browse grid
  -> user submits ImportCatalogMcpRequest
  -> backend validates existence + non-duplicate + supported transport
  -> backend generates McpToolConfig.config_content
  -> tool is created through existing archive flow
  -> catalog + tool queries invalidate and refetch
  -> card shows Installed badge
  -> user may sync imported tool to repository mcp.json
```

---

## Error States

| State | Trigger | Expected Handling |
|-------|---------|-------------------|
| Catalog unavailable | Upstream timeout, network failure, or invalid JSON | Serve stale cache when available; otherwise return a user-facing catalog-unavailable error |
| Unsafe upstream or repo URL | Non-HTTPS or non-allowlisted URL | Reject upstream fetch configuration or drop unsafe repo link from surfaced model |
| Unsupported transport | Catalog entry uses an unmapped transport | Reject import with a validation error |
| Missing required install fields | Remote entry without URL or local entry without command | Reject import with a validation error |
| Duplicate import | Selected server already exists for the project | Return conflict and keep card in Installed state |
