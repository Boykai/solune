# ADR-007: Backend Pyright strict-mode legacy downgrades

**Status**: Accepted
**Date**: 2026-04-18

## Context

`solune/backend/pyproject.toml` was tightened in spec 001-backend-pyright-strict (removed). The rollout flips Pyright's global `typeCheckingMode` from `"standard"` to `"strict"` and locks a strict floor on the cleanest packages (`src/api`, `src/models`, `src/services/agents`).

Doing the strict flip in one shot would surface ~3,160 pre-existing type errors in legacy modules (`src/services/copilot_polling/**`, `src/services/github_projects/**`, `src/services/workflow_orchestrator/**`, `src/main.py`, etc.). Fixing all of them up front would block the rollout indefinitely.

## Decision

Adopt a per-file `# pyright: basic` downgrade pragma for every module that fails strict, recorded in this ADR. Each pragma is paired with a `# reason:` line per pragma-contract.md § P1. The burn-down gate (burn-down-gate-contract.md) prevents new pragmas from leaking into the strict floor and reports the global count on every CI run.

Removing a pragma — i.e., paying down legacy debt — requires deleting the matching row from this table in the same PR (FR-008, P5).

## Consequences

- **+** Global `typeCheckingMode = "strict"` is achievable now; new code under any package gets full strict analysis by default.
- **+** Every downgrade is auditable: file, reason, owner, and target removal milestone live in one place.
- **+** The strict floor (`src/api`, `src/models`, `src/services/agents`) is enforced exclusively — no pragmas allowed there.
- **−** ~84 modules remain on `basic` analysis; bugs in those files may surface only at runtime until the burn-down completes.
- **−** Reviewers must reject PRs that drift the ADR table from the on-disk pragma set.

## Downgrade table

