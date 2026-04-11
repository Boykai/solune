# Implementation Plan: Fleet-Dispatch Agent Pipelines via GitHub CLI

**Branch**: `copilot/create-implementation-plan-for-pipelines` | **Date**: 2026-04-11 | **Spec**: [#1386](https://github.com/Boykai/solune/issues/1386)
**Input**: Parent issue #1386 — Fleet-Dispatch Agent Pipelines via GitHub CLI

## Summary

Replace the Python-only dispatch path (`copilot.py → _assign_copilot_graphql()`) with a standalone Bash fleet-dispatch script that uses `gh api graphql` to dispatch Copilot cloud agents. The script consumes a standalone JSON pipeline config (extracted from the Python backend's `_PRESET_DEFINITIONS`), pre-creates sub-issues via `gh issue create`, and dispatches parallel agent groups using background processes (`&` + `wait`). Completion polling uses `gh api graphql` to check sub-issue state with exponential backoff.

## Technical Context

**Language/Version**: Bash 5.x (script), Python 3.12 (config extraction), JSON (config format)
**Primary Dependencies**: `gh` CLI ≥2.80, `jq` ≥1.6, GNU `gettext` (`envsubst`)
**Storage**: Local JSON state file (`fleet-state.json`) for dispatch tracking; no database changes
**Testing**: `bats` (Bash Automated Testing System) for shell script tests; `pytest` for Python extraction script
**Target Platform**: Linux (CI/CD), macOS (local dev)
**Project Type**: Web application (extending existing `solune/` monorepo)
**Performance Goals**: Dispatch ≤10 agents in <30 seconds; parallel group dispatch should be truly concurrent
**Constraints**: Must use `gh api graphql` for full `agentAssignment` support; no new Python runtime dependencies
**Scale/Scope**: Pipelines with up to 15 agents across 4–5 groups; typically 3–5 concurrent agents per parallel group

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Specification-First Development ✅

The parent issue (#1386) provides detailed requirements with phased steps, CLI entry point analysis, and the GraphQL mutation specification. This plan document formalizes the specification.

### II. Template-Driven Workflow ✅

This plan follows the canonical `plan-template.md` structure. All artifacts (`research.md`, `data-model.md`, `contracts/`, `quickstart.md`) conform to the template conventions established by previous features.

### III. Agent-Orchestrated Execution ✅

The feature itself is about agent dispatch — single-responsibility agents receive focused sub-issues. The implementation decomposes into clear phases: config extraction → dispatch script → monitoring.

### IV. Test Optionality with Clarity ✅

Tests are included for the dispatch script (bats) and config extraction (pytest) since this is a critical infrastructure component. The shell script handles production agent dispatch and must be validated.

### V. Simplicity and DRY ✅

The design extracts pipeline config to a single JSON file consumed by both Python and Bash, eliminating the current duplication between `pipeline_orchestrator.py`, `pipelines/service.py`, and `preset-pipelines.ts`. `envsubst` templating is the simplest approach for instruction generation.

### Post-Design Re-Check ✅

All five principles verified after Phase 1 design completion. No violations detected.

## Project Structure

### Documentation (this feature)

```text
(repo root)
├── plan.md              # This file
├── research.md          # Phase 0 output — R1–R7 decisions
├── data-model.md        # Phase 1 output — config and state entities
├── quickstart.md        # Phase 1 output — setup and usage guide
├── contracts/           # Phase 1 output — JSON schemas and CLI interface
│   ├── pipeline-config-schema.json
│   └── fleet-dispatch-cli.yaml
└── tasks.md             # Phase 2 output (NOT created by speckit.plan)
```

### Source Code (repository root)

```text
solune/
├── config/
│   ├── pipeline-config.json          # Extracted preset definitions (Phase 2)
│   └── templates/
│       ├── agent-instructions.tpl    # Base instruction template (Phase 2)
│       ├── speckit-specify.tpl       # Agent-specific: speckit.specify
│       ├── speckit-plan.tpl          # Agent-specific: speckit.plan
│       ├── speckit-tasks.tpl         # Agent-specific: speckit.tasks
│       ├── speckit-implement.tpl     # Agent-specific: speckit.implement
│       └── copilot-review.tpl       # Agent-specific: copilot-review
├── scripts/
│   ├── fleet-dispatch.sh            # Main dispatch script (Phase 1)
│   ├── extract-pipeline-config.py   # Config extraction tool (Phase 2)
│   └── validate-contracts.sh        # Existing — extended for new schemas
├── backend/
│   └── src/
│       └── services/
│           └── pipelines/
│               └── service.py        # Updated: reads from JSON config (Phase 2)
└── frontend/
    └── src/
        └── data/
            └── preset-pipelines.ts   # Updated: generated from JSON config (Phase 2)
```

**Structure Decision**: Extends the existing `solune/` monorepo structure. New files are placed in `solune/config/` (pipeline config and templates) and `solune/scripts/` (dispatch script). No new top-level directories needed.

## Phase Breakdown

### Phase 1 — CLI Fleet Dispatch Script

**Goal**: Create `solune/scripts/fleet-dispatch.sh` that dispatches agents per pipeline config.

**Tasks**:

1. **Script skeleton**: Argument parsing (`--config`, `--repo`, `--parent-issue`, `--base-ref`, `--dry-run`), environment validation (`gh` CLI, `jq`, auth check)
2. **Sub-issue creation**: Loop through pipeline stages and groups; create sub-issues with `gh issue create --label "agent:{agent_name}" --body "..."`. Parse returned URL for issue number; fetch node ID via GraphQL
3. **GraphQL dispatch function**: Mirror `_assign_copilot_graphql()` — construct mutation payload with `agentAssignment { customAgent, customInstructions, model, baseRef }`. Set required `GraphQL-Features` header
4. **Parallel group dispatch**: For each group with `execution_mode: "parallel"`, dispatch all agents as background processes (`dispatch "$agent" &`), then `wait` for all PIDs. Capture exit codes
5. **Serial group dispatch**: For sequential groups, dispatch one agent at a time with completion polling between agents
6. **Retry logic**: 3 attempts with exponential backoff (3s, 6s, 9s) per dispatch call
7. **State file management**: Write `fleet-state.json` tracking issue numbers, node IDs, dispatch timestamps, and completion status

**Dependencies**: `gh` CLI ≥2.80, `jq` ≥1.6, authenticated `gh auth status`

### Phase 2 — Pipeline Config Extraction

**Goal**: Extract pipeline definitions to standalone JSON; template custom instructions for shell consumption.

**Tasks**:

1. **Config extraction script**: `extract-pipeline-config.py` reads `_PRESET_DEFINITIONS` from `pipelines/service.py` and writes `config/pipeline-config.json`
2. **Schema definition**: JSON Schema for pipeline config (validates structure matches Pydantic models)
3. **Instruction templates**: Port `format_issue_context_as_prompt()` and `tailor_body_for_agent()` logic to `envsubst`-compatible template files
4. **Backend integration**: Update `PipelineService.seed_presets()` to read from `pipeline-config.json` instead of inline `_PRESET_DEFINITIONS`
5. **Frontend sync**: Generate `preset-pipelines.ts` from the JSON config (build-time script or manual sync)

**Dependencies**: Phase 1 script skeleton (consumes the JSON config); existing Pydantic models in `models/pipeline.py`

### Phase 3 — Monitoring & Completion

**Goal**: Poll agent completion and advance pipeline state.

**Tasks**:

1. **Completion polling**: `gh api graphql` to check sub-issue state (open/closed) with exponential backoff (30s → 5min)
2. **PR detection**: Query for PRs matching the agent branch pattern; check merge status
3. **Pipeline advancement**: When a serial agent completes, dispatch the next agent in the group. When all agents in a parallel group complete, advance to the next group
4. **Timeout handling**: Configurable per-agent timeout (default 60 minutes); log warning and continue on timeout
5. **Summary report**: At completion, print a summary table of all agents, their status, duration, and issue/PR links

**Dependencies**: Phase 1 dispatch script, Phase 2 config extraction

## Complexity Tracking

No constitution violations requiring justification. The design follows YAGNI — each phase builds on the previous one, and Phase 3 monitoring can be omitted for initial fire-and-forget use cases.
