# ADR-008: Ruff BLE001 — lint-enforced blind-except policy

**Status**: Accepted
**Date**: 2026-04-19

## Context

The backend codebase contained ~570 `except Exception` handlers across ~87 source files. Most were intentional best-effort wrappers — logging the error and continuing — but the broad catch masked genuine bugs and prevented reviewers from distinguishing intentional resilience patterns from accidental exception swallowing.

Ruff's `BLE001` rule (flake8-blind-except) flags every `except Exception` that is not suppressed with an inline `# noqa`. Enabling it gives the linter a gate: new broad-excepts fail CI unless the author explicitly justifies the handler.

## Decision

1. **Enable `BLE`** in `pyproject.toml` `[tool.ruff.lint] select` (line 92).
2. **Tag every surviving `except Exception`** with `# noqa: BLE001 — reason: <category>` using the repo's existing `reason:` suppression convention (see [Suppression Policy](../testing.md#suppression-policy)).
3. **Standardise reason categories** so tags are searchable and auditable:

   | Category | When to use |
   |----------|-------------|
   | `best-effort operation; failure logged, execution continues` | Fire-and-forget work (cache warm-up, telemetry flush, non-critical writes) |
   | `best-effort operation; returns fallback value on failure` | Helper returns a safe default on any failure |
   | `polling resilience; failure logged, polling loop continues` | Copilot polling or background polling steps |
   | `GitHub API resilience; failure logged, operation returns fallback` | GitHub REST/GraphQL calls behind `_best_effort` / `_with_fallback` |
   | `orchestrator resilience; step failure must not abort workflow` | Workflow/pipeline orchestrator steps |
   | `boundary handler; logs and re-raises as safe AppException` | API endpoint catch-all that converts unknown errors to HTTP 500 |
   | `agent operation resilience; failure logged, pipeline continues` | Agent/chat pipeline steps |
   | `signal delivery resilience; failure logged, delivery continues` | Signal bridge/chat/delivery best-effort sends |
   | `health-check endpoint; must return degraded status, never crash` | `/health` and readiness probes |
   | `mixed exception surface; operation failure is non-critical` | Multiple unrelated exception sources (e.g. JSON + I/O + HTTP) |
   | `test assertion; catches all exceptions to produce test-specific error` | Test code that intentionally catches broadly to call `pytest.fail()` or assert |
   | `asyncio gather; child exceptions unbounded` | `asyncio.gather` / `TaskGroup` drain |

4. **New code** introducing `except Exception` must either:
   - Narrow the catch to the actual exception type(s), or
   - Add a `# noqa: BLE001 — reason:` tag with a category from the table above.

## Consequences

- **+** CI now rejects silent exception swallowers — every broad catch must be justified.
- **+** Tags are greppable (`grep -rn "noqa: BLE001"`) for auditing and burn-down tracking.
- **+** The standardised category vocabulary makes it easy to find all handlers sharing a resilience pattern.
- **−** ~570 existing handlers carry `# noqa` tags, adding line noise. This is intentional: each tag is a reviewed decision, not a blanket suppression.
- **−** Developers must learn the category vocabulary; the Suppression Policy table and this ADR are the canonical references.
