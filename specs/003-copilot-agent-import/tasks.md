# Tasks: Awesome Copilot Agent Import

**Input**: Design documents from `/specs/003-copilot-agent-import/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests ARE included — the spec explicitly requests targeted coverage in `test_agents_service.py`, `test_api_agents.py`, `test_github_agents.py`, `AgentsPanel.test.tsx`, `useAgents.test.tsx`, `AgentsPage.test.tsx`, and `agent-creation.spec.ts` (plan.md Constitution Check IV).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/frontend/src/`
- Backend tests: `solune/backend/tests/unit/`
- Frontend tests: `solune/frontend/src/components/agents/`, `solune/frontend/src/hooks/`, `solune/frontend/src/pages/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database migration and shared model/type extensions that all user stories depend on

- [ ] T001 Create database migration in `solune/backend/src/migrations/030_agent_import.sql` adding `agent_type`, `catalog_source_url`, `catalog_agent_id`, `raw_source_content`, and `imported_at` columns to `agent_configs` table with `idx_agent_configs_catalog` index
- [ ] T002 [P] Extend `AgentStatus` enum with `IMPORTED = "imported"` and `INSTALLED = "installed"` values in `solune/backend/src/models/agents.py`
- [ ] T003 [P] Add `CatalogAgent`, `ImportAgentRequest`, `ImportAgentResult`, and `InstallAgentResult` Pydantic models in `solune/backend/src/models/agents.py`
- [ ] T004 [P] Extend existing `Agent` model with `agent_type`, `catalog_source_url`, `catalog_agent_id`, and `imported_at` fields in `solune/backend/src/models/agents.py`
- [ ] T005 [P] Add `CatalogAgent`, `ImportAgentRequest`, `ImportAgentResult`, `InstallAgentResult` TypeScript interfaces and extend `AgentConfig` and `AgentStatus` types in `solune/frontend/src/services/api.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core catalog reader service and shared API/service infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Create catalog reader module in `solune/backend/src/services/agents/catalog.py` with `_fetch_catalog_index()` helper to fetch llms.txt from `https://awesome-copilot.github.com/agents/llms.txt`
- [ ] T007 Implement `_parse_catalog_index(raw_text)` function in `solune/backend/src/services/agents/catalog.py` to parse llms.txt text into `CatalogAgent` objects
- [ ] T008 Implement `list_catalog_agents(project_id, db)` in `solune/backend/src/services/agents/catalog.py` using `InMemoryCache` + `cached_fetch` with 1-hour TTL and stale-fallback, marking `already_imported` flag from DB
- [ ] T009 Implement `fetch_agent_raw_content(source_url)` in `solune/backend/src/services/agents/catalog.py` to fetch raw agent markdown on demand
- [ ] T010 [P] Extend `_list_local_agents()` in `solune/backend/src/services/agents/service.py` to include `agent_type`, `catalog_source_url`, `catalog_agent_id`, and `imported_at` fields when constructing `Agent` objects

**Checkpoint**: Foundation ready — catalog reader works, models extended, migration applied. User story implementation can now begin.

---

## Phase 3: User Story 1 — Browse Available Agents (Priority: P1) 🎯 MVP

**Goal**: A user opens a dedicated browse modal from the Agents page to discover, search, and filter available Awesome Copilot agents from a cached catalog index.

**Independent Test**: Open the browse modal and verify agents are listed, searchable, and filterable. Delivers value by letting users explore the Awesome Copilot catalog without leaving Solune.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T011 [P] [US1] Add catalog parsing unit tests in `solune/backend/tests/unit/test_catalog.py` — test `_parse_catalog_index` with valid llms.txt content, empty content, and malformed content
- [ ] T012 [P] [US1] Add catalog caching unit tests in `solune/backend/tests/unit/test_catalog.py` — test `list_catalog_agents` with cache hit, cache miss, stale fallback, and `already_imported` flag marking
- [ ] T013 [P] [US1] Add catalog browse endpoint test in `solune/backend/tests/unit/test_api_agents.py` — test `GET /{project_id}/catalog` returns 200 with agent list, handles auth, and returns empty list on fetch failure
- [ ] T014 [P] [US1] Add `useCatalogAgents` hook test in `solune/frontend/src/hooks/useAgents.test.tsx` — test loading state, successful fetch, error state, and cache behavior
- [ ] T015 [P] [US1] Add `BrowseAgentsModal` component test in `solune/frontend/src/components/agents/AgentsPanel.test.tsx` — test modal opens on button click, agents render, search filters, loading/error states, already-imported badge
- [ ] T016 [P] [US1] Add `AgentsPage` browse integration test in `solune/frontend/src/pages/AgentsPage.test.tsx` — test "Browse Agents" button renders and opens modal

