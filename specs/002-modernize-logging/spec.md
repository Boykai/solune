# Feature Specification: Modernize Logging Practices

**Feature Branch**: `002-modernize-logging`  
**Created**: 2026-04-13  
**Status**: Draft  
**Input**: User description: "Modernize Logging Practices — expand backend structured logging fields, silence noisy loggers, add OTel logs bridge, create frontend logger utility, replace raw console calls, and consolidate duplicate error-message utilities."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Backend Operator Queries Structured Log Fields (Priority: P1)

An operations engineer investigating a production incident opens the APM dashboard and filters log records by `operation`, `duration_ms`, or `error_type`. Today only five log call-sites in the commit-workflow service populate these fields; the rest emit plain text messages. After this feature, every key service-layer call emits a canonical set of structured fields, enabling the engineer to quickly isolate slow operations, group errors by type, and correlate request flows across services without parsing free-text messages.

**Why this priority**: Structured fields are the foundation of all APM queries, alerting rules, and SLO dashboards. Without consistent field coverage, observability tooling is limited to keyword search across unstructured messages. This unlocks value for every subsequent phase.

**Independent Test**: Deploy the backend with `STRUCTURED_LOGGING=true`, exercise the service layer (create a chat session, run an orchestrator pipeline, trigger a database migration), and verify that JSON log output contains `operation`, `duration_ms`, and `error_type` fields in the expected records.

**Acceptance Scenarios**:

1. **Given** the backend is running with structured logging enabled, **When** a service-layer operation completes successfully, **Then** the log record includes `operation` and `duration_ms` fields with correct values.
2. **Given** a service-layer operation raises an exception, **When** the error is caught by `handle_service_error()` or the `@handle_github_errors` decorator, **Then** the log record includes an `error_type` field containing the exception class name.
3. **Given** a request passes through the chat agent, orchestrator, pipeline, or database service, **When** the operation is logged, **Then** the `operation` field uses a consistent naming convention (e.g., `"chat_agent.run"`, `"orchestrator.execute_step"`).

---

### User Story 2 — Backend Operator Silences Noisy Debug Loggers (Priority: P1)

A developer running the backend locally at DEBUG level sees hundreds of lines per second from uvicorn internals, asyncio event-loop diagnostics, and watchfiles polling. These drown out the application's own debug messages. After this feature, five additional third-party loggers are silenced to WARNING level, matching the existing pattern for httpx and httpcore. The developer can now read application logs without noise.

**Why this priority**: This is a small, zero-risk change (five `setLevel` calls) that immediately improves the developer experience for everyone running the backend locally and reduces log volume in production when DEBUG is enabled for troubleshooting.

**Independent Test**: Start the backend with `DEBUG=true`, confirm that `uvicorn`, `uvicorn.access`, `uvicorn.error`, `asyncio`, and `watchfiles` loggers no longer emit DEBUG or INFO messages while the application's own loggers still do.

**Acceptance Scenarios**:

1. **Given** the backend starts with DEBUG-level logging, **When** log output is inspected, **Then** no log records originate from `uvicorn`, `uvicorn.access`, `uvicorn.error`, `asyncio`, or `watchfiles` at DEBUG or INFO level.
2. **Given** the backend is running, **When** an actual warning or error occurs in uvicorn or asyncio, **Then** the warning or error log record is still emitted (not suppressed entirely).

---

### User Story 3 — Backend Operator Sees Logs in OTel Collector (Priority: P2)

An SRE has the OTel collector running and already sees distributed traces and metrics from the backend. After this feature, log records also appear in the collector alongside spans, enabling unified search ("show me all logs for trace ID X") and log-based alerting without a separate log aggregation pipeline.

**Why this priority**: The tracing and metrics pipelines are already live; adding the logs bridge completes the three pillars of observability. This is gated behind the existing `otel_enabled` flag, so it adds zero overhead when disabled and carries no risk to existing deployments.

