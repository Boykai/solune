# Implementation Plan: Autonomous App Builder

**Branch**: `002-autonomous-app-builder` | **Date**: 2026-03-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-autonomous-app-builder/spec.md`

## Summary

Enable natural-language app creation ("Build me a stock app with AI using Microsoft tools") through a conversational AI flow that asks 2–3 clarifying questions, selects a template, configures a pipeline, and autonomously scaffolds the app. The feature extends the existing `app_service.py`, `agent_tools.py`, and pipeline orchestration with an app template library (4 templates: SaaS, API, CLI, Dashboard), GitHub repository import, architect agent for IaC generation, and unified build-progress reporting across chat, WebSocket, and Signal.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript 6.0+ / React 19 (frontend)
**Primary Dependencies**: FastAPI ≥0.135, Microsoft Agent Framework ≥1.0.0b1, githubkit ≥0.14.6, Pydantic ≥2.12, React 19.2, TanStack React Query 5.96, Radix UI, Tailwind CSS 4.2, Vite 8.0
**Storage**: SQLite via aiosqlite ≥0.22 (existing); file-system for template definitions
**Testing**: pytest + pytest-asyncio (backend), Vitest 4.0 + Playwright 1.58 (frontend)
**Target Platform**: Linux server (backend), modern browsers (frontend)
**Project Type**: Web application (backend + frontend)
**Performance Goals**: Build progress visible within 2 s of phase transition (SC-005); import completes within 30 s (SC-004); idea-to-scaffold < 5 min interaction time (SC-001)
**Constraints**: No actual cloud deployment (IaC generation only); template rendering must block path-traversal 100 % (SC-010); simple `{{var}}` substitution — no external template engine
**Scale/Scope**: 4 app templates, 7 implementation phases, ~25 new/modified source files across backend + frontend

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Specification-First** | ✅ PASS | `spec.md` contains 6 prioritized user stories (P1–P3) with Given-When-Then scenarios, edge cases, 27 functional requirements, and 10 measurable success criteria. |
| **II. Template-Driven Workflow** | ✅ PASS | This plan follows `plan-template.md`. All output artifacts (`research.md`, `data-model.md`, `contracts/`, `quickstart.md`) adhere to the prescribed phase outputs. |
| **III. Agent-Orchestrated Execution** | ✅ PASS | Work is produced by the `speckit.plan` agent with single-purpose scope. Implementation will be handed off to `speckit.tasks` → `speckit.implement`. |
| **IV. Test Optionality** | ✅ PASS | The spec explicitly mandates tests (unit for template rendering, pipeline config, URL validation; integration for chat→build flow; E2E for full build). Tests are required. |
| **V. Simplicity and DRY** | ✅ PASS | Design reuses existing `app_service.py`, `agent_tools.py`, pipeline presets, WebSocket `ConnectionManager`, and Signal delivery. New abstractions (template registry, build progress model) are minimal and justified. No premature abstraction. |

**Gate Result**: ALL PASS — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/002-autonomous-app-builder/
├── plan.md              # This file
├── research.md          # Phase 0 output — technology decisions and research
├── data-model.md        # Phase 1 output — entity definitions and relationships
├── quickstart.md        # Phase 1 output — developer onboarding guide
├── contracts/           # Phase 1 output — API contract definitions
│   ├── templates-api.yaml
│   ├── import-api.yaml
│   ├── build-api.yaml
│   └── progress-ws.yaml
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── models/
│   │   ├── app.py                          # EXTEND: Add template_id, source fields to App/AppCreate
│   │   ├── app_template.py                 # NEW: AppTemplate, AppCategory, ScaffoldType, IaCTarget dataclass
│   │   └── build_progress.py               # NEW: BuildProgress, BuildPhase, BuildMilestone
│   ├── services/
│   │   ├── app_service.py                  # EXTEND: template-aware create_app(), import_app_from_repo()
│   │   ├── agent_tools.py                  # EXTEND: 6 new tools (list/get templates, import, build, iterate, generate questions)
│   │   ├── signal_delivery.py              # EXTEND: milestone notification formatting
│   │   ├── websocket.py                    # EXTEND: broadcast build progress events
│   │   ├── app_templates/                  # NEW PACKAGE
│   │   │   ├── __init__.py
│   │   │   ├── registry.py                 # Template discovery and lookup
│   │   │   ├── loader.py                   # Template file loading from disk
│   │   │   └── renderer.py                 # {{var}} substitution + path-traversal validation
│   │   └── pipelines/
│   │       ├── service.py                  # EXTEND: architect agent in hard/expert presets
│   │       └── pipeline_config.py          # NEW: template + difficulty → preset mapping
│   ├── api/
│   │   └── apps.py                         # EXTEND: POST /apps/import endpoint
│   ├── prompts/
│   │   └── agent_instructions.py           # EXTEND: app-builder intent recognition + clarification flow
│   └── migrations/
│       └── 027_app_template_fields.sql     # NEW: Add template_id column to apps table
├── templates/
│   └── app-templates/                      # NEW: Template definitions
│       ├── saas-react-fastapi/
│       │   ├── template.json
│       │   └── files/                      # .tmpl file tree
│       ├── api-fastapi/
│       │   ├── template.json
│       │   └── files/
│       ├── cli-python/
│       │   ├── template.json
│       │   └── files/
│       └── dashboard-react/
│           ├── template.json
│           └── files/
└── tests/
    └── unit/
        ├── test_app_templates.py           # NEW: Template rendering, registry, path-traversal tests
        ├── test_pipeline_config.py         # NEW: Pipeline auto-configuration tests
        └── test_import_validation.py       # NEW: URL validation tests

solune/frontend/
├── src/
│   ├── components/
│   │   ├── apps/
│   │   │   ├── CreateAppDialog.tsx         # EXTEND: Template selection step
│   │   │   ├── TemplateBrowser.tsx         # NEW: Grid of template cards + category filter
│   │   │   ├── ImportAppDialog.tsx         # NEW: GitHub repo import flow
│   │   │   └── BuildProgressCard.tsx       # NEW: In-chat progress card
│   │   └── pipeline/
│   │       └── BuildProgress.tsx           # NEW: Stepper/timeline panel
│   ├── pages/
│   │   └── AppsPage.tsx                    # EXTEND: Tabs for templates + import
│   ├── hooks/
│   │   └── useBuildProgress.ts             # NEW: WebSocket subscription for build events
│   └── types/
│       └── app-template.ts                 # NEW: TypeScript types for templates + progress
└── tests/
    └── unit/
        └── TemplateBrowser.test.tsx         # NEW: Template browser component tests
```

**Structure Decision**: Existing web application structure (backend + frontend under `solune/`). All new code extends existing directories. The only new sub-package is `services/app_templates/` for clean separation of template logic from the main `app_service.py`. Template definitions live under the existing `backend/templates/` directory alongside agent definitions.

## Complexity Tracking

> No Constitution violations detected — this section is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *None* | — | — |
