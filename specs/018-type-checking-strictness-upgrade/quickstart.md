# Quickstart: Type Checking Strictness Upgrade

**Feature**: 018-type-checking-strictness-upgrade | **Date**: 2026-04-06

> Step-by-step developer guide for implementing the type-checking strictness upgrade. Each step is independently verifiable — run the validation command after completing each step.

## Prerequisites

```bash
cd solune/backend
PATH=$HOME/.local/bin:$PATH uv sync --dev

cd solune/frontend
npm ci
```

## Validation Commands

```bash
# Backend source type check (run after each backend step)
cd solune/backend && PATH=$HOME/.local/bin:$PATH uv run pyright src

# Backend test type check (run after Steps 7-11)
cd solune/backend && PATH=$HOME/.local/bin:$PATH uv run pyright -p pyrightconfig.tests.json

# Backend unit tests (run after any backend change)
cd solune/backend && PATH=$HOME/.local/bin:$PATH uv run pytest tests/unit/ -x -q

# Frontend type check (run after each frontend step)
cd solune/frontend && npm run type-check && npm run type-check:test

# Frontend tests (run after any frontend change)
cd solune/frontend && npm run test
```

---

## Phase 1 — Backend Source Suppressions

### Step 1: OTel Protocol Inheritance (4 suppressions)

**File**: `solune/backend/src/services/otel_setup.py`

1. Expand the `TYPE_CHECKING` import block to include `SpanProcessor`:
   ```python
   if TYPE_CHECKING:
       from opentelemetry.metrics import Meter
       from opentelemetry.trace import Tracer
       from opentelemetry.sdk.trace import SpanProcessor
   ```

2. Add base class to `_RequestIDSpanProcessor`:
   ```python
   if TYPE_CHECKING:
       class _RequestIDSpanProcessor(SpanProcessor): ...
   else:
       class _RequestIDSpanProcessor: ...
   ```
   Or use the simpler `TYPE_CHECKING`-guarded inheritance pattern.

3. Add base classes to `_NoOpTracer` and `_NoOpMeter` (same pattern).

4. Add `add()` method to `_NoOpInstrument` (missing — latent bug):
   ```python
   def add(self, amount: object, attributes: object = None) -> None:
       pass
   ```

5. Remove the 4 `# type: ignore` comments on lines 70, 80, 148, 155.

**Verify**: `uv run pyright src` passes with 0 errors.

### Step 2: Pydantic Settings Construction (2 suppressions)

**Files**: `solune/backend/src/config.py:318`, `solune/backend/src/main.py`

1. Find `Settings()` calls (should be at config.py:318 and main.py — search for the exact line)
2. Replace with `Settings.model_validate({})`
3. Remove `# type: ignore` comments

**Verify**: `uv run pyright src` and `uv run pytest tests/unit/ -x -q`.

### Step 3: Copilot SDK Type Stubs (6 suppressions)

1. Create directory structure:
   ```bash
   mkdir -p src/typestubs/copilot/generated
   ```

2. Create stub files per `contracts/copilot-stubs.md`:
   - `src/typestubs/copilot/__init__.pyi`
   - `src/typestubs/copilot/types.pyi`
   - `src/typestubs/copilot/generated/session_events.pyi`

3. Before writing stubs, audit actual imports in:
   - `src/services/agent_provider.py`
   - `src/services/completion_providers.py`
   - `src/services/plan_agent_provider.py`

4. Add to `pyproject.toml [tool.pyright]`:
   ```toml
   stubPath = "src/typestubs"
   ```

5. Remove 6 `# type: ignore[reportMissingImports]` comments.

**Verify**: `uv run pyright src` passes.

### Step 4: ExtendedGitHubCopilotOptions (3 suppressions)

1. Create shared type or declare locally in each file:
   ```python
   class ExtendedGitHubCopilotOptions(GitHubCopilotOptions, total=False):
       reasoning_effort: str
   ```

2. Update type annotations where `GitHubCopilotOptions` dicts are constructed with `reasoning_effort`.

3. Remove 3 `# type: ignore[typeddict-unknown-key]` comments.

**Verify**: `uv run pyright src` passes.

### Step 5: slowapi + FastAPIInstrumentor (2 suppressions)

**Files**: `solune/backend/src/main.py`, `solune/backend/src/services/otel_setup.py`

1. For `FastAPIInstrumentor.instrument()` — should be resolved after Step 1 adds OTel protocol inheritance. Check if the `# type: ignore[call-arg]` on line 80 is still needed.

