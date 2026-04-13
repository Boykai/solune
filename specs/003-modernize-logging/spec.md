# Feature Specification: Modernize Logging Practices

**Feature Branch**: `003-modernize-logging`  
**Created**: 2026-04-13  
**Status**: Draft  
**Input**: Parent Issue #1643 — Modernize Logging Practices

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Backend: Expand Structured Logging Fields (Priority: P1)

A backend developer investigating a production incident uses APM dashboards to filter structured JSON logs by `operation`, `duration_ms`, `error_type`, and `status_code`. Today only `github_commit_workflow.py` emits those fields (3 call sites). After this story, every key service-layer call across `service.py`, `chat_agent.py`, `orchestrator.py`, `pipeline.py`, and `database.py` emits structured extra fields, enabling rich APM queries without custom log-parsing rules.

**Why this priority**: Structured fields are the foundation for all downstream observability (OTel bridge, APM dashboards). Without them, logs exported to a collector carry no queryable dimensions beyond `message` and `level`.

**Independent Test**: Set `STRUCTURED_LOGGING=true`, trigger a service-layer operation, and verify the JSON log line includes `operation` and `duration_ms` keys with correct values.

**Acceptance Scenarios**:

1. **Given** `STRUCTURED_LOGGING=true`, **When** a service-layer function in `service.py` completes, **Then** the JSON log line includes `operation` and `duration_ms` fields.
2. **Given** an exception in a service-layer call, **When** `handle_service_error()` logs the error, **Then** the JSON log line includes `error_type` set to the exception class name.
3. **Given** the `@handle_github_errors` decorator wraps a function that raises, **When** the decorator catches the exception, **Then** the log line includes `error_type`.
4. **Given** `logging_utils.py` defines a canonical `STRUCTURED_FIELDS` set, **When** StructuredJsonFormatter formats a record, **Then** it emits any field present in `STRUCTURED_FIELDS` from the record's extra dict.

---

### User Story 2 — Backend: Silence Remaining Noisy Loggers (Priority: P1)

A developer running the backend at `DEBUG` level sees excessive noise from `uvicorn`, `uvicorn.access`, `uvicorn.error`, `asyncio`, and `watchfiles` loggers. After this story, those loggers are set to `WARNING` in `config.py`, matching the existing suppression of `httpx`, `httpcore`, and `aiosqlite`.

**Why this priority**: Noisy loggers at DEBUG obscure application logs and waste log-collector bandwidth. This is a trivial, risk-free change.

**Independent Test**: Run the backend with `LOG_LEVEL=DEBUG`, verify that `uvicorn.access` and `watchfiles` messages do not appear below WARNING.

**Acceptance Scenarios**:

1. **Given** `config.py` `setup_logging()` runs, **When** the root logger is at DEBUG, **Then** `uvicorn`, `uvicorn.access`, `uvicorn.error`, `asyncio`, and `watchfiles` loggers are all at WARNING or above.

---

### User Story 3 — Backend: Add OTel Logs Bridge (Priority: P2)

An SRE operating a local OTLP collector wants to see Python log records alongside traces and metrics in the same backend. After this story, when `OTEL_ENABLED=true`, the `init_otel()` function creates a `LoggerProvider` with an `OTLPLogExporter` and attaches a `LoggingHandler` to the root logger so all stdlib log records are forwarded to the collector.

**Why this priority**: Depends conceptually on structured fields being populated (US-1) to get value from exported logs, though can be implemented independently.

**Independent Test**: Start backend with `OTEL_ENABLED=true` and a local OTLP collector, trigger a log, verify the collector receives a log record.

**Acceptance Scenarios**:

1. **Given** `OTEL_ENABLED=true`, **When** `init_otel()` completes, **Then** a `LoggingHandler` backed by `OTLPLogExporter` is attached to the root logger.
2. **Given** `OTEL_ENABLED=false` (or env var absent), **When** `init_otel()` completes, **Then** no LoggerProvider or LoggingHandler is created (zero cost).
3. **Given** the OTel logs bridge is active, **When** a structured log is emitted, **Then** the OTLP collector receives the record with `operation` and `duration_ms` attributes.

---

### User Story 4 — Frontend: Create Logger Utility (Priority: P1)

A frontend developer needs a centralized logger that gates debug output behind `import.meta.env.DEV`, always emits error/warn, redacts sensitive keys (`authorization`, `token`, `cookie`), and provides a `captureException` hook for future APM integration. After this story, `src/lib/logger.ts` exists with `logger.debug(tag, msg, ctx?)`, `logger.warn(...)`, `logger.error(...)`, and `logger.captureException(error, ctx?)`.

**Why this priority**: This is the foundation for all frontend logging improvements. Without it, Phases 5–6 cannot proceed.

**Independent Test**: Import and call `logger.debug('test', 'hello', { authorization: 'Bearer xyz' })` in a Vitest test; verify the output is suppressed in production mode and the `authorization` value is redacted in dev mode.

**Acceptance Scenarios**:

1. **Given** `import.meta.env.DEV` is `false`, **When** `logger.debug()` is called, **Then** nothing is emitted to console.
2. **Given** `import.meta.env.DEV` is `true`, **When** `logger.debug('tag', 'msg', { authorization: 'secret' })` is called, **Then** the console output shows `authorization: '[REDACTED]'`.
3. **Given** any environment, **When** `logger.error()` or `logger.warn()` is called, **Then** the message is always emitted.
4. **Given** an error, **When** `logger.captureException(error, ctx)` is called, **Then** `console.error` is invoked and the error is available for APM forwarding.

