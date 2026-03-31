"""App template data models for the template library."""

import re
from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class AppCategory(StrEnum):
    SAAS = "saas"
    API = "api"
    CLI = "cli"
    DASHBOARD = "dashboard"


class ScaffoldType(StrEnum):
    SKELETON = "skeleton"
    STARTER = "starter"


class IaCTarget(StrEnum):
    NONE = "none"
    AZURE = "azure"
    AWS = "aws"
    DOCKER = "docker"


class TemplateFile(BaseModel):
    """A single file in a template's file manifest."""

    source: str = Field(..., description="Relative path in template dir")
    target: str = Field(..., description="Relative output path in scaffolded app")
    variables: list[str] = Field(
        default_factory=list,
        description="Variable names used in this file",
    )

    @field_validator("target")
    @classmethod
    def validate_target_path(cls, v: str) -> str:
        if ".." in v:
            msg = f"Template target path must not contain '..': {v}"
            raise ValueError(msg)
        if v.startswith("/"):
            msg = f"Template target path must not be absolute: {v}"
            raise ValueError(msg)
        return v


_KEBAB_CASE_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")


@dataclass(frozen=True)
class AppTemplate:
    """Metadata for an app scaffold template."""

    id: str
    name: str
    description: str
    category: AppCategory
    difficulty: str
    tech_stack: list[str]
    scaffold_type: ScaffoldType
    files: list[TemplateFile]
    recommended_preset_id: str
    iac_target: IaCTarget = IaCTarget.NONE

    # Internal — resolved base directory for template files on disk.
    _base_dir: str = field(default="", repr=False, compare=False)

    def __post_init__(self) -> None:
        if not _KEBAB_CASE_RE.match(self.id):
            msg = f"Template id must be kebab-case (got '{self.id}')"
            raise ValueError(msg)
        if not self.tech_stack:
            msg = "tech_stack must have at least one entry"
            raise ValueError(msg)
        if not self.files:
            msg = "files must have at least one entry"
            raise ValueError(msg)

    def to_summary_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "difficulty": self.difficulty,
            "tech_stack": list(self.tech_stack),
            "scaffold_type": self.scaffold_type.value,
            "iac_target": self.iac_target.value,
        }

    def to_detail_dict(self) -> dict[str, object]:
        d = self.to_summary_dict()
        d["files"] = [f.model_dump() for f in self.files]
        d["recommended_preset_id"] = self.recommended_preset_id
        return d
