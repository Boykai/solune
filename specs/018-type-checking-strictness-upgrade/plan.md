# Implementation Plan: Type Checking Strictness Upgrade

**Branch**: `copilot/type-checking-strictness-upgrade` | **Date**: 2026-04-06 | **Spec**: [#1018](https://github.com/Boykai/solune/issues/1018)
**Input**: Parent issue #1018 — remove all type suppression comments and tighten strictness

## Summary

Remove all type suppression comments across the Solune monorepo (34 `# type: ignore` + 9 `# pyright:` directives in backend; 2 `@ts-expect-error` + 1 `as any` + 2 `eslint-disable` + 1 production `as unknown as` + 55 test `as unknown as` in frontend) and resolve the underlying type issues. Both pyright (backend) and tsc (frontend) currently pass with 0 errors — all suppressions mask real typing gaps. Additionally tighten strictness settings: upgrade backend test pyright from `"off"` to `"standard"`.

The approach creates targeted type stubs for untyped third-party libraries (copilot SDK, githubkit), adds explicit protocol inheritance for OTel no-op classes, uses Pydantic's `model_validate({})` for Settings construction, declares proper TypeScript interfaces for vendor APIs, and introduces typed mock helpers to eliminate test `as unknown as` casts.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript 6.0 / ES2022 (frontend)
**Primary Dependencies**: FastAPI, Pydantic, githubkit, github-copilot-sdk, OpenTelemetry, slowapi (backend); React 19, Vite, TanStack Query, Vitest (frontend)
**Storage**: SQLite via aiosqlite (backend)
**Testing**: pytest + pytest-asyncio (backend), Vitest + Testing Library (frontend)
**Target Platform**: Linux server (Docker), Modern browsers (ES2022)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: N/A — no runtime changes, type-only refactor
**Constraints**: Zero breaking changes; pyright and tsc must pass with 0 errors after each step; all existing tests must continue passing
**Scale/Scope**: ~34 backend source files + ~38 frontend test files affected; 104 total suppressions to resolve

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Parent issue #1018 serves as specification with detailed step-by-step requirements |
| II. Template-Driven Workflow | ✅ PASS | Using canonical plan template; all artifacts in `specs/018-type-checking-strictness-upgrade/` |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan phase produces plan.md, research.md, data-model.md, quickstart.md; handoff to tasks phase |
| IV. Test Optionality | ✅ PASS | No new tests required by spec; existing tests must continue passing. Step 11 tightens test pyright config |
| V. Simplicity and DRY | ✅ PASS | Each fix is the simplest correct resolution — protocol inheritance, typed stubs, `model_validate({})`. No new abstractions beyond what's needed |

**Gate Result**: ✅ ALL PASS — proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/018-type-checking-strictness-upgrade/
├── plan.md              # This file
├── research.md          # Phase 0: resolution strategies per suppression category
├── data-model.md        # Phase 1: type stubs and extended type definitions
├── quickstart.md        # Phase 1: step-by-step developer implementation guide
├── contracts/
│   ├── copilot-stubs.md # Type stub contracts for github-copilot-sdk
│   └── githubkit-stubs.md # Type stub contracts for githubkit
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── config.py                          # Step 2: Settings.model_validate({})
│   │   ├── main.py                            # Step 2 + Step 5: Settings + slowapi
│   │   ├── typestubs/                         # Step 3 + Step 6: NEW — type stubs
│   │   │   ├── copilot/
│   │   │   │   ├── __init__.pyi
│   │   │   │   ├── types.pyi
│   │   │   │   └── generated/
│   │   │   │       └── session_events.pyi
│   │   │   └── githubkit/
│   │   │       └── __init__.pyi
│   │   └── services/
│   │       ├── otel_setup.py                  # Step 1 + Step 5: protocol inheritance
│   │       ├── agent_provider.py              # Step 3 + Step 4: stubs + ExtendedOptions
│   │       ├── completion_providers.py        # Step 3 + Step 4 + Step 6: stubs + options + githubkit
│   │       ├── plan_agent_provider.py         # Step 3 + Step 4: stubs + ExtendedOptions
│   │       └── github_projects/               # Step 6: remove all pyright directives
│   │           ├── board.py
│   │           ├── repository.py
│   │           ├── branches.py
│   │           ├── agents.py
│   │           ├── projects.py
│   │           ├── copilot.py
│   │           ├── issues.py
│   │           └── pull_requests.py
│   ├── tests/
│   │   ├── concurrency/test_transaction_safety.py  # Step 8
│   │   ├── integration/test_production_mode.py     # Step 9
│   │   └── unit/
│   │       ├── test_agent_output.py                # Step 7
│   │       ├── test_api_board.py                   # Step 8
│   │       ├── test_human_delay.py                 # Step 10
│   │       ├── test_label_classifier.py            # Step 7
│   │       ├── test_pipeline_state_store.py        # Step 10
│   │       ├── test_polling_loop.py                # Step 7
│   │       ├── test_run_mutmut_shard.py            # Step 10
│   │       └── test_transcript_detector.py         # Step 7
│   ├── pyrightconfig.tests.json                    # Step 11: "off" → "standard"
│   └── pyproject.toml                              # Step 3 + Step 6: add stubPath
│
└── frontend/
    └── src/
        ├── hooks/useVoiceInput.ts                  # Step 12: SpeechRecognitionWindow interface
        ├── lib/lazyWithRetry.ts                    # Step 13: proper generic constraint
        ├── services/api.ts                         # Step 14: Zod/type-guard for ThinkingEvent
        ├── test/setup.ts                           # Step 15: typed shims
        └── hooks/__tests__/ + components/__tests__/ # Step 16: typed mock helpers
```

**Structure Decision**: Web application (Option 2). This feature modifies existing files across `solune/backend/` and `solune/frontend/` — no new directories except `solune/backend/src/typestubs/` for Python type stubs.

## Execution Phases (from Issue #1018)

### Phase 1 — Backend Source Suppressions (15 ignores + 9 pyright directives)

| Step | Target | Suppressions | Fix Strategy |
|------|--------|-------------|--------------|
| 1 | OTel protocol implementations | 4 (`otel_setup.py`) | Add explicit protocol inheritance guarded by `TYPE_CHECKING` |
| 2 | Pydantic Settings() call-arg | 2 (`config.py`, `main.py`) | Use `Settings.model_validate({})` |
| 3 | Copilot SDK missing imports | 6 (`agent_provider.py`, `completion_providers.py`, `plan_agent_provider.py`) | Create `src/typestubs/copilot/` stubs; add `stubPath` to pyright config |
| 4 | TypedDict reasoning_effort | 3 (same files as Step 3) | Declare `ExtendedGitHubCopilotOptions(GitHubCopilotOptions, total=False)` |
| 5 | slowapi + FastAPIInstrumentor | 2 (`main.py`, `otel_setup.py`) | Typed adapter wrapper; OTel resolves after Step 1 |
| 6 | githubkit reportAttributeAccessIssue | 9 (8 files + 1 inline) | Create `src/typestubs/githubkit/` stubs; remove all directives |

### Phase 2 — Backend Test Suppressions (19 ignores) + Pyright Upgrade

| Step | Target | Suppressions | Fix Strategy |
|------|--------|-------------|--------------|
| 7 | Frozen dataclass mutations | 4 | `object.__setattr__()` or `dataclasses.replace()` |
| 8 | Mock method/attribute overrides | 3 | `patch.object()` or `MagicMock(spec=...)` |
| 9 | Pydantic Settings in tests | 6 | Resolved by Step 2 pattern |
| 10 | Remaining test ignores | 3+3 | Type annotations, `getattr()`, runtime bug investigation |
| 11 | Upgrade test pyright mode | config change | `"off"` → `"standard"`, remove `reportInvalidTypeForm: "none"` |

### Phase 3 — Frontend Source Suppressions (7 suppressions)

| Step | Target | Suppressions | Fix Strategy |
|------|--------|-------------|--------------|
| 12 | useVoiceInput.ts | 2 (`as any` + eslint-disable) | Declare `SpeechRecognitionWindow` interface |
| 13 | lazyWithRetry.ts | 2 (`ComponentType<any>` + eslint-disable) | Proper generic constraint `ComponentType<Record<string, unknown>>` |
| 14 | api.ts | 1 (`as unknown as ThinkingEvent`) | Type guard or Zod parse |
| 15 | test/setup.ts | 2 (`@ts-expect-error`) | Typed shim interfaces for crypto and WebSocket |

### Phase 4 — Frontend Test Suppressions (55 `as unknown as` casts)

| Step | Target | Suppressions | Fix Strategy |
|------|--------|-------------|--------------|
| 16 | Test mock casts | 55 across 38 files | Typed mock factory helpers (`mockFetchResponse<T>()`, `mockQueryResult<T>()`) or `satisfies Partial<T>` pattern |

## Constitution Re-Check (Post-Design)

*Re-evaluated after Phase 1 design completion.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | All design artifacts trace back to issue #1018 requirements |
| II. Template-Driven Workflow | ✅ PASS | plan.md, research.md, data-model.md, quickstart.md, contracts/ all follow templates |
| III. Agent-Orchestrated Execution | ✅ PASS | Clear handoff: plan → tasks → implement. Each step independently verifiable |
| IV. Test Optionality | ✅ PASS | No new tests added; existing tests validated at each step; Step 11 tightens test type checking |
| V. Simplicity and DRY | ✅ PASS | Type stubs are minimal (only imported symbols). `ExtendedGitHubCopilotOptions` is DRY shared type. No new abstractions beyond what's necessary |

**Post-Design Gate Result**: ✅ ALL PASS — ready for `/speckit.tasks`

## Complexity Tracking

> No constitution violations detected — table intentionally left empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
