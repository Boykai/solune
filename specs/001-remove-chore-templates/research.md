# Research: Remove Issue Templates, Use DB + Parent Issue Intake Flow

**Feature**: 001-remove-chore-templates | **Date**: 2026-04-13 | **Status**: Complete

## R1: execute_pipeline_launch() HTTP Dependency Coupling

**Decision**: Construct a `UserSession` object from chore-service context fields (`access_token`, `github_user_id`, `github_username`) and call `execute_pipeline_launch()` directly. No service-layer extraction needed.

**Rationale**: `execute_pipeline_launch()` accepts a `UserSession` parameter but does not depend on HTTP request context — it uses `session.access_token`, `session.github_user_id`, `session.github_username`, and `session.session_id`. All of these can be constructed from fields already available in the chore trigger context. The function is `async` and does not require FastAPI `Depends()` injection — the `Depends(get_session_dep)` is only on the route handler, not on `execute_pipeline_launch()` itself.

Current signature (pipelines.py L293):
```python
async def execute_pipeline_launch(
    *,
    project_id: str,
    issue_description: str,
    pipeline_id: str | None,
    session: UserSession,
    pipeline_project_id: str | None = None,
    target_repo: tuple[str, str] | None = None,
    auto_merge: bool = False,
    prerequisite_issues: list[int] | None = None,
) -> WorkflowResult:
```

The `session` parameter is a plain Pydantic model (`UserSession`) — not a FastAPI dependency. It can be constructed in the chores service:

```python
from src.models.user import UserSession
session = UserSession(
    github_user_id=github_user_id,
    github_username="",  # Not needed for pipeline launch
    access_token=access_token,
)
```

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Extract core logic into a service-layer function | Over-engineering — `execute_pipeline_launch()` is already a standalone async function, not coupled to HTTP |
| Pass individual fields instead of UserSession | Would require changing the shared function signature, impacting all callers |
| Create a lightweight session factory | Unnecessary abstraction — direct construction is simpler and clearer |

---

## R2: execute_pipeline_launch() Extension for extra_labels and title_override

**Decision**: Add two optional parameters to `execute_pipeline_launch()`: `extra_labels: list[str] | None = None` and `issue_title_override: str | None = None`. The title override takes precedence over both AI-derived and transcript-derived titles. Extra labels are appended to AI-classified labels.

**Rationale**: The function already has an internal `issue_title_override` variable used by transcript detection. The new parameter provides an external override that takes precedence. For labels, the function builds an `issue_labels` list from AI classification — extra labels are simply appended/merged after classification.

Implementation approach:
```python
# Title: external override > transcript override > AI-derived
issue_title = param_title_override or issue_title_override or _derive_issue_title(issue_description)

# Labels: AI-classified + pipeline label + extra labels
if extra_labels:
    for label in extra_labels:
        if label not in issue_labels:
            issue_labels.append(label)
```

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Create a separate function for chore launches | Duplicates ~100 lines of pipeline logic; violates DRY |
| Use a config object for all overrides | Over-abstracted for two optional params |
| Override labels via post-creation GitHub API call | Race condition with pipeline agents that read labels immediately |

---

## R3: Database Migration Strategy

**Decision**: Create migration `045_chore_description.sql` that renames `template_content` → `description` using SQLite's `ALTER TABLE RENAME COLUMN`, drops `template_path` using `ALTER TABLE DROP COLUMN`, and strips YAML front matter from existing rows via Python-driven data migration.

**Rationale**: SQLite 3.25+ supports `ALTER TABLE RENAME COLUMN` natively. SQLite 3.35+ supports `ALTER TABLE DROP COLUMN`. Python 3.12 bundles SQLite 3.40+, so both operations are supported natively.

Migration steps:
1. `ALTER TABLE chores RENAME COLUMN template_content TO description;`
2. `ALTER TABLE chores DROP COLUMN template_path;`
3. Strip YAML front matter from existing rows using Python-driven migration that reuses the `_strip_front_matter()` regex.

The YAML front matter stripping is best done in Python within the migration runner to reuse the existing `_strip_front_matter()` regex logic, since SQL string manipulation for multi-line patterns is fragile.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Soft-deprecate (keep old columns, add new) | Adds complexity; clean break is simpler per issue decision |
| Application-level migration on read | Leaves stale data; migration is the right time |
| Pure SQL front matter stripping | Fragile for multi-line YAML parsing; Python regex is robust |

---

## R4: is_sparse_input() Relocation

**Decision**: Move `is_sparse_input()` from `template_builder.py` (L56-93) to a new `src/services/chores/utils.py` module. Update the single import in the chat flow.

**Rationale**: `is_sparse_input()` is used by:
1. `template_builder.py` (being deleted) — internally, no action needed
2. `chat.py` — import updated to `from .utils import is_sparse_input`
3. `tests/unit/test_chores_template_builder.py` — test imports updated
4. Frontend `AddChoreModal.tsx` — has its own JS implementation, no backend import

The function is a pure utility (no dependencies, no state) and logically belongs in a chores utils module.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Move to top-level `src/utils.py` | Too broad; function is chore-specific |
| Keep in template_builder.py (don't delete file) | File name misleading after template removal |
| Inline into chat.py | DRY violation — tests also import it directly |

---

## R5: Preset File Rewriting Strategy

**Decision**: Strip YAML front matter from the 3 preset files in-place, leaving only the plain markdown body. Update `_CHORE_PRESET_DEFINITIONS` to remove `template_path` and rename `template_file` → `description_file`.

**Rationale**: The 3 preset files (security-review.md, performance-review.md, bug-basher.md) currently have YAML front matter:
```yaml
---
name: Security Review
about: Recurring chore — Security Review
title: '[CHORE] Security Review'
labels: chore
assignees: ''
---
```

This front matter was needed for GitHub Issue Templates. With DB-only storage, the files should contain just the plain description. The preset definition's `template_path` field is no longer needed.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Delete preset files, embed content in code | Harder to maintain long descriptions; files are more readable |
| Keep YAML front matter, strip at load time | Confusing; files should represent their actual content |
| Rename files to .txt | .md extension is correct for markdown content |

---

## R6: Template API Endpoint Disposition

**Decision**: Remove `GET /{project_id}/templates` entirely. Remove `PUT /.../inline-update` (SHA/PR logic). Remove `POST /.../create-with-merge`. Simplify `POST /{project_id}` (create) to stop calling `build_template()`/`derive_template_path()`.

**Rationale**: These endpoints exist solely for the template file workflow:
- `GET /templates` (api/chores.py L109-165): Lists `.github/ISSUE_TEMPLATE/chore-*.md` files from the repo — no longer relevant
- `PUT /inline-update` (api/chores.py L505-562): Updates chore + creates PR with SHA conflict detection — replaced by simple DB update
- `POST /create-with-merge` (api/chores.py L568-601): Creates chore + commits template + opens PR + auto-merges — replaced by simple DB create

The `PATCH /{project_id}/{chore_id}` endpoint already handles DB-only updates for schedule, status, etc. — it will be extended to also handle `description` updates.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Keep endpoints but make them no-op | Dead code; violates simplicity |
| Deprecate with warning headers | Over-engineered for an internal API |
| Merge into a single update endpoint | `PATCH` already serves this purpose |
