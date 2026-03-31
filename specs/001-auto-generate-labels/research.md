# Research: Auto-generate Labels for GitHub Parent Issues

**Feature**: 001-auto-generate-labels
**Date**: 2026-03-31
**Status**: Complete

## Research Tasks

### RT-001: AI Completion Provider Selection for Label Classification

**Context**: The spec assumes the existing AI completion provider can be used for label classification. Need to confirm which provider to use and how to invoke it.

**Decision**: Use the existing `CompletionProvider` abstraction from `src/services/completion_providers.py` (CopilotCompletionProvider or AzureOpenAICompletionProvider). Despite being marked deprecated in favor of the Microsoft Agent Framework, the completion provider is simpler and more appropriate for a single-shot classification call than spinning up a full agent session.

**Rationale**: The label classifier needs a simple text-in/labels-out function. The Microsoft Agent Framework (`chat_agent.py`) is designed for multi-turn, tool-using agent conversations — massive overkill for a one-shot classification. The `CompletionProvider.complete()` method provides exactly the interface needed: send messages, receive a text response.

**Alternatives considered**:
- **Microsoft Agent Framework**: Too heavyweight for single-shot classification; requires session management, tool registration, and turn-based conversation flow.
- **Direct HTTP call to Copilot/OpenAI API**: Bypasses the existing abstraction; would duplicate client management and authentication logic already solved by `CompletionProvider`.
- **Regex/keyword matching (no AI)**: Simpler but would not achieve the 90% accuracy target (SC-005); keyword lists cannot infer intent from context (e.g., distinguishing "frontend" scope from "frontend" mentioned as context).

---

### RT-002: Prompt Engineering for Label Classification

**Context**: Need a prompt that reliably produces structured, valid labels from the predefined taxonomy given an issue title and optional description.

**Decision**: Use a system prompt that includes the full label taxonomy from `constants.LABELS` (dynamically injected, not hardcoded in the prompt template) and instructs the model to return a JSON object with a single `labels` array. The prompt explicitly states the rules: exactly one type label, "ai-generated" always included, only labels from the taxonomy.

**Rationale**: JSON output is reliably parseable. Dynamically injecting the taxonomy from `constants.LABELS` satisfies FR-010 (no hardcoded labels in the prompt). Providing the full taxonomy in the prompt gives the model the complete context to make accurate selections.

**Alternatives considered**:
- **Comma-separated text output**: Harder to parse reliably; edge cases with label names containing commas or spaces (e.g., "good first issue").
- **Multiple separate prompts (one per category)**: More accurate per category but 3-4x the latency and cost; single prompt achieves acceptable accuracy for this use case.
- **Few-shot examples in prompt**: Adds token cost and maintenance burden; the taxonomy is small enough that the model performs well with zero-shot instruction.

---

### RT-003: Error Handling and Fallback Strategy

**Context**: Classification failure must never block issue creation (FR-008, SC-003). Need to define what constitutes failure and what each path falls back to.

**Decision**: Wrap the entire classification call in a try/except that catches all exceptions. On failure, return path-specific default labels:
- Pipeline path: `["ai-generated"]` + `pipeline:<name>` (current behavior)
- Task path: `["ai-generated"]` (minimal safe default)
- Agent tool path: `["ai-generated"]` (minimal safe default)

Log the error at WARNING level (not ERROR) since fallback behavior is expected and acceptable.

**Rationale**: The classifier is a best-effort enhancement, not a critical path. Current behavior (hardcoded or no labels) is the baseline that users already accept. Logging at WARNING avoids alert fatigue while preserving observability.

**Alternatives considered**:
- **Retry with exponential backoff**: Adds latency; contradicts the 3-second budget (SC-006). The AI service is either available or not; retrying once is unlikely to help within the time budget.
- **Cache previous classifications**: Adds storage and cache invalidation complexity for minimal benefit since each issue has unique content. Rejected per YAGNI (Constitution Principle V).
- **Circuit breaker pattern**: Premature for initial implementation; can be added later if classification failures become frequent.

---

### RT-004: Label Validation and Deduplication Approach

