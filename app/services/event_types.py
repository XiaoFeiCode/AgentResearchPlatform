"""Event type constants for the EventBus — one source of truth for all publish/subscribe strings."""

from enum import StrEnum


class EventType(StrEnum):
    SUMMARY_READY = "summary_ready"
    ENGINE_PROGRESS = "engine_progress"
    FORUM_MESSAGE = "forum_message"
    CONSOLE_OUTPUT = "console_output"
    ENGINE_ERROR = "engine_error"
    ENGINE_RESULT = "engine_result"
