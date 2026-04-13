# Quickstart: Remove Fleet Dispatch & Copilot CLI Code

**Branch**: `002-remove-fleet-dispatch` | **Date**: 2026-04-13

## Overview

This feature removes all fleet dispatch orchestration and GitHub Copilot CLI plugin code from Solune. The "classic" dispatch path (format_issue_context_as_prompt + assign_copilot_to_issue) becomes the sole execution path.

## What Changes

- **~30 files deleted**: Fleet service, CLI plugin, shell scripts, pipeline templates, fleet test files
- **~15 files modified**: Orchestrators, models, config, API layer, frontend types, remaining tests, docs
- **Zero new files** (except spec artifacts)

## Verification Commands

After implementation, run these commands to verify correctness:

```bash
# 1. Backend unit tests — all pass, no import errors
cd solune/backend && python -m pytest tests/unit/ -x -q

# 2. Backend integration tests — no broken imports
cd solune/backend && python -m pytest tests/integration/ -x -q

# 3. Frontend type checking — no type errors
cd solune/frontend && npx tsc --noEmit

# 4. Frontend tests — schema tests pass
cd solune/frontend && npx vitest run

# 5. Zero fleet references remaining (excluding CHANGELOG.md and specs/)
grep -rn "fleet\|FleetDispatch\|fleet_dispatch\|fleet-dispatch\|agent_task_ids\|dispatch_backend" solune/ \
  --exclude-dir=__pycache__ --exclude="CHANGELOG.md" | grep -v "specs/"
# Expected: zero matches

# 6. Verify preserved callers work
grep -n "assign_copilot_to_issue" solune/backend/src/services/app_plan_orchestrator.py \
  solune/backend/src/services/copilot_polling/auto_merge.py \
  solune/backend/src/services/workflow_orchestrator/orchestrator.py
# Expected: 3 call sites, all functional
```

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| `assign_copilot_to_issue()` preserved | Shared by fleet AND non-fleet callers |
| Legacy fallback stages become primary constant | Current fallback is the production default |
| `dispatch_backend`/`agent_task_ids` removed from API | Zero UI consumers |
| `.github/agents/*.agent.md` unchanged | Fleet eligibility was runtime, not in agent defs |
| `guard-config.yml` unchanged | No fleet-specific entries |
| `scripts/pipelines/` deleted entirely | Empty after fleet file removal |
