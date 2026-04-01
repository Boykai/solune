# Research: Awesome Copilot Agent Import

**Feature**: 003-copilot-agent-import
**Date**: 2026-04-01
**Status**: Complete

## Research Tasks

### RT-001: Awesome Copilot llms.txt Catalog Format and Parsing Strategy

**Context**: The spec requires browsing and searching agents from Awesome Copilot's cached `llms.txt` index (FR-003). Need to determine the format of this file and how to parse it reliably for agent metadata (name, description, source URL).

**Decision**: Fetch and cache the `llms.txt` file from `https://awesome-copilot.github.com/agents/llms.txt` using the existing `InMemoryCache` + `cached_fetch` pattern from `cache.py`. Parse it as a structured text index where each agent entry contains a name, description, and a URL pointing to the raw agent markdown file. The catalog reader (`catalog.py`) will expose a `list_catalog_agents()` function that returns parsed `CatalogAgent` objects and a `fetch_agent_raw_content(url)` function that fetches the full raw markdown only when a user triggers import.

**Rationale**: The `llms.txt` format is a lightweight text index designed for LLM consumption — it contains structured metadata per agent without the full content. This aligns perfectly with the spec's requirement to browse metadata only and fetch raw content on demand (FR-003). Using `cached_fetch` with a TTL of 1 hour provides fast repeated access while keeping the catalog reasonably fresh. The stale-fallback mode in `cached_fetch` handles temporary catalog unavailability (edge case from spec).

**Alternatives considered**:
- **Scrape the HTML agents page**: Fragile; depends on HTML structure which can change without notice. The `llms.txt` endpoint is the stable machine-readable interface.
- **Clone the awesome-copilot repository**: Over-engineered; requires git operations, large download, and ongoing sync. The text index is sufficient for browsing.
- **Pre-seed a local agent database**: Adds maintenance burden; the cached index approach is simpler and always reflects the latest catalog without manual updates.

---

### RT-002: Database Schema Strategy for Import Lifecycle

**Context**: The spec requires agents to exist in an `imported-but-not-installed` state (FR-017) with catalog-origin metadata and raw source snapshots alongside existing repo/PR fields. Need to decide between extending the existing `agent_configs` table or creating a new table.

**Decision**: Extend the existing `agent_configs` table with 5 new nullable columns via a new migration (`030_agent_import.sql`):
- `agent_type TEXT NOT NULL DEFAULT 'custom'` — distinguishes `'custom'` (existing behavior) from `'imported'` agents
- `catalog_source_url TEXT` — URL of the agent in the Awesome Copilot catalog
- `catalog_agent_id TEXT` — unique identifier from the catalog (slug or name-based)
- `raw_source_content TEXT` — full raw markdown content snapshot stored verbatim
- `imported_at TEXT` — ISO 8601 timestamp of when the agent was imported

The `lifecycle_status` column (existing, default `'pending_pr'`) is extended with new values: `'imported'` (after import, before install) and `'installed'` (after successful install). A `UNIQUE(catalog_agent_id, project_id)` constraint on non-null `catalog_agent_id` values prevents duplicate imports (FR-008).

**Rationale**: Extending the existing table keeps the agent model unified — `_list_local_agents()` in `service.py` already queries `agent_configs` and all existing logic (listing, pagination, cleanup) naturally includes imported agents. New columns are nullable, so existing rows are unaffected. The `agent_type` discriminator allows filtering custom vs imported agents in queries without changing existing code paths. A separate table would require joining on every agent list query and duplicating model logic.

