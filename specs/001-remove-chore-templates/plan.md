# Implementation Plan: Remove Issue Templates, Use DB + Parent Issue Intake Flow

**Branch**: `001-remove-chore-templates` | **Date**: 2026-04-13 | **Spec**: GitHub Issue #1716
**Input**: Parent issue Boykai/solune#1716 — Chores — Remove Issue Templates, Use DB + Parent Issue Intake Flow

## Summary

Remove all ISSUE_TEMPLATE integration from Chores. Rename `template_content` → `description` and drop `template_path` in the Chore model and database. Rewrite `trigger_chore()` to delegate to `execute_pipeline_launch()` with `extra_labels=["chore"]` and `issue_title_override=chore.name`, getting transcript detection, AI label classification, sub-issue creation, and pipeline orchestration for free. Simplify the frontend to remove template picker, PR creation buttons, and SHA conflict detection. Move `is_sparse_input()` to a utils module. Strip YAML front matter from preset files.

## Technical Context

**Language/Version**: Python 3.12+ (backend); TypeScript 5.x / React 18 (frontend)
**Primary Dependencies**: FastAPI, Pydantic, aiosqlite (backend); React, TanStack Query, Tailwind CSS (frontend)
**Storage**: SQLite via aiosqlite — migration `045_chore_description.sql` renames column + drops column + strips YAML
**Testing**: `pytest` (backend: `uv run pytest tests/unit/`); Vitest (frontend: `npm run test`); `pyright` type checking; `ruff` linting
**Target Platform**: Linux server (backend); browser SPA (frontend)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: N/A — refactoring-only; fewer GitHub API calls per chore creation (removes PR/file operations)
**Constraints**: Zero behavioral regressions for trigger → pipeline flow; existing tests must pass; 1-open-instance constraint preserved
**Scale/Scope**: ~1 model change, ~1 migration, ~3 backend service files modified/deleted, ~1 API file simplified, ~6 frontend files modified, ~3 preset files stripped

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Specification-First Development**: PASS — The parent issue (#1716) provides a comprehensive specification with phased requirements, explicit scope boundaries, key decisions, and risks. This plan follows the issue as the authoritative spec. A structured spec.md has been generated in `specs/001-remove-chore-templates/spec.md` with 6 user stories, 24 functional requirements, and 10 success criteria.
- **II. Template-Driven Workflow**: PASS — This plan and all Phase 0/1 artifacts reside in `specs/001-remove-chore-templates/` using the canonical Speckit artifact set (plan.md, research.md, data-model.md, contracts/, quickstart.md).
- **III. Agent-Orchestrated Execution**: PASS — The plan decomposes into 5 independent/dependent phases suitable for single-responsibility agent execution. Each phase has clear inputs, outputs, and verification criteria.
- **IV. Test Optionality with Clarity**: PASS — No new tests are mandated. Existing test suites serve as regression gates. Tests for deprecated template builder functions are updated to test the relocated `is_sparse_input()` in `utils.py`. Tests that reference `template_content` are updated to use `description`.
- **V. Simplicity and DRY**: PASS — The plan removes complexity (~278 lines of manual issue creation in `trigger_chore()` replaced with a single `execute_pipeline_launch()` call). Template builder functions are deleted rather than deprecated. `is_sparse_input()` is preserved in a utils module rather than duplicated.

**Post-Phase-1 Re-check**: PASS — No constitution violations introduced by the design. The delegation pattern (chore → `execute_pipeline_launch()`) reduces duplication. The `UserSession` construction approach is simple and direct (research.md R1 confirms no service-layer extraction needed).

## Project Structure

### Documentation (this feature)

```text
specs/001-remove-chore-templates/
├── plan.md              # This file
├── research.md          # Phase 0 output — migration/coupling research
├── data-model.md        # Phase 1 output — entity and schema changes
├── quickstart.md        # Phase 1 output — execution guide
├── contracts/           # Phase 1 output — updated OpenAPI contract
│   └── chores-api.yaml
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── api/
│   │   ├── chores.py                 # Phase 2: remove template endpoints, simplify create
│   │   └── pipelines.py              # Phase 2: add extra_labels + issue_title_override params
│   ├── models/
│   │   └── chores.py                 # Phase 1: rename template_content → description, drop template_path
│   ├── migrations/
│   │   └── 045_chore_description.sql # Phase 1: schema migration
│   └── services/
│       └── chores/
│           ├── service.py            # Phase 2: rewrite trigger_chore(), gut inline_update, simplify create
│           ├── template_builder.py   # Phase 2: DELETE (is_sparse_input moved to utils.py)
│           ├── utils.py              # Phase 2: NEW — relocated is_sparse_input()
│           ├── chat.py               # Phase 2: update import from template_builder → utils
│           └── presets/
│               ├── security-review.md    # Phase 4: strip YAML front matter
│               ├── performance-review.md # Phase 4: strip YAML front matter
│               └── bug-basher.md         # Phase 4: strip YAML front matter
├── tests/
│   └── unit/
│       ├── test_chores_service.py        # Phase 5: update imports, field names
│       └── test_chores_template_builder.py # Phase 5: update for utils.py relocation

solune/frontend/
└── src/
    ├── types/
    │   └── index.ts                      # Phase 3: update Chore, ChoreCreate, remove ChoreTemplate, etc.
    ├── services/
    │   └── api.ts                        # Phase 3: remove template/PR API methods
    ├── hooks/
    │   └── useChores.ts                  # Phase 3: remove useChoreTemplates, simplify hooks
    └── components/
        └── chores/
            ├── AddChoreModal.tsx          # Phase 3: remove template picker, rename field label
            ├── ChoreCard.tsx              # Phase 3: remove "Save & Create PR", use description
            ├── ChoreInlineEditor.tsx      # Phase 3: remove SHA references
            └── ChoresPanel.tsx            # Phase 3: remove template membership checks
```

**Structure Decision**: Existing web application monorepo structure (`solune/backend/`, `solune/frontend/`). This feature modifies and deletes files in-place; one new file introduced (`services/chores/utils.py`).

## Phase Execution Plan

### Phase 1 — Backend Model & DB (Foundation, no dependencies)

**Goal**: Rename `template_content` → `description`, drop `template_path` from model and DB.

| Step | Action | File | Details |
|------|--------|------|---------|
| 1.1 | Rename field in Pydantic model | `src/models/chores.py` L35-36 | `template_path` → remove, `template_content` → `description` |
| 1.2 | Update ChoreCreate model | `src/models/chores.py` L56-60 | `template_content` → `description` |
| 1.3 | Create DB migration | `src/migrations/045_chore_description.sql` | `RENAME COLUMN`, `DROP COLUMN`, strip YAML front matter |
| 1.4 | Update all SQL queries in service.py | `src/services/chores/service.py` | Replace `template_content` → `description`, remove `template_path` references in INSERT/SELECT/UPDATE |

**Verification**: `uv run pyright src/models/chores.py`; migration file syntax check.

### Phase 2 — Backend Services (Depends on Phase 1)

**Goal**: Rewrite trigger_chore() to use execute_pipeline_launch(), remove template infrastructure.

| Step | Action | File | Details |
|------|--------|------|---------|
| 2.1 | Add `extra_labels` + `issue_title_override` params | `src/api/pipelines.py` L293 | New optional params; title override > transcript > AI; extra labels appended |
| 2.2 | Move `is_sparse_input()` to utils | `src/services/chores/utils.py` (NEW) | Pure function move from `template_builder.py` L56-93 |
| 2.3 | Rewrite `trigger_chore()` | `src/services/chores/service.py` L462 | Replace ~278 lines with `execute_pipeline_launch()` call; keep 1-open-instance + CAS |
| 2.4 | Simplify `inline_update_chore()` | `src/services/chores/service.py` L841 | Remove SHA check, PR creation — pure DB update |
| 2.5 | Simplify `create_chore_with_auto_merge()` → `create_chore()` | `src/services/chores/service.py` L967 | Remove `build_template()`, `derive_template_path()` calls |
| 2.6 | Delete `template_builder.py` | `src/services/chores/template_builder.py` | All functions removed; `is_sparse_input` already in utils.py |
| 2.7 | Update `chat.py` import | `src/services/chores/chat.py` | `from .template_builder import is_sparse_input` → `from .utils import is_sparse_input` |
| 2.8 | Remove template API endpoints | `src/api/chores.py` | Remove `GET /templates` (L109-165), `PUT /inline-update` (L505-562), `POST /create-with-merge` (L568-601); simplify `POST /` create |
| 2.9 | Update preset definitions | `src/services/chores/service.py` L22-53 | Remove `template_path` from `_CHORE_PRESET_DEFINITIONS`; rename `template_file` → `description_file` |
| 2.10 | Update `seed_presets()` | `src/services/chores/service.py` L108-180 | Use `description` column in INSERT; remove `template_path` |
| 2.11 | Remove `_strip_front_matter()` from service | `src/services/chores/service.py` L80 | Keep only in migration script |

**Verification**: `uv run ruff check src/`; `uv run pyright src/`; `uv run pytest tests/unit/ -q`.

### Phase 3 — Frontend (Depends on Phase 1 + Phase 2 API changes)

**Goal**: Remove template UI, PR flow, SHA tracking from frontend.

| Step | Action | File | Details |
|------|--------|------|---------|
| 3.1 | Update types | `src/types/index.ts` | Remove `ChoreTemplate`; update `Chore`, `ChoreCreate`, `ChoreInlineUpdate`, `ChoreEditState`, simplify response types |
| 3.2 | Update API client | `src/services/api.ts` | Remove `listTemplates()` (L1181), `inlineUpdate()` (L1255), `createWithAutoMerge()` (L1269); update payloads |
| 3.3 | Update hooks | `src/hooks/useChores.ts` | Remove `useChoreTemplates()` (L77), `useCreateChoreWithAutoMerge()` (L435); simplify `useInlineUpdateChore()` (L377) |
| 3.4 | Simplify AddChoreModal | `src/components/chores/AddChoreModal.tsx` | Remove template picker (L76-78), `initialTemplate` prop, rename label |
| 3.5 | Update ChoreCard | `src/components/chores/ChoreCard.tsx` | Remove "Save & Create PR"; use `description` field |
| 3.6 | Update ChoreInlineEditor | `src/components/chores/ChoreInlineEditor.tsx` | Remove SHA-related references |
| 3.7 | Update ChoresPanel | `src/components/chores/ChoresPanel.tsx` | Remove template membership checks, `uncreatedTemplates` |

**Verification**: `npm run lint`; `npm run type-check`; `npm run test`; `npm run build`.

### Phase 4 — Cleanup (Depends on Phase 2)

**Goal**: Strip YAML front matter from preset files, update MCP tools.

| Step | Action | File | Details |
|------|--------|------|---------|
| 4.1 | Strip YAML front matter | `presets/security-review.md` | Remove `---...\n---` header block |
| 4.2 | Strip YAML front matter | `presets/performance-review.md` | Remove `---...\n---` header block |
| 4.3 | Strip YAML front matter | `presets/bug-basher.md` | Remove `---...\n---` header block |
| 4.4 | Update MCP tools if needed | `src/services/mcp_server/tools/chores.py` | Replace `template_content` → `description` references |

**Verification**: `uv run pytest tests/unit/ -q`.

### Phase 5 — Testing & Verification (Depends on all phases)

| Step | Action | File | Details |
|------|--------|------|---------|
| 5.1 | Update test imports | `tests/unit/test_chores_template_builder.py` | `from ...template_builder import is_sparse_input` → `from ...utils import is_sparse_input` |
| 5.2 | Update test field names | `tests/unit/test_chores_service.py` | `template_content` → `description`; remove template-related test cases |
| 5.3 | Remove template builder tests | `tests/unit/test_chores_template_builder.py` | Remove `build_template`, `derive_template_path`, `commit_template_to_repo` tests; keep `is_sparse_input` tests |
| 5.4 | Full backend validation | All backend | `ruff check`, `ruff format --check`, `pyright`, `pytest` |
| 5.5 | Full frontend validation | All frontend | `npm run lint`, `npm run type-check`, `npm run test`, `npm run build` |
| 5.6 | Zero-reference grep | Entire codebase | No `template_content`, `template_path`, or `ISSUE_TEMPLATE/chore` references (except migration) |

## Verification Matrix

| Check | Command | After Phase |
|-------|---------|-------------|
| Backend lint | `cd solune/backend && uv run ruff check src/ tests/` | 2, 4, 5 |
| Backend types | `cd solune/backend && uv run pyright src/` | 1, 2, 4 |
| Backend tests | `cd solune/backend && uv run pytest tests/unit/ -q` | 2, 4, 5 |
| Frontend lint | `cd solune/frontend && npm run lint` | 3, 5 |
| Frontend types | `cd solune/frontend && npm run type-check` | 3, 5 |
| Frontend tests | `cd solune/frontend && npm run test` | 3, 5 |
| Frontend build | `cd solune/frontend && npm run build` | 3, 5 |
| Dead reference grep | `grep -rn "template_content\|template_path\|ISSUE_TEMPLATE/chore" solune/backend/src/ solune/frontend/src/` | 5 |

## Decisions

| Decision | Rationale |
|----------|-----------|
| **Clean break**: `template_path` and PR columns removed, not soft-deprecated | Simpler migration; no dead fields in model |
| **Full delegation**: `trigger_chore()` → `execute_pipeline_launch()` | Eliminates ~278 lines of duplicated logic; chores get AI labels, transcript detection, sub-issues for free |
| **Title override**: Chore name used as issue title (skip AI derivation) | Chore names are descriptive enough; AI title derivation is for raw user input |
| **`is_sparse_input()` preserved**: Moved to `utils.py` | Still used by chat flow for sparse input detection |
| **UserSession construction**: Build from available fields | `execute_pipeline_launch()` is not HTTP-coupled; accepts plain Pydantic model (R1) |
| **SQLite native column ops**: `RENAME COLUMN` + `DROP COLUMN` | Python 3.12 bundles SQLite 3.40+ which supports both operations (R3) |
| **Preset files stripped in-place**: Keep .md files, remove YAML header | Files are more maintainable than inline strings; .md extension correct for markdown |

## Complexity Tracking

> No constitution violations found. No complexity justifications required.

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `execute_pipeline_launch()` coupling to API-layer imports | `trigger_chore()` would need API-layer imports | Research R1 confirms function is standalone; construct `UserSession` from available fields |
| Migration YAML stripping misses edge cases | Some chores retain front matter | Use proven `_strip_front_matter()` regex; validate with test data |
| Preset content quality after stripping | Presets lose GitHub Issue Template metadata | Metadata was only for GitHub UI; not needed for DB-stored descriptions |
| Frontend type changes break at runtime | API returns `description` but frontend expects `template_content` | Deploy backend + frontend atomically; type-check catches mismatches |
