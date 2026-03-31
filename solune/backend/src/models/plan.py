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


# ---------------------------------------------------------------------------
# Core domain models
# ---------------------------------------------------------------------------


class PlanStep(BaseModel):
    """A single step within an implementation plan."""

    step_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique step identifier")
    plan_id: str = Field(..., description="Parent plan reference")
    position: int = Field(..., ge=0, description="Step order (0-indexed)")
    title: str = Field(..., min_length=1, max_length=256, description="Step title (becomes issue title)")
    description: str = Field(
        ..., min_length=1, max_length=65536, description="Step description (becomes issue body)"
    )
    dependencies: list[str] = Field(default_factory=list, description="step_ids this step depends on")
    issue_number: int | None = Field(default=None, description="GitHub issue number (post-approval)")
    issue_url: str | None = Field(default=None, description="GitHub issue URL (post-approval)")


class Plan(BaseModel):
    """A structured implementation plan scoped to a project/repo."""

    plan_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique plan identifier")
    session_id: str = Field(..., description="Parent chat session")
    title: str = Field(..., min_length=1, max_length=256, description="Plan title")
    summary: str = Field(..., min_length=1, max_length=65536, description="Plan summary/description")
    status: PlanStatus = Field(default=PlanStatus.DRAFT, description="Plan lifecycle status")
    project_id: str = Field(..., min_length=1, description="Associated GitHub project ID")
    project_name: str = Field(..., min_length=1, description="Project display name")
    repo_owner: str = Field(..., min_length=1, description="GitHub repository owner")
    repo_name: str = Field(..., min_length=1, description="GitHub repository name")
    parent_issue_number: int | None = Field(default=None, description="Parent issue number (post-approval)")
    parent_issue_url: str | None = Field(default=None, description="Parent issue URL (post-approval)")
    steps: list[PlanStep] = Field(default_factory=list, description="Ordered plan steps")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    updated_at: str | None = Field(default=None, description="Last-updated timestamp")

    @field_validator("steps")
    @classmethod
    def _validate_step_positions(cls, v: list[PlanStep]) -> list[PlanStep]:
        """Ensure step positions are non-negative (already enforced by PlanStep.position ge=0)."""
        return v


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
    issue_number: int | None = None
    issue_url: str | None = None


class PlanResponse(BaseModel):
    """API response model for a full plan."""

    plan_id: str
    session_id: str
    title: str
    summary: str
    status: str
    project_id: str
    project_name: str
    repo_owner: str
    repo_name: str
    parent_issue_number: int | None = None
    parent_issue_url: str | None = None
    steps: list[PlanStepResponse]
    created_at: str
    updated_at: str


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

    title: str | None = None
    summary: str | None = None
