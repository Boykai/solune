# Research: Type Checking Strictness Upgrade

**Feature**: 018-type-checking-strictness-upgrade | **Date**: 2026-04-06

## R1: OpenTelemetry Protocol Inheritance for No-Op Classes

**Context**: `_NoOpTracer`, `_NoOpMeter`, `_RequestIDSpanProcessor` implement OTel protocols but lack explicit class inheritance, causing 4 `# type: ignore` comments in `otel_setup.py`.

**Decision**: Add explicit protocol base classes (`Tracer`, `Meter`, `SpanProcessor`) guarded by `TYPE_CHECKING` to preserve zero-import behavior at runtime.

**Rationale**: OTel types are only needed for static analysis. The `TYPE_CHECKING` guard ensures no runtime import penalty. This is the standard Python pattern for protocol conformance (PEP 544).

**Alternatives considered**:
- `@runtime_checkable Protocol` subclass: Rejected — adds unnecessary runtime overhead; these classes only need static type checking
- Keep suppressions with better comments: Rejected — masks potential latent bugs (e.g., missing methods on `_NoOpInstrument`)
- Full OTel imports at module level: Rejected — defeats the purpose of conditional OTel loading

**Implementation detail**: After adding `SpanProcessor` as a base class, verify `_NoOpMeter._NoOpInstrument` has all required `Instrument` methods. The OTel `Meter.create_counter()` etc. return types like `Counter`, `Histogram`, `Gauge` — confirm `_NoOpInstrument` satisfies those protocols by implementing `add()` alongside existing `set()` and `record()`.

## R2: Pydantic Settings Construction

**Context**: `Settings()` no-arg constructor triggers pyright `[call-arg]` because pydantic-settings loads field values from environment variables, not constructor arguments. 2 suppressions in `config.py:318` and `main.py:746`, plus 6 more in `test_production_mode.py`.

**Decision**: Replace `Settings()` with `Settings.model_validate({})` throughout.

**Rationale**: `model_validate({})` is a fully-typed Pydantic v2 API that achieves the same result — Pydantic populates missing fields from environment sources. Pyright understands it correctly because the method signature accepts `dict[str, Any]`.

**Alternatives considered**:
- `from_env()` classmethod factory: Rejected — adds code without benefit; `model_validate({})` is already idiomatic Pydantic
- `# type: ignore` with structured comments: Rejected — doesn't fix the root cause; new Settings() calls would need the same suppression
- `model_config = SettingsConfigDict(env_prefix=...)` changes: Not needed — config already uses env-based loading, only the call site needs updating

## R3: Copilot SDK Type Stubs

**Context**: `github-copilot-sdk` doesn't ship `py.typed` or type stubs. 6 `# type: ignore[reportMissingImports]` across `agent_provider.py`, `completion_providers.py`, `plan_agent_provider.py`.

**Decision**: Create minimal `.pyi` stubs in `src/typestubs/copilot/` covering the imported symbols. Add `stubPath` to `[tool.pyright]` in `pyproject.toml`.

**Rationale**: Authoring project-local stubs is the pyright-recommended approach for untyped third-party packages. Stubs need only declare the symbols actually imported — no need for complete library coverage.

**Alternatives considered**:
- Inline `if TYPE_CHECKING:` blocks with `Any` aliases: Rejected — doesn't provide real type safety; just moves the suppression
- Contribute stubs upstream to typeshed/copilot-sdk: Desirable long-term but doesn't help now
- `reportMissingImports = false`: Rejected — would hide legitimate missing imports across the entire project

**Required stub modules**:
1. `copilot/__init__.pyi` — `CopilotClient` class
2. `copilot/types.pyi` — `GitHubCopilotOptions` TypedDict, `PermissionHandler`
3. `copilot/generated/session_events.pyi` — `SessionEventType` enum

## R4: reasoning_effort in Project-Local Type Stubs

**Context**: `GitHubCopilotOptions` TypedDict doesn't include `reasoning_effort` key. 3 `# type: ignore[typeddict-unknown-key]` across the copilot provider files.

**Decision**: Include `reasoning_effort: str` directly in the project-local `SessionConfig` stub (`src/typestubs/copilot/types.pyi`) and `GitHubCopilotOptions` stub (`src/typestubs/agent_framework_github_copilot/__init__.pyi`). No separate `ExtendedGitHubCopilotOptions` TypedDict is needed since the stubs are project-local and we control their type surface.

**Rationale**: Since we author the stubs ourselves (R3), we can declare the full surface used by the codebase — including `reasoning_effort`. This is simpler than a TypedDict extension and avoids an extra type that consumers would need to track.

**Alternatives considered**:
- Declare `ExtendedGitHubCopilotOptions(GitHubCopilotOptions, total=False)`: Rejected — unnecessary indirection since we control the stubs; adding the key directly is simpler and more maintainable
- Use `dict[str, Any]` instead of TypedDict: Rejected — loses type safety for all other keys
- `cast()` the dict: Rejected — no better than `type: ignore`

## R5: slowapi Handler Signature Mismatch

**Context**: `main.py:746` — the `RateLimitExceeded` exception handler registered with FastAPI has a signature that pyright considers incompatible with the expected `Callable`. 1 `# type: ignore[arg-type]`.

