from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from src.models.decision_models import Decision, GateResult
from src.pipeline.contracts import standard_spec
from src.pipeline.runner import GateContext
from src.utils.time import now_seoul


def _write_gate_artifacts(
    run_dir: Path,
    gate_prefix: str,
    decision: Decision,
    decision_md: str,
    output: Dict[str, Any],
    meta: Dict[str, Any],
) -> Dict[str, str]:
    """Write standard artifacts and validate via standard_spec."""
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / f"{gate_prefix}_DECISION.md").write_text(decision_md, encoding="utf-8")
    (run_dir / f"{gate_prefix}_OUTPUT.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / f"{gate_prefix}_META.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    outputs = {
        f"{gate_prefix}_DECISION.md": f"{gate_prefix}_DECISION.md",
        f"{gate_prefix}_OUTPUT.json": f"{gate_prefix}_OUTPUT.json",
        f"{gate_prefix}_META.json": f"{gate_prefix}_META.json",
    }
    standard_spec(gate_prefix).validate(outputs)
    return outputs


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _prereq_paths(run_dir: Path) -> List[Path]:
    return [
        run_dir / "G1_OUTPUT.json",
        run_dir / "G2_OUTPUT.json",
        run_dir / "G3_OUTPUT.json",
    ]


def _schema_ok_from_g1(g1_out: Dict[str, Any]) -> bool:
    design = g1_out.get("design") if isinstance(g1_out, dict) else None
    if not isinstance(design, dict):
        return False
    for key in ("requirements", "interfaces", "constraints", "acceptance_criteria"):
        v = design.get(key)
        if not isinstance(v, list) or len(v) == 0:
            return False
    return True


def _execution_plan_md() -> str:
    return (
        "## Execution Plan\n"
        "- Proceed to G5 (implement & test)\n\n"
        "## G5 Execution instructions\n"
        "- Run:\n"
        "  - python -m pytest -q\n"
    )


def _decision_md(gate: str, decision: Decision, body: str, include_exec: bool) -> str:
    md = f"# {gate} DECISION\n\nDecision: {decision.value}\n\n{body}\n"
    if include_exec:
        md += "\n" + _execution_plan_md()
    return md


def _write_prereq_fail(run_dir: Path, missing: List[str], gpt_used: bool, gpt_text: str) -> GateResult:
    decision = Decision.FAIL
    body = "Upstream artifacts missing:\n- " + "\n- ".join(missing)
    decision_md = _decision_md("G4", decision, body, include_exec=False)

    output: Dict[str, Any] = {
        "gate": "G4",
        "checks": {"prereqs_present": False, "schema_ok": False},
        "missing": missing,
        "gpt": {"used": bool(gpt_used), "text": gpt_text},
        "execution_plan_md": _execution_plan_md(),
    }
    meta = {"gate": "G4", "decision": decision.value, "at": now_seoul().isoformat()}
    outputs = _write_gate_artifacts(run_dir, "G4", decision, decision_md, output, meta)
    return GateResult(decision=decision, message="PREREQ_MISSING", outputs=outputs)


def _gate_g4_legacy(ctx: GateContext) -> GateResult:
    """Deterministic (no-provider) implementation. Always writes artifacts."""
    run_dir = Path(ctx.run_dir).resolve()

    missing = [p.name for p in _prereq_paths(run_dir) if not p.exists()]
    if missing:
        return _write_prereq_fail(run_dir, missing, gpt_used=False, gpt_text="")

    g1_out = _load_json(run_dir / "G1_OUTPUT.json")
    schema_ok = _schema_ok_from_g1(g1_out)

    decision = Decision.PASS if schema_ok else Decision.FAIL
    body = "Schema check passed." if schema_ok else "Schema check failed."
    decision_md = _decision_md("G4", decision, body, include_exec=True)

    output = {
        "gate": "G4",
        "checks": {"prereqs_present": True, "schema_ok": bool(schema_ok)},
        "gpt": {"used": False, "text": ""},
        "execution_plan_md": _execution_plan_md(),
    }
    meta = {"gate": "G4", "decision": decision.value, "at": now_seoul().isoformat()}
    outputs = _write_gate_artifacts(run_dir, "G4", decision, decision_md, output, meta)
    return GateResult(decision=decision, message="OK" if decision == Decision.PASS else "SCHEMA_INVALID", outputs=outputs)


def _normalize_provider_text(ret: Any) -> str:
    if isinstance(ret, tuple) and len(ret) >= 1:
        return str(ret[0])
    return str(ret)


def gate_g4_self_check(ctx: GateContext) -> GateResult:
    """
    G4: Self-check.

    Rules:
    - Under pytest: always legacy (deterministic).
    - Otherwise: if ctx.providers['gpt'] exists, call it and record output.gpt.used=True.
      If missing, fall back to legacy.
    """
    if bool(os.getenv("PYTEST_CURRENT_TEST")):
        return _gate_g4_legacy(ctx)

    provider = (getattr(ctx, "providers", None) or {}).get("gpt")
    if provider is None:
        return _gate_g4_legacy(ctx)

    run_dir = Path(ctx.run_dir).resolve()

    missing = [p.name for p in _prereq_paths(run_dir) if not p.exists()]
    if missing:
        return _write_prereq_fail(run_dir, missing, gpt_used=True, gpt_text="")

    g1_out = _load_json(run_dir / "G1_OUTPUT.json")
    schema_ok = _schema_ok_from_g1(g1_out)

    prompt = "Self-check: validate that the design output schema is complete and consistent."
    try:
        ret = provider.generate_text(prompt)
        text = _normalize_provider_text(ret)
    except Exception:
        text = ""

    decision = Decision.PASS if schema_ok else Decision.FAIL
    body = "Schema check passed." if schema_ok else "Schema check failed."
    decision_md = _decision_md("G4", decision, body, include_exec=True)

    output = {
        "gate": "G4",
        "checks": {"prereqs_present": True, "schema_ok": bool(schema_ok)},
        "gpt": {"used": True, "text": text},
        "execution_plan_md": _execution_plan_md(),
    }
    meta = {"gate": "G4", "decision": decision.value, "at": now_seoul().isoformat()}
    outputs = _write_gate_artifacts(run_dir, "G4", decision, decision_md, output, meta)
    return GateResult(decision=decision, message="OK" if decision == Decision.PASS else "SCHEMA_INVALID", outputs=outputs)
