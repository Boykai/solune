# Implementation Plan: Awesome Copilot Agent Import

**Branch**: `003-copilot-agent-import` | **Date**: 2026-04-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-copilot-agent-import/spec.md`

## Summary

This feature adds one-click import of Awesome Copilot agents into Solune projects and a separate install action that commits agents to GitHub repositories. The implementation extends the existing agent lifecycle with an `imported` state, adds a catalog reader that parses Awesome Copilot's cached `llms.txt` index for browsing/searching, stores raw agent markdown snapshots in the database on import (no GitHub writes), and reuses the existing `github_commit_workflow.py` pipeline on install to create a parent issue and PR containing the raw `.agent.md` file plus a generated `.prompt.md` routing file. The frontend gains a dedicated browse modal, import badges, and a confirmation-gated install flow — all kept separate from the existing custom-agent authoring.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript/React (frontend)
**Primary Dependencies**: FastAPI, Pydantic, aiosqlite, PyYAML (backend); React, Vite, TailwindCSS, React Query (frontend)
**Storage**: SQLite via aiosqlite (schema migration to add columns to `agent_configs` + new `agent_catalog_cache` table)
**Testing**: pytest + pytest-asyncio (backend), Vitest (frontend)
**Target Platform**: Linux server (Docker)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: Browse modal loads within 3 seconds (SC-001); import completes in under 5 seconds (SC-002); search filters within 1 second (SC-005)
**Constraints**: Zero GitHub API calls during import (SC-006); imported agent raw content must be preserved verbatim through the full lifecycle (SC-004); import is project-scoped, not global
**Scale/Scope**: 1 new DB migration; 1 new backend service module (catalog reader); extensions to agents service, API, and models; 3 new frontend components (BrowseAgentsModal, ImportAgentButton, InstallConfirmDialog); extensions to AgentsPanel, AgentCard, useAgents, api.ts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | `spec.md` exists with 4 prioritized user stories (P1–P3), Given-When-Then acceptance scenarios, edge cases, and clear scope boundaries (Awesome Copilot only, project-scoped, no custom-agent editing of imports) |
| II. Template-Driven | ✅ PASS | All artifacts follow canonical templates from `.specify/templates/` |
| III. Agent-Orchestrated | ✅ PASS | Single-responsibility: this plan phase produces design artifacts; implementation deferred to `/speckit.tasks` + `/speckit.implement` |
| IV. Test Optionality | ✅ PASS | Spec explicitly requests targeted coverage in `test_agents_service.py`, `test_api_agents.py`, `test_github_agents.py`, `AgentsPanel.test.tsx`, `useAgents.test.tsx`, `AgentsPage.test.tsx`, and `agent-creation.spec.ts`. Tests will be included in task generation |
| V. Simplicity and DRY | ✅ PASS | Reuses existing `github_commit_workflow.py` for install; reuses `InMemoryCache` + `cached_fetch` for catalog caching; reuses `.prompt.md` generation pattern from `agent_creator.py`; no new abstractions beyond a catalog reader function and import/install service split |

**Gate Result**: ALL PASS — proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/003-copilot-agent-import/
├── plan.md              # This file
├── research.md          # Phase 0: Research findings
├── data-model.md        # Phase 1: Entity and data model
├── quickstart.md        # Phase 1: Developer quickstart guide
├── contracts/           # Phase 1: API contracts
│   └── agent-import.yaml  # Import/install/catalog endpoint contracts
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── api/
│   │   └── agents.py              # MODIFY: Add catalog browse, import, and install endpoints
│   ├── models/
│   │   └── agents.py              # MODIFY: Add CatalogAgent, ImportedAgent models, extend AgentStatus
│   ├── services/
│   │   ├── agents/
│   │   │   ├── service.py         # MODIFY: Split import from install; add import_agent(), install_agent()
│   │   │   └── catalog.py         # NEW: Awesome Copilot catalog reader (parse llms.txt, fetch raw markdown)
│   │   ├── cache.py               # EXISTING: Reuse InMemoryCache + cached_fetch (no changes)
│   │   ├── agent_creator.py       # EXISTING: Reuse .prompt.md generation pattern (no changes)
│   │   └── github_commit_workflow.py  # EXISTING: Reuse for install workflow (no changes)
│   └── migrations/
│       └── 030_agent_import.sql   # NEW: Add import columns to agent_configs + catalog cache table
└── tests/
    └── unit/
        ├── test_agents_service.py # MODIFY: Add import/install service tests
        ├── test_api_agents.py     # MODIFY: Add catalog/import/install endpoint tests
        ├── test_github_agents.py  # MODIFY: Add install GitHub workflow tests
        └── test_catalog.py        # NEW: Catalog reader unit tests

solune/frontend/
├── src/
│   ├── components/
│   │   ├── agents/
│   │   │   ├── AgentsPanel.tsx            # MODIFY: Add browse button, imported agent rendering
│   │   │   ├── AgentCard.tsx              # MODIFY: Add imported/installed status badges, install action
│   │   │   ├── BrowseAgentsModal.tsx      # NEW: Dedicated modal for browsing/searching catalog agents
│   │   │   ├── InstallConfirmDialog.tsx   # NEW: Confirmation dialog before install
│   │   │   └── AddAgentModal.tsx          # EXISTING: No changes (custom-agent authoring stays separate)
│   │   └── pages/
│   │       └── AgentsPage.tsx             # EXISTING: No structural changes (project-scoped shell preserved)
│   ├── hooks/
│   │   └── useAgents.ts                   # MODIFY: Add useCatalogAgents, useImportAgent, useInstallAgent hooks
│   ├── services/
│   │   └── api.ts                         # MODIFY: Add catalogApi methods (browse, import, install)
│   └── types/
│       └── index.ts                       # MODIFY: Add CatalogAgent, ImportedAgent types (or api.ts inline)
└── tests/
    ├── AgentsPanel.test.tsx       # MODIFY: Add browse modal, imported agent badge tests
    ├── useAgents.test.tsx         # MODIFY: Add catalog/import/install hook tests
    └── AgentsPage.test.tsx        # MODIFY: Add imported agent rendering tests
```

**Structure Decision**: Web application structure. Changes span both `solune/backend/` (new catalog reader, import/install service split, DB migration, API endpoints) and `solune/frontend/` (browse modal, import badges, install confirmation). One new backend module (`catalog.py`), two new frontend components (`BrowseAgentsModal.tsx`, `InstallConfirmDialog.tsx`), and one new migration. All other changes extend existing files. Custom-agent authoring (`AddAgentModal.tsx`) is untouched.

## Constitution Re-Check (Post-Design)

*Re-evaluation after Phase 1 design artifacts are complete.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Design artifacts (data-model, contracts, quickstart) all trace back to spec.md requirements FR-001 through FR-018 |
| II. Template-Driven | ✅ PASS | All generated artifacts follow canonical templates |
| III. Agent-Orchestrated | ✅ PASS | Plan phase complete; handoff to `/speckit.tasks` for task decomposition |
| IV. Test Optionality | ✅ PASS | Tests explicitly requested in spec — backend tests for catalog parsing, import storage, and install workflow; frontend tests for browse modal, import badges, and install confirmation |
| V. Simplicity and DRY | ✅ PASS | Catalog reader is a single function parsing a text index; import is a DB insert; install reuses `commit_files_workflow()` and `.prompt.md` generation from `agent_creator.py`. No new frameworks, no new abstraction layers. Raw markdown stored verbatim avoids lossy normalization |

**Gate Result**: ALL PASS — ready for Phase 2 (`/speckit.tasks`).

## Complexity Tracking

> No constitution violations — this section is intentionally empty.