---

### User Story 5 — Frontend: Replace Raw Console Calls (Priority: P1, depends on US-4)

A security reviewer auditing the frontend finds zero raw `console.*` calls outside of tests and the logger utility itself. All 13 existing call sites have been replaced with `logger.*` equivalents, SSE/WebSocket payloads are sanitized (log event type + error code only, not user content), and the codebase passes `grep -r 'console\.\(log\|debug\|warn\|error\)' src/ --include='*.ts' --include='*.tsx'` with zero hits (excluding tests and logger.ts).

**Why this priority**: Raw console calls risk leaking user content (SSE payloads, WebSocket messages) and bypass env guards.

**Independent Test**: Run `grep -r 'console\.\(log\|debug\|warn\|error\)' src/ --include='*.ts' --include='*.tsx'` excluding tests and logger.ts; verify zero matches.

**Acceptance Scenarios**:

1. **Given** `main.tsx` global error handlers, **When** `window.onerror` fires, **Then** `logger.error('global:onerror', ...)` is called instead of `console.error`.
2. **Given** `ErrorBoundary.tsx`, **When** `componentDidCatch` fires, **Then** `logger.captureException(error, { componentStack })` is called.
3. **Given** `api.ts` SSE handlers, **When** SSE data fails to parse, **Then** `logger.debug('sse', ...)` is called with only event type and error code (no raw payload).
4. **Given** `useRealTimeSync.ts`, **When** WebSocket message parsing fails, **Then** `logger.error('websocket', ...)` is called with sanitized message (no raw content).
5. **Given** the full frontend source, **When** a console audit grep is run, **Then** zero raw `console.*` calls remain outside tests and `logger.ts`.

---

### User Story 6 — Frontend: Consolidate Error Message Utilities (Priority: P2)

A developer maintaining error handling finds a single `getErrorMessage()` function in `src/utils/errorUtils.ts` instead of three duplicates (`errMsg()` in `usePipelineConfig.ts`, `getErrorMessage()` in `useApps.ts`, `getErrorHint()` in `errorHints.ts`). The first two are consolidated; `getErrorHint()` remains separate (different purpose).

**Why this priority**: DRY improvement that reduces maintenance surface but is not blocking.

**Independent Test**: Import `getErrorMessage` from `src/utils/errorUtils.ts`, pass an `ApiError` and a plain `Error`, verify correct message extraction.

**Acceptance Scenarios**:

1. **Given** `src/utils/errorUtils.ts` exports `getErrorMessage(error, fallback)`, **When** called with an `ApiError`, **Then** it returns the API error message.
2. **Given** `usePipelineConfig.ts` previously defined inline `errMsg()`, **When** the module is loaded, **Then** it imports `getErrorMessage` from `@/utils/errorUtils`.
3. **Given** `useApps.ts` previously defined `getErrorMessage()`, **When** the module is loaded, **Then** it imports from `@/utils/errorUtils`.

---

## Scope Boundaries

### In Scope

- Backend: Canonical STRUCTURED_FIELDS set and formatter extension
- Backend: Structured extra fields on key service-layer log calls
- Backend: Silence 5 additional noisy loggers
- Backend: OTel LoggerProvider + OTLPLogExporter bridge (gated)
- Frontend: Logger utility with env gating, redaction, APM hook
- Frontend: Replace all 13 raw console.* calls
- Frontend: Consolidate duplicate error-extraction utilities

### Out of Scope

- Backend log-level reclassification (current DEBUG/INFO split is appropriate)
- Switching from stdlib logging to structlog/loguru (existing stack is solid)
- Frontend APM service integration (Phase 6 in parent issue — deferred)
- Frontend production error tracking service setup
- Backend metric/trace enhancements beyond log bridge

## Decisions

1. **Backend stays stdlib logging** — existing stack is solid; structlog/loguru would be churn.
2. **SSE/WebSocket sanitization** — log event type + error, strip raw payloads to prevent user content leakage.
3. **No backend log-level reclassification** — current DEBUG/INFO split is appropriate.
4. **`opentelemetry-exporter-otlp-proto-grpc`** — added as optional dependency, same version range as existing OTel deps.

## Edge Cases

1. OTel collector unreachable — LoggingHandler must not block or crash the application.
2. Structured fields missing from log record — formatter emits record without those keys (no KeyError).
3. Logger utility called before DOM ready — must not throw; console methods always exist.
4. Redaction of deeply nested context objects — redact only top-level keys matching sensitive patterns.
5. SSE stream with malformed JSON — log event type only, never the raw payload string.

## Assumptions

1. `STRUCTURED_LOGGING=true` environment variable controls JSON formatter activation (already implemented).
2. `OTEL_ENABLED=true` environment variable gates OTel setup (already implemented for traces/metrics).
3. The frontend uses Vite with `import.meta.env.DEV` for development mode detection.
4. Existing `useApps.test.tsx` tests cover `getErrorMessage` behavior and will be updated for new import path.
5. The 13 console.* call sites identified in the issue are current and complete.
