# Implementation Plan: Auto-Merge After All Agents Complete + CI Pass + DevOps Retry

**Branch**: `copilot/speckit-plan-auto-merge-implementation` | **Date**: 2026-04-04 | **Spec**: [#770](https://github.com/Boykai/solune/issues/770)
**Input**: Parent issue #770 — Auto-Merge After All Agents Complete + CI Pass + DevOps Retry

## Summary

Close three gaps in the auto-merge pipeline so that, after every agent completes and CI passes, the parent PR is automatically squash-merged — and if CI fails or merge conflicts arise, the DevOps agent is dispatched to fix the issue, then re-merge is attempted. The core merge logic, CI verification, retry loop, and DevOps dispatch code already exist; this plan fills in (1) the DevOps agent template + registration, (2) post-DevOps re-merge scheduling, and (3) live webhook-to-action wiring.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI, httpx, pydantic, asyncio  
**Storage**: PostgreSQL (via existing `chat_store`) + in-memory `BoundedDict` caches  
**Testing**: pytest + pytest-asyncio (≈4 800 unit tests)  
**Target Platform**: Linux server (Azure Container Apps)  
**Project Type**: Web (backend API + frontend SPA)  
**Performance Goals**: Webhook handlers must respond < 2 s; polling interval 120 s for post-DevOps retry  
**Constraints**: Max 2 DevOps attempts per issue; max 3 auto-merge retries with exponential backoff (60 s / 120 s / 240 s); deduplication required to prevent concurrent dispatch  
**Scale/Scope**: Single-tenant SaaS; dozens of concurrent pipelines

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Parent issue #770 provides detailed spec with phases, files, and verification criteria |
| II. Template-Driven Workflow | ✅ PASS | This plan follows the canonical `plan-template.md`; agent template follows existing `.agent.md` format |
| III. Agent-Orchestrated Execution | ✅ PASS | DevOps agent has single responsibility (CI fix + merge-conflict resolution); handoff via "Done!" marker comment |
| IV. Test Optionality | ✅ PASS | Tests are specified in verification section of parent issue; unit tests for each gap |
| V. Simplicity and DRY | ✅ PASS | Changes reuse existing `dispatch_devops_agent()`, `_attempt_auto_merge()`, and `schedule_auto_merge_retry()` patterns; no new abstractions |

**Post-Design Re-Check**: ✅ All principles still satisfied. No complexity tracking entries needed — all changes modify existing files and one new template file.

## Project Structure

### Documentation (this feature)

```text
specs/770-auto-merge-devops-retry/
├── plan.md              # This file
├── research.md          # Phase 0 output — resolved unknowns
├── data-model.md        # Phase 1 output — state & entity model
├── quickstart.md        # Phase 1 output — developer quick-start
├── contracts/           # Phase 1 output
│   └── auto-merge-events.yaml   # Internal event contract (WebSocket + webhook)
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   └── webhooks.py                          # MODIFY — wire check_run/check_suite handlers
│   ├── models/
│   │   └── agent.py                             # EXISTING — AvailableAgent model (no change)
│   └── services/
│       ├── copilot_polling/
│       │   ├── auto_merge.py                    # MODIFY — add schedule_post_devops_merge_retry()
│       │   ├── pipeline.py                      # MODIFY — add In Review polling fallback
│       │   └── state.py                         # EXISTING — config constants (no change)
│       └── github_projects/
│           └── agents.py                        # MODIFY — register DevOps in BUILTIN_AGENTS
├── templates/
│   └── .github/agents/
│       └── devops.agent.md                      # NEW — DevOps agent template
└── tests/
    └── unit/
        ├── test_auto_merge.py                   # MODIFY — add post-DevOps retry tests
        ├── test_github_agents.py                # MODIFY — update count + slug assertions
        ├── test_webhook_ci.py                   # MODIFY — add dispatch/re-merge tests
        └── test_pipeline_in_review_recovery.py  # NEW — In Review polling fallback tests
```

**Structure Decision**: Web application (backend + frontend). All changes are backend-only within the existing `solune/backend/` tree. One new template file in `backend/templates/`, one potential new test file. No frontend changes needed.

---

## Phase 0: Research

> See [research.md](./research.md) for full findings.

### Unknowns Resolved

| # | Unknown | Resolution |
|---|---------|------------|
| 1 | DevOps agent template format | Follows existing `.agent.md` YAML front-matter + markdown body (see `linter.agent.md`, `tester.agent.md`) |
| 2 | How to detect DevOps "Done!" comment | Scan issue timeline for comment body containing `devops: Done!` marker via GitHub REST API `GET /repos/{owner}/{repo}/issues/{number}/comments` |
| 3 | Post-DevOps re-merge trigger mechanism | Polling loop (120 s interval) after DevOps dispatch; webhook provides proactive fast-path |
| 4 | Webhook → auto-merge issue lookup | Map PR number → parent issue via existing `_discover_main_pr_for_review()` reverse lookup or new lightweight PR-to-issue cache |
| 5 | check_suite "success" handling | Add `conclusion="success"` branch to `handle_check_suite_event()` for re-merge proactive path |

---

## Phase 1: Design

### Gap 1 — Create DevOps Agent

**1.1 Create `devops.agent.md` template**

- **File**: `backend/templates/.github/agents/devops.agent.md` (NEW)
- **Format**: YAML front-matter (`name`, `description`, `mcp-servers`) + markdown body
- **Persona**: Fix CI failures, resolve merge conflicts, push fixes to PR branch
- **Completion marker**: `devops: Done!` in final issue comment
- **MCP servers**: Same context7 config as other agents
- **Note**: The deployed version at `.github/agents/devops.agent.md` already exists and is functional. This template is the source-of-truth for new repo scaffolding.

**1.2 Register as built-in agent**

- **File**: `backend/src/services/github_projects/agents.py`
- **Change**: Add `AvailableAgent(slug="devops", display_name="DevOps", description="CI failure diagnosis and resolution agent", source=AgentSource.BUILTIN)` to `BUILTIN_AGENTS` list
- **Impact**: Agent count goes from 8 → 9; tests must update assertions

### Gap 2 — Post-DevOps Re-Merge

**2.1 New function: `schedule_post_devops_merge_retry()`**

- **File**: `backend/src/services/copilot_polling/auto_merge.py`
- **Behavior**:
  1. After DevOps dispatch succeeds, schedule a background polling loop
  2. Every 120 s, check for DevOps "Done!" comment on the issue
  3. When found: set `devops_active = False`, call `_attempt_auto_merge()`
  4. If merge succeeds → transition to Done
  5. If merge fails again with `devops_needed` → re-dispatch DevOps (up to cap of 2 attempts)
  6. If cap reached → broadcast failure, stop
- **Deduplication**: Track in `_pending_post_devops_retries: BoundedDict` (maxlen=200) keyed by `issue_number`
- **Constants**: `POST_DEVOPS_POLL_INTERVAL = 120.0` (in `state.py`)

**2.2 Wire retry into `dispatch_devops_agent()`**

- **File**: `backend/src/services/copilot_polling/auto_merge.py`
- **Change**: After successful dispatch (return True), call `schedule_post_devops_merge_retry()` with issue context
- **Dependency**: Requires 2.1

**2.3 Polling fallback for "In Review" status**

- **File**: `backend/src/services/copilot_polling/pipeline.py`
- **Function**: `check_in_review_issues()` — add secondary check
- **When**: Issue is "In Review" with no active pipeline + auto-merge enabled + `devops_active` in metadata
- **Action**: Check for DevOps "Done!" comment; if found, call `_attempt_auto_merge()`
- **Purpose**: Handles server restart recovery (background task lost)
- **Dependency**: Requires 2.1

### Gap 3 — Wire Webhook Handlers

**3.1 CI failure webhook → DevOps dispatch**

- **File**: `backend/src/api/webhooks.py`
- **Function**: `handle_check_run_event()` (line ~750)
- **Change**: After detecting failure + associated PRs, look up parent issue → dispatch DevOps with failure context
- **Logic**:
  1. For each PR number in the event, resolve parent issue number
  2. Check if issue has auto-merge enabled (pipeline metadata)
  3. Build merge_result_context from check_run data
  4. Call `dispatch_devops_agent()` with context
- **Dependency**: Requires Gap 1 (DevOps agent registered) and Gap 2 (retry wiring)

**3.2 CI pass webhook → re-merge**

- **File**: `backend/src/api/webhooks.py`
- **Function**: `handle_check_suite_event()` (line ~784)
- **Change**: Add `conclusion="success"` branch (currently only handles `"failure"`)
- **Logic**:
  1. On check_suite completion with `conclusion="success"`:
  2. For each PR, resolve parent issue number
  3. If issue is "In Review" with auto-merge enabled:
  4. Call `_attempt_auto_merge()` proactively
- **Dependency**: Requires Gap 1-2

---

## Dependency Graph

```
Gap 1.1 (devops.agent.md template)
    │
    ├──► Gap 1.2 (register BUILTIN_AGENTS)
    │         │
    │         ▼
    │    Gap 2.1 (schedule_post_devops_merge_retry)
    │         │
    │         ├──► Gap 2.2 (wire into dispatch_devops_agent)
    │         │         │
    │         │         ▼
    │         ├──► Gap 2.3 (In Review polling fallback)
    │         │
    │         ▼
    │    Gap 3.1 (CI failure webhook → DevOps)
    │         │
    │         ▼
    └──► Gap 3.2 (CI pass webhook → re-merge)
```

**Execution Order**: 1.1 → 1.2 → 2.1 → 2.2 → 2.3 → 3.1 → 3.2

---

## Verification Plan

| # | Type | Scenario | Validates |
|---|------|----------|-----------|
| 1 | Unit | DevOps agent slug in `BUILTIN_AGENTS`, count = 9 | Gap 1.2 |
| 2 | Unit | `dispatch_devops_agent()` succeeds with new agent | Gap 1.1, 1.2 |
| 3 | Unit | `schedule_post_devops_merge_retry()` polls for "Done!" and re-merges | Gap 2.1 |
| 4 | Unit | `dispatch_devops_agent()` triggers post-DevOps retry | Gap 2.2 |
| 5 | Unit | `check_in_review_issues()` recovers stalled DevOps issues | Gap 2.3 |
| 6 | Unit | `handle_check_run_event()` dispatches DevOps on CI failure | Gap 3.1 |
| 7 | Unit | `handle_check_suite_event()` re-merges on CI success | Gap 3.2 |
| 8 | Integration | All agents complete → CI passes → auto-merge → Done | End-to-end happy path |
| 9 | Integration | All agents complete → CI fails → DevOps fixes → re-merge → Done | End-to-end recovery |
| 10 | Integration | CI failure webhook → proactive DevOps dispatch | Webhook fast-path |
| 11 | Integration | CI pass webhook → proactive re-merge | Webhook fast-path |
| 12 | Edge | DevOps fails 2× → stops, broadcasts failure | Retry cap |
| 13 | Edge | Server restart during DevOps → In Review polling recovers | Resilience |

---

## Complexity Tracking

> No constitution violations to justify. All changes follow existing patterns.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
