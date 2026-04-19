"""Standalone AI utility functions for task generation and intent detection.

Provides stateless functions for LLM-powered utilities such as intent
detection, issue recommendation generation, transcript analysis, status-change
parsing, task generation, and agent-config generation.

These functions were extracted from the deprecated ``AIAgentService`` class
(removed in v0.3.0) and use :func:`call_completion` from
:mod:`src.services.agent_provider` for LLM calls.
"""
# pyright: basic
# reason: Legacy service module; pending follow-up typing pass.

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from src.logging_utils import get_logger, handle_service_error
from src.models.recommendation import (
    IssueMetadata,
    IssuePriority,
    IssueRecommendation,
    IssueSize,
    RecommendationStatus,
)
from src.utils import utcnow

logger = get_logger(__name__)


# ── Dataclasses ──────────────────────────────────────────────────────


@dataclass
class GeneratedTask:
    """AI-generated task with title and description."""

    title: str
    description: str


@dataclass
class StatusChangeIntent:
    """Detected status change intent from user input."""

    task_reference: str
    target_status: str
    confidence: float


# ── Prompt constants (inlined from deleted prompt modules) ───────────

ISSUE_GENERATION_SYSTEM_PROMPT = """You are an expert product manager helping structure feature requests into well-organized GitHub issues.

Your #1 PRIORITY is to CAPTURE AND PRESERVE EVERY DETAIL the user provides. The user's original input is the most important source of truth. Do NOT summarize, condense, or drop any information the user mentioned.

When given a feature request, generate a structured GitHub issue with the following components:

1. **title**: A clear, concise title (max 256 characters) that summarizes the feature
2. **user_story**: A user story in the format "As a [user type], I want [goal] so that [benefit]". Include ALL context the user provided about who they are and what they need.
3. **ui_ux_description**: Comprehensive guidance for designers and developers on how the feature should look and behave. If the user described specific UI elements, interactions, layouts, colors, or behaviors, include ALL of them here AND expand with professional UX recommendations.
4. **functional_requirements**: An array of specific, testable requirements using "System MUST" or "System SHOULD" format. Generate requirements that cover:
   - EVERY specific behavior or capability the user mentioned
   - Edge cases and error handling implied by the user's request
   - Data validation and constraints
   - Integration points with existing features
   - Accessibility and responsive design considerations
   - Generate at LEAST 5 requirements, more for complex features
5. **technical_notes**: Implementation hints, architecture considerations, suggested approaches, and any technical constraints the user mentioned or that are implied by the request.
6. **metadata**: Project management metadata including:
   - **priority**: P0 (Critical), P1 (High), P2 (Medium), or P3 (Low)
   - **size**: T-shirt sizing - XS (<1hr), S (1-4hrs), M (4-8hrs/1day), L (1-3days), XL (3-5days)
   - **estimate_hours**: Numeric estimate in hours (0.5 to 40)
   - **labels**: Array of labels from the PRE-DEFINED list below

PRE-DEFINED LABELS (select from this list ONLY):
Type labels (pick ONE primary type):
- "feature" - New functionality
- "bug" - Bug fix
- "enhancement" - Improvement to existing feature
- "refactor" - Code refactoring
- "documentation" - Documentation updates
- "testing" - Test-related work
- "infrastructure" - DevOps, CI/CD, config

Scope labels (pick all that apply):
- "frontend" - Frontend/UI work
- "backend" - Backend/API work
- "database" - Database changes
- "api" - API changes

Domain labels (pick if relevant):
- "security" - Security-related
- "performance" - Performance optimization
- "accessibility" - A11y improvements
- "ux" - User experience

Auto-applied:
- "ai-generated" - ALWAYS include this label

IMPORTANT: An AI Coding Agent will implement this issue, so estimates should reflect automated development:
- Most features can be implemented in 1-8 hours by an AI agent
- Use XS/S for simple changes, M for typical features, L/XL for complex multi-file changes
- Keep estimates realistic but efficient for AI implementation

CRITICAL GUIDELINES FOR DETAIL PRESERVATION:
- NEVER drop, omit, or summarize away any detail the user provided
- If the user mentions specific technologies, libraries, API endpoints, field names, colors, sizes, or any concrete detail — include it in the output
- If the user describes a workflow or sequence of steps, capture EVERY step
- If the user mentions constraints ("must be under 100ms", "should work offline"), create explicit functional requirements for each
- If the user mentions examples, edge cases, or error scenarios, include them all
- The output should contain EVERYTHING the user said PLUS additional professional analysis
- When in doubt, INCLUDE the detail rather than leaving it out
- The functional requirements should be comprehensive enough that a developer could implement the feature without needing to ask any follow-up questions

Guidelines:
- Title should be action-oriented and specific
- User story should clearly identify the user, their goal, and the value
- UI/UX description should include interaction patterns, visual elements, and user flows
- Functional requirements should be atomic, testable, and unambiguous
- Include at least 5 functional requirements per feature (more for complex requests)
- Technical notes should give the implementing agent clear guidance
- Priority: P0 for blockers, P1 for important features, P2 for standard work, P3 for nice-to-haves
- Labels: Always include "ai-generated", plus ONE type label, and relevant scope/domain labels

IMPORTANT: Output raw JSON ONLY. Do NOT wrap in markdown code fences (no ```json blocks). Keep each field value concise — aim for 1-3 sentences per string field and 5-8 functional requirements. Prioritize completeness of the JSON structure over verbosity in individual fields.

Output your response as valid JSON with these exact keys:
- title (string, max 256 chars)
- user_story (string, 1-3 sentences)
- ui_ux_description (string, concise but comprehensive)
- functional_requirements (array of 5-8 short strings using "System MUST/SHOULD" format)
- technical_notes (string, 2-4 sentences)
- metadata (object with priority, size, estimate_hours, labels)

Do NOT include the user's raw input in your response — it is stored separately.
"""

