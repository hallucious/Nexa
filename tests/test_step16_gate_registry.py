from pathlib import Path

from src.pipeline.runner import PipelineRunner
from src.pipeline.state import RunMeta, GateId
from src.utils.time import now_seoul
from src.models.decision_models import GateResult, Decision


def _dummy_gate(ctx):
    return GateResult(decision=Decision.PASS, outputs={"ok": True}, meta={})


def test_gate_registry_introspection(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    meta = RunMeta(run_id="TEST_REGISTRY", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(run_dir))

    runner.register(GateId.G1, _dummy_gate)
    snapshot = runner.registered_gates()

    assert "G1" in snapshot
    assert snapshot["G1"] == "_dummy_gate"