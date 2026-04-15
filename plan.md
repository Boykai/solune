# Implementation Plan: MCP Catalog on Tools Page

**Branch**: `006-mcp-catalog-tools-page` | **Date**: 2026-04-15 | **Spec**: [/home/runner/work/solune/solune/spec.md](./spec.md)
**Input**: Feature specification from `/home/runner/work/solune/solune/spec.md`

## Summary

Add a Glama-backed MCP Catalog section to the Tools page so users can browse external MCP servers, filter them by text or category, import a selected server into the existing `McpToolConfig` archive, and then sync the imported tool into the repository `mcp.json` through Solune's existing MCP workflow. The implementation stays within current backend tools services and current frontend Tools page patterns, using cached upstream fetches, derived installed-state detection, and the same repo-sync path already used by manually added MCP tools.

## Technical Context

**Language/Version**: Python >=3.12 (backend); TypeScript ~6.0.2 + React ^19.2.5 (frontend)  
**Primary Dependencies**: FastAPI, Pydantic, httpx, existing `InMemoryCache`/`cached_fetch`; React, TanStack Query, Zod, existing `toolsApi`/Tools page UI primitives  
**Storage**: Existing MCP tool persistence plus repository `mcp.json` sync flow; transient in-memory cache for catalog responses  
**Testing**: Backend `pytest` + `pytest-asyncio`; frontend `vitest`, `eslint`, `tsc`, and `vite build`; markdownlint for planning artifacts  
**Target Platform**: Solune web application (`/home/runner/work/solune/solune/solune/backend` + `/home/runner/work/solune/solune/solune/frontend`)  
**Project Type**: Web application feature enhancement  
**Performance Goals**: Keep browse interactions responsive for 21,000+ upstream servers; serve cached results for one hour with stale fallback during Glama outages; keep text/category filtering within the existing interactive Tools page flow  
**Constraints**: Proxy only allowlisted HTTPS upstream hosts, sanitize external repository URLs, reuse existing tool CRUD/sync behavior, avoid database schema changes, and prevent duplicate imports per project  
**Scale/Scope**: One backend catalog service and API surface, one frontend browse section plus supporting hooks/client/types, targeted backend/frontend tests, and one OpenAPI contract for browse/import

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Specification-First Development**: PASS — `/home/runner/work/solune/solune/spec.md` defines user stories, acceptance scenarios, edge cases, requirements, assumptions, and measurable success criteria for browse, import, sync, and installed-state detection.
- **II. Template-Driven Workflow**: PASS — This plan and its supporting artifacts follow the standard speckit artifact set while using the root-level copilot-branch layout already present in this PR (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/`).
- **III. Agent-Orchestrated Execution**: PASS — The work decomposes cleanly into backend catalog proxying, import mapping, frontend browse/import UX, and validation, with explicit dependencies between phases.
- **IV. Test Optionality with Clarity**: PASS — The specification explicitly requires backend, frontend, and manual verification, so the plan includes targeted existing-suite tests and a manual browse/import/sync flow.
- **V. Simplicity and DRY**: PASS — The design reuses existing tools persistence, repo sync, query invalidation, and page composition rather than introducing a second storage model or a separate catalog app.

**Post-Phase-1 Re-check**: PASS — The design remains within existing Solune seams: one normalized Glama proxy, one import mapper into `McpToolConfig`, one inline browse component, and reuse of the current sync-to-repo workflow. No constitution violations or complexity justifications are required.

## Project Structure

### Documentation (this feature)

```text
/home/runner/work/solune/solune/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── mcp-catalog-contract.yaml
└── tasks.md             # Phase 2 output (not created by /speckit.plan)
```

### Source Code (repository root)

```text
/home/runner/work/solune/solune/solune/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   └── tools.py                     # Catalog browse/import endpoints
│   │   ├── models/
│   │   │   └── tools.py                     # Catalog install/browse/import models
│   │   └── services/
│   │       ├── cache.py                     # Cached fetch + stale fallback primitives
│   │       └── tools/
│   │           ├── catalog.py               # Glama proxy, normalization, import mapping
│   │           └── service.py               # Existing tool CRUD/sync flow reused by import
│   └── tests/
│       └── unit/
│           └── test_tools_catalog.py        # Service + API coverage for catalog behavior
└── frontend/
    ├── src/
    │   ├── components/
    │   │   └── tools/
    │   │       ├── McpCatalogBrowse.tsx     # Catalog browse/import UI
    │   │       ├── McpPresetsGallery.tsx    # Existing discovery section above catalog
    │   │       ├── ToolsPanel.tsx           # Integrates catalog between presets and archive
    │   │       └── __tests__/
    │   │           ├── McpCatalogBrowse.test.tsx
    │   │           └── ToolsPanel.test.tsx
    │   ├── hooks/
    │   │   ├── useTools.ts                  # Catalog browse/import hooks and invalidation
    │   │   └── useTools.test.tsx
    │   ├── services/
    │   │   ├── api.ts                       # Catalog client methods
    │   │   └── api.test.ts                  # Contract validation for catalog payloads
    │   └── types/
    │       └── index.ts                     # Catalog interfaces used by hooks/UI
    └── package.json                         # Existing lint/type-check/test/build commands
```

**Structure Decision**: Keep the feature inside the existing backend/frontend split. Backend work stays inside current tools models, tools API, and tools services. Frontend work stays inside the existing Tools page composition and shared API/hook/type layers. No new package, repository, or storage system is introduced.

## Phase Execution Plan

### Phase 0 — Research and Design Framing

**Goal**: Resolve upstream integration, security, and mapping decisions before implementation details are broken down.

| Step | Action | Details |
|------|--------|---------|
| 0.1 | Confirm upstream source contract | Validate that Glama remains the sole catalog source and normalize its variable payload shape (`list` vs wrapper object, alternate field names, optional tags/categories). |
| 0.2 | Define SSRF and sanitization boundaries | Restrict backend fetches to the allowlisted Glama HTTPS endpoint and sanitize surfaced repository URLs before returning them to the client. |
| 0.3 | Choose installed-state strategy | Derive `already_installed` from current project tools instead of adding persisted catalog metadata. |
| 0.4 | Choose import mapping contract | Normalize `http`, `sse`, `stdio`, and `local` transports into the existing `mcpServers` snippet accepted by the tool archive/sync flow. |
| 0.5 | Choose validation strategy | Use targeted backend/frontend catalog tests plus manual browse/import/sync verification rather than inventing new test infrastructure. |

**Dependencies**: Specification complete.

**Output**: `/home/runner/work/solune/solune/research.md`

### Phase 1 — Backend Catalog Browse and Import Contract

**Goal**: Expose a project-aware catalog API that reuses existing tool storage and sync behavior.

| Step | Action | Details |
|------|--------|---------|
| 1.1 | Add transient catalog models | Add `CatalogInstallConfig`, `CatalogMcpServer`, `CatalogMcpServerListResponse`, and `ImportCatalogMcpRequest` to backend tools models. |
| 1.2 | Build the Glama proxy service | Create `services/tools/catalog.py` with allowlisted HTTPS validation, normalized parsing, one-hour TTL caching, and stale fallback. |
| 1.3 | Derive installed-state | Compare current project tool names against normalized catalog server names to set `already_installed`. |
| 1.4 | Expose browse endpoint | Add `GET /api/v1/tools/{project_id}/catalog` with optional `query` and `category` filters. |
| 1.5 | Expose import endpoint | Add `POST /api/v1/tools/{project_id}/catalog/import`, locate the requested catalog entry, reject duplicates, map the install config, and create a standard MCP tool record. |
| 1.6 | Verify backend behavior | Cover normalization, SSRF protection, error mapping, cache behavior, installed detection, and import mapping in `test_tools_catalog.py`. |

**Dependencies**: Phase 0 decisions complete.

**Output**: Stable backend browse/import API contract for frontend consumption.

### Phase 2 — Frontend Catalog Browse Experience

**Goal**: Surface the catalog inline on the Tools page using existing Solune UI and query conventions.

| Step | Action | Details |
|------|--------|---------|
| 2.1 | Add frontend catalog types | Add TypeScript interfaces mirroring the backend catalog models. |
| 2.2 | Extend the API client | Add `toolsApi.browseCatalog()` and `toolsApi.importFromCatalog()` with schema validation on browse responses. |
| 2.3 | Add hooks | Add `useMcpCatalog(projectId, query, category)` and `useImportMcpServer(projectId)` with related query invalidation. |
| 2.4 | Create browse component | Build `McpCatalogBrowse.tsx` with deferred search input, category chips, loading/error/empty states, server cards, quality/type badges, and import CTA or installed badge. |
| 2.5 | Integrate into ToolsPanel | Render the catalog section between the presets gallery and the tool archive, preserving the existing repo config, preset gallery, and upload flows. |
| 2.6 | Verify frontend behavior | Cover schema validation, hooks, and browse/import UI states in existing Vitest suites. |

**Dependencies**: Phase 1 backend contract must exist.

**Output**: Inline Tools page catalog browse/import UX backed by the new API.

### Phase 3 — Import Flow Completion and Sync Reuse

**Goal**: Make imported catalog entries behave identically to manually added MCP tools.

| Step | Action | Details |
|------|--------|---------|
| 3.1 | Normalize supported transports | Accept `http`, `sse`, `stdio`, and `local`; reject unsupported transports with clear validation errors. |
| 3.2 | Generate canonical tool config | Produce a standard `mcpServers` JSON snippet using a slugified server key and the normalized install config. |
| 3.3 | Reuse current tool creation path | Persist imported servers as ordinary `McpToolConfig` records via the existing tools service. |
| 3.4 | Refresh related client state | Invalidate tools, repo MCP, and catalog queries after import so the archive and installed badges update immediately. |
| 3.5 | Reuse sync-to-repo | Keep imported tools inside the existing sync flow so they land in repository `mcp.json` without special-case logic. |

**Dependencies**: Phases 1 and 2.

**Output**: End-to-end import behavior consistent with the existing tool archive and repo sync workflow.

### Phase 4 — Verification

**Goal**: Validate the final browse/import/sync experience with existing tooling and manual checks.

| Step | Action | Details |
|------|--------|---------|
| 4.1 | Run backend targeted tests | Execute the catalog-specific pytest suite. |
| 4.2 | Run frontend targeted tests | Execute the catalog-specific Vitest suites that cover API validation, hooks, and UI states. |
| 4.3 | Run frontend safety checks | Run `type-check`, `lint`, and `build` to ensure the Tools page changes remain production-safe. |
| 4.4 | Manually verify the user flow | Browse catalog → search `github` → import a server → verify installed badge and tool archive entry → sync to repo → confirm `mcp.json` content. |

**Dependencies**: Phases 1–3 complete.

**Output**: A validated MCP catalog feature ready for task decomposition.

## Verification Matrix

| Check | Command / Method | After Phase |
|-------|------------------|-------------|
| Backend catalog tests | `cd /home/runner/work/solune/solune/solune/backend && uv run --with pytest --with pytest-asyncio pytest tests/unit/test_tools_catalog.py -q` | 1, 3, 4 |
| Frontend catalog tests | `cd /home/runner/work/solune/solune/solune/frontend && npm run test -- --reporter=verbose --run src/components/tools/__tests__/McpCatalogBrowse.test.tsx src/hooks/useTools.test.tsx src/services/api.test.ts` | 2, 3, 4 |
| Frontend type check | `cd /home/runner/work/solune/solune/solune/frontend && npm run type-check` | 2, 4 |
| Frontend lint | `cd /home/runner/work/solune/solune/solune/frontend && npm run lint` | 4 |
| Frontend build | `cd /home/runner/work/solune/solune/solune/frontend && npm run build` | 4 |
| Manual browse/import/sync | Tools page flow described in the feature spec | 4 |
| Artifact lint | `cd /home/runner/work/solune/solune && npx --yes markdownlint-cli plan.md research.md data-model.md quickstart.md contracts/mcp-catalog-contract.yaml --config solune/.markdownlint.json` | 0, 4 |

## Decisions

| Decision | Rationale |
|----------|-----------|
| **Glama is the only live catalog source** | It already provides server metadata, install instructions, quality scores, and search/category inputs without introducing multi-source reconciliation. |
| **Catalog fetches happen on the backend** | This centralizes SSRF controls, upstream error handling, caching, and normalization rather than exposing the browser directly to upstream availability or shape drift. |
| **Installed-state is derived, not stored** | Matching current project tool names against normalized catalog names avoids a schema migration and keeps the feature aligned with existing tool CRUD. |
| **Import creates a normal `McpToolConfig`** | Reusing the existing archive and sync behavior keeps the feature small and consistent with current tooling. |
| **Inline Tools page UX mirrors existing discovery patterns** | Rendering the catalog between presets and the archive preserves context and avoids creating a separate page or modal workflow. |

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Upstream Glama payloads vary in field names or wrapper shape | Browse/import could break on payload drift | Normalize alternate field names and wrapper shapes in one backend adapter with tests. |
| Upstream outages degrade the Tools page | Users may lose browse access during outages | Use one-hour TTL cache plus stale fallback and an explicit retry/error UI. |
| Malformed or unsupported install configs appear upstream | Some catalog entries may fail to import | Validate transport-specific requirements and surface precise user-facing validation errors. |
| Duplicate imports create conflicting tool records | Users could end up with ambiguous tool archive entries | Derive `already_installed` during browse and reject duplicate import attempts on the backend. |
| Tools page becomes overloaded | UX regression in an already dense surface | Keep the section inline, scoped, and visually consistent with existing Tools panel sections. |

## Complexity Tracking

> No constitution violations found. No complexity justifications required.