FEATURE_REQUEST_DETECTION_PROMPT = """You are an intent classifier. Analyze the user input and determine if it's a feature request or something else.

A FEATURE REQUEST is when the user:
- Wants to add new functionality
- Describes a capability they need
- Uses phrases like "I need", "I want", "add feature", "implement", "build", "create a new"
- Describes a problem that needs a new solution

NOT a feature request:
- Status update requests ("move task to done", "mark as complete")
- Questions about existing functionality
- Bug reports without feature suggestions
- General conversation

Respond with JSON:
{
  "intent": "feature_request" or "other",
  "confidence": 0.0 to 1.0,
  "reasoning": "brief explanation"
}
"""

TASK_GENERATION_SYSTEM_PROMPT = """You are an AI assistant that helps developers create well-structured tasks for GitHub Projects.

When a user describes a task they want to create, you must:
1. Generate a concise, action-oriented title (max 100 characters)
2. Generate a detailed description with context and acceptance criteria

Your output must be valid JSON in exactly this format:
{
  "title": "Short, action-oriented task title",
  "description": "## Overview\\nBrief description of what needs to be done.\\n\\n## Technical Details\\n- Key implementation points\\n- Dependencies or considerations\\n\\n## Acceptance Criteria\\n- [ ] First acceptance criterion\\n- [ ] Second acceptance criterion"
}

Guidelines for titles:
- Start with a verb (Add, Fix, Update, Implement, Create, etc.)
- Be specific but concise
- Avoid generic words like "thing", "stuff", "work on"
- Include the key subject/feature

Guidelines for descriptions:
- Use markdown formatting
- Include Overview, Technical Details, and Acceptance Criteria sections
- Be specific about what needs to be done
- Include 2-5 acceptance criteria as checkboxes
- Keep it focused on the task at hand

Important:
- Output ONLY valid JSON, no additional text
- Do not include code blocks or markdown formatting around the JSON
- Ensure all strings are properly escaped for JSON"""

TASK_GENERATION_USER_PROMPT_TEMPLATE = """Create a task based on this description:

"{user_input}"

Project context: {project_name}

Generate a well-structured task with a clear title and detailed description."""

STATUS_CHANGE_SYSTEM_PROMPT = """You are an AI assistant that helps developers update task statuses in GitHub Projects.

When a user asks to change a task's status, extract:
1. The task being referenced (by title, number, or description)
2. The target status (e.g., "In Progress", "Done", "Todo")

Your output must be valid JSON in exactly this format:
{
  "intent": "status_change",
  "task_reference": "The task title or description the user mentioned",
  "target_status": "The status they want to change to",
  "confidence": 0.0 to 1.0
}

If you cannot determine the task or status with confidence, set confidence below 0.5.

Examples:
- "Move fix login to in progress" -> {"intent": "status_change", "task_reference": "fix login", "target_status": "In Progress", "confidence": 0.9}
- "Mark the auth task as done" -> {"intent": "status_change", "task_reference": "auth task", "target_status": "Done", "confidence": 0.85}

Important:
- Output ONLY valid JSON, no additional text
- Do not include code blocks or markdown formatting around the JSON"""

