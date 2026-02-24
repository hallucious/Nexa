from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from src.models.decision_models import Decision, GateResult
from src.pipeline.contracts import standard_spec
from src.pipeline.runner import GateContext
from src.utils.time import now_seoul


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_standard_artifacts(
    run_dir: Path,
    gate_prefix: str,
    decision: Decision,
    output_payload: Dict[str, Any],
    meta_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Write standard artifacts + contract-validate outputs mapping."""

    spec = standard_spec(gate_prefix)

    (run_dir / f"{gate_prefix}_DECISION.md").write_text(
        f"# {gate_prefix} DECISION\n\n{decision.value}\n", encoding="utf-8"
    )

    (run_dir / f"{gate_prefix}_OUTPUT.json").write_text(
        json.dumps(output_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    mp: Dict[str, Any] = {
        "gate": gate_prefix,
        "decision": decision.value,
        "at": now_seoul().isoformat(),
    }
    if isinstance(meta_payload, dict):
        mp.update(meta_payload)

    (run_dir / f"{gate_prefix}_META.json").write_text(
        json.dumps(mp, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    outputs = {
        f"{gate_prefix}_DECISION.md": f"{gate_prefix}_DECISION.md",
        f"{gate_prefix}_OUTPUT.json": f"{gate_prefix}_OUTPUT.json",
        f"{gate_prefix}_META.json": f"{gate_prefix}_META.json",
    }
    spec.validate(outputs)
    return outputs


def _gate_g6_legacy(ctx: GateContext) -> GateResult:
    """Deterministic test-safe implementation.

    - Requires G1_OUTPUT.json, G2_OUTPUT.json, G3_OUTPUT.json, G4_OUTPUT.json, G5_OUTPUT.json.
    - Always writes standard artifacts.
    - PASS when prereqs exist; FAIL otherwise.
    """

    run_dir = Path(ctx.run_dir)
    gate_prefix = "G6"

    prereqs = [
        "G1_OUTPUT.json",
        "G2_OUTPUT.json",
        "G3_OUTPUT.json",
        "G4_OUTPUT.json",
        "G5_OUTPUT.json",
    ]
    missing = [p for p in prereqs if not (run_dir / p).exists()]

    if missing:
        decision = Decision.FAIL
        output = {
            "gate": gate_prefix,
            "counterfactuals": [],
            "errors": [f"missing prereqs: {', '.join(missing)}"],
        }
        outputs = _write_standard_artifacts(run_dir, gate_prefix, decision, output)
        return GateResult(decision=decision, message="prereq_missing", outputs=outputs)

    g1 = _read_json(run_dir / "G1_OUTPUT.json")
    g2 = _read_json(run_dir / "G2_OUTPUT.json")
    g3 = _read_json(run_dir / "G3_OUTPUT.json")
    g4 = _read_json(run_dir / "G4_OUTPUT.json")
    g5 = _read_json(run_dir / "G5_OUTPUT.json")

    counterfactuals = [
        {
            "id": "CF1",
            "hypothesis": "If baseline is missing, continuity checks should not block PASS.",
            "evidence": {"baseline_present": bool(g2.get("baseline_present", False))},
        },
        {
            "id": "CF2",
            "hypothesis": "If any required artifact is missing, the gate must FAIL deterministically.",
            "evidence": {"prereqs_present": True},
        },
    ]

    decision = Decision.PASS
    output = {
        "gate": gate_prefix,
        "counterfactuals": counterfactuals,
        "inputs": {
            "g1": bool(g1),
            "g2": bool(g2),
            "g3": bool(g3),
            "g4": bool(g4),
            "g5": bool(g5),
        },
        "errors": [],
    }
    outputs = _write_standard_artifacts(run_dir, gate_prefix, decision, output)
    return GateResult(decision=decision, message="counterfactual_review", outputs=outputs)


def _try_platform_provider_call(ctx: GateContext) -> Dict[str, Any]:
    """Best-effort runtime-only provider call. Never changes PASS/FAIL semantics."""

    providers = (ctx.providers or {})
    engine = "gemini" if "gemini" in providers else ("gpt" if "gpt" in providers else "")
    provider = providers.get(engine) if engine else None
    if provider is None:
        return {}

    run_dir = Path(ctx.run_dir)
    g1 = _read_json(run_dir / "G1_OUTPUT.json")
    prompt = (
        "Generate 2 short counterfactual checks for the following design summary. "
        "Return plain text.\n\n"
        f"G1_OUTPUT: {json.dumps(g1, ensure_ascii=False)}\n"
    )

    try:
        raw = provider.generate_text(prompt)
        # Some stubs return (text, meta, error). Normalize to text.
        text = raw[0] if isinstance(raw, tuple) and raw else raw
        return {
            "ai": {
                "engine": engine,
                "provider": getattr(provider, "name", type(provider).__name__),
                "used": True,
                "text": str(text),
            }
        }
    except Exception as e:  # noqa: BLE001
        return {
            "ai": {
                "engine": engine or None,
                "used": False,
                "error": f"{type(e).__name__}: {e}",
            }
        }


def gate_g6_counterfactual_review(ctx: GateContext) -> GateResult:
    """G6: Counterfactual review gate.

    - Pytest: deterministic legacy implementation (no provider/network).
    - Runtime: legacy semantics + optional best-effort provider call (injected).
    """

    if bool(os.getenv("PYTEST_CURRENT_TEST")):
        return _gate_g6_legacy(ctx)

    base = _gate_g6_legacy(ctx)
    try:
        run_dir = Path(ctx.run_dir)
        out_path = run_dir / "G6_OUTPUT.json"
        out = _read_json(out_path)
        out.update(_try_platform_provider_call(ctx))
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return base
