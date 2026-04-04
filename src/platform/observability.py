from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from src.utils.nexa_config import get_observability_filename


def append_observability_event(*, run_dir: str, event: Dict[str, Any]) -> None:
    """Append one observability event as JSONL into run_dir.

    Best-effort: never raises to callers.
    """
    try:
        rd = Path(run_dir)
        rd.mkdir(parents=True, exist_ok=True)
        path = rd / get_observability_filename()
        line = json.dumps(event, ensure_ascii=False)
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        return


def read_observability_events(*, run_dir: str):
    """Read OBSERVABILITY.jsonl events. Returns [] if missing/unreadable."""
    try:
        path = Path(run_dir) / get_observability_filename()
        if not path.exists():
            return []
        events = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if isinstance(obj, dict):
                events.append(obj)
        return events
    except Exception:
        return []
