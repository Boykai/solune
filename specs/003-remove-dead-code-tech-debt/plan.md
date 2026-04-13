# Implementation Plan: Remove Dead Code & Tech Debt

**Branch**: `copilot/remove-dead-code-tech-debt` | **Date**: 2026-04-13 | **Spec**: GitHub Issue #1630
**Input**: Parent issue Boykai/solune#1630 — Remove Dead Code & Tech Debt

## Summary

Remove 5 deprecated backend modules (marked for v0.3.0 removal) that are still lazily imported in active code, migrate their consumers to the current `ChatAgentService` and `agent_provider` abstractions, guard unstructured frontend console logging behind `import.meta.env.DEV`, evaluate a stale pipeline field, convert singleton TODO markers to a tracked issue, and consolidate misplaced root-level spec files into the mono-spec directory structure.

## Technical Context

**Language/Version**: Python 3.12+ (backend); TypeScript/React (frontend)
**Primary Dependencies**: FastAPI, Pydantic, Microsoft Agent Framework (`ChatAgentService`), Vite (frontend build)
**Storage**: N/A — no schema or persistence changes; `pipeline_metadata` field evaluation may defer removal pending data-migration analysis
**Testing**: `pytest` (backend: `uv run pytest tests/`); Vitest (frontend: `npm run test`); `pyright` type checking; `ruff` linting
**Target Platform**: Linux server (backend); browser SPA (frontend)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: N/A — cleanup-only; no new runtime paths
**Constraints**: Zero behavioral regressions; all existing tests must pass; no new type errors; OpenAPI schema unaffected
**Scale/Scope**: ~5 deprecated modules removed, ~12 consumer files migrated, ~3 frontend files guarded, ~6 root-level files relocated

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Specification-First Development**: PASS — The parent issue (#1630) provides a structured specification with phased requirements, explicit scope boundaries, exclusion list, and verification criteria. This plan follows the issue as the authoritative spec.
- **II. Template-Driven Workflow**: PASS — This plan and all Phase 0/1 artifacts reside in `specs/003-remove-dead-code-tech-debt/` using the canonical Speckit artifact set.
- **III. Agent-Orchestrated Execution**: PASS — The plan decomposes into six independent/dependent phases suitable for single-responsibility agent execution. Each phase has clear inputs, outputs, and handoff criteria.
- **IV. Test Optionality with Clarity**: PASS — No new tests are mandated. Existing test suites serve as regression gates. Tests for deprecated modules (`test_ai_agent.py`, `test_completion_providers.py`, `test_issue_generation_prompt.py`, `test_task_generation_prompt.py`, `test_transcript_analysis_prompt.py`) are removed alongside their subjects. Test fixtures (`mock_ai_agent_service`) are removed from `conftest.py`.
- **V. Simplicity and DRY**: PASS — The plan removes complexity (deprecated abstractions) rather than adding it. Migration paths use existing `ChatAgentService` and `agent_provider` patterns already established in the codebase.

**Post-Phase-1 Re-check**: PASS — No constitution violations introduced by the design. The phased approach maintains simplicity and avoids premature abstraction. The deferred singleton DI refactor (TODO-018) is correctly scoped out per the Simplicity principle.

## Project Structure

### Documentation (this feature)

```text
specs/003-remove-dead-code-tech-debt/
├── plan.md              # This file
├── research.md          # Phase 0 output — migration path research
├── data-model.md        # Phase 1 output — affected modules and dependency map
├── quickstart.md        # Phase 1 output — execution guide for each phase
├── contracts/           # Phase 1 output — N/A (OpenAPI schema unaffected)
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── api/
│   │   ├── chat.py                      # Phase 2: migrate get_ai_agent_service → ChatAgentService
│   │   └── pipelines.py                 # Phase 2: migrate analyze_transcript() usage
│   ├── prompts/
│   │   ├── issue_generation.py          # Phase 1: DELETE
│   │   ├── task_generation.py           # Phase 1: DELETE
│   │   └── transcript_analysis.py       # Phase 1: DELETE
│   └── services/
│       ├── ai_agent.py                  # Phase 2: DELETE (after consumer migration)
│       ├── completion_providers.py       # Phase 3: DELETE (after consumer migration)
│       ├── chat_agent.py                # Migration target (ChatAgentService)
│       ├── agent_provider.py            # Phase 3: relocate get_copilot_client_pool
│       ├── plan_agent_provider.py       # Phase 3: update lazy import
│       ├── model_fetcher.py             # Phase 3: update direct import
│       ├── label_classifier.py          # Phase 3: update lazy imports
│       ├── app_service.py               # Phase 2: replace lazy import
│       ├── agent_creator.py             # Phase 2: migrate generate_agent_config()
│       ├── signal_chat.py               # Phase 2: replace existence check
│       ├── agents/service.py            # Phase 2: migrate _call_completion() usage
│       ├── chores/chat.py               # Phase 2: migrate _call_completion() usage
│       ├── workflow_orchestrator/
│       │   └── orchestrator.py          # Phase 2: migrate type + factory
│       └── copilot_polling/
│           └── auto_merge.py            # Phase 4: evaluate pipeline_metadata
├── tests/
│   ├── conftest.py                      # Phase 2: remove AIAgentService import + fixture
│   └── unit/
│       ├── test_ai_agent.py             # Phase 2: DELETE
│       ├── test_completion_providers.py  # Phase 3: DELETE
│       ├── test_issue_generation_prompt.py   # Phase 1: DELETE
│       ├── test_task_generation_prompt.py    # Phase 1: DELETE
│       └── test_transcript_analysis_prompt.py # Phase 1: DELETE

solune/frontend/
└── src/
    ├── services/api.ts                  # Phase 5: wrap console.debug in DEV guard
    └── hooks/usePipelineConfig.ts       # Phase 5: wrap console.warn in DEV guard
```

**Structure Decision**: Existing web application monorepo structure (`solune/backend/`, `solune/frontend/`). This feature modifies and deletes files in-place; no new directories or modules are introduced.

## Phase Execution Plan

### Phase 1 — Remove Deprecated Prompt Modules (parallel with Phase 2)

**Goal**: Delete 3 prompt files only imported by the already-deprecated `ai_agent.py`.

| Step | Action | File |
|------|--------|------|
| 1.1 | Delete deprecated prompt module | `src/prompts/issue_generation.py` |
| 1.2 | Delete deprecated prompt module | `src/prompts/task_generation.py` |
| 1.3 | Delete deprecated prompt module | `src/prompts/transcript_analysis.py` |
| 1.4 | Verify no `prompts/__init__.py` re-exports (confirmed: none exist) | `src/prompts/__init__.py` |
| 1.5 | Delete test for issue_generation prompt | `tests/unit/test_issue_generation_prompt.py` |
| 1.6 | Delete test for task_generation prompt | `tests/unit/test_task_generation_prompt.py` |
| 1.7 | Delete test for transcript_analysis prompt | `tests/unit/test_transcript_analysis_prompt.py` |

**Verification**: `uv run pytest tests/ --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency` — existing tests pass (prompt module tests removed alongside modules).

### Phase 2 — Remove AIAgentService (depends on Phase 1)

**Goal**: Migrate all consumers of the deprecated `AIAgentService` / `get_ai_agent_service()` to `ChatAgentService` or inline equivalents, then delete `ai_agent.py`.

| Step | Action | File | Details |
|------|--------|------|---------|
| 2.1 | Replace lazy import | `src/api/chat.py` (L46, L50) | Replace `get_ai_agent_service` with `get_chat_agent_service`; adapt `identify_target_task()` call |
| 2.2 | Replace lazy import | `src/services/app_service.py` (L163) | Replace lazy `get_ai_agent_service` import |
| 2.3 | Migrate `_call_completion()` calls | `src/services/chores/chat.py` (L158, L193) | Replace with `ChatAgentService.run()` or direct agent-provider completion |
| 2.4 | Migrate `_call_completion()` calls | `src/services/agents/service.py` (L1373, L1507, L1630, L1691) | Replace 4 lazy imports with `ChatAgentService` equivalents |
| 2.5 | Migrate `analyze_transcript()` | `src/api/pipelines.py` (L333) | Move logic into `ChatAgentService` or a standalone utility |
| 2.6 | Migrate type + factory | `src/services/workflow_orchestrator/orchestrator.py` (L52, L3060) | Replace `AIAgentService` type hint and `get_ai_agent_service()` call |
| 2.7 | Migrate `generate_agent_config()` | `src/services/agent_creator.py` (L28, L467) | Move logic to `ChatAgentService` or inline |
| 2.8 | Remove existence check | `src/services/signal_chat.py` (L659) | Replace with `get_chat_agent_service()` or configuration check |
| 2.9 | Remove import + fixture | `tests/conftest.py` (L67, L204–207) | Remove `AIAgentService` import and `mock_ai_agent_service` fixture |
| 2.10 | Update dependent tests | Various test files | Update any tests that depend on `mock_ai_agent_service` fixture |
| 2.11 | Delete deprecated service | `src/services/ai_agent.py` | Remove after all consumers migrated |
| 2.12 | Delete deprecated test | `tests/unit/test_ai_agent.py` | Remove alongside service |
| 2.13 | Grep verification | `grep -rn "ai_agent" src/ tests/` | Zero hits expected |

**Verification**: Full `pytest` pass; `pyright` no new errors; `ruff check` clean.

### Phase 3 — Remove completion_providers.py (depends on Phase 2)

**Goal**: Migrate 4 services still importing from the deprecated provider, relocate `CopilotClientPool` / `get_copilot_client_pool` into `agent_provider.py`, then delete `completion_providers.py`.

| Step | Action | File | Details |
|------|--------|------|---------|
| 3.1 | Relocate `CopilotClientPool` + `get_copilot_client_pool` | `src/services/agent_provider.py` | Move/inline from `completion_providers.py`; these are the only non-deprecated symbols |
| 3.2 | Update lazy import | `src/services/agent_provider.py` (L200) | Point to local definition |
| 3.3 | Update lazy import | `src/services/plan_agent_provider.py` (L194) | Import from `agent_provider` |
| 3.4 | Update direct import | `src/services/model_fetcher.py` (L17) | Import from `agent_provider` |
| 3.5 | Migrate `create_completion_provider()` | `src/services/label_classifier.py` (L101, L157) | Replace with `agent_provider`-based completion or inline equivalent |
| 3.6 | Delete deprecated provider | `src/services/completion_providers.py` | Remove after all consumers migrated |
| 3.7 | Delete deprecated test | `tests/unit/test_completion_providers.py` | Remove alongside module |
| 3.8 | Grep verification | `grep -rn "completion_providers" src/ tests/` | Zero hits expected |

**Verification**: Full `pytest` pass; `pyright` no new errors; `ruff check` clean.

### Phase 4 — Minor Backend Cleanup (parallel with Phase 3)

| Step | Action | File | Details |
|------|--------|------|---------|
| 4.1 | Evaluate `pipeline_metadata` field | `src/services/copilot_polling/auto_merge.py` | Field is wired through `dispatch_devops_agent()` → `schedule_post_devops_merge_retry()` → `_post_devops_retry_loop()` with active mutation (`devops_active = False`). **Decision**: Keep for now — removal requires data-migration analysis and call-site audit across the retry flow. Document as deferred. |
| 4.2 | Convert singleton TODOs | `src/services/chores/service.py`, `src/services/agents/service.py` | Confirm TODO markers exist; if present, convert to tracked issue reference (TODO-018). If not found at specified lines, skip. |

**Verification**: `ruff check`; `pyright`.

### Phase 5 — Frontend Logging Cleanup (independent, parallel with all)

| Step | Action | File | Details |
|------|--------|------|---------|
| 5.1 | Wrap `console.debug()` in DEV guard | `api.ts` (L462, L477, L641) | `if (import.meta.env.DEV) { console.debug(...) }` |
| 5.2 | Verify tooltip already guarded | `tooltip.tsx` (L52) | Already wrapped in `import.meta.env.DEV` — no change needed |
| 5.3 | Wrap `console.warn()` in DEV guard | `usePipelineConfig.ts` (L170) | `if (import.meta.env.DEV) { console.warn(...) }` |

**Verification**: `npm run lint`; `npm run type-check`; `npm run test`.

### Phase 6 — Repository Organization (independent, parallel with all)

| Step | Action | Details |
|------|--------|---------|
| 6.1 | Create `specs/000-simplify-page-headers/` | New directory for root-level spec files |
| 6.2 | Move root-level spec files | `plan.md`, `spec.md`, `tasks.md`, `data-model.md`, `research.md`, `quickstart.md` → `specs/000-simplify-page-headers/` |
| 6.3 | Verify mono-spec consistency | Structure matches `specs/001-fleet-dispatch-pipelines/` pattern |

**Verification**: All spec file paths resolve; no broken references.

## Verification Matrix

| Check | Command | After Phase |
|-------|---------|-------------|
| Backend tests | `cd solune/backend && uv run pytest tests/ --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency` | 1, 2, 3, 4 |
| Type checking | `cd solune/backend && uv run pyright src/` | 2, 3, 4 |
| Lint | `cd solune/backend && uv run ruff check src/ tests/` | 2, 3, 4 |
| Frontend tests | `cd solune/frontend && npm run test` | 5 |
| Frontend lint | `cd solune/frontend && npm run lint` | 5 |
| Frontend types | `cd solune/frontend && npm run type-check` | 5 |
| Dead code grep | `grep -rn "ai_agent\|completion_providers\|issue_generation\|task_generation\|transcript_analysis" solune/backend/src/ solune/backend/tests/` | 3 |
| OpenAPI schema | `validate-contracts.sh` | 3 |
| Docker builds | Backend and frontend Dockerfiles | Final |

## Decisions

| Decision | Rationale |
|----------|-----------|
| **Excluded**: Circular import workarounds in `dependencies.py` and `github_projects/service.py` | Intentional and documented; not dead code |
| **Excluded**: Auto-generated OpenAPI types in `openapi-generated.d.ts` | Managed by contract pipeline; not manual code |
| **Excluded**: Frontend structural cleanup | No dead components, hooks, routes, or unused deps found |
| **Deferred**: Singleton DI refactor (TODO-018) | Replacing module-level singletons with FastAPI DI is a larger architecture change — recommend separate issue |
| **Deferred**: `pipeline_metadata` removal in `auto_merge.py` | Field is actively mutated in retry flow; removal requires data-migration analysis |
| **tooltip.tsx already guarded** | `console.warn()` at L52 is already inside `import.meta.env.DEV` check — no change needed |

## Complexity Tracking

> No constitution violations found. No complexity justifications required.
