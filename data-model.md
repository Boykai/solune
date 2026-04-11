# Data Model: Fleet-Dispatch Agent Pipelines via GitHub CLI

**Feature**: Fleet-Dispatch Agent Pipelines via GitHub CLI | **Date**: 2026-04-11 | **Status**: Complete

## Entity: PipelineConfig (JSON — `pipeline-config.json`)

The canonical pipeline definition consumed by both the Python backend (`PipelineService.seed_presets()`) and the Bash fleet-dispatch script. Replaces the inline `_PRESET_DEFINITIONS` in `pipelines/service.py`.

### Fields

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `preset_id` | string | REQUIRED, unique | — | Unique identifier for the preset (e.g., `"spec-kit"`, `"expert"`) |
| `name` | string | REQUIRED, 1–100 chars | — | Human-readable pipeline name |
| `description` | string | Optional, max 500 chars | `""` | Pipeline description |
| `stages` | array[Stage] | REQUIRED, ≥1 element | — | Ordered list of pipeline stages |

### Nested: Stage

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | string | REQUIRED | — | Unique stage identifier |
| `name` | string | REQUIRED, 1–100 chars | — | Human-readable stage name (e.g., `"Backlog"`, `"In progress"`) |
| `order` | integer | REQUIRED, ≥0 | — | Execution order (0-indexed) |
| `groups` | array[ExecutionGroup] | REQUIRED | `[]` | Execution groups within the stage |
| `agents` | array[AgentNode] | Optional | `[]` | Flattened list of all agents in the stage (backward-compatible convenience field derived from groups) |
| `execution_mode` | enum | `"sequential"` or `"parallel"` | `"sequential"` | Stage-level execution mode (backward-compatible convenience field) |

### Nested: ExecutionGroup

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | string | REQUIRED | — | Unique group identifier |
| `order` | integer | ≥0 | `0` | Group execution order within stage |
| `execution_mode` | enum | `"sequential"` or `"parallel"` | `"sequential"` | How agents in this group are dispatched |
| `agents` | array[AgentNode] | REQUIRED | `[]` | Agents in this group |

### Nested: AgentNode

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | string | REQUIRED | — | Unique agent node identifier |
| `agent_slug` | string | REQUIRED | — | Agent identifier (e.g., `"speckit.specify"`, `"judge"`) |
| `agent_display_name` | string | Optional | `""` | Human-readable agent name |
| `model_id` | string | Optional | `""` | Model override (empty = auto/default) |
| `model_name` | string | Optional | `""` | Human-readable model name |
| `tool_ids` | array[string] | Optional | `[]` | Tool overrides |
| `tool_count` | integer | ≥0 | `0` | Number of tools |
| `config` | object | Optional | `{}` | Agent-specific configuration overrides |

### Relationships

| Related Entity | Cardinality | Description |
|---------------|-------------|-------------|
| PipelineConfig → Stage | 1:N | Each pipeline has ordered stages |
| Stage → ExecutionGroup | 1:N | Each stage has ordered execution groups |
| ExecutionGroup → AgentNode | 1:N | Each group contains agents |

### Validation Rules

- `preset_id` must be unique across all pipeline configs
- Stage `order` values must be contiguous starting from 0
- `execution_mode` must be either `"sequential"` or `"parallel"`
- At least one stage is required per pipeline
- `agent_slug` must match a known agent slug from `AgentsMixin.BUILTIN_AGENTS` or a custom agent

### Mapping to Existing Pydantic Models

| JSON Field | Pydantic Model | Python Field |
|-----------|----------------|--------------|
| PipelineConfig | `PipelineConfig` | `models/pipeline.py` |
| Stage | `PipelineStage` | `models/pipeline.py` |
| ExecutionGroup | `ExecutionGroup` | `models/pipeline.py` |
| AgentNode | `PipelineAgentNode` | `models/pipeline.py` |

---

## Entity: FleetState (JSON — `fleet-state.json`)

Local state file written by the fleet-dispatch script to track dispatch progress. Created at the start of a dispatch run; updated as agents are dispatched and complete.

