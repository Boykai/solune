# Research: Fleet-Dispatch Agent Pipelines via GitHub CLI

**Feature**: Fleet-Dispatch Agent Pipelines via GitHub CLI | **Date**: 2026-04-11 | **Status**: Complete

## R1: CLI Dispatch Mechanism — `gh api graphql` vs Higher-Level Commands

**Decision**: Use `gh api graphql` exclusively for production fleet dispatch. Higher-level commands (`gh agent-task create`, `gh issue edit --add-assignee`) are documented as convenience alternatives but not used in the dispatch script.

**Rationale**: The existing Python backend (`copilot.py → _assign_copilot_graphql()`) uses the `addAssigneesToAssignable` GraphQL mutation with the full `agentAssignment` input object. This mutation supports all required fields: `customAgent`, `customInstructions`, `model`, and `baseRef`. No higher-level `gh` CLI command currently exposes `--model` or `--custom-instructions` flags. Using `gh api graphql` ensures feature parity between the Python backend and the shell-based fleet dispatch.

The GraphQL mutation requires the header `GraphQL-Features: issues_copilot_assignment_api_support,coding_agent_model_selection` — already used in the existing `_graphql()` call in `copilot.py` (line 537).

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| `gh agent-task create` (v2.80+) | Supports `--custom-agent` and `--base` but lacks `--model` and `--custom-instructions` flags needed for full pipeline control |
| `gh issue edit N --add-assignee @copilot` | Only assigns Copilot — no custom agent, model, or instruction support |
| `gh issue create --assignee @copilot` | Combines issue creation + assignment but lacks `agentAssignment` input fields |
| Mixed approach (higher-level for simple, GraphQL for complex) | Adds code paths and branching logic; inconsistency increases debugging surface |

---

## R2: Parallel Dispatch Strategy — Background Processes vs `xargs`

**Decision**: Use Bash background processes (`&`) with `wait` for parallel group dispatch. Each agent in a parallel group spawns a concurrent `gh api graphql` call as a background process; `wait` blocks until all complete.

**Rationale**: The existing Python backend uses `asyncio.gather()` for parallel groups (see `execute_full_workflow()` in `orchestrator.py` line 2702 and `_advance_pipeline()` in `pipeline.py` line 2390). The Bash equivalent is `command & ... wait`, which:

- Maps 1:1 to the existing concurrency model (fire all, wait for all)
- Requires no additional dependencies (pure Bash)
- Captures exit codes per background job via `wait $pid; echo $?`
- Allows the script to detect partial failures (some agents succeed, some fail)

For serial groups, agents dispatch sequentially with completion polling between each agent.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| `xargs -P N` | Less control over per-process exit codes; harder to associate failures with specific agents |
| GNU `parallel` | External dependency not guaranteed on all systems; overkill for 3–5 concurrent processes |
| `tmux`/`screen` sessions | Over-engineered; designed for interactive sessions, not scripted dispatch |
| Node.js/Python subprocess wrapper | Defeats the purpose of a self-contained shell script; adds runtime dependency |

---

## R3: Pipeline Config Format — JSON Extraction from Python

**Decision**: Extract pipeline definitions to a standalone JSON file (`solune/config/pipeline-config.json`) that both the Python backend and the shell script consume. The Python `_PRESET_DEFINITIONS` in `pipelines/service.py` becomes the source of truth; a build-time extraction script generates the JSON.

**Rationale**: The current pipeline definitions live in two places:
1. Python backend: `PIPELINE_STAGES` in `pipeline_orchestrator.py` (lines 26–43) and `_PRESET_DEFINITIONS` in `pipelines/service.py` (lines 68–310)
2. Frontend TypeScript: `preset-pipelines.ts` (duplicate of backend presets)

A standalone JSON config enables the shell script to parse group/agent definitions with `jq` without importing Python. The Python code reads the same JSON at startup (replacing the inline dict literals), eliminating the frontend/backend duplication.

The JSON schema follows the existing `PipelineStage` / `ExecutionGroup` / `PipelineAgentNode` Pydantic models exactly, so no structural changes are needed.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| YAML config | Requires `yq` dependency for shell parsing; JSON is natively supported by `jq` and Python |
| TOML config | Awkward for nested arrays of objects (stages → groups → agents); limited shell tooling |
| Inline config in shell script | Duplicates definitions; diverges from Python source of truth over time |
| Environment variables | Cannot express nested group/agent hierarchies; limited to flat key-value pairs |

---

## R4: Custom Instructions Templating — `envsubst` vs Mustache

**Decision**: Use `envsubst` for instruction templating in the shell script. Template files use `${VARIABLE}` placeholders that are expanded at dispatch time from environment variables populated by the script.

