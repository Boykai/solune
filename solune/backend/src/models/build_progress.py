"""Build progress models — in-memory only, not persisted to database."""

from enum import StrEnum

from pydantic import BaseModel, Field


class BuildPhase(StrEnum):
    SCAFFOLDING = "scaffolding"
    CONFIGURING = "configuring"
    ISSUING = "issuing"
    BUILDING = "building"
    DEPLOYING_PREP = "deploying_prep"
    COMPLETE = "complete"
    FAILED = "failed"


class BuildMilestone(StrEnum):
    SCAFFOLDED = "scaffolded"
    WORKING = "working"
    REVIEW = "review"
    COMPLETE = "complete"


class BuildProgress(BaseModel):
    """Ephemeral build progress state emitted via WebSocket."""

    app_name: str
    phase: BuildPhase
    agent_name: str | None = None
    detail: str = ""
    pct_complete: int = Field(default=0, ge=0, le=100)
    started_at: str = ""
    updated_at: str = ""
