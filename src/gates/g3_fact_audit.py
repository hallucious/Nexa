from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from src.models.decision_models import GateResult, Decision
from src.pipeline.runner import GateContext
from src.pipeline.contracts import standard_spec
from src.utils.time import now_seoul


# --- Heuristic extractors (deterministic, no AI) ---

FACT_PATTERNS = [
    r"\b(always|never|guarantee|guaranteed)\b",
    r"\b(\d+%|\d+\.\d+%|\d+\/\d+)\b",
    r"\b(must|will)\b",
    r"\b(best|optimal|only)\b",
]


def _flatten_text(obj: Any) -> List[str]:
    """
    Collect text leaves from JSON-like object.
    """
    texts: List[str] = []
    if isinstance(obj, dict):
        for v in obj.values():
            texts.extend(_flatten_text(v))
    elif isinstance(obj, list):
        for v in obj:
            texts.extend(_flatten_text(v))
    elif isinstance(obj, str):
        texts.append(obj)
    return texts


def _extract_fact_candidates(g1: Dict[str, Any]) -> List[str]:
    texts = _flatten_text(g1)
    candidates: List[str] = []
    for t in texts:
        for pat in FACT_PATTERNS:
            if re.search(pat, t, flags=re.IGNORECASE):
                candidates.append(t)
                break
    return sorted(set(candidates))


def _rule_based_audit(statement: str) -> Dict[str, Any]:
    """
    Deterministic audit without web access.
    Labels:
      - ERROR: provably false by internal contradiction keywords (rare)
      - WARN: unverifiable / absolute claims
      - OK: neutral / design intent
    """
    s = statement.lower()
    if "always" in s and "except" in s:
        return {"label": "ERROR", "reason": "Self-contradictory absolute claim."}
    if any(k in s for k in ["always", "never", "guarantee", "guaranteed", "only", "best"]):
        return {"label": "WARN", "reason": "Absolute or marketing-like claim; needs external verification."}
    return {"label": "OK", "reason": "Design intent or non-factual statement."}


def gate_g3_fact_audit(ctx: GateContext) -> GateResult:
    run_dir = Path(ctx.run_dir)
    g1_path = run_dir / "G1_OUTPUT.json"
    if not g1_path.exists():
        raise FileNotFoundError("G1_OUTPUT.json not found (Gate3 requires Gate1 output)")

    g1 = json.loads(g1_path.read_text(encoding="utf-8"))
    candidates = _extract_fact_candidates(g1)

    audited: List[Dict[str, Any]] = []
    fail_reasons: List[str] = []

    for c in candidates:
        res = _rule_based_audit(c)
        audited.append({"statement": c, **res})
        if res["label"] == "ERROR":
            fail_reasons.append(f"Provable error: {c}")

    decision = Decision.FAIL if fail_reasons else Decision.PASS

    # --- write artifacts ---
    decision_md = (
        "# G3 FACT AUDIT DECISION\n\n"
        f"Decision: {decision.value}\n\n"
        "## Summary\n"
        f"- Candidates audited: {len(audited)}\n\n"
        "## Fail reasons\n"
        + (("\n".join([f"- {r}" for r in fail_reasons]) + "\n") if fail_reasons else "- None\n")
    )
    (run_dir / "G3_DECISION.md").write_text(decision_md, encoding="utf-8")

    output = {
        "gate": "G3",
        "mode": "fact_audit_stub",
        "candidates": candidates,
        "results": audited,
        "notes": [
            "No external search performed.",
            "Labels are heuristic and deterministic.",
        ],
    }
    (run_dir / "G3_OUTPUT.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    meta = {
        "gate": "G3",
        "decision": decision.value,
        "at": now_seoul().isoformat(),
        "attempt": ctx.meta.attempts.get("G3", 1),
        "inputs": {"G1_OUTPUT.json": "G1_OUTPUT.json"},
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
        message="Fact audit completed (stub)",
        outputs=outputs,
        meta={"fail_reasons": fail_reasons},
    )
