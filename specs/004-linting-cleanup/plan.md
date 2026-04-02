# Implementation Plan: Linting Clean Up

**Branch**: `004-linting-cleanup` | **Date**: 2026-04-02 | **Spec**: [`specs/004-linting-cleanup/spec.md`](spec.md)
**Input**: Feature specification from `/specs/004-linting-cleanup/spec.md`

## Summary

Remove all type-suppression comments from authored backend and frontend code, add dedicated test type-check gates to CI and pre-commit, and tighten ESLint guardrails to prevent regression. The cleanup is ordered so that type-check gates for test code are established first (making suppressions visible), then backend source → backend tests → frontend source → frontend tests are cleaned in dependency order. Bugs exposed by removing suppressions are fixed in the same pass.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript ES2022 / React 18 (frontend)
**Primary Dependencies**: FastAPI, Pydantic, Pyright (backend); Vite, Vitest, ESLint, TypeScript strict (frontend)
**Storage**: SQLite via aiosqlite (backend)
**Testing**: pytest + pytest-asyncio (backend), Vitest + React Testing Library (frontend), Playwright (E2E)
**Target Platform**: Linux server (backend), modern browsers (frontend)
**Project Type**: Web application (monorepo: `solune/backend/` + `solune/frontend/`)
**Performance Goals**: N/A — tooling/quality change, no runtime performance targets
**Constraints**: Zero net new suppressions; all existing CI gates must continue to pass
**Scale/Scope**: ~46 backend source suppressions, 9 pyright file-level directives, ~28 backend test suppressions, ~17 frontend production suppressions, ~46 frontend test suppressions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| Specification-First Development | ✅ PASS | `spec.md` includes 5 prioritised user stories (P1–P5) with Given-When-Then acceptance scenarios and explicit scope boundaries |
| Template-Driven Workflow | ✅ PASS | All artifacts follow `.specify/templates/` structure; no custom sections added |
| Agent-Orchestrated Execution | ✅ PASS | Single-responsibility plan phase; clear input (spec.md) and output (plan.md, research.md, data-model.md, quickstart.md, contracts/) |
| Test Optionality with Clarity | ✅ PASS | Spec explicitly mandates type-check gates and test cleanup; tests are in scope by design |
| Simplicity and DRY | ✅ PASS | Shared suppression patterns resolved first to create reusable solutions; no new dependencies introduced |
| Independent User Stories | ✅ PASS | Each P-level story is independently implementable and testable (gate expansion, backend source, backend test, frontend source, frontend test) |

**Post-Phase 1 Re-check**: ✅ PASS — No new violations introduced by design artifacts. Data model is configuration-only (tsconfig, pyright config). No new runtime code patterns.

## Project Structure

### Documentation (this feature)

```text
specs/004-linting-cleanup/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: Suppression inventory and resolution strategies
├── data-model.md        # Phase 1: Configuration models (tsconfig, pyright, ESLint)
├── quickstart.md        # Phase 1: Step-by-step contributor guide
├── contracts/           # Phase 1: No API contracts (tooling-only change)
│   └── README.md        # Explains why no API contracts are needed
├── checklists/          # Quality checklists
│   └── requirements.md
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── pyproject.toml          # Pyright config (add test include)
│   ├── src/
│   │   ├── config.py           # Settings type-ignore cleanup
│   │   ├── logging_utils.py    # LogRecord extension cleanup
│   │   ├── main.py             # Rate-limit handler cleanup
│   │   ├── utils.py            # Cache generic cleanup
│   │   ├── api/
│   │   │   ├── chat.py         # Assignment cleanup
│   │   │   └── workflow.py     # Agent mapping cleanup
│   │   └── services/
│   │       ├── cache.py                      # Generic return-value cleanup
│   │       ├── task_registry.py              # asyncio.Task typing
│   │       ├── model_fetcher.py              # asyncio.Task typing
│   │       ├── completion_providers.py       # Optional import cleanup
│   │       ├── agent_provider.py             # Optional import cleanup
│   │       ├── otel_setup.py                 # OTel typing stubs
│   │       ├── metadata_service.py           # Row indexing cleanup
│   │       ├── agents/service.py             # dict.get arg cleanup
│   │       ├── tools/service.py              # dict iteration cleanup
│   │       └── github_projects/
│   │           ├── service.py                # asyncio.Task + cache cleanup
│   │           ├── board.py                  # pyright directive cleanup
│   │           ├── repository.py             # pyright directive cleanup
│   │           ├── branches.py               # pyright directive cleanup
│   │           ├── agents.py                 # pyright directive cleanup
│   │           ├── projects.py               # pyright directive cleanup
│   │           ├── copilot.py                # pyright directive cleanup
│   │           ├── issues.py                 # pyright directive cleanup
│   │           └── pull_requests.py          # pyright directive cleanup
│   └── tests/
│       ├── unit/
│       │   ├── test_metadata_service.py      # Typed fake cleanup
│       │   ├── test_logging_utils.py         # LogRecord attr cleanup
│       │   ├── test_polling_loop.py          # Frozen field cleanup
│       │   ├── test_template_files.py        # Generator yield cleanup
│       │   ├── test_pipeline_state_store.py  # TypedDict cleanup
│       │   ├── test_api_board.py             # retry_after attr cleanup
│       │   ├── test_transcript_detector.py   # Frozen field cleanup
│       │   └── test_agent_output.py          # Frozen field cleanup
│       ├── integration/
│       │   └── test_production_mode.py       # Settings call-arg cleanup
│       └── concurrency/
│           └── test_transaction_safety.py    # Mock method-assign cleanup
├── frontend/
│   ├── tsconfig.json             # Main config (unchanged)
│   ├── tsconfig.test.json        # NEW: Test type-check config
│   ├── eslint.config.js          # Tighten suppression rules
│   ├── src/
│   │   ├── test/setup.ts                          # WebSocket/crypto typing
│   │   ├── services/api.ts                        # ThinkingEvent cast
│   │   ├── hooks/useVoiceInput.ts                 # SpeechRecognition typing
│   │   ├── hooks/useRealTimeSync.ts               # Deps comment
│   │   ├── lib/lazyWithRetry.ts                   # Generic constraint
│   │   ├── components/board/AgentColumnCell.tsx    # dnd-kit typing
│   │   └── components/settings/McpSettings.tsx     # Error shape typing
│   └── e2e/
│       └── fixtures.ts           # Rules-of-hooks (keep — E2E pattern)
├── .pre-commit-config.yaml       # Add test type-check hooks
├── scripts/pre-commit            # Add test type-check steps
└── docs/testing.md               # Update with new commands

.github/
└── workflows/ci.yml              # Add test type-check CI steps
```

**Structure Decision**: Existing web application structure (`solune/backend/` + `solune/frontend/`). No new directories created. New configuration files: `solune/frontend/tsconfig.test.json` (frontend test type-check) and pyright `include` expansion in `pyproject.toml` (backend test type-check).

## Complexity Tracking

> No Constitution Check violations to justify. All changes use existing tools and patterns.
