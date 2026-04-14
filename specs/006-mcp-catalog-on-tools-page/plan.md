# Implementation Plan: MCP Catalog on Tools Page

**Branch**: `006-mcp-catalog-on-tools-page` | **Date**: 2026-04-14 | **Spec**: [GitHub Issue #1823](https://github.com/Boykai/solune/issues/1823)
**Input**: Parent issue Boykai/solune#1823 — MCP Catalog on Tools Page (PR #1836)

## Summary

Add an MCP Catalog section to the Tools page that lets users browse external MCP servers from the Glama catalog, search/filter them inline, import a selected server as a standard `McpToolConfig`, and then reuse Solune's existing tool archive + sync-to-repo flow. The implementation should mirror the current Agents Catalog pattern for browse/import UX while keeping all persistence and repo synchronization inside the existing Tools feature.

## Technical Context

**Language/Version**: Python 3.12+ (backend); TypeScript ~6.0.2 + React ^19.2.5 (frontend)  
**Primary Dependencies**: FastAPI, Pydantic, httpx, existing `InMemoryCache`/`cached_fetch`; React, TanStack Query, existing `toolsApi`, Zod  
**Storage**: Existing `mcp_configurations` persistence plus in-memory catalog cache; imported tools continue syncing to repository `mcp.json` files via current GitHub flow  
**Testing**: Backend `uv run pytest` unit/API tests for tools/catalog; frontend `npm run test`, `npm run type-check`, `npm run lint`, `npm run build`  
**Target Platform**: Solune web application (`solune/backend` + `solune/frontend`)  
**Project Type**: Web application feature enhancement  
**Performance Goals**: Catalog browse responses should be cache-backed and interactive on the Tools page; upstream fetches should tolerate temporary Glama outages via 1-hour TTL + stale fallback  
**Constraints**: SSRF-safe upstream access, no direct browser dependency on Glama, reuse current MCP CRUD/sync behavior, keep Microsoft MCP curation as filtering metadata rather than a second backend source  
**Scale/Scope**: Backend model + API additions, one new backend service module, frontend type/API/hook changes, one new browse component, targeted backend/frontend tests, no required database schema change

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Specification-First Development**: PASS — The parent issue provides the feature scope, UX flow, source-of-truth decisions, relevant files, phased rollout, and verification expectations needed for a planning artifact even though no separate `spec.md` was present in the generated feature directory.
- **II. Template-Driven Workflow**: PASS — This plan and its supporting artifacts are being produced in `/home/runner/work/solune/solune/specs/006-mcp-catalog-on-tools-page/` using the standard Speckit artifact set.
- **III. Agent-Orchestrated Execution**: PASS — The work naturally decomposes into backend catalog proxy work, frontend browse/import work, import mapping, and verification, each with explicit dependencies and handoff points.
- **IV. Test Optionality with Clarity**: PASS — The issue explicitly asks for backend and frontend verification, so the plan includes targeted existing-suite tests plus standard frontend validation.
- **V. Simplicity and DRY**: PASS — The design reuses the existing tools persistence/sync path and the existing agents catalog/presets UI patterns instead of introducing a second storage or sync model.

**Post-Phase-1 Re-check**: PASS — The Phase 0 research and Phase 1 design keep the feature within existing architectural seams: one cached proxy service, API/view-model additions, and reuse of existing tool CRUD/sync behavior. No constitution violations or complexity justifications are required.

## Project Structure

### Documentation (this feature)

```text
specs/006-mcp-catalog-on-tools-page/
├── plan.md              # This file
├── research.md          # Phase 0 output — upstream/source and implementation decisions
├── data-model.md        # Phase 1 output — catalog/import entities and transitions
├── quickstart.md        # Phase 1 output — implementation sequence and validation guide
├── contracts/
│   └── mcp-catalog-contract.yaml
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   └── tools.py                     # Add catalog browse/import endpoints
│   │   ├── models/
│   │   │   └── tools.py                     # Add CatalogMcpServer request/response models
│   │   └── services/
│   │       ├── agents/
│   │       │   └── catalog.py               # Reference browse/cache/error-handling pattern
│   │       └── tools/
│   │           ├── catalog.py               # NEW: Glama proxy + cache + already-installed detection
│   │           ├── presets.py               # Reference JSON MCP snippet generation
│   │           └── service.py               # Reuse create/import/sync behavior
│   └── tests/
│       └── unit/
│           ├── test_api_tools.py            # Extend or add catalog endpoint coverage
│           ├── test_catalog.py              # Reference cache/error tests
│           └── test_tools_service.py        # Extend import mapping / sync behavior tests
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── agents/
    │   │   │   └── AgentsPanel.tsx          # Reference catalog browse UX
    │   │   └── tools/
    │   │       ├── McpCatalogBrowse.tsx     # NEW: inline browse/import UI
    │   │       ├── McpPresetsGallery.tsx    # Reference existing discovery UI
    │   │       ├── ToolsPanel.tsx           # Integrate catalog section into Tools page
    │   │       └── __tests__/
    │   │           └── ToolsPanel.test.tsx  # Extend or add catalog UI tests
    │   ├── hooks/
    │   │   └── useTools.ts                  # Add catalog browse/import hooks or helpers
    │   ├── services/
    │   │   └── api.ts                       # Add browseCatalog/importFromCatalog client methods
    │   └── types/
    │       └── index.ts                     # Add CatalogMcpServer interfaces
    └── package.json                         # Existing validation commands
```

**Structure Decision**: This feature fits the existing web-app split. Backend changes stay within the current tools API/model/service boundaries, while frontend changes stay within the current Tools page component/hook/API/type stack. No new top-level packages, services, or storage systems are required.

## Phase Execution Plan

### Phase 1 — Backend Catalog Service

**Goal**: Expose a project-aware MCP catalog browse/import backend contract without changing the existing tool persistence model.

| Step | Action | Details |
|------|--------|---------|
| 1.1 | Add catalog API/view models | Extend `backend/src/models/tools.py` with `CatalogMcpServer`, list/import request models, and response wrappers aligned to the new contract |
| 1.2 | Build the Glama proxy service | Create `backend/src/services/tools/catalog.py` using `httpx`, `cached_fetch`, a 1-hour cache TTL, stale fallback, and allowlisted HTTPS upstream validation |
| 1.3 | Detect installed catalog entries | Compare current project MCP tools against normalized catalog entries to compute `already_installed` without requiring a schema migration |
| 1.4 | Add catalog endpoints | Extend `backend/src/api/tools.py` with `GET /tools/{project_id}/catalog` and `POST /tools/{project_id}/catalog/import` |
| 1.5 | Map import payloads into existing tool flow | Convert upstream `install_config` into the existing `config_content` JSON shape, then reuse current tool creation/sync behavior |
| 1.6 | Add backend test coverage | Extend/add API and service tests for cache behavior, error mapping, already-installed detection, and import mapping |

**Dependencies**: None — backend browse/import contract is the foundation for the frontend.

**Output**: API-ready catalog browse/import endpoints and targeted backend tests.

### Phase 2 — Frontend Catalog UI

**Goal**: Surface the external MCP catalog inline on the Tools page using the same discovery/import conventions already used elsewhere in Solune.

| Step | Action | Details |
|------|--------|---------|
| 2.1 | Add frontend catalog types and schema guards | Extend `frontend/src/types/index.ts` with `CatalogMcpServer` and list/import response types, plus align the frontend Zod validation used for API safety |
| 2.2 | Extend the tools API client | Add `browseCatalog()` and `importFromCatalog()` to `frontend/src/services/api.ts` |
| 2.3 | Add query/mutation hooks | Extend `frontend/src/hooks/useTools.ts` with `useMcpCatalog(projectId, query, category)` and `useImportMcpServer(projectId)` or equivalent helpers |
| 2.4 | Build catalog browse component | Create `frontend/src/components/tools/McpCatalogBrowse.tsx` with search input, category chips, server cards, quality/type badges, install CTA, installed badge, and retry/empty states |
| 2.5 | Integrate with ToolsPanel | Insert the browse section between `McpPresetsGallery` and the tool archive in `ToolsPanel.tsx`, preserving current presets/upload/repo-config flows |
| 2.6 | Add frontend tests | Extend/add hook and component tests covering loading/error/empty/imported states, section integration, and Zod schema validation for `CatalogMcpServer` |

**Dependencies**: Phase 1 browse/import contract must exist first.

**Output**: Inline Tools page catalog browse/import experience backed by the new API.

### Phase 3 — Import Logic, Sync, and UX Completion

**Goal**: Make imported catalog servers behave exactly like manually uploaded tools after selection.

| Step | Action | Details |
|------|--------|---------|
| 3.1 | Normalize transport variants | Support `http`, `sse`, and `stdio/local` Glama install configs and reject unsupported variants clearly |
| 3.2 | Reuse current tool archive state | After import succeeds, invalidate/refetch the existing tools queries so the new server appears in the archive immediately |
| 3.3 | Preserve sync-to-repo workflow | Ensure the imported server uses the existing repo sync flow and `mcp.json` generation path |
| 3.4 | Reflect installed status in browse cards | After import, the same catalog item should render its installed badge using refreshed browse data and current tool state |
| 3.5 | Validate conflict handling | Reuse current duplicate-tool / duplicate-server-name checks so catalog imports cannot silently overwrite existing tool definitions |

**Dependencies**: Backend catalog import endpoint (Phase 1) and frontend browse/import UI (Phase 2).

**Output**: End-to-end import behavior that lands inside existing tool management and repo sync workflows.

### Phase 4 — Verification

**Goal**: Prove the new catalog behavior works across backend, frontend, and repo sync expectations.

| Step | Action | Details |
|------|--------|---------|
| 4.1 | Backend verification | Run targeted pytest coverage for tools API/service/catalog behavior |
| 4.2 | Frontend verification | Run targeted component/hook tests, then the standard frontend lint/type-check/test/build sequence |
| 4.3 | Manual flow validation | Browse catalog → search `github` → import GitHub MCP → verify tool archive → sync to repo → confirm repository `mcp.json` contains the imported server |
| 4.4 | UX regression review | Confirm presets gallery, repo config panel, manual upload flow, and tool archive behavior remain unchanged except for the new catalog section |

**Dependencies**: Phases 1–3 complete.

**Output**: Validated MCP catalog browse/import feature ready for task breakdown and implementation.

## Verification Matrix

| Check | Command / Method | After Phase |
|-------|------------------|-------------|
| Backend API/service tests | `cd /home/runner/work/solune/solune/solune/backend && uv run pytest tests/unit/test_api_tools.py tests/unit/test_tools_service.py tests/unit/test_catalog.py -q` | 1, 3, 4 |
| Frontend targeted tests | `cd /home/runner/work/solune/solune/solune/frontend && npm run test -- src/hooks/useTools.test.tsx src/components/tools/__tests__/ToolsPanel.test.tsx` | 2, 3 |
| Frontend type safety | `cd /home/runner/work/solune/solune/solune/frontend && npm run type-check` | 2, 4 |
| Frontend lint | `cd /home/runner/work/solune/solune/solune/frontend && npm run lint` | 4 |
| Frontend full unit suite | `cd /home/runner/work/solune/solune/solune/frontend && npm run test` | 4 |
| Frontend production build | `cd /home/runner/work/solune/solune/solune/frontend && npm run build` | 4 |
| Manual browse/import verification | Tools page search/import/sync flow described in issue | 4 |

## Decisions

| Decision | Rationale |
|----------|-----------|
| **Glama is the only live catalog source** | It already supplies the browse/search/category/install data required by the feature and avoids multi-source reconciliation. |
| **Backend proxy instead of direct browser fetch** | Protects the UI from upstream volatility, centralizes SSRF controls, and allows stale-cache fallback. |
| **Import into existing `McpToolConfig` records** | Reuses CRUD, validation, repo sync, and existing tool archive UI instead of inventing a second tool persistence path. |
| **Mirror Agents Catalog / Presets UX** | The repository already has proven inline browse/import patterns that fit this feature with minimal design drift. |
| **No required DB schema change in the initial plan** | The issue only calls for new API models and import behavior; installed-state can be derived from existing tool data. |

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Glama API shape differs from assumptions in the issue | Browse/import mapping may need a thin adapter update | Isolate upstream parsing in `services/tools/catalog.py` and contract-test the normalized model |
| Catalog results become unavailable upstream | Tools page browse section could fail noisily | Use cache + stale fallback + explicit retry/error UI |
| Imported install configs don't fit current MCP validation | Users cannot import some servers | Normalize supported transports early and fail unsupported variants with precise validation errors |
| Installed-state matching is too weak without persisted catalog metadata | Browse cards might not show accurate Installed badges | Normalize matching by server name/config/repo URL and cover it with backend tests |
| Tools page becomes visually crowded | UX regression on an already dense page | Keep the catalog inline, reuse existing visual patterns, and place it between presets and the archive as requested |

## Complexity Tracking

> No constitution violations found. No complexity justifications required.
