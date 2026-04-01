# Tasks: Autonomous App Builder

**Input**: Design documents from `/specs/002-autonomous-app-builder/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests ARE included — the spec explicitly mandates unit tests for template rendering, pipeline auto-config, and import URL validation (Constitution Check IV, Verification section).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/` under `solune/`
- Backend tests: `backend/tests/unit/`
- Frontend tests: `frontend/tests/unit/` or co-located `*.test.tsx`
- Templates on disk: `backend/templates/app-templates/`
- DB migrations: `backend/src/migrations/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization — new packages, directories, DB migration, and TypeScript types

- [x] T001 Create `backend/src/services/app_templates/` package with `__init__.py` in `solune/backend/src/services/app_templates/__init__.py`
- [x] T002 [P] Create app template directories structure under `solune/backend/templates/app-templates/` with subdirectories: `saas-react-fastapi/files/`, `api-fastapi/files/`, `cli-python/files/`, `dashboard-react/files/`
- [x] T003 [P] Create DB migration `solune/backend/src/migrations/036_app_template_fields.sql` adding nullable `template_id TEXT` column to the `apps` table
- [x] T004 [P] Create TypeScript types for templates and build progress in `solune/frontend/src/types/app-template.ts` (AppTemplateSummary, AppTemplate, TemplateFile, BuildProgressPayload, BuildMilestonePayload, BuildCompletePayload, BuildFailedPayload, ImportAppRequest, ImportAppResponse, BuildAppRequest, BuildAppResponse, IterateRequest, IterateResponse — per contracts/)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and template definitions that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Create `AppCategory`, `ScaffoldType`, `IaCTarget` enums and `TemplateFile`, `AppTemplate` dataclass in `solune/backend/src/models/app_template.py` per data-model.md (StrEnum classes, Pydantic BaseModel for TemplateFile, dataclass with validation: id kebab-case pattern, files[].target no `..` or leading `/`, non-empty tech_stack)
- [x] T006 [P] Extend `App` and `AppCreate` models with nullable `template_id: str | None` field in `solune/backend/src/models/app.py`
- [x] T007 [P] Create `BuildProgress`, `BuildPhase`, `BuildMilestone` models in `solune/backend/src/models/build_progress.py` per data-model.md (Pydantic model with app_name, phase, agent_name, detail, pct_complete, started_at, updated_at; BuildPhase and BuildMilestone as StrEnum)
- [x] T008 [P] Create `template.json` metadata for `saas-react-fastapi` template in `solune/backend/templates/app-templates/saas-react-fastapi/template.json` (id, name: "SaaS — React + FastAPI", category: saas, difficulty: L, tech_stack: [react, fastapi, postgresql], scaffold_type: starter, recommended_preset_id, iac_target: azure, files manifest)
- [x] T009 [P] Create `template.json` metadata for `api-fastapi` template in `solune/backend/templates/app-templates/api-fastapi/template.json` (id, name: "API — FastAPI", category: api, difficulty: M, tech_stack: [fastapi, postgresql], scaffold_type: skeleton, recommended_preset_id, iac_target: docker, files manifest)
- [x] T010 [P] Create `template.json` metadata for `cli-python` template in `solune/backend/templates/app-templates/cli-python/template.json` (id, name: "CLI — Python", category: cli, difficulty: S, tech_stack: [python, click], scaffold_type: skeleton, recommended_preset_id, iac_target: none, files manifest)
- [x] T011 [P] Create `template.json` metadata for `dashboard-react` template in `solune/backend/templates/app-templates/dashboard-react/template.json` (id, name: "Dashboard — React", category: dashboard, difficulty: M, tech_stack: [react, vite, tailwind], scaffold_type: starter, recommended_preset_id, iac_target: docker, files manifest)
- [x] T012 [P] Create `.tmpl` file trees for `saas-react-fastapi` template under `solune/backend/templates/app-templates/saas-react-fastapi/files/` (e.g., `backend/main.py.tmpl`, `frontend/App.tsx.tmpl`, `README.md.tmpl` with `{{app_name}}`, `{{description}}`, `{{port}}` variables)
- [x] T013 [P] Create `.tmpl` file trees for `api-fastapi` template under `solune/backend/templates/app-templates/api-fastapi/files/` (e.g., `main.py.tmpl`, `requirements.txt.tmpl`, `README.md.tmpl`)
- [x] T014 [P] Create `.tmpl` file trees for `cli-python` template under `solune/backend/templates/app-templates/cli-python/files/` (e.g., `cli.py.tmpl`, `pyproject.toml.tmpl`, `README.md.tmpl`)
- [x] T015 [P] Create `.tmpl` file trees for `dashboard-react` template under `solune/backend/templates/app-templates/dashboard-react/files/` (e.g., `src/App.tsx.tmpl`, `vite.config.ts.tmpl`, `README.md.tmpl`)

**Checkpoint**: Foundation ready — all models defined, template definitions on disk, DB migration prepared. User story implementation can now begin.

---

## Phase 3: User Story 2 — App Template Browsing and Selection (Priority: P1) 🎯 MVP

**Goal**: Users can browse a library of 4 app templates, filter by category, and select one to start app creation. AI agent can list and inspect templates during conversation.

**Independent Test**: Navigate to the template browser → verify 4 template cards displayed → filter by category → click "Use Template" → verify creation flow starts.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T016 [P] [US2] Unit tests for template registry and loader in `solune/backend/tests/unit/test_app_templates.py` — test `discover_templates()` finds all 4 templates, `get_template()` returns correct metadata, `get_template()` returns None for unknown ID, `list_templates()` with category filter
- [x] T017 [P] [US2] Unit test for TemplateBrowser component in `solune/frontend/src/components/apps/TemplateBrowser.test.tsx` — test renders 4 template cards, category filter works, "Use Template" click triggers callback

### Implementation for User Story 2

- [x] T018 [US2] Implement template loader in `solune/backend/src/services/app_templates/loader.py` — `load_template(template_dir: Path) -> AppTemplate` reads `template.json`, validates against AppTemplate model, resolves file paths relative to template dir
- [x] T019 [US2] Implement template registry in `solune/backend/src/services/app_templates/registry.py` — `discover_templates(base_dir: Path) -> dict[str, AppTemplate]` scans `app-templates/` subdirectories, `get_template(template_id: str) -> AppTemplate | None`, `list_templates(category: AppCategory | None) -> list[AppTemplate]`; lazy-load with module-level cache
- [x] T020 [US2] Add `list_app_templates()` and `get_app_template()` agent tools in `solune/backend/src/services/agent_tools.py` — `list_app_templates(category: str | None) -> list[dict]` returns template summaries, `get_app_template(template_id: str) -> dict | None` returns full template details; register both with the agent tool registry
- [x] T021 [US2] Add `GET /api/templates` and `GET /api/templates/{template_id}` endpoints in `solune/backend/src/api/apps.py` — list endpoint with optional `?category=` query param, detail endpoint returns full template or 404; per `contracts/templates-api.yaml`
- [x] T022 [P] [US2] Create `TemplateBrowser.tsx` component in `solune/frontend/src/components/apps/TemplateBrowser.tsx` — grid of template cards (name, category badge, difficulty, description, tech stack tags), category dropdown filter, "Use Template" button per card, "Let AI configure" button that opens chat
- [x] T023 [US2] Extend `AppsPage.tsx` in `solune/frontend/src/pages/AppsPage.tsx` — add "Templates" tab that renders the TemplateBrowser component alongside existing app list

**Checkpoint**: Template library fully browsable via API, agent tools, and frontend. 4 templates visible with filtering.

---

## Phase 4: User Story 1 — Conversational App Building (Priority: P1) 🎯 MVP

**Goal**: User types "Build me a stock app" → agent asks 2–3 questions → presents plan → user confirms → app scaffolded with template files, pipeline configured, issue created, pipeline launched.

**Independent Test**: Type "Build me a dashboard app" in chat → answer 2–3 questions → confirm plan → verify new app in Apps page with scaffolded files, configured pipeline, and launched issue.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T024 [P] [US1] Unit tests for template renderer in `solune/backend/tests/unit/test_app_templates.py` (append to existing) — test `render_template()` substitutes `{{app_name}}` correctly, rejects path-traversal (`../` in target), rejects absolute paths in target, fails gracefully for undefined variables with clear error message
- [x] T025 [P] [US1] Unit tests for pipeline auto-configuration in `solune/backend/tests/unit/test_pipeline_config.py` — test `configure_pipeline_preset()` maps difficulty S→easy/M→medium/L→hard/XL→expert, inserts architect agent when `iac_target != none`, omits architect when `iac_target == none`, respects difficulty_override

### Implementation for User Story 1

- [x] T026 [US1] Implement template renderer in `solune/backend/src/services/app_templates/renderer.py` — `render_template(template_id: str, context: dict[str, str], target_dir: Path) -> list[Path]`: loads template via registry, validates all target paths with `os.path.realpath()` boundary check (R3), substitutes `{{var}}` via `str.replace()` (R1), writes rendered files, returns list of created paths; raises `ValueError` for undefined variables or path-traversal attempts
- [x] T027 [US1] Implement pipeline auto-configuration in `solune/backend/src/services/pipelines/pipeline_config.py` — `configure_pipeline_preset(template: AppTemplate, difficulty_override: str | None = None) -> tuple[str, bool]`: returns `(preset_id, include_architect)` per data-model.md mapping logic; `DIFFICULTY_PRESET_MAP` dict mapping S/M/L/XL to preset IDs
- [x] T028 [US1] Extend `create_app()` in `solune/backend/src/services/app_service.py` to accept optional `template_id: str | None` parameter — when provided, call `render_template()` to scaffold files instead of minimal default; store `template_id` in the App record
- [x] T029 [US1] Implement `build_app()` orchestration tool in `solune/backend/src/services/agent_tools.py` — chains: validate template → `create_app(template_id)` → `configure_pipeline_preset()` → create pipeline with architect insertion if needed → create parent issue → launch pipeline; returns `BuildAppResponse` dict per `contracts/build-api.yaml`
- [x] T030 [US1] Implement `generate_app_questions()` clarification tool in `solune/backend/src/services/agent_tools.py` — `generate_app_questions(description: str) -> list[str]`: returns 2–3 targeted questions using template catalog context (category preference, complexity, deployment target); per R7 decision
- [x] T031 [US1] Add `POST /api/apps/{app_name}/build` endpoint in `solune/backend/src/api/apps.py` — accepts `BuildAppRequest` body per `contracts/build-api.yaml`, returns 202 with `BuildAppResponse`, validates template exists, enforces unique app name (409 on conflict)
- [x] T032 [US1] Extend `AGENT_SYSTEM_INSTRUCTIONS` in `solune/backend/src/prompts/agent_instructions.py` — add app-builder intent recognition: "build me an app" / "create an app" → call `generate_app_questions()` → collect answers → select template → present structured plan card (template, preset, ETA) → on confirmation call `build_app()`
- [x] T033 [P] [US1] Extend `CreateAppDialog.tsx` in `solune/frontend/src/components/apps/CreateAppDialog.tsx` — add template selection step: show TemplateBrowser inline → on template select, pre-populate form with template defaults (name suggestion, description) → proceed to name/customize step → create
- [x] T034 [P] [US1] Create app creation wizard flow in `solune/frontend/src/pages/AppsPage.tsx` — wire "Use Template" action from TemplateBrowser to CreateAppDialog with template pre-selected; wire "Let AI configure" to open chat with template context

**Checkpoint**: Full conversational build flow works end-to-end. User can build an app from template via chat or UI wizard.

---

## Phase 5: User Story 4 — GitHub Repository Import (Priority: P2)

**Goal**: Users can import an existing GitHub repository into Solune, creating an app record linked to the external repo with optional pipeline and Project V2 board.

**Independent Test**: Navigate to "Import from GitHub" → enter valid repo URL → see repo info → confirm import → verify app record created with linked repo.

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T035 [P] [US4] Unit tests for import URL validation in `solune/backend/tests/unit/test_import_validation.py` — test valid `https://github.com/owner/repo` accepted, malformed URLs rejected, non-GitHub URLs rejected, URLs with extra path segments handled, duplicate import detection

