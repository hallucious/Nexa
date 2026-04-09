from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional
import time

from src.automation.trigger_model import DEFAULT_TRIGGER_SOURCE, normalize_trigger_source


@dataclass
class ExecutionEvent:
    type: str
    execution_id: str
    node_id: Optional[str]
    timestamp_ms: int
    payload: Dict[str, Any]
    trigger_source: str = DEFAULT_TRIGGER_SOURCE
    automation_id: Optional[str] = None

    @staticmethod
    def now(
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        execution_id: str,
        node_id: Optional[str] = None,
        trigger_source: str = DEFAULT_TRIGGER_SOURCE,
        automation_id: Optional[str] = None,
    ) -> "ExecutionEvent":
        return ExecutionEvent(
            type=event_type,
            execution_id=execution_id,
            node_id=node_id,
            timestamp_ms=int(time.time() * 1000),
            payload=payload or {},
            trigger_source=normalize_trigger_source(trigger_source),
            automation_id=automation_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["trigger_source"] = normalize_trigger_source(payload.get("trigger_source"))
        if payload.get("automation_id") is None:
            payload["automation_id"] = None
        return payload
