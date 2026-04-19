# Contract: Batch PR and Cleanup Report

## Purpose

Define the required shape of the combined pull request and the cleanup behavior for successful vs. skipped Dependabot updates.

## Batch PR requirements

- **Title**: `chore(deps): apply Dependabot batch update`
- **Base branch**: repository default branch (`main`)
- **Creation rule**: create the PR only when at least one update is successfully retained

## Required PR description sections

### 1. Applied updates checklist

Each successful update must appear as a checklist entry in the form:

```text
- [x] <dependency-name> <old-version> -> <new-version> (<ecosystem>, PR #<number>)
```

### 2. Skipped updates section

Each skipped update must appear in the form:

```text
- <dependency-name> <target-version> (PR #<number>): <one-line failure summary>
```

If the skip was caused by a major-version migration requirement, append the migration note after the failure summary.

## Cleanup behavior

### Successful updates

For every Dependabot PR whose change is absorbed into the combined batch PR:

1. Close the Dependabot PR.
2. Delete its remote Dependabot branch.
3. Record the cleanup action in the batch report.

### Skipped updates

For every Dependabot PR that fails blocking verification:

1. Leave the Dependabot PR open.
2. Leave its remote branch intact.
3. Include the skip reason in the batch report.

## Empty-batch behavior

If no updates are applied successfully:

- Do not create a combined PR.
- Emit a no-op or skipped summary instead.
- Perform no PR-closing or branch-deletion actions.
