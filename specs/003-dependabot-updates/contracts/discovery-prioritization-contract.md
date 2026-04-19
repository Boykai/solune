# Contract: Discovery and Prioritization

## Purpose

Define the required inputs and outputs for discovering open Dependabot PRs and turning them into an ordered execution queue.

## Inputs

- GitHub open pull request inventory for `Boykai/solune`
- `.github/dependabot.yml`
- Default branch reference (`main`)
- Current manifest / lockfile / workflow / Dockerfile contents on the default branch

## Required discovery behavior

1. Include only pull requests whose author is `dependabot[bot]`.
2. Extract, per PR:
   - PR number
   - ecosystem
   - dependency name
   - current version
   - target version
   - changed file paths
   - source branch name
3. Group results by ecosystem exactly as configured in `.github/dependabot.yml`.
4. Detect overlaps when two or more PRs:
   - edit the same manifest, lockfile, workflow file, or Dockerfile
   - target the same dependency name
   - constrain the same dependency graph
5. Assign each candidate a priority tier:
   - `patch`
   - `minor`
   - `major`
   - `unknown` (fallback when semver parsing is not possible)
6. Sort the execution queue by:
   - priority tier (`patch` before `minor` before `major` before `unknown`)
   - isolated candidates before overlapping candidates
   - stable tie-breaker (PR number ascending is acceptable)

## Output shape

The discovery phase must produce a machine-readable or at least deterministic table/list where every entry contains:

| Field | Required |
|---|---|
| `pr_number` | yes |
| `ecosystem` | yes |
| `dependency_name` | yes |
| `current_version` | yes |
| `target_version` | yes |
| `bump_type` | yes |
| `source_paths` | yes |
| `overlap_status` | yes |
| `priority_position` | yes |

## Zero-result behavior

If no open Dependabot PRs exist, the phase must return an empty queue plus an explicit no-op message. This is a successful outcome and must not be treated as a failure.
