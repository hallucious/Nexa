from __future__ import annotations

import json
from pathlib import Path

from src.pipeline.observability_report import summarize_run


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_step35_observability_report_summary(tmp_path: Path) -> None:
    rows = [
        {"run_id": "R1", "gate": "G1", "decision": "PASS", "execution_time_ms": 10, "provider": "none", "vendor": "none", "source": "G1"},
        {"run_id": "R1", "gate": "G2", "decision": "PASS", "execution_time_ms": 30, "provider": "none", "vendor": "none", "source": "G2"},
        {"run_id": "R1", "gate": "G2", "decision": "STOP", "execution_time_ms": 50, "provider": "none", "vendor": "none", "source": "G2"},
        {"run_id": "R1", "gate": "G3", "decision": "PASS", "execution_time_ms": 20, "provider": "none", "vendor": "none", "source": "G3"},
    ]
    _write_jsonl(tmp_path / "OBSERVABILITY.jsonl", rows)

    s = summarize_run(run_dir=str(tmp_path))
    assert s["events"] == 4
    assert s["pass"] == 3
    assert s["stop"] == 1
    assert s["fail"] == 0
    assert s["total_execution_time_ms"] == 110

    gates = {g["gate"]: g for g in s["gates"]}
    assert gates["G1"]["count"] == 1 and gates["G1"]["avg_ms"] == 10
    assert gates["G2"]["count"] == 2 and gates["G2"]["stop"] == 1
