from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from src.models.decision_models import GateResult, Decision
from src.pipeline.runner import GateContext
from src.pipeline.contracts import standard_spec
from src.utils.time import now_seoul
from src.utils.env import load_dotenv
from src.providers.perplexity_provider import PerplexityProvider


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
    # Load .env once per gate execution (cheap, safe)
    load_dotenv()

    run_dir = Path(ctx.run_dir)
    g1_path = run_dir / "G1_OUTPUT.json"
    if not g1_path.exists():
        raise FileNotFoundError("G1_OUTPUT.json not found")

    g1 = json.loads(g1_path.read_text(encoding="utf-8"))
    candidates = _extract_fact_candidates(g1)

    provider = None
    # IMPORTANT: do not make real external calls during unit tests by default.
    # Enable Perplexity-based verification only when explicitly requested.
    is_pytest = os.getenv("PYTEST_CURRENT_TEST") is not None
    enable_flag = os.getenv("ENABLE_PERPLEXITY_FACT_AUDIT", "0").strip() in ("1", "true", "True", "yes", "YES")
    # Default behavior:
    # - Normal pipeline runs: external evidence check ON (intended role of G3)
    # - Pytest runs: external calls OFF unless explicitly enabled (keeps unit tests deterministic)
    enable_pplx = (not is_pytest) or enable_flag
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if enable_pplx and api_key:
        try:
            provider = PerplexityProvider(api_key)
        except Exception:
            provider = None

    results: List[Dict[str, Any]] = []
    fail_reasons: List[str] = []

    for stmt in candidates:
        if provider:
            try:
                r = provider.verify(stmt)
                label = r["verdict"]
                result = {
                    "statement": stmt,
                    "label": label,
                    "engine": "perplexity",
                    "confidence": r.get("confidence"),
                    "citations": r.get("citations"),
                    "summary": r.get("summary"),
                }
            except Exception as e:
                rb = _rule_based_audit(stmt)
                result = {
                    "statement": stmt,
                    "label": rb["label"],
                    "engine": "rule_fallback",
                    "reason": rb["reason"],
                    "error": str(e),
                }
        else:
            rb = _rule_based_audit(stmt)
            result = {
                "statement": stmt,
                "label": rb["label"],
                "engine": "rule_only",
                "reason": rb["reason"],
            }

        results.append(result)
        if result["label"] == "ERROR":
            fail_reasons.append(stmt)

    decision = Decision.FAIL if fail_reasons else Decision.PASS

    (run_dir / "G3_DECISION.md").write_text(
        "# G3 FACT AUDIT DECISION\n\n"
        f"Decision: {decision.value}\n\n"
        "## Fail reasons\n"
        + ("\n".join([f"- {s}" for s in fail_reasons]) if fail_reasons else "- None\n"),
        encoding="utf-8",
    )

    output = {
        "gate": "G3",
        "mode": "fact_audit_perplexity_if_available",
        "engine_used": "perplexity" if provider else "rule_only",
        "candidates": candidates,
        "results": results,
    }
    (run_dir / "G3_OUTPUT.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    meta = {
        "gate": "G3",
        "decision": decision.value,
        "at": now_seoul().isoformat(),
        "engine": "perplexity" if provider else "rule_only",
    }
    (run_dir / "G3_META.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    outputs = {
        "G3_DECISION.md": "G3_DECISION.md",
        "G3_OUTPUT.json": "G3_OUTPUT.json",
        "G3_META.json": "G3_META.json",
    }
    standard_spec("G3").validate(outputs)

    return GateResult(
        decision=decision,
        message="Fact audit completed",
        outputs=outputs,
        meta={"engine": meta["engine"], "fail_count": len(fail_reasons)},
    )
