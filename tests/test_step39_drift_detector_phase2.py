from __future__ import annotations

import json
from pathlib import Path

from src.pipeline.drift_detector import run_drift_detector


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def test_step39_phase2_soft_drift_trace_only(tmp_path: Path) -> None:
    baseline = tmp_path / "runs" / "BASE"
    current = tmp_path / "runs" / "CURR"
    baseline.mkdir(parents=True)
    current.mkdir(parents=True)

    _write_jsonl(
        baseline / "OBSERVABILITY.jsonl",
        [
            {"gate": "G1", "decision": "PASS", "reason_code": "SUCCESS", "reason_trace": ["a=1"]},
        ],
    )
    _write_jsonl(
        current / "OBSERVABILITY.jsonl",
        [
            {"gate": "G1", "decision": "PASS", "reason_code": "SUCCESS", "reason_trace": ["a=2"]},
        ],
    )

    report = run_drift_detector(
        baseline_run_dir=baseline,
        current_run_dir=current,
        baseline_id="BASE",
        current_id="CURR",
    )
    assert report is not None
    assert len(report.hard_drift) == 0
    assert len(report.soft_drift) == 1
    assert report.soft_drift[0].gate_id == "G1"

    out = json.loads((current / "DRIFT_REPORT.json").read_text(encoding="utf-8"))
    assert out["baseline_id"] == "BASE"
    assert out["current_id"] == "CURR"
    assert len(out["hard_drift"]) == 0
    assert len(out["soft_drift"]) == 1
    assert out["soft_drift"][0]["gate_id"] == "G1"


def test_step39_phase2_hard_drift_reason_code_change(tmp_path: Path) -> None:
    baseline = tmp_path / "runs" / "BASE"
    current = tmp_path / "runs" / "CURR"
    baseline.mkdir(parents=True)
    current.mkdir(parents=True)

    _write_jsonl(
        baseline / "OBSERVABILITY.jsonl",
        [
            {"gate": "G2", "decision": "PASS", "reason_code": "SUCCESS", "reason_trace": ["x=1"]},
        ],
    )
    _write_jsonl(
        current / "OBSERVABILITY.jsonl",
        [
            {"gate": "G2", "decision": "PASS", "reason_code": "DIFFERENT", "reason_trace": ["x=1"]},
        ],
    )

    report = run_drift_detector(
        baseline_run_dir=baseline,
        current_run_dir=current,
        baseline_id="BASE",
        current_id="CURR",
    )
    assert report is not None
    assert len(report.hard_drift) == 1
    assert len(report.soft_drift) == 0
    assert report.hard_drift[0].gate_id == "G2"

    out = json.loads((current / "DRIFT_REPORT.json").read_text(encoding="utf-8"))
    assert len(out["hard_drift"]) == 1
    assert out["hard_drift"][0]["gate_id"] == "G2"


def test_step39_phase2_skips_when_baseline_missing(tmp_path: Path) -> None:
    baseline = tmp_path / "runs" / "BASE"
    current = tmp_path / "runs" / "CURR"
    current.mkdir(parents=True)

    report = run_drift_detector(
        baseline_run_dir=baseline,
        current_run_dir=current,
        baseline_id="BASE",
        current_id="CURR",
    )
    assert report is None
    assert not (current / "DRIFT_REPORT.json").exists()
