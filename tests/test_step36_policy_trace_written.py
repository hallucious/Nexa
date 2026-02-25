from __future__ import annotations

import json
from pathlib import Path

from src.pipeline.runner import PipelineRunner, GateContext
from src.pipeline.state import RunMeta, GateId
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


def make_gate_with_trace(gate_prefix: str):
    def _exec(ctx: GateContext) -> GateResult:
        outputs = _write_standard_artifacts(Path(ctx.run_dir), gate_prefix, "PASS")
        return GateResult(
            decision=Decision.PASS,
            message="ok",
            outputs=outputs,
            meta={
                "provider": "none",
                "vendor": "none",
                "reason_code": "SUCCESS",
                "detail_code": None,
                "reason_trace": ["x=1", "branch=PASS"],
            },
        )
    return _exec


def test_step36_reason_trace_is_written_to_observability(tmp_path: Path) -> None:
    meta = RunMeta(run_id="TEST_STEP36_TRACE", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(tmp_path))
    runner.register(GateId.G1, make_gate_with_trace("G1"))
    runner.run()

    path = tmp_path / "OBSERVABILITY.jsonl"
    assert path.exists()
    first = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert first["run_id"] == "TEST_STEP36_TRACE"
    assert first["gate"] == "G1"
    assert first["reason_trace"] == ["x=1", "branch=PASS"]
