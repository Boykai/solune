# Research: Linting Clean Up

**Feature**: 004-linting-cleanup | **Date**: 2026-04-02
**Purpose**: Resolve all NEEDS CLARIFICATION items and document resolution strategies for each suppression category.

## 1. Suppression Inventory (Verified Counts)

### Backend Source (`solune/backend/src/`)

| Category | Count | Files |
|----------|-------|-------|
| `asyncio.Task` type-arg | 7 | `task_registry.py` (5), `model_fetcher.py` (1), `github_projects/service.py` (1) |
| Cache generic return-value | 8 | `cache.py` (6), `utils.py` (1), `github_projects/service.py` (1) |
| Optional/vendor imports | 5 | `completion_providers.py` (4), `agent_provider.py` (1) |
| OTel typing stubs | 7 | `otel_setup.py` (7) |
| pyright file-level directives | 9 | `github_projects/` (8 modules), `completion_providers.py` (1 inline) |
| Config/dynamic boundaries | 5 | `config.py` (1), `logging_utils.py` (3), `workflow_orchestrator/config.py` (1) |
| Row indexing / dict ops | 6 | `metadata_service.py` (3), `agents/service.py` (1), `tools/service.py` (1), `main.py` (1) |
| Assignment / return type | 4 | `api/chat.py` (2), `api/workflow.py` (1), `completion_providers.py` (1) |
| **Total** | **55** | **20 files** (46 `type: ignore` + 9 `pyright:` directives) |

### Backend Tests (`solune/backend/tests/`)

| Category | Count | Files |
|----------|-------|-------|
| `Settings()` call-arg | 6 | `test_production_mode.py` (6) |
| Fake/mock `attr-defined` | 9 | `test_metadata_service.py` (8), `test_api_board.py` (1) |
| `LogRecord` dynamic attrs | 5 | `test_logging_utils.py` (5) |
| Frozen/readonly field mutation | 4 | `test_polling_loop.py` (1), `test_transcript_detector.py` (1), `test_agent_output.py` (1), `test_template_files.py` (1) |
| `method-assign` on mocks | 2 | `test_transaction_safety.py` (2) |
| TypedDict update | 1 | `test_pipeline_state_store.py` (1) |
| `retry_after` attr | 1 | `test_api_board.py` (1) |
| **Total** | **28** | **10 files** |

### Frontend Production (`solune/frontend/src/` excluding tests)

| Category | Count | Files |
|----------|-------|-------|
| `as unknown as` casts | 5 | `api.ts` (1), `AgentColumnCell.tsx` (2), `McpSettings.tsx` (2) |
| `eslint-disable` exhaustive-deps | 6 | `ChatInterface.tsx`, `UploadMcpModal.tsx`, `AgentChatFlow.tsx`, `ChoreChatFlow.tsx`, `AddChoreModal.tsx`, `ModelSelector.tsx` |
| `eslint-disable` jsx-a11y | 4 | `AddAgentPopover.tsx` (1), `AgentIconPickerModal.tsx` (1), `AgentPresetSelector.tsx` (2) |
| `eslint-disable` no-explicit-any | 2 | `useVoiceInput.ts` (1), `lazyWithRetry.ts` (1) |
| `eslint-disable` exhaustive-deps (documented) | 1 | `useRealTimeSync.ts` (1) |
| **Total** | **18** | **13 files** |

### Frontend Tests (`*.test.ts`, `*.test.tsx`, `src/test/setup.ts`)

| Category | Count | Files |
|----------|-------|-------|
| `@ts-expect-error` WebSocket/crypto | 5 | `setup.ts` (2), `useRealTimeSync.test.tsx` (3) |
| `as unknown as` mock API casts | 34 | 28 hook test files (see inventory) |
| `as unknown as` other test mocks | 7 | `api.test.ts` (2), `useBuildProgress.test.ts` (1), `useCyclingPlaceholder.test.ts` (2), `useVoiceInput.test.ts` (2) |
| `as unknown as` type erasure | 5 | Various test files for null/mock object typing |
| **Total** | **51** | **~35 files** |

### E2E / Out of Scope

| Item | Count | Disposition |
|------|-------|-------------|
| `eslint-disable` in `e2e/fixtures.ts` | 1 | Keep — legitimate Playwright fixture pattern, not authored test code |
| `pyright: reportAttributeAccessIssue=false` in `github_projects/` | 8 | In scope — replace with narrower per-line suppressions or proper typing |

---

## 2. Resolution Strategies

### Decision: `asyncio.Task` Type Arguments (7 instances)

**Chosen approach**: Use `asyncio.Task[None]` for fire-and-forget coroutines and `asyncio.Task[T]` where the return type is known.

- **Rationale**: Python 3.13 fully supports `asyncio.Task[T]` generics. The `# type: ignore[type-arg]` comments exist because the original code used bare `asyncio.Task` without the type parameter. Adding the explicit type argument satisfies Pyright without changing runtime behaviour.
- **Alternatives considered**: (1) Using `asyncio.Task[Any]` — rejected because it defeats the purpose of type checking. (2) Leaving bare `asyncio.Task` and configuring Pyright to suppress — rejected because it hides real errors.

