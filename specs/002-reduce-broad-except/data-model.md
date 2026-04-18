# Phase 1 Data Model: Reduce Broad-Except + Log + Continue Pattern

**Feature**: 002-reduce-broad-except
**Date**: 2026-04-18

This feature modifies lint configuration, source-level exception handlers, and introduces a single helper method. The "entities" below are configuration records and code constructs whose shape and lifecycle the implementation must preserve.

---

## E1 — `[tool.ruff.lint]` block (in `solune/backend/pyproject.toml`)

**Storage**: TOML table starting at `pyproject.toml:85`.

**Fields** (delta only — fields not listed remain unchanged):

| Key | Pre-Workstream A | Post-Workstream A |
|---|---|---|
| `select` | `["E", "W", "F", "I", "B", "C4", "UP", "FURB", "PTH", "PERF", "RUF"]` | `["E", "W", "F", "I", "B", "BLE", "C4", "UP", "FURB", "PTH", "PERF", "RUF"]` |

**Validation rules**:

- `"BLE"` MUST appear in `select` after `"B"` and before `"C4"` (alphabetical ordering matches the existing convention).
- No entries may be added to `ignore` for BLE001 at the project level — suppressions are per-line only.
- The `ignore` list retains its existing `"E501"` entry unchanged.

**State transitions**: Single forward step (add `"BLE"` to select). Rollback is by removing the entry.

---

## E2 — `# noqa: BLE001 — reason:` inline tag (Workstream A)

**Storage**: Trailing comment on the `except Exception` line in Python source files.

**Format** (per Phase 0 research R2):

```python
except Exception:  # noqa: BLE001 — reason: <one-line human-readable justification>
    logger.warning("Non-blocking: could not configure status columns: %s", exc)
```

Or with the exception binding:

```python
except Exception as exc:  # noqa: BLE001 — reason: <one-line human-readable justification>
    logger.error("Failed to resolve repository: %s", exc)
```

**Validation rules**:

- The tag MUST follow the regex: `# noqa: BLE001\s*[—-]\s*reason:\s*.+`
- The `reason:` text MUST be non-empty. Empty reasons pass the linter (Ruff ignores text after the rule code) but violate code-review policy per spec Acceptance Scenario 3.2.
- The tag MUST appear on the same line as the `except` keyword — Ruff requires inline `# noqa` on the flagged line.
- A file MUST NOT use `# noqa: BLE001` without the `— reason:` suffix (code-review enforced, not tool-enforced).

**Lifecycle**: A tag is added during the Workstream A triage (Tagged bucket) and removed if a follow-up refactor narrows the handler or replaces it with `_best_effort()` (Workstream B).

---

## E3 — Triage bucket assignment (Workstream A)

**Storage**: No persistent record — the triage outcome is encoded in the code itself. Each `except Exception` handler resolves to exactly one of three states:

| Bucket | Code outcome | Example |
|---|---|---|
| **Narrow** | `except Exception` replaced with specific type(s) | `except aiosqlite.Error:` or `except (httpx.HTTPStatusError, httpx.TimeoutException):` |
| **Promote** | `except` block removed entirely; error propagates | Caller handles the error, or the operation should not be best-effort |
| **Tagged** | `except Exception` retained with `# noqa: BLE001 — reason:` tag | Third-party callback, asyncio.TaskGroup drain, best-effort helper body |

**Validation rules**:

- Every `except Exception` handler in `solune/backend/src/` MUST be resolved to exactly one bucket (FR-003).
- Post-triage, `uv run ruff check src/ --select BLE001` MUST report zero violations (SC-001).
- The Tagged bucket MUST contain fewer than 15% of the original ~568 handlers (SC-003), meaning fewer than ~85 tagged handlers.

**Cross-entity invariant**: After Workstream B lands, the Tagged count drops further by ~50 (the `github_projects/` handlers absorbed by `_best_effort()`).

---

## E4 — `_best_effort()` helper method (Workstream B)

**Storage**: Instance method on `_ServiceMixin` in `solune/backend/src/services/github_projects/service.py`.

**Signature** (per Phase 0 research R4):

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

**Parameters**:

