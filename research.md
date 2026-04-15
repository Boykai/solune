# Research: MCP Catalog on Tools Page

**Feature**: MCP Catalog on Tools Page | **Date**: 2026-04-15 | **Status**: Complete

## R1: Upstream Catalog Source and Fetch Strategy

**Decision**: Use the Glama MCP API as the sole live catalog source and proxy it through the backend with a one-hour TTL cache plus stale-fallback behavior.

**Rationale**: The feature only needs one source that already exposes searchable server metadata, categories, quality scores, and install instructions. Keeping the fetch on the backend centralizes caching, upstream error translation, and security controls, while stale fallback preserves browse functionality during transient upstream failures.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Direct browser fetch to Glama | Pushes upstream volatility and security exposure into the client; no centralized cache or SSRF boundary |
| Combine Glama with `microsoft/mcp` scraping | Adds source-reconciliation complexity without improving the core browse/import flow |
| No stale fallback | Makes the Tools page brittle whenever the upstream catalog times out or errors |

---

## R2: Upstream Normalization and URL Safety

**Decision**: Normalize Glama payloads in one backend adapter and expose only sanitized HTTPS repository URLs while allowlisting the actual upstream fetch host.

**Rationale**: The upstream payload can vary between list and wrapped-object responses and may use alternate field names such as `title`, `summary`, `repository`, or `github_url`. Centralized normalization keeps the frontend contract stable. Independent sanitization of surfaced repo links prevents unsafe URLs from reaching the browser, while allowlisting Glama as the only upstream host mitigates SSRF risk.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Trust all upstream fields as-is | Couples the UI to payload drift and could surface unsafe URLs |
| Allow arbitrary upstream hosts | Weakens SSRF protections and exceeds feature scope |
| Normalize data in the frontend | Duplicates parsing logic and leaks backend integration concerns into UI code |

---

## R3: Installed-State Detection

**Decision**: Derive `already_installed` by comparing normalized catalog server names against the current project's existing tool names.

**Rationale**: Installed-state is purely a projection of existing project data. Deriving it during browse avoids schema changes, catalog-specific persistence, or background synchronization. This also keeps the catalog section aligned with the existing MCP tool archive as the source of truth.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Persist catalog installation metadata in the database | Adds schema and migration work for data that can already be derived |
| Match only on repository URL | Misses servers that lack `repo_url` and is less aligned with how tools are labeled in the UI |
| Match on raw install config hash | More fragile and harder to reason about than the user-visible tool name |

---

## R4: Import Mapping Strategy

**Decision**: Convert supported catalog transports into the existing `mcpServers` JSON snippet used by `McpToolConfig`, with transport-specific validation.

**Rationale**: Reusing the existing `McpToolConfig` contract preserves current CRUD, archive, and sync-to-repo behavior. `http` and `sse` entries map to URL-based configs, while `stdio` and `local` map to command-based configs. Rejecting unsupported transports explicitly is safer than silently importing invalid or partial configurations.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Store raw upstream install payloads unchanged | Breaks the existing sync flow and forces downstream consumers to understand Glama-specific formats |
| Create a separate catalog-import table | Duplicates the existing MCP tool model and complicates the sync path |
| Silently skip unsupported transports | Produces confusing UX and hides import failures from users |

---

## R5: Frontend Browse and Import UX

**Decision**: Add an inline `McpCatalogBrowse` section to the Tools page between the presets gallery and the tool archive, with deferred search, category chips, server cards, and immediate installed-state feedback after import.

**Rationale**: The Tools page is already where users discover presets, upload MCP configs, and sync tools to the repo. Keeping the catalog inline preserves context and mirrors existing discovery patterns. Deferred search avoids unnecessary request churn during typing, while query invalidation after import keeps browse results and the tool archive synchronized.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Separate catalog page | Breaks the existing Tools workflow and adds unnecessary navigation |
| Import from a modal only | Hides browse/filter context and makes the feature feel detached from the archive |
| Manual refresh after import | Delays installed-badge feedback and weakens the perceived responsiveness of the feature |

---

## R6: Verification Strategy

**Decision**: Validate the feature with targeted backend and frontend suites plus one manual browse/import/sync flow.

**Rationale**: The implementation already has focused test coverage for the backend service/API, frontend hooks, API client validation, and the browse component. Using those existing suites gives fast confidence without requiring new infrastructure. Manual verification is still necessary to confirm the end-to-end Tools page flow and repo sync behavior.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Manual verification only | Too easy to miss contract and regression issues already covered by automated tests |
| Full repository test suite only | Slower and less targeted than the existing feature-specific tests |
| New end-to-end-only coverage | Higher maintenance cost than warranted for the current planning scope |
