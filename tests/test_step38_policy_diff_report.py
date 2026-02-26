from __future__ import annotations

import json
from pathlib import Path

from src.pipeline.policy_diff import diff_policy_between_runs


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def test_step38_policy_diff_detects_changed_gate(tmp_path: Path) -> None:
    run_a = tmp_path / "run_a"
    run_b = tmp_path / "run_b"

    _write_jsonl(
        run_a / "OBSERVABILITY.jsonl",
        [
            {"run_id": "A", "gate": "G1", "decision": "PASS", "reason_code": "SUCCESS", "reason_trace": ["x=1"]},
            {"run_id": "A", "gate": "G2", "decision": "PASS", "reason_code": "SUCCESS", "reason_trace": ["y=1"]},
        ],
    )
    _write_jsonl(
        run_b / "OBSERVABILITY.jsonl",
        [
            {"run_id": "B", "gate": "G1", "decision": "PASS", "reason_code": "SUCCESS", "reason_trace": ["x=1"]},
            {"run_id": "B", "gate": "G2", "decision": "REJECT", "reason_code": "POLICY_REJECTED", "reason_trace": ["y=2", "branch=REJECT"]},
        ],
    )

    report = diff_policy_between_runs(run_dir_a=run_a, run_dir_b=run_b)
    changed = [d.gate for d in report.changed_gates]
    assert changed == ["G2"]


def test_step38_policy_diff_handles_missing_obs_file(tmp_path: Path) -> None:
    run_a = tmp_path / "run_a"
    run_b = tmp_path / "run_b"
    run_a.mkdir(parents=True)
    run_b.mkdir(parents=True)

    report = diff_policy_between_runs(run_dir_a=run_a, run_dir_b=run_b)
    assert report.deltas == []
