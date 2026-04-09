from __future__ import annotations

from enum import Enum


class LaunchStatus(str, Enum):
    CREATED = "created"
    READY = "ready"
    BLOCKED = "blocked"
    STARTED = "started"
    RESUMED = "resumed"
    FAILED = "failed"


class ExecutionStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    PARTIAL = "partial"


class StreamingStatus(str, Enum):
    NOT_REQUESTED = "not_requested"
    REQUESTED = "requested"
    STARTED = "started"
    CHUNKING = "chunking"
    COMPLETED = "completed"
    FALLBACK = "fallback"
    SKIPPED = "skipped"
    FAILED = "failed"


LAUNCH_STATUSES = tuple(item.value for item in LaunchStatus)
EXECUTION_STATUSES = tuple(item.value for item in ExecutionStatus)
STREAMING_STATUSES = tuple(item.value for item in StreamingStatus)
