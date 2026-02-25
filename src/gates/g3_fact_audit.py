from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from src.models.decision_models import GateResult, Decision
from src.pipeline.runner import GateContext
from src.gates.gate_common import write_standard_artifacts
from src.pipeline.stop_reason import StopReason
from src.utils.env import load_dotenv
from src.platform import g3_fact_audit_plugin


FACT_PATTERNS = [
    r"\b(always|never|guarantee|guaranteed)\b",
    r"\b(\d+%|\d+\.\d+%|\d+\/\d+)\b",
    r"\b(must|will)\b",
    r"\b(best|optimal|only)\b",
]


def _flatten_text(obj: Any) -> List[str]:
    out: List[str] = []
    if isinstance(obj, dict):
        for v in obj.values():
            out.extend(_flatten_text(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_flatten_text(v))
    elif isinstance(obj, str):
        out.append(obj)
    return out


def _extract_fact_candidates(g1: Dict[str, Any]) -> List[str]:
    texts = _flatten_text(g1)
    cands: List[str] = []
    for t in texts:
        for pat in FACT_PATTERNS:
            if re.search(pat, t, flags=re.IGNORECASE):
                cands.append(t)
                break
    return sorted(set(cands))


def _rule_based_audit(statement: str) -> Dict[str, Any]:
    s = statement.lower()
    if "always" in s and "except" in s:
        return {"label": "ERROR", "reason": "Self-contradictory absolute claim."}
    if any(k in s for k in ["always", "never", "guarantee", "only", "best"]):
        return {"label": "WARN", "reason": "Absolute claim; needs verification."}
    return {"label": "OK", "reason": "Design intent / neutral."}


def gate_g3_fact_audit(ctx: GateContext) -> GateResult:
    is_pytest = os.getenv("PYTEST_CURRENT_TEST") is not None

    if not is_pytest:
        load_dotenv()

    run_dir = Path(ctx.run_dir)
    g1_path = run_dir / "G1_OUTPUT.json"
    if not g1_path.exists():
        raise FileNotFoundError("G1_OUTPUT.json not found")

    g1 = json.loads(g1_path.read_text(encoding="utf-8"))
    candidates = _extract_fact_candidates(g1)

    injected_provider = None
    try:
        injected_provider = ctx.providers.get("perplexity") if getattr(ctx, "providers", None) else None
    except Exception:
        injected_provider = None

    enable_tests_flag = os.getenv("ENABLE_PERPLEXITY_FACT_AUDIT_TESTS", "0").strip() in ("1", "true", "True", "yes", "YES")
    enable_pplx = (not is_pytest) or enable_tests_flag

    plugins = ctx.context.get("plugins") if isinstance(ctx.context, dict) else None
    fact_check = g3_fact_audit_plugin.resolve(ctx) if enable_pplx else None

    results: List[Dict[str, Any]] = []
    fail_reasons: List[str] = []
    stop_error: str = ""

    provider_required = bool(enable_pplx) and (not is_pytest)

    if provider_required and fact_check is None:
        stop_error = "Fact-check plugin/provider unavailable"

    for stmt in candidates:
        if stop_error:
            break

        if fact_check is None:
            rb = _rule_based_audit(stmt)
            results.append({
                "statement": stmt,
                "label": rb["label"],
                "engine": "rule_only",
                "reason": rb["reason"],
            })
            if rb["label"] == "ERROR":
                fail_reasons.append(stmt)
            continue

        try:
            r = fact_check.verify(stmt)
            label = r.get("verdict", "UNKNOWN")
            results.append({
                "statement": stmt,
                "label": label,
                "engine": ("plugin" if plugins and isinstance(plugins, dict) and plugins.get("fact_check") is not None else "perplexity"),
                "confidence": r.get("confidence"),
                "citations": r.get("citations"),
                "summary": r.get("summary"),
            })
            if label == "ERROR":
                fail_reasons.append(stmt)
        except Exception as e:
            stop_error = str(e)
            break

    from src.policy.gate_policy import evaluate_g3

    policy = evaluate_g3(
        stop_error=stop_error,
        fail_reasons_count=len(fail_reasons),
    )

    decision = policy.decision

    decision_md = (
        "# G3 FACT AUDIT DECISION\n\n"
        f"Decision: {decision.value}\n\n"
        "## Fail reasons\n"
        + ("\n".join([f"- {s}" for s in fail_reasons]) if fail_reasons else "- None\n")
        + "\n\n## Stop reason\n"
        + (f"- {stop_error}\n" if decision == Decision.STOP else "- None\n")
    )

    output = {
        "gate": "G3",
        "engine_used": "perplexity" if (fact_check is not None and enable_pplx) else "rule_only",
        "stop_error": stop_error,
        "candidates": candidates,
        "results": results,
    }

    outputs = write_standard_artifacts("G3", decision, decision_md, output, ctx)

    meta = {
        "reason_trace": getattr(policy, "reason_trace", []),
        "engine": "perplexity" if (fact_check is not None and enable_pplx) else "rule_only",
        "fail_count": len(fail_reasons),
        "stop_error": stop_error,
    }

    if policy.stop_reason:
        meta["stop_reason"] = policy.stop_reason
        meta["stop_detail"] = policy.stop_detail

    return GateResult(
        decision=decision,
        message="Fact audit completed",
        outputs=outputs,
        meta=meta,
    )
