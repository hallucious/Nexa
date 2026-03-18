from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional
import time


@dataclass
class ExecutionEvent:
    type: str
    execution_id: str
    node_id: Optional[str]
    timestamp_ms: int
    payload: Dict[str, Any]

    @staticmethod
    def now(
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        execution_id: str,
        node_id: Optional[str] = None,
    ) -> "ExecutionEvent":
        return ExecutionEvent(
            type=event_type,
            execution_id=execution_id,
            node_id=node_id,
            timestamp_ms=int(time.time() * 1000),
            payload=payload or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)