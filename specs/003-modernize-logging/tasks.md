# Tasks: Modernize Logging Practices

**Input**: Design documents from `specs/003-modernize-logging/`
**Prerequisites**: `specs/003-modernize-logging/plan.md`, `specs/003-modernize-logging/spec.md`, `specs/003-modernize-logging/research.md`, `specs/003-modernize-logging/data-model.md`, `specs/003-modernize-logging/quickstart.md`, `specs/003-modernize-logging/contracts/logger-api.yaml`

**Tests**: Frontend logger tests (`logger.test.ts`) are included because the spec explicitly requests them. Backend verification uses existing `pytest` coverage and structured log spot-checks per `quickstart.md`.

**Organization**: Tasks are grouped by user story so each increment can be implemented and validated independently once its dependencies are complete.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Define the canonical structured fields contract and prepare the formatter to consume them.

- [ ] T001 Define `STRUCTURED_FIELDS: frozenset[str]` containing `{"operation", "duration_ms", "error_type", "status_code"}` in `solune/backend/src/logging_utils.py`
- [ ] T002 Refactor `StructuredJsonFormatter.format()` to iterate `STRUCTURED_FIELDS` via `getattr(record, key, None)` instead of ad-hoc checks in `solune/backend/src/logging_utils.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Error-handler structured fields that all user stories and service-layer tasks depend on.

**⚠️ CRITICAL**: Complete this phase before starting user story service-layer work — `handle_service_error()` and `@handle_github_errors` are shared by all service modules.

- [ ] T003 Add `extra={"error_type": type(exc).__name__}` to `handle_service_error()` log calls in `solune/backend/src/logging_utils.py`
- [ ] T004 Add `extra={"error_type": type(exc).__name__}` to `@handle_github_errors` decorator log calls in `solune/backend/src/logging_utils.py`

**Checkpoint**: Foundation ready — STRUCTURED_FIELDS defined, formatter updated, error handlers enriched. User story work can begin.

---

## Phase 3: User Story 1 — Backend: Expand Structured Logging Fields (Priority: P1) 🎯 MVP

**Goal**: Every key service-layer call emits `extra={"operation": ..., "duration_ms": ...}` so APM dashboards can filter by operation and latency.

**Independent Test**: Set `STRUCTURED_LOGGING=true`, trigger a service-layer operation, and verify the JSON log line includes `operation` and `duration_ms` keys with correct values.

### Implementation for User Story 1

- [ ] T005 [P] [US1] Add `extra={"operation": ..., "duration_ms": ...}` to key functions in `solune/backend/src/services/agents/service.py`
- [ ] T006 [P] [US1] Add `extra={"operation": ..., "duration_ms": ...}` to key functions in `solune/backend/src/services/pipelines/service.py`
- [ ] T007 [P] [US1] Add `extra={"operation": ..., "duration_ms": ...}` to key functions in `solune/backend/src/services/github_projects/service.py`
- [ ] T008 [P] [US1] Add `extra={"operation": ..., "duration_ms": ...}` to key functions in `solune/backend/src/services/tools/service.py`
- [ ] T009 [P] [US1] Add `extra={"operation": ..., "duration_ms": ...}` to key functions in `solune/backend/src/services/chores/service.py`
- [ ] T010 [P] [US1] Add `extra={"operation": ..., "duration_ms": ...}` to key functions in `solune/backend/src/services/database.py`
- [ ] T011 [P] [US1] Add `extra={"operation": ..., "duration_ms": ...}` to key functions in `solune/backend/src/services/ai_agent.py`
- [ ] T012 [P] [US1] Add `extra={"operation": ..., "duration_ms": ...}` to key functions in `solune/backend/src/services/chat_agent.py`
- [ ] T013 [P] [US1] Add `extra={"operation": ..., "duration_ms": ...}` to key functions in `solune/backend/src/services/pipeline_orchestrator.py`
- [ ] T014 [P] [US1] Add `extra={"operation": ..., "duration_ms": ...}` to key functions in `solune/backend/src/services/copilot_polling/pipeline.py`
- [ ] T015 [P] [US1] Add `extra={"operation": ..., "duration_ms": ...}` to key functions in `solune/backend/src/services/workflow_orchestrator/orchestrator.py`

**Checkpoint**: All service-layer log calls emit structured fields. Verify with `STRUCTURED_LOGGING=true` spot-check per quickstart.md Phase 1.

---

## Phase 4: User Story 2 — Backend: Silence Remaining Noisy Loggers (Priority: P1)

**Goal**: Suppress 5 additional noisy third-party loggers (`uvicorn`, `uvicorn.access`, `uvicorn.error`, `asyncio`, `watchfiles`) at WARNING level, matching the existing pattern for `httpx`/`httpcore`/`aiosqlite`.

**Independent Test**: Run the backend with `LOG_LEVEL=DEBUG` and verify the 5 loggers are all at WARNING or above.

### Implementation for User Story 2

- [ ] T016 [US2] Add `setLevel(logging.WARNING)` for `uvicorn`, `uvicorn.access`, `uvicorn.error`, `asyncio`, and `watchfiles` loggers in `solune/backend/src/config.py`

**Checkpoint**: All noisy loggers silenced. Verify with quickstart.md Phase 2 script.

---

## Phase 5: User Story 3 — Backend: Add OTel Logs Bridge (Priority: P2)

**Goal**: When `OTEL_ENABLED=true`, forward stdlib log records to the OTLP collector via a `LoggerProvider` + `LoggingHandler` bridge. Zero cost when disabled.

**Independent Test**: Start backend without OTel and verify no LoggingHandler is attached. With `OTEL_ENABLED=true` and a local collector, verify log records are received.

### Implementation for User Story 3

- [ ] T017 [US3] Add `opentelemetry-exporter-otlp-proto-grpc` to optional dependencies in `solune/backend/pyproject.toml`
- [ ] T018 [US3] Create `LoggerProvider` with `BatchLogRecordProcessor` and `OTLPLogExporter` in `init_otel()` in `solune/backend/src/services/otel_setup.py`
- [ ] T019 [US3] Attach `LoggingHandler` to root logger gated behind `otel_enabled` flag in `solune/backend/src/services/otel_setup.py`
- [ ] T020 [US3] Add `LoggerProvider.shutdown()` to the existing shutdown path in `solune/backend/src/services/otel_setup.py`

**Checkpoint**: OTel logs bridge functional when enabled. Verify with quickstart.md Phase 3 script.

---

## Phase 6: User Story 4 — Frontend: Create Logger Utility (Priority: P1)

**Goal**: Centralized `logger` object in `src/lib/logger.ts` with `debug`, `warn`, `error`, and `captureException` methods — env-gated debug, always-on warn/error, sensitive key redaction, and APM hook.

**Independent Test**: Import logger in a Vitest test, verify debug is suppressed in production, sensitive keys are redacted, and error/warn always emit.

### Tests for User Story 4

- [ ] T021 [P] [US4] Write tests for `logger.debug` env gating (suppressed when DEV=false, emitted when DEV=true) in `solune/frontend/src/lib/logger.test.ts`
- [ ] T022 [P] [US4] Write tests for sensitive key redaction (`authorization`, `token`, `cookie`, `password`, `secret`) in `solune/frontend/src/lib/logger.test.ts`
- [ ] T023 [P] [US4] Write tests for `logger.warn`, `logger.error`, and `logger.captureException` behavior in `solune/frontend/src/lib/logger.test.ts`

### Implementation for User Story 4

- [ ] T024 [US4] Create `redactContext()` helper that replaces top-level sensitive keys with `'[REDACTED]'` in `solune/frontend/src/lib/logger.ts`
- [ ] T025 [US4] Create `logger.debug(tag, msg, ctx?)` gated by `import.meta.env.DEV` in `solune/frontend/src/lib/logger.ts`
- [ ] T026 [US4] Create `logger.warn(tag, msg, ctx?)` and `logger.error(tag, msg, ctx?)` (always emit) in `solune/frontend/src/lib/logger.ts`
- [ ] T027 [US4] Create `logger.captureException(error, ctx?)` that calls `console.error` and stores for APM in `solune/frontend/src/lib/logger.ts`

**Checkpoint**: Logger utility created and tested. Verify with `npm run test -- --run src/lib/logger.test.ts`.

---

## Phase 7: User Story 5 — Frontend: Replace Raw Console Calls (Priority: P1, depends on US-4)

**Goal**: Replace all 13 raw `console.*` calls with `logger.*` equivalents. SSE/WebSocket payloads are sanitized (log event type + error code only, not user content). Zero raw `console.*` calls remain outside tests and `logger.ts`.

**Independent Test**: Run `grep -r 'console\.\(log\|debug\|warn\|error\)' src/ --include='*.ts' --include='*.tsx'` excluding tests and `logger.ts` — zero matches.

### Implementation for User Story 5

- [ ] T028 [P] [US5] Replace `console.error` calls in global error handlers with `logger.error('global:onerror', ...)` and `logger.error('global:unhandledrejection', ...)` in `solune/frontend/src/main.tsx`
- [ ] T029 [P] [US5] Replace `console.error` in `componentDidCatch` with `logger.captureException(error, { componentStack })` in `solune/frontend/src/components/common/ErrorBoundary.tsx`
- [ ] T030 [P] [US5] Replace `console.error` auth-expired call with `logger.error('auth', ...)` in `solune/frontend/src/services/api.ts`
- [ ] T031 [US5] Replace `console.debug` SSE parse calls with `logger.debug('sse', ...)` — sanitize to event type + error code only — in `solune/frontend/src/services/api.ts`
- [ ] T032 [P] [US5] Replace `console.error` schema validation call with `logger.warn('schema', ...)` in `solune/frontend/src/services/schemas/validate.ts`
- [ ] T033 [P] [US5] Replace `console.error` WebSocket parse call with `logger.error('websocket', ...)` — sanitize raw message — in `solune/frontend/src/hooks/useRealTimeSync.ts`
- [ ] T034 [P] [US5] Replace `console.warn` chore seeding call with `logger.warn('chores', ...)` in `solune/frontend/src/pages/ChoresPage.tsx`
- [ ] T035 [P] [US5] Replace `console.warn` pipeline seeding call with `logger.warn('pipeline', ...)` in `solune/frontend/src/pages/AgentsPipelinePage.tsx`
- [ ] T036 [P] [US5] Replace `console.warn` pipeline assignment call with `logger.warn('pipeline', ...)` and import `getErrorMessage` in `solune/frontend/src/hooks/usePipelineConfig.ts`
- [ ] T037 [P] [US5] Replace `console.warn` tooltip registry call with `logger.debug('tooltip', ...)` in `solune/frontend/src/components/ui/tooltip.tsx`

**Checkpoint**: Zero raw `console.*` calls outside tests and `logger.ts`. Verify with quickstart.md Phase 5 grep audit.

---

## Phase 8: User Story 6 — Frontend: Consolidate Error Message Utilities (Priority: P2)

**Goal**: Single canonical `getErrorMessage()` in `src/utils/errorUtils.ts`. Replace inline `errMsg()` in `usePipelineConfig.ts` and local `getErrorMessage()` in `useApps.ts` with the shared import. `getErrorHint()` in `errorHints.ts` remains separate (different purpose).

**Independent Test**: Import `getErrorMessage` from `src/utils/errorUtils.ts`, pass an `ApiError` and a plain `Error`, verify correct message extraction.

### Implementation for User Story 6

- [ ] T038 [US6] Create `getErrorMessage(error, fallback)` function in `solune/frontend/src/utils/errorUtils.ts`
- [ ] T039 [US6] Replace local `getErrorMessage()` in `solune/frontend/src/hooks/useApps.ts` with import from `@/utils/errorUtils`
- [ ] T040 [US6] Replace inline `errMsg()` in `solune/frontend/src/hooks/usePipelineConfig.ts` with import of `getErrorMessage` from `@/utils/errorUtils`
- [ ] T041 [US6] Update import paths and verify tests pass in `solune/frontend/src/hooks/useApps.test.tsx`

**Checkpoint**: Single error extraction utility. Verify with quickstart.md Phase 6 script.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, and cross-story verification.

- [ ] T042 [P] Run backend validation: `ruff check src/ tests/`, `pyright src/`, `pytest tests/ -q` in `solune/backend/`
- [ ] T043 [P] Run frontend validation: `npm run lint`, `npm run type-check`, `npm run test` in `solune/frontend/`
- [ ] T044 [P] Run structured log spot-check with `STRUCTURED_LOGGING=true` per `specs/003-modernize-logging/quickstart.md` Phase 1
- [ ] T045 [P] Run noisy logger verification per `specs/003-modernize-logging/quickstart.md` Phase 2
- [ ] T046 [P] Run OTel bridge verification per `specs/003-modernize-logging/quickstart.md` Phase 3
- [ ] T047 Run console audit grep in `solune/frontend/src/` — confirm zero raw `console.*` calls outside tests and `logger.ts`
- [ ] T048 [P] Verify both Dockerfiles build cleanly via `docker compose build` using `solune/backend/Dockerfile` and `solune/frontend/Dockerfile`
- [ ] T049 Run full validation end-to-end per `specs/003-modernize-logging/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — can start immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1 (STRUCTURED_FIELDS and formatter must exist before error handler enrichment).
- **Phase 3 (US1)**: Depends on Phase 2 — service-layer calls rely on enriched error handlers and the formatter.
- **Phase 4 (US2)**: Independent — depends only on Phase 1 completion; can run in parallel with Phase 3.
- **Phase 5 (US3)**: Independent — depends only on Phase 1 completion; can run in parallel with Phase 3/4.
- **Phase 6 (US4)**: Independent — frontend work, no backend dependencies.
- **Phase 7 (US5)**: Depends on Phase 6 — logger utility must exist before replacing console calls.
- **Phase 8 (US6)**: Independent — frontend utility consolidation, no cross-story dependency.
- **Phase 9 (Polish)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational (Phase 2). No dependencies on other stories.
- **US2 (P1)**: Can start after Phase 1. No dependencies on other stories.
- **US3 (P2)**: Can start after Phase 1. No dependencies on other stories.
- **US4 (P1)**: Can start immediately. No backend dependencies.
- **US5 (P1)**: Depends on US4 (Phase 6). No other story dependencies.
- **US6 (P2)**: Can start immediately. No dependencies on other stories.

