# Implementation Plan: Auto-Generated Project Labels & Fields on Pipeline Launch

**Branch**: `730-auto-generated-labels-fields` | **Date**: 2026-04-04 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/730-auto-generated-labels-fields/spec.md`

## Summary

When a GitHub parent issue is created via pipeline launch, project fields (Priority, Size, Estimate, Start/Target date) remain empty because `execute_pipeline_launch()` never calls `set_issue_metadata()`. This plan adds a lightweight heuristic estimator (`pipeline_estimate.py`) that derives metadata from agent count, integrates it into the launch flow, and extends the AI label classifier to optionally detect urgency for priority override. Existing agent/stalled label lifecycles are verified, not changed.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, Pydantic, aiohttp (GitHub GraphQL), azure-ai-projects (AI completion)  
**Storage**: SQLite via aiosqlite (existing — no schema changes needed for this feature)  
**Testing**: pytest with pytest-asyncio, unittest.mock (AsyncMock pattern)  
**Target Platform**: Linux server (Docker container, Azure Container Apps)  
**Project Type**: Web application (backend + frontend monorepo)  
**Performance Goals**: Pipeline launch must complete within existing SLA; metadata setting is non-blocking (fire-and-forget with logging)  
**Constraints**: Metadata failures must not abort pipeline launch; AI classification timeout remains 5s; no new external dependencies  
**Scale/Scope**: Affects all pipeline launches (~50-100/day); single new module + 2 modified files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | spec.md with prioritized user stories (P1-P3), acceptance criteria, GWT scenarios |
| II. Template-Driven | ✅ PASS | All artifacts follow canonical templates |
| III. Agent-Orchestrated | ✅ PASS | Single-agent changes; no new agent creation |
| IV. Test Optionality | ✅ PASS | Tests included per specification (unit tests for heuristic, classification) |
| V. Simplicity & DRY | ✅ PASS | Single new module (pipeline_estimate.py), reuses existing IssueMetadata model and set_issue_metadata() |

**Gate Result**: ✅ ALL PASS — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/730-auto-generated-labels-fields/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── pipeline-estimate-api.md
└── tasks.md             # Phase 2 output (NOT created by speckit.plan)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── models/
│   │   └── recommendation.py          # IssueMetadata, IssuePriority, IssueSize (EXISTING)
│   ├── services/
│   │   ├── pipeline_estimate.py       # NEW — Heuristic estimate from agent count
│   │   ├── label_classifier.py        # MODIFIED — Parse optional priority from AI
│   │   └── github_projects/
│   │       └── projects.py            # EXISTING — set_issue_metadata() (no changes)
│   ├── api/
│   │   └── pipelines.py              # MODIFIED — Call set_issue_metadata() after project add
│   └── prompts/
│       └── label_classification.py    # MODIFIED — Add optional priority to prompt
└── tests/
    └── unit/
        ├── test_pipeline_estimate.py  # NEW — Heuristic tests
        ├── test_label_classifier.py   # MODIFIED — Priority parsing tests
        └── test_api_pipelines.py      # MODIFIED — Metadata integration tests
```

**Structure Decision**: Web application structure — all changes in `solune/backend/` following existing module conventions. No frontend changes needed (project fields render automatically from GitHub Projects API).

## Constitution Check — Post-Design Re-evaluation

*Re-evaluated after Phase 1 design completion.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | spec.md complete with P1-P3 user stories, acceptance criteria, and independent test criteria |
| II. Template-Driven | ✅ PASS | All 5 artifacts (plan.md, research.md, data-model.md, quickstart.md, contracts/) generated per template |
| III. Agent-Orchestrated | ✅ PASS | No new agents; changes integrate into existing pipeline launch flow |
| IV. Test Optionality | ✅ PASS | Tests specified for new pipeline_estimate.py module and classifier extension |
| V. Simplicity & DRY | ✅ PASS | Reuses IssueMetadata model, set_issue_metadata(), existing classify_labels() pattern. One new module (pipeline_estimate.py), one new dataclass (ClassificationResult). No new dependencies. |

**Post-Design Gate Result**: ✅ ALL PASS — ready for Phase 2 (tasks generation via speckit.tasks).

## Complexity Tracking

> No violations detected — no entries needed.
