# Research: Fleet-Dispatch Agent Pipelines via GitHub CLI

## Decision 1: Use `gh api graphql` as the production dispatch primitive

- **Decision**: Mirror `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/graphql.py` and `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/copilot.py` by issuing `addAssigneesToAssignable` through `gh api graphql` with `customAgent`, `customInstructions`, `model`, and `baseRef`, plus the required `GraphQL-Features` header.
- **Rationale**: The existing backend already depends on this payload shape for custom-agent routing and model selection. Reusing the same mutation preserves behavioral parity and avoids inventing a separate CLI-only assignment mechanism.
- **Alternatives considered**:
  - `gh issue edit --add-assignee @copilot` — rejected because it cannot carry model selection or custom instructions.
  - `gh agent-task create` — rejected as the primary path because it does not expose the full `agentAssignment` input used by the backend today.

## Decision 2: Extract the fleet definition from the current hard-coded pipeline groups

- **Decision**: Treat `/home/runner/work/solune/solune/solune/backend/src/services/pipeline_orchestrator.py` as the canonical source for the first standalone fleet config and convert its four ordered groups into JSON with explicit group mode, agent order, template reference, and model metadata.
- **Rationale**: That file already captures the serial/parallel boundaries called out in the issue (`Group 1` serial, `Group 2` and `Group 3` parallel, `Group 4` serial). Promoting that shape into JSON lets the shell entry point and backend loader consume the same source of truth.
- **Alternatives considered**:
  - Reconstruct the config from `DEFAULT_AGENT_MAPPINGS` in `/home/runner/work/solune/solune/solune/backend/src/constants.py` — rejected because it flattens groups and loses the current parallel boundaries.
  - Create a shell-only config unrelated to backend models — rejected because SC-003 requires parity between CLI and backend consumption.

## Decision 3: Reuse existing prompt-formatting behavior via file-based templates

- **Decision**: Port the behavior of `format_issue_context_as_prompt()` and `tailor_body_for_agent()` from `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/agents.py` into repository templates rendered by the shell script with environment substitution.
- **Rationale**: Those functions already encode branch reuse notes, issue title/body/comment formatting, agent-specific descriptions, and output expectations. Template files keep the rendered instructions inspectable while preserving parity with current Python behavior.
- **Alternatives considered**:
  - Hard-code prompts directly in `fleet-dispatch.sh` — rejected because it would duplicate large prompt bodies and make agent-specific maintenance brittle.
  - Introduce a heavy templating runtime such as Mustache or Jinja — rejected because the spec assumes standard shell utilities only.

## Decision 4: Model monitoring around GitHub CLI polling plus per-agent dispatch records

- **Decision**: Poll dispatch state with `gh agent-task list`, `gh agent-task view`, and sub-issue metadata, and record each agent run as a dispatch record keyed by parent issue, group, agent slug, and sub-issue number.
- **Rationale**: The spec requires near-real-time status, timeout detection, and a final summary. A dispatch-record model gives the CLI enough structured state to support full-pipeline runs, resumable monitoring, and single-agent retry without relying on backend memory.
- **Alternatives considered**:
  - Depend only on Copilot assignee presence on issues — rejected because it is insufficient for queued vs. in-progress vs. failed differentiation.
  - Introduce a new backend polling service for CLI runs — rejected because SC-008 requires the runtime path to work with `gh`, bash, and `jq` alone.

## Decision 5: Keep validation and testing inside existing pytest-based tooling

- **Decision**: Validate the extracted JSON config with a JSON Schema contract and cover config loading, template rendering, and shell command construction with targeted `pytest` tests in `/home/runner/work/solune/solune/solune/backend/tests/unit/`.
- **Rationale**: The repository already has fast backend unit tests for pipeline orchestration and GitHub-agent prompt generation, and `uv run pytest tests/unit/test_pipeline_orchestrator.py tests/unit/test_github_agents.py -q` currently passes. Reusing pytest avoids adding Bats or another dedicated shell-test framework.
- **Alternatives considered**:
  - Add a separate shell-test framework — rejected because it would increase maintenance surface for a feature that can be tested through subprocess calls and mocked `gh` responses.
  - Skip automated tests — rejected because the spec explicitly requires behavior parity, validation, retry handling, and monitoring correctness.
