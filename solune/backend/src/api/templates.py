"""App template API endpoints — browse and inspect templates."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.auth import get_session_dep
from src.models.app_template import AppCategory
from src.models.user import UserSession
from src.services.app_templates.registry import get_template, list_templates

router = APIRouter()

_SessionDep = Annotated[UserSession, Depends(get_session_dep)]


@router.get("")
async def list_templates_endpoint(
    _session: _SessionDep,
    category: Annotated[str | None, Query(description="Filter by category")] = None,
) -> list[dict]:
    """List all available app templates."""
    cat: AppCategory | None = None
    if category:
        try:
            cat = AppCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}") from None
    templates = list_templates(category=cat)
    return [t.to_summary_dict() for t in templates]


@router.get("/{template_id}")
async def get_template_endpoint(
    template_id: str,
    _session: _SessionDep,
) -> dict:
    """Get detailed template information including file manifest."""
    template = get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return template.to_detail_dict()