| Parameter | Type | Purpose |
|---|---|---|
| `fn` | `Callable[..., Awaitable[T]]` | The async function to call (e.g., `self._rest`, `self._graphql`) |
| `*args` | `Any` | Positional args forwarded to `fn` |
| `fallback` | `T` | Value returned on failure (e.g., `[]`, `None`, `False`, `""`) |
| `context` | `str` | Human-readable description for the log message (e.g., `"REST PR search for issue #42"`) |
| `log_level` | `int` | Logging severity (default `logging.ERROR`; some sites use `logging.WARNING` or `logging.DEBUG`) |
| `**kwargs` | `Any` | Keyword args forwarded to `fn` |

**Return type**: `T` — same type as `fallback`.

**Validation rules**:

- The helper MUST catch `Exception` only (not `BaseException`) — `KeyboardInterrupt` and `SystemExit` must propagate (FR-007).
- The helper MUST log the exception with the provided `context` string and severity level (FR-009).
- The helper MUST return the provided `fallback` value on failure (FR-006).
- The helper MUST NOT re-raise the exception (by definition — this is a best-effort wrapper).
- The helper's own `except Exception` MUST carry the `# noqa: BLE001 — reason:` tag (FR-004).

**Lifecycle**: The helper is added in Workstream B. Call sites in `pull_requests.py`, `projects.py`, `copilot.py`, and `issues.py` are refactored to use it, replacing their ad-hoc try/except blocks.

---

## E5 — Existing `_with_fallback()` method (unchanged)

**Storage**: Instance method on `_ServiceMixin` in `solune/backend/src/services/github_projects/service.py` (lines 223–314).

**Purpose**: Orchestrates a primary → verify → fallback strategy chain for critical operations. This method is NOT modified by this feature (per research R10).

**Cross-entity invariant**: `_with_fallback()` and `_best_effort()` coexist on the same mixin. They serve different patterns:

- `_best_effort()`: single call, log on failure, return fallback value.
- `_with_fallback()`: multi-step strategy (primary function → optional verification → fallback function).

Call sites should use `_best_effort()` for simple best-effort wrappers and `_with_fallback()` for operations requiring a fallback strategy.

---

## E6 — Exception type hierarchy for Narrow bucket

**Storage**: Import statements and `except` clauses in narrowed handlers.

**Common narrowing targets** (from Phase 0 research R3):

| Original handler context | Narrowed exception type(s) | Import source |
|---|---|---|
| Database operations (aiosqlite) | `aiosqlite.Error` | `import aiosqlite` |
| HTTP client errors | `httpx.HTTPStatusError` | `import httpx` |
| HTTP connection failures | `httpx.ConnectError` | `import httpx` |
| HTTP timeouts | `httpx.TimeoutException` | `import httpx` |
| JSON parsing | `json.JSONDecodeError` | `import json` (stdlib) |
| File system operations | `OSError` | builtin |
| Dictionary key access | `KeyError` | builtin |
| Type/value conversion | `ValueError` | builtin |
| Async timeouts | `asyncio.TimeoutError` | `import asyncio` (stdlib) |
| GitHub API errors | `GitHubAPIError` | `from src.exceptions import GitHubAPIError` |
| githubkit request failures | `githubkit.exception.RequestFailed` | `from githubkit.exception import RequestFailed` |

**Validation rules**:

- Narrowed handlers MUST catch only the exception types that the wrapped call can actually raise.
- Union types (`except (TypeA, TypeB):` or `except TypeA | TypeB:`) are preferred over separate handlers when multiple exception types are possible from a single call.
- Narrowed handlers MUST NOT add new `# noqa: BLE001` tags — BLE001 only fires on `except Exception` and `except BaseException`, not on specific types.

---

## Cross-entity invariants

1. **Zero violations**: After Workstream A completes, `uv run ruff check src/ --select BLE001` exits with zero findings.
2. **Tagged ceiling**: `count(E2 tags) < 0.15 × 568 ≈ 85` after Workstream A.
3. **Helper exclusivity**: After Workstream B, no `except Exception` handlers remain in `pull_requests.py`, `projects.py`, `copilot.py`, or `issues.py` outside of `_with_fallback()` internals.
4. **Behavioural equivalence**: Every refactored handler (Narrow, Promote, or helper-wrapped) produces the same observable logging output and return value as the original handler (SC-006).
5. **Test suite green**: `uv run pytest` passes with zero failures after each workstream (FR-011).
