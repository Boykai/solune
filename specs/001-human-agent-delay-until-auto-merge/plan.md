# Implementation Plan: Human Agent — Delay Until Auto-Merge

**Branch**: `copilot/add-delay-until-auto-merge-config` | **Date**: 2026-04-04 | **Spec**: `specs/001-human-agent-delay-until-auto-merge/spec.md`
**Input**: Parent Issue #703 — Human Agent — Delay Until Auto-Merge

## Summary

Extend the existing Human agent node with an optional `delay_seconds` config. When set (1–86400 seconds), the pipeline creates the human sub-issue, waits the configured duration (with 15-second early-cancel polling), then triggers the existing `_attempt_auto_merge()` flow. When unset, current behavior is preserved — the pipeline pauses until the user manually closes the sub-issue or comments "Done!". This replaces the current all-or-nothing "skip human entirely when auto-merge is active" behavior with a configurable grace-period review window.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript / React (frontend)
**Primary Dependencies**: FastAPI, Pydantic (backend); React, Vite, Tailwind CSS, Radix UI, dnd-kit (frontend)
**Storage**: In-memory `PipelineState` dataclass (no database migration needed — `delay_seconds` stored in `PipelineAgentNode.config` dict)
**Testing**: pytest with coverage (backend, fail_under=75); Vitest + Playwright (frontend)
**Target Platform**: Linux server (Docker containers on Azure Container Apps)
**Project Type**: Web application (backend + frontend)
**Performance Goals**: Polling loop already runs on 15-second intervals; delay loop reuses this cadence — no additional performance overhead
**Constraints**: Max delay 86400 seconds (24 hours); polling granularity 15 seconds; must not block the main polling event loop (use `asyncio.sleep`)
**Scale/Scope**: Single config field addition per human agent node; touches ~6 backend files, ~3 frontend files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Feature specified in parent issue #703 with clear requirements, phases, and verification criteria |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates in `.specify/templates/` |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan created by speckit.plan agent with clear handoff to speckit.tasks |
| IV. Test Optionality | ✅ PASS | Tests included — unit tests for validation + execution specified in issue verification section |
| V. Simplicity and DRY | ✅ PASS | Reuses existing `PipelineAgentNode.config` dict (no schema migration), reuses `_attempt_auto_merge()`, reuses polling loop cadence. No new abstractions introduced |

**Pre-design gate**: ✅ ALL PASS — proceeding to Phase 0.

### Post-Design Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Design aligns with spec: delay in config, polling loop, early cancel, auto-merge trigger |
| II. Template-Driven Workflow | ✅ PASS | Plan, research, data-model, contracts, quickstart all generated per template |
| III. Agent-Orchestrated Execution | ✅ PASS | Clear Phase 1→2→3 decomposition with dependency ordering |
| IV. Test Optionality | ✅ PASS | Unit tests for validation + execution paths defined in verification section |
| V. Simplicity and DRY | ✅ PASS | No new models, no migrations, no new abstractions — extends existing config dict and execution flow |

**Post-design gate**: ✅ ALL PASS.

## Project Structure

### Documentation (this feature)

```text
specs/001-human-agent-delay-until-auto-merge/
├── plan.md              # This file
├── research.md          # Phase 0: Architecture research and decisions
├── data-model.md        # Phase 1: Data model changes
├── quickstart.md        # Phase 1: Implementation quickstart guide
├── contracts/           # Phase 1: API contracts
│   └── delay-config.yaml
└── tasks.md             # Phase 2 output (created by /speckit.tasks, NOT this command)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── models/
│   │   │   └── pipeline.py                              # PipelineAgentNode.config (existing, no changes needed)
│   │   └── services/
│   │       ├── workflow_orchestrator/
│   │       │   ├── config.py                            # AgentAssignment.config merge (Phase 1, Step 1)
│   │       │   ├── models.py                            # PipelineState.agent_configs (Phase 1, Step 2)
│   │       │   └── orchestrator.py                      # Sub-issue body with delay info (Phase 3)
│   │       ├── copilot_polling/
│   │       │   ├── pipeline.py                          # Delay-then-merge execution (Phase 1, Step 4-5)
│   │       │   └── auto_merge.py                        # _attempt_auto_merge (existing, no changes)
│   │       ├── agent_tracking.py                        # Tracking table delay display (Phase 3)
│   │       └── github_projects/
│   │           └── agents.py                            # tailor_body_for_agent (existing, no changes needed)
│   └── tests/
│       └── unit/
│           └── test_human_delay.py                      # Unit tests for delay feature
└── frontend/
    └── src/
        ├── types/
        │   └── index.ts                                 # PipelineAgentNode type (existing, no changes needed)
        ├── components/
        │   └── pipeline/
        │       └── AgentNode.tsx                         # Delay toggle + badge UI (Phase 2)
        └── hooks/
            └── usePipelineBoardMutations.ts             # Config merge verification (Phase 2)
```

