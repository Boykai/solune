# Contract: githubkit Type Stubs

**Feature**: 018-type-checking-strictness-upgrade | **Date**: 2026-04-06

> This contract defines the `.pyi` stub interface for `githubkit` (v0.14.x).
> Stubs live in `solune/backend/src/typestubs/githubkit/` and resolve 9 `# pyright:` directives.

## Scope

The `githubkit` library returns `Response` objects whose `.parsed_data` attribute is dynamically typed based on the API endpoint called. The 8 `github_projects/` modules + 1 line in `completion_providers.py` suppress `reportAttributeAccessIssue` at the file or line level.

### Affected Files

| File | Directive | Line |
|------|-----------|------|
| `src/services/github_projects/board.py` | `# pyright: reportAttributeAccessIssue = false` | 3 |
| `src/services/github_projects/repository.py` | `# pyright: reportAttributeAccessIssue = false` | 3 |
| `src/services/github_projects/branches.py` | `# pyright: reportAttributeAccessIssue = false` | 3 |
| `src/services/github_projects/agents.py` | `# pyright: reportAttributeAccessIssue = false` | 3 |
| `src/services/github_projects/projects.py` | `# pyright: reportAttributeAccessIssue = false` | 3 |
| `src/services/github_projects/copilot.py` | `# pyright: reportAttributeAccessIssue = false` | 3 |
| `src/services/github_projects/issues.py` | `# pyright: reportAttributeAccessIssue = false` | 3 |
| `src/services/github_projects/pull_requests.py` | `# pyright: reportAttributeAccessIssue = false` | 3 |
| `src/services/completion_providers.py` | `# pyright: ignore[reportAttributeAccessIssue]` | 196 |

### Stub File Structure

```
src/typestubs/
└── githubkit/
    ├── __init__.pyi      # Response[T], GitHub, TokenAuthStrategy
    ├── exception.pyi     # RequestFailed, PrimaryRateLimitExceeded
    ├── retry.pyi         # RetryChainDecision, RETRY_RATE_LIMIT, RETRY_SERVER_ERROR
    └── throttling.pyi    # LocalThrottler
```

## Stub Definitions

### `githubkit/__init__.pyi`

```python
from typing import Any

class Response[T]:
    """Typed githubkit Response enabling attribute access on parsed_data."""
    parsed_data: T
    status_code: int
    headers: dict[str, str]
    url: str
    content: bytes

class GitHub:
    """GitHub API client."""
    def __init__(self, auth: Any = ..., **kwargs: Any) -> None: ...
    @property
    def rest(self) -> Any: ...
    @property
    def graphql(self) -> Any: ...
    async def arequest(self, method: str, url: str, **kwargs: Any) -> Any: ...
    async def async_graphql(self, query: str, **kwargs: Any) -> Any: ...
    async def __aenter__(self) -> GitHub: ...
    async def __aexit__(self, *args: Any) -> None: ...

class TokenAuthStrategy:
    def __init__(self, token: str) -> None: ...
```

### `githubkit/exception.pyi`

```python
from typing import Any

class RequestFailed(Exception):
    response: Any

class PrimaryRateLimitExceeded(RequestFailed):
    retry_after: int | None
```

### `githubkit/retry.pyi`

```python
from typing import Any

class RetryChainDecision:
    def __init__(self, *decisions: Any) -> None: ...

RETRY_RATE_LIMIT: Any
RETRY_SERVER_ERROR: Any
```

### `githubkit/throttling.pyi`

```python
class LocalThrottler:
    def __init__(self, max_concurrency: int = ..., **kwargs: object) -> None: ...
```

**Key design choices**:
- `GitHub` does NOT define `__getattr__` — this ensures pyright checks concrete attribute access
- Submodule stubs (`exception`, `retry`, `throttling`) prevent the project-local stubs from shadowing the real package's submodules
- `Response[T]` uses a generic type parameter so pyright can infer `T` from context

## Resolution Strategy

For each of the 8 `github_projects/` files:
1. Remove the line `# pyright: reportAttributeAccessIssue = false`
2. Run pyright on the file
3. Fix any remaining attribute access issues by:
   - Adding proper type annotations to response variables
   - Using `cast()` where the response type is known
   - Adding `.parsed_data` access where raw response attributes were used

For `completion_providers.py:196`:
1. Remove the inline `# pyright: ignore[reportAttributeAccessIssue]`
2. Add proper type annotation to the variable being accessed

## Validation

After creating stubs and removing directives:
1. Run `uv run pyright src` — should pass with 0 errors
2. All 9 `# pyright:` directives related to `reportAttributeAccessIssue` should be removed
3. No new `# type: ignore` or `# pyright:` comments should be added

## Maintenance

- githubkit is actively maintained; when it ships improved types, these stubs may become redundant
- If new `github_projects/` modules are added, they should use proper type annotations from the start (no `# pyright:` directives)
