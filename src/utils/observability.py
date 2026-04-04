from __future__ import annotations

import json
from typing import Any, Dict, Optional

from src.utils.nexa_config import get_observability_path, is_observability_enabled
from src.utils.time import now_utc_iso


def observability_path() -> str:
    return get_observability_path()


def _safe_json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False)


def emit_event(event: Dict[str, Any]) -> None:
    """Append a single JSON event to the configured observability path.

    Best-effort only: never raises to callers.
    """
    try:
        path = get_observability_path()
        line = _safe_json_dumps(event)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        return


def make_event(
    *,
    run_id: str,
    circuit_id: str,
    node_id: Optional[str],
    stage: Optional[str],
    event: str,
    success: Optional[bool] = None,
    reason_code: Optional[str] = None,
    metrics: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a normalized observability event dict."""
    return {
        "ts_utc": now_utc_iso(),
        "run_id": run_id,
        "circuit_id": circuit_id,
        "node_id": node_id,
        "stage": stage,
        "event": event,
        "success": success,
        "reason_code": reason_code,
        "metrics": metrics or {},
        "meta": meta or {},
    }
