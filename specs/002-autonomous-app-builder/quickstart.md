# Quickstart: Autonomous App Builder

**Feature**: 002-autonomous-app-builder | **Date**: 2026-03-31

This guide walks a developer through the key touchpoints of the Autonomous App Builder feature for local development, testing, and verification.

## Prerequisites

- Python 3.12+ with `uv` package manager
- Node.js 20+ with `npm`
- GitHub Personal Access Token with `repo`, `project`, `read:org` scopes
- Solune backend and frontend running locally (see main README)

## Quick Setup

```bash
# From solune/backend/
uv sync --locked --extra dev
cp .env.example .env  # Configure GITHUB_TOKEN, etc.

# From solune/frontend/
npm install
```

## Feature Touchpoints

### 1. App Template Library

**Backend**: Templates live in `backend/templates/app-templates/`. Each template directory contains:

```
saas-react-fastapi/
├── template.json     # Metadata: id, name, category, difficulty, tech_stack, etc.
└── files/            # Renderable file tree with .tmpl extensions
    ├── backend/
    │   └── main.py.tmpl
    ├── frontend/
    │   └── App.tsx.tmpl
    └── README.md.tmpl
```

**API Endpoints**:
- `GET /api/templates` — List all templates (with optional `?category=dashboard` filter)
- `GET /api/templates/{id}` — Get full template details including file manifest

**Agent Tools**:
- `list_app_templates()` — Returns template summaries for chat agent
- `get_app_template(template_id)` — Returns full template details

### 2. GitHub Repository Import

**API Endpoint**:
- `POST /api/apps/import` — Import an external GitHub repository

```bash
curl -X POST http://localhost:8000/api/apps/import \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/user/my-project", "create_project": true}'
```

**Agent Tool**:
- `import_github_repo(url)` — Import via chat conversation

### 3. Template-Aware App Creation

**Extended Flow**:
1. User selects a template (via UI or chat)
2. `create_app()` accepts `template_id` and renders template files
3. Pipeline auto-configured based on template category + difficulty
4. Architect agent inserted when template has IaC target

**Agent Tool**:
- `build_app(app_name, template_id, description, context_variables)` — Full orchestration

### 4. Build Progress Monitoring

**WebSocket Events** (on existing `/api/ws/{project_id}` connection):
- `build_progress` — Phase transitions with percentage
- `build_milestone` — Key milestones (scaffolded, working, review, complete)
- `build_complete` — Final summary with links
- `build_failed` — Error reporting

**Chat Integration**: Progress messages auto-injected into the active chat session.

**Signal Notifications**: Milestone events delivered via existing Signal integration.

### 5. Iteration on Existing Apps

**Agent Tool**:
- `iterate_on_app(app_name, change_description)` — Creates issue + launches pipeline

**Chat Flow**: "Add dark mode to my dashboard app" → issue created → pipeline launched

## Testing

### Backend Unit Tests

```bash
cd solune/backend

# Template rendering and path-traversal validation
.venv/bin/python -m pytest tests/unit/test_app_templates.py -v

# Pipeline auto-configuration
.venv/bin/python -m pytest tests/unit/test_pipeline_config.py -v

# Import URL validation
.venv/bin/python -m pytest tests/unit/test_import_validation.py -v
```

### Frontend Tests

```bash
cd solune/frontend

# Template browser component
npx vitest run src/components/apps/TemplateBrowser.test.tsx

# Build progress component
npx vitest run src/components/pipeline/BuildProgress.test.tsx
```

### Integration Testing

```bash
# Full chat → build flow (requires running backend)
cd solune/backend
.venv/bin/python -m pytest tests/integration/test_build_flow.py -v
```

### Manual Verification

1. **Template browsing**: Navigate to Apps page → Template Browser tab → Verify 4 templates shown → Filter by category
2. **Conversational build**: Type "Build me a dashboard app" in chat → Answer 2–3 questions → Confirm plan → Watch progress
3. **Import flow**: Apps page → Import tab → Enter GitHub URL → Verify validation → Import
4. **Progress monitoring**: During a build, check chat for progress messages, frontend for stepper panel
5. **Iteration**: With an existing app, type "Add user authentication to my dashboard" → Verify issue + pipeline created

## Key Files

| Area | File | Action |
|------|------|--------|
| Template model | `src/models/app_template.py` | NEW |
| Build progress model | `src/models/build_progress.py` | NEW |
| App model | `src/models/app.py` | EXTEND (add template_id) |
| Template registry | `src/services/app_templates/registry.py` | NEW |
| Template renderer | `src/services/app_templates/renderer.py` | NEW |
| Pipeline config | `src/services/pipelines/pipeline_config.py` | NEW |
| App service | `src/services/app_service.py` | EXTEND |
| Agent tools | `src/services/agent_tools.py` | EXTEND (6 new tools) |
| Agent instructions | `src/prompts/agent_instructions.py` | EXTEND |
| Apps API | `src/api/apps.py` | EXTEND (import endpoint) |
| Signal delivery | `src/services/signal_delivery.py` | EXTEND (milestones) |
| DB migration | `src/migrations/027_app_template_fields.sql` | NEW |
| Template browser | `frontend/src/components/apps/TemplateBrowser.tsx` | NEW |
| Import dialog | `frontend/src/components/apps/ImportAppDialog.tsx` | NEW |
| Build progress panel | `frontend/src/components/pipeline/BuildProgress.tsx` | NEW |
| Build progress card | `frontend/src/components/apps/BuildProgressCard.tsx` | NEW |
| Build progress hook | `frontend/src/hooks/useBuildProgress.ts` | NEW |
