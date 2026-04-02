# Specification Analysis Report: Model Reasoning Level Selection

**Feature**: `545-model-reasoning-selection`  
**Analyzed**: 2026-04-02  
**Artifacts**: spec.md, plan.md, tasks.md, data-model.md, contracts/, quickstart.md, constitution.md  
**Status**: All 3 core artifacts present ✅ | All 17 referenced source files verified ✅

---

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F1 | Underspecification | **CRITICAL** | tasks.md:T018, orchestrator.py:1661 | T018 changes `_resolve_effective_model()` return type from `str` to `tuple[str, str]` but no task addresses updating the single call site at orchestrator.py:1661 (`effective_model = await self._resolve_effective_model(...)`) which expects a `str`. This would cause a runtime type error. | Add a sub-task under T018 (or a new task) to update the call site at orchestrator.py:1661 to unpack the tuple: `effective_model, reasoning_effort = await self._resolve_effective_model(...)` and thread `reasoning_effort` downstream. |
| F2 | Coverage Gap | **HIGH** | tasks.md Phase 6 (US4), spec.md:US4 | User Story 4 has **zero test tasks** despite the tasks.md header declaring "Tests: Included — the feature specification explicitly requests backend unit tests, frontend unit tests, and contract validation." Phase 6 contains only T019-T020 (implementation), violating the document's own test-first approach. | Add test tasks for US4: at minimum, a frontend test verifying AgentNode stores `reasoning_effort` alongside `model_id` and PipelineModelDropdown passes it through on selection. |
| F3 | Underspecification | **HIGH** | tasks.md:T018, plan.md:L6 (FR-006), orchestrator.py:836-886 | The precedence chain specifies "pipeline config → user settings → **model default** → empty" but `_resolve_effective_model()` currently receives only `agent_assignment`, `agent_slug`, `project_id`, `user_agent_model`. It has no access to `ModelOption` data needed to resolve the "model default" step. No task describes how to pass model metadata to the orchestrator. | Either (a) add a parameter to `_resolve_effective_model()` for the model's `default_reasoning_effort`, or (b) document that "model default" is deferred to the SDK (omitted = provider picks default) and update FR-006 accordingly. |
| F4 | Underspecification | **HIGH** | tasks.md:T019, AgentNode.tsx:130-133, ExecutionGroupCard.tsx:193-194 | The `onModelSelect` callback in AgentNode/ExecutionGroupCard currently has signature `(modelId: string, modelName: string)`. To pass `reasoning_effort` for pipeline agent configuration, this callback needs a third parameter or an object parameter. No task explicitly addresses this callback signature change. | Add explicit instructions to T019 to update the `onModelSelect` callback signature in AgentNode.tsx and the `onUpdateAgent` call in ExecutionGroupCard.tsx to include `reasoning_effort`. |
| F5 | Inconsistency | **MEDIUM** | quickstart.md:L141, tasks.md Phases 3-6 | quickstart.md labels "Phase 3: Frontend — Types, API, and UI **(P2)**" but this phase covers all frontend work including P1 user stories (US1, US2). The tasks.md uses a different (correct) phase numbering: Phase 3=US1(P1), Phase 4=US2(P1), Phase 5=US3(P1), Phase 6=US4(P2). Priority label "(P2)" in quickstart is misleading. | Update quickstart.md Phase 3 to remove the "(P2)" priority label, or restructure quickstart phases to match tasks.md numbering. |
| F6 | Coverage Gap | **MEDIUM** | spec.md:FR-009, tasks.md:T010 | FR-009: "The system MUST visually highlight the model's default reasoning level among its variants." T010's description mentions color-coded pills but does **not explicitly mention default highlighting**. T006 (test) does test for "highlights model default", creating a gap between the test expectation and the implementation task description. | Amend T010 description to explicitly include: "highlight the model's default reasoning level variant (e.g., with a '(Default)' suffix or distinct visual indicator)." |
| F7 | Coverage Gap | **MEDIUM** | spec.md:FR-013, tasks.md | FR-013: "The system MUST maintain backwards compatibility — existing users with no reasoning preference MUST experience no change in behavior." No dedicated test task verifies backwards compatibility (e.g., existing settings without `reasoning_effort` field continue to work). This is implicitly covered by empty-string defaults but not explicitly tested. | Add a test case (in T014 or T015) verifying that an AIPreferences object without `reasoning_effort` (or with `reasoning_effort=""`) results in reasoning_effort being omitted from SessionConfig and no behavioral change. |
| F8 | Underspecification | **MEDIUM** | tasks.md:T002, frontend types/index.ts:1181-1190 | T002 adds `reasoningEffort` to `PipelineModelOverride` (pipeline-level override) but does not mention the frontend `PipelineAgentNode` type. While `PipelineAgentNode.config: Record<string, unknown>` can hold `reasoning_effort` without a type change, this is less type-safe and inconsistent with the typed `PipelineModelOverride` approach. Existing test fixtures for PipelineModelOverride (`usePipelineBoardMutations.test.tsx:45-46`) will also need updating. | Either (a) document that per-agent reasoning_effort uses the generic `config` dict (acceptable), or (b) add an explicit `reasoning_effort?: string` field to `PipelineAgentNode` frontend type for type safety. Also note that existing PipelineModelOverride test fixtures need updating. |
| F9 | Ambiguity | **MEDIUM** | spec.md:SC-009, tasks.md | SC-009: "Users can complete the reasoning level selection workflow in **under 10 seconds**." No automated test infrastructure exists for UX timing measurement, making this criterion untestable in CI. It can only be validated manually. | Either (a) remove SC-009 as a measurable outcome and move to manual verification, or (b) document it as a manual-only verification step in Phase 7. |
| F10 | Underspecification | **LOW** | data-model.md:L24-26, tasks.md | Data-model specifies validation rules: `supported_reasoning_efforts` values MUST be from `{"low", "medium", "high", "xhigh"}` and `default_reasoning_effort` MUST be a member of `supported_reasoning_efforts`. No task adds a Pydantic validator to enforce these rules. The current approach trusts SDK data. | Either (a) add a Pydantic `field_validator` to ModelOption to enforce the enum constraint (defensive), or (b) explicitly document in data-model.md that validation is delegated to the SDK and no server-side validation is needed (trust SDK). |
| F11 | Underspecification | **LOW** | tasks.md:T017 | T017 uses `type: ignore[typeddict-extra-key]` to inject `reasoning_effort` into `GitHubCopilotOptions`, a workaround for the MAF framework not natively supporting reasoning_effort. This is fragile and should be tracked as tech debt. | Add a note in plan.md Complexity Tracking section documenting this workaround and the condition for removing it (when `agent_framework_github_copilot` adds native `reasoning_effort` support to `GitHubCopilotOptions`). |
| F12 | Inconsistency | **LOW** | quickstart.md:L57-60, tasks.md:T021 | quickstart.md Step 3 shows `cd solune/backend && python ../scripts/export-openapi.py` but T021 says `python scripts/export-openapi.py` from `solune/backend/`. The actual script is at `solune/scripts/export-openapi.py` (repo root `scripts/`). The quickstart path `../scripts/` is correct relative to `solune/backend/`; T021's path is ambiguous. | Clarify T021 to use an absolute path from repo root: `cd solune/backend && python ../scripts/export-openapi.py` or `python solune/scripts/export-openapi.py` from repo root. |

