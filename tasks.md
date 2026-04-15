# Tasks: MCP Catalog on Tools Page

**Feature**: `006-mcp-catalog-tools-page` | **Branch**: `copilot/add-mcp-catalog-tools-page`
**Input**: Design documents from the copilot branch artifact root `/home/runner/work/solune/solune/`
**Prerequisites**: `/home/runner/work/solune/solune/plan.md` ✅, `/home/runner/work/solune/solune/spec.md` ✅, `/home/runner/work/solune/solune/research.md` ✅, `/home/runner/work/solune/solune/data-model.md` ✅, `/home/runner/work/solune/solune/quickstart.md` ✅, `/home/runner/work/solune/solune/contracts/mcp-catalog-contract.yaml` ✅

**Tests**: Included. The specification explicitly requires backend, frontend, and manual verification for browse, import, installed-state detection, and repo sync.

**Organization**: Tasks are grouped by user story so each story can be implemented, verified, and demoed independently while still following the backend → frontend dependency chain in the plan.

## Format: `- [ ] T### [P?] [US#?] Description with file path`

- **[P]**: Task can run in parallel with other marked tasks once its dependencies are met.
- **[US#]**: Required on all user story tasks and omitted on Setup, Foundational, and Polish tasks.
- Every task below includes at least one exact file path.

## Path Conventions

- **Backend root**: `/home/runner/work/solune/solune/solune/backend`
- **Frontend root**: `/home/runner/work/solune/solune/solune/frontend`
- **Backend catalog API**: `/home/runner/work/solune/solune/solune/backend/src/api/tools.py`
- **Backend catalog models**: `/home/runner/work/solune/solune/solune/backend/src/models/tools.py`
- **Backend catalog service**: `/home/runner/work/solune/solune/solune/backend/src/services/tools/catalog.py`
- **Frontend tools panel**: `/home/runner/work/solune/solune/solune/frontend/src/components/tools/ToolsPanel.tsx`
- **Frontend browse UI**: `/home/runner/work/solune/solune/solune/frontend/src/components/tools/McpCatalogBrowse.tsx`
- **Frontend hooks**: `/home/runner/work/solune/solune/solune/frontend/src/hooks/useTools.ts`
- **Frontend API client**: `/home/runner/work/solune/solune/solune/frontend/src/services/api.ts`
- **Validation**: `/home/runner/work/solune/solune/quickstart.md`

---

## Phase 1: Setup (Shared Implementation Baseline)

**Purpose**: Prepare the feature-specific test and contract scaffolding that guides the backend and frontend work.

- [ ] T001 Create backend catalog test coverage scaffold in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_tools_catalog.py` for browse, import, cache, duplicate, and sync-ready config scenarios
- [ ] T002 [P] Create frontend catalog test coverage scaffold in `/home/runner/work/solune/solune/solune/frontend/src/components/tools/__tests__/McpCatalogBrowse.test.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/hooks/useTools.test.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/services/api.test.ts`, and `/home/runner/work/solune/solune/solune/frontend/src/components/tools/__tests__/ToolsPanel.test.tsx`
- [ ] T003 [P] Align the browse/import contract details in `/home/runner/work/solune/solune/contracts/mcp-catalog-contract.yaml` with `/home/runner/work/solune/solune/plan.md`, `/home/runner/work/solune/solune/spec.md`, and `/home/runner/work/solune/solune/data-model.md` before wiring implementation files

**Checkpoint**: Test targets, contract expectations, and file touchpoints are explicit before shared code starts.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add the shared backend and frontend primitives that every user story relies on.

**⚠️ CRITICAL**: No user story work should begin until these shared models, services, and client primitives exist.

- [ ] T004 Add `CatalogInstallConfig`, `CatalogMcpServer`, `CatalogMcpServerListResponse`, and `ImportCatalogMcpRequest` to `/home/runner/work/solune/solune/solune/backend/src/models/tools.py`
- [ ] T005 [P] Create the shared Glama catalog service structure in `/home/runner/work/solune/solune/solune/backend/src/services/tools/catalog.py` with allowlisted upstream constants, TTL cache helpers, normalization helpers, and import-mapping helpers
- [ ] T006 [P] Add `CatalogInstallConfig`, `CatalogMcpServer`, and related schema/types to `/home/runner/work/solune/solune/solune/frontend/src/types/index.ts` and `/home/runner/work/solune/solune/solune/frontend/src/services/api.ts`
- [ ] T007 Wire shared catalog query keys, browse helpers, and mutation invalidation helpers in `/home/runner/work/solune/solune/solune/frontend/src/hooks/useTools.ts` and `/home/runner/work/solune/solune/solune/frontend/src/services/api.ts`

**Checkpoint**: Shared models, service scaffolding, and client primitives are ready; browse and import stories can now build on the same contract.

---

## Phase 3: User Story 1 - Browse MCP Server Catalog (Priority: P1) 🎯 MVP

**Goal**: Let users browse Glama-backed MCP servers on the Tools page with text search, category filters, responsive cards, and resilient loading/error behavior.

**Independent Test**: Open the Tools page, scroll to the MCP catalog section, search for `github`, switch category chips, and confirm the card grid updates while loading, empty, and retry states remain understandable.

### Tests for User Story 1

- [ ] T008 [P] [US1] Add backend browse tests in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_tools_catalog.py` for Glama response normalization, one-hour stale-fallback caching, SSRF-safe upstream validation, category filtering, and catalog-unavailable error handling
- [ ] T009 [P] [US1] Add browse response schema validation coverage to `/home/runner/work/solune/solune/solune/frontend/src/services/api.test.ts` for `CatalogMcpServerListResponse` parsing and invalid payload rejection

### Implementation for User Story 1

- [ ] T010 [US1] Implement Glama fetch, payload normalization, query/category filtering, and stale-fallback cache reads in `/home/runner/work/solune/solune/solune/backend/src/services/tools/catalog.py`
- [ ] T011 [US1] Add `GET /api/v1/tools/{project_id}/catalog` to `/home/runner/work/solune/solune/solune/backend/src/api/tools.py` using the shared models from `/home/runner/work/solune/solune/solune/backend/src/models/tools.py`
- [ ] T012 [P] [US1] Implement `toolsApi.browseCatalog()` in `/home/runner/work/solune/solune/solune/frontend/src/services/api.ts` and `useMcpCatalog(projectId, query, category)` in `/home/runner/work/solune/solune/solune/frontend/src/hooks/useTools.ts`
- [ ] T013 [P] [US1] Build the browse/search/filter UI in `/home/runner/work/solune/solune/solune/frontend/src/components/tools/McpCatalogBrowse.tsx` with search input, category chips, card grid, quality/type badges, and loading/error/empty states, then cover those states in `/home/runner/work/solune/solune/solune/frontend/src/components/tools/__tests__/McpCatalogBrowse.test.tsx`
- [ ] T014 [US1] Integrate `/home/runner/work/solune/solune/solune/frontend/src/components/tools/McpCatalogBrowse.tsx` into `/home/runner/work/solune/solune/solune/frontend/src/components/tools/ToolsPanel.tsx` between the presets gallery and tool archive, and update `/home/runner/work/solune/solune/solune/frontend/src/components/tools/__tests__/ToolsPanel.test.tsx`

**Checkpoint**: Users can browse and filter the catalog independently of import or repo sync.

---

## Phase 4: User Story 2 - Import MCP Server from Catalog (Priority: P1)

**Goal**: Let users import a selected catalog server into the existing MCP tool archive with transport-aware config mapping and immediate UI feedback.

**Independent Test**: From the catalog section, click `Import` on an HTTP, SSE, or stdio server and confirm the tool archive updates, the request handles errors cleanly, and the card flips to `Installed` when import succeeds.

### Tests for User Story 2

- [ ] T015 [P] [US2] Add import tests in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_tools_catalog.py` for supported transport mapping, malformed install configs, duplicate import rejection, and not-found catalog IDs
- [ ] T016 [P] [US2] Add import client and mutation tests in `/home/runner/work/solune/solune/solune/frontend/src/services/api.test.ts` and `/home/runner/work/solune/solune/solune/frontend/src/hooks/useTools.test.tsx` for success, conflict, and validation-error flows

### Implementation for User Story 2

- [ ] T017 [US2] Implement `import_from_catalog()` in `/home/runner/work/solune/solune/solune/backend/src/services/tools/catalog.py` so `http`, `sse`, `stdio`, and `local` install configs become sync-ready `mcpServers` JSON snippets for `McpToolConfig.config_content`
- [ ] T018 [US2] Add `POST /api/v1/tools/{project_id}/catalog/import` to `/home/runner/work/solune/solune/solune/backend/src/api/tools.py` with duplicate prevention and existing tool-service reuse
- [ ] T019 [P] [US2] Implement `toolsApi.importFromCatalog()` in `/home/runner/work/solune/solune/solune/frontend/src/services/api.ts` and `useImportMcpServer(projectId)` in `/home/runner/work/solune/solune/solune/frontend/src/hooks/useTools.ts` with catalog, tools, and repo-MCP query invalidation
- [ ] T020 [US2] Update `/home/runner/work/solune/solune/solune/frontend/src/components/tools/McpCatalogBrowse.tsx` and `/home/runner/work/solune/solune/solune/frontend/src/components/tools/__tests__/McpCatalogBrowse.test.tsx` so each card shows `Import`, pending, `Installed`, and user-friendly error states

**Checkpoint**: A catalog entry can be imported into the standard MCP tool archive without touching repo sync yet.

---

## Phase 5: User Story 3 - Sync Imported MCP Server to Repository (Priority: P2)

**Goal**: Ensure imported catalog tools flow through the existing sync-to-repo path so `mcp.json` updates without any catalog-specific sync logic.

**Independent Test**: Import a catalog server, click the existing `Sync to Repo` action on the archived tool, and confirm the repository `mcp.json` gains the expected `mcpServers` entry alongside any existing tools.

### Tests for User Story 3

- [ ] T021 [P] [US3] Add sync-readiness assertions to `/home/runner/work/solune/solune/solune/backend/tests/unit/test_tools_catalog.py` proving imported `config_content` matches the `mcp.json` format consumed by `/home/runner/work/solune/solune/solune/backend/src/services/tools/service.py`

### Implementation for User Story 3

- [ ] T022 [US3] Reuse the existing sync flow by ensuring `/home/runner/work/solune/solune/solune/backend/src/services/tools/catalog.py` creates ordinary `McpToolConfig` records compatible with `/home/runner/work/solune/solune/solune/backend/src/services/tools/service.py` and existing `mcp.json` merge behavior
- [ ] T023 [P] [US3] Extend `/home/runner/work/solune/solune/solune/frontend/src/components/tools/__tests__/ToolsPanel.test.tsx` and `/home/runner/work/solune/solune/solune/frontend/src/hooks/useTools.test.tsx` to confirm imported catalog tools appear in the archive and remain syncable through the current UI workflow

**Checkpoint**: Imported catalog tools behave exactly like manually created MCP tools during repo sync.

---

## Phase 6: User Story 4 - Already-Installed Detection (Priority: P2)

**Goal**: Prevent duplicate imports by marking catalog cards as installed whenever the current project already contains the matching MCP tool.

**Independent Test**: Import a server, return to the catalog, and confirm the same card shows `Installed`; remove the tool through existing archive flows, refresh the catalog query, and confirm the card can return to `Import`.

### Tests for User Story 4

- [ ] T024 [P] [US4] Add installed-state coverage in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_tools_catalog.py` and `/home/runner/work/solune/solune/solune/frontend/src/components/tools/__tests__/McpCatalogBrowse.test.tsx` for matching and non-matching project tools

### Implementation for User Story 4

- [ ] T025 [US4] Derive `already_installed` from current project tool names during catalog normalization in `/home/runner/work/solune/solune/solune/backend/src/services/tools/catalog.py` and surface it through `/home/runner/work/solune/solune/solune/backend/src/api/tools.py`
- [ ] T026 [US4] Update `/home/runner/work/solune/solune/solune/frontend/src/components/tools/McpCatalogBrowse.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/components/tools/__tests__/McpCatalogBrowse.test.tsx`, and `/home/runner/work/solune/solune/solune/frontend/src/components/tools/__tests__/ToolsPanel.test.tsx` so refetched catalog cards swap between `Import` and `Installed` based on the current tool list

**Checkpoint**: Installed-state feedback prevents duplicate imports and stays aligned with the actual project tool archive.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Run the planned backend, frontend, and manual verification steps once all user stories are complete.

- [ ] T027 Run the backend catalog verification command from `/home/runner/work/solune/solune/quickstart.md` against `/home/runner/work/solune/solune/solune/backend/tests/unit/test_tools_catalog.py`
- [ ] T028 [P] Run the targeted frontend catalog tests from `/home/runner/work/solune/solune/quickstart.md` covering `/home/runner/work/solune/solune/solune/frontend/src/components/tools/__tests__/McpCatalogBrowse.test.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/hooks/useTools.test.tsx`, and `/home/runner/work/solune/solune/solune/frontend/src/services/api.test.ts`
- [ ] T029 [P] Run the frontend safety checks from `/home/runner/work/solune/solune/quickstart.md` in `/home/runner/work/solune/solune/solune/frontend`: `npm run type-check`, `npm run lint`, and `npm run build`
- [ ] T030 [P] Execute the manual browse → import → sync verification flow from `/home/runner/work/solune/solune/quickstart.md` and confirm the synced repository `mcp.json` contains the imported `mcpServers` entry

**Checkpoint**: The catalog feature is verified end to end across backend tests, frontend tests, and the manual sync workflow.

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 (Setup)
  -> Phase 2 (Foundational)
     -> Phase 3 (US1: Browse catalog)
        -> Phase 4 (US2: Import catalog server)
           -> Phase 5 (US3: Sync imported tool to repo)
           -> Phase 6 (US4: Already-installed detection)
              -> Final Phase (Polish)
```

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2. No dependency on other user stories.
- **US2 (P1)**: Depends on US1 browse surfaces existing so the import action has a visible catalog entry point.
- **US3 (P2)**: Depends on US2 because sync-to-repo only applies after a catalog tool has been imported.
- **US4 (P2)**: Depends on US1 and US2 because installed-state is derived from the browse response plus imported tool data.

### Within Each Phase

- Tests in each user story phase should be written first and fail before implementation begins.
- Backend contract/model/service work should land before the frontend hook/UI task that consumes it.
- Tasks marked **[P]** touch different files or can be prepared simultaneously from the same contract.
- The Final Phase starts only after the desired user stories are complete.

### Parallel Opportunities

- **Setup**: T002 and T003 can run in parallel after T001 establishes the test target.
- **Foundational**: T005 and T006 can run in parallel after T004 defines the shared backend models.
- **US1**: T008 and T009 can run in parallel; T012 and T013 can run in parallel once T010 and T011 settle the browse contract.
- **US2**: T015 and T016 can run in parallel; T019 can proceed in parallel with backend endpoint work once T017 is stable.
- **US3**: T021 and T023 can run in parallel while T022 ensures the persisted payload stays sync-compatible.
- **US4**: T024 can be split across backend and frontend test files in parallel before T025 and T026 land.
- **Polish**: T028, T029, and T030 can run in parallel after T027 if the team wants separate owners for frontend tests, safety checks, and manual verification.

---

## Parallel Execution Examples Per Story

### User Story 1

```text
T008 backend browse tests in /home/runner/work/solune/solune/solune/backend/tests/unit/test_tools_catalog.py
T009 frontend browse schema tests in /home/runner/work/solune/solune/solune/frontend/src/services/api.test.ts
```

### User Story 2

```text
T015 backend import tests in /home/runner/work/solune/solune/solune/backend/tests/unit/test_tools_catalog.py
T016 frontend import mutation tests in /home/runner/work/solune/solune/solune/frontend/src/services/api.test.ts and /home/runner/work/solune/solune/solune/frontend/src/hooks/useTools.test.tsx
```

### User Story 3

```text
T021 sync-readiness backend assertions in /home/runner/work/solune/solune/solune/backend/tests/unit/test_tools_catalog.py
T023 archive and sync workflow frontend assertions in /home/runner/work/solune/solune/solune/frontend/src/components/tools/__tests__/ToolsPanel.test.tsx
```

### User Story 4

```text
Backend half of T024 in /home/runner/work/solune/solune/solune/backend/tests/unit/test_tools_catalog.py
Frontend half of T024 in /home/runner/work/solune/solune/solune/frontend/src/components/tools/__tests__/McpCatalogBrowse.test.tsx
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Deliver Phase 3 so users can browse and filter the MCP catalog on the Tools page.
3. Validate the independent test for US1 before moving on.

### Incremental Delivery

1. Deliver US1 browse so discovery value lands first.
2. Add US2 import so discovery becomes actionable.
3. Add US3 sync reuse so imported tools activate in `mcp.json`.
4. Add US4 installed-state detection so duplicate prevention stays aligned with the archive.
5. Finish with the planned automated and manual verification tasks.

### Suggested Team Split

1. One engineer handles backend models, service logic, and API routes in `/home/runner/work/solune/solune/solune/backend`.
2. One engineer handles frontend types, hooks, and API client work in `/home/runner/work/solune/solune/solune/frontend/src/services`, `/home/runner/work/solune/solune/solune/frontend/src/hooks`, and `/home/runner/work/solune/solune/solune/frontend/src/types`.
3. One engineer handles the browse UI and Tools page integration in `/home/runner/work/solune/solune/solune/frontend/src/components/tools`.

---

## Notes

- Total tasks: 30
- User story task counts: US1 = 7, US2 = 6, US3 = 3, US4 = 3
- Setup tasks: 3
- Foundational tasks: 4
- Polish tasks: 4
- Absolute repository paths are intentional because this task's generation instructions require absolute paths.
- All task lines follow the required `- [ ] T### [P?] [US#?] Description with file path` checklist format.
