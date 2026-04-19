# Data Model: Dependabot Batch Update Workflow

## Entity: Dependabot Pull Request

| Field | Type | Description |
|---|---|---|
| `number` | integer | GitHub PR number |
| `title` | string | PR title, usually containing dependency and version bump |
| `author` | string | Must be `dependabot[bot]` for in-scope records |
| `ecosystem` | enum(`pip`, `npm`, `docker`, `github-actions`) | Source ecosystem from Dependabot config / PR metadata |
| `dependency_name` | string | Package, action, or base image being updated |
| `current_version` | string | Version currently on the default branch |
| `target_version` | string | Version proposed by the PR |
| `bump_type` | enum(`patch`, `minor`, `major`, `unknown`) | Semver delta used for prioritization |
| `source_paths` | string[] | Manifest/workflow/Dockerfile paths modified by the update |
| `branch_name` | string | Remote Dependabot branch backing the PR |
| `overlap_keys` | string[] | Keys used to detect shared dependency surfaces |
| `state` | enum(`open`, `applied`, `skipped`, `closed`) | Lifecycle state during batch processing |

**Validation rules**:

- `author` must equal `dependabot[bot]`.
- `state` begins as `open` and can only move forward through the update workflow.
- `bump_type` should be derived from semantic versions when possible; otherwise mark `unknown` and treat conservatively.
- `source_paths` must stay within `.github/`, `solune/backend/`, or `solune/frontend/`.

## Entity: Update Candidate

| Field | Type | Description |
|---|---|---|
| `pr_number` | integer | Reference to the Dependabot PR |
| `priority_tier` | integer | `1=patch`, `2=minor`, `3=major`, `4=unknown` |
| `overlap_status` | enum(`isolated`, `overlapping`) | Whether the candidate shares files/dependency graph with another candidate |
| `manifest_paths` | string[] | Primary files to edit/apply from the PR |
| `lockfile_paths` | string[] | Lockfiles that must be regenerated |
| `requires_migration_review` | boolean | True for major bumps or non-semver changes |
| `verification_profiles` | string[] | Names of command groups required to accept the update |

**Relationships**:

- Each `Update Candidate` is created from exactly one `Dependabot Pull Request`.
- Each candidate produces at most one `Update Attempt Result`.
- Multiple candidates can belong to the same `Overlap Group`.

## Entity: Overlap Group

| Field | Type | Description |
|---|---|---|
| `key` | string | Shared surface identifier such as `pip:solune/backend/pyproject.toml` |
| `ecosystem` | enum | Ecosystem of the shared surface |
| `members` | integer[] | PR numbers that overlap on this surface |
| `reason` | string | Human-readable explanation of the overlap |

**Validation rules**:

- A group must contain at least two members.
- `key` must identify a concrete file or dependency graph surface.

## Entity: Verification Profile

| Field | Type | Description |
|---|---|---|
| `name` | string | Stable identifier such as `backend-core`, `frontend-core`, `repo-cross-checks` |
| `working_directory` | string | Directory from which commands run |
| `commands` | string[] | Ordered shell commands |
| `blocking` | boolean | Whether failure rejects the update |
| `applies_to` | enum[] | Ecosystems that require the profile |

**Profiles expected for this feature**:

- `backend-core`: backend install, audit, lint, type checks, and pytest.
- `frontend-core`: frontend install, audit, lint, type checks, tests, and build.
- `repo-cross-checks`: docs lint, diagrams, contract validation, Docker builds, and Trivy.
- `advisory-extended`: non-blocking advanced backend tests and frontend E2E checks.

## Entity: Update Attempt Result

| Field | Type | Description |
|---|---|---|
| `pr_number` | integer | Candidate/PR reference |
| `status` | enum(`applied`, `skipped`) | Outcome of the attempt |
| `changed_files` | string[] | Files retained after the attempt |
| `failure_summary` | string? | One-line explanation for skipped updates |
| `migration_notes` | string? | Required when a major update fails due to needed code changes |
| `verification_evidence` | string[] | Commands/checks that were run |
| `recorded_at` | datetime | Audit timestamp |

**Validation rules**:

- `failure_summary` is required when `status = skipped`.
- `migration_notes` is required for skipped major updates that imply code changes.
- `changed_files` must be limited to manifests, lockfiles, workflow YAML, Dockerfiles, or generated dependency artifacts allowed by the spec.

## Entity: Batch Pull Request Report

| Field | Type | Description |
|---|---|---|
| `title` | string | Fixed title: `chore(deps): apply Dependabot batch update` |
| `base_branch` | string | Default branch targeted by the combined PR |
| `applied_updates` | integer[] | PR numbers successfully absorbed into the batch |
| `skipped_updates` | integer[] | PR numbers skipped with reasons |
| `description_checklist` | string[] | Applied update checklist lines |
| `description_skips` | string[] | Skipped update summaries |
| `cleanup_actions` | string[] | Closed PRs / deleted branches for successful Dependabot updates |
| `state` | enum(`not_created`, `drafted`, `opened`) | Batch PR lifecycle |

**Validation rules**:

- `state = opened` requires at least one applied update.
- `title` must match the spec exactly.
- `cleanup_actions` can reference only Dependabot PRs/branches tied to `applied_updates`.

## State Transitions

### Dependabot Pull Request / Update Candidate

```text
open -> prioritized -> attempting -> applied
                         \-> skipped
```

- `open -> prioritized`: discovery has classified ecosystem, semver tier, and overlap status.
- `prioritized -> attempting`: repository is reset to the correct baseline and the update is applied.
- `attempting -> applied`: required verification profiles passed and the dependency-only diff is retained.
- `attempting -> skipped`: any blocking validation fails, the diff is reverted, and the failure summary is recorded.

### Batch Pull Request Report

```text
not_created -> drafted -> opened
not_created -> not_created   (no successful updates)
```

- The report remains `not_created` when there are no successful updates.
- Cleanup of successful Dependabot PRs happens only after the batch report reaches `opened`.
