# Research: Harden Phase 2

**Feature**: Test Coverage Improvement  
**Date**: 2026-04-10  
**Status**: Complete

## R1: Backend Coverage Gap Analysis

**Decision**: All ~30 previously-untested backend modules now have test files  
**Rationale**: Comprehensive audit of `solune/backend/src/` vs `solune/backend/tests/` confirms
every public module (prompts/, copilot_polling/, mcp_server/tools/, chores/, middleware/) has at
least one corresponding test file. The 75 → 80% threshold increase targets depth of coverage
rather than breadth of new test files.  
**Alternatives considered**: Creating new test files for each module — unnecessary because test
files already exist; the gap is in branch and line coverage within those files.

### Findings

| Module Group | Source Files | Test Files | Notes |
|---|---|---|---|
| prompts/ | 6 | 6 | agent_instructions, issue_generation, label_classification, plan_instructions, task_generation, transcript_analysis |
| copilot_polling/ | 11 | 11 | All internal modules covered including state_validation, recovery, pipeline_state_service |
| mcp_server/tools/ | 8 | 8 | activity, agents, apps, chat, chores, pipelines, projects, tasks |
| services/chores/ | 5 | 5 | chat, counter, scheduler, service, template_builder |
| middleware/ | 5 | 5 | admin_guard, csp, csrf, rate_limit, request_id |

**Action**: Deepen existing test coverage — add edge-case tests, error paths, and branch coverage
to reach 80% threshold. Focus on files with lowest current coverage.

## R2: Frontend Coverage Gap Analysis

**Decision**: ~69 untested components identified across 6 categories  
**Rationale**: Component-level audit of `solune/frontend/src/components/` cross-referenced with
test files (`*.test.tsx`, `*.test.ts`, `__tests__/`) reveals significant gaps in chores (13),
agents (11), tools (9), settings (7), UI (13), and pipeline (16) directories.  
**Alternatives considered**: Only covering high-traffic components — rejected because the
threshold increase from 50%→60% statements requires broad coverage improvement.

### Untested Components by Category

| Category | Count | Components |
|---|---|---|
| chores/ | 13 | AddChoreModal, ChoreCard, ChoreChatFlow, ChoreInlineEditor, ChoreScheduleConfig, ChoresGrid, ChoresPanel, ChoresSaveAllBar, ChoresSpotlight, ChoresToolbar, ConfirmChoreModal, FeaturedRitualsPanel, PipelineSelector |
| agents/ | 11 | AddAgentModal, AgentAvatar, AgentCard, AgentChatFlow, AgentIconCatalog, AgentIconPickerModal, AgentInlineEditor, AgentsPanel, BulkModelUpdateDialog, InstallConfirmDialog, ToolsEditor |
| tools/ | 9 | EditRepoMcpModal, GitHubMcpConfigGenerator, McpPresetsGallery, RepoConfigPanel, ToolCard, ToolChips, ToolSelectorModal, ToolsPanel, UploadMcpModal |
| settings/ | 7 | AIPreferences, PrimarySettings, ProjectSettings, SignalConnection + 3 partially tested |
| ui/ | 13 | alert-dialog, character-counter, confirmation-dialog, copy-button, dialog, hover-card, keyboard-shortcut-modal, popover, skeleton, tooltip + 3 partially tested |
| pipeline/ | 16 | ModelSelector, ParallelStageGroup, PipelineStagesOverview + 13 partially tested |

### Current Thresholds vs Targets

| Metric | Current | Target | Delta |
|---|---|---|---|
| Statements | 50% | 60% | +10% |
| Branches | 44% | 52% | +8% |
| Functions | 41% | 50% | +9% |
| Lines | 50% | 60% | +10% |

## R3: Property-Based Testing Expansion

**Decision**: Expand from 15 files (9 backend + 6 frontend) with new round-trip serialization,
API validation edge cases, and migration idempotency tests  
**Rationale**: Property-based testing with Hypothesis (backend) and fast-check (frontend) is
already established with proper CI/dev profiles. Expanding coverage to serialization boundaries
and validation edge cases catches bugs that example-based tests miss.  
**Alternatives considered**: Fuzz testing expansion — already 4 fuzz files in backend; property
tests are more structured and provide better regression guarantees.

### Existing Property Tests

**Backend (Hypothesis 6.131.0+)**:

