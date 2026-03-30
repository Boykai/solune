# Tasks: Complete v0.2.0 — Intelligent Chat Agent

**Input**: Design documents from `/specs/001-intelligent-chat-agent/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/tool-contracts.yaml ✅, quickstart.md ✅

**Tests**: Included — explicitly required by the feature specification verification section and parent issue.

**Organization**: Tasks are grouped by user story (3 stories from spec.md) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- All file paths are relative to repository root

## Path Conventions

- **Project type**: Web application (backend + frontend monorepo)
- **Backend**: `solune/backend/src/`, `solune/backend/tests/`
- **Frontend**: No changes (existing chat UI handles action responses generically)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify project readiness — no new files are created; all changes extend existing files.

- [ ] T001 Verify backend development environment and sync dependencies via `uv sync --prerelease=allow` in solune/backend/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Enum extension and config setting that must exist before User Story 2 can be implemented. These are small, isolated changes in separate files.

**⚠️ CRITICAL**: Phase 4 (US2) cannot begin until these are complete.

- [ ] T002 [P] Add `PIPELINE_LAUNCH = "pipeline_launch"` value to the `ActionType` StrEnum in solune/backend/src/models/chat.py
- [ ] T003 [P] Add `chat_auto_create_enabled: bool = False` setting to the `Settings` class in solune/backend/src/config.py

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 — Automatic Difficulty Assessment & Pipeline Selection (Priority: P1) 🎯 MVP

**Goal**: Agent evaluates project complexity (XS/S/M/L/XL) and selects the appropriate pipeline preset automatically, giving users actionable guidance on project scope.

**Independent Test**: Describe a project idea in chat (e.g., "Build me a stock tracking app with React and Azure") and verify the agent responds with a complexity rating and recommended pipeline configuration including stages and agents.

### Implementation for User Story 1

- [ ] T004 [US1] Add `DIFFICULTY_PRESET_MAP` constant dict mapping difficulty levels to preset IDs (XS→`github-copilot`, S→`easy`, M→`medium`, L→`hard`, XL→`expert`) in solune/backend/src/services/agent_tools.py
- [ ] T005 [US1] Create `assess_difficulty` `@tool` function that accepts `difficulty` (str) and `reasoning` (str) parameters, records `difficulty` in `context.session.state["assessed_difficulty"]`, maps to preset via `DIFFICULTY_PRESET_MAP`, and returns `ToolResult(content=reasoning_text, action_type=None, action_data=None)` in solune/backend/src/services/agent_tools.py
- [ ] T006 [US1] Create `select_pipeline_preset` `@tool` function that accepts `difficulty` (str) and `project_name` (str), reads presets from `_PRESET_DEFINITIONS` in the pipelines service module, maps difficulty to preset ID via `DIFFICULTY_PRESET_MAP` (fallback to `"medium"` per FR-013), sets `context.session.state["selected_preset_id"]`, and returns `ToolResult` with preset details (name, stages, agents) in solune/backend/src/services/agent_tools.py
- [ ] T007 [US1] Register `assess_difficulty` and `select_pipeline_preset` in `register_tools()` return list in solune/backend/src/services/agent_tools.py
- [ ] T008 [P] [US1] Update `AGENT_SYSTEM_INSTRUCTIONS` in `build_system_instructions()` to include difficulty assessment workflow: always assess difficulty before creating a project, use assess→select→create sequence, explain the selected pipeline preset (stages, agents) to the user, and default to "medium" if assessment is ambiguous in solune/backend/src/prompts/agent_instructions.py

### Tests for User Story 1

- [ ] T009 [P] [US1] Add `TestAssessDifficulty` test class with tests: valid `ToolResult` returned with `action_type=None`, session state `assessed_difficulty` is set correctly, all five difficulty levels (XS/S/M/L/XL) produce correct results in solune/backend/tests/unit/test_agent_tools.py
- [ ] T010 [US1] Add `TestSelectPipelinePreset` test class with tests: correct preset ID selected for each difficulty level, unknown/ambiguous difficulty falls back to `"medium"` preset (FR-013), `selected_preset_id` is set in session state, preset details (stages, agents) included in result content in solune/backend/tests/unit/test_agent_tools.py
- [ ] T011 [US1] Update `TestRegisterTools` assertion to verify 9 tools returned (7 existing + 2 new: `assess_difficulty`, `select_pipeline_preset`) in solune/backend/tests/unit/test_agent_tools.py

**Checkpoint**: User Story 1 is fully functional — agent can assess difficulty and select pipeline presets. Verify with `uv run pytest tests/unit/test_agent_tools.py -x -v` from solune/backend/.

---

## Phase 4: User Story 2 — Autonomous Project Creation from Chat (Priority: P2)

**Goal**: Agent creates GitHub issues and launches pipelines directly from chat conversation, with an opt-in safety gate (`CHAT_AUTO_CREATE_ENABLED`) and mandatory confirmation prompt.

**Independent Test**: Enable autonomous creation, describe a project in chat, confirm when asked, and verify a GitHub issue is created and a pipeline is launched. When disabled, verify the agent presents a proposal instead.

### Implementation for User Story 2

- [ ] T012 [US2] Create `create_project_issue` `@tool` function that accepts `title` (str) and `body` (str), checks `CHAT_AUTO_CREATE_ENABLED` from settings — when disabled returns proposal `ToolResult(action_type=None)`, when enabled calls `GitHubProjectsService.create_issue()` using `github_token`/`project_name` from session state and returns `ToolResult(action_type="issue_create", action_data={issue_number, issue_url, preset_id, project_name})` in solune/backend/src/services/agent_tools.py
- [ ] T013 [US2] Create `launch_pipeline` `@tool` function that accepts optional `pipeline_id` (str), reads `selected_preset_id` and `project_id` from session state, calls `PipelineService` to initiate pipeline execution, and returns `ToolResult(action_type="pipeline_launch", action_data={pipeline_id, preset, stages})` in solune/backend/src/services/agent_tools.py
- [ ] T014 [US2] Register `create_project_issue` and `launch_pipeline` in `register_tools()` return list in solune/backend/src/services/agent_tools.py
- [ ] T015 [P] [US2] Handle `PIPELINE_LAUNCH` action_type in `_convert_response()` and `run_stream()` methods — ensure `pipeline_launch` tool results are correctly extracted and mapped to `ChatMessage.action_type` and `ChatMessage.action_data` in solune/backend/src/services/chat_agent.py
- [ ] T016 [P] [US2] Update `AGENT_SYSTEM_INSTRUCTIONS` with autonomous creation workflow: full sequence is clarify→assess difficulty→select preset→create issue→launch pipeline→report back; always ask "Shall I proceed?" before creating any external resources (FR-006); when auto-create is disabled, present a detailed proposal instead in solune/backend/src/prompts/agent_instructions.py

### Tests for User Story 2

- [ ] T017 [US2] Add `TestCreateProjectIssue` test class with tests: calls `GitHubProjectsService.create_issue()` with correct arguments, returns `ToolResult` with `action_type="issue_create"` and valid `action_data`, respects `CHAT_AUTO_CREATE_ENABLED=False` by returning proposal with `action_type=None`, handles GitHub API errors gracefully in solune/backend/tests/unit/test_agent_tools.py
- [ ] T018 [US2] Add `TestLaunchPipeline` test class with tests: calls `PipelineService` correctly, returns `ToolResult` with `action_type="pipeline_launch"` and `action_data` containing `pipeline_id`/`preset`/`stages`, reads `selected_preset_id` from session state in solune/backend/tests/unit/test_agent_tools.py
- [ ] T019 [P] [US2] Add test for `pipeline_launch` response conversion in `TestChatAgentServiceRun` — verify `_convert_response()` correctly maps `pipeline_launch` action_type and action_data to `ChatMessage` in solune/backend/tests/unit/test_chat_agent.py
- [ ] T020 [US2] Update `TestRegisterTools` assertion to verify 11 tools returned (7 existing + 4 new) in solune/backend/tests/unit/test_agent_tools.py

**Checkpoint**: User Stories 1 AND 2 are both functional — full end-to-end workflow (assess→select→create→launch) works. Verify with `uv run pytest tests/unit/test_agent_tools.py tests/unit/test_chat_agent.py -x -v` from solune/backend/.

---

## Phase 5: User Story 3 — MCP Tool Extensibility for Projects (Priority: P3)

**Goal**: Dynamic MCP tool loading so the agent can invoke project-configured MCP servers alongside built-in tools. Foundation layer only — full marketplace deferred to v0.4.0.

**Independent Test**: Configure an MCP tool server for a project and verify the agent loads and includes those tools when initialized. If no MCP tools are configured, the agent functions normally with built-in tools only and no errors.

### Implementation for User Story 3

- [ ] T021 [US3] Create `load_mcp_tools(project_id: str, db: aiosqlite.Connection) -> dict[str, Any]` async function that queries `mcp_tool_configs` table for active configs matching `project_id`, converts each `McpToolConfig` to a dict compatible with `GitHubCopilotOptions.mcp_servers` (using `name` as key, `endpoint_url` and `config_content` as values), returns empty dict when no MCP tools configured (log at INFO level) or on error (log at WARNING/ERROR level per FR-012) in solune/backend/src/services/agent_tools.py
- [ ] T022 [P] [US3] Update `create_agent()` and `_create_copilot_agent()` in agent_provider.py to accept optional `mcp_servers: dict[str, Any] | None = None` parameter and pass it to `GitHubCopilotOptions` when creating the Copilot agent in solune/backend/src/services/agent_provider.py
- [ ] T023 [US3] Wire `load_mcp_tools()` into `ChatAgentService` — call `load_mcp_tools(project_id, db)` during agent creation and pass the resulting `mcp_servers` dict to `create_agent()` in solune/backend/src/services/chat_agent.py

### Tests for User Story 3

- [ ] T024 [US3] Add `TestLoadMcpTools` test class with tests: returns valid config dicts when active MCP configs exist for project, returns empty dict when no MCP tools configured (INFO log), returns empty dict and logs warning/error on database failure (FR-012), only loads `is_active=True` configs in solune/backend/tests/unit/test_agent_tools.py

**Checkpoint**: All three user stories are independently functional. MCP tools are loaded when available, skipped gracefully when not. Verify with `uv run pytest tests/unit/test_agent_tools.py tests/unit/test_chat_agent.py -x -v` from solune/backend/.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verification across all stories, code quality, and deployment validation.

- [ ] T025 Run full backend test suite via `uv run pytest --cov=src -x` in solune/backend/
- [ ] T026 [P] Run linting via `uv run ruff check src/ tests/` and `uv run ruff format --check src/ tests/` in solune/backend/
- [ ] T027 [P] Run type checking via `uv run pyright` on modified files (agent_tools.py, chat_agent.py, agent_provider.py, chat.py, config.py, agent_instructions.py) in solune/backend/
- [ ] T028 Verify Docker build via `docker compose build backend && docker compose up -d` from solune/
- [ ] T029 Run quickstart.md validation — verify both E2E scenarios (auto=True and auto=False) from specs/001-intelligent-chat-agent/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS User Story 2 (Phase 4)
- **User Story 1 (Phase 3)**: Can start after Setup (Phase 1) — does not require Foundational (Phase 2)
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) AND User Story 1 (Phase 3) — the autonomous workflow requires difficulty assessment to be implemented first
- **User Story 3 (Phase 5)**: Can start after Setup (Phase 1) — independent of Phases 2-4; can run in parallel with Phase 4
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Setup (Phase 1) — No dependencies on other stories. Delivers immediate value (difficulty assessment + pipeline recommendation).
- **User Story 2 (P2)**: Depends on Foundational (Phase 2) for `PIPELINE_LAUNCH` enum and `CHAT_AUTO_CREATE_ENABLED` config. Depends on User Story 1 (Phase 3) because the autonomous workflow requires `assess_difficulty` → `select_pipeline_preset` → `create_project_issue` → `launch_pipeline` sequence.
- **User Story 3 (P3)**: Can start after Setup (Phase 1) — Independent of US1 and US2. Can run in parallel with Phase 4 by a different developer.

### Within Each User Story

- Implementation tasks in `agent_tools.py` are sequential (same file: constant → tool functions → registration)
- Instruction updates (`agent_instructions.py`) can parallel with implementation (different file) but logically depend on knowing tool names
- Tests (`test_agent_tools.py`) can parallel with instruction updates (different files) but depend on implementation being complete
- Response handling (`chat_agent.py`) can parallel with tool implementation (different file)

### Parallel Opportunities

- **Phase 2**: T002 ‖ T003 (models/chat.py ‖ config.py)
- **Phase 3**: T008 ‖ T009 (agent_instructions.py ‖ test_agent_tools.py — after T004-T007 complete)
- **Phase 4**: T015 ‖ T016 (chat_agent.py ‖ agent_instructions.py — after T012-T014 complete); T019 ‖ T017 (test_chat_agent.py ‖ test_agent_tools.py)
- **Phase 5**: T022 ‖ T021 (agent_provider.py ‖ agent_tools.py)
- **Cross-phase**: Phase 3 (US1) ‖ Phase 5 (US3) can run in parallel by different developers
- **Phase 6**: T026 ‖ T027 (linting ‖ type checking)

---

## Parallel Example: User Story 1

```text
# Sequential: Implementation in agent_tools.py (same file)
T004: Add DIFFICULTY_PRESET_MAP constant in solune/backend/src/services/agent_tools.py
T005: Create assess_difficulty tool in solune/backend/src/services/agent_tools.py
T006: Create select_pipeline_preset tool in solune/backend/src/services/agent_tools.py
T007: Register new tools in solune/backend/src/services/agent_tools.py