**Rationale**: The existing Python functions `format_issue_context_as_prompt()` (agents.py:106) and `tailor_body_for_agent()` (agents.py:215) build custom instructions by string concatenation with agent-specific logic. The shell equivalent uses template files with `envsubst`:

- No additional dependencies — `envsubst` is part of GNU `gettext`, available on all Linux/macOS systems
- Templates are plain text with `${VAR}` markers — easy to read and maintain
- Variables are set before expansion: `ISSUE_TITLE`, `ISSUE_BODY`, `AGENT_NAME`, `AGENT_DESCRIPTION`, `PARENT_ISSUE_NUMBER`, `BASE_REF`, etc.
- Agent-specific sections use conditional includes (separate template files per agent type)

The template files live in `solune/config/templates/` alongside the pipeline JSON config.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Mustache (`mo` or `mustache.bash`) | External dependency; overkill for simple variable substitution |
| `sed` replacement | Fragile with special characters in issue bodies; no native variable scoping |
| Heredoc strings in shell | Inlined templates become unreadable; cannot be versioned/reviewed independently |
| Jinja2 (Python) | Requires Python runtime; defeats the purpose of a standalone shell script |

---

## R5: Completion Polling Strategy

**Decision**: Poll for agent completion using `gh api graphql` to check sub-issue status (open/closed) and PR merge status. Poll interval: 30 seconds with exponential backoff up to 5 minutes. Timeout: configurable, default 60 minutes per agent.

**Rationale**: The existing backend uses `copilot_polling/pipeline.py` with webhook-driven advancement (PR merge/close events trigger `_advance_pipeline()`). The shell script cannot register webhooks, so it polls instead.

The polling checks:
1. **Sub-issue state**: If the sub-issue is closed, the agent has completed (success or failure)
2. **PR status**: If a PR was created from the agent's branch, check merge status
3. **Agent task status**: `gh agent-task list --repo OWNER/REPO` for Copilot-specific completion signals

Exponential backoff prevents rate-limit exhaustion while maintaining responsiveness. The 60-minute default timeout matches the typical maximum Copilot agent session duration.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Fixed-interval polling (e.g., every 10s) | Wastes API calls; risks rate limiting over long agent runs |
| Webhook-based (start a local HTTP server) | Requires public URL or tunnel; impractical for local/CI environments |
| GitHub Actions workflow_dispatch event | Adds CI infrastructure dependency; not suitable for ad-hoc local dispatch |
| No polling (fire-and-forget) | Breaks serial group semantics; cannot advance to next group without completion signal |

---

## R6: Sub-Issue Creation Strategy

**Decision**: Pre-create all sub-issues for a pipeline run before dispatching any agents. Use `gh issue create` in a loop with appropriate labels and parent-issue linking. Store issue numbers and node IDs in a local JSON state file.

**Rationale**: The existing backend creates sub-issues before dispatch (see `execute_full_workflow()` which calls `_create_sub_issues()` before `_execute_copilot_assignment()`). Pre-creating all issues provides:

- **Visibility**: All planned work is visible in the GitHub project before execution begins
- **Labeling**: Each sub-issue gets `agent:{agent_name}` labels for filtering
- **Linking**: Sub-issues reference the parent issue via body text (`> Parent Issue: #N`)
- **State tracking**: The script writes a `fleet-state.json` file mapping agent → issue number → node ID

The `gh issue create` command returns the issue URL; the script parses it for the issue number. Node IDs are fetched via a follow-up `gh api graphql` query (required for the `addAssigneesToAssignable` mutation).

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Create issues on-demand (just before dispatch) | Serial groups must wait for the previous agent; pre-creation separates planning from execution |
| Use existing issues (assume pre-created) | Breaks the self-contained script model; requires external setup |
| Use GitHub Projects items directly | Issues are still needed for Copilot assignment; project items are metadata, not work containers |

---

## R7: Error Handling and Retry Strategy

**Decision**: Implement retry with exponential backoff (3 attempts, base delay 3 seconds) for GraphQL dispatch calls. Log failures to stderr with structured JSON. On partial group failure (some agents fail in a parallel group), continue with successful agents and report failures at completion.

**Rationale**: The existing Python backend uses a 3-retry loop with exponential backoff in `_execute_copilot_assignment()` (orchestrator.py line 1731). The shell script mirrors this:

```bash
for attempt in 1 2 3; do
  if gh api graphql ...; then break; fi
  sleep $((3 * attempt))
done
```

Partial failure handling follows the same pattern as the Python backend's `asyncio.gather()` results processing (orchestrator.py lines 2712–2733): successful agents proceed, failed agents are logged, and the overall run reports partial success.