### Implementation for User Story 4

- [x] T036 [US4] Implement `import_app_from_repo()` in `solune/backend/src/services/app_service.py` — validate URL format (regex for `github.com/{owner}/{repo}`), verify repo accessibility via githubkit API call (R6), check not already imported (unique `external_repo_url`), create App record with `repo_type=EXTERNAL_REPO`, optionally create Project V2 board; return created App + project URL
- [x] T037 [US4] Add `POST /api/apps/import` endpoint in `solune/backend/src/api/apps.py` — accepts `ImportAppRequest` body per `contracts/import-api.yaml`, returns 201 with `ImportAppResponse`, returns 400 for invalid URL / already imported, 403 for insufficient permissions
- [x] T038 [US4] Implement `import_github_repo()` agent tool in `solune/backend/src/services/agent_tools.py` — `import_github_repo(url: str, pipeline_id: str | None = None, create_project: bool = True) -> dict`: wraps `import_app_from_repo()`, optionally triggers iteration pipeline if `pipeline_id` provided
- [x] T039 [P] [US4] Create `ImportAppDialog.tsx` component in `solune/frontend/src/components/apps/ImportAppDialog.tsx` — URL input with real-time validation feedback, repo info display (name, description, language) on valid URL, "Create Project Board" checkbox, optional pipeline selector, "Import" confirmation button
- [x] T040 [US4] Extend `AppsPage.tsx` in `solune/frontend/src/pages/AppsPage.tsx` — add "Import from GitHub" tab that renders the ImportAppDialog component

