# Quickstart: Verifying Each PR

**Feature**: 002-lifespan-startup-steps
**Audience**: Implementer of the per-PR changes and reviewers.

This document gives copy-pasteable verification recipes for each of the four PRs. Each recipe is the minimum sequence required to satisfy the spec's Acceptance Scenarios and Success Criteria for that phase.

All commands assume `pwd == /root/repos/solune` (the workspace root) unless stated otherwise.

---

## PR 1 — Scaffold + Runner

### What ships

- `solune/backend/src/startup/__init__.py`
- `solune/backend/src/startup/protocol.py`
- `solune/backend/src/startup/runner.py`
- `solune/backend/src/startup/steps/__init__.py` (empty `STARTUP_STEPS = []`)
- `solune/backend/tests/unit/startup/__init__.py`
- `solune/backend/tests/unit/startup/conftest.py`
- `solune/backend/tests/unit/startup/test_runner.py`
- `solune/backend/tests/unit/startup/test_protocol.py`

### Verify: unit tests pass

```bash
cd solune/backend
uv run pytest tests/unit/startup/ -v
# MUST: all tests pass
# MUST: test_runner.py covers all 13 scenarios from contracts/runner-contract.md § R4
```

### Verify: no behaviour change

```bash
cd solune/backend
uv run pytest tests/ -v --timeout=60
# MUST: all existing tests still pass (this PR adds code, touches nothing)
```

### Verify: type check

```bash
cd solune/backend
uv run pyright src/startup/
# MUST: exit 0 (new code is type-clean)
```

### Verify: protocol conformance

```bash
cd solune/backend
uv run pytest tests/unit/startup/test_protocol.py -v
# MUST: runtime_checkable Protocol validates fake step instances
```

---

## PR 2 — Move Pure Init Steps (Steps 1–9)

### What ships

- `solune/backend/src/startup/steps/s01_logging.py` through `s09_sentry.py`
- `solune/backend/tests/unit/startup/test_s01_logging.py` through `test_s09_sentry.py`
- `solune/backend/src/main.py` — `lifespan()` calls `run_startup(STARTUP_STEPS[:9], ctx)` for the first nine steps, then continues with the rest of its body.

### Verify: unit tests for new steps

```bash
cd solune/backend
uv run pytest tests/unit/startup/ -v
# MUST: all step tests pass
# MUST: each step test completes in < 2 seconds (SC-001)
```

### Verify: integration tests unchanged

```bash
cd solune/backend
uv run pytest tests/integration/ -v --timeout=120
# MUST: all existing integration tests pass without modification (SC-004)
```

### Verify: step execution order preserved

```bash
cd solune/backend
uv run pytest tests/unit/startup/test_runner.py -v -k "order"
# MUST: steps execute in declared list order (SC-008)
```

### Verify: structured logs

```bash
cd solune/backend
uv run pytest tests/unit/startup/test_runner.py -v -k "log"
# MUST: each step produces one log line with step/status/duration_ms keys (SC-005)
```

### Canary: conditional skip

```bash
cd solune/backend
uv run pytest tests/unit/startup/test_s08_otel.py -v -k "skip"
# MUST: OTel step reports "skipped" when otel_enabled=False
uv run pytest tests/unit/startup/test_s09_sentry.py -v -k "skip"
# MUST: Sentry step reports "skipped" when sentry_dsn=""
```

---

## PR 3 — Move Pipeline/Polling Steps (Steps 10–14) + Background Loops (Step 15)

### What ships

- `solune/backend/src/startup/steps/s10_signal_ws.py` through `s15_background_loops.py`
- `solune/backend/tests/unit/startup/test_s10_signal_ws.py` through `test_s15_background_loops.py`
- `solune/backend/src/main.py` — `lifespan()` now calls `run_startup(STARTUP_STEPS, ctx)` for all 15 steps. The inline `try/except` clusters for polling/discovery/restore are removed.

### Verify: unit tests for new steps

