# Quickstart: Fleet-Dispatch Agent Pipelines via GitHub CLI

**Feature**: Fleet-Dispatch Agent Pipelines via GitHub CLI | **Date**: 2026-04-11

## Prerequisites

- `gh` CLI ≥2.80 (with `gh agent-task` support)
- `jq` ≥1.6
- `envsubst` (GNU `gettext` package)
- Authenticated GitHub session (`gh auth login`)
- Repository with GitHub Copilot agent access enabled

## Verify Prerequisites

```bash
# Check gh CLI version (must be ≥2.80)
gh --version

# Check jq availability
jq --version

# Check envsubst availability
envsubst --version

# Verify GitHub authentication
gh auth status
```

## Phase 1: Fleet Dispatch Script

### Basic Usage

```bash
# Dispatch a pipeline for a parent issue
cd solune
./scripts/fleet-dispatch.sh \
  --repo "owner/repo" \
  --parent-issue 1386 \
  --config config/pipeline-config.json \
  --preset "spec-kit" \
  --base-ref "main"
```

### Dry Run (no actual dispatch)

```bash
# Preview what would be dispatched without executing
./scripts/fleet-dispatch.sh \
  --repo "owner/repo" \
  --parent-issue 1386 \
  --config config/pipeline-config.json \
  --preset "expert" \
  --base-ref "main" \
  --dry-run
```

### Custom Model Override

```bash
# Override the default model for all agents
./scripts/fleet-dispatch.sh \
  --repo "owner/repo" \
  --parent-issue 1386 \
  --config config/pipeline-config.json \
  --preset "spec-kit" \
  --base-ref "main" \
  --model "claude-sonnet-4"
```

### Expected Output

```
[fleet-dispatch] Loading pipeline config: config/pipeline-config.json
[fleet-dispatch] Preset: spec-kit (5 stages, 8 agents)
[fleet-dispatch] Parent issue: #1386
[fleet-dispatch] Base ref: main

[fleet-dispatch] Creating sub-issues...
  ✓ speckit.specify → #1387
  ✓ speckit.plan → #1388
  ✓ speckit.tasks → #1389
  ✓ speckit.implement → #1390
  ✓ speckit.analyze → #1391

[fleet-dispatch] Dispatching Stage 1: Backlog (sequential)
  → Dispatching speckit.specify to #1387... ✓
  → Polling for completion...

[fleet-dispatch] Dispatching Stage 2: Ready (sequential)
  → Dispatching speckit.plan to #1388... ✓
  → Polling for completion...

[fleet-dispatch] Dispatching Stage 3: In progress (parallel)
  → Dispatching quality-assurance to #1392... (background)
  → Dispatching tester to #1393... (background)
  → Dispatching copilot-review to #1394... (background)
  → Waiting for parallel group to complete...
  ✓ All 3 agents completed

[fleet-dispatch] Summary:
  Agents dispatched: 8/8
  Successful: 8
  Failed: 0
  Duration: 2h 15m
  State file: fleet-state.json
```

## Phase 2: Pipeline Config Extraction

### Extract Config from Python Backend

```bash
# Generate pipeline-config.json from backend preset definitions
cd solune
python scripts/extract-pipeline-config.py \
  --source backend/src/services/pipelines/service.py \
  --output config/pipeline-config.json

# Validate the generated config against the JSON schema
# NOTE: ./scripts/validate-contracts.sh currently validates only OpenAPI → TypeScript
# type generation and does not accept a pipeline config file path argument.
# JSON Schema validation for pipeline configs will be added in a later phase.
# For now, validate manually:
python -m jsonschema -i config/pipeline-config.json contracts/pipeline-config-schema.json
```

### Inspect the Config

```bash
# List all presets
jq '.[].preset_id' config/pipeline-config.json

# Show agents in the "expert" pipeline
jq '.[] | select(.preset_id == "expert") | .stages[].groups[].agents[].agent_slug' \
  config/pipeline-config.json

# Show parallel groups
jq '.[] | select(.preset_id == "expert") | .stages[].groups[] | select(.execution_mode == "parallel") | {id, agents: [.agents[].agent_slug]}' \
  config/pipeline-config.json
```

## Phase 3: Monitoring

### Check Dispatch State

```bash
# View current dispatch state
jq '.' fleet-state.json

# Show agent statuses
jq '.agents[] | {agent_slug, dispatch_status, issue_number}' fleet-state.json

# Show only failed agents
jq '.agents[] | select(.dispatch_status == "failed")' fleet-state.json
```

### Manual Completion Polling

```bash
# Check if a sub-issue is closed (agent completed)
gh issue view 1387 --repo owner/repo --json state -q '.state'

# List Copilot agent tasks
gh agent-task list --repo owner/repo

# View a specific agent task
gh agent-task view TASK_ID --repo owner/repo
```

## Development & Testing

### Run Shell Script Tests

```bash
# Install bats-core (Bash Automated Testing System)
# macOS: brew install bats-core
# Ubuntu/Debian: sudo apt-get install bats
# Or from source: https://bats-core.readthedocs.io/en/stable/installation.html

# Run fleet-dispatch tests
bats solune/scripts/tests/fleet-dispatch.bats
```

### Run Python Extraction Tests

```bash
cd solune/backend
python -m pytest tests/unit/test_extract_pipeline_config.py -v
```

### Manual Verification

```bash
# 1. Verify the GraphQL mutation works with gh CLI
gh api graphql \
  -H "GraphQL-Features: issues_copilot_assignment_api_support,coding_agent_model_selection" \
  -f query='
    mutation($issueId: ID!, $assigneeIds: [ID!]!, $repoId: ID!, $baseRef: String!, $customInstructions: String!, $customAgent: String!, $model: String!) {
      addAssigneesToAssignable(input: {
        assignableId: $issueId,
        assigneeIds: $assigneeIds,
        agentAssignment: {
          targetRepositoryId: $repoId,
          baseRef: $baseRef,
          customInstructions: $customInstructions,
          customAgent: $customAgent,
          model: $model
        }
      }) {
        assignable {
          ... on Issue {
            id
            assignees(first: 10) { nodes { login } }
          }
        }
      }
    }
  ' \
  -f issueId="ISSUE_NODE_ID" \
  -f assigneeIds='["COPILOT_BOT_ID"]' \
  -f repoId="REPO_NODE_ID" \
  -f baseRef="main" \
  -f customInstructions="Your instructions here" \
  -f customAgent="speckit.specify" \
  -f model="claude-opus-4.6"

# 2. Verify sub-issue creation
gh issue create \
  --repo owner/repo \
  --title "[speckit.specify] Feature Name" \
  --body "> **Parent Issue:** #1386 — Feature Name" \
  --label "agent:speckit.specify"
```