# Parallel after T004-T007 complete (different files):
T008: Update agent instructions in solune/backend/src/prompts/agent_instructions.py
T009: Add assess_difficulty tests in solune/backend/tests/unit/test_agent_tools.py
```

## Parallel Example: User Story 2

```text
# Sequential: Implementation in agent_tools.py (same file)
T012: Create create_project_issue tool in solune/backend/src/services/agent_tools.py
T013: Create launch_pipeline tool in solune/backend/src/services/agent_tools.py
T014: Register new tools in solune/backend/src/services/agent_tools.py

# Parallel after T012-T014 complete (different files):
T015: Handle pipeline_launch in solune/backend/src/services/chat_agent.py
T016: Update agent instructions in solune/backend/src/prompts/agent_instructions.py
T019: Add pipeline_launch test in solune/backend/tests/unit/test_chat_agent.py
```

## Parallel Example: Cross-Phase

```text
# After Phase 2 (Foundational) completes, these can run in parallel:
Developer A: Phase 3 (US1) → Phase 4 (US2)
Developer B: Phase 5 (US3)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 3: User Story 1 (Difficulty Assessment & Pipeline Selection)
3. **STOP and VALIDATE**: Test US1 independently — agent assesses difficulty and recommends presets
4. Deploy/demo if ready — delivers immediate value without autonomous creation

