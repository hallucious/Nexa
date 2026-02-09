# tests/test_step11_3_g2_pic_priority.py
from __future__ import annotations

import json
from pathlib import Path

from src.pipeline.state import RunMeta, GateId
from src.pipeline.runner import PipelineRunner
from src.gates.g1_design import gate_g1_design
from src.gates.g2_continuity import gate_g2_continuity
from src.gates.gates_testutils import make_contract_pass_gate
from src.utils.time import now_seoul


def test_g2_pic_priority_prefers_baseline_pic_over_baseline_packet(tmp_path: Path):
    # Fake repo structure
    repo = tmp_path / "repo"
    runs = repo / "runs"
    baseline = repo / "baseline"
    runs.mkdir(parents=True)
    baseline.mkdir(parents=True)

    # Both exist; baseline/PIC.md must win
    (baseline / "PIC.md").write_text("PIC CANON\n", encoding="utf-8")
    (baseline / "BASELINE_PACKET.md").write_text("LEGACY PACKET\n", encoding="utf-8")

    run_dir = runs / "2099-01-01_0011"
    run_dir.mkdir()

    (run_dir / "00_USER_REQUEST.md").write_text("Build pipeline\n", encoding="utf-8")

    meta = RunMeta(run_id="2099-01-01_0011", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(run_dir))

    runner.register(GateId.G1, gate_g1_design)
    runner.register(GateId.G2, gate_g2_continuity)
    runner.register(GateId.G3, make_contract_pass_gate("G3", "OK"))
    runner.register(GateId.G4, make_contract_pass_gate("G4", "OK"))
    runner.register(GateId.G5, make_contract_pass_gate("G5", "OK"))
    runner.register(GateId.G6, make_contract_pass_gate("G6", "OK"))
    runner.register(GateId.G7, make_contract_pass_gate("G7", "OK"))

    runner.run()

    out = json.loads((run_dir / "G2_OUTPUT.json").read_text(encoding="utf-8"))
    assert out["semantic"]["pic_source"] == "baseline/PIC.md"