**Independent Test**: Start the backend with `OTEL_ENABLED=true` and a local OTel collector. Trigger a request, then query the collector's log endpoint and confirm that application log records appear with correct severity, message, and trace correlation.

**Acceptance Scenarios**:

1. **Given** the backend starts with `OTEL_ENABLED=true` and a reachable OTel collector, **When** the application emits log records, **Then** those records appear in the collector with correct severity level, message body, and resource attributes.
2. **Given** `OTEL_ENABLED=false` (the default), **When** the application starts, **Then** no OTel log exporter is created and no additional overhead is incurred.
3. **Given** the OTel collector is temporarily unreachable, **When** the application emits logs, **Then** logs are still written to the standard output handler and the application does not crash or hang.

---

### User Story 4 — Frontend Developer Uses a Centralized Logger (Priority: P2)

A frontend developer needs to add debug logging to a new feature. Today they would add a raw `console.debug(...)` call with no environment gating, no redaction, and no APM routing. After this feature, they import a `logger` utility that automatically gates debug output to development mode, redacts sensitive keys (authorization, token, cookie) from context objects, and provides a `captureException` method for future APM forwarding.

**Why this priority**: The logger utility is a prerequisite for replacing the 13+ existing raw console calls (User Story 5) and for any future APM integration. Building the utility first establishes the contract and enables incremental adoption.

**Independent Test**: Import the logger utility in a test file, call `logger.debug(...)`, `logger.warn(...)`, `logger.error(...)`, and `logger.captureException(...)`. Verify that debug is suppressed in production mode, that sensitive keys are redacted, and that error/warn always emit.

**Acceptance Scenarios**:

1. **Given** the application is running in production mode, **When** `logger.debug(tag, message, context)` is called, **Then** nothing is emitted to the console.
2. **Given** the application is running in development mode, **When** `logger.debug(tag, message, context)` is called, **Then** the message is emitted to the console with the tag prefix.
3. **Given** a context object containing an `authorization` key, **When** any logger method is called with that context, **Then** the value of `authorization` is replaced with `[REDACTED]` in the output.
4. **Given** an error occurs, **When** `logger.captureException(error, context)` is called, **Then** the error is logged and the method is structured to allow future APM forwarding without changing the call site.

---

### User Story 5 — Frontend Codebase Has Zero Raw Console Calls (Priority: P3)

A security auditor reviews the frontend source and finds no raw `console.*` calls outside of test files. All logging flows through the centralized logger utility, ensuring consistent redaction of sensitive data, environment-appropriate output levels, and a single integration point for future APM services.

**Why this priority**: This depends on User Story 4 (the logger utility must exist first). The migration is mechanical — each call site is replaced with the equivalent logger method — but it is important for security (SSE/WebSocket payloads may contain user content) and maintainability.

**Independent Test**: Run `grep -r 'console\.\(log\|debug\|warn\|error\)' src/ --include='*.ts' --include='*.tsx'` excluding test files and confirm zero matches. Then exercise each replaced call site (trigger a global error, an SSE parse failure, a WebSocket disconnect, etc.) and confirm the logger utility handles each case correctly.

**Acceptance Scenarios**:

1. **Given** the frontend source tree (excluding test files), **When** a text search for raw `console.log`, `console.debug`, `console.warn`, or `console.error` is performed, **Then** zero matches are found.
2. **Given** an SSE stream returns an unparseable payload, **When** the parse failure is logged, **Then** only the event type and error code are included — raw payload content is not logged.
3. **Given** a WebSocket message fails to parse, **When** the error is logged, **Then** the raw message content is not included in the log output.
4. **Given** the global `window.onerror` handler fires, **When** the error is logged, **Then** it is routed through `logger.error` with the `global:onerror` tag.

---

### User Story 6 — Frontend Developer Uses a Single Error-Message Utility (Priority: P3)