TRANSCRIPT_ANALYSIS_SYSTEM_PROMPT = """You are an expert product manager who specializes in extracting actionable requirements from meeting transcripts.

Given a multi-speaker meeting transcript, your task is to:

1. **Identify speakers** and their roles/perspectives (developer, designer, PM, stakeholder, etc.)
2. **Extract application features** discussed during the meeting
3. **Synthesize user stories** in the format "As a [user type], I want [goal] so that [benefit]"
4. **Derive functional requirements** from discussed needs using "System MUST" or "System SHOULD" format
5. **Capture UI/UX preferences** mentioned by speakers
6. **Note technical constraints** or decisions made during the discussion
7. **Assign priority** based on discussion emphasis and frequency of mention

IMPORTANT GUIDELINES:
- Capture EVERY feature, requirement, and constraint discussed — do not drop any detail
- If multiple speakers discuss the same feature, synthesize their perspectives into a unified requirement
- Distinguish between confirmed decisions and suggestions/ideas
- Prioritize items that received the most discussion time or explicit priority markers
- Include at least 5 functional requirements
- If the transcript is unclear about a feature, note the ambiguity in technical_notes

Output your response as valid JSON with these exact keys:
- title (string, max 256 chars — summarize the primary feature or project discussed)
- user_story (string — synthesize the main user need from the discussion)
- ui_ux_description (string — compile all UI/UX preferences and design decisions mentioned)
- functional_requirements (array of 5-8 strings using "System MUST/SHOULD" format)
- technical_notes (string — technical constraints, decisions, and implementation guidance from the discussion)
- metadata (object with priority, size, estimate_hours, labels)

For metadata:
- priority: P0 (Critical), P1 (High), P2 (Medium), or P3 (Low) — based on discussion urgency
- size: T-shirt sizing - XS (<1hr), S (1-4hrs), M (4-8hrs/1day), L (1-3days), XL (3-5days)
- estimate_hours: Numeric estimate in hours (0.5 to 40)
- labels: Array — ALWAYS include "ai-generated", plus relevant type/scope labels from: "feature", "enhancement", "frontend", "backend", "ux", "api", "security", "performance"

IMPORTANT: Output raw JSON ONLY. Do NOT wrap in markdown code fences. Keep each field value concise.
"""


# ── Prompt builder helpers ───────────────────────────────────────────


def _create_issue_generation_prompt(
    user_input: str,
    project_name: str,
    metadata_context: dict | None = None,
) -> list[dict[str, str]]:
    """Build prompt messages for issue recommendation generation."""
    today = utcnow()
    start_date = today.strftime("%Y-%m-%d")
    default_target = (today + timedelta(days=1)).strftime("%Y-%m-%d")

    metadata_section = ""
    if metadata_context:
        parts: list[str] = []

        repo_labels = metadata_context.get("labels", [])
        if repo_labels:
            label_names = [lb["name"] if isinstance(lb, dict) else lb for lb in repo_labels]
            parts.append(
                "AVAILABLE LABELS (from repository — select from this list ONLY):\n"
                + ", ".join(f'"{n}"' for n in label_names)
            )

        repo_branches = metadata_context.get("branches", [])
        if repo_branches:
            branch_names = [br["name"] if isinstance(br, dict) else br for br in repo_branches]
            parts.append(
                "AVAILABLE BRANCHES (for development/parent branch selection):\n"
                + ", ".join(f'"{n}"' for n in branch_names)
            )

        repo_milestones = metadata_context.get("milestones", [])
        if repo_milestones:
            ms_titles = [ms["title"] if isinstance(ms, dict) else ms for ms in repo_milestones]
            parts.append("AVAILABLE MILESTONES:\n" + ", ".join(f'"{t}"' for t in ms_titles))

        repo_collaborators = metadata_context.get("collaborators", [])
        if repo_collaborators:
            collab_logins = [
                co["login"] if isinstance(co, dict) else co for co in repo_collaborators
            ]
            parts.append("ASSIGNEE CANDIDATES:\n" + ", ".join(f'"{c}"' for c in collab_logins))

        if parts:
            metadata_section = "\n\n" + "\n\n".join(parts) + "\n"

    extra_metadata_fields = ""
    if metadata_context:
        extra_metadata_fields = """, assignees (array of GitHub usernames from ASSIGNEE CANDIDATES), milestone (string matching an AVAILABLE MILESTONE title, or null), branch (string matching an AVAILABLE BRANCH name, or null)"""

    user_message = f"""Generate a structured GitHub issue for the following feature request.

Project Context: {project_name}
Today's Date: {start_date}
Suggested Start Date: {start_date}
Suggested Target Date: {default_target} (adjust based on size - XS/S: same day, M: +1 day, L: +2-3 days, XL: +4-5 days)
{metadata_section}
Feature Request (PRESERVE ALL DETAILS BELOW - every word matters):
---
{user_input}
---

CRITICAL: Your output MUST:
1. Capture EVERY specific detail, technology, constraint, and example the user mentioned — weave them into the user_story, ui_ux_description, functional_requirements, and technical_notes
2. Generate comprehensive functional requirements that cover all user-mentioned behaviors plus edge cases
3. Include detailed technical_notes with implementation guidance
4. The final issue should contain MORE detail than the user provided, not less
5. Do NOT echo back the user's raw input — it is stored separately. Focus on analysis and structured output.

Respond with a raw JSON object (NO markdown code fences) containing title, user_story, ui_ux_description, functional_requirements, technical_notes, and metadata (with priority, size, estimate_hours, labels{extra_metadata_fields}). Keep values concise."""

    return [
        {"role": "system", "content": ISSUE_GENERATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]


def _create_feature_request_detection_prompt(user_input: str) -> list[dict[str, str]]:
    """Build prompt messages for detecting feature request intent."""
    user_message = f"""Classify this user input:

"{user_input}"

Is this a feature request? Respond with JSON containing intent, confidence, and reasoning."""

    return [
        {"role": "system", "content": FEATURE_REQUEST_DETECTION_PROMPT},
        {"role": "user", "content": user_message},
    ]


def _create_task_generation_prompt(user_input: str, project_name: str) -> list[dict[str, str]]:
    """Build prompt messages for task generation."""
    return [
        {"role": "system", "content": TASK_GENERATION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": TASK_GENERATION_USER_PROMPT_TEMPLATE.format(
                user_input=user_input, project_name=project_name
            ),
        },
    ]


