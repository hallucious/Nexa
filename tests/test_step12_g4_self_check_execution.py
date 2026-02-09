from __future__ import annotations

import json
from pathlib import Path

from src.gates.g4_self_check import gate_g4_self_check
from src.pipeline.runner import PipelineRunner
from src.pipeline.state import GateId, RunMeta, RunStatus
from src.utils.time import now_seoul

from src.gates.g1_design import gate_g1_design
from src.gates.g2_continuity import gate_g2_continuity
from src.gates.g3_fact_audit import gate_g3_fact_audit
from src.gates.gates_testutils import make_contract_pass_gate


def test_g4_writes_artifacts_and_execution_plan(tmp_path: Path):
    # fake repo structure
    repo = tmp_path / "repo"
    runs = repo / "runs"
    baseline = repo / "baseline"
    runs.mkdir(parents=True)
    baseline.mkdir(parents=True)

    run_dir = runs / "2099-01-01_0012"
    run_dir.mkdir()

    (run_dir / "00_USER_REQUEST.md").write_text("Build pipeline\n", encoding="utf-8")

    meta = RunMeta(run_id="2099-01-01_0012", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(run_dir))

    runner.register(GateId.G1, gate_g1_design)
    runner.register(GateId.G2, gate_g2_continuity)
    runner.register(GateId.G3, gate_g3_fact_audit)
    runner.register(GateId.G4, gate_g4_self_check)
    runner.register(GateId.G5, make_contract_pass_gate("G5", "OK"))
    runner.register(GateId.G6, make_contract_pass_gate("G6", "OK"))
    runner.register(GateId.G7, make_contract_pass_gate("G7", "OK"))

    runner.run()

    # G4 artifacts exist
    assert (run_dir / "G4_DECISION.md").exists()
    assert (run_dir / "G4_META.json").exists()
    assert (run_dir / "G4_OUTPUT.json").exists()

    decision_md = (run_dir / "G4_DECISION.md").read_text(encoding="utf-8")
    assert "## G5 Execution instructions" in decision_md
    assert "python -m pytest -q" in decision_md

    out = json.loads((run_dir / "G4_OUTPUT.json").read_text(encoding="utf-8"))
    assert "execution_plan_md" in out
    assert "python -m pytest -q" in out["execution_plan_md"]

    assert meta.status in (RunStatus.PASS, RunStatus.FAIL, RunStatus.STOP)


def test_g4_fail_when_prereq_missing(tmp_path: Path):
    # direct call with missing upstream artifacts -> should FAIL
    repo = tmp_path / "repo"
    runs = repo / "runs"
    baseline = repo / "baseline"
    runs.mkdir(parents=True)
    baseline.mkdir(parents=True)

    run_dir = runs / "2099-01-01_0013"
    run_dir.mkdir()
    (run_dir / "00_USER_REQUEST.md").write_text("Build pipeline\n", encoding="utf-8")

    meta = RunMeta(run_id="2099-01-01_0013", created_at=now_seoul().isoformat())
    ctx = type("Ctx", (), {"meta": meta, "run_dir": str(run_dir)})  # minimal GateContext shape

    res = gate_g4_self_check(ctx)  # type: ignore
    assert res.decision.value == "FAIL"
    md = (run_dir / "G4_DECISION.md").read_text(encoding="utf-8")
    assert "Upstream artifacts missing" in md
