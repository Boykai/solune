# Quickstart: Full-Stack Plan Pipeline Enhancement

**Feature**: 016-plan-pipeline-enhancement | **Date**: 2026-04-04

## Prerequisites

- Python 3.11+ with `uv` package manager
- Node.js 18+ with npm
- SQLite 3.35+ (for `RETURNING` clause support)
- Docker & Docker Compose (for full-stack local development)

## Local Development Setup

### 1. Backend

```bash
cd solune/backend

# Install dependencies
uv sync

# Run migrations (applies 040 + 041 automatically)
uv run python -m src.migrations

# Run backend server
uv run uvicorn src.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd solune/frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

### 3. Full Stack (Docker)

```bash
docker-compose up --build
```

## Verification Commands

### Backend Tests

```bash
cd solune/backend

# Unit tests for plan store (versioning, step CRUD, DAG validation)
uv run pytest -q tests/unit/test_plan_store.py tests/unit/test_api_chat.py

# Full coverage check
uv run pytest tests/unit/ --cov=src --cov-report=term-missing --cov-fail-under=75
```

### Frontend Tests

```bash
cd solune/frontend

# Specific component and hook tests
npm test -- --run src/components/chat/PlanPreview.test.tsx src/hooks/usePlan.test.tsx src/components/chat/PlanDependencyGraph.test.tsx

# Lint + type check
npm run lint -- --quiet && npx tsc --noEmit

# Coverage
npm run test:coverage
```

## Feature Walkthrough

### Phase 1: Iterative Refinement Loop

1. **Start a plan session**: Navigate to `/plan` and describe your feature
2. **Review the generated plan**: Plan appears in `PlanPreview` with steps
3. **Request changes with per-step feedback**: Click "Request Changes" → inline comment inputs appear per step → submit feedback
4. **Observe version diff**: After refinement, changed steps show yellow border, new steps show green border
5. **View version history**: Click "History" to see all versions with step snapshots

### Phase 2: Step CRUD + Dependency Graph

6. **Add a step**: Click "Add Step" button below the step list
7. **Edit inline**: Click any step title or description to edit inline
8. **Delete a step**: Click delete icon → confirmation dialog shows dependent steps
9. **Drag to reorder**: Drag step handles to reorder → positions update via API
10. **View dependency graph**: Toggle graph view → SVG shows topological layout with clickable nodes
11. **Selective approval**: Check individual steps → "Approve Selected" creates issues for checked steps only

### Phase 3: Polish + Export + Board Sync

12. **Rich thinking events**: During plan generation, see breadcrumbs for tools used and context gathered
13. **Export**: Click "Export as Markdown" → downloads `.md` file; "Copy to clipboard" → copies Markdown text
14. **Board sync**: After approval, step statuses sync from GitHub issues via polling
15. **Progress bar**: "3/7 issues completed" bar displays at top of plan view

## New API Endpoints Summary

| Method | Path | Description | Phase |
|--------|------|-------------|-------|
| GET | `/chat/plans/{plan_id}/history` | Get version history | 1 |
| POST | `/chat/plans/{plan_id}/steps/{step_id}/feedback` | Submit step feedback | 1 |
| POST | `/chat/plans/{plan_id}/steps` | Add a step | 2 |
| PUT | `/chat/plans/{plan_id}/steps/{step_id}` | Update a step | 2 |
| DELETE | `/chat/plans/{plan_id}/steps/{step_id}` | Delete a step (cascade) | 2 |
| POST | `/chat/plans/{plan_id}/steps/reorder` | Bulk reorder steps | 2 |
| GET | `/chat/plans/{plan_id}/export?format=markdown` | Export plan | 3 |
| POST | `/chat/plans/{plan_id}/approve` | Approve (extended with step_ids) | 2 |

## New Migrations

| File | Description |
|------|-------------|
| `040_plan_versioning.sql` | Adds `version` column to `chat_plans`; creates `chat_plan_versions` table |
| `041_plan_step_status.sql` | Adds `issue_status` column to `chat_plan_steps` |

## Key Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Snapshot versioning (not event sourcing) | O(1) reads; ≤50 versions per plan |
| Transient feedback (not persisted) | Ephemeral by nature; avoids table + cleanup |
| Custom SVG graph (no new deps) | ≤15 nodes; avoids D3/dagre bundle weight |
| Reuse @dnd-kit patterns | Already installed; proven in ExecutionGroupCard |
| Polling for board sync (not webhooks) | Simpler for SQLite; no GitHub App setup |
| Extend existing `/approve` | Backward-compatible; unified approval flow |
