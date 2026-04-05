"""Plan and PlanStep models for the /plan planning mode.

These models represent structured implementation plans scoped to a
specific project and repository.  Each plan contains ordered steps
that become GitHub issues upon approval.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class PlanStatus(StrEnum):
    """Lifecycle status of a plan."""

    DRAFT = "draft"
    APPROVED = "approved"
    COMPLETED = "completed"
    FAILED = "failed"


class StepApprovalStatus(StrEnum):
    """Per-step approval status for granular plan review."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Core domain models
# ---------------------------------------------------------------------------


class PlanStep(BaseModel):
    """A single step within an implementation plan."""

    step_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique step identifier")
    plan_id: str = Field(..., description="Parent plan reference")
    position: int = Field(..., ge=0, description="Step order (0-indexed)")
    title: str = Field(
        ..., min_length=1, max_length=256, description="Step title (becomes issue title)"
    )
    description: str = Field(
        ..., min_length=1, max_length=65536, description="Step description (becomes issue body)"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="step_ids this step depends on"
    )
    approval_status: StepApprovalStatus = Field(
        default=StepApprovalStatus.PENDING,
        description="Per-step approval status",
    )
    issue_number: int | None = Field(
        default=None, description="GitHub issue number (post-approval)"
    )
    issue_url: str | None = Field(default=None, description="GitHub issue URL (post-approval)")


class Plan(BaseModel):
    """A structured implementation plan scoped to a project/repo."""

    plan_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique plan identifier")
    session_id: str = Field(..., description="Parent chat session")
    title: str = Field(..., min_length=1, max_length=256, description="Plan title")
    summary: str = Field(
        ..., min_length=1, max_length=65536, description="Plan summary/description"
    )
    status: PlanStatus = Field(default=PlanStatus.DRAFT, description="Plan lifecycle status")
    version: int = Field(default=1, ge=1, description="Auto-incremented version number")
    project_id: str = Field(..., min_length=1, description="Associated GitHub project ID")
    project_name: str = Field(..., min_length=1, description="Project display name")
    repo_owner: str = Field(..., min_length=1, description="GitHub repository owner")
    repo_name: str = Field(..., min_length=1, description="GitHub repository name")
    parent_issue_number: int | None = Field(
        default=None, description="Parent issue number (post-approval)"
    )
    parent_issue_url: str | None = Field(
        default=None, description="Parent issue URL (post-approval)"
    )
    steps: list[PlanStep] = Field(default_factory=list, description="Ordered plan steps")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    updated_at: str | None = Field(default=None, description="Last-updated timestamp")


class PlanVersion(BaseModel):
    """Immutable snapshot of a plan at a specific version."""

    version_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique version identifier"
    )
    plan_id: str = Field(..., description="Parent plan reference")
    version: int = Field(..., ge=1, description="Version number at time of snapshot")
    title: str = Field(..., description="Title at this version")
    summary: str = Field(..., description="Summary at this version")
    steps_json: str = Field(default="[]", description="JSON array of step snapshots")
    created_at: str | None = Field(default=None, description="Snapshot timestamp")


# ---------------------------------------------------------------------------
# Response / request models
# ---------------------------------------------------------------------------


class PlanStepResponse(BaseModel):
    """API response model for a single plan step."""

    step_id: str
    position: int
    title: str
    description: str
    dependencies: list[str]
    approval_status: StepApprovalStatus = StepApprovalStatus.PENDING
    issue_number: int | None = None
    issue_url: str | None = None


class PlanResponse(BaseModel):
    """API response model for a full plan."""

    plan_id: str
    session_id: str
    title: str
    summary: str
    status: str
    version: int = 1
    project_id: str
    project_name: str
    repo_owner: str
    repo_name: str
    parent_issue_number: int | None = None
    parent_issue_url: str | None = None
    steps: list[PlanStepResponse]
    created_at: str
    updated_at: str


class PlanVersionResponse(BaseModel):
    """API response model for a plan version snapshot."""

    version_id: str
    plan_id: str
    version: int
    title: str
    summary: str
    steps_json: str
    created_at: str


class PlanHistoryResponse(BaseModel):
    """API response wrapping a plan's version history."""

    plan_id: str
    current_version: int
    versions: list[PlanVersionResponse]


class PlanApprovalResponse(BaseModel):
    """API response after plan approval (issue creation)."""

    plan_id: str
    status: str
    parent_issue_number: int | None = None
    parent_issue_url: str | None = None
    steps: list[PlanStepResponse]


class PlanExitResponse(BaseModel):
    """API response for exiting plan mode."""

    message: str
    plan_id: str
    plan_status: str


class PlanUpdateRequest(BaseModel):
    """Request body for updating plan metadata."""

    title: str | None = Field(
        default=None,
        min_length=1,
        description="Updated plan title (must be non-empty when provided)",
    )
    summary: str | None = Field(
        default=None,
        min_length=1,
        description="Updated plan summary (must be non-empty when provided)",
    )

    @field_validator("title", "summary")
    @classmethod
    def _non_empty_when_provided(cls, v: str | None) -> str | None:
        """Ensure provided strings are not empty or whitespace-only."""
        if v is None:
            return None
        if not v.strip():
            raise ValueError("must not be empty or whitespace only")
        return v


# ---------------------------------------------------------------------------
# Step CRUD request models
# ---------------------------------------------------------------------------


class StepCreateRequest(BaseModel):
    """Request body for creating a new plan step."""

    title: str = Field(..., min_length=1, max_length=256, description="Step title")
    description: str = Field(..., min_length=1, max_length=65536, description="Step description")
    dependencies: list[str] = Field(
        default_factory=list, description="step_ids this step depends on"
    )
    position: int | None = Field(
        default=None, ge=0, description="Insert position (auto-appended if omitted)"
    )


class StepUpdateRequest(BaseModel):
    """Request body for updating an existing plan step."""

    title: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = Field(default=None, min_length=1, max_length=65536)
    dependencies: list[str] | None = Field(default=None)

    @field_validator("title", "description")
    @classmethod
    def _non_empty_when_provided(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not v.strip():
            raise ValueError("must not be empty or whitespace only")
        return v


class StepReorderRequest(BaseModel):
    """Request body for reordering plan steps."""

    step_ids: list[str] = Field(
        ..., min_length=1, description="Ordered list of step_ids defining new positions"
    )


class StepApprovalRequest(BaseModel):
    """Request body for approving/rejecting a plan step."""

    approval_status: StepApprovalStatus = Field(..., description="New approval status")


class FeedbackType(StrEnum):
    """Allowed feedback types for step-level feedback."""

    COMMENT = "comment"
    APPROVE = "approve"
    REJECT = "reject"


class StepFeedbackRequest(BaseModel):
    """Request body for submitting step-level feedback."""

    feedback_type: FeedbackType = Field(
        ..., description="Feedback type: 'comment', 'approve', or 'reject'"
    )
    content: str = Field(default="", max_length=65536, description="Feedback text")


class StepFeedbackResponse(BaseModel):
    """Response after submitting step feedback."""

    step_id: str
    feedback_type: str
    status: str = "accepted"
