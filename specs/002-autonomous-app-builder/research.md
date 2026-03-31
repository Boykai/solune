# Research: Autonomous App Builder

**Feature**: 002-autonomous-app-builder | **Date**: 2026-03-31
**Input**: [plan.md](plan.md) Technical Context

## R1: Template Rendering Engine — `{{var}}` Substitution vs. External Engine

**Decision**: Custom `{{var}}` substitution with `str.replace()` — no external template engine.

**Rationale**: The spec explicitly mandates simple `{{variable}}` substitution (Assumption 2). The four initial templates have a small, predictable variable set (`app_name`, `display_name`, `description`, `port`, `repo_owner`). A custom renderer is ~50 lines of code, adds zero dependencies, and gives full control over path-traversal validation (FR-004, SC-010). External engines (Jinja2, Mako) are heavyweight, introduce attack surface (template injection), and would violate Constitution Principle V (Simplicity).

**Alternatives Considered**:
- **Jinja2**: Powerful but overkill. Introduces server-side template injection risk. Would require sandboxing configuration.
- **string.Template (stdlib)**: Safe substitution mode exists but uses `$var` syntax instead of `{{var}}`, inconsistent with spec language.
- **Mustache/Chevron**: Lightweight but adds a dependency for minimal gain.

---

## R2: Template File Storage — Filesystem vs. Database

**Decision**: Filesystem under `backend/templates/app-templates/`. Each template is a directory with `template.json` (metadata) and a `files/` subdirectory containing `.tmpl` files.

**Rationale**: Templates are static, versioned assets that ship with the application. Filesystem storage keeps them in source control, makes them reviewable in PRs, and avoids database migration complexity. The existing `backend/templates/` directory already holds agent definitions and project scaffolding files — app templates are a natural extension. The `registry.py` module discovers templates by scanning the directory at startup.

**Alternatives Considered**:
- **SQLite storage**: Adds migration complexity, makes templates harder to review, and loses Git history.
- **External package/CDN**: Over-engineered for 4 static templates; introduces availability dependency.

---

## R3: Path-Traversal Validation Strategy

**Decision**: Validate rendered file paths using `os.path.realpath()` resolution. After joining the target app directory with each rendered path, verify the resolved path starts with the target directory prefix. Reject any path containing `..`, absolute paths, or symlinks that escape the boundary.

**Rationale**: FR-004 and SC-010 mandate 100% path-traversal blocking. The `realpath()` approach handles all known traversal techniques (relative `../`, symlink following, null bytes in older Python). This is a well-established pattern used in secure file-serving code. The renderer validates paths *before* writing any files.

**Alternatives Considered**:
- **Regex-only filtering**: Fragile — misses encoded sequences and platform-specific edge cases.
- **chroot/sandbox**: Overkill for a write-to-directory operation; adds OS-level complexity.

---

## R4: Pipeline Auto-Configuration — Template × Difficulty Mapping

**Decision**: New `pipeline_config.py` module with a deterministic mapping: template category + difficulty → pipeline preset ID. When `iac_target != "none"`, inject the architect agent into the "In progress" stage as a "deploy-prep" execution group after `speckit.implement`.

**Rationale**: The spec mandates deterministic preset selection (FR-009, Assumption 6). The existing `DIFFICULTY_PRESET_MAP` in `agent_tools.py` maps difficulty strings to preset IDs. The new module extends this by incorporating template metadata. Architect agent insertion modifies the preset's stage groups at pipeline creation time, not at the preset definition level — this avoids polluting presets for non-IaC templates.

**Alternatives Considered**:
- **Modify preset definitions globally**: Would add architect agent to all hard/expert pipelines even when IaC is not requested.
- **Runtime agent injection during pipeline execution**: Too late — pipeline stages are immutable once created. Must be configured at pipeline creation.

---

## R5: Build Progress Tracking Architecture

**Decision**: New `BuildProgress` Pydantic model stored in-memory (not persisted to SQLite). Progress events emitted via existing `ConnectionManager.broadcast_to_project()`. Chat integration via background task that monitors progress and injects status messages. Signal notifications via existing `signal_delivery.py` with new milestone formatting.

**Rationale**: Build progress is ephemeral — it only matters during an active build. In-memory storage avoids database overhead and migration. The existing WebSocket broadcast infrastructure (used for task/board updates) is the natural channel. Chat injection follows the existing pattern where system messages are inserted into chat sessions. Signal delivery already supports fire-and-forget async delivery with retry.

