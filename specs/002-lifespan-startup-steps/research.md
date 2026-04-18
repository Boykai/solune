# Phase 0 Research: Refactor main.py Lifespan into src/startup/ Step Package

**Feature**: 002-lifespan-startup-steps
**Date**: 2026-04-18

This document resolves the open questions and validates the assumptions in `spec.md` and `plan.md` Technical Context. No `NEEDS CLARIFICATION` markers were present; the items below capture investigations that informed concrete design decisions.

---

## R1 — Step Protocol: class-based vs. function-based

**Decision**: Use a `typing.Protocol` with class-based steps. Each step is a class with `name: str`, `fatal: bool`, `run(ctx: StartupContext) -> Awaitable[None]`, and an optional `skip_if(ctx: StartupContext) -> bool` method.

**Rationale**: The spec explicitly requires `fatal` and `skip_if` as data attributes on steps (not hidden inside closures). A Protocol is the lightest formalism: steps don't inherit from a base class, they just satisfy the structural interface. This matches Python's duck-typing idiom and Pyright's structural subtyping. Classes are preferred over `@dataclass` wrappers because each step's `run()` method may import step-specific dependencies at the module level — a class body provides natural scoping.

**Alternatives considered**:

- **Named tuples / dataclasses with a `Callable` field**: Rejected because `run` is async and the ergonomics of `step.run(ctx)` vs `step.run_fn(ctx)` are worse. Also harder to test with `isinstance`-like protocol checks.
- **ABC base class with abstract methods**: Rejected as heavier than needed; Python Protocols are the modern idiom for structural typing and avoid the diamond problem if a step ever needs multiple protocols.
- **Decorated async functions with metadata attributes**: Rejected because `fatal` and `skip_if` would need to be monkey-patched onto functions, which is fragile and loses Pyright visibility.

---

## R2 — StartupContext: mutable dataclass vs. TypedDict vs. dict

**Decision**: Use a mutable `@dataclass` for `StartupContext`. Fields: `app: FastAPI`, `settings: Settings`, `db: aiosqlite.Connection | None`, `task_registry: TaskRegistry`, `background: list[Coroutine[Any, Any, None]]`, `shutdown_hooks: list[Callable[[], Awaitable[None]]]`.

**Rationale**: The existing lifespan function mutates `app.state` and local variables as it progresses through steps. A dataclass mirrors this pattern directly — steps can read and write fields. `db` starts as `None` and is set by the database step; downstream steps read it. `background` accumulates coroutines that the runner starts in the TaskGroup after all steps complete. `shutdown_hooks` accumulates callables that run in LIFO order during shutdown.

**Alternatives considered**:

- **TypedDict**: Rejected because TypedDict is immutable by convention (Pyright flags mutations on `TypedDict` in strict mode) and lacks method attachment points.
- **Plain dict**: Rejected — loses all type safety. The whole point of the refactor is to make startup logic easier to reason about.
- **Dependency injection container (e.g., `python-inject`)**: Rejected per Constitution V (Simplicity). The existing pattern is direct attribute access on a shared object; a DI container would be a paradigm shift with no proportionate benefit for 15 steps.

---

## R3 — StepOutcome representation

**Decision**: `StepOutcome` is a `@dataclass` with fields: `name: str`, `status: Literal["ok", "failed", "skipped"]`, `duration_ms: float`, `error: str | None`. The list of outcomes is stashed on `app.state.startup_report` after all steps complete.

**Rationale**: The spec (FR-010) requires a machine-readable startup report. A dataclass is the simplest serialisable representation. The `status` field uses a string literal union rather than an enum to keep JSON serialisation trivial (a future healthcheck endpoint can return the list as-is). `duration_ms` uses `float` because `time.perf_counter()` returns sub-millisecond precision.

**Alternatives considered**:

- **Enum for status**: Rejected — adds an import and `.value` access for no benefit; three string literals are self-documenting and JSON-friendly.
- **Exception object in the `error` field**: Rejected — exceptions are not serialisable. Storing `str(exc)` is sufficient for logging and introspection.

---

## R4 — Runner error handling: re-raise vs. aggregate

**Decision**: For fatal steps, the runner re-raises the original exception immediately (wrapping it in a `StartupError(step_name, original)` for context). For non-fatal steps, the runner logs a warning with `exc_info=True` and continues. The outcome list records all results regardless.

**Rationale**: The spec (FR-008) requires fatal steps to abort cold start by re-raising. FastAPI's lifespan protocol expects an unhandled exception to abort startup. Wrapping in `StartupError` preserves the original traceback while adding the step name for log correlation. Non-fatal steps (FR-009) exactly mirror today's `try/except` wrappers around each restore helper.