### Incremental Delivery

1. Complete Setup → Foundation ready
2. Add User Story 1 → Test independently → **MVP!** (agent recommends pipelines)
3. Complete Foundational (Phase 2) → Enum + config ready
4. Add User Story 2 → Test independently → **Full workflow** (assess→select→create→launch)
5. Add User Story 3 → Test independently → **Extensible** (project MCP tools loaded)
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup together
2. Once Setup is done:
   - Developer A: Phase 2 (Foundational) + Phase 3 (US1) + Phase 4 (US2) — main workflow path
   - Developer B: Phase 5 (US3) — MCP extensibility, independent
3. Stories complete and integrate independently
4. Team reconvenes for Phase 6 (Polish)

---

## Notes

- [P] tasks = different files, no dependencies on other incomplete tasks in the same phase
- [Story] label maps task to specific user story for traceability
- All 4 new tools follow the established `@tool` → `ToolResult` pattern (7 existing tools use this pattern)
- `DIFFICULTY_PRESET_MAP` uses simplified primary mapping per research.md R2 (not overlap ranges)
- `load_mcp_tools()` is a regular async function, NOT a `@tool` — it runs at agent initialization, not during conversation
- `register_tools()` final count: 11 tools (7 existing + 4 new `@tool` functions)
- Avoid: modifying `PipelineService` or `GitHubProjectsService` — reuse existing methods only
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
