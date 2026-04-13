"""Plan mode endpoints for the chat API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from src.api.auth import get_session_dep
from src.dependencies import require_selected_project
from src.logging_utils import get_logger
from src.middleware.rate_limit import limiter
from src.models.chat import ActionType, ChatMessage, ChatMessageRequest, SenderType
from src.models.user import UserSession
from src.services.cache import cache, get_user_projects_cache_key
from src.services.chat_agent import get_chat_agent_service
from src.services.database import get_db

from src.api.chat.persistence import add_message, _trigger_signal_delivery
from src.api.chat.messages import _resolve_repository

logger = get_logger(__name__)
router = APIRouter()


@router.post("/messages/plan")
@limiter.limit("10/minute")
async def send_plan_message(
    request: Request,
    chat_request: ChatMessageRequest,
    session: Annotated[UserSession, Depends(get_session_dep)],
):
    """Enter plan mode (non-streaming).

    The user's message is treated as a feature description for the plan agent.
    """
    selected_project_id = require_selected_project(session)

    content = chat_request.content.strip()
    # Strip /plan prefix if present
    if content.lower().startswith("/plan"):
        content = content[5:].strip()
    if not content:
        return JSONResponse(
            status_code=400,
            content={"detail": "Please provide a feature description after /plan."},
        )

    try:
        owner, repo = await _resolve_repository(session)
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"detail": "No repository linked to the selected project."},
        )

    # Get project details
    project_name = "Unknown Project"
    project_columns: list[str] = []
    cache_key = get_user_projects_cache_key(session.github_user_id)
    cached_projects = cache.get(cache_key)
    if cached_projects:
        for p in cached_projects:
            if p.project_id == selected_project_id:
                project_name = p.name
                project_columns = [col.name for col in p.status_columns]
                break

    try:
        chat_agent_svc = get_chat_agent_service()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"detail": "Plan mode not available."},
        )

    # Create user message only after plan mode is confirmed available.
    user_message = ChatMessage(
        session_id=session.session_id,
        sender_type=SenderType.USER,
        content=chat_request.content,
        conversation_id=chat_request.conversation_id,
    )
    await add_message(session.session_id, user_message)

    result = await chat_agent_svc.run_plan(
        message=content,
        session_id=session.session_id,
        github_token=session.access_token,
        project_name=project_name,
        project_id=selected_project_id,
        available_statuses=project_columns,
        repo_owner=owner,
        repo_name=repo,
        selected_pipeline_id=chat_request.pipeline_id,
        db=get_db(),
    )
    result.conversation_id = chat_request.conversation_id
    await add_message(session.session_id, result)
    return result


@router.post("/messages/plan/stream")
@limiter.limit("10/minute")
async def send_plan_message_stream(
    request: Request,
    chat_request: ChatMessageRequest,
    session: Annotated[UserSession, Depends(get_session_dep)],
):
    """Enter plan mode with SSE streaming and thinking events."""
    from sse_starlette.sse import EventSourceResponse

    selected_project_id = require_selected_project(session)

    content = chat_request.content.strip()
    if content.lower().startswith("/plan"):
        content = content[5:].strip()
    if not content:
        return JSONResponse(
            status_code=400,
            content={"detail": "Please provide a feature description after /plan."},
        )

    try:
        owner, repo = await _resolve_repository(session)
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"detail": "No repository linked to the selected project."},
        )

    # Get project details
    project_name = "Unknown Project"
    project_columns: list[str] = []
    cache_key = get_user_projects_cache_key(session.github_user_id)
    cached_projects = cache.get(cache_key)
    if cached_projects:
        for p in cached_projects:
            if p.project_id == selected_project_id:
                project_name = p.name
                project_columns = [col.name for col in p.status_columns]
                break

    try:
        chat_agent_svc = get_chat_agent_service()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"detail": "Plan mode not available."},
        )

    # Create user message only after plan mode is confirmed available.
    user_message = ChatMessage(
        session_id=session.session_id,
        sender_type=SenderType.USER,
        content=chat_request.content,
        conversation_id=chat_request.conversation_id,
    )
    await add_message(session.session_id, user_message)

    async def event_generator():
        async for event in chat_agent_svc.run_plan_stream(
            message=content,
            session_id=session.session_id,
            github_token=session.access_token,
            project_name=project_name,
            project_id=selected_project_id,
            available_statuses=project_columns,
            repo_owner=owner,
            repo_name=repo,
            selected_pipeline_id=chat_request.pipeline_id,
            db=get_db(),
        ):
            if event.get("event") == "done":
                try:
                    assistant_message = ChatMessage.model_validate_json(event["data"])
                    assistant_message.conversation_id = chat_request.conversation_id
                    await add_message(session.session_id, assistant_message)
                    yield {
                        "event": "done",
                        "data": assistant_message.model_dump_json(),
                    }
                except Exception:
                    logger.error(
                        "Failed to persist plan streamed response",
                        exc_info=True,
                    )
                    yield event
                continue
            yield event

    return EventSourceResponse(event_generator())


@router.get("/plans/{plan_id}")
async def get_plan_endpoint(
    plan_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
):
    """Retrieve a plan with all steps."""
    from src.models.plan import PlanResponse, PlanStepResponse
    from src.services import chat_store

    db = get_db()
    plan = await chat_store.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    # Verify the plan belongs to this session
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    steps = [
        PlanStepResponse(
            step_id=s["step_id"],
            position=s["position"],
            title=s["title"],
            description=s["description"],
            dependencies=s.get("dependencies", []),
            approval_status=s.get("approval_status", "pending"),
            issue_number=s.get("issue_number"),
            issue_url=s.get("issue_url"),
        )
        for s in plan.get("steps", [])
    ]
    return PlanResponse(
        plan_id=plan["plan_id"],
        session_id=plan["session_id"],
        title=plan["title"],
        summary=plan["summary"],
        status=plan["status"],
        version=plan.get("version", 1),
        project_id=plan["project_id"],
        project_name=plan["project_name"],
        repo_owner=plan["repo_owner"],
        repo_name=plan["repo_name"],
        parent_issue_number=plan.get("parent_issue_number"),
        parent_issue_url=plan.get("parent_issue_url"),
        steps=steps,
        created_at=plan["created_at"],
        updated_at=plan["updated_at"],
    )


@router.patch("/plans/{plan_id}")
async def update_plan_endpoint(
    plan_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    request: Request,
):
    """Update plan metadata (title and/or summary)."""
    from src.models.plan import PlanResponse, PlanStepResponse, PlanUpdateRequest
    from src.services import chat_store

    body = await request.json()
    update_req = PlanUpdateRequest(**body)

    db = get_db()
    plan = await chat_store.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["status"] != "draft":
        return JSONResponse(
            status_code=400,
            content={"detail": "Only draft plans can be updated."},
        )

    await chat_store.update_plan(db, plan_id, title=update_req.title, summary=update_req.summary)
    updated = await chat_store.get_plan(db, plan_id)
    if updated is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found after update."})
    steps = [
        PlanStepResponse(
            step_id=s["step_id"],
            position=s["position"],
            title=s["title"],
            description=s["description"],
            dependencies=s.get("dependencies", []),
            issue_number=s.get("issue_number"),
            issue_url=s.get("issue_url"),
        )
        for s in updated.get("steps", [])
    ]
    return PlanResponse(
        plan_id=updated["plan_id"],
        session_id=updated["session_id"],
        title=updated["title"],
        summary=updated["summary"],
        status=updated["status"],
        project_id=updated["project_id"],
        project_name=updated["project_name"],
        repo_owner=updated["repo_owner"],
        repo_name=updated["repo_name"],
        parent_issue_number=updated.get("parent_issue_number"),
        parent_issue_url=updated.get("parent_issue_url"),
        steps=steps,
        created_at=updated["created_at"],
        updated_at=updated["updated_at"],
    )


@router.post("/plans/{plan_id}/approve")
async def approve_plan_endpoint(
    plan_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
):
    """Approve a plan and launch it through the shared parent-issue pipeline flow."""
    from src.api.pipelines import execute_pipeline_launch
    from src.models.plan import PlanApprovalResponse, PlanStepResponse
    from src.services import chat_store
    from src.services.plan_issue_service import format_plan_issue_markdown

    db = get_db()
    plan = await chat_store.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["status"] != "draft":
        return JSONResponse(
            status_code=400,
            content={"detail": "Only draft plans can be approved."},
        )
    if not plan.get("steps"):
        return JSONResponse(
            status_code=400,
            content={"detail": "Cannot approve a plan with zero steps."},
        )

    # Set status to approved before creating issues
    await chat_store.update_plan_status(db, plan_id, "approved")

    try:
        workflow_result = await execute_pipeline_launch(
            project_id=plan["project_id"],
            issue_description=format_plan_issue_markdown(plan),
            pipeline_id=plan.get("selected_pipeline_id"),
            session=session,
        )
    except Exception:
        logger.error("Plan issue creation failed", exc_info=True)
        await chat_store.update_plan_status(db, plan_id, "failed")
        return JSONResponse(
            status_code=502,
            content={
                "error": "GitHub issue creation failed",
                "plan_id": plan_id,
                "status": "failed",
                "detail": "An error occurred while creating GitHub issues. Please try again.",
            },
        )

    if workflow_result.issue_number and workflow_result.issue_url:
        await chat_store.update_plan_parent_issue(
            db,
            plan_id,
            workflow_result.issue_number,
            workflow_result.issue_url,
        )

    if not workflow_result.issue_number:
        await chat_store.update_plan_status(db, plan_id, "failed")
        return JSONResponse(
            status_code=502,
            content={
                "error": "GitHub issue creation failed",
                "plan_id": plan_id,
                "status": "failed",
                "detail": workflow_result.message,
            },
        )

    if not workflow_result.success:
        logger.warning(
            "Plan %s created parent issue #%s but pipeline launch returned a warning: %s",
            plan_id,
            workflow_result.issue_number,
            workflow_result.message,
        )

    await chat_store.update_plan_status(db, plan_id, "completed")

    if workflow_result.issue_number and workflow_result.issue_url:
        confirmation_prefix = (
            "✅ GitHub parent issue created for plan"
            if workflow_result.success
            else "⚠️ GitHub parent issue created for plan"
        )
        confirmation_content = (
            f"{confirmation_prefix} **{plan['title']}** "
            f"([#{workflow_result.issue_number}]({workflow_result.issue_url}))"
        )
        if not workflow_result.success and workflow_result.message:
            confirmation_content += f"\n\n{workflow_result.message}"

        confirm_message = ChatMessage(
            session_id=session.session_id,
            sender_type=SenderType.SYSTEM,
            content=confirmation_content,
            action_type=ActionType.PLAN_CREATE,
            action_data={
                "plan_id": plan_id,
                "parent_issue_number": workflow_result.issue_number,
                "parent_issue_url": workflow_result.issue_url,
                "status": "completed",
            },
        )
        await add_message(session.session_id, confirm_message)
        _trigger_signal_delivery(session, confirm_message)

    # Re-fetch for accurate state
    updated_plan = await chat_store.get_plan(db, plan_id)
    steps = [
        PlanStepResponse(
            step_id=s["step_id"],
            position=s["position"],
            title=s["title"],
            description=s["description"],
            dependencies=s.get("dependencies", []),
            issue_number=s.get("issue_number"),
            issue_url=s.get("issue_url"),
        )
        for s in (updated_plan or plan).get("steps", [])
    ]
    return PlanApprovalResponse(
        plan_id=plan_id,
        status="completed",
        parent_issue_number=workflow_result.issue_number,
        parent_issue_url=workflow_result.issue_url,
        steps=steps,
    )


@router.post("/plans/{plan_id}/exit")
async def exit_plan_mode_endpoint(
    plan_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
):
    """Exit plan mode and return to normal chat."""
    from src.models.plan import PlanExitResponse
    from src.services import chat_store

    db = get_db()
    plan = await chat_store.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    # Clear plan mode from agent session
    try:
        chat_agent_svc = get_chat_agent_service()
        await chat_agent_svc.exit_plan_mode(session.session_id)
    except Exception:
        logger.warning("Failed to clear plan mode from agent session", exc_info=True)

    return PlanExitResponse(
        message="Plan mode deactivated",
        plan_id=plan_id,
        plan_status=plan["status"],
    )


# ---------------------------------------------------------------------------
# Plan v2 endpoints — history, step CRUD, feedback, approval, reorder, export
# ---------------------------------------------------------------------------


# Known safe ValueError messages mapped to (http_status, client-safe description).
# Returning hardcoded strings (never str(exc)) breaks the CodeQL taint chain.
# Non-draft plan conflicts → 409; validation errors → 400.
_SAFE_ERROR_MESSAGES: dict[str, tuple[int, str]] = {
    "Cannot add steps": (409, "Cannot add steps to a non-draft plan."),
    "Cannot change approval": (409, "Cannot change approval status of steps in a non-draft plan."),
    "Cannot delete steps": (409, "Cannot delete steps from a non-draft plan."),
    "Cannot modify steps": (409, "Cannot modify steps in a non-draft plan."),
    "Cannot reorder steps": (409, "Cannot reorder steps in a non-draft plan."),
    "Cannot update steps": (409, "Cannot update steps of a non-draft plan."),
    "DAG validation failed": (400, "DAG validation failed: invalid step dependencies."),
    "Invalid approval_status": (400, "Invalid approval status value."),
    "step_ids must contain exactly the current step IDs": (
        400,
        "step_ids must contain exactly the current step IDs.",
    ),
}


def _safe_validation_detail(exc: ValueError) -> tuple[int, str]:
    """Return a (status_code, detail) pair for a domain ValueError.

    Returns 409 for non-draft plan conflicts, 400 for validation errors,
    and a generic 400 when the exception doesn't match a known prefix.
    Uses hardcoded messages only (never ``str(exc)``) to avoid leaking internals.
    """
    msg = str(exc)  # Used only for prefix matching; never returned to clients.
    for prefix, response in _SAFE_ERROR_MESSAGES.items():
        if msg.startswith(prefix):
            return response
    return 400, "Invalid request: validation failed."


@router.get("/plans/{plan_id}/history")
async def get_plan_history_endpoint(
    plan_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
):
    """Retrieve version history for a plan, ordered by version descending."""
    from src.models.plan import PlanHistoryResponse, PlanVersionResponse
    from src.services import chat_store

    db = get_db()
    plan = await chat_store.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    versions = await chat_store.get_plan_versions(db, plan_id)
    return PlanHistoryResponse(
        plan_id=plan_id,
        current_version=plan.get("version", 1),
        versions=[
            PlanVersionResponse(
                version_id=v["version_id"],
                plan_id=v["plan_id"],
                version=v["version"],
                title=v["title"],
                summary=v["summary"],
                steps_json=v["steps_json"],
                created_at=v["created_at"],
            )
            for v in versions
        ],
    )


@router.post("/plans/{plan_id}/steps")
async def add_plan_step_endpoint(
    plan_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    request: Request,
):
    """Add a new step to a plan."""
    from src.models.plan import PlanStepResponse, StepCreateRequest
    from src.services import chat_store

    db = get_db()
    plan = await chat_store.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    body = await request.json()
    try:
        req = StepCreateRequest(**body)
    except Exception:
        return JSONResponse(status_code=422, content={"detail": "Invalid request body."})

    try:
        step = await chat_store.add_plan_step(
            db,
            plan_id,
            title=req.title,
            description=req.description,
            dependencies=req.dependencies,
            position=req.position,
        )
    except ValueError as e:
        status, detail = _safe_validation_detail(e)
        return JSONResponse(status_code=status, content={"detail": detail})

    if step is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    return JSONResponse(
        status_code=201,
        content=PlanStepResponse(
            step_id=step["step_id"],
            position=step["position"],
            title=step["title"],
            description=step["description"],
            dependencies=step.get("dependencies", []),
            approval_status=step.get("approval_status", "pending"),
        ).model_dump(),
    )


@router.patch("/plans/{plan_id}/steps/{step_id}")
async def update_plan_step_endpoint(
    plan_id: str,
    step_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    request: Request,
):
    """Update an existing plan step."""
    from src.models.plan import PlanStepResponse, StepUpdateRequest
    from src.services import chat_store

    db = get_db()
    plan = await chat_store.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    body = await request.json()
    try:
        req = StepUpdateRequest(**body)
    except Exception:
        return JSONResponse(status_code=422, content={"detail": "Invalid request body."})

    try:
        step = await chat_store.update_plan_step(
            db,
            plan_id,
            step_id,
            title=req.title,
            description=req.description,
            dependencies=req.dependencies,
        )
    except ValueError as e:
        status, detail = _safe_validation_detail(e)
        return JSONResponse(status_code=status, content={"detail": detail})

    if step is None:
        return JSONResponse(status_code=404, content={"detail": "Step not found."})

    return PlanStepResponse(
        step_id=step["step_id"],
        position=step["position"],
        title=step["title"],
        description=step["description"],
        dependencies=step.get("dependencies", []),
        approval_status=step.get("approval_status", "pending"),
    )


@router.delete("/plans/{plan_id}/steps/{step_id}")
async def delete_plan_step_endpoint(
    plan_id: str,
    step_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
):
    """Delete a plan step."""
    from src.services import chat_store

    db = get_db()
    plan = await chat_store.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    try:
        deleted = await chat_store.delete_plan_step(db, plan_id, step_id)
    except ValueError as e:
        status, detail = _safe_validation_detail(e)
        return JSONResponse(status_code=status, content={"detail": detail})

    if not deleted:
        return JSONResponse(status_code=404, content={"detail": "Step not found."})

    return Response(status_code=204)


@router.post("/plans/{plan_id}/steps/reorder")
async def reorder_plan_steps_endpoint(
    plan_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    request: Request,
):
    """Reorder plan steps with DAG re-validation."""
    from src.models.plan import PlanStepResponse, StepReorderRequest
    from src.services import chat_store

    db = get_db()
    plan = await chat_store.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    body = await request.json()
    try:
        req = StepReorderRequest(**body)
    except Exception:
        return JSONResponse(status_code=422, content={"detail": "Invalid request body."})

    try:
        reordered = await chat_store.reorder_plan_steps(db, plan_id, req.step_ids)
    except ValueError as e:
        status, detail = _safe_validation_detail(e)
        return JSONResponse(status_code=status, content={"detail": detail})

    if not reordered:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    # Re-fetch the plan to return the updated steps in new order
    updated_plan = await chat_store.get_plan(db, plan_id)
    if updated_plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    return [
        PlanStepResponse(
            step_id=s["step_id"],
            position=s["position"],
            title=s["title"],
            description=s["description"],
            dependencies=s.get("dependencies", []),
            approval_status=s.get("approval_status", "pending"),
        )
        for s in updated_plan.get("steps", [])
    ]


@router.post("/plans/{plan_id}/steps/{step_id}/approve")
async def approve_plan_step_endpoint(
    plan_id: str,
    step_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    request: Request,
):
    """Update the approval status of a single plan step."""
    from src.models.plan import PlanStepResponse, StepApprovalRequest
    from src.services import chat_store

    db = get_db()
    plan = await chat_store.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    body = await request.json()
    try:
        req = StepApprovalRequest(**body)
    except Exception:
        return JSONResponse(status_code=422, content={"detail": "Invalid request body."})

    try:
        updated = await chat_store.update_step_approval(
            db, plan_id, step_id, req.approval_status.value
        )
    except ValueError as e:
        status, detail = _safe_validation_detail(e)
        return JSONResponse(status_code=status, content={"detail": detail})

    if not updated:
        return JSONResponse(status_code=404, content={"detail": "Step not found."})

    # Re-fetch step to return full response
    updated_plan = await chat_store.get_plan(db, plan_id)
    step_data = None
    if updated_plan:
        for s in updated_plan.get("steps", []):
            if s["step_id"] == step_id:
                step_data = s
                break

    if step_data is None:
        return {"step_id": step_id, "approval_status": req.approval_status.value}

    return PlanStepResponse(
        step_id=step_data["step_id"],
        position=step_data["position"],
        title=step_data["title"],
        description=step_data["description"],
        dependencies=step_data.get("dependencies", []),
        approval_status=step_data.get("approval_status", "pending"),
    )


@router.post("/plans/{plan_id}/steps/{step_id}/feedback")
async def submit_step_feedback_endpoint(
    plan_id: str,
    step_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    request: Request,
):
    """Submit step-level feedback for plan refinement.

    Stub: validates the plan/step and accepts the feedback with HTTP 202,
    but does not yet persist or route the feedback to the active agent
    session.  Persistence and SDK elicitation will be wired in when the
    Copilot SDK upgrade lands.
    """
    from src.models.plan import StepFeedbackRequest, StepFeedbackResponse
    from src.services import chat_store

    db = get_db()
    plan = await chat_store.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    # Verify step exists
    step_found = any(s["step_id"] == step_id for s in plan.get("steps", []))
    if not step_found:
        return JSONResponse(status_code=404, content={"detail": "Step not found."})

    body = await request.json()
    try:
        req = StepFeedbackRequest(**body)
    except Exception:
        return JSONResponse(status_code=422, content={"detail": "Invalid request body."})

    # Feedback is transient — accepted for async agent processing
    return JSONResponse(
        status_code=202,
        content=StepFeedbackResponse(
            step_id=step_id,
            feedback_type=req.feedback_type.value,
            status="accepted",
        ).model_dump(),
    )


@router.get("/plans/{plan_id}/export")
async def export_plan_endpoint(
    plan_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    format: str = "markdown",
):
    """Export a plan as markdown or GitHub issues format."""
    from src.services import chat_store

    db = get_db()
    plan = await chat_store.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    if format == "markdown":
        lines = [f"# {plan['title']}", "", plan["summary"], "", "## Steps", ""]
        for s in plan.get("steps", []):
            deps = ""
            if s.get("dependencies"):
                deps = f" (depends on: {', '.join(s['dependencies'])})"
            lines.append(f"### {s['position'] + 1}. {s['title']}{deps}")
            lines.append("")
            lines.append(s["description"])
            lines.append("")
        return {"format": "markdown", "content": "\n".join(lines)}
    elif format == "github_issues":
        issues = [
            {
                "title": s["title"],
                "body": s["description"],
                "dependencies": s.get("dependencies", []),
            }
            for s in plan.get("steps", [])
        ]
        return {"format": "github_issues", "plan_title": plan["title"], "issues": issues}
    else:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Unsupported format: {format}. Use 'markdown' or 'github_issues'."},
        )
