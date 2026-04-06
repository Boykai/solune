# Contract: Copilot SDK Type Stubs

**Feature**: 018-type-checking-strictness-upgrade | **Date**: 2026-04-06

> This contract defines the `.pyi` stub interface for `github-copilot-sdk` (v0.1.x).
> Stubs live in `solune/backend/src/typestubs/copilot/` and are referenced via `stubPath` in pyright config.

## Scope

Only the symbols **actually imported** in Solune's codebase are stubbed. This is not a complete SDK typing — it's a project-local compatibility layer.

### Imported Symbols Inventory

| Import Statement | File(s) | Stub Location |
|-----------------|---------|---------------|
| `from copilot import CopilotClient` | `completion_providers.py:66` | `copilot/__init__.pyi` |
| `from copilot.types import GitHubCopilotOptions, PermissionHandler` | `agent_provider.py:79`, `completion_providers.py:179`, `plan_agent_provider.py:170` | `copilot/types.pyi` |
| `from copilot.generated.session_events import SessionEventType` | `completion_providers.py:176` | `copilot/generated/session_events.pyi` |

### Stub File Structure

```
src/typestubs/
└── copilot/
    ├── __init__.pyi          # CopilotClient class
    ├── types.pyi             # GitHubCopilotOptions, PermissionHandler
    └── generated/
        └── session_events.pyi  # SessionEventType enum
```

## Stub Definitions

### `copilot/__init__.pyi`

```python
from typing import Any

class CopilotClient:
    """GitHub Copilot SDK client for completions."""
    def __init__(self, **kwargs: Any) -> None: ...
    async def get_completion(self, **kwargs: Any) -> Any: ...
```

**Accuracy requirement**: The actual `CopilotClient` methods used in `completion_providers.py` must match these signatures. Audit the usage before finalizing.

### `copilot/types.pyi`

```python
from typing import Any, Protocol
from typing_extensions import TypedDict

class GitHubCopilotOptions(TypedDict, total=False):
    """Options passed to Copilot completion requests."""
    model: str
    max_tokens: int
    temperature: float
    top_p: float
    stop: list[str]

class PermissionHandler(Protocol):
    """Protocol for permission checking in Copilot agent providers."""
    async def check_permission(self, **kwargs: Any) -> bool: ...
```

**Accuracy requirement**: Inspect actual `GitHubCopilotOptions` keys used in `agent_provider.py`, `completion_providers.py`, and `plan_agent_provider.py`. Add any missing keys.

### `copilot/generated/session_events.pyi`

```python
from enum import Enum

class SessionEventType(Enum):
    """Event types for copilot session events."""
    ...
```

**Accuracy requirement**: Check which `SessionEventType` members are accessed in `completion_providers.py` and add them.

## Validation

After creating stubs:
1. Run `uv run pyright src` — should pass with 0 errors
2. All 6 `# type: ignore[reportMissingImports]` on copilot imports should be removable
3. The `stubPath = "src/typestubs"` config must be added to `pyproject.toml [tool.pyright]`

## Maintenance

- When `github-copilot-sdk` ships `py.typed`, these stubs can be deleted and `stubPath` removed
- If new copilot SDK symbols are imported, stubs must be extended
