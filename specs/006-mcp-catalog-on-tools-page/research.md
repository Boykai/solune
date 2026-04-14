# Research: MCP Catalog on Tools Page

**Feature**: MCP Catalog on Tools Page | **Date**: 2026-04-14 | **Status**: Complete

## R1: External Catalog Source

**Decision**: Use the Glama MCP API (`https://glama.ai/api/mcp/v1/servers`) as the single upstream catalog source for browse/search, with Microsoft MCP servers surfaced as a curated frontend filter rather than a second backend integration.

**Rationale**: The issue explicitly identifies Glama as the recommended primary source because it already exposes the catalog scale, free-text search, categories, quality scores, GitHub links, and install configs needed for the Tools page. Treating Microsoft servers as a filter over the same dataset keeps the implementation simple and avoids mixing incompatible upstream contracts.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| `punkpeye/awesome-mcp-servers` README scraping | Same underlying dataset as Glama, but less structured and harder to query safely |
| `microsoft/mcp` as a second live data source | Useful for curation, but not a full catalog and has no public API |
| `mcp.so` / `mcpservers.org` | No stable public API documented in the issue |

---

## R2: Backend Catalog Proxy Pattern

**Decision**: Add `/home/runner/work/solune/solune/solune/backend/src/services/tools/catalog.py` that mirrors the existing browser-agents catalog pattern: `httpx` fetches, a 1-hour `InMemoryCache`/`cached_fetch` TTL, stale-cache fallback, and allowlisted HTTPS upstream validation.

**Rationale**: `/home/runner/work/solune/solune/solune/backend/src/services/agents/catalog.py` already solves the same class of problem: proxying an external catalog, caching it defensively, translating upstream failures into user-safe errors, and marking already-imported records from the local database. Reusing that shape minimizes new concepts, keeps SSRF protections explicit, and gives the Tools page resilient behavior when the upstream catalog is temporarily unavailable.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Put catalog browse logic directly into `ToolsService` | Mixes external catalog browsing with existing CRUD/sync responsibilities |
| Call Glama directly from the browser | Exposes the UI to CORS/network volatility and bypasses server-side SSRF controls |
| Fetch live on every request without cache | Increases latency and makes the page fragile during upstream interruptions |

---

## R3: Import Mapping Strategy

**Decision**: Treat catalog import as a thin translation layer that converts a Glama `install_config` into the existing `McpToolConfig.config_content` JSON shape, then reuses the current tool creation and sync-to-repo flow.

**Rationale**: `/home/runner/work/solune/solune/solune/backend/src/services/tools/presets.py` and `/home/runner/work/solune/solune/solune/backend/src/services/tools/service.py` already define the JSON structure Solune expects for MCP servers. Mapping `http`, `sse`, and `stdio/local` install variants into that structure avoids inventing a second persistence model and automatically keeps imported servers compatible with the existing tool archive, repo sync, and agent-assignment flows.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Store Glama payloads verbatim in the database | Would force special-case handling everywhere else in the tools stack |
| Create a separate imported-catalog table | Adds schema and sync complexity without new user value |
| Skip reuse of existing sync flow | Would duplicate the hardest part of the current tools feature |

---

## R4: Frontend Browse UX Pattern

**Decision**: Add a dedicated MCP catalog browse section directly in `ToolsPanel`, positioned between the presets gallery and the tool archive, using the same inline discovery pattern as `AgentsPanel` and the same state structure as `McpPresetsGallery`.

**Rationale**: `/home/runner/work/solune/solune/solune/frontend/src/components/agents/AgentsPanel.tsx` already shows the desired catalog UX: search, server cards, imported badges, retry state, and inline import actions. Reusing that presentation model inside `/home/runner/work/solune/solune/solune/frontend/src/components/tools/ToolsPanel.tsx` keeps the Tools page consistent with the rest of the product while still fitting the existing presets → generator → archive flow.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Separate catalog page | Adds navigation overhead for a feature meant to complement the existing Tools page |
| Replace the presets gallery entirely | Presets and external catalog imports serve different discovery use cases |
| Open a modal for catalog browsing | Hides discovery context and is less consistent with the existing agents catalog pattern |

---

## R5: Verification Strategy

**Decision**: Extend the existing backend and frontend test suites rather than inventing new tooling: backend unit/API tests around the catalog service and tools endpoints, frontend hook/component tests around the new types/API/hooks/UI, explicit Zod schema validation coverage for `CatalogMcpServer`, plus the standard frontend lint/type-check/test/build validation.

**Rationale**: The repository already has relevant test anchors: `/home/runner/work/solune/solune/solune/backend/tests/unit/test_catalog.py`, `test_api_tools.py`, and `test_tools_service.py` on the backend, plus `useMcpPresets.test.tsx`, `useTools.test.tsx`, and `components/tools/__tests__/ToolsPanel.test.tsx` on the frontend. Planning against those existing seams keeps the change set surgical and ensures the eventual implementation is validated in the same way as the rest of the Tools feature.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| New test harness for catalog-specific UI | Unnecessary; existing Vitest and pytest coverage patterns are sufficient |
| Rely on manual verification only | Misses schema, hook, and error-state regressions |
| Only test backend import logic | Leaves frontend contract and rendering drift unguarded |
