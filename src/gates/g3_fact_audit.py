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
    # Determine whether we're running under pytest.
    is_pytest = os.getenv("PYTEST_CURRENT_TEST") is not None

    # Load .env for normal runs only. Pytest must remain deterministic even if .env exists.
    if not is_pytest:
        load_dotenv()

    run_dir = Path(ctx.run_dir)
    g1_path = run_dir / "G1_OUTPUT.json"
    if not g1_path.exists():
        raise FileNotFoundError("G1_OUTPUT.json not found")

    g1 = json.loads(g1_path.read_text(encoding="utf-8"))
    candidates = _extract_fact_candidates(g1)

    provider = None
    # IMPORTANT: do not make real external calls during unit tests by default.
    # If you *really* want Perplexity in pytest, set ENABLE_PERPLEXITY_FACT_AUDIT_TESTS=1 explicitly.
    enable_tests_flag = os.getenv("ENABLE_PERPLEXITY_FACT_AUDIT_TESTS", "0").strip() in ("1", "true", "True", "yes", "YES")
    enable_pplx = (not is_pytest) or enable_tests_flag
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if enable_pplx and api_key:
        try:
            provider = PerplexityProvider(api_key)
        except Exception:
            provider = None

    results: List[Dict[str, Any]] = []
    fail_reasons: List[str] = []
    stop_error: str = ""

    def _extract_category(err: BaseException) -> str:
        m = re.search(r"category=([A-Z_]+)", str(err))
        return m.group(1) if m else "UNKNOWN_ERROR"

    # If external evidence checking is required (normal pipeline run) but provider is unavailable, STOP.
    provider_required = bool(enable_pplx) and (not is_pytest)

    if provider_required and provider is None:
        stop_error = "UNKNOWN_ERROR: Perplexity provider unavailable (missing key or init failure)"

    for stmt in candidates:
        if stop_error:
            break

        # If Perplexity is disabled (pytest default) we can only do local rule checks.
        if provider is None:
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
            continue

        # Normal pipeline: Perplexity-based evidence check is non-optional.
        try:
            r = provider.verify(stmt)
            label = r.get("verdict", "UNKNOWN")
            result = {
                "statement": stmt,
                "label": label,
                "engine": "perplexity",
                "confidence": r.get("confidence"),
                "citations": r.get("citations"),
                "summary": r.get("summary"),
            }
            results.append(result)

            if label == "ERROR":
                fail_reasons.append(stmt)

        except Exception as e:  # noqa: BLE001
            cat = _extract_category(e)

            # If we cannot execute verification due to system instability, we STOP.
            if cat in ("UNKNOWN_ERROR", "TRANSIENT_ERROR"):
                stop_error = f"{cat}: {e}"
                break

            # If the request itself is invalid/policy/too-long, treat as FAIL.
            if cat in ("POLICY_REFUSAL", "INVALID_REQUEST", "TOO_LONG"):
                result = {
                    "statement": stmt,
                    "label": "ERROR",
                    "engine": "perplexity_error",
                    "category": cat,
                    "error": str(e),
                }
                results.append(result)
                fail_reasons.append(stmt)
                continue

            stop_error = f"{cat}: {e}"
            break

    # Decide
    if stop_error:
        decision = Decision.STOP
    else:
        decision = Decision.FAIL if fail_reasons else Decision.PASS

    (run_dir / "G3_DECISION.md").write_text(
        "# G3 FACT AUDIT DECISION\n\n"
        f"Decision: {decision.value}\n\n"
        "## Fail reasons\n"
        + ("\n".join([f"- {s}" for s in fail_reasons]) if fail_reasons else "- None\n")
        + "\n\n## Stop reason\n"
        + (f"- {stop_error}\n" if decision == Decision.STOP else "- None\n"),
        encoding="utf-8",
    )

    output = {
        "gate": "G3",
        "mode": "fact_audit_perplexity",
        "engine_used": "perplexity" if provider is not None else "rule_only",
        "stop_error": stop_error,
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
        meta={"engine": meta["engine"], "fail_count": len(fail_reasons), "stop_error": stop_error},
    )