**Checkpoint**: GitHub import fully functional via API, agent tool, and frontend. External repos linked in Solune.

---

## Phase 6: User Story 3 — Build Progress Monitoring (Priority: P2)

**Goal**: Real-time build progress visible across chat (status messages + completion summary), frontend panel (stepper/timeline), and Signal (milestone notifications) within 2 seconds of phase transitions.

**Independent Test**: Start an app build → verify progress messages in chat with phase/agent/indicator → verify frontend stepper shows completed/active/pending phases → verify completion summary with links → verify Signal milestone notifications (if enabled).

### Implementation for User Story 3

- [x] T041 [US3] Implement build progress emission hooks in `solune/backend/src/services/websocket.py` — extend `ConnectionManager` (or add helper) with `broadcast_build_progress(app_name: str, progress: BuildProgress)` that serializes to `BuildProgressPayload` JSON and broadcasts via existing WebSocket; per `contracts/progress-ws.yaml`
- [x] T042 [US3] Add progress emission calls to build orchestration in `solune/backend/src/services/app_service.py` — emit `build_progress` events from `create_app()` (scaffolding phase), and in `solune/backend/src/services/agent_tools.py` from `build_app()` at each step: scaffolding → configuring → issuing → building; emit `build_milestone` at key points (scaffolded, working); emit `build_complete` or `build_failed` at end
- [x] T043 [US3] Implement chat integration for build progress in `solune/backend/src/services/agent_tools.py` — background task monitors build progress and injects status messages into active chat session; sends final summary message with links (app URL, repo URL, project URL, issue URL) on completion; per FR-017
- [x] T044 [US3] Extend Signal milestone notifications in `solune/backend/src/services/signal_delivery.py` — add `format_build_milestone(app_name: str, milestone: BuildMilestone) -> str` formatting function; send notification at each `BuildMilestone` (scaffolded, working, review, complete); per FR-018
- [x] T045 [P] [US3] Create `useBuildProgress.ts` hook in `solune/frontend/src/hooks/useBuildProgress.ts` — subscribe to existing WebSocket connection, filter for `build_progress`/`build_milestone`/`build_complete`/`build_failed` message types for a specific `app_name`, expose current progress state and event history
- [x] T046 [P] [US3] Create `BuildProgress.tsx` stepper/timeline panel in `solune/frontend/src/components/pipeline/BuildProgress.tsx` — uses `useBuildProgress` hook, shows phases as stepper steps (scaffolding → configuring → issuing → building → deploying_prep → complete), highlights current phase, shows agent name and detail text, progress bar with pct_complete
- [x] T047 [P] [US3] Create `BuildProgressCard.tsx` inline chat card in `solune/frontend/src/components/apps/BuildProgressCard.tsx` — compact card for chat messages showing current phase, active agent badge, progress bar, detail text; uses `useBuildProgress` hook; displays completion summary with links when build_complete received