**Alternatives considered**:

- **Collect all fatal errors and raise an `ExceptionGroup`**: Rejected — a fatal step should abort immediately (no subsequent steps run), so there's at most one fatal error. `ExceptionGroup` adds complexity for a single-exception case.
- **Return a success/failure result instead of raising**: Rejected — FastAPI's lifespan protocol requires an exception to abort. Returning failure would require the caller to check and raise, which is a layer of indirection.

---

## R5 — request_id_var integration in the runner

**Decision**: The runner sets `request_id_var` to `f"startup-{step.name}"` before each step and resets it after. This replaces the per-helper `request_id_var.set/reset` dance currently repeated in `_polling_watchdog_loop`, `_session_cleanup_loop`, and `_auto_start_copilot_polling`.

**Rationale**: The spec (FR-007) requires a per-step correlation identifier. Today, three of the six helper functions manually set and reset `request_id_var` with a UUID-based token. Moving this into the runner (a) eliminates duplication across all 15 steps and (b) ensures every step — including future additions — gets correlated logs automatically.

**Implementation detail**: The runner uses `token = request_id_var.set(...)` / `request_id_var.reset(token)` in a `try/finally` block around the step execution. Background loops that continue running after startup (e.g., `_session_cleanup_loop`) set their own `request_id_var` token inside the loop body, as they do today — the runner's token only covers the initial `step.run()` call.

**Alternatives considered**:

- **Leave request_id_var management in each step**: Rejected — violates DRY. The runner is the natural central point for cross-cutting concerns.
- **Use a middleware / decorator pattern**: Rejected — unnecessary indirection for a single `set/reset` call.

---

## R6 — Shutdown hook ordering and trailing hooks

**Decision**: Shutdown hooks registered by steps (via `ctx.shutdown_hooks.append(hook)`) run in LIFO order (reverse of registration). After user-registered hooks, the runner always executes three built-in trailing hooks in fixed order: (1) drain task registry, (2) stop Copilot polling, (3) close database. Trailing hooks run even if a user hook or a fatal startup step failed.

**Rationale**: LIFO mirrors stack-unwind semantics (spec decision). The three trailing hooks correspond to the current `finally` block in lifespan and MUST run unconditionally (FR-012). Making them built-in (not registered by steps) guarantees they cannot be accidentally omitted or reordered by step authors.

**Implementation detail**: `run_shutdown(ctx)` wraps each hook in `try/except` (all hooks are `fatal=False` by definition) and logs outcomes. The trailing hooks are hard-coded in `runner.py`, not in the step list, to prevent accidental removal.

**Alternatives considered**:

- **Register trailing hooks as regular steps with fatal=True**: Rejected — a fatal shutdown hook that fails would prevent subsequent trailing hooks from running, violating FR-012.
- **atexit handlers**: Rejected — `atexit` runs after the event loop is closed; async cleanup needs to happen inside the lifespan's async context.

---

## R7 — Background loop lifecycle

**Decision**: Steps that need long-running background loops (e.g., `_session_cleanup_loop`, `_polling_watchdog_loop`) append coroutine objects to `ctx.background` during `step.run()`. After all steps complete, the runner starts them inside the existing `asyncio.TaskGroup`. The TaskGroup `yield` point (inside the lifespan) keeps loops alive until shutdown.

**Rationale**: This preserves the exact current behaviour (main.py:774–776). The TaskGroup is created in `lifespan()` (which remains in `main.py`); the runner simply populates `ctx.background` and returns the list. No change to task lifetime management (explicitly out of scope per spec).

**Edge case**: If a fatal step fails before all steps complete, `ctx.background` contains partially-accumulated coroutines. Per spec edge case #4, these MUST be discarded without execution and logged. The runner logs a warning listing the queued-but-unstarted coroutines.

**Alternatives considered**:

- **Start each loop immediately in the step's `run()` method**: Rejected — loops started outside the TaskGroup would not be managed by the same cancellation scope. This would change task lifetime semantics (out of scope).
- **Return coroutines from `step.run()` instead of appending to ctx**: Rejected — steps that don't produce background loops would need to return `None`, complicating the runner interface for no benefit.

---

## R8 — Step module naming convention

**Decision**: Step modules are named `s{NN}_{short_name}.py` where `NN` is the two-digit execution order and `short_name` is a kebab-to-underscore version of the step name. Examples: `s01_logging.py`, `s03_database.py`, `s11_copilot_polling.py`.

