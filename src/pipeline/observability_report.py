from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


OBS_FILE_NAME = "OBSERVABILITY.jsonl"


@dataclass(frozen=True)
class GateAgg:
    gate: str
    count: int
    pass_count: int
    stop_count: int
    fail_count: int
    avg_ms: float
    p95_ms: float


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def read_events(*, run_dir: str) -> List[Dict[str, Any]]:
    """Read run_dir/OBSERVABILITY.jsonl as a list of dict events.

    Best-effort: returns [] if missing/unreadable.
    """
    try:
        path = Path(run_dir) / OBS_FILE_NAME
        if not path.exists():
            return []
        out: List[Dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                out.append(obj)
        return out
    except Exception:
        return []


def _pct(num: int, den: int) -> float:
    if den <= 0:
        return 0.0
    return (num / den) * 100.0


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    vs = sorted(values)
    if len(vs) == 1:
        return float(vs[0])
    # nearest-rank percentile
    k = int(round((p / 100.0) * (len(vs) - 1)))
    k = max(0, min(k, len(vs) - 1))
    return float(vs[k])


def aggregate_by_gate(events: Iterable[Dict[str, Any]]) -> List[GateAgg]:
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for ev in events:
        gate = str(ev.get("gate") or "")
        if not gate:
            continue
        buckets.setdefault(gate, []).append(ev)

    aggs: List[GateAgg] = []
    for gate, evs in sorted(buckets.items(), key=lambda kv: kv[0]):
        ms_vals = [_safe_float(e.get("execution_time_ms"), 0.0) for e in evs]
        count = len(evs)
        decisions = [str(e.get("decision") or "") for e in evs]
        pass_count = sum(1 for d in decisions if d.upper() == "PASS")
        stop_count = sum(1 for d in decisions if d.upper() == "STOP")
        fail_count = count - pass_count - stop_count
        avg_ms = sum(ms_vals) / count if count else 0.0
        p95_ms = _percentile(ms_vals, 95.0)
        aggs.append(
            GateAgg(
                gate=gate,
                count=count,
                pass_count=pass_count,
                stop_count=stop_count,
                fail_count=fail_count,
                avg_ms=avg_ms,
                p95_ms=p95_ms,
            )
        )
    return aggs


def summarize_run(*, run_dir: str) -> Dict[str, Any]:
    """Return a compact summary dict for a run_dir."""
    events = read_events(run_dir=run_dir)
    total = len(events)
    by_gate = aggregate_by_gate(events)

    pass_total = sum(a.pass_count for a in by_gate)
    stop_total = sum(a.stop_count for a in by_gate)
    fail_total = sum(a.fail_count for a in by_gate)

    total_ms_vals = [_safe_float(e.get("execution_time_ms"), 0.0) for e in events]
    total_time_ms = int(sum(total_ms_vals)) if total_ms_vals else 0

    return {
        "run_dir": str(run_dir),
        "events": total,
        "pass": pass_total,
        "stop": stop_total,
        "fail": fail_total,
        "pass_rate_pct": _pct(pass_total, total),
        "stop_rate_pct": _pct(stop_total, total),
        "fail_rate_pct": _pct(fail_total, total),
        "total_execution_time_ms": total_time_ms,
        "gates": [
            {
                "gate": a.gate,
                "count": a.count,
                "pass": a.pass_count,
                "stop": a.stop_count,
                "fail": a.fail_count,
                "avg_ms": round(a.avg_ms, 2),
                "p95_ms": round(a.p95_ms, 2),
            }
            for a in by_gate
        ],
    }
