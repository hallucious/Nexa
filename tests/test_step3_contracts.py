from __future__ import annotations

from pathlib import Path

from src.pipeline.runner import PipelineRunner
from src.pipeline.state import RunMeta, GateId, RunStatus
from src.gates.mock_gate_v2 import make_contract_pass_gate
from src.utils.time import now_seoul


def test_contract_enforced(tmp_path: Path):
    meta = RunMeta(run_id="TEST3", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(tmp_path))

    runner.register(GateId.G1, make_contract_pass_gate("G1", "OK"))
    runner.register(GateId.G2, make_contract_pass_gate("G2", "OK"))
    runner.register(GateId.G3, make_contract_pass_gate("G3", "OK"))
    runner.register(GateId.G4, make_contract_pass_gate("G4", "OK"))
    runner.register(GateId.G5, make_contract_pass_gate("G5", "OK"))
    runner.register(GateId.G6, make_contract_pass_gate("G6", "OK"))
    runner.register(GateId.G7, make_contract_pass_gate("G7", "OK"))

    runner.run()

    assert meta.status == RunStatus.PASS
    for g in ["G1", "G2", "G3", "G4", "G5", "G6", "G7"]:
        assert (tmp_path / f"{g}_DECISION.md").exists()
        assert (tmp_path / f"{g}_OUTPUT.json").exists()
        assert (tmp_path / f"{g}_META.json").exists()
