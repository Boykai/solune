# Implementation Plan: Modernize Logging Practices

**Branch**: `003-modernize-logging` | **Date**: 2026-04-13 | **Spec**: `specs/003-modernize-logging/spec.md`
**Input**: Parent Issue #1643 — Modernize Logging Practices

## Summary

Modernize logging across backend and frontend. Backend: define a canonical `STRUCTURED_FIELDS` set in `logging_utils.py`, expand structured extra fields (`operation`, `duration_ms`, `error_type`, `status_code`) across all service-layer log calls, silence 5 additional noisy third-party loggers, and add an OTel `LoggerProvider` bridge gated behind the existing `otel_enabled` flag. Frontend: create a centralized `logger.ts` utility with env gating, sensitive-key redaction, and APM hook; replace all 13 raw `console.*` calls with logger equivalents (sanitizing SSE/WebSocket payloads); consolidate duplicate error-extraction utilities into `src/utils/errorUtils.ts`.

| Phase | Scope | Key Output |
|-------|-------|------------|
| 1 | Backend: Expand structured logging fields | `logging_utils.py` STRUCTURED_FIELDS, service-layer extra fields |
| 2 | Backend: Silence noisy loggers | 5 new `setLevel(WARNING)` lines in `config.py` |
| 3 | Backend: OTel logs bridge | `otel_setup.py` LoggerProvider + LoggingHandler |
| 4 | Frontend: Logger utility | `src/lib/logger.ts` + `src/lib/logger.test.ts` |
| 5 | Frontend: Replace raw console calls (depends on Phase 4) | 13 call sites updated across 8 files |
| 6 | Frontend: Consolidate error utilities | `src/utils/errorUtils.ts` |

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript 5.x (frontend)
**Primary Dependencies**: Backend: FastAPI, stdlib `logging`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`. Frontend: React 18, Vite, Vitest
**Storage**: N/A (logging infrastructure, no data-layer changes)
**Testing**: Backend: `pytest` + `ruff` + `pyright`. Frontend: Vitest + ESLint + `tsc --noEmit`
**Target Platform**: Linux server (backend), modern browsers (frontend SPA)
**Project Type**: Web application (backend + frontend)
**Performance Goals**: Zero-cost when OTel disabled; logger utility adds <1ms per call; no new runtime dependencies in frontend
**Constraints**: Backend stays stdlib `logging` (no structlog/loguru); SSE/WebSocket logs must not expose user content; OTel bridge must not block the application if collector is unreachable
**Scale/Scope**: Backend: 3 files modified (logging_utils.py, config.py, otel_setup.py) + structured fields in ~10 service files. Frontend: 1 file created (logger.ts + tests), 8 files modified (console replacements), 1 file created (errorUtils.ts), 2 files modified (import updates)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Specification-First Development**: PASS — `specs/003-modernize-logging/spec.md` defines 6 prioritized user stories with independent acceptance scenarios and Given-When-Then criteria. Scope boundaries and out-of-scope items are declared.
- **II. Template-Driven Workflow**: PASS — all Phase 0/1 artifacts (`plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/`) follow canonical templates within `specs/003-modernize-logging/`.
- **III. Agent-Orchestrated Execution**: PASS — this plan is produced by the `speckit.plan` agent, consuming the spec as input and producing planning artifacts for the `speckit.tasks` agent.
- **IV. Test Optionality with Clarity**: PASS — the spec explicitly requests frontend logger tests (`logger.test.ts`). Backend structured fields are verified via existing `pytest` and structured log spot-checks. No unnecessary test mandates.
- **V. Simplicity and DRY**: PASS — the frontend logger is a thin wrapper (no third-party library). Error utility consolidation removes duplication. Backend stays on stdlib logging. No premature abstractions.

**Post-Phase 1 Re-check**: PASS — `research.md` resolves all technical decisions without introducing complexity exceptions. `data-model.md` describes only the logger API shape and structured fields set (no new data entities). No constitution violations.

## Project Structure

### Documentation (this feature)

```text
specs/003-modernize-logging/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: research decisions
├── data-model.md        # Phase 1: structured fields + logger API shape
├── quickstart.md        # Phase 1: verification guide
├── contracts/
│   └── logger-api.yaml  # Phase 1: frontend logger contract
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/backend/src/
├── logging_utils.py            # STRUCTURED_FIELDS set, handle_service_error extra, @handle_github_errors extra
├── config.py                   # 5 additional setLevel(WARNING) lines
├── services/
│   ├── otel_setup.py           # LoggerProvider + OTLPLogExporter + LoggingHandler
│   ├── database.py             # extra={"operation": ..., "duration_ms": ...}
│   ├── ai_agent.py             # extra={"operation": ..., "duration_ms": ...}
│   ├── chat_agent.py           # extra={"operation": ..., "duration_ms": ...}
│   ├── pipeline_orchestrator.py # extra={"operation": ..., "duration_ms": ...}
│   ├── copilot_polling/
│   │   └── pipeline.py         # extra={"operation": ..., "duration_ms": ...}
│   ├── workflow_orchestrator/
│   │   └── orchestrator.py     # extra={"operation": ..., "duration_ms": ...}
│   ├── pipelines/service.py    # extra={"operation": ..., "duration_ms": ...}
│   ├── github_projects/service.py
│   ├── tools/service.py
│   ├── chores/service.py
│   └── agents/service.py

solune/backend/pyproject.toml   # opentelemetry-exporter-otlp-proto-grpc optional dep

solune/frontend/src/
├── lib/
│   ├── logger.ts               # NEW: centralized logger utility
│   └── logger.test.ts          # NEW: logger tests
├── utils/
│   └── errorUtils.ts           # NEW: consolidated getErrorMessage()
├── main.tsx                    # Replace console.error → logger.error
├── components/
│   ├── common/ErrorBoundary.tsx # Replace console.error → logger.captureException
│   └── ui/tooltip.tsx          # Replace console.warn → logger.warn
├── services/
│   ├── api.ts                  # Replace console.error/debug → logger.error/debug
│   └── schemas/validate.ts     # Replace console.error → logger.warn
├── hooks/
│   ├── useRealTimeSync.ts      # Replace console.error → logger.error
│   ├── usePipelineConfig.ts    # Replace console.warn + import getErrorMessage
│   └── useApps.ts              # Import getErrorMessage from errorUtils
└── pages/
    ├── ChoresPage.tsx           # Replace console.warn → logger.warn
    └── AgentsPipelinePage.tsx   # Replace console.warn → logger.warn
```

**Structure Decision**: Web application layout. Backend changes modify existing files within `solune/backend/src/`. Frontend changes add 2 new files (`logger.ts`, `errorUtils.ts`) and modify 10 existing files. No new directories created.

## Complexity Tracking

No constitution violations or complexity exceptions are required at plan time.
