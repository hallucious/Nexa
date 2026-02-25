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
    (run_dir / f"{gate_prefix}_DECISION.md").write_text(f"# {gate_prefix} DECISION\n\n{decision_str}\n", encoding="utf-8")
    (run_dir / f"{gate_prefix}_OUTPUT.json").write_text(json.dumps({"gate": gate_prefix}, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / f"{gate_prefix}_META.json").write_text(
        json.dumps({"gate": gate_prefix, "decision": decision_str, "at": now_seoul().isoformat()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    outputs = {
        f"{gate_prefix}_DECISION.md": f"{gate_prefix}_DECISION.md",
        f"{gate_prefix}_OUTPUT.json": f"{gate_prefix}_OUTPUT.json",
        f"{gate_prefix}_META.json": f"{gate_prefix}_META.json",
    }
    spec.validate(outputs)
    return outputs


def make_contract_gate(gate_prefix: str, decision: Decision):
    def _exec(ctx: GateContext) -> GateResult:
        outputs = _write_standard_artifacts(Path(ctx.run_dir), gate_prefix, decision.value)
        # no plugin meta here; runner must still record an observability event
        return GateResult(decision=decision, message=gate_prefix, outputs=outputs, meta={})
    return _exec


def test_step34_observability_jsonl_artifact(tmp_path: Path) -> None:
    meta = RunMeta(run_id="TEST_STEP34_OBS", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(tmp_path))

    for gid in (GateId.G1, GateId.G2, GateId.G3, GateId.G4, GateId.G5, GateId.G6, GateId.G7):
        runner.register(gid, make_contract_gate(gid.value, Decision.PASS))

    runner.run()
    assert meta.status in (RunStatus.PASS, RunStatus.STOP)

    obs_path = tmp_path / "OBSERVABILITY.jsonl"
    assert obs_path.exists()

    lines = [ln for ln in obs_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 7

    # Validate minimal schema on first 3 events (enough to ensure invariant)
    for raw in lines[:3]:
        ev = json.loads(raw)
        assert ev["run_id"] == "TEST_STEP34_OBS"
        assert ev["gate"] in {"G1", "G2", "G3", "G4", "G5", "G6", "G7"}
        assert "decision" in ev
        assert "started_at" in ev and "finished_at" in ev
        assert isinstance(ev["execution_time_ms"], int)
        # provider/vendor should exist even if none
        assert "provider" in ev and "vendor" in ev
