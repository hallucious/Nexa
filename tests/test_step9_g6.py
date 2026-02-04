from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, Mock

from src.pipeline.runner import PipelineRunner
from src.pipeline.state import RunMeta, GateId, RunStatus
from src.gates.g1_design import gate_g1_design
from src.gates.g2_continuity import gate_g2_continuity
from src.gates.g3_fact_audit import gate_g3_fact_audit
from src.gates.g4_self_check import gate_g4_self_check
from src.gates.g5_implement_test import gate_g5_implement_and_test
from src.gates.g6_counterfactual import gate_g6_counterfactual_review
from src.gates.mock_gate_v2 import make_contract_pass_gate
from src.utils.time import now_seoul


def test_g6_writes_artifacts(tmp_path: Path):
    # fake repo layout needed by G5 repo_root finder
    repo = tmp_path / "repo"
    runs = repo / "runs"
    baseline = repo / "baseline"
    srcdir = repo / "src"
    testsdir = repo / "tests"
    runs.mkdir(parents=True)
    baseline.mkdir(parents=True)
    srcdir.mkdir()
    testsdir.mkdir()

    run_dir = runs / "2099-01-01_0009"
    run_dir.mkdir()

    (run_dir / "00_USER_REQUEST.md").write_text("Build pipeline\nThis is the best.\n", encoding="utf-8")

    meta = RunMeta(run_id="2099-01-01_0009", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(run_dir))

    runner.register(GateId.G1, gate_g1_design)
    runner.register(GateId.G2, gate_g2_continuity)
    runner.register(GateId.G3, gate_g3_fact_audit)
    runner.register(GateId.G4, gate_g4_self_check)
    runner.register(GateId.G5, gate_g5_implement_and_test)
    runner.register(GateId.G6, gate_g6_counterfactual_review)
    runner.register(GateId.G7, make_contract_pass_gate("G7", "OK"))

    mock_proc = Mock(returncode=0, stdout="ok\n", stderr="")
    with patch("subprocess.run", return_value=mock_proc):
        runner.run()

    assert meta.status == RunStatus.PASS
    assert (run_dir / "G6_DECISION.md").exists()
    assert (run_dir / "G6_OUTPUT.json").exists()
    assert (run_dir / "G6_META.json").exists()

    out = json.loads((run_dir / "G6_OUTPUT.json").read_text(encoding="utf-8"))
    assert out["gate"] == "G6"
    assert "counterfactuals" in out
