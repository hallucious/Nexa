from __future__ import annotations

import json
from pathlib import Path

from src.pipeline.runner import PipelineRunner, GateContext
from src.pipeline.state import RunMeta, GateId, RunStatus
from src.models.decision_models import GateResult, Decision
from src.pipeline.contracts import standard_spec
from src.utils.time import now_seoul


def _write_standard_artifacts(run_dir: Path, gate_prefix: str, decision_str: str = "PASS") -> dict[str, str]:
    spec = standard_spec(gate_prefix)

    (run_dir / f"{gate_prefix}_DECISION.md").write_text(
        f"# {gate_prefix} DECISION\n\n{decision_str}\n", encoding="utf-8"
    )
    (run_dir / f"{gate_prefix}_OUTPUT.json").write_text(
        json.dumps({"gate": gate_prefix}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / f"{gate_prefix}_META.json").write_text(
        json.dumps(
            {"gate": gate_prefix, "decision": decision_str, "at": now_seoul().isoformat()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    outputs = {
        f"{gate_prefix}_DECISION.md": f"{gate_prefix}_DECISION.md",
        f"{gate_prefix}_OUTPUT.json": f"{gate_prefix}_OUTPUT.json",
        f"{gate_prefix}_META.json": f"{gate_prefix}_META.json",
    }
    spec.validate(outputs)
    return outputs


def make_contract_gate(gate_prefix: str, decision: Decision) -> callable:
    def _exec(ctx: GateContext) -> GateResult:
        outputs = _write_standard_artifacts(Path(ctx.run_dir), gate_prefix, decision.value)
        return GateResult(decision=decision, message=gate_prefix, outputs=outputs, meta={})
    return _exec


def test_observability_meta_fields_exist(tmp_path: Path):
    """Stable Core invariant: observability fields must be persisted into per-gate META.json."""

    meta = RunMeta(run_id="TEST_OBS_META", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(tmp_path))

    # Register minimal contract gates to ensure artifacts exist.
    runner.register(GateId.G1, make_contract_gate("G1", Decision.PASS))
    runner.register(GateId.G2, make_contract_gate("G2", Decision.PASS))
    runner.register(GateId.G3, make_contract_gate("G3", Decision.PASS))
    runner.register(GateId.G4, make_contract_gate("G4", Decision.PASS))
    runner.register(GateId.G5, make_contract_gate("G5", Decision.PASS))
    runner.register(GateId.G6, make_contract_gate("G6", Decision.PASS))
    runner.register(GateId.G7, make_contract_gate("G7", Decision.PASS))

    runner.run()

    assert meta.status in (RunStatus.PASS, RunStatus.STOP)

    for gate_prefix in ("G1", "G2", "G3"):
        meta_path = tmp_path / f"{gate_prefix}_META.json"
        assert meta_path.exists()
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        assert "started_at" in payload
        assert "finished_at" in payload
        assert "execution_time_ms" in payload
        assert isinstance(payload["execution_time_ms"], int)