---

## Coverage Summary

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 (expose-reasoning-levels) | ✅ | T001, T007 | Backend model + SDK population |
| FR-002 (auto-populate-from-provider) | ✅ | T007 | getattr pattern from SDK |
| FR-003 (select-default-reasoning) | ✅ | T001, T012, T013 | AIPreferences field + settings UI |
| FR-004 (separate-fields-storage) | ✅ | T001, T013 | Separate model + reasoning_effort |
| FR-005 (pass-to-provider) | ✅ | T016, T017 | Completion provider + agent provider paths |
| FR-006 (precedence-resolution) | ⚠️ | T018 | "Model default" step underspecified (see F3) |
| FR-007 (expand-variants-in-dropdowns) | ✅ | T009, T012 | useModels expansion + DynamicDropdown |
| FR-008 (reasoning-badge) | ✅ | T010 | ReasoningBadge with Brain icon |
| FR-009 (highlight-default-level) | ⚠️ | T010 | Implicit in T010, not explicit (see F6) |
| FR-010 (non-reasoning-unchanged) | ✅ | T009, T010 | Pass-through logic + no-badge guard |
| FR-011 (per-pipeline-agent-config) | ✅ | T019, T020 | AgentNode + PipelineModelDropdown |
| FR-012 (api-contract-sync) | ✅ | T021, T022 | OpenAPI regen + contract validation |
| FR-013 (backwards-compatibility) | ⚠️ | — | No dedicated task; implicit via empty defaults (see F7) |

