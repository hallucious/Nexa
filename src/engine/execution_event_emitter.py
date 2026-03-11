from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import json

from src.engine.execution_event import ExecutionEvent


class ExecutionEventEmitter:
    """
    Runtime-local execution event collector.

    Responsibilities:
    - collect emitted events in memory
    - optionally append them to a JSONL file
    """

    def __init__(self, event_file: Optional[str] = "EXECUTION_EVENTS.jsonl"):
        self._events: List[ExecutionEvent] = []
        self._event_file = Path(event_file) if event_file else None

    def emit(self, event: ExecutionEvent) -> None:
        self._events.append(event)

        if self._event_file is not None:
            with self._event_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    def get_events(self) -> List[ExecutionEvent]:
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()