### Recommended Execution Order

1. Finish **Phase 1: Setup** (T001–T002)
2. Finish **Phase 2: Foundational** (T003–T004)
3. Deliver **US1** for the backend structured logging MVP (T005–T015)
4. Deliver **US2** to silence noisy loggers (T016)
5. Deliver **US4** for the frontend logger utility (T021–T027)
6. Deliver **US5** to replace all raw console calls (T028–T037)
7. Deliver **US3** for the OTel logs bridge (T017–T020)
8. Deliver **US6** to consolidate error utilities (T038–T041)
9. Finish **Phase 9: Polish** (T042–T049)

---

## Parallel Opportunities per Story

### User Story 1

```bash
# All service-layer files are independent — launch in parallel:
T005 solune/backend/src/services/agents/service.py
T006 solune/backend/src/services/pipelines/service.py
T007 solune/backend/src/services/github_projects/service.py
T008 solune/backend/src/services/tools/service.py
T009 solune/backend/src/services/chores/service.py
T010 solune/backend/src/services/database.py
T011 solune/backend/src/services/ai_agent.py
T012 solune/backend/src/services/chat_agent.py
T013 solune/backend/src/services/pipeline_orchestrator.py
T014 solune/backend/src/services/copilot_polling/pipeline.py
T015 solune/backend/src/services/workflow_orchestrator/orchestrator.py
```

