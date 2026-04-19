# Changelog

---

## [Unreleased]

### Added

- **Startup step runner** — Extracted the 15 startup responsibilities from `main.py`'s monolithic `lifespan()` into a declarative `src/startup/` package with named, individually-testable steps, a `Step` protocol, `StartupContext`, and `run_startup()`/`run_shutdown()` orchestrators. `lifespan()` is now a short delegator.
- Shared Radix dialog and alert-dialog primitives for frontend modal workflows, including reusable character-count and first-error-focus helpers.
- Test skip marker inventory documenting all 16 conditional infrastructure guards across backend and frontend suites.
- Unit tests for `useUndoRedo` hook covering push, undo, redo, redo-stack clearing, and empty-stack edge cases.
- MCP catalog browsing and import on the Tools page (`GET /tools/{project_id}/catalog`, `POST /tools/{project_id}/catalog/import`).
- Pipeline assignment endpoints (`GET/PUT /pipelines/{project_id}/assignment`) and issue-launch endpoint (`POST /pipelines/{project_id}/launch`).
- Agent catalog browsing (`GET /agents/{project_id}/catalog`) and manual MCP sync (`POST /agents/{project_id}/sync-mcps`).
- CompactPageHeader component replacing the decorative CelestialCatalogHero across Agents, Chores, and Tools pages.
- AI-powered label classification during chore and pipeline issue creation.

### Fixed

- Local Docker Compose backend startup now honors `ADMIN_GITHUB_USER_ID`, so the configured admin identity is available inside the container.
- Frontend Docker images now remove the base nginx `user` directive before running as the non-root `nginx-app` user, eliminating noisy startup warnings.
- Backend mutation testing workspace now copies `templates/` directory so app-template tests pass under mutmut.
- `renderWithProviders()` in test-utils.tsx now nests providers correctly instead of rendering children twice.
- Browser Agents catalog now lets unexpected internal fetch failures surface as generic server errors instead of reporting them as upstream outages.
- Browser Agents catalog now derives stable imported IDs from source filenames and follows redirects when fetching catalog indexes and raw agent definitions.
- Browser Agents install confirmations now clear stale error banners when the dialog is closed and reopened.
- Chat now prefers the existing SSE stream for long-running assistant replies, keeps partial progress visible, and surfaces recoverable failures with inline retry affordances.
- Projects, list surfaces, and app chrome now show stronger loading, sync, and retry feedback without replacing the underlying layout.
- Onboarding replay and 404 recovery now offer clearer re-entry paths, and tour steps fall back gracefully when a target cannot be resolved.

### Changed

- Backend mutation CI now runs all 5 shards defined in `run_mutmut_shard.py` (added missing `api-and-middleware` shard).
- Frontend mutation testing is split into 4 CI shards (`hooks-board`, `hooks-data`, `hooks-general`, `lib`) for faster execution.
- Added focused mutation commands (`test:mutate:hooks-board`, `test:mutate:hooks-data`, `test:mutate:hooks-general`, `test:mutate:lib`) to frontend package.json.
- Modal workflows across apps, tools, agents, and pipeline confirmations now share more consistent overlay, focus, and submission behavior.
- Primary route transitions and not-found recovery now provide smoother visual continuity and better navigation suggestions.

## [0.1.0] — 2026-03-17

### Added

- **Pipeline runs persist across restarts** — runs survive server reboots with full recovery
- **Sequential & parallel stage groups** — arrange agents in parallel or sequential execution groups
- **Onboarding tour** — guided walkthrough for new users with per-user progress tracking
- **Pipeline analytics dashboard** — agent frequency, model distribution, and execution mode insights
- **App management** — create, preview, start/stop generated applications from a dedicated Apps page
- **MCP configuration generator** — replaced GitHub toolset on Tools page; includes Context7 and Code Graph presets
- **Parallel agent layout** in pipeline builder
- **Built-in pipeline & chore presets** for quick setup

### Changed

- Collapsible Parent Issue Intake module (collapsed by default)
- Removed "Current Pipeline" section from Pipelines page
- Sidebar: added expand button when collapsed
- Agent pills show only model name on hover
- Simplified project selection via sidebar

### Fixed

- Pipeline recovery reliability improvements
- Chore issue counts now exclude chore-type issues
- UI polish across Pipeline, Board, Chores, and Agents pages

---
