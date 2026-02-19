from __future__ import annotations

import json
from pathlib import Path
from typing import List

from src.pipeline.runner import PipelineRunner, GateContext
from src.pipeline.state import RunMeta, GateId, RunStatus
from src.models.decision_models import GateResult, Decision
from src.pipeline.contracts import standard_spec
from src.utils.time import now_seoul


def _write_standard_artifacts(run_dir: Path, gate_prefix: str, decision: Decision, message: str, attempt: int) -> dict:
    decision_md = f"# {gate_prefix} DECISION\n\n{message}\n"
    output_json = {"gate": gate_prefix, "decision": decision.value, "message": message}
    meta_json = {
        "gate": gate_prefix,
        "decision": decision.value,
        "at": now_seoul().isoformat(),
        "attempt": attempt,
    }

    paths = {
        f"{gate_prefix}_DECISION.md": run_dir / f"{gate_prefix}_DECISION.md",
        f"{gate_prefix}_OUTPUT.json": run_dir / f"{gate_prefix}_OUTPUT.json",
        f"{gate_prefix}_META.json": run_dir / f"{gate_prefix}_META.json",
    }

    paths[f"{gate_prefix}_DECISION.md"].write_text(decision_md, encoding="utf-8")
    paths[f"{gate_prefix}_OUTPUT.json"].write_text(
        json.dumps(output_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    paths[f"{gate_prefix}_META.json"].write_text(
        json.dumps(meta_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    outputs = {name: str(path.name) for name, path in paths.items()}
    # Validate contract keys (runner validates too; this keeps tests explicit)
    standard_spec(gate_prefix).validate(outputs)
    return outputs


def make_contract_gate_sequence(gate_prefix: str, decisions: List[Decision], message: str):
    """Gate that returns decisions in order per invocation, while writing standard artifacts."""
    idx = {"i": 0}

    def _exec(ctx: GateContext) -> GateResult:
        i = idx["i"]
        decision = decisions[i] if i < len(decisions) else decisions[-1]
        idx["i"] += 1

        run_dir = Path(ctx.run_dir)
        attempt = ctx.meta.attempts.get(gate_prefix, 1)
        outputs = _write_standard_artifacts(run_dir, gate_prefix, decision, message, attempt)

        return GateResult(decision=decision, message=message, outputs=outputs)

    return _exec


def test_stop_is_terminal(tmp_path):
    meta = RunMeta(run_id="TEST_STOP", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(tmp_path))

    runner.register(GateId.G1, make_contract_gate_sequence("G1", [Decision.PASS], "G1"))
    runner.register(GateId.G2, make_contract_gate_sequence("G2", [Decision.PASS], "G2"))
    runner.register(GateId.G3, make_contract_gate_sequence("G3", [Decision.STOP], "G3 stop"))
    # Remaining gates registered but should never execute
    runner.register(GateId.G4, make_contract_gate_sequence("G4", [Decision.PASS], "G4"))
    runner.register(GateId.G5, make_contract_gate_sequence("G5", [Decision.PASS], "G5"))
    runner.register(GateId.G6, make_contract_gate_sequence("G6", [Decision.PASS], "G6"))
    runner.register(GateId.G7, make_contract_gate_sequence("G7", [Decision.PASS], "G7"))

    runner.run()

    assert meta.status == RunStatus.STOP
    assert meta.current_gate == GateId.STOP

    # Ensure we terminated at G3 -> STOP and did not run G4 artifacts
    assert (Path(tmp_path) / "G3_DECISION.md").exists()
    assert not (Path(tmp_path) / "G4_DECISION.md").exists()


def test_g6_fail_returns_to_g4_then_recovers(tmp_path):
    """Policy invariant: G6 FAIL must return control to G4 (handover policy)."""
    meta = RunMeta(run_id="TEST_G6_FAIL", created_at=now_seoul().isoformat())
    runner = PipelineRunner(meta=meta, run_dir=str(tmp_path))

    runner.register(GateId.G1, make_contract_gate_sequence("G1", [Decision.PASS], "G1"))
    runner.register(GateId.G2, make_contract_gate_sequence("G2", [Decision.PASS], "G2"))
    runner.register(GateId.G3, make_contract_gate_sequence("G3", [Decision.PASS], "G3"))
    runner.register(GateId.G4, make_contract_gate_sequence("G4", [Decision.PASS, Decision.PASS], "G4"))
    runner.register(GateId.G5, make_contract_gate_sequence("G5", [Decision.PASS, Decision.PASS], "G5"))
    # G6 fails once, then passes
    runner.register(GateId.G6, make_contract_gate_sequence("G6", [Decision.FAIL, Decision.PASS], "G6"))
    runner.register(GateId.G7, make_contract_gate_sequence("G7", [Decision.PASS], "G7"))

    runner.run()

    assert meta.status == RunStatus.PASS
    assert meta.current_gate == GateId.DONE

    # Extract transition path as tuples for easy assertion
    path = [(t.from_gate, t.to_gate, t.decision.value) for t in meta.transitions]

    # We must see a G6 FAIL transition to G4 at least once
    assert ("G6", "G4", "FAIL") in path

    # And we must later reach DONE
    assert path[-1][1] == "DONE"