### Implementation for User Story 1

- [ ] T017 [US1] Add browse catalog endpoint `GET /{project_id}/catalog` in `solune/backend/src/api/agents.py` calling `catalog.list_catalog_agents()` with project access verification
- [ ] T018 [P] [US1] Add `catalogApi.browse(projectId)` method in `solune/frontend/src/services/api.ts`
- [ ] T019 [P] [US1] Add `useCatalogAgents(projectId)` hook in `solune/frontend/src/hooks/useAgents.ts` using React Query with 5-minute stale time
- [ ] T020 [US1] Create `BrowseAgentsModal.tsx` component in `solune/frontend/src/components/agents/BrowseAgentsModal.tsx` with search input, agent list, loading/error/empty states, and "Import" button per agent row
- [ ] T021 [US1] Add "Browse Agents" button to `solune/frontend/src/components/agents/AgentsPanel.tsx` that opens `BrowseAgentsModal`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Users can open the browse modal, see catalog agents, and search/filter the list.

---

## Phase 4: User Story 2 — Import an Agent to Project (Priority: P1) 🎯 MVP

**Goal**: A user selects an agent from the browse modal and imports it into the current project with a single click. The agent is saved as a project-scoped database snapshot with raw source content and appears on the Agents page with an "Imported" badge.

**Independent Test**: Import an agent from the browse modal, then verify it appears on the Agents page with the correct badge and metadata. No GitHub interaction is required.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T022 [P] [US2] Add `import_agent()` service unit tests in `solune/backend/tests/unit/test_agents_service.py` — test successful import stores raw content verbatim, sets `agent_type='imported'`/`lifecycle_status='imported'`, handles duplicate import (409), and handles raw content fetch failure (502)
- [ ] T023 [P] [US2] Add import endpoint test in `solune/backend/tests/unit/test_api_agents.py` — test `POST /{project_id}/import` returns 201 with `ImportAgentResult`, 409 for duplicate, 502 for fetch failure
- [ ] T024 [P] [US2] Add `useImportAgent` hook test in `solune/frontend/src/hooks/useAgents.test.tsx` — test mutation triggers, success invalidates agent and catalog query keys, error handling
- [ ] T025 [P] [US2] Add import button test in `solune/frontend/src/components/agents/AgentsPanel.test.tsx` — test import from browse modal triggers API call, success shows "Imported ✓", duplicate shows error toast

### Implementation for User Story 2

- [ ] T026 [US2] Implement `import_agent()` method in `solune/backend/src/services/agents/service.py` — validate duplicate via `catalog_agent_id + project_id`, fetch raw content via `catalog.fetch_agent_raw_content()`, insert into `agent_configs` with `agent_type='imported'`, `lifecycle_status='imported'`, `raw_source_content` verbatim, return `ImportAgentResult`
- [ ] T027 [US2] Add import endpoint `POST /{project_id}/import` in `solune/backend/src/api/agents.py` with project access verification, delegating to `service.import_agent()`
- [ ] T028 [P] [US2] Add `agentsApi.import(projectId, data)` method in `solune/frontend/src/services/api.ts`
- [ ] T029 [P] [US2] Add `useImportAgent(projectId)` mutation hook in `solune/frontend/src/hooks/useAgents.ts` with query invalidation on success
- [ ] T030 [US2] Wire import button in `BrowseAgentsModal.tsx` to call `useImportAgent` — disable button for already-imported agents, show "Imported ✓" on success, show error toast on failure, keep modal open for multi-import in `solune/frontend/src/components/agents/BrowseAgentsModal.tsx`
- [ ] T031 [US2] Add "Imported" status badge (amber/yellow) to `AgentCard.tsx` for agents with `lifecycle_status === 'imported'` in `solune/frontend/src/components/agents/AgentCard.tsx`
- [ ] T032 [US2] Render imported agents in agent grid in `solune/frontend/src/components/agents/AgentsPanel.tsx` with correct badge differentiation from custom agents

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Users can browse the catalog, import agents, and see them on the Agents page with "Imported" badges.

