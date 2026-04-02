# Changelog

---

## [Unreleased]

### Fixed

- Browser Agents catalog now lets unexpected internal fetch failures surface as generic server errors instead of reporting them as upstream outages.
- Browser Agents catalog now derives stable imported IDs from source filenames and follows redirects when fetching catalog indexes and raw agent definitions.
- Browser Agents install confirmations now clear stale error banners when the dialog is closed and reopened.

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
