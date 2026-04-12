# Contract: `api/chat/` Package Interface

**Feature**: Codebase Modularity Review | **Date**: 2026-04-11

> Defines the public interface of the `api/chat/` package after splitting `api/chat.py`.

## Package Entry Point — `api/chat/__init__.py`

```python
from fastapi import APIRouter

from .messages import router as messages_router
from .proposals import router as proposals_router
from .plans import router as plans_router
from .conversations import router as conversations_router
from .streaming import router as streaming_router

router = APIRouter()
router.include_router(messages_router)
router.include_router(proposals_router)
router.include_router(plans_router)
router.include_router(conversations_router)
router.include_router(streaming_router)
```

**Backward Compatibility**: `from src.api.chat import router` continues to work.

## Module: `state.py` — `ChatStateManager`

```python
class ChatStateManager:
    """Manages in-memory caches for chat state with capacity limits."""

    def __init__(
        self,
        max_messages_cache: int = 1000,
        max_proposals_cache: int = 5000,
        max_recommendations_cache: int = 5000,
        max_locks: int = 10000,
    ) -> None: ...

    # Message cache
    def get_messages(self, session_key: str) -> list[ChatMessage] | None: ...
    def set_messages(self, session_key: str, messages: list[ChatMessage]) -> None: ...
    def append_message(self, session_key: str, message: ChatMessage) -> None: ...
    def clear_messages(self, session_key: str) -> None: ...

    # Proposal cache
    def get_proposal(self, proposal_id: str) -> AITaskProposal | None: ...
    def set_proposal(self, proposal_id: str, proposal: AITaskProposal) -> None: ...

    # Recommendation cache
    def get_recommendation(self, recommendation_id: str) -> IssueRecommendation | None: ...
    def set_recommendation(self, recommendation_id: str, recommendation: IssueRecommendation) -> None: ...

    # Lock management
    async def get_lock(self, key: str) -> asyncio.Lock: ...

    # Lifecycle
    def cleanup(self) -> None: ...
```

**Injection**: Via FastAPI `Depends()`, resolved from `app.state.chat_state_manager`.

## Module: `helpers.py` — Shared Utilities

```python
def _get_lock(key: str) -> asyncio.Lock: ...  # Deprecated, use ChatStateManager.get_lock()
async def _retry_persist(fn: Callable, *args, context: str = "", **kwargs) -> None: ...
async def _persist_message(session_id: UUID, message: ChatMessage) -> None: ...
async def _persist_proposal(proposal: AITaskProposal) -> None: ...
async def _persist_recommendation(recommendation: IssueRecommendation) -> None: ...
def _default_expires_at(created_at_str: str) -> str: ...
async def _resolve_repository(session: UserSession) -> tuple[str, str]: ...
def _trigger_signal_delivery(...) -> None: ...
def _safe_validation_detail(exc: ValueError) -> tuple[int, str]: ...
```

## Module: `dispatch.py` — Message Processing Handlers

```python
async def _handle_agent_command(session: UserSession, message: ChatMessage, ...) -> ChatMessage | None: ...
async def _handle_transcript_upload(session: UserSession, file_urls: list[str], ...) -> ChatMessage | None: ...
async def _handle_feature_request(session: UserSession, message: ChatMessage, ...) -> ChatMessage | None: ...
async def _handle_status_change(session: UserSession, message: ChatMessage, ...) -> ChatMessage | None: ...
async def _handle_task_generation(session: UserSession, message: ChatMessage, ...) -> ChatMessage | None: ...
async def _extract_transcript_content(file_urls: list[str]) -> str | None: ...
async def _post_process_agent_response(session: UserSession, response: ChatMessage, ...) -> ChatMessage: ...
```

## Module: `proposals.py` — Public Endpoints

```python
# POST /api/v1/chat/proposals/{proposal_id}/confirm
async def confirm_proposal(proposal_id: str, ...) -> AITaskProposal: ...

# POST /api/v1/chat/proposals/{proposal_id}/cancel
async def cancel_proposal(proposal_id: str, ...) -> AITaskProposal: ...

# POST /api/v1/chat/upload
async def upload_file(file: UploadFile, ...) -> FileUploadResponse: ...
```

## Cross-Module Dependencies

```text
messages.py imports from: helpers, state
proposals.py imports from: helpers, state, services/proposal_orchestrator
plans.py imports from: helpers, state, dispatch
conversations.py imports from: services/chat_store (no internal deps)
streaming.py imports from: helpers, state, dispatch
dispatch.py imports from: helpers, state
```

No circular imports between sub-modules. Dependency flow is strictly downward: endpoints → dispatch → helpers/state.
