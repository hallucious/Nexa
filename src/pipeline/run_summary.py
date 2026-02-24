from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.pipeline.state import RunMeta


def write_run_summary(*, run_dir: str, meta: RunMeta, gate_summaries: List[Dict[str, Any]]) -> str:
    """Write run-level summary artifact.

    Contract:
    - Additive only: does not affect existing artifacts.
    - Always writes RUN_SUMMARY.json (best-effort).
    """
    out_path = Path(run_dir) / "RUN_SUMMARY.json"

    gates: List[Dict[str, Any]] = []
    for g in gate_summaries or []:
        if not isinstance(g, dict):
            continue
        gates.append(
            {
                "gate": g.get("gate"),
                "decision": g.get("decision"),
                "reason_code": g.get("reason_code"),
            }
        )

    payload: Dict[str, Any] = {
        "run_id": getattr(meta, "run_id", None),
        "final_status": getattr(meta, "status", None).value if getattr(getattr(meta, "status", None), "value", None) else str(getattr(meta, "status", "")),
        "gates": gates,
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out_path.name)
