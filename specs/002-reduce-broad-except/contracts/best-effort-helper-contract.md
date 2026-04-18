# Best-Effort Helper Contract

**Feature**: 002-reduce-broad-except
**Owner**: `solune/backend/src/services/github_projects/service.py` (`_ServiceMixin` class)
**Consumers**: `pull_requests.py`, `projects.py`, `copilot.py`, `issues.py`, and future GitHub-projects service modules.

This contract specifies the API surface, behaviour, and constraints of the `_best_effort()` helper introduced in Workstream B.

---

## B1 — Method signature

```python
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")

class _ServiceMixin:
    async def _best_effort(
        self,
        fn: Callable[..., Awaitable[T]],
        *args: Any,
        fallback: T,
        context: str,
        log_level: int = logging.ERROR,
        **kwargs: Any,
    ) -> T:
        """Execute *fn* and return *fallback* on failure, logging the error."""
        ...
```

### Parameter semantics

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `fn` | `Callable[..., Awaitable[T]]` | Yes | — | Async function to execute. Typically `self._rest`, `self._graphql`, or a bound method on the service. |
| `*args` | `Any` | No | — | Positional arguments forwarded to `fn`. |
| `fallback` | `T` | Yes (keyword) | — | Value returned when `fn` raises. Must match the expected return type. |
| `context` | `str` | Yes (keyword) | — | Human-readable description for the log message. Should include identifiers (e.g., issue number, PR number). |
| `log_level` | `int` | No (keyword) | `logging.ERROR` | Logging severity level. Use `logging.WARNING` for non-critical fallbacks, `logging.DEBUG` for nice-to-have operations. |
| `**kwargs` | `Any` | No | — | Keyword arguments forwarded to `fn`. |

---

## B2 — Behaviour specification

### Success path

```text
GIVEN fn(*args, **kwargs) completes without raising
WHEN _best_effort is called
THEN the return value of fn is returned to the caller
AND no log message is emitted
```

### Failure path

```text
GIVEN fn(*args, **kwargs) raises an Exception subclass
WHEN _best_effort is called
THEN the exception is caught
AND a log message is emitted at the specified log_level
AND the log message format is "{context}: {exc}"
AND the fallback value is returned to the caller
AND the exception does NOT propagate
```

### Non-catchable exceptions

```text
GIVEN fn(*args, **kwargs) raises BaseException (e.g., KeyboardInterrupt, SystemExit)
WHEN _best_effort is called
THEN the exception is NOT caught
AND the exception propagates to the caller
```

---

## B3 — Implementation exemplar

```python
async def _best_effort(
    self,
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    fallback: T,
    context: str,
    log_level: int = logging.ERROR,
    **kwargs: Any,
) -> T:
    """Execute *fn* and return *fallback* on failure, logging the error.

    This is the canonical wrapper for "best-effort" operations where
    the caller explicitly accepts that the call may fail silently.
    Non-HTTP exceptions (``KeyboardInterrupt``, ``SystemExit``) are
    never caught — only ``Exception`` subclasses.
    """
    try:
        return await fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 — reason: canonical best-effort wrapper; callers pass context
        logger.log(log_level, "%s: %s", context, exc)
        return fallback
```

---

## B4 — Call-site migration exemplar

### Before (ad-hoc handler)

```python
async def search_open_prs_for_issue(
    self, access_token: str, owner: str, repo: str, issue_number: int
) -> list[dict]:
    try:
        response = await self._rest_response(
            access_token, "GET", f"/repos/{owner}/{repo}/pulls",
            params={"state": "open", "sort": "updated", "direction": "desc"},
        )
        if response.status_code != 200:
            logger.warning("REST PR search failed with status %d for issue #%d",
                           response.status_code, issue_number)
            return []
        # ... process response ...
        return matched_prs
    except Exception as e:
        logger.error("REST PR search error for issue #%d: %s", issue_number, e)
        return []
```

### After (using _best_effort for the outer wrapper)

```python
async def search_open_prs_for_issue(
    self, access_token: str, owner: str, repo: str, issue_number: int
) -> list[dict]:
    return await self._best_effort(
        self._search_open_prs_for_issue_inner,
        access_token, owner, repo, issue_number,
        fallback=[],
        context=f"REST PR search for issue #{issue_number}",
    )

async def _search_open_prs_for_issue_inner(
    self, access_token: str, owner: str, repo: str, issue_number: int
) -> list[dict]:
    response = await self._rest_response(
        access_token, "GET", f"/repos/{owner}/{repo}/pulls",
        params={"state": "open", "sort": "updated", "direction": "desc"},
    )
    if response.status_code != 200:
        logger.warning("REST PR search failed with status %d for issue #%d",
                       response.status_code, issue_number)
        return []
    # ... process response ...
    return matched_prs
```

**Note**: When the inner logic is short (just a single `self._rest()` or `self._graphql()` call), the inner function can be an inline lambda or the base method itself:

```python
# Simple case — no inner function needed
result = await self._best_effort(
    self._graphql, access_token, SOME_QUERY, variables={"id": node_id},
    fallback=None,
    context=f"Fetch PR #{pr_number} details",
)
```

---

## B5 — Handlers NOT eligible for `_best_effort()`

The following patterns should NOT be migrated to `_best_effort()`:

1. **Cascading fallbacks** (primary → fallback strategy): Use `_with_fallback()` instead.
2. **Conservative assumptions** (return `True` on failure to avoid false negatives): These require custom logic inside the handler. Tag with `# noqa: BLE001 — reason:` instead.
3. **Retry loops** (catch, backoff, retry): These have control flow that does not fit a single-shot wrapper.
4. **Non-async handlers**: `_best_effort()` is async-only. Synchronous handlers should be narrowed or tagged.

---

## B6 — Testing

A unit test for `_best_effort()` MUST be added in `solune/backend/tests/unit/` covering:

1. **Success path**: `fn` returns a value → `_best_effort` returns that value.
2. **Failure path**: `fn` raises `ValueError` → `_best_effort` returns `fallback` and logs at the specified level.
3. **Non-catchable**: `fn` raises `KeyboardInterrupt` → exception propagates.
4. **Custom log level**: `log_level=logging.WARNING` → log message emitted at WARNING.
5. **Kwargs forwarding**: `fn` receives the correct `*args` and `**kwargs`.

---

## B7 — Scope limitation

`_best_effort()` is scoped to the `github_projects/` service layer. It is NOT intended as a general-purpose utility. Other parts of the codebase (e.g., `pipeline.py`, `chat.py`, `main.py`) should resolve their broad-except handlers via Narrow or Tagged buckets in Workstream A, not by importing this helper.

If a future feature identifies a need for a general-purpose best-effort wrapper, it should be proposed as a separate feature with its own specification.