**Rationale**: The numeric prefix ensures file-system listing order matches execution order, which aids discoverability. The `s` prefix avoids collision with Python keywords (e.g., `logging` is a stdlib module; `s01_logging` is unambiguous). The declarative step list in `steps/__init__.py` is the authoritative execution order; file naming is a convenience, not a contract.

**Alternatives considered**:

- **No numeric prefix (alphabetical)**: Rejected — developers would need to cross-reference the step list to understand ordering.
- **Subdirectories per step**: Rejected — Constitution V (Simplicity). Each step is a single short module (~30–80 lines); a directory per step is over-engineering.
- **`step_01_`, `step_02_` prefix**: Rejected — longer prefix adds visual noise. The `s` prefix is terse and clear in context.

---

## R9 — Duplicate step name detection

**Decision**: The runner validates that all step names in the input list are unique before executing any step. If a duplicate is found, the runner raises a `ValueError` immediately (not a `StartupError` — this is a programmer error, not a runtime failure).

**Rationale**: Spec edge case #2 requires the runner to reject duplicate names at startup with a clear error. Detecting this before execution prevents confusing log entries where two steps share a name. A `ValueError` is the standard Python exception for invalid argument values.

**Alternatives considered**:

- **Allow duplicates and disambiguate with a suffix**: Rejected — silent ambiguity defeats the purpose of stable step identifiers (FR-002).
- **Detect at import time via a registry decorator**: Rejected — adds complexity. The runner already has the full list; a simple set check is O(n) and trivial.

---

## R10 — skip_if exception handling

**Decision**: If `skip_if(ctx)` raises an exception, the runner treats it as a step failure and applies the step's `fatal`/`non-fatal` policy. The step's `run()` method is NOT called.

**Rationale**: Spec edge case #1 is explicit: "the runner MUST treat this as a step failure and apply the step's fatal/non-fatal policy." A `skip_if` that throws is unexpected — it indicates a bug in the condition logic, not a transient failure. Applying the same fatal/non-fatal policy keeps the error model uniform.

**Implementation detail**: The runner wraps `skip_if(ctx)` in the same `try/except` block as `step.run(ctx)`. The outcome status is `"failed"` (not `"skipped"`), and the duration reflects the time spent in `skip_if`.

---

## R11 — Shutdown hook timeout

**Decision**: Each shutdown hook is subject to a configurable timeout (default: 30 seconds, matching the existing `task_registry.drain(drain_timeout=30.0)`). If a hook exceeds the timeout, it is cancelled and logged as failed.

**Rationale**: Spec edge case #5 requires a reasonable timeout to prevent shutdown from hanging indefinitely. 30 seconds matches the existing `drain_timeout` convention. The timeout is implemented via `asyncio.wait_for(hook(), timeout=shutdown_timeout)`.

**Alternatives considered**:

- **No timeout (rely on container orchestrator)**: Rejected — the spec explicitly requires the runner to enforce timeouts.
- **Per-hook configurable timeout**: Rejected — over-engineering for the current use case. A single default is sufficient; it can be made per-hook in a follow-up if needed.

---

## R12 — Phased delivery: step migration order

**Decision**: Follow the four-PR strategy from the issue specification:

- **PR 1**: Scaffold `src/startup/` with `protocol.py`, `runner.py`, `__init__.py`, `steps/__init__.py`. Add `tests/unit/startup/test_runner.py` with fake steps. No behaviour change in `main.py`.
- **PR 2**: Migrate steps 1–9 (logging through Sentry) into `src/startup/steps/`. `lifespan()` calls `run_startup([...])` for these steps, keeps remaining body intact. Verify existing integration tests pass.
- **PR 3**: Migrate steps 10–14 (signal WS through agent MCP sync). Move loop helpers (`_polling_watchdog_loop`, `_session_cleanup_loop`) into step modules. Replace inline `try/except` clusters with step entries.
- **PR 4**: Move `finally` block logic into `run_shutdown(hooks)` plus built-in trailing hooks. `lifespan()` shrinks to ~30 lines.

**Rationale**: This ordering minimises risk: PR 1 has zero runtime impact, PR 2 moves simple init logic, PR 3 moves complex polling logic, PR 4 completes the extraction. Each PR is independently shippable and verifiable.

**Alternatives considered**:

- **Single mega-PR**: Rejected — too large for meaningful review; a single revert would undo all work.
- **Step-by-step PRs (one per step)**: Rejected — 15 PRs is excessive overhead for reviewers. The four-PR grouping balances granularity with review burden.

---

## Open questions

None. All Technical Context entries resolved with concrete defaults above. No `NEEDS CLARIFICATION` markers remain.