### Decision: Cache Generic Return Values (8 instances)

**Chosen approach**: Add explicit `TypeVar` bounds or `cast()` at cache entry/exit points with narrowing assertions.

- **Rationale**: Cache methods store `object` and return `object`, but callers know the concrete type. Using `typing.cast()` at the call site with a comment explaining the cache contract is the minimal, safe change. Alternatively, the cache class itself can be made generic with `Generic[V]` if the pattern is shared enough.
- **Alternatives considered**: (1) Making `LRUCache`/`TTLCache` fully generic — viable and preferred if implementation allows; adds compile-time safety. (2) Keeping `# type: ignore` — rejected per spec.

### Decision: Optional/Vendor Import Suppressions (5 instances)

**Chosen approach**: Use `TYPE_CHECKING` guard with conditional import and `if TYPE_CHECKING: from copilot import ...` to satisfy Pyright, while keeping runtime import inside the function. For `reportMissingImports`, add a narrow `# pyright: ignore[reportMissingModuleSource]` only if stubs are truly unavailable, with an explanatory comment.

- **Rationale**: The `copilot` and `openai`/`azure` SDK imports are optional runtime dependencies. Using `TYPE_CHECKING` for the type-level import and keeping the runtime `try/except` or conditional import is the standard Python pattern. Per FR-013, if stubs genuinely don't exist, the narrowest possible suppression with a reason comment is acceptable.
- **Alternatives considered**: (1) Writing custom `.pyi` stub files — possible but high maintenance for rapidly evolving SDKs. (2) Using `Any` aliases — rejected because it hides the real interface.

### Decision: OTel Typing Stubs (7 instances in `otel_setup.py`)

**Chosen approach**: Add proper type annotations to the `_RequestIDSpanProcessor` methods and the `_NoOpTracer`/`_NoOpMeter` stubs. Use `opentelemetry` type stubs (available via `opentelemetry-api` package types) or add a minimal local protocol.

- **Rationale**: OpenTelemetry packages ship with py.typed markers. The `no-untyped-def` errors can be fixed by adding `-> None` return annotations and proper parameter types. The `return-value` errors on `_NoOpTracer` / `_NoOpMeter` can be fixed by having them inherit from the correct abstract base or by using `typing.cast()`.
- **Alternatives considered**: (1) File-level `# pyright: reportGeneralClassIssues=false` — rejected because it suppresses too broadly.

### Decision: `pyright: reportAttributeAccessIssue=false` File-Level Directives (8 files)

**Chosen approach**: Remove file-level directives. These files use the PyGithub library whose types are well-defined. If specific attribute accesses are genuinely missing from stubs, use narrow per-line `# pyright: ignore[reportAttributeAccessIssue]` with a comment linking to the PyGithub issue.

- **Rationale**: File-level suppressions hide all attribute access errors in the entire module. Narrowing to per-line keeps the rest of the file checked. Most attribute accesses should resolve correctly with current PyGithub types.
- **Alternatives considered**: (1) Keeping file-level — rejected per FR-005. (2) Writing `.pyi` overrides — overkill when per-line works.

### Decision: Config / Dynamic Boundary Suppressions (5 instances)

**Chosen approach**:
- `config.py` `Settings()`: Pydantic v2 `model_config` properly declares env loading; use `# pyright: ignore[reportCallIssue]` narrowed to the specific Pydantic pattern, or add a `@classmethod` factory.
- `logging_utils.py` `record.request_id`: Create a `RequestIdLogRecord` protocol extending `logging.LogRecord` with the `request_id` attribute.
- `workflow_orchestrator/config.py`: Use a proper setter or `object.__setattr__` for frozen model fields.

- **Rationale**: Each boundary has a distinct root cause. Pydantic settings use env-based construction that Pyright can't verify. LogRecord extension is a well-known pattern needing a protocol. Frozen model mutation needs explicit override.
- **Alternatives considered**: (1) Global `reportGeneralClassIssues` suppression — rejected as too broad.

### Decision: Backend Test Suppressions (28 instances)

**Chosen approach**:
- `Settings()` calls (6): Use `model_construct()` or explicitly pass required fields for test instances.
- `attr-defined` on fakes (9): Create typed `FakeCache` / `FakePipelineState` protocol classes that declare the test-specific attributes.
- `LogRecord` attrs (5): Reuse the `RequestIdLogRecord` protocol from source cleanup.
- Frozen field mutations (4): Use `model_construct()` or `object.__setattr__()` with a typed helper.
- `method-assign` on mocks (2): Use `unittest.mock.patch.object()` instead of direct assignment.
- TypedDict / other (2): Use `TypedDict` spread or `dict` literal with explicit types.

