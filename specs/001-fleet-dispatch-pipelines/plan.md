# Implementation Plan: Fleet-Dispatch Agent Pipelines via GitHub CLI

**Branch**: `001-fleet-dispatch-pipelines` | **Date**: 2026-04-12 | **Spec**: `/home/runner/work/solune/solune/specs/001-fleet-dispatch-pipelines/spec.md`
**Input**: Feature specification from `/home/runner/work/solune/solune/specs/001-fleet-dispatch-pipelines/spec.md`

## Summary

Add a GitHub CLI-based fleet dispatch path that mirrors the backend's existing Copilot GraphQL assignment flow, externalizes pipeline group definitions into a shared JSON configuration, and documents monitoring plus retry contracts for serial and parallel agent execution without requiring the Python backend at runtime.

## Technical Context

**Language/Version**: Bash 5.x for CLI orchestration; Python 3.12+ backend consumers  
**Primary Dependencies**: GitHub CLI 2.80+, `jq`, existing GitHub GraphQL/REST helpers, Pydantic pipeline models  
**Storage**: GitHub Issues/agent-task state plus repository JSON/template files; existing SQLite-backed pipeline configs remain the backend source of persistence  
**Testing**: `pytest` unit/integration coverage plus shell-script smoke tests driven through existing Python test tooling  
**Target Platform**: Linux/macOS shell environments with authenticated `gh`, plus the existing Solune backend runtime  
**Project Type**: Web application with backend services and repository scripts  
**Performance Goals**: Dispatch bootstrap completes in under 2 minutes excluding agent runtime; parallel groups launch within 10 seconds; status polling reflects changes within 30 seconds  
**Constraints**: Runtime path must use only `gh`, bash, and `jq`; preserve parity with current GraphQL `agentAssignment` payload; handle rate limits/auth failures; support fail-fast or continue semantics  
**Scale/Scope**: Single-repository dispatch for one parent issue at a time, covering ~10 agents across 4 ordered execution groups and one retryable single-agent flow

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Specification-First Development**: PASS — `/home/runner/work/solune/solune/specs/001-fleet-dispatch-pipelines/spec.md` already defines prioritized user stories, acceptance scenarios, edge cases, assumptions, and scope boundaries.
- **Template-Driven Workflow**: PASS — this plan and all Phase 0/1 artifacts stay inside `/home/runner/work/solune/solune/specs/001-fleet-dispatch-pipelines/` using the canonical Speckit artifact set.
- **Agent-Orchestrated Execution**: PASS — the design keeps the existing single-responsibility agents and focuses this feature on dispatch orchestration, config extraction, monitoring, and retry handoffs.
- **Test Optionality with Clarity**: PASS — the spec explicitly calls for verifiable dispatch/config behavior, so the plan includes targeted pytest-backed coverage without imposing unrelated new frameworks.
- **Simplicity and DRY**: PASS — the design reuses the existing GraphQL mutation, prompt-formatting logic, and pipeline-group abstractions instead of introducing a second backend protocol.

**Post-Phase 1 Re-check**: PASS — `research.md`, `data-model.md`, `quickstart.md`, and the contracts continue to reuse existing repository patterns and do not require constitution exceptions.

## Project Structure

### Documentation (this feature)

```text
specs/001-fleet-dispatch-pipelines/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── fleet-dispatch.openapi.yaml
│   ├── github-agent-assignment.graphql
│   └── pipeline-config.schema.json
└── tasks.md
```

### Source Code (repository root)
```text
solune/scripts/
└── fleet-dispatch.sh                 # New CLI orchestration entry point

solune/backend/src/models/
└── pipeline.py                       # Shared pipeline config/group model shape

solune/backend/src/services/
├── pipeline_orchestrator.py          # Current hard-coded group/source behavior
├── workflow_orchestrator/
│   ├── config.py                     # Backend pipeline loading/parity logic
│   └── orchestrator.py               # Existing assignment flow and polling hooks
└── github_projects/
    ├── agents.py                     # Prompt formatting/body tailoring to port into templates
    ├── copilot.py                    # GraphQL/REST Copilot assignment implementation
    └── graphql.py                    # Canonical `addAssigneesToAssignable` mutation

solune/backend/tests/unit/
├── test_pipeline_orchestrator.py
├── test_github_agents.py
└── test_pipeline_config_schema.py    # Planned schema/loader coverage
```

**Structure Decision**: Use the existing web-application repository layout. The implementation will add a shell entry point under `solune/scripts/`, keep backend parity logic in `solune/backend/src/services/` and `solune/backend/src/models/`, and validate the extracted config and prompt-rendering behavior with targeted backend tests.

## Complexity Tracking

No constitution violations or complexity exceptions are required at plan time.
