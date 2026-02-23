from __future__ import annotations

import json
from pathlib import Path

from src.pipeline.runner import PipelineRunner
from src.pipeline.state import RunMeta, GateId, RunStatus
from src.gates.gates_testutils import make_contract_pass_gate
from src.utils.time import now_seoul


def test_runner_writes_meta_json_on_pass(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)

    meta = RunMeta(run_id="TEST_META_JSON", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(run_dir))

    # Register all gates with contract-compliant PASS executors so pipeline reaches DONE.
    runner.register(GateId.G1, make_contract_pass_gate("G1", "OK"))
    runner.register(GateId.G2, make_contract_pass_gate("G2", "OK"))
    runner.register(GateId.G3, make_contract_pass_gate("G3", "OK"))
    runner.register(GateId.G4, make_contract_pass_gate("G4", "OK"))
    runner.register(GateId.G5, make_contract_pass_gate("G5", "OK"))
    runner.register(GateId.G6, make_contract_pass_gate("G6", "OK"))
    runner.register(GateId.G7, make_contract_pass_gate("G7", "OK"))

    runner.run()

    assert meta.status == RunStatus.PASS
    meta_path = run_dir / "META.json"
    assert meta_path.exists()

    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "TEST_META_JSON"
    assert payload["status"] == "PASS"