A frontend developer adding error handling to a new mutation finds a single, well-documented `getErrorMessage()` function in a shared utility module. They no longer need to choose between three near-identical helper functions scattered across hook files. The consolidated utility handles API errors, plain Error objects, and unknown values with a consistent fallback pattern.

**Why this priority**: This is a code-quality improvement that reduces cognitive load and prevents subtle inconsistencies when different helpers handle edge cases differently. It is independent of the logging changes and can be delivered in parallel.

**Independent Test**: Replace all usages of the inline `errMsg()` helper with the shared `getErrorMessage()`, run the existing test suite, and confirm all tests pass with no behavior change.

**Acceptance Scenarios**:

1. **Given** the frontend codebase, **When** a developer searches for error-message extraction functions, **Then** only one canonical `getErrorMessage()` exists in a shared utility module.
2. **Given** the `errMsg()` function in `usePipelineConfig.ts` is removed, **When** all call sites are updated to use `getErrorMessage()`, **Then** all existing tests continue to pass.
3. **Given** an unknown error type (not an Error or API error), **When** `getErrorMessage(unknownValue, "fallback")` is called, **Then** the fallback string is returned.

---

### Edge Cases

- What happens when the OTel collector is unreachable at startup? The backend must start normally and logs must still flow to stdout; the OTel exporter should fail gracefully without blocking.
- What happens when structured logging is disabled (`STRUCTURED_LOGGING=false`)? Extra fields passed via `extra={...}` must not cause errors in the plain-text formatter; they are simply ignored.
- What happens when the frontend logger receives a context object with deeply nested sensitive keys? Only top-level keys matching the redaction list (authorization, token, cookie) are redacted; nested objects are not deep-scanned (document this as a known limitation).
- What happens when `logger.captureException` is called before an APM service is configured? The error is logged to the console; no exception is thrown due to the missing APM integration.
- What happens when the `errMsg()` replacement encounters an API error with a nested `error.error` structure? The consolidated `getErrorMessage()` must handle both flat Error objects and nested API error shapes.
- What happens when a third-party library (uvicorn, asyncio) emits a genuine WARNING or ERROR? Those records must still be emitted — only DEBUG and INFO levels are suppressed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Backend MUST define a canonical set of structured log fields (`operation`, `duration_ms`, `error_type`, `status_code`) and the formatter MUST emit any of these fields when present in a log record's `extra` dictionary.
- **FR-002**: Backend service-layer calls across chat agent, orchestrator, pipeline, and database services MUST include `operation` and `duration_ms` structured fields in key log records.
- **FR-003**: Backend error handlers (`handle_service_error()` and the `@handle_github_errors` decorator) MUST include `error_type` (exception class name) in log records.
- **FR-004**: Backend MUST suppress DEBUG and INFO log output from `uvicorn`, `uvicorn.access`, `uvicorn.error`, `asyncio`, and `watchfiles` loggers while still allowing WARNING and above.
- **FR-005**: Backend MUST bridge log records to the OTel collector when the `otel_enabled` flag is true, forwarding severity, message, and resource attributes.
- **FR-006**: Backend OTel logs bridge MUST be gated behind the existing `otel_enabled` flag with zero additional overhead when disabled.
- **FR-007**: Backend OTel logs bridge MUST fail gracefully (no crash, no hang) when the collector is unreachable.
- **FR-008**: Frontend MUST provide a centralized logger utility with `debug(tag, message, context?)`, `warn(tag, message, context?)`, `error(tag, message, context?)`, and `captureException(error, context?)` methods.
- **FR-009**: Frontend logger `debug()` method MUST be gated by the development environment flag; `error()` and `warn()` MUST always emit.
- **FR-010**: Frontend logger MUST redact values of sensitive keys (`authorization`, `token`, `cookie`) in context objects before emitting.
- **FR-011**: Frontend logger MUST include unit tests covering environment gating, redaction, and all public methods.
- **FR-012**: All raw `console.log`, `console.debug`, `console.warn`, and `console.error` calls in frontend source files (excluding tests) MUST be replaced with the centralized logger utility.
- **FR-013**: SSE and WebSocket log call sites MUST sanitize payloads to log only event type and error code — raw user content MUST NOT be logged.
- **FR-014**: Frontend MUST consolidate duplicate error-message extraction functions (`errMsg()` and `getErrorMessage()`) into a single shared utility.
- **FR-015**: The `getErrorHint()` function MUST remain separate (it serves a different purpose — user-facing recovery suggestions, not message extraction).

