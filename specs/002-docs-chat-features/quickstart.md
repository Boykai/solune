# Quickstart: Update Documentation with New Chat Features

**Feature**: 002-docs-chat-features | **Date**: 2026-03-31

This guide provides step-by-step instructions for implementing the documentation updates. Follow the phases in order — each builds on the previous.

---

## Prerequisites

- Access to the Solune repository (branch `002-docs-chat-features` or child branch)
- Familiarity with Markdown syntax
- Read the [spec.md](spec.md) for full requirements and acceptance criteria
- Read the [contracts/doc-updates.md](contracts/doc-updates.md) for per-file change specifications

## Phase 1: Create the Chat Page Guide

**File**: `docs/pages/chat.md` (NEW)
**Time estimate**: ~30 minutes
**Spec coverage**: FR-001, FR-012, FR-013

1. Create `docs/pages/chat.md`
2. Add the page title (`# Chat`) and introduction paragraph
3. Write each of the 12 sections (see [data-model.md](data-model.md) → Section Outline)
4. For each section, reference the "Content Entities per Section" table in data-model.md for key facts and source files
5. Follow existing conventions:
   - Use `**What you can do:**` bullet format (like `layout.md`)
   - Use markdown tables for constraints (file limits, SSE event types)
   - Use inline code for parameter names, endpoint paths, keyboard shortcuts
6. Do NOT add a "What's Next?" footer (leaf page convention)
7. Verify: All 12 capability sections present with accurate technical details

## Phase 2: Update API Reference

**File**: `docs/api-reference.md` (UPDATE)
**Time estimate**: ~15 minutes
**Spec coverage**: FR-002, FR-003, FR-004

1. In the Chat section, update the `POST /chat/messages` (non-streaming) row description to mention synchronous responses, `ai_enhance`, `file_urls`, and `pipeline_id`, and to note that streaming responses use a separate `POST /chat/messages/stream` SSE endpoint
2. Add or update the `POST /chat/messages/stream` row to document the SSE streaming endpoint, and cross-reference the `### Streaming` subsection for event types and behavior
3. Update the `GET /chat/messages` row to note pagination (`limit`, `offset`)
4. Add a `### Streaming` subsection after the endpoint table describing `POST /chat/messages/stream`:
   - SSE event types table: `token`, `tool_call`, `tool_result`, `done`, `error`
   - Note: `POST /chat/messages/stream` requires `ai_enhance=true` for model-generated content and streams partial results over SSE
   - Note: rate limiting applies (10 streaming requests per minute)
5. Add a `### File Upload Constraints` subsection:
   - Size: 10 MB per file
   - Count: 5 files per message
   - Types: allowed and blocked lists
   - Transcript: .vtt/.srt auto-detection
6. Verify: New content follows existing table and subsection format

## Phase 3: Update Architecture Documentation

**File**: `docs/architecture.md` (UPDATE)
**Time estimate**: ~15 minutes
**Spec coverage**: FR-005, FR-006, FR-007

1. Add a `### ChatAgentService` subsection after "AI Completion Providers":
   - Description: Microsoft Agent Framework wrapper for chat
   - Session management: `AgentSessionMapping` with TTL eviction (3600s default), max 100 concurrent sessions, LRU eviction
   - Tool registration: MCP tool loading from project configuration
   - Dual dispatch: `ai_enhance=true` → Agent Framework, `false` → metadata-only fallback
   - Streaming: `run_stream()` method with SSE event types
2. Update the `components/chat/` row in Key Frontend Modules table:
   - Append: `MentionInput`, `MentionAutocomplete`, `FilePreviewChips`, `MarkdownRenderer`, `ChatMessageSkeleton`, `PipelineWarningBanner`, `PipelineIndicator`
3. Update the `hooks/` row:
   - Append: `useChatProposals`, `useFileUpload`, `useMentionAutocomplete`
4. Verify: New subsection follows existing pattern, tables are well-formatted

## Phase 4: Update Project Structure

**File**: `docs/project-structure.md` (UPDATE)
**Time estimate**: ~10 minutes
**Spec coverage**: FR-008

1. In the backend `services/` tree, add:
   - `chat_agent.py` — ChatAgentService (Microsoft Agent Framework wrapper)
   - `agent_provider.py` — Agent provider factory
   - `agent_tools.py` — Agent tool definitions
2. In the frontend `components/chat/` tree, add the 7 missing components inline
3. In the frontend `hooks/` tree, add the 3 missing hooks
4. Follow existing tree notation: `├──`, `│   ├──`, inline `#` comments
5. Verify: New entries match indentation and comment style of existing entries

## Phase 5: Update Roadmap

**File**: `docs/roadmap.md` (UPDATE)
**Time estimate**: ~10 minutes
**Spec coverage**: FR-009

1. In the v0.2.0 section, add ✅ markers to each feature bullet
2. Update the Architecture Evolution diagram:
   - Change `v0.1.0 (today)` to `v0.2.0 (current)`
   - Update the left side to show the Agent Framework (reflecting current state)
3. Update the Timeline table to show v0.2.0 as shipped
4. Verify: Only v0.2.0 section modified, other versions untouched

## Phase 6: Add Cross-References

**Files**: `docs/pages/layout.md`, `docs/pages/README.md` (UPDATE)
**Time estimate**: ~5 minutes
**Spec coverage**: FR-010, FR-011
**Prerequisite**: Phase 1 complete (chat.md exists)

1. In `layout.md` → Chat Panel section, add a link sentence: `For the full chat feature guide, see [Chat](chat.md).`
2. In `README.md` → Page Overview table, add a row for Chat between existing entries
3. Verify: All links resolve (run a link checker or manually test each `[text](path)` reference)

## Verification Checklist

After all phases complete, verify against the spec's success criteria:

- [ ] `docs/pages/chat.md` exists and covers all 12 capabilities (SC-001, SC-002)
- [ ] API reference has streaming endpoint with SSE event types (SC-004)
- [ ] Architecture page has ChatAgentService subsection + updated tables (SC-005)
- [ ] `chat_agent.py` appears in project-structure.md (SC-007)
- [ ] Roadmap v0.2.0 shows implemented status (SC-006)
- [ ] `layout.md` links to `chat.md` (FR-010)
- [ ] `README.md` lists chat page (FR-010)
- [ ] All internal links resolve — zero broken links (SC-003)
- [ ] No code, env vars, or config changes introduced (SC-008)
- [ ] Documentation follows existing conventions (SC-002)