**Structure Decision**: Web application (Option 2) — existing `solune/backend/` + `solune/frontend/` structure. All changes are additive within existing module boundaries.

## Implementation Phases

### Phase 1: Backend — Config Flow + Execution

| Step | File | Change | Depends On |
|------|------|--------|------------|
| 1.1 | `config.py:367-378` | Merge full `node.config` dict into `AgentAssignment.config` (not just model_id/model_name). When `node.config` has extra keys like `delay_seconds`, they flow through. | — |
| 1.2 | `models.py:140-177` | Add `agent_configs: dict[str, dict] = field(default_factory=dict)` to `PipelineState`. Maps agent_slug → config dict so execution loop can read `delay_seconds`. | — |
| 1.3 | `pipelines.py:467-489` | When constructing `PipelineState`, populate `agent_configs` from `WorkflowConfiguration`'s `AgentAssignment.config` dicts. | 1.1, 1.2 |
| 1.4 | `pipeline.py:1951-2039` | Replace "skip human if auto_merge" block. When `delay_seconds` is set: create sub-issue → comment "⏱️ Auto-merge in Nm" → loop `asyncio.sleep(15)` checking sub-issue status → trigger `_attempt_auto_merge()` → close sub-issue → advance pipeline. When not set AND auto_merge active AND last step: current skip behavior. When not set AND no auto_merge: unchanged manual wait. | 1.1–1.3 |
| 1.5 | `pipeline.py` | Add validation: if `agent_slug == "human"` and `config.get("delay_seconds")` is set, must be `int` in `[1, 86400]`. | 1.4 |

### Phase 2: Frontend — Delay Config UI (parallel with Phase 1 after Step 1.1)

| Step | File | Change | Depends On |
|------|------|--------|------------|
| 2.1 | `AgentNode.tsx` | When `agent_slug === 'human'`, render below model selector: toggle "Delay until auto-merge" (off by default), when on: numeric input for seconds. Updates via existing `onUpdateAgent → config.delay_seconds`. | 1.1 |
| 2.2 | `usePipelineBoardMutations.ts` | Verify `updateAgentInStage` spreads existing config when merging partial updates (already works via `{ ...a, ...updates }` on line 193). No code change expected. | — |
| 2.3 | `AgentNode.tsx` | When delay is set, show badge `⏱️ Auto-merge: {formatted_duration}`. When not set: `Manual review`. | 2.1 |

### Phase 3: Polish

| Step | File | Change | Depends On |
|------|------|--------|------------|
| 3.1 | `agent_tracking.py` | Render delayed human row as `⏱️ Delay ({formatted_duration})` while waiting | 1.4 |
| 3.2 | `orchestrator.py` (or `agents.py`) | Append "⏱️ Auto-merge in {duration}. Close early to skip." to human sub-issue body when delay configured | 1.1 |
| 3.3 | `pipeline.py` | Early cancellation: instead of one big `asyncio.sleep(N)`, loop in 15s increments checking if sub-issue was closed. If closed early, proceed immediately. (Part of 1.4 implementation) | 1.4 |

### Verification

| Test | Type | Validates |
|------|------|-----------|
| `delay_seconds` validation — range [1, 86400], only on human agents | Unit | Step 1.5 |
| Pipeline execution with human + delay → sleep + auto-merge invoked | Unit | Step 1.4 |
| Pipeline execution with human + no delay → manual-wait unchanged | Unit | Step 1.4 |
| Human + 30s delay → verify 30s wait then auto-merge | Manual | Steps 1.1–1.4 |
| Human + no delay → pipeline pauses until sub-issue closed | Manual | Regression |
| Human + delay, close sub-issue before delay expires → early proceed | Manual | Step 3.3 |
| Delay toggle renders only on human agent nodes | Frontend | Step 2.1 |

## Complexity Tracking

> No constitution violations found — this section is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)* | — | — |
