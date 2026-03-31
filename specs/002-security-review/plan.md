# Implementation Plan: Security, Privacy & Vulnerability Audit

**Branch**: `002-security-review` | **Date**: 2026-03-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-security-review/spec.md`

## Summary

Comprehensive security, privacy, and vulnerability audit addressing 21 OWASP Top 10 findings across authentication (A01/A02), configuration (A05), cryptography (A02), authorization (A01), transport security (A05), rate limiting (A04), data protection (A02), error handling (A09), and supply-chain controls. The audit spans 4 phases organized by severity: 3 Critical (fix immediately), 8 High (this week), 9 Medium (next sprint), and 2 Low (backlog). Changes touch the Python/FastAPI backend (auth flow, config validation, encryption, authorization, webhooks, database permissions, rate limiting, error sanitization), the React/nginx frontend (cookie-based auth, chat storage, avatar validation, security headers), Docker infrastructure (non-root containers, volume mounts, port bindings), and CI/CD workflows (minimum permissions). Research confirms all 21 findings are already remediated in the current codebase — the implementation plan documents the patterns applied and validates compliance against each finding.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript 5 / React 19 (frontend)
**Primary Dependencies**: FastAPI ≥0.135, cryptography (Fernet), slowapi, aiosqlite, Pydantic ≥2.12, nginx 1.29-alpine, Vite
**Storage**: SQLite via aiosqlite with WAL mode, encrypted-at-rest OAuth tokens via Fernet
**Testing**: pytest + pytest-asyncio (backend), Vitest (frontend)
**Target Platform**: Linux server (Docker containers — Python 3.14-slim backend, nginx-alpine frontend)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: Rate limits must not add measurable latency to non-limited requests; startup validation completes in < 1 second
**Constraints**: All containers run non-root; all secrets mandatory in production; cookie-only auth (no URL tokens); constant-time comparisons for all secrets
**Scale/Scope**: 21 findings across 30+ files; 4 implementation phases; backend API (22 endpoint modules), frontend (React SPA + nginx), Docker Compose (3 services), 1 GitHub Actions workflow

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | `spec.md` exists with 19 prioritized user stories (P1–P4), Given-When-Then acceptance scenarios, edge cases, and clear scope boundaries (out of scope: GitHub API security, MCP internals, network infrastructure) |
| II. Template-Driven | ✅ PASS | All artifacts follow canonical templates from `.specify/templates/` |
| III. Agent-Orchestrated | ✅ PASS | Single-responsibility: this plan phase produces design artifacts; implementation deferred to `/speckit.tasks` + `/speckit.implement` |
| IV. Test Optionality | ✅ PASS | Tests not mandated by spec but recommended for config validation, authorization checks, and rate limiting. Unit tests exist in the backend test suite |
| V. Simplicity and DRY | ✅ PASS | Security hardening follows existing patterns (shared `verify_project_access` dependency, middleware stack, config validators). No new abstractions introduced — each fix is a targeted change to an existing module |

**Gate Result**: ALL PASS — proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/002-security-review/
├── plan.md              # This file
├── research.md          # Phase 0: Research findings for all 21 security items
├── data-model.md        # Phase 1: Security-relevant entity model
├── quickstart.md        # Phase 1: Developer verification guide
├── contracts/           # Phase 1: Security contracts
│   └── security-controls.yaml  # Security control contracts
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── api/
│   │   ├── auth.py              # MODIFIED: Cookie-only session delivery, POST-only dev login
│   │   ├── tasks.py             # MODIFIED: verify_project_access on all endpoints
│   │   ├── projects.py          # MODIFIED: verify_project_access on all endpoints
│   │   ├── settings.py          # MODIFIED: Project-scoped authorization
│   │   ├── workflow.py          # MODIFIED: verify_project_access + rate limiting
│   │   ├── chat.py              # MODIFIED: Rate limiting on chat endpoints
│   │   ├── agents.py            # MODIFIED: Rate limiting on agent endpoints
│   │   ├── webhooks.py          # MODIFIED: Unconditional signature verification
│   │   ├── signal.py            # MODIFIED: Constant-time secret comparison
│   │   └── main.py              # MODIFIED: ENABLE_DOCS toggle, middleware stack
│   ├── config.py                # MODIFIED: Production secret validation, CORS validation
│   ├── dependencies.py          # MODIFIED: Centralized verify_project_access
│   ├── middleware/
│   │   ├── rate_limit.py        # MODIFIED: Per-user + per-IP rate limiting via slowapi
│   │   ├── csp.py               # MODIFIED: CSP + security headers
│   │   └── csrf.py              # EXISTING: CSRF double-submit cookie
│   └── services/
│       ├── encryption.py        # MODIFIED: Mandatory encryption, migration path
│       ├── database.py          # MODIFIED: 0700/0600 permissions
│       ├── github_auth.py       # MODIFIED: Minimum OAuth scopes
│       └── github_projects/
│           └── graphql.py       # MODIFIED: Sanitized error messages
└── tests/
    └── unit/                    # Existing tests cover config validation, auth flow

solune/frontend/
├── src/
│   ├── hooks/
│   │   ├── useAuth.ts           # MODIFIED: Cookie-based auth (no URL token reading)
│   │   └── useChatHistory.ts    # MODIFIED: In-memory only, legacy cleanup on logout
│   ├── components/
│   │   └── IssueCard.tsx        # MODIFIED: Avatar URL domain validation
│   └── nginx.conf               # MODIFIED: Security headers, server_tokens off
└── Dockerfile                   # MODIFIED: Non-root nginx-app user

docker-compose.yml               # MODIFIED: 127.0.0.1 bindings, /var/lib/solune/data volume

.github/workflows/
└── branch-issue-link.yml        # MODIFIED: Minimum permissions with justification
```

**Structure Decision**: Web application structure. Changes span backend (Python/FastAPI), frontend (React/nginx), Docker infrastructure, and CI/CD. No new modules — all fixes are surgical modifications to existing files. The security hardening follows the existing middleware + dependency injection architecture.

## Constitution Re-Check (Post-Design)

*Re-evaluation after Phase 1 design artifacts are complete.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | All 21 findings traced to spec.md requirements (FR-001 through FR-030); design artifacts reference specific acceptance scenarios |
| II. Template-Driven | ✅ PASS | All generated artifacts follow canonical templates |
| III. Agent-Orchestrated | ✅ PASS | Plan phase complete; handoff to `/speckit.tasks` for task decomposition |
| IV. Test Optionality | ✅ PASS | Existing unit tests cover config validation and auth flow; additional tests recommended for authorization dependency and rate limiting |
| V. Simplicity and DRY | ✅ PASS | Each fix is a targeted change to an existing module. Centralized `verify_project_access` dependency eliminates per-endpoint ownership checks. No new frameworks, abstractions, or services introduced |

**Gate Result**: ALL PASS — ready for Phase 2 (`/speckit.tasks`).

## Complexity Tracking

> No constitution violations — this section is intentionally empty.