---

## Phase 5: User Story 3 — Install Agent to Repository (Priority: P2)

**Goal**: A user selects a previously imported agent and installs it to a repository. A confirmation dialog is shown before creating a GitHub issue and PR that commits the raw `.agent.md` file and generated `.prompt.md` routing file.

**Independent Test**: Install a previously imported agent, confirm the confirmation step appears, verify the GitHub issue and PR are created with the correct file contents, and see the agent status change to "Installed".

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T033 [P] [US3] Add `install_agent()` service unit tests in `solune/backend/tests/unit/test_agents_service.py` — test successful install calls `commit_files_workflow()` with raw `.agent.md` + generated `.prompt.md`, updates `lifecycle_status='installed'`, rejects non-imported agents (400), handles GitHub errors (500)
- [ ] T034 [P] [US3] Add install GitHub workflow tests in `solune/backend/tests/unit/test_github_agents.py` — test install generates correct file paths (`.github/agents/{slug}.agent.md`, `.github/prompts/{slug}.prompt.md`), raw content preserved verbatim, `.prompt.md` routing content generated correctly
- [ ] T035 [P] [US3] Add install endpoint test in `solune/backend/tests/unit/test_api_agents.py` — test `POST /{project_id}/{agent_id}/install` returns 200 with `InstallAgentResult`, 400 for non-imported agent, 404 for missing agent, 500 for GitHub failure
- [ ] T036 [P] [US3] Add `useInstallAgent` hook test in `solune/frontend/src/hooks/useAgents.test.tsx` — test mutation triggers, success invalidates agent query key, error handling
- [ ] T037 [P] [US3] Add `InstallConfirmDialog` component test in `solune/frontend/src/components/agents/AgentsPanel.test.tsx` — test dialog shows agent name/description/target repo/file summary, confirm triggers install API call, cancel closes dialog without action

### Implementation for User Story 3

- [ ] T038 [US3] Implement `install_agent()` method in `solune/backend/src/services/agents/service.py` — load imported agent, generate `.agent.md` (raw content verbatim) and `.prompt.md` (routing file from slug via `agent_creator.py` pattern), call `commit_files_workflow()`, update `lifecycle_status='installed'` with issue/PR/branch references, return `InstallAgentResult`
- [ ] T039 [US3] Add install endpoint `POST /{project_id}/{agent_id}/install` in `solune/backend/src/api/agents.py` with project access verification, validating agent exists and is in `imported` state, delegating to `service.install_agent()`
- [ ] T040 [P] [US3] Add `agentsApi.install(projectId, agentId)` method in `solune/frontend/src/services/api.ts`
- [ ] T041 [P] [US3] Add `useInstallAgent(projectId)` mutation hook in `solune/frontend/src/hooks/useAgents.ts` with query invalidation on success
- [ ] T042 [US3] Create `InstallConfirmDialog.tsx` component in `solune/frontend/src/components/agents/InstallConfirmDialog.tsx` showing agent name, description, target repo, file summary (`.agent.md` + `.prompt.md`), and Install/Cancel buttons with loading state
- [ ] T043 [US3] Add "Add to repo" button to `AgentCard.tsx` for agents with `agent_type === 'imported' && lifecycle_status === 'imported'` that opens `InstallConfirmDialog` in `solune/frontend/src/components/agents/AgentCard.tsx`
- [ ] T044 [US3] Add "Installed" status badge (green) with PR/issue links to `AgentCard.tsx` for agents with `lifecycle_status === 'installed'` in `solune/frontend/src/components/agents/AgentCard.tsx`

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should all work independently. Users can browse, import, and install agents with full GitHub integration.

