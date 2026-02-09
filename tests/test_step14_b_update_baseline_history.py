# tests/test_step14_b_update_baseline_history.py
from __future__ import annotations

import json
from pathlib import Path

from scripts.update_baseline import main as update_main


def test_update_baseline_writes_diff_and_history(tmp_path: Path, monkeypatch):
    # repo layout
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)
    (repo / "runs").mkdir(parents=True)
    (repo / "baseline").mkdir(parents=True)

    run_dir = repo / "runs" / "2099-01-01_9999"
    run_dir.mkdir(parents=True)

    # seed a run G1 output
    (run_dir / "G1_OUTPUT.json").write_text(
        json.dumps({"summary": "new", "interfaces": ["a"], "extra": {"k": 1}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # optional PIC
    (run_dir / "PIC.md").write_text("PIC text", encoding="utf-8")

    # seed an old baseline to force a diff
    (repo / "baseline" / "BASELINE_G1_OUTPUT.json").write_text(
        json.dumps({"summary": "old", "interfaces": ["a"], "old_only": True}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # run in repo root
    monkeypatch.chdir(repo)

    # execute update (promote pic too)
    rc = update_main(["--run-id", "2099-01-01_9999", "--promote-pic", "--note", "test"])
    assert rc == 0

    # baseline files exist
    assert (repo / "baseline" / "BASELINE_G1_OUTPUT.json").exists()
    assert (repo / "baseline" / "PIC.md").exists()
    assert (repo / "baseline" / "BASELINE_PROMOTION_LOG.json").exists()
    assert (repo / "baseline" / "BASELINE_LAST_DIFF.json").exists()
    assert (repo / "baseline" / "BASELINE_HISTORY.jsonl").exists()
    assert (repo / "baseline" / "BASELINE_HISTORY.md").exists()

    # diff schema
    diff_obj = json.loads((repo / "baseline" / "BASELINE_LAST_DIFF.json").read_text(encoding="utf-8"))
    assert "diff" in diff_obj
    assert "diff_summary" in diff_obj
    assert set(diff_obj["diff_summary"].keys()) == {"added", "removed", "changed"}

    # history has at least one entry, and includes note + summary
    lines = (repo / "baseline" / "BASELINE_HISTORY.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 1
    last = json.loads(lines[-1])
    assert last["promoted_from_run"] == "2099-01-01_9999"
    assert last["promote_pic"] is True
    assert last["note"] == "test"
    assert "diff_summary" in last
    assert set(last["diff_summary"].keys()) == {"added", "removed", "changed"}

    # history md is readable and includes the run id
    md = (repo / "baseline" / "BASELINE_HISTORY.md").read_text(encoding="utf-8")
    assert "BASELINE HISTORY" in md
    assert "2099-01-01_9999" in md
