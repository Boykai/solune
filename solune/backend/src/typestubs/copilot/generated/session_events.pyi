"""Minimal type stubs for copilot.generated.session_events."""

import enum

class SessionEventType(enum.Enum):
    ABORT = "abort"
    ASSISTANT_MESSAGE = "assistant_message"
    ASSISTANT_MESSAGE_DELTA = "assistant_message_delta"
    ASSISTANT_TURN_END = "assistant_turn_end"
    SESSION_ERROR = "session_error"
    SESSION_IDLE = "session_idle"
    SESSION_START = "session_start"
    SESSION_TASK_COMPLETE = "session_task_complete"
    TOOL_EXECUTION_START = "tool_execution_start"
    TOOL_EXECUTION_COMPLETE = "tool_execution_complete"
    USER_MESSAGE = "user_message"
    UNKNOWN = "unknown"