---

## Phase 6: User Story 4 — View Imported Agent Details (Priority: P3)

**Goal**: A user can view the full details of an imported agent, including raw source content, catalog origin metadata, and current status. Imported agents are read-only external snapshots.

**Independent Test**: Import an agent and view its detail view to confirm all metadata and raw content are displayed correctly, and that no edit controls are available.

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T045 [P] [US4] Add imported agent detail view test in `solune/frontend/src/components/agents/AgentsPanel.test.tsx` — test clicking imported agent shows name, description, catalog origin URL, import date, and raw source content
- [ ] T046 [P] [US4] Add read-only enforcement test in `solune/frontend/src/components/agents/AgentsPanel.test.tsx` — test imported agents have no edit button, no system-prompt editor, no tool configuration controls

### Implementation for User Story 4

- [ ] T047 [US4] Hide edit/system-prompt/tool-configuration controls in `AgentCard.tsx` when `agent.agent_type === 'imported'` (read-only snapshot per FR-015) in `solune/frontend/src/components/agents/AgentCard.tsx`
- [ ] T048 [US4] Display catalog origin URL, import date, and raw source content preview in `AgentCard.tsx` detail view for imported agents in `solune/frontend/src/components/agents/AgentCard.tsx`

**Checkpoint**: All user stories should now be independently functional. Users can browse, import, install, and view agent details.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration tests, contract validation, error handling improvements, and documentation

- [ ] T049 [P] Add E2E agent import/install test in `solune/frontend/e2e/agent-creation.spec.ts` — test full browse → import → install flow
- [ ] T050 Run contract validation against `specs/003-copilot-agent-import/contracts/agent-import.yaml` to verify API shape matches the contract
- [ ] T051 [P] Add error handling for edge cases across all endpoints: stale cache notice, no repositories connected (disable install), agent file already exists in target repo warning
- [ ] T052 Code cleanup and verify no regressions — run full backend test suite (`uv run pytest tests/ -q`), frontend test suite (`npx vitest run`), linting (`uv run ruff check`, `npm run lint`), and type checking (`uv run pyright src`, `npx tsc --noEmit`)
- [ ] T053 Run `specs/003-copilot-agent-import/quickstart.md` verification steps to validate end-to-end flow

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion — Browse catalog
- **User Story 2 (Phase 4)**: Depends on Phase 2 + Phase 3 (browse modal needed for import button)
- **User Story 3 (Phase 5)**: Depends on Phase 2 + Phase 4 (imported agent needed for install)
- **User Story 4 (Phase 6)**: Depends on Phase 2 (can proceed in parallel with US3 after US2)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **User Story 2 (P1)**: Depends on User Story 1 (the "Import" button lives inside the BrowseAgentsModal from US1)
- **User Story 3 (P2)**: Depends on User Story 2 (needs an imported agent to install)
- **User Story 4 (P3)**: Depends on User Story 2 (needs an imported agent to view). Can proceed in parallel with User Story 3

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints/API
- Backend before frontend (API must exist before UI calls it)
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Phase 1 tasks T002–T005 marked [P] can run in parallel (different files)
- Phase 2 task T010 [P] can run in parallel with T006–T009 (different file)
- All test tasks within each user story marked [P] can run in parallel
- Within Phase 4: T028 [P] and T029 [P] can run in parallel (different files)
- Within Phase 5: T040 [P] and T041 [P] can run in parallel (different files)
- Within Phase 6: T045 [P] and T046 [P] can run in parallel
- User Story 4 (Phase 6) can proceed in parallel with User Story 3 (Phase 5) after User Story 2 completes

---

## Parallel Example: User Story 1

