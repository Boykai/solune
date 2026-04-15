# Quickstart: MCP Catalog on Tools Page

**Feature**: MCP Catalog on Tools Page | **Date**: 2026-04-15

> **Status note (2026-04-15):** The MCP catalog feature is already implemented on this branch. This quickstart captures the exact implementation sequence, file touchpoints, and validation steps so future work can reproduce or extend the feature without drifting from the live architecture.

## Prerequisites

- Python 3.12+
- Node.js 18+
- `uv` for backend commands
- npm for frontend commands
- A Solune project connected to a repository for manual sync verification

## Key Files

### Backend

| File | Purpose |
|------|---------|
| `solune/backend/src/models/tools.py` | Catalog install/browse/import API models |
| `solune/backend/src/services/tools/catalog.py` | Glama proxy, normalization, SSRF checks, cache, import mapping |
| `solune/backend/src/api/tools.py` | Catalog browse/import endpoints |
| `solune/backend/tests/unit/test_tools_catalog.py` | Backend unit/API coverage |

### Frontend

| File | Purpose |
|------|---------|
| `solune/frontend/src/types/index.ts` | Catalog TypeScript interfaces |
| `solune/frontend/src/services/api.ts` | `browseCatalog()` and `importFromCatalog()` client methods |
| `solune/frontend/src/hooks/useTools.ts` | `useMcpCatalog()` and `useImportMcpServer()` hooks |
| `solune/frontend/src/components/tools/McpCatalogBrowse.tsx` | Browse/search/filter/import UI |
| `solune/frontend/src/components/tools/ToolsPanel.tsx` | Integrates catalog between presets and tool archive |
| `solune/frontend/src/components/tools/__tests__/McpCatalogBrowse.test.tsx` | Browse component tests |
| `solune/frontend/src/hooks/useTools.test.tsx` | Hook tests |
| `solune/frontend/src/services/api.test.ts` | API client/schema validation tests |

## Implementation Sequence

### Step 1: Add backend catalog models and service

1. Extend backend tool models with:
   - `CatalogInstallConfig`
   - `CatalogMcpServer`
   - `CatalogMcpServerListResponse`
   - `ImportCatalogMcpRequest`
2. Create the catalog service in `src/services/tools/catalog.py`.
3. Implement:
   - allowlisted upstream validation for `https://glama.ai`
   - one-hour TTL caching with stale fallback
   - normalization of Glama payload variations
   - installed-state derivation
   - import mapping into `McpToolConfigCreate`

### Step 2: Add backend API endpoints

Add two routes in `src/api/tools.py`:

- `GET /api/v1/tools/{project_id}/catalog`
- `POST /api/v1/tools/{project_id}/catalog/import`

The import route should:

1. Load the current project tools.
2. Reuse the catalog service to locate the requested server.
3. Reject duplicates.
4. Build a standard `mcpServers` JSON snippet.
5. Create a normal `McpToolConfig` via the existing tools service.

### Step 3: Add frontend types, API methods, and hooks

1. Add catalog interfaces in `src/types/index.ts`.
2. Add `toolsApi.browseCatalog()` and `toolsApi.importFromCatalog()` in `src/services/api.ts`.
3. Add:
   - `useMcpCatalog(projectId, query, category)`
   - `useImportMcpServer(projectId)`
4. Ensure successful import invalidates:
   - tool list queries
   - repo MCP detail queries
   - catalog browse queries

### Step 4: Add the browse UI

Create `McpCatalogBrowse.tsx` with:

- search input with deferred typing behavior
- category filter chips
- loading, error, and empty states
- server cards with:
  - name
  - description
  - category label
  - quality badge
  - transport badge
  - optional repo link
  - Import button or Installed badge

### Step 5: Integrate into the Tools page

Render `<McpCatalogBrowse projectId={projectId} />` in `ToolsPanel.tsx` immediately after the presets gallery / GitHub MCP generator block and before the tool archive section.

## Validation Commands

### Backend

```bash
cd solune/backend
uv run --with pytest --with pytest-asyncio pytest tests/unit/test_tools_catalog.py -q
```

### Frontend targeted catalog tests

```bash
cd solune/frontend
npm run test -- --reporter=verbose --run \
  src/components/tools/__tests__/McpCatalogBrowse.test.tsx \
  src/hooks/useTools.test.tsx \
  src/services/api.test.ts
```

### Frontend safety checks

```bash
cd /home/runner/work/solune/solune/solune/frontend
npm run type-check
npm run lint
npm run build
```

### Artifact lint

```bash
cd /home/runner/work/solune/solune
npx --yes markdownlint-cli plan.md research.md data-model.md quickstart.md contracts/mcp-catalog-contract.yaml --config solune/.markdownlint.json
```

## Manual Verification

1. Start the backend and frontend in your normal development environment.
2. Open the Tools page for a project with repository access.
3. Scroll to **Browse MCP Servers**.
4. Search for `github`.
5. Apply and clear one category chip.
6. Click **Import** on a non-installed server.
7. Confirm:
   - the imported tool appears in the archive
   - the card flips to **Installed**
   - repo MCP details remain intact
8. Click **Sync to Repo** for the imported tool.
9. Confirm the repository `mcp.json` contains the new `mcpServers` entry.

## Troubleshooting

### Catalog section shows an error immediately

- Verify the backend can reach the Glama endpoint.
- Confirm stale cache behavior using backend logs or tests.
- Retry the targeted backend catalog tests to isolate whether the failure is upstream parsing or network-related.

### Import fails for a specific server

- Inspect the server's normalized `install_config`.
- Check whether the transport is unsupported or missing required fields.
- Confirm the server is not already imported for the current project.

### Installed badge does not update after import

- Verify the import mutation invalidates tools, repo MCP, and catalog query keys.
- Confirm the imported tool name matches the normalized catalog server name used for installed-state detection.