| File | Reason | Owner | Target removal milestone |
|------|--------|-------|--------------------------|
| `src/attachment_formatter.py` | Legacy top-level module; pending follow-up typing pass. | backend | TBD |
| `src/constants.py` | Legacy top-level module; pending follow-up typing pass. | backend | TBD |
| `src/exceptions.py` | Legacy top-level module; pending follow-up typing pass. | backend | TBD |
| `src/logging_utils.py` | Legacy top-level module; pending follow-up typing pass. | backend | TBD |
| `src/main.py` | Legacy top-level module; pending follow-up typing pass. | backend | TBD |
| `src/prompts/plan_instructions.py` | Prompt template module; large untyped string fragments pending refactor. | backend | TBD |
| `src/services/activity_service.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/agent_creator.py` | Legacy agent providers + tools predate typed agent SDK surface. | backend | TBD |
| `src/services/agent_provider.py` | Legacy agent providers + tools predate typed agent SDK surface. | backend | TBD |
| `src/services/agent_tools.py` | Legacy agent providers + tools predate typed agent SDK surface. | backend | TBD |
| `src/services/agent_tracking.py` | Legacy agent providers + tools predate typed agent SDK surface. | backend | TBD |
| `src/services/ai_utilities.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/app_plan_orchestrator.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/app_service.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/app_templates/loader.py` | Template loader/renderer reads arbitrary YAML; typed once template schema is finalised. | backend | TBD |
| `src/services/app_templates/renderer.py` | Template loader/renderer reads arbitrary YAML; typed once template schema is finalised. | backend | TBD |
| `src/services/chat_agent.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/chat_store.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/chores/chat.py` | Legacy chores pipeline; mixed YAML/JSON config payloads pending Pydantic models. | backend | TBD |
| `src/services/chores/service.py` | Legacy chores pipeline; mixed YAML/JSON config payloads pending Pydantic models. | backend | TBD |
| `src/services/chores/template_builder.py` | Legacy chores pipeline; mixed YAML/JSON config payloads pending Pydantic models. | backend | TBD |
| `src/services/cleanup_service.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/copilot_polling/__init__.py` | Legacy Copilot polling pipeline; deep GitHub REST/GraphQL JSON shapes pending typed wrappers. | backend | TBD |
| `src/services/copilot_polling/agent_output.py` | Legacy Copilot polling pipeline; deep GitHub REST/GraphQL JSON shapes pending typed wrappers. | backend | TBD |
| `src/services/copilot_polling/auto_merge.py` | Legacy Copilot polling pipeline; deep GitHub REST/GraphQL JSON shapes pending typed wrappers. | backend | TBD |
| `src/services/copilot_polling/completion.py` | Legacy Copilot polling pipeline; deep GitHub REST/GraphQL JSON shapes pending typed wrappers. | backend | TBD |
| `src/services/copilot_polling/helpers.py` | Legacy Copilot polling pipeline; deep GitHub REST/GraphQL JSON shapes pending typed wrappers. | backend | TBD |
| `src/services/copilot_polling/label_manager.py` | Legacy Copilot polling pipeline; deep GitHub REST/GraphQL JSON shapes pending typed wrappers. | backend | TBD |
| `src/services/copilot_polling/pipeline.py` | Legacy Copilot polling pipeline; deep GitHub REST/GraphQL JSON shapes pending typed wrappers. | backend | TBD |
| `src/services/copilot_polling/pipeline_state_service.py` | Legacy Copilot polling pipeline; deep GitHub REST/GraphQL JSON shapes pending typed wrappers. | backend | TBD |
| `src/services/copilot_polling/polling_loop.py` | Legacy Copilot polling pipeline; deep GitHub REST/GraphQL JSON shapes pending typed wrappers. | backend | TBD |
| `src/services/copilot_polling/recovery.py` | Legacy Copilot polling pipeline; deep GitHub REST/GraphQL JSON shapes pending typed wrappers. | backend | TBD |
| `src/services/copilot_polling/state.py` | Legacy Copilot polling pipeline; deep GitHub REST/GraphQL JSON shapes pending typed wrappers. | backend | TBD |
| `src/services/copilot_polling/state_validation.py` | Legacy Copilot polling pipeline; deep GitHub REST/GraphQL JSON shapes pending typed wrappers. | backend | TBD |
| `src/services/done_items_store.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/encryption.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/github_auth.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/github_commit_workflow.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/github_projects/_mixin_base.py` | Legacy githubkit response shapes; awaiting upstream typed accessors. | backend | TBD |
| `src/services/github_projects/agents.py` | Legacy githubkit response shapes; awaiting upstream typed accessors. | backend | TBD |
| `src/services/github_projects/board.py` | Legacy githubkit response shapes; awaiting upstream typed accessors. | backend | TBD |
| `src/services/github_projects/branches.py` | Legacy githubkit response shapes; awaiting upstream typed accessors. | backend | TBD |
| `src/services/github_projects/copilot.py` | Legacy githubkit response shapes; awaiting upstream typed accessors. | backend | TBD |
| `src/services/github_projects/issues.py` | Legacy githubkit response shapes; awaiting upstream typed accessors. | backend | TBD |
| `src/services/github_projects/projects.py` | Legacy githubkit response shapes; awaiting upstream typed accessors. | backend | TBD |
| `src/services/github_projects/pull_requests.py` | Legacy githubkit response shapes; awaiting upstream typed accessors. | backend | TBD |
| `src/services/github_projects/repository.py` | Legacy githubkit response shapes; awaiting upstream typed accessors. | backend | TBD |
| `src/services/github_projects/service.py` | Legacy githubkit response shapes; awaiting upstream typed accessors. | backend | TBD |
| `src/services/label_classifier.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/mcp_server/auth.py` | MCP server surface accepts arbitrary client JSON; needs schema-first re-design. | backend | TBD |
| `src/services/mcp_server/prompts.py` | MCP server surface accepts arbitrary client JSON; needs schema-first re-design. | backend | TBD |
| `src/services/mcp_server/resources.py` | MCP server surface accepts arbitrary client JSON; needs schema-first re-design. | backend | TBD |
| `src/services/mcp_server/server.py` | MCP server surface accepts arbitrary client JSON; needs schema-first re-design. | backend | TBD |
| `src/services/mcp_server/tools/activity.py` | MCP tool wrappers forward heterogeneous payloads; typed once tools/ catalog stabilises. | backend | TBD |
| `src/services/mcp_server/tools/agents.py` | MCP tool wrappers forward heterogeneous payloads; typed once tools/ catalog stabilises. | backend | TBD |
| `src/services/mcp_server/tools/apps.py` | MCP tool wrappers forward heterogeneous payloads; typed once tools/ catalog stabilises. | backend | TBD |
| `src/services/mcp_server/tools/chat.py` | MCP tool wrappers forward heterogeneous payloads; typed once tools/ catalog stabilises. | backend | TBD |
| `src/services/mcp_server/tools/chores.py` | MCP tool wrappers forward heterogeneous payloads; typed once tools/ catalog stabilises. | backend | TBD |
| `src/services/mcp_server/tools/pipelines.py` | MCP tool wrappers forward heterogeneous payloads; typed once tools/ catalog stabilises. | backend | TBD |
| `src/services/mcp_server/tools/projects.py` | MCP tool wrappers forward heterogeneous payloads; typed once tools/ catalog stabilises. | backend | TBD |
| `src/services/mcp_server/tools/tasks.py` | MCP tool wrappers forward heterogeneous payloads; typed once tools/ catalog stabilises. | backend | TBD |
| `src/services/metadata_service.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/model_fetcher.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/pagination.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/pipeline_launcher.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/pipeline_state_store.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/pipelines/service.py` | Legacy pipeline runner; pending refactor onto typed pipeline_run.PipelineRunStageState. | backend | TBD |
| `src/services/plan_agent_provider.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/plan_issue_service.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/plan_parser.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/rate_limit_tracker.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/settings_store.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/signal_bridge.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/signal_chat.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/signal_delivery.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/tools/catalog.py` | Tools catalog/service handles partially-typed registry entries pending schema rework. | backend | TBD |
| `src/services/tools/service.py` | Tools catalog/service handles partially-typed registry entries pending schema rework. | backend | TBD |
| `src/services/websocket.py` | Legacy service module; pending follow-up typing pass. | backend | TBD |
| `src/services/workflow_orchestrator/__init__.py` | Legacy workflow state machine; dict-based state mutation pending dataclass migration. | backend | TBD |
| `src/services/workflow_orchestrator/config.py` | Legacy workflow state machine; dict-based state mutation pending dataclass migration. | backend | TBD |
| `src/services/workflow_orchestrator/models.py` | Legacy workflow state machine; dict-based state mutation pending dataclass migration. | backend | TBD |
| `src/services/workflow_orchestrator/orchestrator.py` | Legacy workflow state machine; dict-based state mutation pending dataclass migration. | backend | TBD |
| `src/services/workflow_orchestrator/transitions.py` | Legacy workflow state machine; dict-based state mutation pending dataclass migration. | backend | TBD |
| `src/utils.py` | Legacy top-level module; pending follow-up typing pass. | backend | TBD |
