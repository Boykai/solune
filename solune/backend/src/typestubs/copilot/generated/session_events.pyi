from enum import Enum

class SessionEventType(Enum):
    """Event types for copilot session events."""
    ASSISTANT_MESSAGE: str
    SESSION_IDLE: str
    SESSION_ERROR: str