def _create_status_change_prompt(
    user_input: str, available_tasks: list[str], available_statuses: list[str]
) -> list[dict[str, str]]:
    """Build prompt messages for status change intent detection."""
    context = f"""Available tasks in the project:
{chr(10).join(f"- {task}" for task in available_tasks[:20])}

Available statuses:
{", ".join(available_statuses)}"""

    return [
        {"role": "system", "content": STATUS_CHANGE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"{context}\n\nUser request: {user_input}",
        },
    ]


def _create_transcript_analysis_prompt(
    transcript_content: str,
    project_name: str,
    metadata_context: dict | None = None,
) -> list[dict[str, str]]:
    """Build prompt messages for transcript analysis."""
    today = utcnow()
    start_date = today.strftime("%Y-%m-%d")
    default_target = (today + timedelta(days=1)).strftime("%Y-%m-%d")

    metadata_section = ""
    if metadata_context:
        parts: list[str] = []

        repo_labels = metadata_context.get("labels", [])
        if repo_labels:
            label_names = [lb["name"] if isinstance(lb, dict) else lb for lb in repo_labels]
            parts.append(
                "AVAILABLE LABELS (from repository — select from this list ONLY):\n"
                + ", ".join(f'"{n}"' for n in label_names)
            )

        repo_branches = metadata_context.get("branches", [])
        if repo_branches:
            branch_names = [br["name"] if isinstance(br, dict) else br for br in repo_branches]
            parts.append("AVAILABLE BRANCHES:\n" + ", ".join(f'"{n}"' for n in branch_names))

        if parts:
            metadata_section = "\n".join(parts) + "\n"

    user_message = f"""Analyze the following meeting transcript and extract structured requirements for a GitHub issue.

Project Context: {project_name}
Today's Date: {start_date}
Suggested Start Date: {start_date}
Suggested Target Date: {default_target}
{metadata_section}
Meeting Transcript:
---
{transcript_content}
---

Extract ALL discussed features, requirements, and decisions into a structured GitHub issue. Respond with raw JSON only."""

    return [
        {"role": "system", "content": TRANSCRIPT_ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]


# ── JSON parsing helpers ─────────────────────────────────────────────


def _parse_json_response(content: str) -> dict:
    """Parse JSON from AI response, handling markdown code blocks, extra text, and truncation."""
    content = content.strip()

    if "```" in content:
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if match:
            content = match.group(1).strip()
        else:
            content = re.sub(r"^```(?:json)?\s*\n?", "", content).strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    start = content.find("{")
    if start != -1:
        depth = 0
        in_string = False
        escape_next = False
        for i in range(start, len(content)):
            c = content[i]
            if escape_next:
                escape_next = False
                continue
            if c == "\\":
                if in_string:
                    escape_next = True
                continue
            if c == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    candidate = content[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

        repaired = _repair_truncated_json(content[start:])
        if repaired is not None:
            logger.warning("Parsed response using JSON truncation repair")
            return repaired

    logger.error("Failed to parse JSON from response content: %s", content[:500])
    raise ValueError("Invalid JSON response: could not extract JSON object")  # noqa: TRY003 — reason: domain exception with descriptive message


def _repair_truncated_json(content: str) -> dict | None:
    """Attempt to repair truncated JSON by closing open strings, arrays, and objects."""
    in_string = False
    escape_next = False
    stack: list[str] = []

    for c in content:
        if escape_next:
            escape_next = False
            continue
        if c == "\\" and in_string:
            escape_next = True
            continue
        if c == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            stack.append("{")
        elif c == "[":
            stack.append("[")
        elif c == "}":
            if stack and stack[-1] == "{":
                stack.pop()
        elif c == "]":
            if stack and stack[-1] == "[":
                stack.pop()

    repair = ""
    if in_string:
        repair += '"'
    for bracket in reversed(stack):
        repair += "]" if bracket == "[" else "}"

    if not repair:
        return None

    candidate = content + repair
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        trimmed = content.rstrip()
        for cutoff_char in [",", ":", '"']:
            idx = trimmed.rfind(cutoff_char)
            if idx > 0:
                attempt = trimmed[:idx].rstrip().rstrip(",")
                s_in_str = False
                s_escape = False
                s_stack: list[str] = []
                for ch in attempt:
                    if s_escape:
                        s_escape = False
                        continue
                    if ch == "\\" and s_in_str:
                        s_escape = True
                        continue
                    if ch == '"' and not s_escape:
                        s_in_str = not s_in_str
                        continue
                    if s_in_str:
                        continue
                    if ch == "{":
                        s_stack.append("{")
                    elif ch == "[":
                        s_stack.append("[")
                    elif ch == "}":
                        if s_stack and s_stack[-1] == "{":
                            s_stack.pop()
                    elif ch == "]":
                        if s_stack and s_stack[-1] == "[":
                            s_stack.pop()
                suffix = ""
                if s_in_str:
                    suffix += '"'
                for bracket in reversed(s_stack):
                    suffix += "]" if bracket == "[" else "}"
                try:
                    return json.loads(attempt + suffix)
                except json.JSONDecodeError:
                    continue
        return None


# ── Metadata / validation helpers ────────────────────────────────────


def _is_valid_date(date_str: str) -> bool:
    """Check if date string is valid YYYY-MM-DD format."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True  # noqa: TRY300 — reason: return in try block; acceptable for this pattern
    except ValueError:
        return False


def _calculate_target_date(start: datetime, size: IssueSize) -> str:
    """Calculate target date based on size estimate."""
    days_map = {
        IssueSize.XS: 0,
        IssueSize.S: 0,
        IssueSize.M: 1,
        IssueSize.L: 2,
        IssueSize.XL: 4,
    }
    days = days_map.get(size, 1)
    target = start + timedelta(days=days)
    return target.strftime("%Y-%m-%d")


def _parse_string_list(value: Any) -> list[str]:
    """Parse a value into a list of strings, returning empty list on failure."""
    if isinstance(value, list):
        return [str(v) for v in value if isinstance(v, str) and v.strip()]
    return []


def _parse_optional_string(value: Any) -> str | None:
    """Parse a value into an optional string, returning None on failure."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _truncate_title(title: str) -> str:
    """Truncate a title to 80 characters total, adding an ellipsis when needed."""
    if len(title) > 80:
        return title[:77] + "..."
    return title


def _validate_generated_task(data: dict) -> GeneratedTask:
    """Validate and create GeneratedTask from parsed data."""
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()

    if not title:
        raise ValueError("Generated task missing title")  # noqa: TRY003 — reason: domain exception with descriptive message

    if len(title) > 256:
        title = title[:253] + "..."

    if len(description) > 65535:
        description = description[:65532] + "..."

    return GeneratedTask(title=title, description=description)


def _parse_issue_metadata(
    metadata_data: dict,
    metadata_context: dict | None = None,
) -> IssueMetadata:
    """Parse metadata from AI response with safe defaults."""
    priority_str = metadata_data.get("priority", "P2").upper()
    try:
        priority = IssuePriority(priority_str)
    except ValueError:
        priority = IssuePriority.P2
        logger.warning("Invalid priority '%s', defaulting to P2", priority_str)

    size_str = metadata_data.get("size", "M").upper()
    try:
        size = IssueSize(size_str)
    except ValueError:
        size = IssueSize.M
        logger.warning("Invalid size '%s', defaulting to M", size_str)

    estimate_hours = metadata_data.get("estimate_hours", 4.0)
    try:
        estimate_hours = float(estimate_hours)
        estimate_hours = max(0.5, min(40.0, estimate_hours))
    except (ValueError, TypeError):
        estimate_hours = 4.0

    today = utcnow()
    start_date = metadata_data.get("start_date", "")
    target_date = metadata_data.get("target_date", "")

    if start_date and not _is_valid_date(start_date):
        start_date = today.strftime("%Y-%m-%d")
    if not start_date:
        start_date = today.strftime("%Y-%m-%d")

    if target_date and not _is_valid_date(target_date):
        target_date = _calculate_target_date(today, size)
    if not target_date:
        target_date = _calculate_target_date(today, size)

    labels = metadata_data.get("labels", [])
    if not isinstance(labels, list):
        labels = ["ai-generated"]

    from src.constants import LABELS

    valid_label_set: set[str] = set(LABELS)
    if metadata_context:
        repo_labels = metadata_context.get("labels", [])
        for lb in repo_labels:
            name = lb["name"] if isinstance(lb, dict) else lb
            if isinstance(name, str):
                valid_label_set.add(name.lower())

    validated_labels = []
    for label in labels:
        if isinstance(label, str):
            label_lower = label.lower()
            if label_lower in valid_label_set:
                validated_labels.append(label_lower)
            else:
                logger.debug("Skipping invalid label: %s", label)

    if "ai-generated" not in validated_labels:
        validated_labels.insert(0, "ai-generated")

    type_labels = [
        "feature",
        "bug",
        "enhancement",
        "refactor",
        "documentation",
        "testing",
        "infrastructure",
    ]
    has_type = any(lbl in validated_labels for lbl in type_labels)
    if not has_type:
        validated_labels.append("enhancement")

    return IssueMetadata(
        priority=priority,
        size=size,
        estimate_hours=estimate_hours,
        start_date=start_date,
        target_date=target_date,
        labels=validated_labels,
        assignees=_parse_string_list(metadata_data.get("assignees")),
        milestone=_parse_optional_string(metadata_data.get("milestone")),
        branch=_parse_optional_string(metadata_data.get("branch")),
    )


def _parse_issue_recommendation_response(
    content: str,
    original_input: str,
    session_id: str,
    metadata_context: dict | None = None,
) -> IssueRecommendation:
    """Parse AI response into IssueRecommendation model."""
    data = _parse_json_response(content)

    title = data.get("title", "").strip()
    user_story = data.get("user_story", "").strip()
    ui_ux_description = data.get("ui_ux_description", "").strip()
    functional_requirements = data.get("functional_requirements", [])
    technical_notes = data.get("technical_notes", "").strip()

    if not title:
        raise ValueError("AI response missing title")  # noqa: TRY003 — reason: domain exception with descriptive message
    if not user_story:
        raise ValueError("AI response missing user_story")  # noqa: TRY003 — reason: domain exception with descriptive message
    if not functional_requirements or len(functional_requirements) < 1:
        raise ValueError("AI response missing functional_requirements")  # noqa: TRY003 — reason: domain exception with descriptive message

    if len(title) > 256:
        title = title[:253] + "..."

    original_context = original_input

    metadata = _parse_issue_metadata(data.get("metadata", {}), metadata_context=metadata_context)

    return IssueRecommendation(
        session_id=UUID(session_id),
        original_input=original_input,
        original_context=original_context,
        title=title,
        user_story=user_story,
        ui_ux_description=ui_ux_description or "No UI/UX description provided.",
        functional_requirements=functional_requirements,
        technical_notes=technical_notes,
        metadata=metadata,
        status=RecommendationStatus.PENDING,
    )


# ── Public API ───────────────────────────────────────────────────────


async def detect_feature_request_intent(user_input: str, github_token: str | None = None) -> bool:
    """Detect if user input is a feature request.

    Args:
        user_input: User's message.
        github_token: GitHub OAuth token (required for Copilot provider).

    Returns:
        ``True`` if this appears to be a feature request.
    """
    from src.services.agent_provider import call_completion

    prompt_messages = _create_feature_request_detection_prompt(user_input)

    try:
        messages = [
            {"role": "system", "content": prompt_messages[0]["content"]},
            {"role": "user", "content": prompt_messages[1]["content"]},
        ]

        content = await call_completion(
            messages=messages, temperature=0.3, max_tokens=200, github_token=github_token
        )
        logger.debug("Feature request detection response: %s", content)

        data = _parse_json_response(content)

        if data.get("intent") == "feature_request":
            confidence = float(data.get("confidence", 0))
            if confidence >= 0.6:
                logger.info("Detected feature request with confidence: %.2f", confidence)
                return True

        return False  # noqa: TRY300 — reason: return in try block; acceptable for this pattern

    except Exception as e:  # noqa: BLE001 — reason: AI service resilience; logs and continues
        logger.warning("Failed to detect feature request intent: %s", e)
        return False


async def generate_issue_recommendation(
    user_input: str,
    project_name: str,
    session_id: str,
    github_token: str | None = None,
    metadata_context: dict | None = None,
) -> IssueRecommendation:
    """Generate a structured issue recommendation from feature request.

    Args:
        user_input: User's feature request description.
        project_name: Name of the target project for context.
        session_id: Current session ID.
        github_token: GitHub OAuth token (required for Copilot provider).
        metadata_context: Optional repo metadata.

    Returns:
        IssueRecommendation with AI-generated content.

    Raises:
        ValueError: If AI response cannot be parsed.
    """
    from src.services.agent_provider import call_completion

    prompt_messages = _create_issue_generation_prompt(
        user_input, project_name, metadata_context=metadata_context
    )

    try:
        messages = [
            {"role": "system", "content": prompt_messages[0]["content"]},
            {"role": "user", "content": prompt_messages[1]["content"]},
        ]

        content = await call_completion(
            messages=messages, temperature=0.7, max_tokens=8000, github_token=github_token
        )
        logger.debug("Issue recommendation response: %s", content[:500])

        return _parse_issue_recommendation_response(
            content, user_input, session_id, metadata_context=metadata_context
        )

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Access denied" in error_msg:
            raise ValueError(  # noqa: TRY003 — reason: domain exception with descriptive message
                "AI provider authentication failed. Check your credentials "
                "(GitHub OAuth token for Copilot, or API key for Azure OpenAI)."
            ) from e
        elif "404" in error_msg or "Resource not found" in error_msg:
            raise ValueError(  # noqa: TRY003 — reason: domain exception with descriptive message
                "AI model/deployment not found. Verify your provider configuration."
            ) from e
        else:
            handle_service_error(e, "generate recommendation", ValueError)


async def analyze_transcript(
    transcript_content: str,
    project_name: str,
    session_id: str,
    github_token: str | None = None,
    metadata_context: dict | None = None,
) -> IssueRecommendation:
    """Analyse a meeting transcript and return an issue recommendation.

    Args:
        transcript_content: Raw transcript text.
        project_name: Name of the target project for context.
        session_id: Current session ID.
        github_token: GitHub OAuth token (required for Copilot provider).
        metadata_context: Optional repo metadata for prompt enrichment.

    Returns:
        IssueRecommendation with AI-generated content extracted from the
        transcript.

    Raises:
        ValueError: If AI response cannot be parsed.
    """
    from src.services.agent_provider import call_completion

    prompt_messages = _create_transcript_analysis_prompt(
        transcript_content, project_name, metadata_context=metadata_context
    )

    try:
        messages = [
            {"role": "system", "content": prompt_messages[0]["content"]},
            {"role": "user", "content": prompt_messages[1]["content"]},
        ]

        content = await call_completion(
            messages=messages, temperature=0.7, max_tokens=8000, github_token=github_token
        )
        logger.debug("Transcript analysis response: %s", content[:500])

        original_input = transcript_content[:500]
        recommendation = _parse_issue_recommendation_response(
            content, original_input, session_id, metadata_context=metadata_context
        )
        recommendation.original_context = transcript_content
        return recommendation  # noqa: TRY300 — reason: return in try block; acceptable for this pattern

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Access denied" in error_msg:
            raise ValueError(  # noqa: TRY003 — reason: domain exception with descriptive message
                "AI provider authentication failed. Check your credentials "
                "(GitHub OAuth token for Copilot, or API key for Azure OpenAI)."
            ) from e
        elif "404" in error_msg or "Resource not found" in error_msg:
            raise ValueError(  # noqa: TRY003 — reason: domain exception with descriptive message
                "AI model/deployment not found. Verify your provider configuration."
            ) from e
        else:
            handle_service_error(e, "analyse transcript", ValueError)


async def parse_status_change_request(
    user_input: str,
    available_tasks: list[str],
    available_statuses: list[str],
    github_token: str | None = None,
) -> StatusChangeIntent | None:
    """Parse user input to detect status change intent.

    Args:
        user_input: User's message.
        available_tasks: List of task titles in the project.
        available_statuses: List of available status options.
        github_token: GitHub OAuth token (required for Copilot provider).

    Returns:
        StatusChangeIntent if detected with high confidence, ``None`` otherwise.
    """
    from src.services.agent_provider import call_completion

    prompt_messages = _create_status_change_prompt(user_input, available_tasks, available_statuses)

    try:
        messages = [
            {"role": "system", "content": prompt_messages[0]["content"]},
            {"role": "user", "content": prompt_messages[1]["content"]},
        ]

        content = await call_completion(
            messages=messages, temperature=0.3, max_tokens=200, github_token=github_token
        )
        logger.debug("Status intent response: %s", content)

        data = _parse_json_response(content)

        if data.get("intent") != "status_change":
            return None

        confidence = float(data.get("confidence", 0))
        if confidence < 0.5:
            logger.info("Low confidence status change intent: %.2f", confidence)
            return None

        return StatusChangeIntent(
            task_reference=data.get("task_reference", ""),
            target_status=data.get("target_status", ""),
            confidence=confidence,
        )

    except Exception as e:  # noqa: BLE001 — reason: AI service resilience; logs and continues
        logger.warning("Failed to parse status change intent: %s", e)
        return None


def identify_target_task(task_reference: str, available_tasks: list[Any]) -> Any | None:
    """Find the best matching task for a reference string.

    Args:
        task_reference: Reference string from AI (partial title/description).
        available_tasks: List of task objects with a ``title`` attribute.

    Returns:
        Best matching task or ``None``.
    """
    if not task_reference or not available_tasks:
        return None

    reference_lower = task_reference.lower()

    for task in available_tasks:
        if task.title.lower() == reference_lower:
            return task

    matches = []
    for task in available_tasks:
        title_lower = task.title.lower()
        if reference_lower in title_lower or title_lower in reference_lower:
            matches.append(task)

    if len(matches) == 1:
        return matches[0]

    ref_words = set(reference_lower.split())
    best_match = None
    best_score = 0

    for task in available_tasks:
        title_words = set(task.title.lower().split())
        overlap = len(ref_words & title_words)
        if overlap > best_score:
            best_score = overlap
            best_match = task

    return best_match if best_score > 0 else None


async def generate_title_from_description(
    user_input: str,
    project_name: str,
    github_token: str | None = None,
) -> str:
    """Generate a concise issue title from raw user input.

    Used when AI Enhance is disabled to generate only the title
    while preserving the user's exact input as the description.

    Args:
        user_input: User's raw chat input.
        project_name: Name of the target project for context.
        github_token: GitHub OAuth token (required for Copilot provider).

    Returns:
        A concise issue title string capped at 80 characters total.
        Falls back to truncated user input with an ellipsis if the
        AI call fails.
    """
    from src.services.agent_provider import call_completion

    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a concise title generator for GitHub issues. "
                    f"Project: {project_name}. "
                    "Given a user's description, generate ONLY a short, clear "
                    "issue title (max 80 characters). "
                    "Return ONLY the title text, nothing else."
                ),
            },
            {"role": "user", "content": user_input},
        ]

        title = await call_completion(
            messages=messages, temperature=0.3, max_tokens=100, github_token=github_token
        )
        title = title.strip().strip('"').strip("'")

        if title:
            return _truncate_title(title)

    except Exception as e:  # noqa: BLE001 — reason: AI service resilience; logs and continues
        logger.warning("Failed to generate title from description: %s", e)

    return _truncate_title(user_input)