- **Rationale**: Test code benefits from the same type safety as production code. Typed fakes catch interface drift between tests and production. The `model_construct()` pattern is Pydantic's official way to create instances without validation.
- **Alternatives considered**: (1) Using `typing.cast()` everywhere — rejected because it doesn't catch interface changes.

### Decision: Frontend `as unknown as` in Production (5 instances)

**Chosen approach**:
- `api.ts` `ThinkingEvent` cast: Add a type guard function `isThinkingEvent(parsed)` that narrows the type.
- `AgentColumnCell.tsx` dnd-kit attributes/listeners: Declare a `SortableItemProps` interface matching dnd-kit's actual types and use it.
- `McpSettings.tsx` error shape: Create a `ServerErrorShape` type with optional `detail` field and use a type guard.

- **Rationale**: Type guards are the TypeScript-idiomatic way to narrow unknown types. They provide runtime safety alongside compile-time correctness.
- **Alternatives considered**: (1) Using `satisfies` operator — doesn't work for narrowing unknowns. (2) Extending API error types — may be cleaner for the error case.

### Decision: Frontend `eslint-disable` Suppressions (13 instances in production)

**Chosen approach**:
- `react-hooks/exhaustive-deps` (6): Review each case individually. Use `useCallback`/`useMemo` where appropriate, or document with `// deps are stable` comment alongside narrowed disable.
- `jsx-a11y/*` (4): Keep narrowed — these are intentional UX decisions (autofocus, click handlers on presentational wrappers). Document with reason.
- `@typescript-eslint/no-explicit-any` (2): Replace `any` with proper types (`SpeechRecognition` interface, bounded generic).

- **Rationale**: Hook dependency suppressions need case-by-case review — some are correct (stable refs), others hide bugs. Accessibility suppressions are UX decisions that should be kept but documented. `any` can be eliminated with proper typing.
- **Alternatives considered**: (1) Blanket removal of all eslint-disable — rejected because some (jsx-a11y) are intentional design choices.

### Decision: Frontend Test `as unknown as` (41 instances)

**Chosen approach**: Extend `createMockApi()` in `src/test/setup.ts` to cover all API namespaces used in tests. Each hook test then uses the mock factory instead of manual `as unknown as` casts. For non-API mocks (WebSocket, MediaDevices, etc.), create typed mock factories in `src/test/` helpers.

- **Rationale**: The `createMockApi()` pattern already exists and covers several API namespaces. Extending it to cover all namespaces eliminates the most common cast pattern (34 of 41 instances). The remaining 7 instances need individual typed mock helpers.
- **Alternatives considered**: (1) Using `vi.mocked()` everywhere — doesn't help with namespace mocks. (2) Keeping casts in tests — rejected per spec.

### Decision: Test Type-Check Configuration

**Chosen approach**:
- **Backend**: Add `tests/` to pyright `include` alongside `src/`, or create a second pyright config section for tests. Use a separate CI step: `uv run pyright tests`.
- **Frontend**: Create `tsconfig.test.json` extending `tsconfig.json` that includes test files and removes the test exclusions. Add `npm run type-check:test` script. Wire into CI as a separate step.

- **Rationale**: Separate configs keep the existing source type-check unchanged while adding test coverage. Separate CI steps provide independent failure reporting per FR-003.
- **Alternatives considered**: (1) Single combined config — rejected because it changes existing gate behaviour and may surface too many issues at once. (2) Vitest type-checking — Vitest doesn't do full type checking.

---

## 3. Dependency and Ordering Analysis

### Phase Dependencies

```text
Phase 1 (P1: Gate Expansion)
  └── No dependencies — establishes infrastructure
Phase 2 (P2: Backend Source Cleanup)
  └── Depends on Phase 1 — needs gate to verify cleanup
Phase 3 (P3: Backend Test Cleanup)
  └── Depends on Phase 2 — reuses typed helpers from source cleanup
  └── Depends on Phase 1 — needs test gate to verify
Phase 4 (P4: Frontend Source Cleanup)
  └── Depends on Phase 1 — needs gate infrastructure pattern
Phase 5 (P5: Frontend Test Cleanup)
  └── Depends on Phase 4 — reuses typed patterns from source cleanup
  └── Depends on Phase 1 — needs test gate to verify
Phase 6 (Guardrails & Docs)
  └── Depends on all previous phases — validates complete state
```

### Risk Areas

| Risk | Mitigation |
|------|-----------|
| Removing a suppression exposes a runtime bug | Fix in the same change set (FR-010); run full test suite after each file |
| Third-party SDK lacks type stubs | Use narrowest possible suppression per FR-013 with documented reason |
| Test type-check gate reveals hundreds of errors | Phase 1 establishes gate but allows initial failures; Phase 3/5 clean them |
| dnd-kit types are inaccurate | Check latest @dnd-kit/sortable type definitions; may need local augmentation |
| `react-hooks/exhaustive-deps` removal causes infinite re-render | Review each case with runtime testing; keep narrowed disable if correct |
