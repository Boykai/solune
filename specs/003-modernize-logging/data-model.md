# Data Model: Modernize Logging Practices

## 1. STRUCTURED_FIELDS (Backend)

**Purpose**: Canonical set of extra fields recognized by `StructuredJsonFormatter` and emitted into JSON log lines when present on a log record.

| Field | Type | When Set | Description |
|-------|------|----------|-------------|
| `operation` | `str` | Every key service-layer call | Identifies the logical operation (e.g., `"create_issue"`, `"get_agents"`, `"run_pipeline"`) |
| `duration_ms` | `float` | Timed operations | Wall-clock duration of the operation in milliseconds |
| `error_type` | `str` | Exception handlers | Python exception class name (e.g., `"ValueError"`, `"GithubApiError"`) |
| `status_code` | `int` | HTTP responses / API errors | HTTP status code associated with the outcome |

**Validation Rules**:
- `operation` must be a non-empty string; use `snake_case` matching the function name.
- `duration_ms` must be non-negative; computed via `time.perf_counter()` delta × 1000.
- `error_type` must be `type(exc).__name__`; never a stringified traceback.
- `status_code` must be a valid HTTP status code (100–599).

**State Transitions**: N/A — these are write-once fields emitted at log time.

**Relationships**:
- Consumed by `StructuredJsonFormatter.format()` in `logging_utils.py`.
- Forwarded to OTLP collector as log record attributes when OTel bridge is active.
- Queryable in APM dashboards (Grafana, Datadog, etc.) as structured dimensions.

---

## 2. LoggerAPI (Frontend)

**Purpose**: Public API shape of the centralized `logger` object exported from `src/lib/logger.ts`.

| Method | Signature | Behavior |
|--------|-----------|----------|
| `debug` | `(tag: string, msg: string, ctx?: Record<string, unknown>) => void` | Emits to `console.debug` only when `import.meta.env.DEV` is `true`. Context keys are redacted. |
| `warn` | `(tag: string, msg: string, ctx?: Record<string, unknown>) => void` | Always emits to `console.warn`. Context keys are redacted. |
| `error` | `(tag: string, msg: string, ctx?: Record<string, unknown>) => void` | Always emits to `console.error`. Context keys are redacted. |
| `captureException` | `(error: unknown, ctx?: Record<string, unknown>) => void` | Always emits to `console.error`. Stores error for future APM forwarding. Context keys are redacted. |

### RedactedKeys

| Key Pattern | Redaction |
|-------------|-----------|
| `authorization` | `'[REDACTED]'` |
| `token` | `'[REDACTED]'` |
| `cookie` | `'[REDACTED]'` |
| `password` | `'[REDACTED]'` |
| `secret` | `'[REDACTED]'` |
| `key` (when value looks like a credential) | `'[REDACTED]'` |

**Validation Rules**:
- `tag` is a short, kebab-case identifier (e.g., `'sse'`, `'websocket'`, `'auth'`, `'global:onerror'`).
- `msg` is a human-readable description of the event.
- `ctx` is an optional context object; top-level keys matching sensitive patterns are redacted before emission.
- Redaction is shallow (top-level keys only) to keep the utility simple.

**State Transitions**: N/A — stateless utility (except `captureException` which may accumulate errors for APM batch send in a future phase).

---

## 3. getErrorMessage (Frontend Utility)

**Purpose**: Canonical function for extracting a human-readable error message from any error shape.

| Parameter | Type | Description |
|-----------|------|-------------|
| `error` | `unknown` | The caught error (may be `ApiError`, `Error`, `string`, or any other type) |
| `fallback` | `string` | Default message returned when no message can be extracted |

**Returns**: `string` — the extracted message or fallback.

**Logic**:
1. If `error` is an `ApiError` (has `.error?.error` or `.message`): return the API error message.
2. If `error` is an `Error` instance: return `error.message`.
3. Otherwise: return `fallback`.

**Relationships**:
- Replaces inline `errMsg()` in `usePipelineConfig.ts`.
- Replaces local `getErrorMessage()` in `useApps.ts`.
- Does NOT replace `getErrorHint()` in `errorHints.ts` (different return type: `ErrorHint` object).

---

## 4. OTel LoggerProvider Configuration (Backend)

**Purpose**: Runtime configuration for the OpenTelemetry logs bridge created in `init_otel()`.

| Component | Class | Configuration |
|-----------|-------|---------------|
| `LoggerProvider` | `opentelemetry.sdk._logs.LoggerProvider` | Uses same `Resource` as `TracerProvider` |
| `BatchLogRecordProcessor` | `opentelemetry.sdk._logs.export.BatchLogRecordProcessor` | Default batch settings (512 records, 5s interval) |
| `OTLPLogExporter` | `opentelemetry.exporter.otlp.proto.grpc._log_exporter.OTLPLogExporter` | Default endpoint (`localhost:4317`) or `OTEL_EXPORTER_OTLP_ENDPOINT` |
| `LoggingHandler` | `opentelemetry.sdk._logs.LoggingHandler` | Attached to root logger; bridges stdlib → OTLP |

**Validation Rules**:
- Only created when `otel_enabled` is `True`.
- `LoggingHandler` severity maps stdlib levels to OTLP severity numbers automatically.
- If OTLP endpoint is unreachable, `BatchLogRecordProcessor` drops records after retry budget — never blocks the application.

**State Transitions**:
- `init_otel()` called → `LoggerProvider` created → `LoggingHandler` attached → logs flow to collector.
- Application shutdown → `LoggerProvider.shutdown()` flushes remaining records.