**Checkpoint**: Build progress visible in real-time across chat, frontend panel, and Signal. 2-second visibility target met via WebSocket.

---

## Phase 7: User Story 5 — Iterate on Existing App (Priority: P3)

**Goal**: Users describe a change to an existing app in chat and the agent automatically creates an issue and launches a pipeline to implement it.

**Independent Test**: Type "Add user authentication to my dashboard app" in chat → verify issue created in app's project → verify pipeline launched.

### Implementation for User Story 5

- [x] T048 [US5] Implement `iterate_on_app()` tool in `solune/backend/src/services/agent_tools.py` — `iterate_on_app(app_name: str, change_description: str) -> dict`: look up existing app by name, create issue in app's project board describing the change, launch appropriate pipeline, return `IterateResponse` dict; handle app-not-found with helpful message listing available apps; handle pipeline-already-running with queue suggestion; per FR-012, FR-023
- [x] T049 [US5] Add `POST /api/apps/{app_name}/iterate` endpoint in `solune/backend/src/api/apps.py` — accepts `IterateRequest` body per `contracts/build-api.yaml`, returns 202 with `IterateResponse`, returns 404 for app not found, 409 if pipeline already running
- [x] T050 [US5] Extend `AGENT_SYSTEM_INSTRUCTIONS` in `solune/backend/src/prompts/agent_instructions.py` — add iteration intent recognition: "add X to Y app" / "change X in Y" → identify target app → call `iterate_on_app()`; handle app-not-found gracefully; per FR-023

