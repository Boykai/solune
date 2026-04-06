# Implementation Plan: Increase Test Coverage & Fix Discovered Bugs

**Branch**: `001-test-coverage-bugfixes` | **Date**: 2026-04-06 | **Spec**: `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/spec.md`
**Input**: Feature specification from `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Close the MCP authorization gaps, harden MCP middleware and token-cache behavior, and make OpenTelemetry startup resilient in `/home/runner/work/solune/solune/solune/backend`, then finish the scoped React lifecycle bug fixes and targeted coverage work in `/home/runner/work/solune/solune/solune/frontend`. The implementation should stay minimal: reuse the existing MCP tool authorization helpers in resource handlers, fail closed in middleware, keep the auth-cache fix to an exact-bound correction, wrap OTel startup with graceful fallback, and extend or add only the tests needed to satisfy the backend (≥75%) and frontend (50/44/41/50) coverage gates already defined by the repo.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python >=3.12 (backend runtime, pyright configured for 3.13) and TypeScript ~6.0 with React 19.2 (frontend)  
**Primary Dependencies**: FastAPI, Starlette, MCP Python SDK, httpx, OpenTelemetry, uv, pytest, pytest-cov, ruff, pyright; React 19, Vite 8, Vitest 4, eslint, React Testing Library, react-hook-form  
**Storage**: SQLite-backed backend services plus in-memory MCP auth cache/rate-limit state and pipeline state store; frontend browser state only  
**Testing**: Backend uses `uv run pytest` with coverage, `uv run ruff check`, `uv run pyright`; frontend uses `npm run test`, `npm run test:coverage`, `npm run lint`, `npm run type-check`, `npm run build`  
**Target Platform**: Linux-hosted web application with FastAPI backend and browser-based React frontend  
**Project Type**: Web application with separate backend and frontend projects under `/home/runner/work/solune/solune/solune/{backend,frontend}`  
**Performance Goals**: Preserve existing MCP stateless HTTP behavior at `/api/v1/mcp`, avoid extra React render loops, and ensure telemetry outages do not block startup  
**Constraints**: Smallest necessary code changes; fail closed on invalid MCP auth; keep non-HTTP middleware pass-through behavior; no new dependencies; backend coverage must remain ≥75%; frontend coverage must meet 50% statements / 44% branches / 41% functions / 50% lines  
**Scale/Scope**: Targeted edits across backend MCP auth and observability files, five frontend bug-fix modules, existing plus new backend MCP tests, and the frontend tests needed to clear current branch coverage gaps; no schema migrations or new product surface area

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I — Specification-First Development**: PASS. `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/spec.md` contains prioritized user stories, independent tests, acceptance scenarios, scope boundaries, and measurable success criteria.
- **Principle II — Template-Driven Workflow**: PASS. This document keeps the canonical plan template structure and adds one execution-order section only to make the security-first dependency order explicit for this feature.
- **Principle III — Agent-Orchestrated Execution**: PASS. Plan-phase outputs are limited to `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, and the required agent-context refresh.
- **Principle IV — Test Optionality with Clarity**: PASS. Tests are explicitly mandated by FR-005 through FR-017, so this plan orders regression tests ahead of the corresponding source fixes.
- **Principle V — Simplicity and DRY**: PASS. The design reuses `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/tools/__init__.py` helpers, keeps backend fixes localized, and avoids refactors outside the named bug surfaces.

