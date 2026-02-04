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


def _safe_get(d: Dict[str, Any], *keys: str, default=None):
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _summarize_g5(g5: Dict[str, Any]) -> Dict[str, Any]:
    res = _safe_get(g5, "result", default={}) or {}
    cmd = _safe_get(g5, "command", default={}) or {}
    return {
        "returncode": res.get("returncode"),
        "timeout": res.get("timeout"),
        "duration_sec": res.get("duration_sec"),
        "cmd": cmd.get("cmd"),
        "timeout_sec": cmd.get("timeout_sec"),
    }


def _derive_counterfactuals(g1: Dict[str, Any], g2: Dict[str, Any], g3: Dict[str, Any], g4: Dict[str, Any], g5: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Deterministic alternative/counterfactual scenarios.
    No AI. Produces a list of 'what-if' changes + predicted impact.
    """
    counterfactuals: List[Dict[str, Any]] = []

    # CF1: If baseline is missing, what if we set baseline now?
    baseline_present = bool(g2.get("baseline_present", False))
    if not baseline_present:
        counterfactuals.append(
            {
                "id": "CF1_BASELINE_ESTABLISH",
                "what_if": "If we establish a baseline snapshot now (BASELINE_G1_OUTPUT.json) after a stable PASS run.",
                "expected_benefit": "Future continuity checks become meaningful; prevents silent drift.",
                "risk": "If baseline is captured too early, it may lock-in a suboptimal schema.",
                "action": "Add a controlled 'baseline update' step triggered only on Gate7 PASS.",
            }
        )

    # CF2: If Gate3 produced WARNs, what if we force proof requirements?
    g3_results = g3.get("results") or []
    warn_cnt = 0
    err_cnt = 0
    for r in g3_results:
        if isinstance(r, dict):
            lab = (r.get("label") or "").upper()
            if lab == "WARN":
                warn_cnt += 1
            if lab == "ERROR":
                err_cnt += 1

    if warn_cnt > 0:
        counterfactuals.append(
            {
                "id": "CF2_PROOF_FOR_WARN",
                "what_if": "If we require citations/evidence for each Gate3 WARN statement before Gate5 implementation.",
                "expected_benefit": "Reduces hallucination-driven design commitments.",
                "risk": "Slower iteration; may block on hard-to-verify items.",
                "action": "In future Perplexity-connected Gate3, promote WARN->FAIL based on severity tags.",
                "observed": {"g3_warn_count": warn_cnt},
            }
        )

    if err_cnt > 0:
        counterfactuals.append(
            {
                "id": "CF3_HARD_STOP_ON_ERROR",
                "what_if": "If any Gate3 ERROR occurs, we hard-stop the pipeline before Gate4/G5.",
                "expected_benefit": "Prevents implementation based on provably wrong assumptions.",
                "risk": "May over-trigger if ERROR heuristic is too strict.",
                "action": "Adjust state machine or Gate3 to mark ERROR as FAIL and enforce STOP/rollback.",
                "observed": {"g3_error_count": err_cnt},
            }
        )

    # CF4: If tests fail in Gate5, what if we capture richer diagnostics?
    g5_sum = _summarize_g5(g5)
    if g5_sum.get("returncode") not in (0, None):
        counterfactuals.append(
            {
                "id": "CF4_DIAGNOSTICS_ON_TEST_FAIL",
                "what_if": "If Gate5 tests fail, we auto-attach failing test names + short traceback summary.",
                "expected_benefit": "Faster debugging and less copy/paste.",
                "risk": "More code; must avoid leaking huge logs.",
                "action": "Parse pytest output or run pytest with -q plus a failure-summary mode.",
                "observed": {"g5": g5_sum},
            }
        )

    # CF5: If minimality is WARN, what if we enforce trimming?
    checks = g4.get("checks") or []
    minimality = next((c for c in checks if isinstance(c, dict) and c.get("check") == "minimality"), None)
    if minimality and minimality.get("label") == "WARN":
        counterfactuals.append(
            {
                "id": "CF5_TRIM_COMPLEXITY",
                "what_if": "If minimality is WARN, we enforce a reduction pass before proceeding.",
                "expected_benefit": "Less complexity → lower bug surface area.",
                "risk": "May remove useful constraints prematurely.",
                "action": "Add a 'simplification pass' gate or enforce max counts in G1.",
                "observed": {"minimality_reasons": minimality.get("reasons")},
            }
        )

    # Always include a generic counterfactual: swap tooling roles
    counterfactuals.append(
        {
            "id": "CF6_ROLE_SWAP",
            "what_if": "If Gemini/Codex roles are swapped (Gemini implements, Codex reviews), how would failure modes change?",
            "expected_benefit": "May improve implementation quality or review sharpness depending on model strengths.",
            "risk": "May reduce continuity/review effectiveness if memory/context handling differs.",
            "action": "Keep current ordering but add an optional 'implementation alternative' branch for comparison.",
        }
    )

    return counterfactuals


def _detect_conflicts(g2: Dict[str, Any], g4: Dict[str, Any], g5: Dict[str, Any]) -> List[str]:
    """
    Deterministic conflict flags (not web/AI):
    - If baseline present and Gate2 indicates removed fields (backward risk), flag.
    - If Gate4 decision rule indicates ERROR (should have failed already), flag.
    - If Gate5 failed tests but pipeline continued, flag (state machine allows; we still record).
    """
    conflicts: List[str] = []

    baseline_present = bool(g2.get("baseline_present", False))
    bd = g2.get("baseline_diff")
    if baseline_present and isinstance(bd, dict):
        removed = bd.get("removed") or []
        if removed:
            conflicts.append(f"G2 baseline removed fields detected: {len(removed)} removed")

    # Gate4 checks
    checks = g4.get("checks") or []
    for c in checks:
        if isinstance(c, dict) and (c.get("label") == "ERROR"):
            conflicts.append(f"G4 self-check ERROR: {c.get('check')}")

    # Gate5 result
    res = g5.get("result") or {}
    rc = res.get("returncode")
    if rc not in (0, None):
        conflicts.append(f"G5 tests failed (returncode={rc})")

    if res.get("timeout") is True:
        conflicts.append("G5 tests timed out")

    return conflicts


def gate_g6_counterfactual_review(ctx: GateContext) -> GateResult:
    run_dir = Path(ctx.run_dir).resolve()

    # Required inputs from prior real gates
    g1_path = run_dir / "G1_OUTPUT.json"
    g2_path = run_dir / "G2_OUTPUT.json"
    g3_path = run_dir / "G3_OUTPUT.json"
    g4_path = run_dir / "G4_OUTPUT.json"
    g5_path = run_dir / "G5_OUTPUT.json"

    for p in [g1_path, g2_path, g3_path, g4_path, g5_path]:
        if not p.exists():
            raise FileNotFoundError(f"{p.name} not found (Gate6 requires G1~G5 outputs)")

    g1 = _read_json(g1_path)
    g2 = _read_json(g2_path)
    g3 = _read_json(g3_path)
    g4 = _read_json(g4_path)
    g5 = _read_json(g5_path)

    counterfactuals = _derive_counterfactuals(g1, g2, g3, g4, g5)
    conflicts = _detect_conflicts(g2, g4, g5)

    # Decision: Gate6 is advisory by design; never FAIL here.
    # We keep PASS but record conflicts to inform Gate7.
    decision = Decision.PASS

    decision_md = (
        "# G6 COUNTERFACTUAL REVIEW DECISION\n\n"
        f"Decision: {decision.value}\n\n"
        "## Conflicts flagged\n"
        + (("\n".join([f"- {c}" for c in conflicts]) + "\n") if conflicts else "- None\n")
        + "\n## Counterfactuals generated\n"
        + "\n".join([f"- {cf.get('id')}: {cf.get('what_if')}" for cf in counterfactuals])
        + "\n"
    )
    (run_dir / "G6_DECISION.md").write_text(decision_md, encoding="utf-8")

    output = {
        "gate": "G6",
        "mode": "counterfactual_review_stub",
        "inputs": {
            "G1_OUTPUT.json": "G1_OUTPUT.json",
            "G2_OUTPUT.json": "G2_OUTPUT.json",
            "G3_OUTPUT.json": "G3_OUTPUT.json",
            "G4_OUTPUT.json": "G4_OUTPUT.json",
            "G5_OUTPUT.json": "G5_OUTPUT.json",
        },
        "conflicts": conflicts,
        "counterfactuals": counterfactuals,
        "notes": [
            "No AI used. Deterministic rule-based counterfactual generation.",
            "Gate6 is advisory; decision is always PASS in stub.",
        ],
    }
    (run_dir / "G6_OUTPUT.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    meta = {
        "gate": "G6",
        "decision": decision.value,
        "at": now_seoul().isoformat(),
        "attempt": ctx.meta.attempts.get("G6", 1),
    }
    (run_dir / "G6_META.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    outputs = {
        "G6_DECISION.md": "G6_DECISION.md",
        "G6_OUTPUT.json": "G6_OUTPUT.json",
        "G6_META.json": "G6_META.json",
    }
    standard_spec("G6").validate(outputs)

    return GateResult(
        decision=decision,
        message="Counterfactual review completed (stub)",
        outputs=outputs,
        meta={"conflicts_count": len(conflicts), "counterfactuals_count": len(counterfactuals)},
    )