```bash
cd solune/backend
uv run pytest tests/unit/startup/test_s10_signal_ws.py \
              tests/unit/startup/test_s11_copilot_polling.py \
              tests/unit/startup/test_s12_multi_project.py \
              tests/unit/startup/test_s13_pipeline_restore.py \
              tests/unit/startup/test_s14_agent_mcp_sync.py \
              tests/unit/startup/test_s15_background_loops.py -v
# MUST: all pass, each < 2 seconds
```

### Verify: non-fatal behaviour preserved

```bash
cd solune/backend
uv run pytest tests/unit/startup/test_runner.py -v -k "non_fatal"
# MUST: non-fatal step failure is logged and swallowed; subsequent steps run
```

### Verify: background loops enqueued

```bash
cd solune/backend
uv run pytest tests/unit/startup/test_s15_background_loops.py -v
# MUST: ctx.background contains exactly 2 coroutines after step runs
```

### Verify: verbatim relocation

```bash
# Diff the moved helper functions to confirm no logic changes
cd solune/backend
# _auto_start_copilot_polling body in s11 matches main.py:23-203 (minus try/except wrapper)
# _discover_and_register_active_projects body in s12 matches main.py:206-332
# _restore_app_pipeline_polling body in s13 matches main.py:335-465
# _polling_watchdog_loop body in s15 matches main.py:516-592
# _session_cleanup_loop body in s15 matches main.py:595-639
```

### Verify: integration tests still pass

```bash
cd solune/backend
uv run pytest tests/integration/ -v --timeout=120
# MUST: all pass without modification (SC-004)
```

---

## PR 4 — Shutdown Mirror

### What ships

- `solune/backend/src/startup/runner.py` — adds `run_shutdown()` implementation.
- `solune/backend/src/main.py` — `lifespan()` `finally` block replaced with `await run_shutdown(ctx)`. Function shrinks to ~30 lines.
- `solune/backend/tests/unit/startup/test_runner.py` — adds shutdown-specific tests.

### Verify: shutdown correctness

```bash
cd solune/backend
uv run pytest tests/unit/startup/test_runner.py -v -k "shutdown"
# MUST: LIFO hook order verified (SC-006 edge case)
# MUST: failed hook does not prevent subsequent hooks
# MUST: trailing hooks (drain, stop-polling, close-db) always run
```

### Verify: fatal step + shutdown

```bash
cd solune/backend
uv run pytest tests/unit/startup/test_runner.py -v -k "fatal_then_shutdown"
# MUST: fatal step aborts startup, but database close still runs (SC-006)
```

### Verify: shutdown hook timeout

```bash
cd solune/backend
uv run pytest tests/unit/startup/test_runner.py -v -k "timeout"
# MUST: hook exceeding timeout is cancelled and logged as failed
```

### Verify: main.py line count

```bash
wc -l solune/backend/src/main.py
# MUST: ≤ 250 lines (SC-002)
```

### Verify: startup package file sizes

```bash
find solune/backend/src/startup/ -name '*.py' -exec wc -l {} + | sort -n
# MUST: no single file > 120 lines (SC-003)
```

### Verify: integration tests final

```bash
cd solune/backend
uv run pytest tests/ -v --timeout=120
# MUST: all tests pass — full suite green (SC-004)
```

---

## Per-PR Success Criteria Mapping

| PR | Success Criteria Covered |
|---|---|
| 1 | SC-001 (testable steps — demonstrated with fake steps), SC-005 (structured log assertions in test_runner) |
| 2 | SC-001 (real steps testable in isolation < 2s), SC-004 (integration tests pass), SC-005 (per-step logs), SC-008 (execution order preserved) |
| 3 | SC-001, SC-004, SC-008 (all 15 steps in order) |
| 4 | SC-002 (main.py ≤ 250 lines), SC-003 (no file > 120 lines), SC-004 (full suite green), SC-006 (shutdown correctness), SC-007 (≤ 4 PRs) |