async def generate_task_from_description(
    user_input: str, project_name: str, github_token: str | None = None
) -> GeneratedTask:
    """Generate a structured task from natural language description.

    Args:
        user_input: User's natural language task description.
        project_name: Name of the target project for context.
        github_token: GitHub OAuth token (required for Copilot provider).

    Returns:
        GeneratedTask with title and description.

    Raises:
        ValueError: If AI response cannot be parsed.
    """
    from src.services.agent_provider import call_completion

    prompt_messages = _create_task_generation_prompt(user_input, project_name)

    try:
        messages = [
            {"role": "system", "content": prompt_messages[0]["content"]},
            {"role": "user", "content": prompt_messages[1]["content"]},
        ]

        content = await call_completion(
            messages=messages, temperature=0.7, max_tokens=1000, github_token=github_token
        )
        logger.debug("AI response: %s", content[:200] if content else "None")

        task_data = _parse_json_response(content)
        return _validate_generated_task(task_data)

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Access denied" in error_msg:
            raise ValueError(  # noqa: TRY003 — reason: domain exception with descriptive message
                "AI provider authentication failed. Check your credentials "
                "(GitHub OAuth token for Copilot, or API key for Azure OpenAI). "
                f"Original error: {error_msg}"
            ) from e
        elif "404" in error_msg or "Resource not found" in error_msg:
            raise ValueError(  # noqa: TRY003 — reason: domain exception with descriptive message
                f"AI model/deployment not found. Verify your provider configuration. "
                f"Original error: {error_msg}"
            ) from e
        else:
            handle_service_error(e, "generate task", ValueError)