**Alternatives considered**:
- **New `imported_agents` table**: Cleaner separation but requires JOIN queries for unified agent listing, duplicates model logic, and complicates the install flow (would need to move/copy rows between tables). Rejected per Simplicity principle.
- **JSON column for import metadata**: Stores all import fields in a single JSON text column. Less queryable (can't index `catalog_agent_id` for duplicate detection) and harder to validate. Rejected.
- **Separate lifecycle state machine table**: Over-engineered for two additional states. The existing string-based `lifecycle_status` column handles this naturally.

---

### RT-003: Import vs Install Service Split

**Context**: The spec requires splitting import from install (FR-006, FR-011). Import saves to database with no GitHub writes; install creates a parent issue and PR. Need to determine how to structure these as separate operations within the existing `AgentsService`.

**Decision**: Add two new methods to `AgentsService` in `service.py`:

1. **`import_agent(project_id, catalog_agent_id, source_url, raw_content, name, description)`** — validates the agent is not already imported (FR-008), stores a new row in `agent_configs` with `agent_type='imported'`, `lifecycle_status='imported'`, and the raw source content. Returns an `Agent` model with the imported status. Zero GitHub API calls.

2. **`install_agent(project_id, agent_id, owner, repo, access_token, github_user_id)`** — loads the imported agent from the database, generates the `.agent.md` file (using the stored `raw_source_content` verbatim) and the `.prompt.md` routing file (reusing the generation pattern from `agent_creator.py`), then calls `commit_files_workflow()` to create a branch, commit both files, open a PR, and create a parent issue. Updates the agent row with `lifecycle_status='installed'`, `github_issue_number`, `github_pr_number`, and `branch_name`.

**Rationale**: This split maps directly to the spec's two-phase workflow. Import is a pure database write — fast, safe, no side effects. Install reuses the battle-tested `commit_files_workflow()` pipeline that already handles branch creation, commit, PR, issue, and project board assignment. The `.prompt.md` generation is a simple f-string pattern already used in `agent_creator.py` (line 1056: `f"```prompt\n---\nagent: {slug}\n---\n```\n"`). No new GitHub integration code is needed.

**Alternatives considered**:
- **Single `add_agent` method with a flag**: Conflates two distinct operations; violates the spec's requirement for zero GitHub calls during import. Harder to test each step independently.
- **Separate `ImportService` class**: Unnecessary class proliferation for two methods that share the same database connection and service dependencies. Methods on the existing `AgentsService` are simpler.
- **Event-driven install (queue + worker)**: Over-engineered for a synchronous user action. The existing `commit_files_workflow` is already async and returns results directly.

---

### RT-004: Raw Agent Markdown Preservation During Install

**Context**: The spec's key risk is preserving upstream raw `.agent.md` content. Awesome Copilot agents can carry frontmatter Solune does not currently model (tools, mcp-servers, custom metadata). Install must write the imported raw agent file verbatim and only generate the `.prompt.md` wrapper (FR-012, FR-013).

**Decision**: During install, the raw content stored in `raw_source_content` is written as-is to `.github/agents/{slug}.agent.md`. No parsing, normalization, or frontmatter modification is applied to the raw content. The `.prompt.md` file is generated separately using only the agent's slug:

```python
# Raw agent file — verbatim from import snapshot
agent_file = {"path": f".github/agents/{slug}.agent.md", "content": raw_source_content}

# Routing file — generated by Solune
prompt_content = f"```prompt\n---\nagent: {slug}\n---\n```\n"
prompt_file = {"path": f".github/prompts/{slug}.prompt.md", "content": prompt_content}

# Commit both via existing workflow
await commit_files_workflow(files=[agent_file, prompt_file], ...)
```

**Rationale**: This is the simplest approach that guarantees no data loss. The raw content is a byte-for-byte copy of what was fetched from the Awesome Copilot catalog. Any frontmatter fields Solune doesn't understand (custom tools, MCP server configs, metadata extensions) are preserved because the content is never parsed or reconstructed. The `.prompt.md` routing file is the only Solune-generated artifact.

**Alternatives considered**:
- **Parse and re-serialize the frontmatter**: Risks losing unknown fields, reordering keys, or changing formatting. Even with a "preserve unknown fields" strategy, edge cases (comments, multi-line strings, anchors) make lossless round-tripping unreliable. Rejected — the spec explicitly warns against this.
- **Store parsed fields + raw content separately**: Unnecessary complexity. For browsing/display purposes, the name and description are already captured from the catalog index at import time. The full raw content is only needed at install time.
- **Diff the raw content against Solune's generated version**: Would require maintaining a normalization pipeline and handling divergence. Adds complexity without value — the spec says to use the raw content as-is.

---

### RT-005: Catalog Caching Strategy

**Context**: The browse modal must load within 3 seconds (SC-001) and search must filter within 1 second (SC-005). The catalog index needs to be cached to meet these performance targets and to handle temporary catalog unavailability.

**Decision**: Use the existing `InMemoryCache` instance from `cache.py` with a dedicated cache key `awesome_copilot_catalog`. Configuration:
- **TTL**: 3600 seconds (1 hour) for the parsed catalog index
- **Stale fallback**: Enabled — if the fetch fails, return the last successful result with a staleness indicator
- **Refresh**: On first browse modal open or when the user explicitly requests a refresh
- **Content**: Store the parsed list of `CatalogAgent` objects (name, description, source URL, tags/categories if available)

Search/filtering is performed client-side on the cached list. The catalog is small enough (estimated <500 agents) that in-memory filtering is instantaneous.

**Rationale**: The existing `cached_fetch` function in `cache.py` already supports TTL, stale fallback, and rate-limit fallback — no new caching infrastructure needed. A 1-hour TTL balances freshness with performance. Client-side search is appropriate because the full catalog fits in memory and avoids a server round-trip per keystroke. The stale fallback handles the edge case of temporary catalog unavailability (spec edge case).

**Alternatives considered**:
- **Database-backed cache (SQLite)**: Survives server restarts but adds query complexity. In-memory cache is simpler and the catalog can be re-fetched on startup. For a development tool like Solune, brief cold-start latency is acceptable.
- **Redis/external cache**: Over-engineered for a single cached resource. Solune uses SQLite, not Redis.
- **Server-side search with backend filtering**: Unnecessary round-trips for a small dataset. Client-side filtering is faster and simpler.
- **CDN/proxy cache**: Adds infrastructure complexity. The `InMemoryCache` is sufficient.

---

### RT-006: Frontend Browse Modal Architecture

**Context**: The spec requires a dedicated browse modal (FR-001) that is separate from the existing `AddAgentModal.tsx` custom-agent authoring flow (FR-016). Need to determine component architecture and state management.

**Decision**: Create a new `BrowseAgentsModal.tsx` component that:
- Renders a full-screen or large modal with a search input, agent list, and import buttons
- Uses a new `useCatalogAgents(projectId)` hook that calls `GET /api/v1/agents/{project_id}/catalog` with React Query
- Implements client-side filtering on the cached catalog list (search by name + description)
- Shows loading, error, and empty states
- Each agent row shows name, description, and an "Import" button (disabled if already imported)
- Import triggers `POST /api/v1/agents/{project_id}/import` via a `useImportAgent` mutation hook
- On successful import, the modal stays open (user may import multiple agents) and the agent's button changes to "Imported ✓"

The browse modal is opened from a "Browse Agents" button in `AgentsPanel.tsx`, alongside the existing "Add Agent" button. No changes to `AddAgentModal.tsx`.

**Rationale**: A separate modal keeps the browse/import workflow cleanly separated from custom-agent creation (FR-016). React Query provides built-in caching, loading states, and mutation invalidation. Client-side filtering on the returned catalog list avoids server round-trips per keystroke. The modal-stays-open pattern supports the common use case of importing multiple agents in one session.

**Alternatives considered**:
- **Inline catalog section on AgentsPage**: Clutters the main agents list with browseable items. A modal provides focused context for discovery.
- **Separate browse page/route**: Over-engineered; the browse action is transient and project-scoped. A modal is the right UX pattern.
- **Extend AddAgentModal with a browse tab**: Conflates two distinct workflows. The spec explicitly requires keeping custom authoring separate (FR-016).

---

### RT-007: Install Confirmation and Agent Status Display

**Context**: The spec requires a confirmation step before install (FR-010) and clear visual status indicators distinguishing imported, installed, and custom agents (FR-007, SC-007).

**Decision**:

**Install Confirmation**: Create `InstallConfirmDialog.tsx` that shows:
- Agent name and description
- Target repository (owner/repo from the current project)
- Summary: "This will create a GitHub issue and PR containing: `{slug}.agent.md` (raw agent definition) and `{slug}.prompt.md` (routing file)"
- "Install" and "Cancel" buttons
- Uses `useInstallAgent` mutation hook → `POST /api/v1/agents/{project_id}/{agent_id}/install`

**Status Badges on AgentCard**: Extend `AgentCard.tsx` to show:
- `imported` status → amber/yellow badge: "Imported" with a cloud-download icon
- `installed` status → green badge: "Installed" with links to the created issue and PR
- `active` / `pending_pr` / `pending_deletion` → existing badges (unchanged)
- `agent_type === 'imported'` → hide edit/system-prompt controls (read-only snapshot per FR-015)
- `agent_type === 'imported' && lifecycle_status === 'imported'` → show "Add to repo" button

**Rationale**: The confirmation dialog follows the spec exactly (FR-010) and prevents accidental GitHub resource creation. Status badges reuse the existing badge pattern in `AgentCard.tsx` (which already shows Active/Pending PR/Pending Deletion). The read-only constraint for imported agents is enforced at the UI level by hiding edit controls, and at the API level by rejecting update requests for imported agents.

**Alternatives considered**:
- **Inline confirmation (expand card)**: Less prominent; users might miss the confirmation details. A dialog is more explicit.
- **Separate "Imported Agents" section on the page**: Fragments the agent list. The spec says imported agents appear on the same Agents page with badge differentiation (FR-007).
- **Status as a separate field vs lifecycle_status extension**: A separate `import_status` field would create redundant state. Extending `lifecycle_status` keeps the state machine in one place.

---

### RT-008: Duplicate Import Prevention

**Context**: The spec requires preventing duplicate imports of the same agent within the same project (FR-008). Need to determine the uniqueness key and enforcement mechanism.

**Decision**: Use a `UNIQUE(catalog_agent_id, project_id)` partial constraint where `catalog_agent_id IS NOT NULL` in the migration. At the application level, `import_agent()` checks for an existing row with the same `catalog_agent_id` and `project_id` before inserting. If found, it returns an error response with a clear message ("Agent '{name}' is already imported in this project").

The `catalog_agent_id` is derived from the agent's slug in the Awesome Copilot catalog (e.g., `"security-reviewer"`, `"code-documenter"`). This is stable across catalog updates because slugs are URL-safe identifiers.

**Rationale**: Database-level constraint provides a safety net even if the application check is bypassed. The application-level check provides a user-friendly error message before the constraint is hit. Slug-based identification is stable and human-readable.

**Alternatives considered**:
- **Content hash for deduplication**: Would fail if the upstream content changes slightly (whitespace, formatting). Slug-based identity is more stable.
- **Allow re-import with version tracking**: Over-engineered for the first version. The spec says "does not create a duplicate" — a simple uniqueness check is sufficient.
- **Upsert pattern (replace on conflict)**: Dangerous — would overwrite existing import data silently. An explicit error is safer.

---

### RT-009: Migration Numbering and Compatibility

**Context**: The existing migration files go up to `029_activity_events.sql`. Need to choose the right migration number and ensure backward compatibility with existing data.

**Decision**: Use `030_agent_import.sql` as the migration file. The migration uses `ALTER TABLE ... ADD COLUMN` statements to add new nullable columns to `agent_configs`. This is safe because:
- `ALTER TABLE ADD COLUMN` with default values is supported in SQLite
- Existing rows get `agent_type='custom'` via the `DEFAULT 'custom'` clause
- All new columns except `agent_type` are nullable, so existing rows are unaffected
- No data migration is needed — existing agents are already `'custom'` type

The migration also creates an index on `(catalog_agent_id, project_id)` for efficient duplicate detection.

**Rationale**: SQLite's `ALTER TABLE ADD COLUMN` is the simplest migration path. It avoids the need to recreate the table (which would be required for adding constraints to existing columns). The `DEFAULT 'custom'` ensures backward compatibility without a data migration step.

**Alternatives considered**:
- **Recreate table with new schema**: Required for adding NOT NULL columns without defaults. Not needed here — `agent_type` has a default, and other columns are nullable.
- **Conditional migration (check if column exists)**: Not needed — SQLite migrations in Solune are idempotent via the migration runner's version tracking.
- **Store import data in a separate table to avoid ALTER TABLE**: Would require JOIN queries. The `ALTER TABLE ADD COLUMN` approach is simpler and keeps the model unified.
