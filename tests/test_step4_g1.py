from __future__ import annotations

from pathlib import Path

from src.pipeline.runner import PipelineRunner
from src.pipeline.state import RunMeta, GateId, RunStatus
from src.gates.g1_design import gate_g1_design
from src.gates.mock_gate_v2 import make_contract_pass_gate
from src.utils.time import now_seoul


def test_g1_design_pass(tmp_path: Path):
    # prepare request
    (tmp_path / "00_USER_REQUEST.md").write_text(
        "Build a reliable 7-gate pipeline\nEnsure contracts\n",
        encoding="utf-8",
    )

    meta = RunMeta(run_id="TEST4", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(tmp_path))

    runner.register(GateId.G1, gate_g1_design)
    runner.register(GateId.G2, make_contract_pass_gate("G2", "OK"))
    runner.register(GateId.G3, make_contract_pass_gate("G3", "OK"))
    runner.register(GateId.G4, make_contract_pass_gate("G4", "OK"))
    runner.register(GateId.G5, make_contract_pass_gate("G5", "OK"))
    runner.register(GateId.G6, make_contract_pass_gate("G6", "OK"))
    runner.register(GateId.G7, make_contract_pass_gate("G7", "OK"))

    runner.run()

    assert (tmp_path / "G1_DECISION.md").exists()
    assert (tmp_path / "G1_OUTPUT.json").exists()
    assert (tmp_path / "G1_META.json").exists()
    assert meta.status == RunStatus.PASS
