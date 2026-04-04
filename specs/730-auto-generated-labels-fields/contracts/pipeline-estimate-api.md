# API Contract: Pipeline Estimate & Metadata

**Feature**: 730-auto-generated-labels-fields  
**Date**: 2026-04-04  
**Type**: Internal Service API (not HTTP — internal Python module contract)  

## Module: `pipeline_estimate.py`

### Function: `estimate_from_agent_count`

```python
def estimate_from_agent_count(agent_count: int) -> IssueMetadata:
    """Compute pipeline estimate metadata from the number of configured agents.
    
    Args:
        agent_count: Number of agents in the pipeline (≥ 1).
        
    Returns:
        IssueMetadata with priority=P2, size derived from estimate,
        estimate_hours from formula, start_date=today, target_date computed.
        
    Note:
        If agent_count < 1, it is treated as 1 with a warning log.
    """
```

**Input Contract**:
| Parameter | Type | Constraint | Description |
|-----------|------|-----------|-------------|
| agent_count | int | ≥ 1 | Number of configured agents |

**Output Contract** (IssueMetadata fields set):
| Field | Value | Formula |
|-------|-------|---------|
| priority | IssuePriority.P2 | Default |
| size | IssueSize | Threshold from estimate_hours |
| estimate_hours | float | `max(0.5, min(8.0, agent_count * 0.25))` |
| start_date | str | `date.today().isoformat()` (UTC) |
| target_date | str | `(date.today() + timedelta(days=max(1, ceil(estimate_hours / 8)))).isoformat()` |

**Size Thresholds**:
| Estimate Range | Size |
|---------------|------|
| ≤ 0.5 | XS |
| 0.51-1.0 | S |
| 1.01-2.0 | M |
| 2.01-4.0 | L |
| > 4.0 | XL |

---

### Function: `size_from_hours`

```python
def size_from_hours(hours: float) -> IssueSize:
    """Map estimate hours to IssueSize enum value.
    
    Args:
        hours: Estimated hours (0.5-8.0).
        
    Returns:
        IssueSize enum value.
    """
```

---

## Module: `label_classifier.py` (Extension)

### Function: `classify_labels_with_priority`

```python
async def classify_labels_with_priority(
    title: str,
    description: str = "",
    *,
    github_token: str,
    fallback_labels: list[str] | None = None,
) -> ClassificationResult:
    """Classify labels and optionally detect priority for a GitHub issue.
    
    Same as classify_labels() but also extracts priority from the AI response.
    Falls back to labels-only (priority=None) on any failure.
    
    Args:
        title: Issue title.
        description: Optional issue body.
        github_token: GitHub OAuth token.
        fallback_labels: Optional fallback labels.
        
    Returns:
        ClassificationResult with labels and optional priority.
    """
```

**Input Contract**: Same as existing `classify_labels()`.

**Output Contract**:
| Field | Type | Description |
|-------|------|-------------|
| labels | list[str] | Validated label list (identical to classify_labels return) |
| priority | IssuePriority \| None | P0/P1 if AI detects urgency, None otherwise |

### Dataclass: `ClassificationResult`

```python
@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """Result of label classification with optional priority detection."""
    labels: list[str]
    priority: IssuePriority | None = None
```

---

## Module: `pipelines.py` (Integration Point)

### Modified Function: `execute_pipeline_launch`

**New behavior** (after `add_to_project_with_backlog(ctx)` at line ~431):

```python
# Compute and set project metadata (non-blocking)
try:
    agent_count = _count_configured_agents(config)
    metadata = estimate_from_agent_count(agent_count)
    
    # Override priority if AI detected urgency
    if classification_result.priority is not None:
        metadata.priority = classification_result.priority
    
    # Convert to dict and set on project item
    metadata_dict = {
        "priority": metadata.priority.value,
        "size": metadata.size.value,
        "estimate_hours": metadata.estimate_hours,
        "start_date": metadata.start_date,
        "target_date": metadata.target_date,
    }
    await github_projects_service.set_issue_metadata(
        access_token=session.access_token,
        project_id=project_id,
        item_id=ctx.project_item_id,
        metadata=metadata_dict,
    )
except Exception:
    logger.warning("Failed to set pipeline metadata", exc_info=True)
```

**Non-functional requirements**:
- Metadata setting MUST NOT block pipeline launch on failure
- Metadata setting MUST log warnings on failure (no silent failures)
- The `classify_labels()` call is replaced by `classify_labels_with_priority()` in the pipeline launch path only

---

## Module: `label_classification.py` (Prompt Extension)

### Extended Prompt Contract

The system prompt adds an optional `"priority"` key to the expected JSON output:

```json
{
  "labels": ["ai-generated", "feature", "backend"],
  "priority": "P1"
}
```

**Priority detection rules** (in prompt):
- Return `"P0"` for: production outage, data loss, security breach
- Return `"P1"` for: critical bug, security vulnerability, major functionality broken
- Return `null` or omit for: all other issues (default P2 applied by heuristic)

**Backward compatibility**: If the AI response contains no `"priority"` key, `ClassificationResult.priority` is `None`.
