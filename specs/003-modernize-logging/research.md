# Research: Modernize Logging Practices

## Decision 1: Define STRUCTURED_FIELDS as a canonical set in logging_utils.py

- **Decision**: Add a module-level `STRUCTURED_FIELDS: frozenset[str]` containing `{"operation", "duration_ms", "error_type", "status_code"}` at `logging_utils.py:~147`. Update `StructuredJsonFormatter.format()` to iterate `STRUCTURED_FIELDS` via `getattr(record, key, None)` and include any non-None values in the JSON output.
- **Rationale**: The formatter already checks these four fields individually (lines 164–167). Promoting them to a named set makes the contract explicit, simplifies adding future fields, and gives service-layer code a single import to reference for valid extra keys.
- **Alternatives considered**:
  - Keep ad-hoc `getattr` checks without a set — rejected because there is no discoverability for service-layer developers.
  - Use a TypedDict for extra fields — rejected because `logging.Logger.log(extra=...)` accepts `dict[str, Any]`; a TypedDict adds friction without runtime benefit.

## Decision 2: Expand structured extra fields to service-layer calls

- **Decision**: Add `extra={"operation": "<fn_name>", "duration_ms": <elapsed>}` to key log calls in `service.py` (pipelines, github_projects, tools, chores, agents), `chat_agent.py` / `ai_agent.py`, `orchestrator.py`, `pipeline.py`, and `database.py`. Add `extra={"error_type": type(exc).__name__}` to `handle_service_error()` and `@handle_github_errors`.
- **Rationale**: `github_commit_workflow.py` already uses `extra={"operation": ...}` at 5 call sites. Expanding to the remaining service layer gives APM tools filterable dimensions across all backend operations. The `duration_ms` field requires wrapping timed sections with `time.perf_counter()`.
- **Alternatives considered**:
  - A decorator that auto-injects operation/duration — rejected for Phase 1 because it adds abstraction before we know which calls benefit most. Can be introduced in a follow-up.
  - Emit every log field on every call — rejected because not all calls have meaningful duration (fire-and-forget, config loads).

## Decision 3: Silence five additional noisy loggers in config.py

- **Decision**: Add `setLevel(logging.WARNING)` for `uvicorn`, `uvicorn.access`, `uvicorn.error`, `asyncio`, and `watchfiles` immediately after the existing `httpx`/`httpcore`/`aiosqlite` lines in `config.py:~371`.
- **Rationale**: These loggers produce high-volume DEBUG/INFO output that drowns application logs. The existing pattern (`logging.getLogger("name").setLevel(logging.WARNING)`) is proven and consistent.
- **Alternatives considered**:
  - Use a loop over a list of logger names — acceptable and slightly DRYer, but the current style in config.py is individual lines; matching style avoids a refactor.
  - Set uvicorn log level via Uvicorn config instead of stdlib — rejected because it would only cover uvicorn, not asyncio/watchfiles, and the stdlib approach is uniform.

## Decision 4: Add OTel LoggerProvider with OTLPLogExporter

- **Decision**: In `otel_setup.py:init_otel()`, after the existing `TracerProvider` and `MeterProvider` setup, create a `LoggerProvider` with a `BatchLogRecordProcessor` wrapping `OTLPLogExporter()`, then attach a stdlib `LoggingHandler` to the root logger. Gate behind the existing `otel_enabled` conditional.
- **Rationale**: The `opentelemetry-sdk` `LoggerProvider` + `LoggingHandler` is the official bridge from Python stdlib logging to OTLP. It reuses the same OTLP endpoint and authentication as the existing trace exporter. BatchLogRecordProcessor provides async export with backpressure, so the application is not blocked by a slow collector.
- **Alternatives considered**:
  - `opentelemetry-exporter-otlp-proto-http` instead of gRPC — the existing trace exporter uses `opentelemetry-exporter-otlp` which bundles both; the gRPC variant is preferred for streaming and is already implied by the existing dep.
  - Custom log handler instead of official `LoggingHandler` — rejected because the official handler handles attribute mapping, severity mapping, and resource association automatically.

## Decision 5: Frontend logger utility design

- **Decision**: Create `src/lib/logger.ts` exporting a `logger` object with methods `debug(tag, msg, ctx?)`, `warn(tag, msg, ctx?)`, `error(tag, msg, ctx?)`, and `captureException(error, ctx?)`. Debug is gated by `import.meta.env.DEV`. All methods redact sensitive keys (`authorization`, `token`, `cookie`, `password`, `secret`, `key`) from context objects before emitting. `captureException` calls `console.error` and stores the error for future APM forwarding.
- **Rationale**: A thin wrapper preserves the simplicity of console calls while adding env gating, redaction, and a single integration point for future APM. The `tag` parameter enables structured filtering in browser devtools (e.g., filter by `[sse]`, `[websocket]`).
- **Alternatives considered**:
  - Use a third-party library like `loglevel` or `pino` — rejected per Constitution Principle V (Simplicity); the requirements are simple enough for a hand-rolled utility.
  - Class-based logger with instances — rejected because a singleton object is sufficient for the current scope and simpler to import.

## Decision 6: SSE/WebSocket log sanitization strategy

- **Decision**: When replacing SSE/WebSocket console calls, log only the event type, error code, and a truncated identifier (e.g., first 50 chars of error message) — never the raw payload or user-generated content.
- **Rationale**: SSE streams and WebSocket messages may contain user-authored content (chat messages, plan text). Logging raw payloads would expose PII or sensitive content in browser devtools and any future APM pipeline.
- **Alternatives considered**:
  - Full payload logging gated by DEV mode — rejected because developers may share screenshots of devtools, and PII can still leak during local testing.
  - No sanitization, rely on logger redaction — rejected because redaction targets known key names (`authorization`, `token`), not arbitrary user content in payload bodies.

## Decision 7: Consolidate error-extraction utilities

- **Decision**: Move `getErrorMessage()` from `useApps.ts:38` to `src/utils/errorUtils.ts`. Replace the inline `errMsg()` in `usePipelineConfig.ts:18` with an import of `getErrorMessage`. Keep `getErrorHint()` in `errorHints.ts` (it serves a different purpose — producing user-facing hint objects, not extracting raw messages).
- **Rationale**: `errMsg()` and `getErrorMessage()` are functionally identical (extract message from error objects with fallback). A single canonical function in a dedicated utility file follows DRY and makes discovery easier.
- **Alternatives considered**:
  - Merge all three functions — rejected because `getErrorHint()` returns a structured `ErrorHint` object (title, description, icon) while the other two return plain strings.
  - Create a new function name — rejected because `getErrorMessage` is already well-named and used in tests.
