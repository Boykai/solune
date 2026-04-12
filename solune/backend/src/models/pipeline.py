"""Pydantic models for Agent Pipeline configurations."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PipelineAgentNode(BaseModel):
    """An agent placed within a stage, configured with pipeline-scoped model and tool overrides."""

    id: str
    agent_slug: str
    agent_display_name: str = ""
    model_id: str = ""
    model_name: str = ""
    tool_ids: list[str] = Field(default_factory=list)
    tool_count: int = 0
    config: dict = Field(default_factory=dict)


class ExecutionGroup(BaseModel):
    """A group of agents within a stage sharing an execution mode."""

    id: str
    order: int = 0
    execution_mode: str = Field(default="sequential")
    agents: list[PipelineAgentNode] = Field(default_factory=list)

    @field_validator("execution_mode")
    @classmethod
    def validate_execution_mode(cls, v: str) -> str:
        if v not in ("sequential", "parallel"):
            raise ValueError("execution_mode must be 'sequential' or 'parallel'")
        return v


class PipelineStage(BaseModel):
    """A named step within a pipeline containing execution groups."""

    id: str
    name: str = Field(..., min_length=1, max_length=100)
    order: int
    groups: list[ExecutionGroup] = Field(default_factory=list)
    agents: list[PipelineAgentNode] = Field(default_factory=list)
    execution_mode: str = Field(default="sequential")

    @field_validator("execution_mode")
    @classmethod
    def validate_execution_mode(cls, v: str) -> str:
        if v not in ("sequential", "parallel"):
            raise ValueError("execution_mode must be 'sequential' or 'parallel'")
        return v


class PipelineConfig(BaseModel):
    """Full pipeline configuration record."""

    id: str
    project_id: str
    name: str
    description: str = ""
    stages: list[PipelineStage] = Field(default_factory=list)
    is_preset: bool = False
    preset_id: str = ""
    created_at: str
    updated_at: str


class PipelineConfigCreate(BaseModel):
    """Request body for creating a new pipeline."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    stages: list[PipelineStage] = Field(default_factory=list)


class PipelineConfigUpdate(BaseModel):
    """Request body for updating an existing pipeline."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    stages: list[PipelineStage] | None = None


class PipelineConfigSummary(BaseModel):
    """Summary of a pipeline for the list endpoint."""

    id: str
    name: str
    description: str
    stage_count: int
    agent_count: int
    total_tool_count: int = 0
    is_preset: bool = False
    preset_id: str = ""
    stages: list[PipelineStage] = Field(default_factory=list)
    updated_at: str


class PipelineConfigListResponse(BaseModel):
    """Response for the list endpoint."""

    pipelines: list[PipelineConfigSummary]
    total: int


class AIModel(BaseModel):
    """An available AI model for agent assignment."""

    id: str
    name: str
    provider: str
    context_window_size: int
    cost_tier: str
    capability_category: str = ""


class ProjectPipelineAssignment(BaseModel):
    """Links a project to a saved pipeline for auto-assignment to new issues."""

    project_id: str
    pipeline_id: str = ""


class ProjectPipelineAssignmentUpdate(BaseModel):
    """Request body for setting/clearing pipeline assignment."""

    pipeline_id: str = ""


class PipelineIssueLaunchRequest(BaseModel):
    """Request body for launching a pipeline from pasted or uploaded issue text."""

    issue_description: str = Field(..., min_length=1, max_length=65_536)
    pipeline_id: str = Field(..., min_length=1)


class FleetDispatchModel(BaseModel):
    """Base model for portable fleet-dispatch configuration records."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class FleetDispatchRepository(FleetDispatchModel):
    """Repository metadata for a fleet-dispatch pipeline config."""

    owner: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)


class FleetDispatchDefaults(FleetDispatchModel):
    """Default runtime settings for fleet-dispatch runs."""

    base_ref: str = Field(..., alias="baseRef", min_length=1)
    error_strategy: Literal["fail-fast", "continue"] = Field(..., alias="errorStrategy")
    poll_interval_seconds: int = Field(..., alias="pollIntervalSeconds", ge=5)
    task_timeout_seconds: int = Field(..., alias="taskTimeoutSeconds", ge=5)

    @model_validator(mode="after")
    def validate_timeout(self) -> "FleetDispatchDefaults":
        if self.task_timeout_seconds < self.poll_interval_seconds:
            raise ValueError("taskTimeoutSeconds must be >= pollIntervalSeconds")
        return self


class FleetDispatchSubIssue(FleetDispatchModel):
    """Sub-issue metadata for a dispatched agent."""

    title: str = Field(..., min_length=1)
    labels: list[str] = Field(default_factory=list, min_length=1)


class FleetDispatchAgent(FleetDispatchModel):
    """Declarative description of a single fleet-dispatch agent."""

    slug: str = Field(..., min_length=1)
    display_name: str = Field(default="", alias="displayName")
    custom_agent: str = Field(default="", alias="customAgent")
    model: str = Field(..., min_length=1)
    instruction_template: str = Field(..., alias="instructionTemplate", min_length=1)
    sub_issue: FleetDispatchSubIssue = Field(..., alias="subIssue")
    retryable: bool


class FleetDispatchExecutionGroup(FleetDispatchModel):
    """Ordered execution boundary for fleet-dispatch agents."""

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    order: int = Field(..., ge=0)
    execution_mode: Literal["serial", "parallel"] = Field(..., alias="executionMode")
    agents: list[FleetDispatchAgent] = Field(default_factory=list, min_length=1)


class FleetDispatchConfig(FleetDispatchModel):
    """Portable fleet-dispatch pipeline configuration."""

    version: Literal["1"]
    name: str = Field(..., min_length=1)
    repository: FleetDispatchRepository
    defaults: FleetDispatchDefaults
    groups: list[FleetDispatchExecutionGroup] = Field(default_factory=list, min_length=1)


class FleetDispatchStatus(StrEnum):
    """Terminal and in-flight states for a fleet-dispatch record."""

    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    SKIPPED = "skipped"


class FleetDispatchRecord(FleetDispatchModel):
    """Serialized dispatch attempt state for one agent."""

    dispatch_id: str = Field(..., alias="dispatchId", min_length=1)
    attempt: int = Field(default=1, ge=1)
    group_id: str = Field(..., alias="groupId", min_length=1)
    agent_slug: str = Field(..., alias="agentSlug", min_length=1)
    sub_issue_number: int = Field(..., alias="subIssueNumber", ge=1)
    status: FleetDispatchStatus
    started_at: str | None = Field(default=None, alias="startedAt")
    completed_at: str | None = Field(default=None, alias="completedAt")
    error_message: str | None = Field(default=None, alias="errorMessage")
    task_id: str | None = Field(default=None, alias="taskId")
