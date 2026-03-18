from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from src.utils.time import now_utc_iso


def is_observability_enabled(raw: Optional[Dict[str, Any]] = None) -> bool:
    """Observability is opt-in.

    Enable by:
    - env var HAI_OBSERVABILITY=1/true
    - raw["observability_enabled"] == True
    """
    try:
        if isinstance(raw, dict) and raw.get("observability_enabled") is True:
            return True
    except Exception:
        pass

    v = os.getenv("HAI_OBSERVABILITY", "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def observability_path() -> str:
    return os.getenv("HAI_OBSERVABILITY_PATH", "OBSERVABILITY.jsonl")


def _safe_json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False)


def emit_event(event: Dict[str, Any]) -> None:
    """Append a single JSON event to OBSERVABILITY.jsonl.

    This function is best-effort and must never raise.
    """
    try:
        path = observability_path()
        line = _safe_json_dumps(event)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # Never break runtime due to observability.
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
    """Create a normalized event dict."""
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