### Fields

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `run_id` | string (UUID) | REQUIRED | auto-generated | Unique identifier for this dispatch run |
| `repo` | string | REQUIRED | — | Repository in `owner/repo` format |
| `parent_issue` | integer | REQUIRED | — | Parent issue number |
| `base_ref` | string | REQUIRED | `"main"` | Branch to base agent PRs on |
| `pipeline_preset` | string | REQUIRED | — | Preset ID from pipeline config |
| `started_at` | string (ISO 8601) | REQUIRED | auto-generated | Dispatch start timestamp |
| `completed_at` | string (ISO 8601) | Optional | `null` | Dispatch completion timestamp |
| `status` | enum | `"running"`, `"completed"`, `"partial_failure"`, `"failed"` | `"running"` | Overall run status |
| `agents` | array[AgentDispatch] | REQUIRED | `[]` | Per-agent dispatch records |

### Nested: AgentDispatch

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `agent_slug` | string | REQUIRED | — | Agent identifier |
| `group_id` | string | REQUIRED | — | Execution group this agent belongs to |
| `execution_mode` | enum | `"sequential"` or `"parallel"` | — | Group's execution mode |
| `issue_number` | integer | Optional | `null` | Created sub-issue number |
| `issue_node_id` | string | Optional | `null` | GitHub GraphQL node ID for the sub-issue |
| `dispatch_status` | enum | `"pending"`, `"dispatched"`, `"completed"`, `"failed"`, `"timed_out"` | `"pending"` | Current dispatch state |
| `dispatched_at` | string (ISO 8601) | Optional | `null` | When the agent was dispatched |
| `completed_at` | string (ISO 8601) | Optional | `null` | When the agent completed |
| `pr_number` | integer | Optional | `null` | PR created by the agent (if any) |
| `pr_merged` | boolean | Optional | `false` | Whether the agent's PR was merged |
| `error` | string | Optional | `null` | Error message if dispatch/completion failed |
| `retry_count` | integer | ≥0 | `0` | Number of dispatch retry attempts |

### State Transitions

```text
pending → dispatched → completed
pending → dispatched → failed
pending → dispatched → timed_out
pending → failed (dispatch failure after retries)
```

### Validation Rules

- `run_id` is a UUID v4 string generated at dispatch start
- `status` is derived: `"completed"` if all agents are `"completed"`, `"partial_failure"` if some failed, `"failed"` if all failed
- `fleet-state.json` is written atomically (write to temp file, then `mv`)
- File is created in the current working directory or a path specified by `--state-dir`

---

## Entity: AgentInstructionTemplate (file — `config/templates/*.tpl`)

Template files for generating custom instructions passed to agents via the `customInstructions` field of the GraphQL mutation. Uses `envsubst` variable expansion.

### Template Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `${ISSUE_TITLE}` | Parent issue title | Title of the parent GitHub issue |
| `${ISSUE_BODY}` | Parent issue body (cleaned) | Body text with tracking tables stripped |
| `${AGENT_NAME}` | Pipeline config | Agent slug (e.g., `speckit.specify`) |
| `${AGENT_DESCRIPTION}` | Agent descriptions map | Human-readable task description |
| `${PARENT_ISSUE_NUMBER}` | CLI argument | Parent issue number for cross-referencing |
| `${PARENT_ISSUE_TITLE}` | Parent issue title | For sub-issue body generation |
| `${BASE_REF}` | CLI argument | Branch to base PRs on |
| `${REPO_OWNER}` | CLI argument | Repository owner |
| `${REPO_NAME}` | CLI argument | Repository name |
| `${EXISTING_PR_NUMBER}` | Dispatch state | PR number if reusing existing PR |
| `${EXISTING_PR_BRANCH}` | Dispatch state | Branch name if reusing existing PR |

### Template Files

| File | Agent(s) | Purpose |
|------|----------|---------|
| `agent-instructions.tpl` | All | Base template with issue context and output instructions |
| `speckit-specify.tpl` | `speckit.specify` | Specification-specific output file instructions (`spec.md`) |
| `speckit-plan.tpl` | `speckit.plan` | Plan-specific output file instructions (`plan.md`) |
| `speckit-tasks.tpl` | `speckit.tasks` | Tasks-specific output file instructions (`tasks.md`) |
| `speckit-implement.tpl` | `speckit.implement` | Implementation instructions (no specific output files) |
| `copilot-review.tpl` | `copilot-review` | PR review tracking sub-issue template |

### Relationship to Existing Code

The template content is derived from:
- `format_issue_context_as_prompt()` in `agents.py:106–205` — issue context formatting
- `tailor_body_for_agent()` in `agents.py:215–298` — agent-specific body tailoring
- `agent_descriptions` dict in `agents.py:233–248` — agent task descriptions
- `agent_files` dict in `agents.py:169–175` — output file mappings per agent

