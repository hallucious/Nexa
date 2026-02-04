from __future__ import annotations

import json
from pathlib import Path

from src.pipeline.runner import PipelineRunner
from src.pipeline.state import RunMeta, GateId, RunStatus
from src.gates.g1_design import gate_g1_design
from src.gates.g2_continuity import gate_g2_continuity
from src.gates.mock_gate_v2 import make_contract_pass_gate
from src.utils.time import now_seoul


def test_g2_pass_when_no_baseline(tmp_path: Path):
    # Fake repo structure
    repo = tmp_path / "repo"
    runs = repo / "runs"
    baseline = repo / "baseline"
    runs.mkdir(parents=True)
    baseline.mkdir(parents=True)

    run_dir = runs / "2099-01-01_0001"
    run_dir.mkdir()

    # request for G1
    (run_dir / "00_USER_REQUEST.md").write_text("Build pipeline\n", encoding="utf-8")

    meta = RunMeta(run_id="2099-01-01_0001", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(run_dir))

    runner.register(GateId.G1, gate_g1_design)
    runner.register(GateId.G2, gate_g2_continuity)
    runner.register(GateId.G3, make_contract_pass_gate("G3", "OK"))
    runner.register(GateId.G4, make_contract_pass_gate("G4", "OK"))
    runner.register(GateId.G5, make_contract_pass_gate("G5", "OK"))
    runner.register(GateId.G6, make_contract_pass_gate("G6", "OK"))
    runner.register(GateId.G7, make_contract_pass_gate("G7", "OK"))

    runner.run()

    assert meta.status == RunStatus.PASS
    assert (run_dir / "G2_DECISION.md").exists()
    assert (run_dir / "G2_OUTPUT.json").exists()
    assert (run_dir / "G2_META.json").exists()

    out = json.loads((run_dir / "G2_OUTPUT.json").read_text(encoding="utf-8"))
    assert out["baseline_present"] is False


def test_g2_fail_on_removed_fields_vs_baseline(tmp_path: Path):
    # Fake repo structure
    repo = tmp_path / "repo"
    runs = repo / "runs"
    baseline = repo / "baseline"
    runs.mkdir(parents=True)
    baseline.mkdir(parents=True)

    # Baseline has a field that current will not have
    (baseline / "BASELINE_G1_OUTPUT.json").write_text(
        json.dumps(
            {
                "summary": "baseline",
                "interfaces": ["a"],
                "constraints": ["c"],
                "acceptance_criteria": ["x"],
                "extra_field": {"nested": 1},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    run_dir = runs / "2099-01-01_0002"
    run_dir.mkdir()

    # request for G1
    (run_dir / "00_USER_REQUEST.md").write_text("Build pipeline\n", encoding="utf-8")

    meta = RunMeta(run_id="2099-01-01_0002", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(run_dir))

    runner.register(GateId.G1, gate_g1_design)
    runner.register(GateId.G2, gate_g2_continuity)
    runner.register(GateId.G3, make_contract_pass_gate("G3", "OK"))
    runner.register(GateId.G4, make_contract_pass_gate("G4", "OK"))
    runner.register(GateId.G5, make_contract_pass_gate("G5", "OK"))
    runner.register(GateId.G6, make_contract_pass_gate("G6", "OK"))
    runner.register(GateId.G7, make_contract_pass_gate("G7", "OK"))

    runner.run()

    # Gate2 should FAIL due to removed baseline field(s), but pipeline continues by state machine rule (G2 FAIL -> G1)
    # Final status depends on subsequent passes; we only assert Gate2 output indicates removed fields and FAIL decision file.
    decision = (run_dir / "G2_DECISION.md").read_text(encoding="utf-8")
    assert "Decision: FAIL" in decision
