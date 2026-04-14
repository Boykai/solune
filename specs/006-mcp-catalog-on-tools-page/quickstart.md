# Quickstart: MCP Catalog on Tools Page

**Feature**: MCP Catalog on Tools Page | **Date**: 2026-04-14

> This guide describes the intended implementation path for adding the Glama-backed MCP catalog to the existing Tools page.

## Prerequisites

- Repository checkout at `/home/runner/work/solune/solune`
- Python 3.12+ with `uv` for backend validation
- Node.js/npm for frontend validation
- Access to the existing Tools page feature branches and test suites

## Step 1: Backend catalog browse contract

1. Add the catalog browse/import Pydantic models to:
   - `/home/runner/work/solune/solune/solune/backend/src/models/tools.py`
2. Create the Glama proxy service at:
   - `/home/runner/work/solune/solune/solune/backend/src/services/tools/catalog.py`
3. Add the Tools API endpoints in:
   - `/home/runner/work/solune/solune/solune/backend/src/api/tools.py`

### Backend implementation notes

- Reuse the caching/error pattern from `/home/runner/work/solune/solune/solune/backend/src/services/agents/catalog.py`.
- Use existing tool-sync behavior from `/home/runner/work/solune/solune/solune/backend/src/services/tools/service.py`.
- Keep upstream fetches HTTPS-only and allowlisted.

## Step 2: Import mapping

1. Normalize the Glama `install_config` into the stored `mcpServers` JSON structure.
2. Reuse existing tool creation/import validation rather than introducing a second persistence format.
3. Ensure the imported tool immediately participates in the existing repo sync flow.

### Expected mappings

- `http` → remote MCP entry with `type: "http"` + `url`
- `sse` → remote MCP entry with `type: "sse"` + `url`
- `stdio` / `local` → command-driven MCP entry with `command` + `args`

## Step 3: Frontend catalog browsing

1. Extend `/home/runner/work/solune/solune/solune/frontend/src/types/index.ts` with catalog response types and the matching Zod schema guards used by the frontend API layer.
2. Extend `/home/runner/work/solune/solune/solune/frontend/src/services/api.ts` with browse/import methods.
3. Extend `/home/runner/work/solune/solune/solune/frontend/src/hooks/useTools.ts` (or companion hooks) for catalog browse/import state.
4. Create `/home/runner/work/solune/solune/solune/frontend/src/components/tools/McpCatalogBrowse.tsx`.
5. Integrate the new section into `/home/runner/work/solune/solune/solune/frontend/src/components/tools/ToolsPanel.tsx` between presets and the archive.

### Frontend UX notes

- Mirror the inline browse pattern from `/home/runner/work/solune/solune/solune/frontend/src/components/agents/AgentsPanel.tsx`.
- Keep presets and manual upload intact.
- Show loading, retry, empty, and installed/importing states.

## Step 4: Test coverage

### Backend

Add or extend tests around:

- `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_tools.py`
- `/home/runner/work/solune/solune/solune/backend/tests/unit/test_tools_service.py`
- `/home/runner/work/solune/solune/solune/backend/tests/unit/test_catalog.py`
- New catalog-specific tool tests if separation improves readability

Run targeted backend validation:

```bash
cd /home/runner/work/solune/solune/solune/backend
uv run pytest tests/unit/test_api_tools.py tests/unit/test_tools_service.py tests/unit/test_catalog.py -q
```

### Frontend

Add or extend tests around:

- `/home/runner/work/solune/solune/solune/frontend/src/hooks/useTools.test.tsx`
- `/home/runner/work/solune/solune/solune/frontend/src/components/tools/__tests__/ToolsPanel.test.tsx`
- New catalog browse component tests if added

Run targeted frontend validation:

```bash
cd /home/runner/work/solune/solune/solune/frontend
npm run test -- src/hooks/useTools.test.tsx src/components/tools/__tests__/ToolsPanel.test.tsx
npm run type-check
```

## Step 5: Full verification

After implementation is complete, run the standard frontend validation bundle:

```bash
cd /home/runner/work/solune/solune/solune/frontend
npm run lint
npm run type-check
npm run test
npm run build
```

If backend code changed materially, also run the existing backend checks:

```bash
cd /home/runner/work/solune/solune/solune/backend
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run pyright src/
uv run pytest tests/unit/ -q
```

## Manual verification flow

1. Open the Tools page for a project.
2. Confirm the new **Browse MCP Catalog** section renders below presets.
3. Search for `github`.
4. Import the GitHub MCP server.
5. Confirm the imported server appears in the tool archive.
6. Trigger the existing sync-to-repo flow.
7. Confirm the generated repo `mcp.json` now contains the imported server snippet.

## Artifact checklist

- `plan.md` — implementation plan
- `research.md` — design choices and resolved unknowns
- `data-model.md` — catalog/import entities and transitions
- `contracts/mcp-catalog-contract.yaml` — API contract
- `quickstart.md` — implementation execution guide
