# Implementation Plan: Auto-generate Labels for GitHub Parent Issues

**Branch**: `001-auto-generate-labels` | **Date**: 2026-03-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-auto-generate-labels/spec.md`

## Summary

Three code paths create parent GitHub issues, but only the recommendation confirmation path auto-generates content-based labels. The pipeline launch path hardcodes `["ai-generated"]` + `pipeline:<name>`, and the task creation path applies zero labels. This plan introduces a centralized `LabelClassificationService` that all three paths share. The service accepts an issue title and optional description, calls the existing AI completion provider with a structured prompt referencing the predefined label taxonomy from `constants.py`, validates and deduplicates the response, and returns a guaranteed-valid label set (always including `"ai-generated"` + exactly one type label). Each issue creation path is then updated to call this shared service, with graceful fallback to current behavior on failure.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, Pydantic, agent-framework-* (Microsoft Agent Framework runtime/orchestration packages), GitHub Copilot SDK
**Storage**: SQLite via aiosqlite (no schema changes needed for this feature)
**Testing**: pytest + pytest-asyncio (backend), Vitest (frontend — no frontend changes expected)
**Target Platform**: Linux server (Docker)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: Label classification adds ≤ 3 seconds latency to issue creation (SC-006)
**Constraints**: Classification failure must never block issue creation (SC-003); all labels must come from predefined taxonomy in `constants.py` (FR-002)
**Scale/Scope**: 3 issue creation paths to update; 1 new service module; ~200-300 lines of new code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | `spec.md` exists with 4 prioritized user stories (P1-P3), Given-When-Then scenarios, edge cases, and clear scope boundaries |
| II. Template-Driven | ✅ PASS | All artifacts follow canonical templates from `.specify/templates/` |
| III. Agent-Orchestrated | ✅ PASS | Single-responsibility: this plan phase produces design artifacts; implementation deferred to `/speckit.tasks` + `/speckit.implement` |
| IV. Test Optionality | ✅ PASS | Tests not mandated by spec; will be included if requested during implementation phase. Unit tests recommended for the classifier service given its centrality |
| V. Simplicity and DRY | ✅ PASS | Core approach eliminates label duplication across 3 paths via a single shared service. No premature abstractions — the service is a single async function, not a framework |

**Gate Result**: ALL PASS — proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-auto-generate-labels/
├── plan.md              # This file
├── research.md          # Phase 0: Research findings
├── data-model.md        # Phase 1: Entity and data model
├── quickstart.md        # Phase 1: Developer quickstart guide
├── contracts/           # Phase 1: API contracts
│   └── label-classification.yaml  # Label classifier interface contract
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── api/
│   │   ├── pipelines.py          # MODIFY: Call label classifier before create_issue
│   │   ├── tasks.py              # MODIFY: Call label classifier before create_issue
│   │   └── workflow.py           # NO CHANGE: Already uses _build_labels via orchestrator
│   ├── constants.py              # EXISTING: LABELS taxonomy (single source of truth)
│   ├── models/
│   │   └── recommendation.py     # EXISTING: IssueLabel, IssueMetadata (no changes needed)
│   ├── prompts/
│   │   └── label_classification.py  # NEW: Prompt template for label classification
│   └── services/
│       ├── label_classifier.py   # NEW: LabelClassificationService
│       ├── agent_tools.py        # MODIFY: Add optional labels param to create_project_issue
│       └── workflow_orchestrator/
│           └── orchestrator.py   # EXISTING: _build_labels (reference implementation)
└── tests/
    └── unit/
        └── test_label_classifier.py  # NEW: Unit tests for classification service
```

**Structure Decision**: Web application structure (Option 2). All changes are backend-only within `solune/backend/`. The new `label_classifier.py` service module and `label_classification.py` prompt template are the only new files in `src/`. The feature adds no new dependencies, using the existing AI completion provider infrastructure.

## Constitution Re-Check (Post-Design)

*Re-evaluation after Phase 1 design artifacts are complete.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Design artifacts (data-model, contracts, quickstart) all trace back to spec.md requirements |
| II. Template-Driven | ✅ PASS | All generated artifacts follow canonical templates |
| III. Agent-Orchestrated | ✅ PASS | Plan phase complete; handoff to `/speckit.tasks` for task decomposition |
| IV. Test Optionality | ✅ PASS | Test file (`test_label_classifier.py`) listed as recommended, not mandated |
| V. Simplicity and DRY | ✅ PASS | Single `classify_labels()` function shared by all 3 paths; no repository pattern, no cache layer, no event system — just a function |

**Gate Result**: ALL PASS — ready for Phase 2 (`/speckit.tasks`).

## Complexity Tracking

> No constitution violations — this section is intentionally empty.
