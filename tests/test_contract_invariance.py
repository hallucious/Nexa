
from __future__ import annotations

from pathlib import Path

from src.pipeline.runner import PipelineRunner, GateContext
from src.pipeline.state import RunMeta, GateId, RunStatus
from src.models.decision_models import GateResult, Decision
from src.utils.time import now_seoul


def broken_gate_missing_outputs(gate_prefix: str):
    """Gate that violates artifact contract by returning empty outputs."""

    def _exec(ctx: GateContext) -> GateResult:
        return GateResult(decision=Decision.PASS, message=gate_prefix, outputs={})

    return _exec


def test_contract_invariance_broken_gate_causes_stop(tmp_path: Path):
    """Stable Core invariant: contract break must not silently pass; it must STOP safely."""

    meta = RunMeta(run_id="TEST_CONTRACT_BREAK", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(tmp_path))

    runner.register(GateId.G1, broken_gate_missing_outputs("G1"))

    runner.run()

    assert meta.status == RunStatus.STOP
    assert meta.current_gate == GateId.STOP
    # Standardized STOP enum must be used
    assert meta.stop_reason == "INTERNAL_ERROR"
