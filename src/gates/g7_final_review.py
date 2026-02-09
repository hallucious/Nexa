# src/gates/g7_final_review.py
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


def _summarize_gate_decision(md_path: Path) -> str:
    if not md_path.exists():
        return "UNKNOWN"
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines():
        if line.strip().lower().startswith("decision:"):
            return line.split(":", 1)[1].strip()
    return "UNKNOWN"


def _gate_fail_reason_hints(run_dir: Path) -> List[str]:
    hints: List[str] = []

    # G2 removed fields => continuity failure signal
    g2_path = run_dir / "G2_OUTPUT.json"
    if g2_path.exists():
        g2 = _read_json(g2_path)
        bd = g2.get("baseline_diff")
        if isinstance(bd, dict) and (bd.get("removed") or []):
            hints.append(f"G2 baseline removed fields: {len(bd.get('removed') or [])}")

    # G3 ERROR statements
    g3_path = run_dir / "G3_OUTPUT.json"
    if g3_path.exists():
        g3 = _read_json(g3_path)
        results = g3.get("results") or []
        err = [r for r in results if isinstance(r, dict) and (r.get("label") == "ERROR")]
        if err:
            hints.append(f"G3 ERROR statements: {len(err)}")

    # G4 ERROR checks
    g4_path = run_dir / "G4_OUTPUT.json"
    if g4_path.exists():
        g4 = _read_json(g4_path)
        checks = g4.get("checks") or []
        err = [c for c in checks if isinstance(c, dict) and c.get("label") == "ERROR"]
        if err:
            hints.append(f"G4 ERROR checks: {len(err)}")

    # G5 tests failed
    g5_path = run_dir / "G5_OUTPUT.json"
    if g5_path.exists():
        g5 = _read_json(g5_path)
        res = g5.get("result") or {}
        rc = res.get("returncode")
        if rc not in (0, None):
            hints.append(f"G5 tests failed (returncode={rc})")
        if res.get("timeout") is True:
            hints.append("G5 tests timeout")

    return hints


def _baseline_update_recommendation(run_dir: Path, final_decision: Decision) -> Dict[str, Any]:
    """
    Gate7 outputs a *recommendation* only.
    The actual baseline update is executed by scripts/update_baseline.py (controlled step).

    Rule (fixed):
    - recommend_update is True only when:
      (a) final_decision == PASS, AND
      (b) baseline is missing OR baseline is known-stale signal exists (currently: baseline_missing only)
    """
    g2_path = run_dir / "G2_OUTPUT.json"
    baseline_present = False
    if g2_path.exists():
        g2 = _read_json(g2_path)
        baseline_present = bool(g2.get("baseline_present", False))

    # recommend only on PASS
    if final_decision != Decision.PASS:
        return {
            "recommend_update": False,
            "note": "Final decision is not PASS. Baseline promotion is disallowed.",
            "command": "",
            "eligibility": {"final_pass_required": True, "final_is_pass": False, "baseline_present": baseline_present},
        }

    if not baseline_present:
        cmd = f"python scripts/update_baseline.py --run-id {run_dir.name} --promote-pic"
        return {
            "recommend_update": True,
            "note": "Baseline missing. Recommend promoting this PASS run to establish baseline (controlled update).",
            "command": cmd,
            "eligibility": {"final_pass_required": True, "final_is_pass": True, "baseline_present": baseline_present},
        }

    return {
        "recommend_update": False,
        "note": "Baseline already present. No update recommended by fixed rule.",
        "command": "",
        "eligibility": {"final_pass_required": True, "final_is_pass": True, "baseline_present": baseline_present},
    }


def gate_g7_final_review(ctx: GateContext) -> GateResult:
    run_dir = Path(ctx.run_dir).resolve()

    required = [
        "G1_OUTPUT.json",
        "G2_OUTPUT.json",
        "G3_OUTPUT.json",
        "G4_OUTPUT.json",
        "G5_OUTPUT.json",
        "G6_OUTPUT.json",
    ]
    for name in required:
        if not (run_dir / name).exists():
            raise FileNotFoundError(f"{name} not found (Gate7 requires G1~G6 outputs)")

    # Read decisions from DECISION.md
    decisions: Dict[str, str] = {}
    for gid in ["G1", "G2", "G3", "G4", "G5", "G6"]:
        decisions[gid] = _summarize_gate_decision(run_dir / f"{gid}_DECISION.md")

    # Deterministic final decision rules:
    # - FAIL if any of G1~G5 decision == FAIL
    # - Otherwise PASS
    hard_fail = any(decisions[g] == "FAIL" for g in ["G1", "G2", "G3", "G4", "G5"])
    decision = Decision.FAIL if hard_fail else Decision.PASS

    fail_hints = _gate_fail_reason_hints(run_dir)

    # Include Gate6 conflicts
    g6 = _read_json(run_dir / "G6_OUTPUT.json")
    conflicts = g6.get("conflicts") or []

    baseline_reco = _baseline_update_recommendation(run_dir, decision)

    decision_md = (
        "# G7 FINAL REVIEW DECISION\n\n"
        f"Decision: {decision.value}\n\n"
        "## Gate decisions (observed)\n"
        + "\n".join([f"- {k}: {v}" for k, v in decisions.items()])
        + "\n\n"
        "## Failure hints\n"
        + (("\n".join([f"- {h}" for h in fail_hints]) + "\n") if fail_hints else "- None\n")
        + "\n## Gate6 conflicts\n"
        + (("\n".join([f"- {c}" for c in conflicts]) + "\n") if conflicts else "- None\n")
        + "\n## Baseline recommendation\n"
        + f"- recommend_update: {baseline_reco.get('recommend_update')}\n"
        + f"- note: {baseline_reco.get('note')}\n"
        + (f"- command: {baseline_reco.get('command')}\n" if baseline_reco.get("command") else "")
    )
    (run_dir / "G7_DECISION.md").write_text(decision_md, encoding="utf-8")

    output: Dict[str, Any] = {
        "gate": "G7",
        "mode": "final_review_stub",
        "decisions_observed": decisions,
        "final_decision_rule": "FAIL if any of G1~G5 is FAIL else PASS",
        "fail_hints": fail_hints,
        "gate6_conflicts": conflicts,
        "baseline_recommendation": {
            "recommend_update": bool(baseline_reco.get("recommend_update", False)),
            "note": str(baseline_reco.get("note", "")),
            "command": str(baseline_reco.get("command", "")),
            "eligibility": baseline_reco.get("eligibility", {}),
        },
        "notes": [
            "No AI used. Deterministic aggregation review.",
            "Gate7 never mutates baseline; it only emits a recommendation and a copy-paste command.",
        ],
    }
    (run_dir / "G7_OUTPUT.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    meta = {
        "gate": "G7",
        "decision": decision.value,
        "at": now_seoul().isoformat(),
        "attempt": ctx.meta.attempts.get("G7", 1),
    }
    (run_dir / "G7_META.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    outputs = {
        "G7_DECISION.md": "G7_DECISION.md",
        "G7_OUTPUT.json": "G7_OUTPUT.json",
        "G7_META.json": "G7_META.json",
    }
    standard_spec("G7").validate(outputs)

    return GateResult(
        decision=decision,
        message="Final review completed (stub)",
        outputs=outputs,
        meta={
            "hard_fail": hard_fail,
            "fail_hints": fail_hints,
            "baseline_reco": baseline_reco,
        },
    )