2. For the slowapi `RateLimitExceeded` handler in `main.py`:
   - Option A: Create a typed wrapper function matching `ExceptionHandler` signature
   - Option B: Use `cast(ExceptionHandler, handler)` with a comment

3. Remove remaining `# type: ignore` comments.

**Verify**: `uv run pyright src` passes.

### Step 6: githubkit Stubs (9 suppressions)

1. Create stub:
   ```bash
   mkdir -p src/typestubs/githubkit
   ```

2. Create `src/typestubs/githubkit/__init__.pyi` per `contracts/githubkit-stubs.md`.

3. Audit attribute access patterns in all 8 `github_projects/` files.

4. Remove all 8 file-level `# pyright: reportAttributeAccessIssue = false` directives.

5. Remove inline `# pyright: ignore[reportAttributeAccessIssue]` from `completion_providers.py:196`.

6. Fix any new pyright errors by adding type annotations.

**Verify**: `uv run pyright src` passes with 0 errors.

---

## Phase 2 — Backend Test Suppressions + Pyright Upgrade

### Step 7: Frozen Dataclass Mutations (4 suppressions)

**Files**: `test_agent_output.py`, `test_polling_loop.py`, `test_label_classifier.py`, `test_transcript_detector.py`

Replace:
```python
result.field = value  # type: ignore[misc]
```
With:
```python
object.__setattr__(result, "field", value)
```

### Step 8: Mock Method/Attribute Overrides (3 suppressions)

**Files**: `test_transaction_safety.py`, `test_api_board.py`

Replace direct method assignment with `patch.object()` or `MagicMock(spec=...)`.

### Step 9: Settings in Tests (6 suppressions)

**File**: `test_production_mode.py`

Apply same fix as Step 2: `Settings.model_validate({})`.

### Step 10: Remaining Test Ignores (3+ suppressions)

- `test_human_delay.py:356` — investigate `int(raw_delay)` runtime safety
- `test_pipeline_state_store.py:60` — add proper return annotation
- `test_run_mutmut_shard.py:21-23` — use `getattr()` for dynamic module attributes

### Step 11: Upgrade Test Pyright Mode

**File**: `pyrightconfig.tests.json`

```json
{
  "typeCheckingMode": "standard",
  "reportMissingTypeStubs": false,
  "reportMissingImports": "warning"
}
```

Remove `reportInvalidTypeForm: "none"`.

**Verify**: `uv run pyright -p pyrightconfig.tests.json` passes.

---

## Phase 3 — Frontend Source Suppressions

### Step 12: useVoiceInput.ts (2 suppressions)

Replace:
```typescript
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const win = window as any;
```
With:
```typescript
interface SpeechRecognitionWindow extends Window {
  SpeechRecognition?: new () => SpeechRecognitionInstance;
  webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
}

const win: SpeechRecognitionWindow = window;
```

### Step 13: lazyWithRetry.ts (2 suppressions)

Replace `ComponentType<any>` with a properly constrained generic. Remove `eslint-disable`.

### Step 14: api.ts (1 suppression)

Replace `parsed as unknown as ThinkingEvent` with a type guard.

### Step 15: test/setup.ts (2 suppressions)

Replace `@ts-expect-error` with typed shim interfaces.

**Verify**: `npm run type-check && npm run type-check:test && npm run test`

---

## Phase 4 — Frontend Test Suppressions

### Step 16: Test `as unknown as` Casts (55 suppressions)

Create typed mock factory helpers and/or use `satisfies Partial<T>` patterns across 38 test files.

**Verify**: `npm run type-check:test && npm run test:coverage`

---

## Final Verification

```bash
# Full backend validation
cd solune/backend
PATH=$HOME/.local/bin:$PATH uv run ruff check src tests
PATH=$HOME/.local/bin:$PATH uv run ruff format --check src tests
PATH=$HOME/.local/bin:$PATH uv run pyright src
PATH=$HOME/.local/bin:$PATH uv run pyright -p pyrightconfig.tests.json
PATH=$HOME/.local/bin:$PATH uv run pytest tests/unit/ -x --cov=src

# Full frontend validation
cd solune/frontend
npm run lint
npm run type-check
npm run type-check:test
npm run build
npm run test:coverage

# Grep for remaining suppressions (should be 0)
grep -rn "# type: ignore" solune/backend/src/ solune/backend/tests/
grep -rn "# pyright:" solune/backend/src/
grep -rn "@ts-expect-error" solune/frontend/src/
grep -rn "as any" solune/frontend/src/ --include="*.ts" --include="*.tsx"
grep -rn "eslint-disable.*no-explicit-any" solune/frontend/src/
```
