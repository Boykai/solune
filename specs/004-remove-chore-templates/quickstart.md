# Quickstart: Remove Issue Templates, Use DB + Parent Issue Intake Flow

**Feature**: 004-remove-chore-templates | **Date**: 2026-04-13

## Prerequisites

- Python 3.12+ with `uv` package manager
- Node.js 18+ with `npm`
- Backend dev dependencies: `cd solune/backend && uv sync --locked --extra dev`
- Frontend dependencies: `cd solune/frontend && npm install`

## Execution Order

### Phase 1: Backend Model & DB (Foundation)

```bash
# 1. Update Chore model
# File: solune/backend/src/models/chores.py
# - Rename template_content → description
# - Remove template_path field
# - Update ChoreCreate: template_content → description

# 2. Create DB migration
# File: solune/backend/src/migrations/045_chore_description.sql
# - ALTER TABLE chores RENAME COLUMN template_content TO description
# - ALTER TABLE chores DROP COLUMN template_path
# - Strip YAML front matter from existing rows (Python migration helper)

# 3. Verify model changes compile
cd solune/backend && uv run pyright src/models/chores.py
```

### Phase 2: Backend Services (Depends on Phase 1)

```bash
# 4. Extend execute_pipeline_launch()
# File: solune/backend/src/api/pipelines.py (L293)
# - Add extra_labels: list[str] | None = None parameter
# - Add issue_title_override: str | None = None parameter
# - Apply title override before transcript/AI derivation
# - Append extra_labels to classified labels
# NO DEPENDENCY on Phase 1 — can be done in parallel

# 5. Rewrite trigger_chore()
# File: solune/backend/src/services/chores/service.py (L462)
# - Replace ~200 lines with execute_pipeline_launch() call
# - Keep: 1-open-instance check, CAS update
# - Pass: chore.description, chore.name, ["chore"]

# 6. Move is_sparse_input() to utils
# File: solune/backend/src/services/chores/utils.py (NEW)
# - Move is_sparse_input() from template_builder.py
# - Update imports in chat.py and tests

# 7. Remove template-related methods
# File: solune/backend/src/services/chores/service.py
# - Gut inline_update_chore() → simple DB update
# - Simplify create_chore_with_auto_merge() → create_chore()
# - Remove _strip_front_matter() (kept in migration only)

# 8. Delete/gut template_builder.py
# File: solune/backend/src/services/chores/template_builder.py
# - Remove build_template(), derive_template_path(), update_template_in_repo()
# - Remove commit_template_to_repo(), merge_chore_pr(), _slugify()
# - File can be deleted entirely (is_sparse_input moved to utils.py)

# 9. Remove/simplify template API endpoints
# File: solune/backend/src/api/chores.py
# - Remove GET /{project_id}/templates
# - Remove PUT /.../inline-update
# - Remove POST /.../create-with-merge
# - Simplify POST /{project_id} create handler

# Verify backend changes
cd solune/backend
uv run ruff check src/ tests/
uv run pyright src/
uv run pytest tests/unit/ -q
```

### Phase 3: Frontend (Depends on Phase 1 + Phase 2 API changes)

```bash
# 10. Update types
# File: solune/frontend/src/types/index.ts
# - Remove ChoreTemplate type
# - Update Chore: description instead of template_content, remove template_path
# - Update ChoreCreate: description instead of template_content
# - Simplify ChoreInlineUpdate: remove expected_sha
# - Simplify ChoreInlineUpdateResponse: remove PR fields
# - Simplify ChoreCreateResponse: remove PR fields
# - Simplify ChoreEditState: remove fileSha

# 11. Update API client
# File: solune/frontend/src/services/api.ts
# - Remove choresApi.listTemplates()
# - Remove choresApi.inlineUpdate()
# - Remove choresApi.createWithAutoMerge()
# - Update create/update payloads: description instead of template_content

# 12. Update hooks
# File: solune/frontend/src/hooks/useChores.ts
# - Remove useChoreTemplates()
# - Remove useCreateChoreWithAutoMerge() or simplify to useCreateChore()
# - Remove useInlineUpdateChore() or simplify
# - Update payloads

# 13. Simplify AddChoreModal
# File: solune/frontend/src/components/chores/AddChoreModal.tsx
# - Remove template picker buttons (repoTemplates section)
# - Remove useChoreTemplates import
# - Remove initialTemplate prop
# - Rename "Template Content" → "Description"
# - Update payload: description instead of template_content

# 14. Update ChoreCard
# File: solune/frontend/src/components/chores/ChoreCard.tsx
# - Remove "Save & Create PR" button text
# - Use "Save" for all save operations
# - Use description field

# 15. Update ChoreInlineEditor
# File: solune/frontend/src/components/chores/ChoreInlineEditor.tsx
# - Remove SHA conflict detection references

# 16. Update ChoresPanel
# File: solune/frontend/src/components/chores/ChoresPanel.tsx
# - Remove template membership check references
# - Remove uncreatedTemplates filtering

# Verify frontend changes
cd solune/frontend
npm run lint
npm run type-check
npm run test
npm run build
```

### Phase 4: Cleanup (Depends on Phase 2)

```bash
# 17. Update preset files
# Files: solune/backend/src/services/chores/presets/*.md
# - Strip YAML front matter from all 3 files
# - Update _CHORE_PRESET_DEFINITIONS in service.py
# - Update seed_presets() to use description field

# Verify
cd solune/backend && uv run pytest tests/unit/ -q
```

### Phase 5: Testing & Verification

```bash
# Full backend validation
cd solune/backend
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run pyright src/
uv run pytest tests/unit/ -q

# Full frontend validation
cd solune/frontend
npm run lint
npm run type-check
npm run test
npm run build

# Zero-reference check
grep -rn "template_content\|template_path\|ISSUE_TEMPLATE/chore" \
  solune/backend/src/ solune/frontend/src/ \
  --include="*.py" --include="*.ts" --include="*.tsx" \
  | grep -v "migration" | grep -v "test_"
# Expected: zero hits (except migration files)
```

## Verification Checklist

- [ ] Create chore with plain description → saved to DB, no template file, no PR
- [ ] Trigger chore → `execute_pipeline_launch()` flow (same as Parent Issue Intake)
- [ ] Issue gets `["chore"]` label + AI-classified labels
- [ ] Issue title = chore name (not derived from description body)
- [ ] Pipeline dispatches correctly (sub-issues created, agents assigned)
- [ ] Inline edit saves to DB only (no PR)
- [ ] No `.github/ISSUE_TEMPLATE/chore-*.md` references remain
- [ ] `uv run pytest` passes
- [ ] `npm test` passes
- [ ] `npm run build` passes
