# Quickstart: Fleet-Dispatch Agent Pipelines via GitHub CLI

## Prerequisites

1. Authenticate GitHub CLI:

   ```bash
   gh auth status
   gh --version
   jq --version
   ```

2. Prepare a pipeline config that matches `/home/runner/work/solune/solune/specs/001-fleet-dispatch-pipelines/contracts/pipeline-config.schema.json`.

3. Ensure the parent issue already exists in `Boykai/solune` and that Copilot assignment is enabled for the repository.

## Full pipeline dispatch

```bash
cd /home/runner/work/solune/solune

bash /home/runner/work/solune/solune/solune/scripts/fleet-dispatch.sh \
  --owner Boykai \
  --repo solune \
  --parent-issue 1555 \
  --config /home/runner/work/solune/solune/solune/scripts/pipelines/fleet-dispatch.json \
  --base-ref copilot/speckit-specify-fleet-dispatch-agent-pipelines \
  --error-strategy continue
```

### Expected flow

1. Validate `gh` and `jq` availability plus authentication.
2. Validate the pipeline JSON against the config schema.
3. Create or resume sub-issues for every configured agent.
4. Dispatch Group 1 serially.
5. Dispatch Groups 2 and 3 in parallel, waiting on each group boundary.
6. Poll `gh agent-task list` / `gh agent-task view` until all active agents reach terminal states.
7. Print a final summary with elapsed time, status counts, and sub-issue links.

## Monitor an active dispatch

```bash
gh agent-task list --repo Boykai/solune
gh agent-task view <task-id> --repo Boykai/solune
```

Use the CLI summary output plus the `DispatchRecord` model from `/home/runner/work/solune/solune/specs/001-fleet-dispatch-pipelines/data-model.md` to correlate task IDs, agent slugs, and sub-issues.

## Retry a single agent

```bash
cd /home/runner/work/solune/solune

bash /home/runner/work/solune/solune/solune/scripts/fleet-dispatch.sh \
  --owner Boykai \
  --repo solune \
  --parent-issue 1555 \
  --config /home/runner/work/solune/solune/solune/scripts/pipelines/fleet-dispatch.json \
  --agent linter \
  --sub-issue 1568 \
  --retry
```

### Retry behavior

- Unassign Copilot from the existing sub-issue if needed.
- Re-render the instruction template with the latest issue context.
- Re-dispatch only the named agent.
- Leave all other group and sub-issue state untouched.