**Context**: The classifier output must be validated against the taxonomy (FR-002), deduplicated (FR-011), and guaranteed to have "ai-generated" + one type label (FR-003, FR-004).

**Decision**: Post-processing pipeline after AI response parsing:
1. Parse JSON response to extract `labels` array
2. Filter: keep only labels present in `constants.LABELS` (case-insensitive match, lowercase output)
3. Deduplicate while preserving order: iterate over the filtered list, append each label to a new list only if it has not been seen before (track a `seen` set); this keeps the first occurrence of each label and preserves their relative order
4. Ensure "ai-generated" is present and first: if missing, insert at position 0; if present but not at position 0, move it to position 0 while keeping the relative order of all other labels
5. Ensure exactly one type label: determine which labels are type labels according to the taxonomy; if zero type labels, insert the default type label `"feature"` immediately after "ai-generated"; if multiple type labels are present, keep only the first one based on the preserved order from step 3

**Rationale**: Strict validation ensures the classifier can never produce invalid labels regardless of AI output quality. The type label default ("feature") matches the spec edge case requirement. The order-preserving dedup step and explicit reordering rules ensure deterministic, stable output given the same input.

**Alternatives considered**:
- **Pydantic model validation**: Would require a custom validator model just for labels; simpler to validate inline with list operations since the taxonomy is a flat list.
- **Enum-based validation**: `IssueLabel` enum exists in `models/recommendation.py` but represents the same data as `constants.LABELS`; using the constant list directly is more aligned with FR-010 (dynamic reference).

---

### RT-005: Integration Points — Where to Call the Classifier

**Context**: Three paths need integration. Need to determine the minimal changes for each.

**Decision**:

1. **Pipeline launch** (`src/api/pipelines.py`, `execute_pipeline_launch()`, ~line 346):
   - Call classifier with `issue_title` and `issue_description`
   - Merge classified labels with existing pipeline-specific labels (`["ai-generated"] + pipeline:<name>`)
   - On failure, fall back to current hardcoded labels

2. **Task creation** (`src/api/tasks.py`, `create_task()`, ~line 103):
   - Call classifier with `request.title` and `request.description`
   - Pass classified labels to `create_issue()` (currently has no `labels` parameter)
   - On failure, fall back to `["ai-generated"]`

3. **Agent tool** (`src/services/agent_tools.py`, `create_project_issue()`, ~line 449):
   - Add optional `labels: list[str] | None = None` parameter to the tool function
   - If labels provided by agent, use them directly (per spec US-3 scenario 2-3)
   - If no labels provided, call classifier with `title` and `body`
   - On failure, fall back to `["ai-generated"]`

**Rationale**: Minimal changes to existing code; each integration is a ~5-10 line insertion before the existing `create_issue()` call. The recommendation confirmation path is untouched (already works via `_build_labels`).

**Alternatives considered**:
- **Middleware/decorator approach**: Over-engineered for 3 call sites; adds indirection without benefit.
- **Modify `create_issue()` to auto-classify**: Violates separation of concerns; `create_issue()` is a GitHub API wrapper, not a business logic layer.
- **Event-based post-creation labeling**: Adds complexity and race conditions; labels should be set at creation time for consistent project board views.

---

### RT-006: Prompt Input Size Handling

**Context**: Issue descriptions can be up to 65,536 characters (GitHub limit). The classifier prompt needs to handle this without exceeding model context limits.

**Decision**: Truncate the description to 2,000 characters for the classification prompt. The title is always included in full (max 256 characters). This keeps the total prompt well within model context limits while providing enough content for accurate classification.

**Rationale**: Label classification needs the gist of the issue, not every detail. The first 2,000 characters of a description reliably contain the core topic, scope, and intent. Testing with the recommendation path shows labels are primarily derived from the title and first paragraph.

**Alternatives considered**:
- **Full description in prompt**: Risk of exceeding context window; unnecessary token cost for marginal classification improvement.
- **Summarize-then-classify**: Two AI calls doubles latency; violates the 3-second budget.
- **Title-only classification**: Feasible but less accurate for issues with vague titles and detailed descriptions. The 2,000-char truncation is a good middle ground.
