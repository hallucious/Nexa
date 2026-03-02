from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.pipeline.observability import append_observability_event
from src.pipeline.policy_diff import GatePolicySnapshot, diff_policy_between_runs


@dataclass(frozen=True)
class DriftEntry:
    gate_id: str
    from_snapshot: GatePolicySnapshot
    to_snapshot: GatePolicySnapshot


@dataclass(frozen=True)
class DriftReport:
    baseline_id: str
    current_id: str
    hard_drift: List[DriftEntry]
    soft_drift: List[DriftEntry]


def _snapshot_to_dict(s: GatePolicySnapshot) -> Dict[str, Any]:
    # Explicit key ordering for determinism (insertion order preserved).
    return {
        "gate_id": s.gate,
        "decision": s.decision,
        "reason_code": s.reason_code,
        "reason_trace": list(s.reason_trace),
    }


def _entry_to_dict(e: DriftEntry) -> Dict[str, Any]:
    return {
        "gate_id": e.gate_id,
        "from": _snapshot_to_dict(e.from_snapshot),
        "to": _snapshot_to_dict(e.to_snapshot),
    }


def _write_drift_report_json(*, path: Path, report: DriftReport) -> None:
    # Deterministic structure: explicit dict construction + stable ordering upstream.
    obj: Dict[str, Any] = {
        "baseline_id": report.baseline_id,
        "current_id": report.current_id,
        "hard_drift": [_entry_to_dict(e) for e in report.hard_drift],
        "soft_drift": [_entry_to_dict(e) for e in report.soft_drift],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, ensure_ascii=False, indent=2)
    path.write_text(data + "\n", encoding="utf-8")


def run_drift_detector(
    *,
    baseline_run_dir: Path,
    current_run_dir: Path,
    baseline_id: str,
    current_id: str,
) -> Optional[DriftReport]:
    """Run baseline drift detection and write artifacts.

    Side effects (best-effort, exceptions handled by caller in CLI):
    - writes DRIFT_REPORT.json under current_run_dir
    - appends DRIFT_DETECTED event to current OBSERVABILITY.jsonl

    Returns DriftReport if baseline exists and diff was computed, else None.
    """

    if not baseline_run_dir.exists():
        return None

    diff = diff_policy_between_runs(run_dir_a=baseline_run_dir, run_dir_b=current_run_dir)
    changed = diff.changed_gates

    hard: List[DriftEntry] = []
    soft: List[DriftEntry] = []

    # Deterministic ordering: policy_diff already sorts gates; keep order.
    for d in changed:
        # Hard drift if decision or reason_code changed; trace-only => soft.
        if (d.a.decision != d.b.decision) or (d.a.reason_code != d.b.reason_code):
            hard.append(DriftEntry(gate_id=d.gate, from_snapshot=d.a, to_snapshot=d.b))
        else:
            soft.append(DriftEntry(gate_id=d.gate, from_snapshot=d.a, to_snapshot=d.b))

    report = DriftReport(
        baseline_id=baseline_id,
        current_id=current_id,
        hard_drift=hard,
        soft_drift=soft,
    )

    _write_drift_report_json(path=current_run_dir / "DRIFT_REPORT.json", report=report)

    append_observability_event(
        run_dir=str(current_run_dir),
        event={
            "event": "DRIFT_DETECTED",
            "baseline_id": baseline_id,
            "current_id": current_id,
            "hard_count": len(hard),
            "soft_count": len(soft),
        },
    )

    return report
