# Research: Dependabot Batch Update Workflow

## Decision 1: Use GitHub open PR metadata as the discovery source of truth

- **Decision**: Build the discovery phase around the live GitHub open-PR inventory filtered to Dependabot-authored PRs, and treat a zero-result inventory as a successful no-op path rather than an error.
- **Rationale**: The feature specification requires evaluating *open* Dependabot PRs, so GitHub's current PR state is the authoritative source. The current live repo state on 2026-04-19 shows only the feature PRs `#2252` and `#2253` open; no Dependabot-authored PRs are presently open, which makes the no-op path a real requirement instead of a theoretical edge case.
- **Alternatives considered**:
  - Rely on the parent issue text alone — rejected because the issue can become stale relative to the live repository.
  - Infer pending updates from branches or commit messages — rejected because branch names are less reliable than PR metadata and cannot distinguish closed vs. open updates.

## Decision 2: Scope the workflow to the ecosystems declared in `.github/dependabot.yml`

- **Decision**: Treat `.github/dependabot.yml` as the canonical definition of supported update streams: backend `pip`, frontend `npm`, backend `docker`, frontend `docker`, and repo-root `github-actions`.
- **Rationale**: The Dependabot configuration is the repository-owned contract for which directories and ecosystems will generate PRs. Planning directly against that file prevents the workflow from overreaching into unmanaged files or missing a configured ecosystem.
- **Alternatives considered**:
  - Infer ecosystems solely from manifest files — rejected because that would miss repo-root GitHub Actions updates and could misclassify Docker image updates.
  - Limit the plan to backend/frontend package managers — rejected because the specification explicitly mentions GitHub Actions, Maven, etc. as ecosystem examples and requires grouping by ecosystem.

## Decision 3: Regenerate lockfiles only with native ecosystem tooling

- **Decision**: Use `uv` to regenerate `solune/backend/uv.lock` and `npm` to regenerate `solune/frontend/package-lock.json`; GitHub Actions and Docker updates have no lockfile step.
- **Rationale**: The spec explicitly forbids manual lockfile edits. The repository already standardizes backend installs on `uv sync --locked --extra dev` and frontend installs on `npm ci`, so the safest implementation is to regenerate with the same tooling the CI pipeline expects.
- **Alternatives considered**:
  - Manual lockfile edits — rejected because they violate FR-009 and are error-prone.
  - A custom lockfile wrapper script — rejected because the repository already has the necessary package-manager commands.

## Decision 4: Use existing blocking CI jobs as the acceptance baseline for each candidate update

- **Decision**: Define the per-update verification baseline from the blocking checks in `.github/workflows/ci.yml`: backend lint/security/type/test commands, frontend audit/lint/type/test/build commands, docs lint, diagram validation, contract validation, Docker builds, and Trivy image scans. Treat `backend-advanced-tests` and `frontend-e2e` as advisory because CI marks them `continue-on-error: true`.
- **Rationale**: The specification asks for the repository's existing build and test suite, and `.github/workflows/ci.yml` is the clearest expression of what the repository considers required vs. non-blocking. This keeps the implementation aligned with merge requirements without redefining “full verification” ad hoc.
- **Alternatives considered**:
  - Run only the directly affected ecosystem tests — rejected because cross-stack checks (contract validation, Docker, docs) are already required in CI and dependency changes can break them indirectly.
  - Gate every update on non-blocking suites as well — rejected because the repository has explicitly chosen not to make those suites blocking.

## Decision 5: Prioritize updates by semver risk, then by overlap surface

- **Decision**: Sort candidates patch → minor → major, then within each tier attempt isolated updates before overlapping ones. Consider candidates overlapping when they touch the same manifest/lockfile/workflow/Dockerfile, target the same package name, or constrain the same dependency graph.
- **Rationale**: This directly implements FR-004 and FR-005 while fitting the repository layout: backend updates converge on `pyproject.toml` + `uv.lock`, frontend updates converge on `package.json` + `package-lock.json`, GitHub Actions updates share `.github/workflows/*.yml`, and Docker updates share the backend/frontend Dockerfiles.
- **Alternatives considered**:
  - Apply updates in PR creation order — rejected because it ignores the required risk ordering.
  - Group only by ecosystem — rejected because two PRs in the same ecosystem can still be independent or overlapping depending on the files and versions involved.

## Decision 6: Preserve repo-specific install constraints during update attempts

- **Decision**: Keep frontend installs under `.npmrc`'s `legacy-peer-deps=true` behavior and preserve backend `uv` prerelease handling from `[tool.uv] prerelease = "allow"` while testing candidate updates.
- **Rationale**: These settings encode known repository compatibility constraints. Ignoring them during lockfile regeneration would create false negatives (installation failures unrelated to the update itself) and produce dependency states that diverge from CI.
- **Alternatives considered**:
  - Regenerate locks under package-manager defaults — rejected because that would not match the committed repo configuration.
  - Normalize the repo by removing the constraints during this feature — rejected because the spec forbids unrelated configuration changes.

## Decision 7: Skip empty-batch PR creation and preserve skipped Dependabot PRs

- **Decision**: Only create the combined PR when at least one update passes verification; otherwise emit a skipped/no-op report. Close and delete branches only for successfully applied Dependabot PRs, while leaving skipped ones open.
- **Rationale**: The specification explicitly requires retaining skipped updates for later manual follow-up and identifies the “no open PRs” and “all updates fail” cases as valid terminal outcomes.
- **Alternatives considered**:
  - Create an empty batch PR — rejected because it adds review noise and does not satisfy the value statement of the feature.
  - Close skipped PRs after logging failures — rejected because it conflicts with FR-018 and would hide work still needing manual resolution.
