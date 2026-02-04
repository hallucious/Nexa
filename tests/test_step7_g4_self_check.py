from __future__ import annotations

import json
from pathlib import Path

from src.pipeline.runner import PipelineRunner
from src.pipeline.state import RunMeta, GateId, RunStatus
from src.gates.g1_design import gate_g1_design
from src.gates.g2_continuity import gate_g2_continuity
from src.gates.g3_fact_audit import gate_g3_fact_audit
from src.gates.g4_self_check import gate_g4_self_check
from src.gates.mock_gate_v2 import make_contract_pass_gate
from src.utils.time import now_seoul


def test_g4_self_check_pass(tmp_path: Path):
    # fake repo structure (runs + baseline)
    repo = tmp_path / "repo"
    runs = repo / "runs"
    baseline = repo / "baseline"
    runs.mkdir(parents=True)
    baseline.mkdir(parents=True)

    run_dir = runs / "2099-01-01_0004"
    run_dir.mkdir()

    # request includes a "best" statement -> Gate3 WARN only, not ERROR
    (run_dir / "00_USER_REQUEST.md").write_text(
        "This is the best safe pipeline.\nEnsure contracts must pass.\n",
        encoding="utf-8",
    )

    meta = RunMeta(run_id="2099-01-01_0004", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(run_dir))

    runner.register(GateId.G1, gate_g1_design)
    runner.register(GateId.G2, gate_g2_continuity)
    runner.register(GateId.G3, gate_g3_fact_audit)
    runner.register(GateId.G4, gate_g4_self_check)
    runner.register(GateId.G5, make_contract_pass_gate("G5", "OK"))
    runner.register(GateId.G6, make_contract_pass_gate("G6", "OK"))
    runner.register(GateId.G7, make_contract_pass_gate("G7", "OK"))

    runner.run()

    assert meta.status == RunStatus.PASS
    assert (run_dir / "G4_DECISION.md").exists()
    assert (run_dir / "G4_OUTPUT.json").exists()
    assert (run_dir / "G4_META.json").exists()

    out = json.loads((run_dir / "G4_OUTPUT.json").read_text(encoding="utf-8"))
    assert out["gate"] == "G4"
    assert "checks" in out