**Checkpoint**: Iteration flow works end-to-end via chat and API. Users can continuously improve apps through natural language.

---

## Phase 8: User Story 6 — Architect Agent for Infrastructure as Code (Priority: P3)

**Goal**: Apps with IaC targets automatically include an architect agent in the pipeline that generates deployment infrastructure files (Bicep, Terraform, docker-compose, GitHub Actions).

**Independent Test**: Build app from template with `iac_target: azure` → verify pipeline includes "deploy-prep" stage with architect agent → verify IaC files generated.

### Implementation for User Story 6

- [x] T051 [US6] Verify or create `architect.agent.md` in `solune/backend/templates/.github/agents/architect.agent.md` — IaC-focused prompt supporting Bicep, Terraform, docker-compose, GitHub Actions; receives tech_stack and iac_target metadata via sub-issue body; per R9 decision
- [x] T052 [US6] Register architect agent in pipeline presets in `solune/backend/src/services/pipelines/service.py` — extend hard/expert preset definitions to support optional "deploy-prep" `ExecutionGroup` after `speckit.implement` group containing single `PipelineAgentNode` with `agent_slug="architect"`; insertion conditional on `include_architect` flag from `pipeline_config.py`
- [x] T053 [US6] Implement template-driven IaC metadata passing in `solune/backend/src/services/agent_tools.py` — when `build_app()` inserts architect agent (via pipeline config), include `tech_stack` and `iac_target` from template metadata in the sub-issue body so architect agent has context; per R9

**Checkpoint**: Architect agent automatically included for IaC templates and excluded for non-IaC templates. IaC files generated during pipeline.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories — documentation, CI validation, security hardening

- [x] T054 [P] Run `ruff check src tests` and `ruff format --check src tests` from `solune/backend/` to verify backend linting passes
- [x] T055 [P] Run `uv run pyright src` from `solune/backend/` to verify type checking passes
- [x] T056 [P] Run `vitest run` from `solune/frontend/` to verify frontend tests pass
- [x] T057 Run full backend test suite `pytest tests/unit/` from `solune/backend/` to verify all unit tests pass including new ones
- [x] T058 Run quickstart.md validation — verify all manual touchpoints documented in `specs/002-autonomous-app-builder/quickstart.md` are exercisable
- [x] T059 Security review: verify template renderer path-traversal blocking covers all edge cases per R3 (realpath resolution, `..` sequences, absolute paths, null bytes, symlinks)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US2 — Template Browsing (Phase 3)**: Depends on Foundational (Phase 2) — registry/loader need template definitions and AppTemplate model
- **US1 — Conversational Build (Phase 4)**: Depends on US2 (Phase 3) — build flow uses template registry and renderer
- **US4 — GitHub Import (Phase 5)**: Depends on Foundational (Phase 2) only — independent of template browsing
- **US3 — Build Progress (Phase 6)**: Depends on US1 (Phase 4) — needs build orchestration to emit events from
- **US5 — Iterate on App (Phase 7)**: Depends on US1 (Phase 4) — iteration extends the app/pipeline flow
- **US6 — Architect Agent (Phase 8)**: Depends on Foundational (Phase 2); can run in parallel with US1 (Phase 4) — architect registration is independent but integrates at pipeline config level
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 2 (P1)**: Can start after Foundational (Phase 2) — no dependencies on other stories
- **User Story 1 (P1)**: Depends on US2 (Phase 3) for template registry — core build flow
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) — fully independent of templates
- **User Story 3 (P2)**: Depends on US1 (Phase 4) — needs build orchestration to monitor
- **User Story 5 (P3)**: Depends on US1 (Phase 4) — extends app/pipeline management
- **User Story 6 (P3)**: Can start after Foundational (Phase 2) — parallel with US1, integrates at pipeline config level

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints/API
- Backend before frontend (API must exist for frontend to consume)
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002, T003, T004)
- All Foundational tasks T006–T015 marked [P] can run in parallel within Phase 2
- Once Foundational completes: US2 (Phase 3) and US4 (Phase 5) can start in parallel
- Once US2 completes: US1 (Phase 4) and US6 (Phase 8) can start in parallel
- Within US2: T016/T017 tests in parallel, then T018/T019 sequentially, then T022 frontend in parallel with T020/T021
- Within US1: T024/T025 tests in parallel, then T026/T027 in parallel, then T028→T029→T030→T031→T032 sequentially, T033/T034 frontend in parallel
- Within US4: T035 test first, then T036→T037→T038 sequentially, T039 frontend in parallel
- Within US3: T041→T042→T043→T044 sequentially (emission hooks before consumers), T045/T046/T047 frontend in parallel
- Different user stories can be worked on in parallel by different team members (respecting dependencies above)

