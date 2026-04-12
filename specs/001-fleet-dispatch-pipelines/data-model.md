# Data Model: Fleet-Dispatch Agent Pipelines via GitHub CLI

## 1. PipelineConfig

**Purpose**: Portable source of truth shared by the shell dispatcher and backend loader.

| Field | Type | Required | Validation / Notes |
|---|---|---|---|
| `version` | string | yes | Initial contract version, e.g. `"1"` |
| `name` | string | yes | Human-readable pipeline name |
| `repository.owner` | string | yes | GitHub owner/org slug |
| `repository.name` | string | yes | GitHub repository name |
| `defaults.baseRef` | string | yes | Default branch/PR base ref |
| `defaults.errorStrategy` | enum | yes | `fail-fast` or `continue` |
| `defaults.pollIntervalSeconds` | integer | yes | `>= 5` |
| `defaults.taskTimeoutSeconds` | integer | yes | `>= pollIntervalSeconds` |
| `groups` | array\<ExecutionGroup\> | yes | Ordered, at least one group |

**Relationships**:
- Contains one or more `ExecutionGroup` records.
- References one `InstructionTemplate` per agent entry.

## 2. ExecutionGroup

**Purpose**: Ordered dispatch boundary that decides whether agents run serially or in parallel.

| Field | Type | Required | Validation / Notes |
|---|---|---|---|
| `id` | string | yes | Stable identifier used in logs and summaries |
| `name` | string | yes | Operator-facing stage/group label |
| `order` | integer | yes | Unique ascending order within a pipeline |
| `executionMode` | enum | yes | `serial` or `parallel` |
| `agents` | array\<PipelineAgent\> | yes | At least one agent |

**Relationships**:
- Belongs to one `PipelineConfig`.
- Owns one or more `PipelineAgent` records.

## 3. PipelineAgent

**Purpose**: Declarative description of one agent dispatch.

| Field | Type | Required | Validation / Notes |
|---|---|---|---|
| `slug` | string | yes | GitHub/custom agent slug such as `speckit.plan` or `judge` |
| `displayName` | string | no | Human-readable label for summaries |
| `customAgent` | string | yes | Value passed to `agentAssignment.customAgent` (empty for built-in Copilot) |
| `model` | string | yes | Copilot model name used in GraphQL payload |
| `instructionTemplate` | string | yes | Repository-relative template path |
| `subIssue.title` | string | yes | Title template for sub-issue creation |
| `subIssue.labels` | array\<string\> | yes | Must include pipeline/agent linkage labels |
| `retryable` | boolean | yes | Enables single-agent retry workflow |

**Relationships**:
- Belongs to one `ExecutionGroup`.
- Produces zero or one `SubIssueRecord` per dispatch attempt.
- Produces one or more `DispatchRecord` entries over retries.

## 4. InstructionTemplate

**Purpose**: File-based prompt template rendered before assignment.

| Field | Type | Required | Validation / Notes |
|---|---|---|---|
| `path` | string | yes | Repository-relative template file |
| `agentSlug` | string | yes | Agent-specific template owner |
| `fallback` | boolean | yes | Marks generic fallback template |
| `placeholders` | array\<string\> | yes | Supported substitution variable names for the template |

**Relationships**:
- Referenced by `PipelineAgent`.
- Rendered using parent-issue context and optional existing PR metadata.

**Supported placeholders**:
- `ISSUE_TITLE`
- `ISSUE_BODY`
- `ISSUE_COMMENTS`
- `PARENT_ISSUE_NUMBER`
- `PARENT_ISSUE_URL`
- `BASE_REF`
- `PR_BRANCH`

## 5. SubIssueRecord

**Purpose**: Captures the GitHub issue created for an agent.

| Field | Type | Required | Validation / Notes |
|---|---|---|---|
| `number` | integer | yes | GitHub issue number |
| `nodeId` | string | yes | Required by GraphQL assignment |
| `url` | string | yes | HTML URL for summaries |
| `parentIssueNumber` | integer | yes | Links back to the workflow root |
| `agentSlug` | string | yes | Matches the owning agent |
| `labels` | array\<string\> | yes | Includes pipeline and agent labels |

**Relationships**:
- Created from one `PipelineAgent`.
- Referenced by one or more `DispatchRecord` entries.

## 6. DispatchRecord

**Purpose**: Tracks one attempt to assign and monitor an agent.

| Field | Type | Required | Validation / Notes |
|---|---|---|---|
| `dispatchId` | string | yes | Unique identifier for the overall fleet run |
| `attempt` | integer | yes | Starts at `1`, increments on retry |
| `groupId` | string | yes | Execution group for ordering |
| `agentSlug` | string | yes | Agent being dispatched |
| `subIssueNumber` | integer | yes | GitHub issue target |
| `status` | enum | yes | `pending`, `queued`, `in_progress`, `completed`, `failed`, `timed_out`, `skipped` |
| `startedAt` | datetime | no | Present after dispatch starts |
| `completedAt` | datetime | no | Present on terminal states |
| `errorMessage` | string | no | Populated on failure/timeout |
| `taskId` | string | no | `gh agent-task` identifier when available |

**Relationships**:
- Belongs to one `PipelineConfig` run.
- References one `SubIssueRecord`.

## State Transitions

### DispatchRecord

```text
pending
  ├──> queued
  │     └──> in_progress
  │            ├──> completed
  │            ├──> failed
  │            └──> timed_out
  └──> skipped

failed/timed_out
  └──> pending   # new retry attempt for the same agent/sub-issue
```

### Execution semantics

- Groups run strictly by ascending `order`.
- `executionMode=serial` waits for each agent's `DispatchRecord` to reach a terminal state before dispatching the next agent.
- `executionMode=parallel` dispatches all agents in the group first, then waits until every record reaches a terminal state before advancing.