**Alternatives Considered**:
- **Persistent progress in SQLite**: Adds migration, cleanup logic, and storage for data that's only useful for ~5 minutes.
- **Server-Sent Events (SSE)**: Already available via `sse-starlette` but would require a new endpoint and client subscription. WebSocket is already connected for project updates.
- **Polling-only**: Violates SC-005 (2-second visibility requirement).

---

## R6: GitHub Import — URL Validation Approach

**Decision**: Multi-layer validation: (1) regex for URL format (`github.com/{owner}/{repo}`), (2) GitHub API call via `githubkit` to verify repository existence and accessibility, (3) optional permission check for private repos using the user's GitHub token.

**Rationale**: FR-006 requires URL validation, and edge cases (archived repos, empty repos, private repos without access) demand API-level verification. The existing `githubkit` client is already configured in the codebase for GitHub API calls. Regex alone would miss permission issues and non-existent repos.

**Alternatives Considered**:
- **Regex-only validation**: Cannot detect non-existent or inaccessible repos.
- **Git clone probe**: Heavy-weight, slow, and requires Git CLI on the server.

---

## R7: Clarification Question Generation

**Decision**: Implement as an agent tool (`generate_app_questions()`) that returns 2–3 questions based on the user's description and available template metadata. Questions are generated by the AI agent using the app description + template catalog as context, not by a rule-based engine.

**Rationale**: The spec limits clarification to 2–3 questions (Assumption 5) and expects the agent to use template metadata to infer defaults. Since the chat agent already uses Microsoft Agent Framework with tool calling, the simplest approach is a tool that provides template context and lets the LLM generate relevant questions. This avoids building a separate NLP/rule engine.

**Alternatives Considered**:
- **Rule-based question tree**: Rigid, hard to maintain, cannot adapt to novel app descriptions.
- **Separate LLM call**: Unnecessary when the chat agent already has LLM reasoning capability.

---

## R8: Frontend Build Progress — Component Strategy

**Decision**: Two new components: (1) `BuildProgress.tsx` — standalone stepper/timeline panel for the app detail view, (2) `BuildProgressCard.tsx` — compact card for inline display in chat messages. Both subscribe to a shared `useBuildProgress` hook that connects to WebSocket events.

**Rationale**: The spec requires progress in both the frontend panel (FR-019) and chat messages (FR-027). These are different UI contexts with different layouts, so separate components are appropriate. A shared hook avoids duplicating WebSocket subscription logic. The existing `useRealTimeSync` hook provides a pattern for WebSocket integration but is project-scoped; build progress needs app-scoped events.

**Alternatives Considered**:
- **Single component with conditional rendering**: Would become complex trying to serve both full-panel and inline-card layouts.
- **Polling-based updates**: Violates the 2-second update requirement and wastes bandwidth.

---

## R9: Architect Agent Integration — Agent Definition and Pipeline Registration

**Decision**: Verify existing `architect.agent.md` (already exists with IaC-focused prompt for Bicep, Azure scaffolds, architecture diagrams). Register as a "deploy-prep" execution group in the "In progress" stage, inserted after the `speckit.implement` group. The architect receives tech_stack and iac_target via the sub-issue body (same mechanism used by other pipeline agents).

**Rationale**: The `architect.agent.md` already exists in `backend/templates/.github/agents/` with the right capabilities (Bicep/Terraform, Azure MCP server). Pipeline agent integration follows the established sub-issue pattern — each agent in a pipeline stage receives a sub-issue with relevant context in the body. No new integration mechanism is needed.

**Alternatives Considered**:
- **Direct API call to architect**: Breaks the pipeline abstraction. All agents should work through the sub-issue mechanism.
- **New agent definition format**: Unnecessary — existing `.agent.md` format with YAML frontmatter is sufficient.

---

## R10: Database Schema Changes

**Decision**: Single migration `027_app_template_fields.sql` adding `template_id TEXT` column to the `apps` table (nullable, for backward compatibility with existing apps). No new tables — build progress is in-memory, templates are filesystem-based.

**Rationale**: Minimal schema change. The `template_id` column links an app to its originating template for display and potential re-scaffolding. Existing apps have `NULL` template_id. The `repo_type` enum already includes `EXTERNAL_REPO` for imported repos — no schema change needed for import.

**Alternatives Considered**:
- **Separate `app_templates` table**: Over-engineered — template metadata lives in `template.json` files, not the database.
- **JSON column for template metadata**: Loses queryability and adds complexity.