---

## Parallel Example: User Story 2 (Template Browsing)

```bash
# Launch all tests for US2 together:
Task T016: "Unit tests for template registry and loader in backend/tests/unit/test_app_templates.py"
Task T017: "Unit test for TemplateBrowser component in frontend/src/components/apps/TemplateBrowser.test.tsx"

# After tests written, launch backend implementation:
Task T018: "Implement template loader in backend/src/services/app_templates/loader.py"
Task T019: "Implement template registry in backend/src/services/app_templates/registry.py" (depends on T018)

# Frontend can run in parallel with API tasks:
Task T022: "Create TemplateBrowser.tsx in frontend/src/components/apps/TemplateBrowser.tsx"
# While backend wires up:
Task T020: "Add list/get template agent tools in backend/src/services/agent_tools.py"
Task T021: "Add GET /api/templates endpoints in backend/src/api/apps.py"
```

## Parallel Example: User Story 1 (Conversational Build)

```bash
# Launch both test files in parallel:
Task T024: "Unit tests for template renderer in backend/tests/unit/test_app_templates.py"
Task T025: "Unit tests for pipeline config in backend/tests/unit/test_pipeline_config.py"

# Core services in parallel (different files):
Task T026: "Implement template renderer in backend/src/services/app_templates/renderer.py"
Task T027: "Implement pipeline auto-config in backend/src/services/pipelines/pipeline_config.py"

# Frontend wizard in parallel with backend orchestration:
Task T033: "Extend CreateAppDialog.tsx with template selection step"
Task T034: "Wire template browser to creation flow in AppsPage.tsx"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 2 — Template Browsing (P1)
4. Complete Phase 4: User Story 1 — Conversational Build (P1)
5. **STOP and VALIDATE**: Test full conversational build flow end-to-end
6. Deploy/demo if ready — users can build apps from templates via chat and UI

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US2 (Template Browsing) → Test independently → Templates browsable (partial MVP)
3. Add US1 (Conversational Build) → Test independently → Full build flow works (MVP!)
4. Add US4 (GitHub Import) → Test independently → External repos importable
5. Add US3 (Build Progress) → Test independently → Real-time visibility across channels
6. Add US5 (Iteration) → Test independently → Continuous improvement via chat
7. Add US6 (Architect Agent) → Test independently → IaC generation in pipeline
8. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US2 (Template Browsing) → then US1 (Conversational Build)
   - Developer B: US4 (GitHub Import) — independent track
   - Developer C: US6 (Architect Agent) — parallel with US1
3. Once US1 is done:
   - Developer A: US3 (Build Progress)
   - Developer C: US5 (Iteration)
4. Stories complete and integrate independently

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tasks** | 59 |
| **Phase 1 (Setup)** | 4 tasks |
| **Phase 2 (Foundational)** | 11 tasks |
| **US2 — Template Browsing (P1)** | 8 tasks (2 test + 6 impl) |
| **US1 — Conversational Build (P1)** | 11 tasks (2 test + 9 impl) |
| **US4 — GitHub Import (P2)** | 6 tasks (1 test + 5 impl) |
| **US3 — Build Progress (P2)** | 7 tasks (0 test + 7 impl) |
| **US5 — Iterate on App (P3)** | 3 tasks |
| **US6 — Architect Agent (P3)** | 3 tasks |
| **Phase 9 (Polish)** | 6 tasks |
| **Parallel opportunities** | 28 tasks marked [P] across phases |
| **Suggested MVP scope** | US2 + US1 (Phases 1–4, 34 tasks) |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in same phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
- All backend paths relative to `solune/backend/`
- All frontend paths relative to `solune/frontend/`
- Template definitions ship as static files in source control (R2 decision)
- Template renderer uses custom `{{var}}` substitution — no external engine (R1 decision)
- Build progress is in-memory only — not persisted to database (R5 decision)
