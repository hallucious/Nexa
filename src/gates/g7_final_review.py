# -*- coding: utf-8 -*-
"""
G7 Final Review

Responsibilities (as exercised by test-suite):
- Read prior gate artifacts (DECISION + OUTPUT) and decide PASS/FAIL/STOP.
- Always write standard artifacts via gate_common.write_standard_artifacts:
    G7_DECISION.md, G7_OUTPUT.json, G7_META.json
- In non-pytest execution, optionally use injected provider ctx.providers["gpt"] (best-effort)
  and record provider result in output JSON with:
    provider.used == True/False and provider.text == "..."
- Provide baseline recommendation block:
    baseline_recommendation.recommend_update is boolean
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from src.gates.gate_common import (
    Decision,
    GateContext,
    GateResult,
    format_standard_decision_md,
    is_pytest,
    read_json_file,
    read_text_file,
    write_standard_artifacts,
)
from src.platform.g7_final_review_plugin import resolve_g7_final_review_plugin

# ----------------------------
# helpers
# ----------------------------

def _read_gate_decision(run_dir: Path, gate_id: str) -> Optional[str]:
    p = run_dir / f"{gate_id}_DECISION.md"
    if not p.exists():
        return None
    t = read_text_file(p) or ""
    # very small parser: look for "Decision: XXX"
    for line in t.splitlines():
        if line.strip().lower().startswith("decision:"):
            return line.split(":", 1)[1].strip().upper()
    return None


def _safe_provider_call(ctx: GateContext, prompt: str) -> Dict[str, Any]:
    """Best-effort provider call (non-pytest) via plugin resolver."""

    info: Dict[str, Any] = {
        "engine": "gpt",
        "used": False,
        "text": "",
        "meta": {},
        "model_name": None,
    }

    if is_pytest():
        return info

    plugin = resolve_g7_final_review_plugin(ctx)
    if plugin is None:
        return info

    try:
        text, meta = plugin.generate(prompt)
        info["used"] = True
        info["text"] = str(text or "")
        info["meta"] = {
            **(meta or {}),
            "prompt_len": len(prompt or ""),
        }
        info["model_name"] = (meta or {}).get("model") or (meta or {}).get("model_name")
        return info
    except Exception as e:
        info["meta"] = {"error": type(e).__name__, "detail": str(e)}
        return info


def _baseline_recommendation(run_dir: Path) -> Dict[str, Any]:
    """
    Deterministic baseline recommendation:
    - if G2 says baseline_present == True => recommend_update False
    - else recommend_update True
    """
    g2 = read_json_file(run_dir / "G2_OUTPUT.json") or {}
    baseline_present = bool(g2.get("baseline_present", False))
    recommend_update = not baseline_present
    reason = "Baseline missing; recommend creating/updating baseline." if recommend_update else "Baseline present; no update recommended."
    return {
        "recommend_update": recommend_update,
        "reason": reason,
        "baseline_present": baseline_present,
    }


# ----------------------------
# gate
# ----------------------------

def gate_g7_final_review(ctx: GateContext) -> GateResult:
    run_dir = Path(ctx.run_dir)

    # Determine if any prior gate STOP/FAIL
    prior = ["G1", "G2", "G3", "G4", "G5", "G6"]
    decisions: Dict[str, Optional[str]] = {gid: _read_gate_decision(run_dir, gid) for gid in prior}

    if any(v == "STOP" for v in decisions.values()):
        decision = Decision.STOP
        summary = "Upstream STOP detected."
    elif any(v == "FAIL" for v in decisions.values()):
        decision = Decision.FAIL
        summary = "Upstream FAIL detected."
    else:
        decision = Decision.PASS
        summary = "All gates passed; artifacts written."

    baseline_rec = _baseline_recommendation(run_dir)

    # optional provider call (non-pytest)
    prompt = (
        "Final review: summarize run status and baseline recommendation.\n"
        f"decision={decision.value}\n"
        f"baseline_present={baseline_rec.get('baseline_present')}\n"
    )
    provider_info = _safe_provider_call(ctx, prompt)

    output_payload: Dict[str, Any] = {
        "gate": "G7",
        "status": decision.value.lower(),
        "summary": summary,
        "baseline_recommendation": baseline_rec,
        "provider": provider_info,
    }

    decision_md = format_standard_decision_md(
        gate_id="G7",
        title="Final Review",
        decision=decision,
        summary=summary,
        inputs={
            "prior_decisions": {k: (v or "MISSING") for k, v in decisions.items()},
            "baseline_present": bool(baseline_rec.get("baseline_present", False)),
        },
        outputs={
            "recommend_update": bool(baseline_rec.get("recommend_update", False)),
            "provider_used": bool(provider_info.get("used", False)),
        },
        notes=[
            "G7 aggregates upstream decisions and emits final standardized artifacts.",
            "Provider call (if any) is best-effort and does not affect PASS/FAIL/STOP.",
        ],
    )

    artifacts = write_standard_artifacts(
        ctx=ctx,
        gate_id="G7",
        decision=decision,
        decision_md=decision_md,
        output_dict=output_payload,
    )

    return GateResult(
        decision=decision,
        message=summary,
        outputs=artifacts,
        meta={},
    )