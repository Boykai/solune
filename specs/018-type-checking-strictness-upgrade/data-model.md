# Data Model: Type Checking Strictness Upgrade

**Feature**: 018-type-checking-strictness-upgrade | **Date**: 2026-04-06

> This feature creates no new runtime data models. This document defines the **type-level entities** — stubs, extended TypedDicts, and interfaces — that replace suppression comments.

## Backend Type Stubs

### Entity: Copilot SDK Stubs (`src/typestubs/copilot/`)

These stubs provide type declarations for `github-copilot-sdk` which ships without `py.typed`.

#### `copilot/__init__.pyi`

```python
from typing import Any

class CopilotClient:
    """Minimal stub for github-copilot-sdk's CopilotClient."""
    def __init__(self, **kwargs: Any) -> None: ...
    async def get_completion(self, **kwargs: Any) -> Any: ...
```

#### `copilot/types.pyi`

```python
from typing import Any, Protocol
from typing_extensions import TypedDict

class GitHubCopilotOptions(TypedDict, total=False):
    model: str
    max_tokens: int
    temperature: float
    top_p: float
    stop: list[str]

class PermissionHandler(Protocol):
    async def check_permission(self, **kwargs: Any) -> bool: ...
```

#### `copilot/generated/session_events.pyi`

```python
from enum import Enum

class SessionEventType(Enum):
    """Stub for copilot session event types."""
    ...
```

### Entity: githubkit Stubs (`src/typestubs/githubkit/`)

#### `githubkit/__init__.pyi`

```python
from typing import Any, Generic, TypeVar

T = TypeVar("T")

class Response(Generic[T]):
    """Typed stub for githubkit Response — enables attribute access checking."""
    parsed_data: T
    status_code: int
    headers: dict[str, str]
    url: str
    content: bytes

class GitHub:
    """Minimal stub for githubkit GitHub client."""
    def __init__(self, **kwargs: Any) -> None: ...
    @property
    def rest(self) -> Any: ...
    @property
    def graphql(self) -> Any: ...
```

> **Note**: Stubs are intentionally minimal — they cover only the symbols and attributes actually used in the Solune codebase. Expand as needed when new usage is added.

### Entity: SessionConfig and reasoning_effort

**Location**: `src/typestubs/copilot/types.pyi`

The `reasoning_effort` key is included directly in the `SessionConfig` TypedDict stub rather than via an `ExtendedGitHubCopilotOptions` extension. This is simpler because the stubs are project-local and can declare the full surface used in the codebase.

```python
class SessionConfig(TypedDict, total=False):
    """Options passed to create_session."""
    model: str
    on_permission_request: Any
    system_message: dict[str, str]
    reasoning_effort: str
```

Similarly, `GitHubCopilotOptions` in `src/typestubs/agent_framework_github_copilot/__init__.pyi` includes `reasoning_effort` directly.

**Rationale**: Since we author the stubs ourselves, there's no need for a separate extension TypedDict — we control the type surface and can include all fields used by the codebase.

### Entity: OTel Protocol Classes (Modified)

These are existing classes in `otel_setup.py` that gain explicit base classes:

| Class | Base Added | Guard |
|-------|-----------|-------|
| `_RequestIDSpanProcessor` | `SpanProcessor` | `TYPE_CHECKING` |
| `_NoOpTracer` | `Tracer` | `TYPE_CHECKING` |
| `_NoOpMeter` | `Meter` | `TYPE_CHECKING` |

**Missing method audit for `_NoOpMeter._NoOpInstrument`**:
The OTel `Meter` protocol returns instruments (`Counter`, `Histogram`, `Gauge`). Ensure `_NoOpInstrument` implements:
- `set(value, attributes)` — ✅ present
- `record(value, attributes)` — ✅ present
- `add(amount, attributes)` — ❌ **MISSING** — needed for `Counter.add()`. **Latent bug** — add this method.

## Frontend Type Definitions

### Entity: SpeechRecognitionWindow

**Location**: `src/hooks/useVoiceInput.ts`

```typescript
interface SpeechRecognitionWindow extends Window {
  SpeechRecognition?: new () => SpeechRecognitionInstance;
  webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
}
```

**Replaces**: `window as any` cast (2 suppressions: `as any` + `eslint-disable`)

### Entity: Typed Test Setup Shims

**Location**: `src/test/setup.ts`

```typescript
interface CryptoShim {
  randomUUID: () => string;
  getRandomValues: <T extends ArrayBufferView>(array: T) => T;
  subtle: SubtleCrypto;
}

interface MockWebSocket {
  send: ReturnType<typeof vi.fn>;
  close: ReturnType<typeof vi.fn>;
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
  readyState: number;
  CONNECTING: 0;
  OPEN: 1;
  CLOSING: 2;
  CLOSED: 3;
}
```

**Replaces**: 2 `@ts-expect-error` comments in test setup

### Entity: ThinkingEvent Type Guard

**Location**: `src/services/api.ts`

```typescript
function isThinkingEvent(parsed: unknown): parsed is ThinkingEvent {
  return (
    typeof parsed === 'object' &&
    parsed !== null &&
    'type' in parsed &&
    (parsed as Record<string, unknown>).type === 'thinking'
  );
}
```

**Replaces**: `parsed as unknown as ThinkingEvent` cast (1 suppression)

## Configuration Changes

### pyproject.toml `[tool.pyright]`

```diff
 [tool.pyright]
 pythonVersion = "3.13"
 typeCheckingMode = "standard"
 include = ["src"]
 exclude = ["**/__pycache__", "htmlcov"]
 reportMissingTypeStubs = false
 reportMissingImports = "warning"
+stubPath = "src/typestubs"
```

### pyrightconfig.tests.json

```diff
 {
   "include": ["tests"],
   "exclude": ["**/__pycache__", "htmlcov"],
   "pythonVersion": "3.13",
-  "typeCheckingMode": "off",
-  "reportInvalidTypeForm": "none",
+  "typeCheckingMode": "standard",
+  "reportMissingTypeStubs": false,
+  "reportMissingImports": "warning",
   "executionEnvironments": [
     {
       "root": ".",
-      "extraPaths": ["src"]
+      "extraPaths": ["src", "src/typestubs"]
     }
   ]
 }
```

## Dependency Graph

```
Step 1 (OTel protocols) ──┐
Step 2 (Settings)         ├─→ Step 5 (slowapi + OTel arg)
Step 3 (Copilot stubs) ──┤
                          ├─→ Step 4 (ExtendedOptions) ─────────────┐
Step 6 (githubkit stubs) ─┘                                         │
                                                                     │
Step 7 (frozen dataclass) ─┐                                        │
Step 8 (mock overrides)    ├─→ Step 11 (pyright "standard") ──→ DONE
Step 9 (Settings tests)  ──┤                                        │
Step 10 (remaining tests) ─┘                                        │
                                                                     │
Step 12 (useVoiceInput) ──┐                                         │
Step 13 (lazyWithRetry)   ├─→ Step 16 (test as unknown as) ──→ DONE
Step 14 (api.ts)          │
Step 15 (test/setup.ts) ──┘
```
