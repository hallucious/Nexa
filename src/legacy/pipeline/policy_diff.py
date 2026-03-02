from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


OBS_FILE_NAME = "OBSERVABILITY.jsonl"


@dataclass
class GatePolicySnapshot:
    """Best-effort snapshot of the policy-related fields for a gate."""

    gate: str
    decision: Optional[str]
    reason_code: Optional[str]
    reason_trace: List[str]


@dataclass
class GatePolicyDelta:
    gate: str
    a: GatePolicySnapshot
    b: GatePolicySnapshot

    @property
    def changed(self) -> bool:
        return (
            (self.a.decision != self.b.decision)
            or (self.a.reason_code != self.b.reason_code)
            or (self.a.reason_trace != self.b.reason_trace)
        )


@dataclass
class PolicyDiffReport:
    deltas: List[GatePolicyDelta]

    @property
    def changed_gates(self) -> List[GatePolicyDelta]:
        return [d for d in self.deltas if d.changed]

    @property
    def unchanged_gates(self) -> List[GatePolicyDelta]:
        return [d for d in self.deltas if not d.changed]


def _safe_json_loads(line: str) -> Optional[Dict[str, Any]]:
    try:
        obj = json.loads(line)
        if isinstance(obj, dict):
            return obj
        return None
    except Exception:
        return None


def read_observability_jsonl(*, run_dir: Path) -> List[Dict[str, Any]]:
    """Read <run_dir>/OBSERVABILITY.jsonl into list[dict]. Best-effort."""

    path = run_dir / OBS_FILE_NAME
    if not path.exists():
        return []

    events: List[Dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        obj = _safe_json_loads(raw)
        if obj is not None:
            events.append(obj)
    return events


def _extract_snapshot_from_event(event: Dict[str, Any]) -> Optional[GatePolicySnapshot]:
    gate = event.get("gate")
    if not isinstance(gate, str) or not gate.strip():
        return None

    decision = event.get("decision")
    if decision is not None and not isinstance(decision, str):
        decision = None

    reason_code = event.get("reason_code")
    if reason_code is not None and not isinstance(reason_code, str):
        reason_code = None

    reason_trace_raw = event.get("reason_trace")
    reason_trace: List[str] = []
    if isinstance(reason_trace_raw, list):
        for x in reason_trace_raw:
            if isinstance(x, str):
                reason_trace.append(x)

    return GatePolicySnapshot(
        gate=gate,
        decision=decision,
        reason_code=reason_code,
        reason_trace=reason_trace,
    )


def latest_policy_snapshots_by_gate(events: Iterable[Dict[str, Any]]) -> Dict[str, GatePolicySnapshot]:
    """Collapse events into the last-seen policy snapshot per gate."""

    out: Dict[str, GatePolicySnapshot] = {}
    for ev in events:
        snap = _extract_snapshot_from_event(ev)
        if snap is None:
            continue
        out[snap.gate] = snap
    return out


def diff_policy_between_runs(*, run_dir_a: Path, run_dir_b: Path) -> PolicyDiffReport:
    """Compute policy deltas between two runs.

    Inputs are run directories (the folders containing OBSERVABILITY.jsonl).
    """

    a_events = read_observability_jsonl(run_dir=run_dir_a)
    b_events = read_observability_jsonl(run_dir=run_dir_b)
    a_map = latest_policy_snapshots_by_gate(a_events)
    b_map = latest_policy_snapshots_by_gate(b_events)

    all_gates = sorted(set(a_map.keys()) | set(b_map.keys()))
    deltas: List[GatePolicyDelta] = []
    for gate in all_gates:
        a = a_map.get(gate) or GatePolicySnapshot(gate=gate, decision=None, reason_code=None, reason_trace=[])
        b = b_map.get(gate) or GatePolicySnapshot(gate=gate, decision=None, reason_code=None, reason_trace=[])
        deltas.append(GatePolicyDelta(gate=gate, a=a, b=b))

    return PolicyDiffReport(deltas=deltas)
