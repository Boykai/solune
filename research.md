# Research: Harden Phase 3 — Code Quality & Tech Debt

**Feature**: Harden Phase 3 | **Date**: 2026-04-10 | **Plan**: [plan.md](plan.md)

## R1: Module-Level Singleton Pattern in GitHubProjectsService

### Decision

Retain the module-level singleton instance but remove the deferred-TODO comments. Migrate all API route files (11) to use the existing `get_github_service(request)` accessor via FastAPI `Depends()`. Non-request consumers (background tasks, polling loops, orchestrator) continue importing the singleton directly — this is the designed fallback path in the accessor.

### Rationale

- The accessor pattern already exists in `dependencies.py` (lines 33–42) and is registered on `app.state` in `main.py` (line 597).
- 11 API route files can trivially switch to `Depends(get_github_service)` — this is a mechanical refactor.
- 6 non-request files (signal_bridge, signal_chat, copilot_polling/*, workflow_orchestrator) have no HTTP request context. Forcing them through app.state would require threading the app instance through multiple layers — complexity that contradicts Constitution Principle V (Simplicity).
- The TODO comments originally deferred this to a follow-up PR (FR-008). Phase 3 is that follow-up.

### Alternatives Considered

1. **Full app-instance threading**: Pass `app` or `app.state` to every background task constructor. Rejected because it couples background services to the ASGI lifecycle, adds 15+ constructor parameter changes, and gains no testability benefit over the accessor pattern.
2. **ContextVar-based injection**: Store the service in an `asyncio.ContextVar` set at startup. Rejected because ContextVars require careful lifecycle management in background tasks and add cognitive overhead without clear benefit over the existing fallback pattern.
3. **Remove singleton entirely; always create fresh**: Rejected because `GitHubProjectsService` holds cached state (rate limits, inflight GraphQL dedup) that must be shared across all callers.

---

## R2: Pre-release Dependency Upgrade Landscape

### Decision

Upgrade each dependency individually in order of risk (lowest first). Pin to the latest available version at implementation time. For `github-copilot-sdk` v2 (package rename to `copilot-sdk`), perform a full import audit before upgrading.

### Rationale

- All 7 pre-release packages are in active development. Upgrading to the latest available version (GA preferred, latest beta acceptable) reduces the risk of hitting known-fixed bugs and aligns with upstream support timelines.
- The `github-copilot-sdk` → `copilot-sdk` rename is the highest-risk change because it requires updating every Python import that references the old package name.
- `agent-framework-*` packages are tightly coupled (core + azure-ai + github-copilot); they should be upgraded together in a single commit.
- `opentelemetry-instrumentation-*` packages follow the OpenTelemetry release cadence and should be upgraded together.

### Alternatives Considered

1. **Batch all upgrades in one commit**: Rejected because a single failing package would block the entire upgrade and make bisection difficult.
2. **Wait for all packages to reach GA**: Rejected because some packages (especially agent-framework-*) may not reach GA soon, and staying on older betas increases the risk of encountering known-fixed issues.
3. **Fork or vendor pre-release packages**: Rejected as unnecessary maintenance burden.

---

## R3: Stryker Config Consolidation Strategy

### Decision

Consolidate the 4 shard config files into the base `stryker.config.mjs` using a `STRYKER_SHARD` environment variable to select the shard. Delete the 4 separate shard config files.

### Rationale

- All 4 shard configs follow an identical pattern: spread the base config, override `mutate` and `htmlReporter.fileName`. This duplication is a maintenance risk — changes to shared settings (thresholds, timeouts, concurrency) must be replicated 5 times.
- A single config with env-var sharding is simpler, reduces file count, and makes the shard definitions discoverable in one place.
- The CI workflow (`mutation-testing.yml`) already uses a matrix strategy with shard names — switching from `-c stryker-{shard}.config.mjs` to `STRYKER_SHARD={shard} stryker run` is a one-line change per matrix entry.

### Alternatives Considered

1. **Keep separate configs (status quo)**: The current pattern works and is explicit. Rejected only because the consolidation is specifically requested in the issue (Task 3.3) and reduces maintenance surface.
2. **Use Stryker's built-in `--mutate` CLI flag**: Each npm script would pass `--mutate` inline. Rejected because the hooks-general shard requires complex negation patterns that are unwieldy on the command line.
3. **Stryker plugin/preset pattern**: Create a shared preset module. Rejected as over-engineering for 4 shard definitions.

---

## R4: Plan-Mode Orphaned Chat History Status

### Decision

No code changes required. Both plan-mode endpoints already persist user messages after the `get_chat_agent_service()` availability check. Add a verification test to confirm the behavior and prevent regression.

### Rationale

- `send_plan_message` (chat.py:2010–2024): The `get_chat_agent_service()` call is in a try/except that returns 503 before any message persistence occurs. User message creation and `add_message()` happen at lines 2018–2024, after the service check.
- `send_plan_message_stream` (chat.py:2083–2097): Identical pattern — service check at 2083–2089, message persistence at 2091–2097.
- Previous memory confirms this was already fixed: "Bug 3.4 (plan-mode orphaned chat) is RESOLVED: messages persist after service check."

### Alternatives Considered

1. **Refactor to extract a shared guard pattern**: Create a decorator or middleware that checks service availability before any endpoint logic. Rejected as over-engineering for 2 endpoints, and the existing inline pattern is clear and explicit.
2. **Apply the same fix to regular chat endpoints**: The `POST /messages` endpoint still persists user messages before the service check (line 1049–1055). This is a valid improvement but out of scope for Task 3.4 which specifically targets plan-mode. Noted as future work in the plan.