### Key Entities

- **Structured Log Record**: A JSON log entry emitted by the backend formatter, containing mandatory fields (timestamp, level, message, logger, request_id) and optional structured fields (operation, duration_ms, error_type, status_code).
- **Logger Utility**: A frontend module providing environment-aware, redaction-capable logging methods with a consistent interface for all application logging.
- **Error Message Utility**: A shared frontend function that extracts a human-readable error message from heterogeneous error types (Error, API error, unknown) with a fallback.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of key backend service-layer operations (chat agent, orchestrator, pipeline, database) emit `operation` and `duration_ms` structured fields — verified by running with `STRUCTURED_LOGGING=true` and inspecting JSON output.
- **SC-002**: All backend error-handling paths emit `error_type` in the log record — verified by triggering known error conditions and inspecting output.
- **SC-003**: Zero DEBUG or INFO log records from `uvicorn`, `uvicorn.access`, `uvicorn.error`, `asyncio`, or `watchfiles` appear in backend log output at any application log level.
- **SC-004**: When OTel is enabled with a reachable collector, log records appear alongside trace spans in the collector — verified by querying the collector after a test request.
- **SC-005**: Zero raw `console.log`, `console.debug`, `console.warn`, or `console.error` calls exist in frontend source files (excluding tests) — verified by automated grep.
- **SC-006**: Frontend logger utility test suite achieves 100% branch coverage for environment gating, redaction, and all public methods.
- **SC-007**: Only one canonical `getErrorMessage()` function exists in the frontend codebase — verified by searching for duplicate error-extraction helpers.
- **SC-008**: All existing backend tests (pytest), linting (ruff), and type checking (pyright) pass after changes.
- **SC-009**: All existing frontend tests (npm test), linting (eslint), and type checking pass after changes.
- **SC-010**: Both Docker images build cleanly after all changes.

## Assumptions

- The backend will continue to use Python's stdlib `logging` module. No migration to structlog, loguru, or other logging frameworks is planned — the existing stack is mature.
- The `StructuredJsonFormatter` already handles the `extra` dictionary correctly for known fields; the implementation will extend the canonical field set without breaking existing behavior.
- SSE/WebSocket sanitization policy: log the event type and error code only; strip raw payloads to prevent user content leakage. This is a security decision, not a clarification item.
- The frontend logger's `captureException` method will initially log to the console. APM forwarding is a future enhancement that will not require call-site changes.
- The OTel logs bridge will use the same OTLP gRPC exporter endpoint already configured for traces and metrics.
- The `getErrorHint()` function in `errorHints.ts` is intentionally distinct from `getErrorMessage()` — it maps errors to user-facing recovery suggestions and will not be consolidated.
- Backend log-level assignments (DEBUG vs. INFO) for existing log calls are appropriate and will not be reclassified as part of this feature.
- The five additional noisy loggers to silence (`uvicorn`, `uvicorn.access`, `uvicorn.error`, `asyncio`, `watchfiles`) are safe to suppress at DEBUG/INFO level based on observed behavior in development and production environments.

## Dependencies

- **OTel logs bridge** depends on the `opentelemetry-exporter-otlp-proto-grpc` package being added to backend optional dependencies.
- **Frontend console replacement** (User Story 5) depends on the logger utility (User Story 4) being implemented first.
- All other user stories are independent and can be developed in parallel.
