# Changelog

All notable changes to this project will be documented in this file.

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) conventions.

---

## [Unreleased]

## [0.1.0] — 2026-03-17

### Added

- **Pipeline state persistence**: Pipeline runs now persist to SQLite and survive application restarts
- **Pipeline run management**: Full API for creating, monitoring, canceling, and recovering pipeline runs
- **Stage groups**: Sequential and parallel agent execution support with group management API
- **Label-based state recovery**: GitHub labels enable faster pipeline state recovery with 60% fewer API calls
- **Onboarding tour**: Per-user progress tracking for guided product onboarding
- **Enhanced health checks**: Health endpoint now includes startup validation state and version info

### Security

- **Cookie hardening**: Session cookies use HttpOnly and SameSite=Strict flags
- **Startup validation**: Application refuses to start if required environment variables are missing
- **Project access control**: Enforced membership checks on all project operations
- **HTTP security headers**: CSP, X-Frame-Options, HSTS, and other security headers on all responses
- **Non-root containers**: Both backend and frontend run as non-privileged users
- **User-aware rate limiting**: Rate limits tied to GitHub user ID to prevent abuse

### Changed

- Removed artificial 500-entry limit on pipeline run history

---

## [Pre-0.1.0]

### Added

- **Monorepo structure**: Separated platform core (`solune/`) from generated apps (`apps/`)
- **Product rebrand**: Renamed from "Agent Projects" / "ghchat" to "Solune" throughout
- **App management system**: Create, manage, and preview generated applications with lifecycle controls
- **Apps page**: Visual interface for managing apps with live preview iframes
- **Admin guard system**: File operation protection with configurable access levels
- **Pipeline analytics dashboard**: Agent frequency, model distribution, and execution mode insights
- **CSRF protection**: Double-submit cookie pattern for all state-changing requests
- **Task registry**: Centralized background task tracking with graceful shutdown
- **Performance indexes**: Database indexes for better query performance
- **Automated diagram generation**: Mermaid architecture diagrams via CI and git hooks

### Changed

- **Sidebar improvements**: Added expand button when collapsed, improved navigation
- **Agent display**: Agent pills now show only model name on hover
- **Projects page**: Simplified project selection via sidebar
- **Chat persistence**: SQLite as single source of truth with write-through caching
- **Background tasks**: Modernized using asyncio.TaskGroup for proper lifecycle management
- **Documentation**: Updated all docs to match current codebase state

### Security

- **CSRF middleware**: Protection for all POST/PUT/PATCH/DELETE endpoints
- **Cache key scoping**: Isolated cache per project to prevent data leakage

---

## 2026-03-11

### Added

- Group-aware pipeline execution and tracking
- Automated Mermaid architecture diagram generation

### Changed

- Removed "Current Pipeline" section from Pipelines page
- Made Parent Issue Intake module collapsible
- Required `ADMIN_GITHUB_USER_ID` in production mode

### Fixed

- Chore issue counts now exclude chore-type issues
- Documentation drift fixes

---

## 2026-03-04

### Added

- GitHub label-based agent pipeline state tracking
- CodeGraph context filtering via `.cgcignore`

---

## 2026-02-25

### Added

- Code quality overhaul with 9-phase refactor
- MCP configuration generator on Tools page replacing GitHub toolset
- Parallel agent layout in pipelines
- Context7 and Code Graph Context as built-in MCP presets

### Fixed

- Pipeline recovery reliability improvements
- Throttled popover scroll handlers

---

## 2026-02-18

### Added

- Built-in preset configs for pipelines and chores
- Simplified model resolution

### Fixed

- UI improvements across Pipeline, Board, Chores, and Agents pages
- Documentation gaps and outdated references

---
