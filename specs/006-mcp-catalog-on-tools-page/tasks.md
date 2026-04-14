# Tasks: MCP Catalog on Tools Page

**Feature**: `006-mcp-catalog-on-tools-page` | **Branch**: `006-mcp-catalog-on-tools-page`  
**Input**: Design documents from `specs/006-mcp-catalog-on-tools-page/`  
**Spec Source**: Use `specs/006-mcp-catalog-tools-page/spec.md` as the authoritative user-story source because `specs/006-mcp-catalog-on-tools-page/spec.md` is absent and the task request explicitly said not to move or rename files  
**Prerequisites**: plan.md ✅, alternate spec source ✅, research.md ✅, data-model.md ✅, quickstart.md ✅, contracts/mcp-catalog-contract.yaml ✅

**Tests**: Included — the spec and plan explicitly require backend API/service verification plus frontend test, lint, type-check, and build validation.

**Organization**: Tasks are grouped by user story in spec priority order so each story remains independently implementable and testable.

## Format: `- [ ] T### [P?] [US#?] Description with exact file path`

- **[P]**: Can run in parallel (different files, no unmet dependency)
- **[US#]**: Required on every user-story task
- **No [US#]**: Setup, Foundational, and Polish phases only
- Every task below includes exact repo-root-relative file paths

## Path Conventions

- **Backend root**: `solune/backend`
- **Frontend root**: `solune/frontend`
- **Feature docs**: `specs/006-mcp-catalog-on-tools-page`
- **Primary backend files**: `solune/backend/src/api/tools.py`, `solune/backend/src/models/tools.py`, `solune/backend/src/services/tools/catalog.py`, `solune/backend/src/services/tools/service.py`
- **Primary frontend files**: `solune/frontend/src/services/api.ts`, `solune/frontend/src/services/schemas/tools.ts`, `solune/frontend/src/hooks/useTools.ts`, `solune/frontend/src/components/tools/McpCatalogBrowse.tsx`, `solune/frontend/src/components/tools/ToolsPanel.tsx`, `solune/frontend/src/types/index.ts`

---

## Phase 1: Setup (Baseline Audit)

**Purpose**: Confirm the implementation seams, alternate spec source, and current test baseline before code changes.

- [ ] T001 Audit `specs/006-mcp-catalog-on-tools-page/plan.md`, `specs/006-mcp-catalog-on-tools-page/research.md`, `specs/006-mcp-catalog-on-tools-page/data-model.md`, `specs/006-mcp-catalog-on-tools-page/contracts/mcp-catalog-contract.yaml`, and `specs/006-mcp-catalog-tools-page/spec.md` to lock user-story scope, transport mapping, cache behavior, and acceptance criteria
- [ ] T002 [P] Audit existing backend seams in `solune/backend/src/api/tools.py`, `solune/backend/src/models/tools.py`, `solune/backend/src/services/agents/catalog.py`, and `solune/backend/src/services/tools/service.py` to confirm reuse points for proxy caching, error mapping, import creation, and repo sync
- [ ] T003 [P] Audit existing frontend seams in `solune/frontend/src/components/tools/ToolsPanel.tsx`, `solune/frontend/src/hooks/useTools.ts`, `solune/frontend/src/services/api.ts`, `solune/frontend/src/types/index.ts`, and `solune/frontend/src/components/agents/AgentsPanel.tsx` to confirm browse/import insertion points and query invalidation behavior
- [ ] T004 [P] Run baseline verification against `solune/backend/tests/unit/test_api_tools.py`, `solune/backend/tests/unit/test_tools_service.py`, `solune/frontend/src/hooks/useTools.test.tsx`, and `solune/frontend/src/components/tools/__tests__/ToolsPanel.test.tsx`: `cd solune/backend && uv run pytest tests/unit/test_api_tools.py tests/unit/test_tools_service.py -q && cd ../frontend && npm run test -- src/hooks/useTools.test.tsx src/components/tools/__tests__/ToolsPanel.test.tsx`

**Checkpoint**: Existing browse/import-adjacent seams and baseline tests are understood.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared catalog models, validators, and service scaffolding required by every user story.

**⚠️ CRITICAL**: No user story work should begin until this phase is complete.

- [ ] T005 Add shared catalog request/response models in `solune/backend/src/models/tools.py` for `CatalogInstallConfig`, `CatalogMcpServer`, `CatalogMcpServerListResponse`, and `ImportCatalogMcpRequest` aligned to `specs/006-mcp-catalog-on-tools-page/contracts/mcp-catalog-contract.yaml`
- [ ] T006 [P] Add shared frontend catalog interfaces in `solune/frontend/src/types/index.ts` for `CatalogInstallConfig`, `CatalogMcpServer`, `CatalogMcpServerListResponse`, and catalog import request/response payloads used by `solune/frontend/src/services/api.ts`
- [ ] T007 [P] Create Zod-backed catalog response validators in `solune/frontend/src/services/schemas/tools.ts` for browse/import payloads and wire them for reuse by `solune/frontend/src/services/api.ts`
- [ ] T008 Create `solune/backend/src/services/tools/catalog.py` with shared Glama constants, HTTPS allowlist validation, cache key/TTL definitions, upstream normalization helpers, and transport classification used by browse, import, and installed-state flows
- [ ] T009 [P] Extend `solune/frontend/src/services/api.ts` and `solune/frontend/src/hooks/useTools.ts` with shared catalog query-key and request-helper scaffolding that later story tasks can use for browse/import invalidation without duplicating cache logic

**Checkpoint**: Shared backend/frontend catalog primitives exist and all stories can build on them.

---

## Phase 3: User Story 1 - Browse MCP Server Catalog (Priority: P1) 🎯 MVP

**Goal**: Let a user browse, search, and filter a Glama-backed MCP catalog section inline on the Tools page.

**Independent Test**: Open the Tools page, verify the new Browse MCP Catalog section appears between presets and the tool archive, search for `github`, apply a category chip, confirm cards update, and verify empty/retry states are usable without importing anything.

### Tests for User Story 1 ⚠️

- [ ] T010 [P] [US1] Add backend catalog browse service tests in `solune/backend/tests/unit/test_tools_catalog.py` for Glama parsing, HTTPS-only upstream validation, stale-cache fallback, query/category filtering, and normalized server-type output
- [ ] T011 [P] [US1] Extend `solune/backend/tests/unit/test_api_tools.py` with `GET /api/v1/tools/{project_id}/catalog` coverage for success, invalid query handling, stale-cache fallback, and upstream 502/503 mapping from `solune/backend/src/api/tools.py`
- [ ] T012 [P] [US1] Extend `solune/frontend/src/hooks/useTools.test.tsx` with failing tests for `useMcpCatalog(projectId, query, category)` query keys, refetch behavior, retry state, and result caching backed by `solune/frontend/src/hooks/useTools.ts`
- [ ] T013 [P] [US1] Add failing browse UI tests in `solune/frontend/src/components/tools/__tests__/McpCatalogBrowse.test.tsx` and extend `solune/frontend/src/components/tools/__tests__/ToolsPanel.test.tsx` for search input, category chips, card rendering, empty state, retry state, and incremental result reveal

### Implementation for User Story 1

- [ ] T014 [US1] Implement Glama browse fetching, cache-backed stale fallback, query/category filtering, response normalization, and SSRF-safe upstream validation in `solune/backend/src/services/tools/catalog.py`
- [ ] T015 [US1] Add the `GET /tools/{project_id}/catalog` endpoint in `solune/backend/src/api/tools.py` using the shared models from `solune/backend/src/models/tools.py`
- [ ] T016 [US1] Implement validated `browseCatalog()` support in `solune/frontend/src/services/api.ts` using `solune/frontend/src/services/schemas/tools.ts`
- [ ] T017 [US1] Implement `catalogKeys` and `useMcpCatalog(projectId, query, category)` in `solune/frontend/src/hooks/useTools.ts` with stable cache behavior and retry/refetch support
- [ ] T018 [US1] Create `solune/frontend/src/components/tools/McpCatalogBrowse.tsx` with search input, category chips, server cards, quality/type badges, retry UI, no-results messaging, and incremental loading for large result sets
- [ ] T019 [US1] Integrate `solune/frontend/src/components/tools/McpCatalogBrowse.tsx` into `solune/frontend/src/components/tools/ToolsPanel.tsx` between `McpPresetsGallery` and the tool archive while keeping presets, repo config, and upload flows intact
- [ ] T020 [US1] Run story verification against `solune/backend/tests/unit/test_api_tools.py`, `solune/backend/tests/unit/test_tools_catalog.py`, `solune/frontend/src/hooks/useTools.test.tsx`, `solune/frontend/src/components/tools/__tests__/McpCatalogBrowse.test.tsx`, and `solune/frontend/src/components/tools/__tests__/ToolsPanel.test.tsx`: `cd solune/backend && uv run pytest tests/unit/test_api_tools.py tests/unit/test_tools_catalog.py -q && cd ../frontend && npm run test -- src/hooks/useTools.test.tsx src/components/tools/__tests__/McpCatalogBrowse.test.tsx src/components/tools/__tests__/ToolsPanel.test.tsx`

**Checkpoint**: Browsing, search, category filtering, empty state, retry state, and incremental result display work independently.

---

## Phase 4: User Story 2 - Import MCP Server from Catalog (Priority: P1)

**Goal**: Let a user import a selected catalog server as an `McpToolConfig` and see it reflected in the existing tool archive.

**Independent Test**: From the Browse MCP Catalog section, import one HTTP server, one SSE server, and one stdio/local server in separate runs; verify each import creates a tool in the archive with the correct stored configuration shape and user-friendly error handling on invalid imports.

### Tests for User Story 2 ⚠️

- [ ] T021 [P] [US2] Extend `solune/backend/tests/unit/test_tools_service.py` and `solune/backend/tests/unit/test_api_tools.py` with failing import tests for `POST /api/v1/tools/{project_id}/catalog/import`, `http`/`sse`/`stdio` mapping, unsupported transport rejection, malformed install-config errors, and duplicate conflict handling
- [ ] T022 [P] [US2] Extend `solune/frontend/src/hooks/useTools.test.tsx` and `solune/frontend/src/components/tools/__tests__/McpCatalogBrowse.test.tsx` with failing tests for import mutations, per-card loading states, error recovery, and archive refresh after import

### Implementation for User Story 2

- [ ] T023 [US2] Implement install-config normalization and `mcpServers` JSON mapping in `solune/backend/src/services/tools/catalog.py` for `http`, `sse`, `stdio`, and `local` transports while rejecting unsupported variants with clear validation errors
- [ ] T024 [US2] Reuse existing tool creation and conflict checks in `solune/backend/src/services/tools/service.py` and `solune/backend/src/api/tools.py` to add `POST /tools/{project_id}/catalog/import` without creating a second persistence path
- [ ] T025 [US2] Add validated `importFromCatalog()` support in `solune/frontend/src/services/api.ts` and `useImportMcpServer(projectId)` mutation logic in `solune/frontend/src/hooks/useTools.ts` that invalidates `toolKeys.list(projectId)`, `repoMcpKeys.detail(projectId)`, and catalog queries on success
- [ ] T026 [US2] Update `solune/frontend/src/components/tools/McpCatalogBrowse.tsx` to trigger imports, disable non-importable entries, surface user-friendly import errors, and update imported cards/tool archive state after successful creation
- [ ] T027 [US2] Run story verification against `solune/backend/tests/unit/test_api_tools.py`, `solune/backend/tests/unit/test_tools_service.py`, `solune/frontend/src/hooks/useTools.test.tsx`, and `solune/frontend/src/components/tools/__tests__/McpCatalogBrowse.test.tsx`: `cd solune/backend && uv run pytest tests/unit/test_api_tools.py tests/unit/test_tools_service.py -q && cd ../frontend && npm run test -- src/hooks/useTools.test.tsx src/components/tools/__tests__/McpCatalogBrowse.test.tsx`

**Checkpoint**: Catalog imports create valid MCP tools, unsupported variants fail clearly, and imported tools appear in the existing archive.

---

## Phase 5: User Story 3 - Sync Imported MCP Server to Repository (Priority: P2)

**Goal**: Ensure imported catalog tools flow through the existing Sync to Repo behavior and merge into repository `mcp.json` content safely.

**Independent Test**: Import a catalog server, use the existing sync action from the tool archive, and confirm the repository `mcp.json` contains the imported server alongside existing entries without overwriting them.

### Tests for User Story 3 ⚠️

- [ ] T028 [P] [US3] Extend `solune/backend/tests/unit/test_tools_service.py` and `solune/backend/tests/unit/test_api_tools.py` with failing sync regression tests proving catalog-imported tools reuse repository merge behavior, preserve existing `mcpServers`, and surface sync failures cleanly
- [ ] T029 [P] [US3] Extend `solune/frontend/src/hooks/useTools.test.tsx` and `solune/frontend/src/components/tools/__tests__/ToolsPanel.test.tsx` with failing tests that imported catalog tools appear in the archive immediately and retain the existing Sync to Repo action and error messaging

### Implementation for User Story 3

- [ ] T030 [US3] Ensure catalog-imported tools populate sync-compatible `name`, `description`, `endpoint_url`, `config_content`, and `github_repo_target` fields in `solune/backend/src/services/tools/catalog.py` and `solune/backend/src/services/tools/service.py` so repository sync reuses the current merge path unchanged
- [ ] T031 [US3] Update `solune/frontend/src/components/tools/ToolsPanel.tsx` and `solune/frontend/src/components/tools/ToolCard.tsx` so catalog-imported tools surface immediately in the archive and continue using the existing Sync to Repo UX without catalog-specific branching
- [ ] T032 [US3] Run story verification against `solune/backend/tests/unit/test_tools_service.py`, `solune/backend/tests/unit/test_api_tools.py`, `solune/frontend/src/components/tools/__tests__/ToolsPanel.test.tsx`, and the manual sync flow documented in `specs/006-mcp-catalog-on-tools-page/quickstart.md`

**Checkpoint**: Imported catalog tools behave exactly like manually uploaded tools during repository sync.

---

## Phase 6: User Story 4 - Already-Installed Detection (Priority: P2)

**Goal**: Show installed badges for catalog entries already present in the current project and prevent duplicate imports visually and behaviorally.

**Independent Test**: Import a server, reload or refetch the catalog, confirm its card shows `Installed` with no import button, then remove the tool and confirm the card returns to an importable state.

### Tests for User Story 4 ⚠️

- [ ] T033 [P] [US4] Extend `solune/backend/tests/unit/test_tools_catalog.py` and `solune/backend/tests/unit/test_tools_service.py` with failing tests for `already_installed` matching by normalized server name, parsed `config_content`, repo URL, duplicate-prevention flows, and removal-driven badge reset
- [ ] T034 [P] [US4] Extend `solune/frontend/src/components/tools/__tests__/McpCatalogBrowse.test.tsx` and `solune/frontend/src/components/tools/__tests__/ToolsPanel.test.tsx` with failing tests for installed badges, hidden import CTAs, and badge reset after delete/refetch

### Implementation for User Story 4

- [ ] T035 [US4] Implement project-aware `already_installed` derivation in `solune/backend/src/services/tools/catalog.py` by comparing normalized catalog entries against existing project tools exposed through `solune/backend/src/services/tools/service.py`
- [ ] T036 [US4] Update `solune/frontend/src/hooks/useTools.ts` and `solune/frontend/src/components/tools/McpCatalogBrowse.tsx` so import/delete mutations refetch catalog data and render `Installed` badges consistently while preserving current search/category state
- [ ] T037 [US4] Run story verification against `solune/backend/tests/unit/test_tools_catalog.py`, `solune/backend/tests/unit/test_tools_service.py`, `solune/frontend/src/components/tools/__tests__/McpCatalogBrowse.test.tsx`, and `solune/frontend/src/components/tools/__tests__/ToolsPanel.test.tsx`: `cd solune/backend && uv run pytest tests/unit/test_tools_catalog.py tests/unit/test_tools_service.py -q && cd ../frontend && npm run test -- src/components/tools/__tests__/McpCatalogBrowse.test.tsx src/components/tools/__tests__/ToolsPanel.test.tsx`

**Checkpoint**: Installed-state badges, duplicate prevention, and badge reset after removal all work independently.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Run the full validation bundle and manual smoke tests across the completed browse/import/sync workflow.

- [ ] T038 Run backend quality gates for `solune/backend/src/api/tools.py`, `solune/backend/src/models/tools.py`, `solune/backend/src/services/tools/catalog.py`, and `solune/backend/src/services/tools/service.py`: `cd solune/backend && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run pyright src/ && uv run pytest tests/unit/test_api_tools.py tests/unit/test_tools_service.py tests/unit/test_catalog.py tests/unit/test_tools_catalog.py -q`
- [ ] T039 [P] Run frontend quality gates for `solune/frontend/src/components/tools/McpCatalogBrowse.tsx`, `solune/frontend/src/components/tools/ToolsPanel.tsx`, `solune/frontend/src/hooks/useTools.ts`, `solune/frontend/src/services/api.ts`, `solune/frontend/src/services/schemas/tools.ts`, and `solune/frontend/src/types/index.ts`: `cd solune/frontend && npm run lint && npm run type-check && npm run test && npm run build`
- [ ] T040 [P] Execute the manual browse/import/sync smoke test from `specs/006-mcp-catalog-on-tools-page/quickstart.md` against `solune/frontend/src/components/tools/ToolsPanel.tsx` and repository `mcp.json` outputs: browse catalog, search `github`, import GitHub MCP, verify archive appearance, sync to repo, and confirm the imported server is written alongside existing MCP entries
- [ ] T041 [P] Perform regression review across `solune/frontend/src/components/tools/McpPresetsGallery.tsx`, `solune/frontend/src/components/tools/RepoConfigPanel.tsx`, `solune/frontend/src/components/tools/UploadMcpModal.tsx`, and `solune/frontend/src/components/tools/ToolsPanel.tsx` to confirm the new catalog section does not break presets, repo-config editing, manual upload, or existing tool archive behavior

**Checkpoint**: Full validation passes and the end-to-end feature behaves as specified.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies; can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories
- **Phase 3 (US1 Browse)**: Depends on Phase 2
- **Phase 4 (US2 Import)**: Depends on US1 browse surface and shared foundations
- **Phase 5 (US3 Sync)**: Depends on US2 import creating standard MCP tools
- **Phase 6 (US4 Installed Detection)**: Depends on US1 browse plus US2 import state
- **Final Phase (Polish)**: Depends on all desired user stories being complete

### User Story Dependencies

| Story | Priority | Depends On | Notes |
|-------|----------|------------|-------|
| US1 | P1 | Phase 2 | Independent MVP browse value |
| US2 | P1 | US1 | Reuses browse cards and shared catalog models |
| US3 | P2 | US2 | Requires imported MCP tool records |
| US4 | P2 | US1, US2 | Installed badges need browse + imported tool state |

### Within Each User Story

- Write tests first and confirm they fail before implementation
- Backend normalization/service work before API wiring
- API client/hooks before UI integration
- Import must reuse existing tool CRUD and sync behavior rather than creating a second path
- Finish story verification before starting dependent stories

---

## Parallel Opportunities

- **Setup**: T002-T004 can run in parallel after T001
- **Foundational**: T006, T007, and T009 can run in parallel once T005/T008 requirements are understood
- **US1**: T010-T013 can run in parallel; T016-T018 can run in parallel after T014-T015 establish the backend contract
- **US2**: T021 and T022 can run in parallel; T025 and T026 can proceed in parallel after T023-T024 define the import contract
- **US3**: T028 and T029 can run in parallel
- **US4**: T033 and T034 can run in parallel
- **Polish**: T039-T041 can run in parallel after T038 starts or completes

---

## Parallel Execution Examples Per Story

### US1 Parallel Example

```bash
# Write browse tests in parallel
Task: "T010 Add backend catalog browse service tests in solune/backend/tests/unit/test_tools_catalog.py"
Task: "T011 Extend solune/backend/tests/unit/test_api_tools.py for GET /tools/{project_id}/catalog"
Task: "T012 Extend solune/frontend/src/hooks/useTools.test.tsx for useMcpCatalog"
Task: "T013 Add browse UI tests in solune/frontend/src/components/tools/__tests__/McpCatalogBrowse.test.tsx"
```

### US2 Parallel Example

```bash
# Add import-focused tests in parallel
Task: "T021 Extend solune/backend/tests/unit/test_tools_service.py and test_api_tools.py for catalog import"
Task: "T022 Extend solune/frontend/src/hooks/useTools.test.tsx and McpCatalogBrowse.test.tsx for import UX"
```

### US3 Parallel Example

```bash
# Verify sync regressions in parallel
Task: "T028 Extend solune/backend/tests/unit/test_tools_service.py and test_api_tools.py for repo sync reuse"
Task: "T029 Extend solune/frontend/src/hooks/useTools.test.tsx and ToolsPanel.test.tsx for archive + sync behavior"
```

### US4 Parallel Example

```bash
# Add installed-state coverage in parallel
Task: "T033 Extend solune/backend/tests/unit/test_tools_catalog.py and test_tools_service.py for already_installed detection"
Task: "T034 Extend solune/frontend/src/components/tools/__tests__/McpCatalogBrowse.test.tsx and ToolsPanel.test.tsx for Installed badges"
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2
2. Deliver **US1 only** to prove the browse/search/filter catalog experience
3. Validate the Tools page catalog section independently before enabling import work

### Incremental Delivery

1. Add US1 browse UX
2. Add US2 import mapping and archive integration
3. Add US3 repo-sync verification for imported tools
4. Add US4 installed-state detection and duplicate-prevention polish
5. Finish with full backend/frontend validation and manual smoke tests

### Parallel Team Strategy

1. One developer completes backend catalog foundations in `solune/backend/src/models/tools.py` and `solune/backend/src/services/tools/catalog.py`
2. One developer completes frontend catalog types/validators in `solune/frontend/src/types/index.ts` and `solune/frontend/src/services/schemas/tools.ts`
3. After the shared contract is stable:
   - Developer A: backend API/import work (`solune/backend/src/api/tools.py`, `solune/backend/src/services/tools/service.py`)
   - Developer B: frontend hooks/client work (`solune/frontend/src/services/api.ts`, `solune/frontend/src/hooks/useTools.ts`)
   - Developer C: UI work (`solune/frontend/src/components/tools/McpCatalogBrowse.tsx`, `solune/frontend/src/components/tools/ToolsPanel.tsx`)

---

## Notes

- `specs/006-mcp-catalog-on-tools-page/spec.md` is missing; this task list intentionally uses `specs/006-mcp-catalog-tools-page/spec.md` as the authoritative story source because the request explicitly forbids moving or renaming files
- `solune/backend/tests/unit/test_tools_catalog.py` and `solune/frontend/src/components/tools/__tests__/McpCatalogBrowse.test.tsx` are expected new test files
- Keep Glama as the only live catalog source; Microsoft MCP curation remains filtering metadata only
- Reuse existing tool persistence and repo sync flows; do not introduce a second MCP storage model
