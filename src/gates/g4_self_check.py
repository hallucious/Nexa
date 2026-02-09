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


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _heuristic_minimality(design: Dict[str, Any]) -> Tuple[str, List[str]]:
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
    reasons: List[str] = []
    interfaces = design.get("interfaces") or []
    ac = design.get("acceptance_criteria") or []

    if not interfaces or not isinstance(interfaces, list):
        reasons.append("interfaces missing or not a list")
    if not ac or not isinstance(ac, list):
        reasons.append("acceptance_criteria missing or not a list")

    if isinstance(ac, list) and ac:
        weak = []
        for line in ac:
            if not isinstance(line, str) or len(line.strip()) < 6:
                weak.append(str(line))
                continue
            l = line.lower()
            if not any(k in l for k in ["must", "should", "pass", "fail", "exists", "returns", "status"]):
                weak.append(line)
        if len(weak) >= 3:
            reasons.append(f"acceptance_criteria appear weak/non-testable (>=3): {weak[:3]}")

    if reasons:
        return "WARN", reasons
    return "OK", []


def _heuristic_overconfidence(g3_output: Dict[str, Any]) -> Tuple[str, List[str]]:
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


def _execution_plan_md(run_dir: Path) -> str:
    # Deterministic, no-network instructions.
    return (
        "## G5 Execution instructions\n"
        "\n"
        "Gate5 is responsible for implementing changes and running tests.\n"
        "\n"
        "1. Make code changes in the repo working tree (src/, tests/ as needed).\n"
        "2. Run the test command:\n"
        f"   - cwd: {run_dir}\n"
        "   - cmd: python -m pytest -q\n"
        "3. If tests fail, fix deterministically (no network required) and re-run.\n"
    )


def _write_prereq_fail_artifacts(run_dir: Path, missing: List[str]) -> GateResult:
    decision = Decision.FAIL
    exec_md = _execution_plan_md(run_dir)

    decision_md = (
        "# G4 SELF CHECK DECISION\n\n"
        f"Decision: {decision.value}\n\n"
        "Upstream artifacts missing\n\n"
        "## ERROR\n"
        + "\n".join([f"- missing prerequisite artifact: {m}" for m in missing])
        + "\n\n## WARN\n- None\n\n## Notes\n- Gate4 cannot proceed without upstream artifacts.\n\n"
        + exec_md
    )
    (run_dir / "G4_DECISION.md").write_text(decision_md, encoding="utf-8")

    output = {
        "gate": "G4",
        "mode": "self_check_stub",
        "prereq_ok": False,
        "missing_prerequisites": missing,
        "checks": [],
        "notes": ["Gate4 cannot proceed without upstream artifacts."],
        "execution_plan_md": exec_md,
    }
    _write_json(run_dir / "G4_OUTPUT.json", output)

    meta = {
        "gate": "G4",
        "decision": decision.value,
        "at": now_seoul().isoformat(),
        "prereq_ok": False,
        "missing_prerequisites": missing,
    }
    _write_json(run_dir / "G4_META.json", meta)

    outputs = {
        "G4_DECISION.md": "G4_DECISION.md",
        "G4_OUTPUT.json": "G4_OUTPUT.json",
        "G4_META.json": "G4_META.json",
    }
    standard_spec("G4").validate(outputs)

    return GateResult(
        decision=decision,
        message=f"Upstream artifacts missing: {missing}",
        outputs=outputs,
        meta={"prereq_ok": False, "missing": missing},
    )


def gate_g4_self_check(ctx: GateContext) -> GateResult:
    run_dir = Path(ctx.run_dir).resolve()

    g1_path = run_dir / "G1_OUTPUT.json"
    g2_path = run_dir / "G2_OUTPUT.json"
    g3_path = run_dir / "G3_OUTPUT.json"

    missing: List[str] = []
    if not g1_path.exists():
        missing.append("G1_OUTPUT.json")
    if not g2_path.exists():
        missing.append("G2_OUTPUT.json")
    if not g3_path.exists():
        missing.append("G3_OUTPUT.json")

    # IMPORTANT: do not raise; write artifacts and return FAIL
    if missing:
        return _write_prereq_fail_artifacts(run_dir, missing)

    g1 = _read_json(g1_path)
    g2 = _read_json(g2_path)
    g3 = _read_json(g3_path)

    checks: List[Dict[str, Any]] = []
    notes: List[str] = []

    # 1) Minimality
    label, reasons = _heuristic_minimality(g1)
    checks.append({"check": "minimality", "label": label, "reasons": reasons})

    # 2) Actionability
    label2, reasons2 = _heuristic_actionability(g1)
    checks.append({"check": "actionability", "label": label2, "reasons": reasons2})

    # 3) Continuity awareness (Gate2)
    baseline_present = bool(g2.get("baseline_present", False))
    if not baseline_present:
        notes.append("Baseline missing in G2; continuity vs baseline not verifiable (WARN).")
        checks.append({"check": "continuity_baseline", "label": "WARN", "reasons": ["baseline_present=false"]})
    else:
        checks.append({"check": "continuity_baseline", "label": "OK", "reasons": []})

    # 4) Fact audit alignment (Gate3)
    label3, reasons3 = _heuristic_overconfidence(g3)
    checks.append({"check": "fact_audit_alignment", "label": label3, "reasons": reasons3})

    # Decision rule (deterministic)
    has_error = any(c.get("label") == "ERROR" for c in checks)
    decision = Decision.FAIL if has_error else Decision.PASS

    warn_lines: List[str] = []
    err_lines: List[str] = []
    for c in checks:
        lab = c.get("label")
        if lab == "WARN":
            warn_lines.append(f"- {c['check']}: {c.get('reasons')}")
        if lab == "ERROR":
            err_lines.append(f"- {c['check']}: {c.get('reasons')}")

    exec_md = _execution_plan_md(run_dir)

    decision_md = (
        "# G4 SELF CHECK DECISION\n\n"
        f"Decision: {decision.value}\n\n"
        "## ERROR\n"
        + ("\n".join(err_lines) + "\n" if err_lines else "- None\n")
        + "\n## WARN\n"
        + ("\n".join(warn_lines) + "\n" if warn_lines else "- None\n")
        + "\n## Notes\n"
        + ("\n".join([f"- {n}" for n in notes]) + "\n" if notes else "- None\n")
        + "\n"
        + exec_md
    )
    (run_dir / "G4_DECISION.md").write_text(decision_md, encoding="utf-8")

    output = {
        "gate": "G4",
        "mode": "self_check_stub",
        "prereq_ok": True,
        "inputs": {
            "G1_OUTPUT.json": "G1_OUTPUT.json",
            "G2_OUTPUT.json": "G2_OUTPUT.json",
            "G3_OUTPUT.json": "G3_OUTPUT.json",
        },
        "checks": checks,
        "notes": notes,
        "decision_rule": "FAIL if any ERROR else PASS (WARNs recorded)",
        "execution_plan_md": exec_md,
    }
    _write_json(run_dir / "G4_OUTPUT.json", output)

    meta = {
        "gate": "G4",
        "decision": decision.value,
        "at": now_seoul().isoformat(),
        "attempt": ctx.meta.attempts.get("G4", 1),
        "prereq_ok": True,
    }
    _write_json(run_dir / "G4_META.json", meta)

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
        meta={"has_error": has_error, "prereq_ok": True},
    )
