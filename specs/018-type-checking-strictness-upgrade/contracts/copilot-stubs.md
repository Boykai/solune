# Contract: Copilot SDK Type Stubs

**Feature**: 018-type-checking-strictness-upgrade | **Date**: 2026-04-06

> This contract defines the `.pyi` stub interface for `github-copilot-sdk` (v0.1.x) and `agent-framework-github-copilot`.
> Stubs live in `solune/backend/src/typestubs/` and are referenced via `stubPath` in pyright config.

## Scope

Only the symbols **actually imported** in Solune's codebase are stubbed. This is not a complete SDK typing — it's a project-local compatibility layer.

### Imported Symbols Inventory

| Import Statement | File(s) | Stub Location |
|-----------------|---------|---------------|
| `from copilot import CopilotClient` | `completion_providers.py:66` | `copilot/__init__.pyi` |
| `from copilot import PermissionHandler` | `agent_provider.py:79` | `copilot/__init__.pyi` (re-export from types) |
| `from copilot.types import CopilotClientOptions` | `completion_providers.py:67` | `copilot/types.pyi` |
| `from copilot.types import SessionConfig, PermissionHandler` | `completion_providers.py:179`, `plan_agent_provider.py:170` | `copilot/types.pyi` |
| `from copilot.generated.session_events import SessionEventType` | `completion_providers.py:176` | `copilot/generated/session_events.pyi` |
| `from agent_framework_github_copilot import GitHubCopilotAgent, GitHubCopilotOptions` | `agent_provider.py:78` | `agent_framework_github_copilot/__init__.pyi` |

### Stub File Structure

```
src/typestubs/
├── copilot/
│   ├── __init__.pyi          # CopilotClient, PermissionHandler re-export
│   ├── types.pyi             # CopilotClientOptions, SessionConfig, GitHubCopilotOptions, PermissionHandler
│   └── generated/
│       └── session_events.pyi  # SessionEventType enum
└── agent_framework_github_copilot/
    └── __init__.pyi          # GitHubCopilotAgent, GitHubCopilotOptions
```

## Stub Definitions

### `copilot/__init__.pyi`

```python
from typing import Any
from copilot.types import PermissionHandler as PermissionHandler

class CopilotClient:
    """GitHub Copilot SDK client for completions."""
    def __init__(self, **kwargs: Any) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def create_session(self, config: Any) -> Any: ...
    async def get_completion(self, **kwargs: Any) -> Any: ...
```

### `copilot/types.pyi`

```python
from typing import Any
from typing_extensions import TypedDict

class CopilotClientOptions(TypedDict, total=False):
    github_token: str
    auto_start: bool

class SessionConfig(TypedDict, total=False):
    model: str
    on_permission_request: Any
    system_message: dict[str, str]
    reasoning_effort: str

class GitHubCopilotOptions(TypedDict, total=False):
    model: str
    max_tokens: int
    temperature: float
    top_p: float
    stop: list[str]

class PermissionHandler:
    @staticmethod
    def approve_all(*args: Any, **kwargs: Any) -> Any: ...
    async def check_permission(self, **kwargs: Any) -> bool: ...
```

**Note**: `reasoning_effort` is included directly in `SessionConfig` rather than via a separate extension TypedDict, since we control the stubs.

### `copilot/generated/session_events.pyi`

```python
from enum import Enum

class SessionEventType(Enum):
    """Event types for copilot session events."""
    ...
```

### `agent_framework_github_copilot/__init__.pyi`

```python
from typing import Any, Generic, TypeVar
from typing_extensions import TypedDict

class GitHubCopilotOptions(TypedDict, total=False):
    system_message: dict[str, str]
    model: str
    on_permission_request: Any
    reasoning_effort: str
    # ... additional fields

class GitHubCopilotAgent(Generic[OptionsT]):
    def __init__(self, *, name: str = ..., instructions: str = ..., **kwargs: Any) -> None: ...
```

## Validation

After creating stubs:
1. Run `uv run pyright src` — should pass with 0 errors
2. All `# type: ignore[reportMissingImports]` on copilot imports should be removable
3. The `stubPath = "src/typestubs"` config must be added to `pyproject.toml [tool.pyright]`

## Maintenance

- When `github-copilot-sdk` ships `py.typed`, these stubs can be deleted and `stubPath` removed
- If new copilot SDK symbols are imported, stubs must be extended
