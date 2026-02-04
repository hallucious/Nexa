from __future__ import annotations

import json
from pathlib import Path

from src.pipeline.runner import PipelineRunner
from src.pipeline.state import RunMeta, GateId, RunStatus
from src.gates.g1_design import gate_g1_design
from src.gates.g2_continuity import gate_g2_continuity
from src.gates.g3_fact_audit import gate_g3_fact_audit
from src.gates.mock_gate_v2 import make_contract_pass_gate
from src.utils.time import now_seoul


def test_g3_fact_audit_pass(tmp_path: Path):
    # fake repo
    repo = tmp_path / "repo"
    runs = repo / "runs"
    baseline = repo / "baseline"
    runs.mkdir(parents=True)
    baseline.mkdir(parents=True)

    run_dir = runs / "2099-01-01_0003"
    run_dir.mkdir()

    (run_dir / "00_USER_REQUEST.md").write_text(
        "System will ensure contracts.\nDesign is optimal for safety.\n",
        encoding="utf-8",
    )

    meta = RunMeta(run_id="2099-01-01_0003", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(run_dir))

    runner.register(GateId.G1, gate_g1_design)
    runner.register(GateId.G2, gate_g2_continuity)
    runner.register(GateId.G3, gate_g3_fact_audit)
    runner.register(GateId.G4, make_contract_pass_gate("G4", "OK"))
    runner.register(GateId.G5, make_contract_pass_gate("G5", "OK"))
    runner.register(GateId.G6, make_contract_pass_gate("G6", "OK"))
    runner.register(GateId.G7, make_contract_pass_gate("G7", "OK"))

    runner.run()

    assert meta.status == RunStatus.PASS
    out = json.loads((run_dir / "G3_OUTPUT.json").read_text(encoding="utf-8"))
    assert "candidates" in out
    assert "results" in out
