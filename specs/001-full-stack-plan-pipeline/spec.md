# Feature Specification: Full-Stack Plan Pipeline Enhancement (v2 — Copilot SDK + MAF)

**Branch**: `001-full-stack-plan-pipeline` | **Date**: 2026-04-04 | **Parent Issue**: #716

## Overview

Evolve the `/plan` pipeline into a versioned, step-editable planning surface powered by the Copilot Python SDK's native multi-agent, session hook, and streaming primitives instead of rolling custom orchestration. The project already wraps `CopilotClient` behind `GitHubCopilotAgent` in `agent_provider.py`; this upgrade exploits SDK v1.0.17 capabilities to reduce bespoke plumbing and gain CLI/IDE interoperability.

## User Stories

### P1: SDK Agent Orchestration Layer

**As a** developer using Solune's plan pipeline,
**I want** plan mode to use dedicated Copilot SDK custom agents with tool whitelists and per-agent system prompts,
**So that** plan generation is isolated from general chat with proper tool access control and CLI interoperability.

**Acceptance Criteria**:
- Given the Copilot SDK ≥1.0.17 is installed, when a user enters plan mode, then a dedicated `solune-plan` custom agent session is created with only `get_project_context`, `get_pipeline_list`, and `save_plan` tools whitelisted
- Given a plan session is active, when the agent invokes `save_plan`, then a pre-tool hook automatically snapshots the current plan version before overwrite
- Given the plan pipeline runs, when speckit agents execute, then sub-agent events (`subagent.started/completed/failed`) drive stage transitions via a pipeline orchestrator
- Given SDK streaming is active, when the agent generates content, then SDK events (`assistant.reasoning_delta`, `tool.execution_start`) map to enhanced SSE events

**Independent Test**: Create a plan session with custom agents, verify tool whitelist enforcement, confirm hook fires on `save_plan`

### P2: Plan Versioning and Iterative Refinement

**As a** user refining an implementation plan,
**I want** automatic version snapshots on every save and step-level feedback via SDK elicitation,
**So that** I can review plan history, provide per-step comments, and iteratively improve the plan.

**Acceptance Criteria**:
- Given a plan exists, when `save_plan` is called, then the previous version is automatically snapshotted in `chat_plan_versions` via the session hook
- Given a plan with versions, when I request history via `GET /plans/{plan_id}/history`, then I receive all version snapshots with timestamps
- Given a plan step, when I submit feedback via `POST /plans/{plan_id}/steps/{step_id}/feedback`, then the SDK elicitation handler routes the feedback to the agent
- Given the refinement sidebar is active, when I click "Request Changes" on a step, then an inline comment input appears and the agent receives structured feedback

**Independent Test**: Save a plan twice, verify two version snapshots exist; submit step feedback and confirm agent receives it

### P3: Step CRUD and Dependency Graph

**As a** user managing plan steps,
**I want** full step mutation capabilities (add/edit/delete/reorder) with DAG validation and visual dependency graph,
**So that** I can fine-tune the implementation plan structure and understand step relationships.

**Acceptance Criteria**:
- Given a draft plan, when I add/edit/delete steps via API or agent tools, then the plan updates with DAG validation ensuring no circular dependencies
- Given plan steps with dependencies, when I view the dependency graph, then a visual DAG renders showing step relationships
- Given a step, when I approve it individually, then per-step approval status is tracked separately from plan status
- Given the agent has `@define_tool` registered step mutation tools, when the agent adds/edits/deletes steps programmatically, then the same CRUD and validation logic applies

**Independent Test**: Create steps with dependencies, verify DAG validation rejects cycles; use agent tools to mutate steps

### P4 (Stretch): Copilot CLI Plugin and ACP Interop

**As a** developer using Copilot CLI,
**I want** to access Solune's plan pipeline via `copilot /plugin install` and ACP server endpoints,
**So that** I can create and manage plans from the command line and IDE without the web UI.

**Acceptance Criteria**:
- Given the CLI plugin is installed, when I run plan commands via Copilot CLI, then the same plan pipeline executes as in the web UI
- Given ACP mode is enabled, when external tools connect via Agent Client Protocol, then the plan pipeline is accessible for integration

**Independent Test**: Install CLI plugin, create a plan via CLI commands; connect via ACP and verify pipeline access

## Out of Scope

- General chat agent changes (only plan mode affected)
- Mobile-specific UI (web-first)
- Breaking changes to existing plan approval flow (additive only)
- Azure OpenAI provider changes (Copilot SDK only)