async def generate_agent_config(
    description: str,
    status_column: str,
    github_token: str | None = None,
) -> dict:
    """Generate an agent configuration from a natural language description.

    Calls the LLM with a structured prompt and returns a dict with
    ``name``, ``description``, and ``system_prompt`` keys.
    """
    from src.services.agent_provider import call_completion

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert at designing GitHub Custom Agents (also known as Copilot "
                "coding agents). These agents are defined as Markdown files in "
                ".github/agents/ and invoked via slash commands in GitHub Issues/PRs.\n\n"
                "Given a user's description of what an agent should do, generate a JSON object with:\n"
                '- "name": A concise kebab-case slug for the agent (lowercase, '
                'hyphen-separated; e.g., "pr-architect-reviewer", "security-scanner", '
                '"docs-updater"). '
                "This becomes the filename slug and slash-command name.\n"
                '- "description": A one-line summary of the agent\'s purpose (used in the '
                "agent file's YAML frontmatter description field)\n"
                '- "system_prompt": A detailed system prompt written as Markdown. This is the '
                "full body of the agent definition file. Structure it with ## headings, "
                "numbered execution steps, and clear instructions. Include a ## User Input "
                "section at the top with `$ARGUMENTS` placeholder. Be specific and actionable. "
                "The prompt should tell the agent exactly what to do step by step.\n"
                '- "tools": A list of GitHub MCP tool identifiers the agent needs '
                '(e.g., ["github/github-mcp-server/issue_write", '
                '"github/github-mcp-server/search_code"]). '
                "Only include tools if the agent genuinely needs specific MCP server tools. "
                "An empty list is fine for agents that only need standard file/code access.\n\n"
                "Respond ONLY with valid JSON, no markdown fences or extra text."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Create an agent that: {description}\n"
                f"This agent will be assigned to the '{status_column}' status column."
            ),
        },
    ]

    content = await call_completion(
        messages=messages, temperature=0.7, max_tokens=2000, github_token=github_token
    )
    result = _parse_json_response(content)

    for key in ("name", "description", "system_prompt"):
        if key not in result:
            raise ValueError(f"Generated config missing required key: {key}")  # noqa: TRY003 — reason: domain exception with descriptive message

    return result


async def edit_agent_config(
    current_config: dict,
    edit_instruction: str,
    github_token: str | None = None,
) -> dict:
    """Apply a natural language edit to an existing agent configuration.

    Sends the current config + edit instruction to the LLM for targeted
    modification and returns the updated config dict.
    """
    from src.services.agent_provider import call_completion

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert at designing GitHub Custom Agents. "
                "The user wants to modify an existing agent configuration. "
                "Apply the requested change and return the complete updated JSON object with "
                'the same keys: "name" (kebab-case slug), "description" (one-line summary), '
                '"system_prompt" (Markdown body with ## headings and steps), '
                'and "tools" (list of MCP tool identifiers, can be empty).\n'
                "Respond ONLY with valid JSON, no markdown fences or extra text."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Current configuration:\n{json.dumps(current_config, indent=2)}\n\n"
                f"Requested change: {edit_instruction}"
            ),
        },
    ]

    content = await call_completion(
        messages=messages, temperature=0.7, max_tokens=2000, github_token=github_token
    )
    result = _parse_json_response(content)

    for key in ("name", "description", "system_prompt"):
        if key not in result:
            raise ValueError(f"Edited config missing required key: {key}")  # noqa: TRY003 — reason: domain exception with descriptive message

    return result