---

## Constitution Alignment

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Specification-First** | ✅ PASS | spec.md has 4 prioritized user stories (P1-P2) with GWT scenarios and independent test criteria |
| **II. Template-Driven Workflow** | ✅ PASS | All 7 artifacts follow canonical templates |
| **III. Agent-Orchestrated** | ✅ PASS | Clear phase transitions; well-defined inputs/outputs per agent |
| **IV. Test Optionality** | ⚠️ PARTIAL | Tests are included per spec requirement, but **US4 has zero test tasks** (F2). Violates test-first discipline declared in tasks.md header. |
| **V. Simplicity and DRY** | ✅ PASS | Expansion centralized in `useModels()` hook; single `ReasoningBadge` reused; no premature abstraction |

**Constitution Issues**: 1 partial violation (Principle IV for US4 test coverage). Not CRITICAL because US4 is P2 and the core P1 stories are well-tested, but should be remediated before `/speckit.implement`.

---

## Unmapped Tasks

None — all 23 tasks map to at least one requirement or user story.

---

## Metrics

| Metric | Value |
|--------|-------|
| Total Functional Requirements | 13 |
| Total Tasks | 23 |
| Coverage % (requirements with ≥1 task) | **84.6%** (11/13 fully covered, 2 partially) |
| Ambiguity Count | 1 (SC-009 timing) |
| Duplication Count | 0 |
| Critical Issues | **1** (F1: return type break) |
| High Issues | **3** (F2, F3, F4) |
| Medium Issues | **5** (F5-F9) |
| Low Issues | **3** (F10-F12) |
| Total Findings | **12** |

---

## Next Actions

### ⛔ Resolve Before `/speckit.implement` (CRITICAL + HIGH)

1. **F1** (CRITICAL): Add a task to update the `_resolve_effective_model()` call site at orchestrator.py:1661 to handle the new tuple return type. Without this, the implementation will produce a runtime error.

2. **F2** (HIGH): Add test tasks for US4 in Phase 6 to maintain test-first discipline. At minimum:
   - Frontend test: AgentNode stores `reasoning_effort` in config on model variant selection
   - Frontend test: PipelineModelDropdown passes `reasoning_effort` through on selection

3. **F3** (HIGH): Clarify the "model default" precedence step in T018. Either:
   - Add a new parameter to `_resolve_effective_model()` for model default reasoning
   - Or simplify precedence to "pipeline config → user settings → empty (SDK default)" and update spec FR-006

4. **F4** (HIGH): Update T019 to explicitly address the `onModelSelect` callback signature change in AgentNode.tsx and ExecutionGroupCard.tsx.

### ✅ Proceed with Awareness (MEDIUM + LOW)

- **F5**: quickstart.md phase numbering drift — cosmetic, won't block implementation
- **F6-F7**: Task description gaps — implementer should reference spec FRs directly
- **F8**: PipelineAgentNode type safety — acceptable if documented
- **F9-F12**: Minor clarifications and tech debt tracking

### Suggested Commands

```bash
# After resolving CRITICAL/HIGH issues:
# Run /speckit.tasks with refinements to regenerate tasks.md
# OR manually edit tasks.md to add missing tasks/descriptions

# Then proceed:
# /speckit.implement
```

---

## Remediation Offer

Would you like me to suggest concrete remediation edits for the top 4 issues (F1-F4)? (Edits will NOT be applied automatically — this analysis is read-only.)
