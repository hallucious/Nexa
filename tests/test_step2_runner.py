from __future__ import annotations

from src.pipeline.runner import PipelineRunner
from src.pipeline.state import RunMeta, GateId, RunStatus
from src.gates.mock_gate_v2 import make_contract_pass_gate
from src.utils.time import now_seoul


def test_full_pass_pipeline(tmp_path):
    meta = RunMeta(run_id="TEST", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(tmp_path))

    runner.register(GateId.G1, make_contract_pass_gate("G1", "G1"))
    runner.register(GateId.G2, make_contract_pass_gate("G2", "G2"))
    runner.register(GateId.G3, make_contract_pass_gate("G3", "G3"))
    runner.register(GateId.G4, make_contract_pass_gate("G4", "G4"))
    runner.register(GateId.G5, make_contract_pass_gate("G5", "G5"))
    runner.register(GateId.G6, make_contract_pass_gate("G6", "G6"))
    runner.register(GateId.G7, make_contract_pass_gate("G7", "G7"))

    runner.run()

    assert meta.status == RunStatus.PASS
    assert meta.current_gate == GateId.DONE
    assert len(meta.transitions) == 7
