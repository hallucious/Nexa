from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.models.decision_models import GateResult, Decision
from src.pipeline.runner import GateContext
from src.pipeline.contracts import standard_spec
from src.utils.time import now_seoul


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _flatten_strings(obj: Any) -> List[str]:
    """
    Collect string leaves from JSON-like object.
    """
    out: List[str] = []
    if isinstance(obj, dict):
        for v in obj.values():
            out.extend(_flatten_strings(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_flatten_strings(v))
    elif isinstance(obj, str):
        out.append(obj)
    return out


def _heuristic_minimality(design: Dict[str, Any]) -> Tuple[str, List[str]]:
    """
    Minimality heuristic (deterministic):
    - Too many constraints/interfaces/acceptance criteria is a smell.
    - Excessively long requirement list is a smell.
    Returns (label, reasons) where label in {"OK","WARN","ERROR"}.
    """
    reasons: List[str] = []
    reqs = design.get("requirements") or []
    interfaces = design.get("interfaces") or []
    constraints = design.get("constraints") or []
    ac = design.get("acceptance_criteria") or []

    if isinstance(reqs, list) and len(reqs) > 80:
        reasons.append(f"requirements too many: {len(reqs)} (>80)")
    if isinstance(interfaces, list) and len(interfaces) > 20:
        reasons.append(f"interfaces too many: {len(interfaces)} (>20)")
    if isinstance(constraints, list) and len(constraints) > 30:
        reasons.append(f"constraints too many: {len(constraints)} (>30)")
    if isinstance(ac, list) and len(ac) > 30:
        reasons.append(f"acceptance_criteria too many: {len(ac)} (>30)")

    if reasons:
        return "WARN", reasons
    return "OK", []


def _heuristic_actionability(design: Dict[str, Any]) -> Tuple[str, List[str]]:
    """
    Actionability heuristic:
    - Must have concrete interfaces + acceptance criteria.
    - Each acceptance criterion should be "testable-ish" (contains verbs / measurable).
    """
    reasons: List[str] = []
    interfaces = design.get("interfaces") or []
    ac = design.get("acceptance_criteria") or []

    if not interfaces or not isinstance(interfaces, list):
        reasons.append("interfaces missing or not a list")
    if not ac or not isinstance(ac, list):
        reasons.append("acceptance_criteria missing or not a list")

    # If present, check for low-quality AC lines
    if isinstance(ac, list) and ac:
        weak = []
        for line in ac:
            if not isinstance(line, str) or len(line.strip()) < 6:
                weak.append(str(line))
                continue
            # simple testability hint: contains keywords like "must/should/exists/pass/fail"
            l = line.lower()
            if not any(k in l for k in ["must", "should", "pass", "fail", "exists", "returns", "status"]):
                weak.append(line)
        if len(weak) >= 3:
            reasons.append(f"acceptance_criteria appear weak/non-testable (>=3): {weak[:3]}")

    if reasons:
        # still not a "provable error", but it's a self-check failure for this gate
        return "WARN", reasons
    return "OK", []


def _heuristic_overconfidence(g3_output: Dict[str, Any]) -> Tuple[str, List[str]]:
    """
    Overconfidence heuristic:
    - If Gate3 contains WARN statements, we mark this as WARN (not FAIL).
    - If Gate3 contains ERROR statements, mark ERROR (FAIL).
    """
    reasons: List[str] = []
    results = g3_output.get("results") or []
    if not isinstance(results, list):
        return "WARN", ["G3 results missing or invalid"]

    error_cnt = 0
    warn_cnt = 0
    for r in results:
        if not isinstance(r, dict):
            continue
        label = (r.get("label") or "").upper()
        if label == "ERROR":
            error_cnt += 1
        if label == "WARN":
            warn_cnt += 1

    if error_cnt > 0:
        reasons.append(f"G3 has ERROR statements: {error_cnt}")
        return "ERROR", reasons

    if warn_cnt > 0:
        reasons.append(f"G3 has WARN statements requiring verification: {warn_cnt}")
        return "WARN", reasons

    return "OK", []


def gate_g4_self_check(ctx: GateContext) -> GateResult:
    run_dir = Path(ctx.run_dir).resolve()

    g1_path = run_dir / "G1_OUTPUT.json"
    g2_path = run_dir / "G2_OUTPUT.json"
    g3_path = run_dir / "G3_OUTPUT.json"

    if not g1_path.exists():
        raise FileNotFoundError("G1_OUTPUT.json not found (Gate4 requires Gate1 output)")
    if not g2_path.exists():
        raise FileNotFoundError("G2_OUTPUT.json not found (Gate4 requires Gate2 output)")
    if not g3_path.exists():
        raise FileNotFoundError("G3_OUTPUT.json not found (Gate4 requires Gate3 output)")

    g1 = _read_json(g1_path)
    g2 = _read_json(g2_path)
    g3 = _read_json(g3_path)

    checks: List[Dict[str, Any]] = []

    # 1) Minimality
    label, reasons = _heuristic_minimality(g1)
    checks.append({"check": "minimality", "label": label, "reasons": reasons})

    # 2) Actionability
    label2, reasons2 = _heuristic_actionability(g1)
    checks.append({"check": "actionability", "label": label2, "reasons": reasons2})

    # 3) Continuity awareness (Gate2)
    # If baseline missing, that's not a fail, but warn because continuity can't be verified.
    notes: List[str] = []
    baseline_present = bool(g2.get("baseline_present", False))
    if not baseline_present:
        notes.append("Baseline missing in G2; continuity vs baseline not verifiable (WARN).")
        checks.append({"check": "continuity_baseline", "label": "WARN", "reasons": ["baseline_present=false"]})
    else:
        checks.append({"check": "continuity_baseline", "label": "OK", "reasons": []})

    # 4) Overconfidence / fact audit linkage (Gate3)
    label3, reasons3 = _heuristic_overconfidence(g3)
    checks.append({"check": "fact_audit_alignment", "label": label3, "reasons": reasons3})

    # Decision rule (deterministic):
    # - FAIL if any check label == ERROR
    # - Otherwise PASS (even if WARN), but WARNs are recorded
    has_error = any(c.get("label") == "ERROR" for c in checks)
    decision = Decision.FAIL if has_error else Decision.PASS

    # Write artifacts
    warn_lines = []
    err_lines = []
    for c in checks:
        lab = c.get("label")
        if lab == "WARN":
            warn_lines.append(f"- {c['check']}: {c.get('reasons')}")
        if lab == "ERROR":
            err_lines.append(f"- {c['check']}: {c.get('reasons')}")

    decision_md = (
        "# G4 SELF CHECK DECISION\n\n"
        f"Decision: {decision.value}\n\n"
        "## ERROR\n"
        + ("\n".join(err_lines) + "\n" if err_lines else "- None\n")
        + "\n## WARN\n"
        + ("\n".join(warn_lines) + "\n" if warn_lines else "- None\n")
        + "\n## Notes\n"
        + ("\n".join([f"- {n}" for n in notes]) + "\n" if notes else "- None\n")
    )
    (run_dir / "G4_DECISION.md").write_text(decision_md, encoding="utf-8")

    output = {
        "gate": "G4",
        "mode": "self_check_stub",
        "inputs": {
            "G1_OUTPUT.json": "G1_OUTPUT.json",
            "G2_OUTPUT.json": "G2_OUTPUT.json",
            "G3_OUTPUT.json": "G3_OUTPUT.json",
        },
        "checks": checks,
        "notes": notes,
        "decision_rule": "FAIL if any ERROR else PASS (WARNs recorded)",
    }
    (run_dir / "G4_OUTPUT.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    meta = {
        "gate": "G4",
        "decision": decision.value,
        "at": now_seoul().isoformat(),
        "attempt": ctx.meta.attempts.get("G4", 1),
    }
    (run_dir / "G4_META.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    outputs = {
        "G4_DECISION.md": "G4_DECISION.md",
        "G4_OUTPUT.json": "G4_OUTPUT.json",
        "G4_META.json": "G4_META.json",
    }
    standard_spec("G4").validate(outputs)

    return GateResult(
        decision=decision,
        message="Self-check completed (stub)",
        outputs=outputs,
        meta={"has_error": has_error},
    )