### User Story 4

```bash
# Write all test cases in parallel (same file, different describe blocks):
T021 solune/frontend/src/lib/logger.test.ts (env gating)
T022 solune/frontend/src/lib/logger.test.ts (redaction)
T023 solune/frontend/src/lib/logger.test.ts (warn/error/captureException)
```

### User Story 5

```bash
# All replacement tasks target different files — launch in parallel:
T028 solune/frontend/src/main.tsx
T029 solune/frontend/src/components/common/ErrorBoundary.tsx
T030 solune/frontend/src/services/api.ts
T032 solune/frontend/src/services/schemas/validate.ts
T033 solune/frontend/src/hooks/useRealTimeSync.ts
T034 solune/frontend/src/pages/ChoresPage.tsx
T035 solune/frontend/src/pages/AgentsPipelinePage.tsx
T037 solune/frontend/src/components/ui/tooltip.tsx
```

### Cross-Story Parallelism

```bash
# Backend and frontend stories are fully independent:
# Backend track: US1 → US2 → US3
# Frontend track: US4 → US5, and US6 in parallel with US4
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T004)
3. Complete Phase 3: User Story 1 (T005–T015)
4. **STOP and VALIDATE**: Run `STRUCTURED_LOGGING=true` spot-check + `pytest` + `ruff` + `pyright`
5. Deploy/demo if ready — APM dashboards can now filter by operation and latency

### Incremental Delivery

1. **US1** delivers structured logging fields across all service-layer calls
2. **US2** silences noisy loggers for cleaner DEBUG output
3. **US4** delivers the frontend logger utility foundation
4. **US5** eliminates all raw console calls and sanitizes SSE/WebSocket logs
5. **US3** bridges stdlib logs to the OTel collector
6. **US6** consolidates duplicate error extraction utilities

### Parallel Team Strategy

1. Team completes **Setup + Foundational** together
2. Then split by backend/frontend track:
   - Engineer A: **US1** → **US2** → **US3** (all backend)
   - Engineer B: **US4** → **US5** (frontend logger + replacements)
   - Engineer C: **US6** (frontend error utilities) + **Phase 9 polish**

---

## Notes

- All task lines follow the required checklist format with sequential IDs, optional `[P]` markers, and `[USx]` labels only inside story phases.
- Every task points to an exact repository path so an implementation agent can act without additional clarification.
- Frontend logger tests (T021–T023) are included because the spec explicitly requests `logger.test.ts`.
- Backend structured fields are verified via existing `pytest` and quickstart.md spot-checks — no new backend test files required.
- `getErrorHint()` in `errorHints.ts` is intentionally NOT consolidated (different purpose: produces structured `ErrorHint` objects, not plain strings).
