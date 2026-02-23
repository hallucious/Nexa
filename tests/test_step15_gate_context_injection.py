from __future__ import annotations

from src.pipeline.runner import PipelineRunner, GateContext
from src.pipeline.state import RunMeta, GateId, RunStatus
from src.models.decision_models import GateResult, Decision
from src.gates.mock_gate_v2 import make_contract_pass_gate
from src.utils.time import now_seoul


def test_gate_context_is_injected_and_shared(tmp_path):
    """GateContext.context should be available to gates and shared across steps."""

    meta = RunMeta(run_id="TEST_CTX", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(tmp_path), context={"k": "v"})

    def g1(ctx: GateContext) -> GateResult:
        assert ctx.context["k"] == "v"
        # mutate to verify shared-ness
        ctx.context["x"] = 1
        return make_contract_pass_gate("G1", "ok")(ctx)

    def g2(ctx: GateContext) -> GateResult:
        assert ctx.context["k"] == "v"
        assert ctx.context["x"] == 1
        return make_contract_pass_gate("G2", "ok")(ctx)

    # Remaining gates: contract-valid passes.
    g3 = make_contract_pass_gate("G3", "ok")
    g4 = make_contract_pass_gate("G4", "ok")
    g5 = make_contract_pass_gate("G5", "ok")
    g6 = make_contract_pass_gate("G6", "ok")
    g7 = make_contract_pass_gate("G7", "ok")

    runner.register(GateId.G1, g1)
    runner.register(GateId.G2, g2)
    runner.register(GateId.G3, g3)
    runner.register(GateId.G4, g4)
    runner.register(GateId.G5, g5)
    runner.register(GateId.G6, g6)
    runner.register(GateId.G7, g7)

    runner.run()

    assert meta.status == RunStatus.PASS