```text
# Launch all tests for User Story 1 together:
Task: T011 "Catalog parsing unit tests in solune/backend/tests/unit/test_catalog.py"
Task: T012 "Catalog caching unit tests in solune/backend/tests/unit/test_catalog.py"
Task: T013 "Catalog browse endpoint test in solune/backend/tests/unit/test_api_agents.py"
Task: T014 "useCatalogAgents hook test in solune/frontend/src/hooks/useAgents.test.tsx"
Task: T015 "BrowseAgentsModal component test in solune/frontend/src/components/agents/AgentsPanel.test.tsx"
Task: T016 "AgentsPage browse integration test in solune/frontend/src/pages/AgentsPage.test.tsx"

# Launch parallel frontend tasks:
Task: T018 "Add catalogApi.browse() method in solune/frontend/src/services/api.ts"
Task: T019 "Add useCatalogAgents hook in solune/frontend/src/hooks/useAgents.ts"
```

## Parallel Example: User Story 2

```text
# Launch all tests for User Story 2 together:
Task: T022 "import_agent() service tests in solune/backend/tests/unit/test_agents_service.py"
Task: T023 "Import endpoint test in solune/backend/tests/unit/test_api_agents.py"
Task: T024 "useImportAgent hook test in solune/frontend/src/hooks/useAgents.test.tsx"
Task: T025 "Import button test in solune/frontend/src/components/agents/AgentsPanel.test.tsx"

# Launch parallel frontend tasks:
Task: T028 "Add agentsApi.import() in solune/frontend/src/services/api.ts"
Task: T029 "Add useImportAgent hook in solune/frontend/src/hooks/useAgents.ts"
```

## Parallel Example: User Story 3

```text
# Launch all tests for User Story 3 together:
Task: T033 "install_agent() service tests in solune/backend/tests/unit/test_agents_service.py"
Task: T034 "Install GitHub workflow tests in solune/backend/tests/unit/test_github_agents.py"
Task: T035 "Install endpoint test in solune/backend/tests/unit/test_api_agents.py"
Task: T036 "useInstallAgent hook test in solune/frontend/src/hooks/useAgents.test.tsx"
Task: T037 "InstallConfirmDialog test in solune/frontend/src/components/agents/AgentsPanel.test.tsx"

# Launch parallel frontend tasks:
Task: T040 "Add agentsApi.install() in solune/frontend/src/services/api.ts"
Task: T041 "Add useInstallAgent hook in solune/frontend/src/hooks/useAgents.ts"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup (migration + models + types)
2. Complete Phase 2: Foundational (catalog reader + list extension)
3. Complete Phase 3: User Story 1 — Browse Available Agents
4. Complete Phase 4: User Story 2 — Import an Agent to Project
5. **STOP and VALIDATE**: Test browse + import flow independently
6. Deploy/demo if ready — users can already discover and import agents

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (Browse) → Test independently → Deploy/Demo
3. Add User Story 2 (Import) → Test independently → Deploy/Demo (MVP!)
4. Add User Story 3 (Install) → Test independently → Deploy/Demo
5. Add User Story 4 (View Details) → Test independently → Deploy/Demo
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Browse) → then User Story 2 (Import)
   - Developer B: User Story 3 (Install) — starts after US2 delivers import service
   - Developer C: User Story 4 (View Details) — starts after US2 delivers imported agents
3. Stories complete and integrate independently

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tasks** | 53 |
| **Phase 1 (Setup)** | 5 tasks |
| **Phase 2 (Foundational)** | 5 tasks |
| **Phase 3 (US1 — Browse)** | 11 tasks (6 test + 5 impl) |
| **Phase 4 (US2 — Import)** | 11 tasks (4 test + 7 impl) |
| **Phase 5 (US3 — Install)** | 12 tasks (5 test + 7 impl) |
| **Phase 6 (US4 — View Details)** | 4 tasks (2 test + 2 impl) |
| **Phase 7 (Polish)** | 5 tasks |
| **Parallel opportunities** | 33 tasks marked [P] or parallelizable within phases |
| **Suggested MVP scope** | Phase 1 + Phase 2 + Phase 3 (Browse) + Phase 4 (Import) |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Raw agent markdown MUST be preserved verbatim throughout the entire lifecycle (key risk from spec)
- The `.prompt.md` routing file is the ONLY generated artifact during install
- Zero GitHub API calls during import — only during install (SC-006)
- Custom-agent authoring (`AddAgentModal.tsx`) is completely untouched