**Decision**: Wrap the handler with a typed adapter function matching FastAPI's expected `ExceptionHandler` signature, or use an explicit `cast()` with a comment explaining the runtime compatibility.

**Rationale**: slowapi's `_rate_limit_exceeded_handler` has a slightly different signature than FastAPI expects. A thin typed wrapper is the cleanest fix.

**Alternatives considered**:
- Contribute type fixes to slowapi: Desirable long-term but slowapi hasn't released type improvements
- Inline the handler implementation: Possible but duplicates slowapi logic

## R6: githubkit Dynamic Attribute Access

**Context**: githubkit's `Response` objects have dynamically-typed data attributes. 8 module-level `# pyright: reportAttributeAccessIssue = false` directives in `github_projects/` + 1 inline in `completion_providers.py:196`.

**Decision**: Create `src/typestubs/githubkit/` stubs with a typed `Response` class that includes common attributes (`parsed_data`, `status_code`, etc.). Remove all 9 directives.

**Rationale**: githubkit returns `Response[T]` where `T` is the parsed model. Creating stubs for the `Response` class with proper generic types allows pyright to verify attribute access.

**Alternatives considered**:
- Use `getattr()` everywhere: Rejected — verbose and loses IDE autocomplete
- Keep file-level suppression: Rejected — hides real bugs in 8 entire files
- Contribute stubs upstream: githubkit is actively maintained; could PR stubs but doesn't help timeline

## R7: Frozen Dataclass Mutations in Tests

**Context**: Tests mutate frozen dataclass fields directly (4 suppressions in test files). Pyright correctly flags `result.field = value` on frozen dataclasses.

**Decision**: Use `object.__setattr__(result, 'field', value)` for in-place mutation, or `dataclasses.replace(result, field=value)` for creating new instances.

**Rationale**: `object.__setattr__()` is the idiomatic way to override frozen dataclass enforcement in test fixtures. `dataclasses.replace()` is cleaner when you need a new instance. The choice depends on whether the test needs to mutate in-place (checking state transitions) or just needs a modified copy.

**Alternatives considered**:
- Make dataclasses non-frozen for testing: Rejected — changes production code for test convenience; frozen is a design choice
- Use `unittest.mock.patch.object()`: Works but overly verbose for simple field assignments

## R8: Frontend `as any` / `as unknown as` in Production

**Context**: `useVoiceInput.ts` uses `window as any` with an `eslint-disable` (2 suppressions); `lazyWithRetry.ts` uses `ComponentType<any>` with an `eslint-disable` (1 suppression — the `eslint-disable` is the only directive, `ComponentType<any>` is the code it protects); `api.ts` uses `as unknown as ThinkingEvent` (1 suppression). Total: 4 production code suppressions (+ 2 `@ts-expect-error` in test/setup.ts covered by Step 15 = 6 frontend source total per SC-003).

**Decision**:
- **useVoiceInput.ts**: Declare `SpeechRecognitionWindow` interface extending `Window` with optional `SpeechRecognition` and `webkitSpeechRecognition` constructors
- **lazyWithRetry.ts**: Replace `ComponentType<any>` with `ComponentType<Record<string, unknown>>` or use a properly constrained generic
- **api.ts**: Add a type guard function `isThinkingEvent(parsed: unknown): parsed is ThinkingEvent` or use Zod schema validation

**Rationale**: Each fix uses the simplest correct TypeScript pattern. The SpeechRecognition interface pattern is well-documented for cross-browser Web Speech API support.

## R9: Frontend Test `as unknown as` Casts (55 instances)

**Context**: 55 test files use `as unknown as SomeType` for API mocking — consistent pattern across hooks and component tests.

**Decision**: Create typed mock factory helpers in `src/test/` that produce properly-typed mock objects. For example, `createMockResponse<T>(data: Partial<T>): T` using `satisfies` or `Partial<T> & Required<Pick<T, KeyFields>>` patterns.

**Rationale**: A shared mock helper reduces the 55 casts to a single well-typed utility. This is a common testing pattern in large React codebases with TanStack Query.

**Alternatives considered**:
- Individual `satisfies Partial<T>` at each call site: Works but doesn't reduce repetition
- Keep `as unknown as`: Rejected — masks potential test bugs when API types change
- Generate mocks from API types: Over-engineered for this codebase size

## R10: Backend Test Pyright Upgrade (Step 11)

**Context**: `pyrightconfig.tests.json` has `typeCheckingMode: "off"` and `reportInvalidTypeForm: "none"`. Tests are currently not type-checked at all.

**Decision**: Change to `typeCheckingMode: "standard"`, remove `reportInvalidTypeForm: "none"`. Fix all new errors that surface.

**Rationale**: Steps 7–10 resolve all known test suppressions. With those fixed, the test codebase should be clean enough for standard mode. This catches type bugs in tests before they become runtime failures.

**Alternatives considered**:
- `"basic"` mode first: Possible as an intermediate step, but `"standard"` matches production config
- Keep `"off"`: Rejected — tests are a significant portion of the codebase and deserve type safety
