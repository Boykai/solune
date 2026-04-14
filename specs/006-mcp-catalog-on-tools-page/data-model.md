# Data Model: MCP Catalog on Tools Page

**Feature**: MCP Catalog on Tools Page | **Date**: 2026-04-14 | **Status**: Complete

## Entity: CatalogMcpServer

A transient API model representing one external MCP server returned from the proxied Glama catalog.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | `string` | Required, stable | Upstream catalog identifier used for import actions |
| `name` | `string` | Required | Human-readable server name shown in the Tools page cards |
| `description` | `string` | Required | Summary text for browsing/search |
| `repo_url` | `string \| null` | HTTPS when present | Repository URL surfaced for trust/discovery |
| `category` | `string \| null` | Optional | Upstream category label used by the UI filter chips |
| `server_type` | `enum` | `http`, `sse`, `stdio`, `local`, `remote`, `unknown` | Normalized install/runtime type for badges and import mapping |
| `install_config` | `CatalogInstallConfig` | Required | Upstream install payload used to build `config_content` |
| `quality_score` | `string \| null` | Optional (`A`, `B`, `C`, etc.) | Upstream quality signal shown in the browse UI |
| `already_installed` | `boolean` | Required, derived | Whether the current project already has an equivalent MCP tool imported |

### Validation Rules

- `repo_url`, when present, must be HTTPS and allowlisted for safe display/import metadata.
- `server_type` is derived from the upstream install payload and must never be blank in API responses.
- `already_installed` is computed per project; it is not persisted.

### Relationships

- `CatalogMcpServer` is a read-only browse entity.
- Importing a `CatalogMcpServer` creates or reuses an existing `McpToolConfig` record.

---

## Value Object: CatalogInstallConfig

A normalized representation of the upstream Glama install instructions before conversion into Solune's stored `mcp.json` snippet.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `transport` | `enum` | `http`, `sse`, `stdio`, `local` | Canonical transport/runtime mode |
| `url` | `string \| null` | Required for `http`/`sse` | Remote endpoint URL |
| `command` | `string \| null` | Required for `stdio`/`local` | Executable command (for example `npx`) |
| `args` | `string[]` | Optional | Command arguments for `stdio`/`local` servers |
| `env` | `object` | Optional | Environment variable mapping carried into the stored MCP snippet |
| `headers` | `object` | Optional | Header mapping for remote transports |
| `tools` | `string[]` | Optional | Tool selection list if supplied upstream |

### Validation Rules

- Remote transports require a non-empty HTTPS `url`.
- Local/stdio transports require a non-empty `command`.
- Unsupported transport shapes fail import with a validation error rather than being stored partially.

---

## Existing Entity Impact: McpToolConfig

Imported catalog servers are persisted using the existing MCP tool entity already backed by `mcp_configurations`.

### Impacted Fields

| Field | Existing Type | Import Behavior |
|-------|---------------|-----------------|
| `name` | `string` | Defaults to the catalog server display name |
| `description` | `string` | Defaults to the catalog description |
| `endpoint_url` | `string` | Derived from `url` or `command` for current tool list behavior |
| `config_content` | `string` | Stores a valid `mcpServers` JSON snippet built from `CatalogInstallConfig` |
| `github_repo_target` | `string` | Reuses current target selection/sync flow |
| `sync_status` | `string` | Starts in the normal create/import lifecycle (`pending` → `synced` / `error`) |

### Import Mapping Rules

| Catalog transport | Stored MCP snippet |
|-------------------|--------------------|
| `http` | `{ "type": "http", "url": "...", ... }` |
| `sse` | `{ "type": "sse", "url": "...", ... }` |
| `stdio` / `local` | `{ "command": "npx", "args": [...], ... }` (plus `type` if required by existing validation) |

The stored JSON remains wrapped in the existing root structure:

```json
{
  "mcpServers": {
    "<normalized-server-name>": {
      "type": "http",
      "url": "https://example.com/mcp"
    }
  }
}
```

---

## API Response Shapes

### CatalogMcpServerListResponse

| Field | Type | Description |
|-------|------|-------------|
| `servers` | `CatalogMcpServer[]` | Browse/search results for the current project |
| `count` | `number` | Result count returned by the proxy |
| `query` | `string` | Echo of the search term used |
| `category` | `string \| null` | Echo of the selected category filter |

### ImportCatalogMcpRequest

| Field | Type | Description |
|-------|------|-------------|
| `catalog_server_id` | `string` | Stable catalog identifier to import |

### ImportCatalogMcpResponse

This reuses the existing `McpToolConfigResponse` payload so the frontend can immediately add the imported tool to the archive and repo-sync flows without a second mapping layer.

---

## State Transitions

### Catalog Browse → Import Lifecycle

```text
Catalog server discovered
  → Filtered/searched in Tools page
  → Import requested
  → Install config validated + mapped
  → McpToolConfig created
  → Existing sync-to-repo flow available/executed
  → Catalog card reflects already_installed = true
```

### Error Paths

```text
Catalog fetch fails
  → stale cached browse results returned when available
  → otherwise API returns catalog-unavailable error

Catalog import fails validation
  → no McpToolConfig created
  → user sees import error and browse state remains unchanged
```

---

## Derived Matching Rules for `already_installed`

Because the issue scopes the catalog model to API/view models rather than new database fields, installed-state matching is derived from existing project tools using one or more of:

1. normalized catalog server ID / server name
2. parsed server entry inside `config_content`
3. upstream repo URL when present

This keeps the plan aligned with the requested minimal data-model change: new catalog models for request/response handling, but no mandatory persistence schema expansion.