| File | Strategy | Type |
|---|---|---|
| test_pipeline_state_machine.py | RuleBasedStateMachine | Stateful |
| test_markdown_parser_roundtrips.py | text strategies | Round-trip |
| test_pipeline_states.py | composite strategies | Invariant |
| test_model_validation.py | builds strategies | Validation |
| test_bounded_cache_stateful.py | RuleBasedStateMachine | Stateful |
| test_blocking_queue.py | integers + lists | Concurrency |
| test_model_roundtrips.py | builds strategies | Round-trip |

**Frontend (fast-check/vitest 0.4.0)**:

| File | Strategy | Type |
|---|---|---|
| formatTime.property.test.ts | arbitrary timestamps | Round-trip |
| utils.property.test.ts | string strategies | Invariant |
| time-utils.property.test.ts | date strategies | Invariant |
| case-utils.property.test.ts | string strategies | Round-trip |
| pipelineMigration.property.test.ts | pipeline configs | Idempotency |
| buildGitHubMcpConfig.property.test.ts | config objects | Invariant |

### Expansion Targets

- **Round-trip serialization**: Model → JSON → Model for all API request/response types
- **API validation edge cases**: Boundary values, Unicode, empty strings, max-length fields
- **Migration idempotency**: Pipeline migrations applied twice produce same result

## R4: Axe-Core Playwright Integration

**Decision**: Extend @axe-core/playwright usage from 2 files to 6 files (auth, board, chat,
settings flows)  
**Rationale**: @axe-core/playwright 4.10.1 is installed and working in `ui.spec.ts` and
`protected-routes.spec.ts`. The pattern uses `new AxeBuilder({ page }).analyze()` with WCAG 2.1
tags. Auth, board, chat, and settings flows are user-critical paths missing a11y checks.  
**Alternatives considered**: jest-axe for unit tests — already installed (jest-axe 10.0.0) but
E2E-level a11y catches rendering and interaction issues that unit tests miss.

### Current State

| File | Has AxeBuilder | A11y Tests |
|---|---|---|
| ui.spec.ts | ✓ | 1 test (login page audit) |
| protected-routes.spec.ts | ✓ | 1 test per route (redirect + a11y) |
| auth.spec.ts | ✗ | None |
| board-navigation.spec.ts | ✗ | None |
| chat-interaction.spec.ts | ✗ | None |
| settings-flow.spec.ts | ✗ | None |

### Integration Pattern

```typescript
import AxeBuilder from '@axe-core/playwright';

// After page loads and stabilizes:
const results = await new AxeBuilder({ page })
  .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
  .analyze();
expect(results.violations).toEqual([]);
```

### E2E Fixture Architecture

- `fixtures.ts`: Unauthenticated, mocks `/api/**` with 401 for auth/me
- `authenticated-fixtures.ts`: Authenticated, provides `mockApi` helper
- Auth/UI specs use `fixtures.ts`; board/chat/settings use `authenticated-fixtures.ts`

## R5: Test Infrastructure and CI

**Decision**: Leverage existing CI pipeline (9 jobs) without structural changes  
**Rationale**: CI already runs Backend, Frontend, Frontend E2E as separate jobs. Coverage
thresholds are enforced in pyproject.toml (backend) and vitest.config.ts (frontend). Threshold
bumps require only config changes.  
**Alternatives considered**: Adding dedicated coverage jobs — unnecessary overhead; existing jobs
already collect and enforce coverage.

### CI Job Structure

| Job | Blocking | Runs |
|---|---|---|
| Backend | Yes | pytest with coverage |
| Backend Advanced Tests | No (continue-on-error) | Property/chaos/fuzz tests |
| Frontend | Yes | vitest with coverage |
| Frontend E2E | No (continue-on-error) | Playwright specs |
| Docs Lint | Yes | markdownlint |
| Diagrams | Yes | Diagram validation |
| Contract Validation | Yes | API contract checks |
| Build Validation | Yes | Full build check |
| Docker Build | Yes (needs backend+frontend) | Docker image build |

### Test Configuration Summary

**Backend (pyproject.toml)**:
- `fail_under = 75` (target: 80)
- `asyncio_mode = "auto"`
- `branch = true` (branch coverage enabled)
- Mutation testing: mutmut 3.2.0 for api/, middleware/, utils.py

**Frontend (vitest.config.ts)**:
- Provider: v8
- Environment: happy-dom
- Globals: true
- Coverage: all source files included
