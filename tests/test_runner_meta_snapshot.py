from __future__ import annotations

import json
from pathlib import Path

from src.pipeline.runner import PipelineRunner
from src.pipeline.state import RunMeta, GateId, RunStatus
from src.gates.gates_testutils import make_contract_pass_gate
from src.utils.time import now_seoul


def test_runner_final_meta_status_snapshot(tmp_path: Path):
    """
    Contract test (lightweight "snapshot"):
    - Runner must produce META.json
    - Final meta.status must be a valid terminal value
    - For an all-PASS pipeline, final status must be PASS
    """
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)

    meta = RunMeta(run_id="TEST_RUNNER_META_STATUS", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(run_dir))

    # Register contract-compliant PASS gates so the pipeline deterministically reaches PASS.
    runner.register(GateId.G1, make_contract_pass_gate("G1", "OK"))
    runner.register(GateId.G2, make_contract_pass_gate("G2", "OK"))
    runner.register(GateId.G3, make_contract_pass_gate("G3", "OK"))
    runner.register(GateId.G4, make_contract_pass_gate("G4", "OK"))
    runner.register(GateId.G5, make_contract_pass_gate("G5", "OK"))
    runner.register(GateId.G6, make_contract_pass_gate("G6", "OK"))
    runner.register(GateId.G7, make_contract_pass_gate("G7", "OK"))

    runner.run()

    # In-memory meta must be terminal and PASS for this all-PASS run.
    assert meta.status == RunStatus.PASS

    # Runner must persist META.json
    meta_path = run_dir / "META.json"
    assert meta_path.exists(), "Runner must write META.json"

    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
