from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.pipeline.runner import PipelineRunner, GateContext
from src.pipeline.state import RunMeta, GateId, RunStatus
from src.models.decision_models import GateResult, Decision
from src.pipeline.contracts import standard_spec
from src.utils.time import now_seoul


def _write_standard_artifacts(run_dir: Path, gate_prefix: str, decision_str: str = "PASS") -> dict[str, str]:
    """Write standard artifacts and return outputs mapping (contract key -> filename)."""
    spec = standard_spec(gate_prefix)

    (run_dir / f"{gate_prefix}_DECISION.md").write_text(
        f"# {gate_prefix} DECISION\n\n{decision_str}\n", encoding="utf-8"
    )
    (run_dir / f"{gate_prefix}_OUTPUT.json").write_text(
        json.dumps({"gate": gate_prefix}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / f"{gate_prefix}_META.json").write_text(
        json.dumps(
            {
                "gate": gate_prefix,
                "decision": decision_str,
                "at": now_seoul().isoformat(),
            },
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


def make_contract_gate(gate_prefix: str, decision: Decision | object) -> callable:
    """A minimal mock gate. Can intentionally return an invalid decision type for UNKNOWN policy tests."""

    def _exec(ctx: GateContext) -> GateResult:
        outputs = _write_standard_artifacts(Path(ctx.run_dir), gate_prefix, str(getattr(decision, "value", decision)))
        # NOTE: GateResult typing says Decision, but we intentionally pass through 'decision' for robustness tests.
        return GateResult(decision=decision, message=gate_prefix, outputs=outputs)  # type: ignore[arg-type]

    return _exec


def make_raising_gate(gate_prefix: str) -> callable:
    def _exec(ctx: GateContext) -> GateResult:
        _write_standard_artifacts(Path(ctx.run_dir), gate_prefix, "RAISE")
        raise RuntimeError("boom")

    return _exec


def test_final_meta_status_is_pass_or_stop(tmp_path: Path):
    """Handover invariant: meta.status final value must be PASS or STOP (no FAIL)."""
    meta = RunMeta(run_id="TEST_FINAL_STATUS", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(tmp_path))

    # Pass everything until G7, then FAIL at G7 -> should STOP (not FAIL)
    runner.register(GateId.G1, make_contract_gate("G1", Decision.PASS))
    runner.register(GateId.G2, make_contract_gate("G2", Decision.PASS))
    runner.register(GateId.G3, make_contract_gate("G3", Decision.PASS))
    runner.register(GateId.G4, make_contract_gate("G4", Decision.PASS))
    runner.register(GateId.G5, make_contract_gate("G5", Decision.PASS))
    runner.register(GateId.G6, make_contract_gate("G6", Decision.PASS))
    runner.register(GateId.G7, make_contract_gate("G7", Decision.FAIL))

    runner.run()

    assert meta.status in (RunStatus.PASS, RunStatus.STOP)
    assert meta.status == RunStatus.STOP
    assert meta.current_gate == GateId.STOP


def test_required_decision_artifacts_exist_for_key_gates(tmp_path: Path):
    """Handover artifact invariant: G2/G4/G5/G6/G7 must produce Gx_DECISION.md."""
    meta = RunMeta(run_id="TEST_ARTIFACTS", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(tmp_path))

    for gid in [GateId.G1, GateId.G2, GateId.G3, GateId.G4, GateId.G5, GateId.G6, GateId.G7]:
        runner.register(gid, make_contract_gate(gid.value, Decision.PASS))

    runner.run()

    for gate_prefix in ("G2", "G4", "G5", "G6", "G7"):
        assert (tmp_path / f"{gate_prefix}_DECISION.md").exists()


def test_unknown_decision_is_treated_as_stop(tmp_path: Path):
    """Handover invariant: UNKNOWN is treated as STOP (safety)."""
    meta = RunMeta(run_id="TEST_UNKNOWN", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(tmp_path))

    runner.register(GateId.G1, make_contract_gate("G1", Decision.PASS))
    runner.register(GateId.G2, make_contract_gate("G2", Decision.PASS))
    runner.register(GateId.G3, make_contract_gate("G3", Decision.PASS))

    # Intentionally return an invalid decision type to simulate "UNKNOWN"
    runner.register(GateId.G4, make_contract_gate("G4", "UNKNOWN"))

    # The rest shouldn't run, but register anyway.
    runner.register(GateId.G5, make_contract_gate("G5", Decision.PASS))
    runner.register(GateId.G6, make_contract_gate("G6", Decision.PASS))
    runner.register(GateId.G7, make_contract_gate("G7", Decision.PASS))

    runner.run()

    assert meta.status == RunStatus.STOP
    assert meta.current_gate == GateId.STOP


def test_gate_exception_is_converted_to_stop(tmp_path: Path):
    """Safety: if a gate crashes, runner must STOP (not crash the whole process)."""
    meta = RunMeta(run_id="TEST_EXCEPTION", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(tmp_path))

    runner.register(GateId.G1, make_contract_gate("G1", Decision.PASS))
    runner.register(GateId.G2, make_contract_gate("G2", Decision.PASS))

    # G3 raises
    runner.register(GateId.G3, make_raising_gate("G3"))

    runner.register(GateId.G4, make_contract_gate("G4", Decision.PASS))
    runner.register(GateId.G5, make_contract_gate("G5", Decision.PASS))
    runner.register(GateId.G6, make_contract_gate("G6", Decision.PASS))
    runner.register(GateId.G7, make_contract_gate("G7", Decision.PASS))

    runner.run()

    assert meta.status == RunStatus.STOP
    assert meta.current_gate == GateId.STOP