**Pre-Research Gate Result**: PASS — no constitution violations or unresolved clarifications block Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-test-coverage-bugfixes/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
/home/runner/work/solune/solune/solune/
├── backend/
│   ├── src/
│   │   ├── main.py
│   │   ├── config.py
│   │   └── services/
│   │       ├── mcp_server/
│   │       │   ├── auth.py
│   │       │   ├── middleware.py
│   │       │   ├── resources.py
│   │       │   ├── server.py
│   │       │   └── tools/__init__.py
│   │       └── otel_setup.py
│   └── tests/
│       └── unit/
│           └── test_mcp_server/
│               ├── test_auth.py
│               ├── test_server.py
│               ├── test_tools_agents.py
│               ├── test_tools_apps.py
│               ├── test_tools_pipelines.py
│               ├── test_tools_projects.py
│               └── test_tools_tasks.py
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── agents/
    │   │   │   ├── AddAgentModal.tsx
    │   │   │   └── __tests__/AddAgentModal.test.tsx
    │   │   ├── chores/
    │   │   │   ├── AddChoreModal.tsx
    │   │   │   ├── ChoreCard.tsx
    │   │   │   └── __tests__/
    │   │   │       ├── AddChoreModal.test.tsx
    │   │   │       └── ChoreScheduleConfig.test.tsx
    │   │   ├── command-palette/CommandPalette.tsx
    │   │   └── tools/ToolSelectorModal.tsx
    │   └── hooks/
    │       ├── useCountdown.ts
    │       ├── useFirstErrorFocus.ts
    │       └── useCommandPalette.test.tsx
    └── package.json
```

**Structure Decision**: Use the existing split web-app structure rooted at `/home/runner/work/solune/solune/solune/backend` and `/home/runner/work/solune/solune/solune/frontend`. Backend planning centers on MCP auth/resource/observability files plus `tests/unit/test_mcp_server`; frontend planning centers on the named modal/component/hook files and their existing colocated tests so the work stays scoped and regression-focused.

## Execution Order

1. **Backend security fixes first (P1)**  
   - Add failing regression tests for MCP middleware and resource handlers.  
   - Fix `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/middleware.py` to return 401 on failed token verification while preserving non-HTTP pass-through.  
   - Fix `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/resources.py` to reuse `get_mcp_context()` and `verify_mcp_project_access()` for all three MCP resource URIs.
2. **Backend correctness and resilience second (P2)**  
   - Add or extend backend tests covering exact cache bounds, rate-limit cleanup, API timeout/error paths, and OTel graceful degradation.  
   - Fix `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/auth.py` cache eviction to enforce the configured maximum exactly.  
   - Wrap OTel initialization from `/home/runner/work/solune/solune/solune/backend/src/main.py` with graceful fallback using `/home/runner/work/solune/solune/solune/backend/src/services/otel_setup.py`.
3. **Frontend lifecycle bug fixes third (P2/P3)**  
   - Expand existing tests before source edits where tests already exist (`AddAgentModal.test.tsx`, `AddChoreModal.test.tsx`, `InstallConfirmDialog.test.tsx`, `ChoreScheduleConfig.test.tsx`).  
   - Apply minimal effect/ref/cleanup fixes in `AddAgentModal.tsx`, `AddChoreModal.tsx`, `ChoreCard.tsx`, `ToolSelectorModal.tsx`, and `CommandPalette.tsx`.
4. **Frontend coverage push last (P2)**  
   - Add missing hook and component tests for `useCountdown`, `useFirstErrorFocus`, `ConfirmChoreModal`, `ChoresGrid`, `ToolSelectorModal`, `CommandPalette`, and any other scoped files still needed to clear thresholds.  
   - Finish with repo-standard frontend coverage, lint, type-check, and build validation.

## Post-Design Constitution Re-Check

- **Principle I — Specification-First Development**: PASS. `research.md`, `data-model.md`, `contracts/`, and `quickstart.md` all trace directly back to the accepted stories and functional requirements in `spec.md`.
- **Principle II — Template-Driven Workflow**: PASS. All required plan-phase artifacts now exist under `/home/runner/work/solune/solune/specs/001-test-coverage-bugfixes/`.
- **Principle III — Agent-Orchestrated Execution**: PASS. The plan stops after Phase 1 artifacts and agent-context refresh, exactly matching the command scope.
- **Principle IV — Test Optionality with Clarity**: PASS. The design keeps tests only where the spec requires them and preserves tests-first ordering for each implementation workstream.
- **Principle V — Simplicity and DRY**: PASS. The design keeps to shared helper reuse, minimal lifecycle fixes, and no unjustified abstractions.

**Post-Design Gate Result**: PASS — design artifacts are consistent with the constitution and ready for `/speckit.tasks`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
