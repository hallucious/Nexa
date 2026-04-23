from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

TRIGGER_SOURCE_MANUAL = "manual"
TRIGGER_SOURCE_AUTOMATION = "automation"
TRIGGER_SOURCE_SCHEDULE = "schedule"
TRIGGER_SOURCE_EVENT = "event"
TRIGGER_SOURCE_API = "api"
TRIGGER_SOURCE_REPLAY = "replay"

ALLOWED_TRIGGER_SOURCES = frozenset(
    {
        TRIGGER_SOURCE_MANUAL,
        TRIGGER_SOURCE_AUTOMATION,
        TRIGGER_SOURCE_SCHEDULE,
        TRIGGER_SOURCE_EVENT,
        TRIGGER_SOURCE_API,
        TRIGGER_SOURCE_REPLAY,
    }
)

DEFAULT_TRIGGER_SOURCE = TRIGGER_SOURCE_MANUAL


def normalize_trigger_source(value: Optional[str]) -> str:
    normalized = (value or DEFAULT_TRIGGER_SOURCE).strip().lower()
    if normalized in ALLOWED_TRIGGER_SOURCES:
        return normalized
    return DEFAULT_TRIGGER_SOURCE


@dataclass(frozen=True)
class ExecutionTriggerIdentity:
    execution_id: str
    trigger_source: str = DEFAULT_TRIGGER_SOURCE
    automation_id: Optional[str] = None

    def normalized(self) -> "ExecutionTriggerIdentity":
        return ExecutionTriggerIdentity(
            execution_id=str(self.execution_id),
            trigger_source=normalize_trigger_source(self.trigger_source),
            automation_id=(str(self.automation_id).strip() if self.automation_id is not None else None) or None,
        )
