"""Plan approval helpers.

Renders chat-generated plans into the same markdown shape used when a user
copies a plan into Parent Issue Intake before launching the shared pipeline.
"""
# pyright: basic
# reason: Legacy service module; pending follow-up typing pass.

from __future__ import annotations

from collections.abc import Mapping


def _coerce_step_position(value: object) -> int:
    """Convert persisted step positions to a safe integer for markdown labels."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _step_dependency_labels(
    step_lookup: dict[str, Mapping[str, object]],
    dependencies: object,
) -> list[str]:
    if not isinstance(dependencies, list):
        return []

    labels: list[str] = []
    for dep_id in dependencies:
        dep_key = str(dep_id)
        dep_step = step_lookup.get(dep_key)
        if dep_step is None:
            labels.append(dep_key)
            continue

        dep_position = _coerce_step_position(dep_step.get("position", 0)) + 1
        dep_title = str(dep_step.get("title") or dep_key).strip() or dep_key
        labels.append(f"Step {dep_position}: {dep_title}")
    return labels


def format_plan_issue_markdown(plan: Mapping[str, object]) -> str:
    """Render a saved plan into parent-issue markdown for pipeline launch."""
    title = str(plan.get("title") or "Implementation Plan").strip() or "Implementation Plan"
    summary = str(plan.get("summary") or "").strip()
    raw_steps = plan.get("steps")
    steps = raw_steps if isinstance(raw_steps, list) else []
    step_lookup = {
        str(step.get("step_id")): step
        for step in steps
        if isinstance(step, Mapping) and step.get("step_id") is not None
    }

    lines = [f"# {title}", ""]
    if summary:
        lines.extend([summary, ""])

    if steps:
        lines.extend(["## Implementation Steps", ""])

    for index, raw_step in enumerate(steps, start=1):
        if not isinstance(raw_step, Mapping):
            continue

        step_title = str(raw_step.get("title") or f"Step {index}").strip() or f"Step {index}"
        step_description = str(raw_step.get("description") or "").strip()
        dependency_labels = _step_dependency_labels(step_lookup, raw_step.get("dependencies"))

        lines.append(f"### Step {index}: {step_title}")
        lines.append("")
        if step_description:
            lines.extend(step_description.splitlines())
            lines.append("")
        if dependency_labels:
            lines.append("Dependencies:")
            lines.extend(f"- {label}" for label in dependency_labels)
            lines.append("")

    return "\n".join(lines).strip()
