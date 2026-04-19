# ADR-008: Ruff BLE001 blind-except policy

**Status**: Accepted
**Date**: 2026-Q2

## Context

The backend contained ~450 `except Exception` blocks and ~10 `except Exception: pass`
blocks. Most of these follow legitimate patterns (API boundary error translation,
best-effort GitHub API wrappers, polling resilience), but without a lint gate any new
code could silently swallow arbitrary exceptions with no review signal.

## Decision

1. **Enable Ruff `BLE001`** in `pyproject.toml` to flag every `except Exception`.
2. **Enable `S110`** (try-except-pass) as a **non-waivable** rule — empty `pass`
   blocks must always be replaced with at least a `logger.debug(…, exc_info=True)`.
3. **Enable `TRY002`, `TRY003`, `TRY004`, `TRY300`, `TRY301`** for related
   exception anti-patterns; keep `TRY400` / `TRY401` off (higher noise).
4. Each surviving `except Exception` gets a **tagged noqa comment** on the same line:

   ```python
   except Exception as exc:  # noqa: BLE001 — reason: <category>
   ```

5. Tests are **exempt** from `BLE001`, `TRY003`, and `TRY301` via `per-file-ignores`.

### Reason categories

Every `# noqa: BLE001` tag must use one of these standard categories:

| Category | When to use |
|---|---|
| api boundary; re-raises as HTTP error | FastAPI endpoint catch-all around `handle_service_error` |
| api boundary; logs and returns graceful error | Endpoint returns a user-facing error message |
| best-effort GitHub API call; logs and returns default | GitHub service wrapper that logs and returns `[]` / `None` |
| startup/shutdown resilience; logs and continues | `lifespan` or middleware initialisation |
| polling resilience; logs and continues | Copilot polling loop or cycle helpers |
| orchestrator resilience; logs and continues | Workflow orchestrator error handling |
| webhook resilience; logs and continues | Webhook dispatch fallback paths |
| signal relay; logs and continues | Signal bridge / chat relay |
| graceful degradation; health-check probe | Health endpoint sub-checks |
| graceful degradation; non-critical feature probe | Optional feature detection |
| transaction rollback; re-raises after cleanup | DB transaction rollback-and-reraise |
| 3rd-party callback; unbounded input | Plugin / extension callbacks |
| background task; logs and continues | Background tasks and cleanup jobs |
| agent service resilience; logs and continues | Agent creator / provider error handling |
| AI service resilience; logs and continues | AI utility / model error handling |
| notification resilience; logs and continues | Alert dispatcher error handling |
| middleware resilience; logs and continues | Rate limiter and other middleware |
| graceful degradation; label pre-creation fallback | Label pre-creation in constants |
| graceful degradation; logging infrastructure | Logging utility error handling |
| test assertion; catches all exceptions to produce test-specific error | Test files only |

### Escape hatch

To add a new `except Exception`, a developer must:

1. Pick a category from the table above (or propose a new one via PR).
2. Add `# noqa: BLE001 — reason: <category>` on the `except` line.
3. The CI suppression guard (`check-suppressions.sh`) verifies the `— reason:` marker.

## Consequences

- **+** Every new broad-except is visible in code review with a documented justification.
- **+** Silent `pass` blocks are banned outright (`S110`), forcing at least a debug log.
- **+** Consistent log shape across the codebase improves grep-ability.
- **−** Existing code carries ~450 noqa tags — this is a one-time cost.
- **−** TRY003/TRY300 tags add some visual noise to raise statements.
