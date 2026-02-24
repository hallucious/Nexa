# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Gate G6: Counterfactual review.

Purpose
- Provide a lightweight "what could go wrong?" check after implementation/tests.
- Deterministic checks must remain stable under pytest.
- Runtime-only provider call is best-effort; it must never change PASS/FAIL semantics.

Artifacts
- G6_DECISION.md
- G6_OUTPUT.json
- G6_META.json
"""

import re


import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.gates.gate_common import (
    Decision,
    GateContext,
    GateResult,
    format_standard_decision_md,
    is_pytest,
    now_seoul,
    read_text_file,
    stable_json_dumps,
    write_standard_artifacts,
)


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _find_repo_root(run_dir: Path) -> Path:
    """
    Find repo root by walking upward until 'runs' exists.
    Test harness creates: repo/runs/<run_id>. We start inside <run_id>.
    """
    p = run_dir.resolve()
    for _ in range(6):
        if (p / "runs").exists():
            return p
        p = p.parent
    # Fallback: assume parent of run_dir is runs; then its parent is repo.
    return run_dir.parent.parent


def _counterfactual_checks_from_request(request_text: str) -> List[Dict[str, Any]]:
    """Lightweight, deterministic counterfactual checks over the user request.

    Design intent for this project/test-suite:
    - G6 should be conservative and *not* fail on marketing/superlative language like "best".
      Those belong in G3 as WARN, not as a counterfactual FAIL.
    - G6 should only FAIL on *hard impossibility / absolute guarantees* that are likely false
      in real systems and often indicate mis-specified expectations.
    """
    if not request_text:
        return []

    text = request_text.strip()
    t = text.lower()

    patterns = [
        # absolute guarantees / impossibilities
        (r"\b(guarantee|guaranteed|100%|always)\b", "ABSOLUTE_GUARANTEE"),
        (r"\b(impossible|cannot fail|can't fail|never fail|zero failure)\b", "IMPOSSIBLE_CLAIM"),
        (r"\b(no bugs|bug[- ]free|perfect)\b", "PERFECTION_CLAIM"),
    ]

    conflicts: List[Dict[str, Any]] = []
    for pat, code in patterns:
        m = re.search(pat, t)
        if not m:
            continue
        conflicts.append({
            "reason_code": code,
            "snippet": _extract_snippet(text, m.start(), m.end()),
            "detail": f"Request contains strong absolute claim: {m.group(0)!r}",
        })

    return conflicts
def _extract_snippet(text: str, needle: str, radius: int = 40) -> str:
    low = text.lower()
    idx = low.find(needle.lower())
    if idx < 0:
        return ""
    start = max(0, idx - radius)
    end = min(len(text), idx + len(needle) + radius)
    return text[start:end].replace("\n", " ").strip()


def _provider_generate_text(provider: Any, prompt: str) -> Tuple[str, Dict[str, Any], Optional[str]]:
    """
    Normalize provider.generate_text across stubs/implementations.

    Expected (preferred):
      provider.generate_text(prompt=..., temperature=..., max_output_tokens=...) -> (text, meta, err)

    Fallback:
      provider.generate_text(prompt) -> str OR (text, meta, err) OR tuple-like
    """
    # Preferred signature
    try:
        res = provider.generate_text(prompt=prompt, temperature=0.0, max_output_tokens=256)
        if isinstance(res, tuple) and len(res) >= 1:
            text = str(res[0] if res[0] is not None else "")
            meta = res[1] if len(res) >= 2 and isinstance(res[1], dict) else {}
            err = res[2] if len(res) >= 3 else None
            return text, meta, err
        return str(res), {}, None
    except TypeError:
        # Fallback: positional
        res = provider.generate_text(prompt)
        if isinstance(res, tuple) and len(res) >= 1:
            text = str(res[0] if res[0] is not None else "")
            meta = res[1] if len(res) >= 2 and isinstance(res[1], dict) else {}
            err = res[2] if len(res) >= 3 else None
            return text, meta, err
        return str(res), {}, None
    except Exception as e:  # noqa: BLE001
        return "", {}, f"{type(e).__name__}: {e}"


def _try_runtime_provider_call(ctx: GateContext) -> Dict[str, Any]:
    """
    Best-effort runtime-only provider call.
    - Must NEVER change decision.
    - Skipped under pytest to keep tests deterministic.
    """
    if is_pytest():
        return {}

    providers = (ctx.providers or {})
    engine = "gemini" if "gemini" in providers else ("gpt" if "gpt" in providers else "")
    provider = providers.get(engine) if engine else None
    if provider is None:
        return {"provider": {"used": False, "engine": None}}

    run_dir = Path(ctx.run_dir)
    g1 = _read_json(run_dir / "G1_OUTPUT.json")

    prompt = (
        "You are Gate6 (Counterfactual Review). "
        "Given the design summary (G1 output JSON), generate 2 short counterfactual checks.\n"
        "- Output plain text (two bullet points is fine).\n\n"
        f"G1_OUTPUT:\n{stable_json_dumps(g1 or {})}\n"
    )

    text, meta, err = _provider_generate_text(provider, prompt)
    used = (err is None) and bool(text.strip())

    out: Dict[str, Any] = {
        "provider": {
            "used": used,
            "engine": engine,
            "model_name": getattr(provider, "model", None),
        }
    }
    if used:
        out["provider"]["text"] = text.strip()
        out["provider"]["meta"] = meta
    else:
        out["provider"]["error"] = err or "empty_output"
    return out


def gate_g6_counterfactual_review(ctx: GateContext) -> GateResult:
    run_dir = Path(ctx.run_dir)

    # Inputs
    request_text = read_text_file(run_dir / "00_USER_REQUEST.md")
    conflicts = _counterfactual_checks_from_request(request_text)

    from src.policy.gate_policy import evaluate_g6
    policy = evaluate_g6(conflicts_count=len(conflicts))
    decision = policy.decision

    # Runtime provider (optional)
    provider_info = _try_runtime_provider_call(ctx)

    summary = policy.message

    output = {
        "gate": "G6",
        "status": decision.value.lower(),
        "summary": summary,
        "counterfactuals": conflicts,
        "conflicts": conflicts,  # legacy alias
    }
    output.update(provider_info)

    decision_md = format_standard_decision_md(
        gate_id="G6",
        title="Counterfactual Review",
        decision=decision,
        summary=summary,
        inputs={
            "request_len": len(request_text or ""),
        },
        outputs={
            "conflicts_count": len(conflicts),
            "provider_used": bool(provider_info.get("provider", {}).get("used", False)),
        },
        notes=[
            "Deterministic checks are heuristic and intentionally conservative.",
            "Provider call (if any) is best-effort and does not affect PASS/FAIL.",
        ],
    )

    artifacts = write_standard_artifacts(
        ctx=ctx,
        gate_id="G6",
        decision=decision,
        decision_md=decision_md,
        output=output,
    )

    return GateResult(
        decision=decision,
        message=summary,
        outputs=artifacts,
    )
