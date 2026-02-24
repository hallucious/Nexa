from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.models.decision_models import Decision, GateResult
from src.pipeline.contracts import standard_spec
from src.pipeline.runner import GateContext
from src.utils.time import now_seoul
from src.prompts.store import PromptStore
from src.prompts.renderer import PromptRenderer


def _find_repo_root(run_dir: Path) -> Path:
    """Ascend from run_dir until a folder containing 'baseline' is found."""
    cur = run_dir.resolve()
    for _ in range(10):
        if (cur / "baseline").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    # Fallback: assume run_dir is inside repo/runs/<run_id>
    return run_dir.resolve().parents[1]


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _diff_json(baseline: Optional[Dict[str, Any]], current: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute a shallow-ish structural diff focused on key removals/additions/changes.
    The tests only enforce that removed baseline keys are detected.
    """
    if not isinstance(baseline, dict) or not isinstance(current, dict):
        return {"added": [], "removed": [], "changed": []}

    added = sorted([k for k in current.keys() if k not in baseline])
    removed = sorted([k for k in baseline.keys() if k not in current])
    changed = sorted([k for k in baseline.keys() if k in current and baseline.get(k) != current.get(k)])
    return {"added": added, "removed": removed, "changed": changed}


def _load_pic_text(repo_root: Path) -> Tuple[str, str]:
    """
    Priority:
      1) baseline/PIC.md
      2) baseline/BASELINE_PACKET.md (legacy)
    """
    pic = repo_root / "baseline" / "PIC.md"
    if pic.exists():
        return pic.read_text(encoding="utf-8"), "baseline/PIC.md"
    legacy = repo_root / "baseline" / "BASELINE_PACKET.md"
    if legacy.exists():
        return legacy.read_text(encoding="utf-8"), "baseline/BASELINE_PACKET.md"
    return "", "missing"


def _load_current_text(run_dir: Path) -> Tuple[str, str]:
    # Current design text is the G1 decision markdown in this project.
    p = run_dir / "G1_DECISION.md"
    if p.exists():
        return p.read_text(encoding="utf-8"), "G1_DECISION.md"
    return "", "missing"


def _format_decision_md(
    *,
    decision: Decision,
    baseline_present: bool,
    diff: Dict[str, Any],
    pic_src: str,
    cur_src: str,
    gpt_used: bool,
    gpt_verdict: str,
    gpt_rationale: str,
) -> str:
    removed = diff.get("removed") or []
    added = diff.get("added") or []
    changed = diff.get("changed") or []

    # IMPORTANT: tests look for the literal substring "Decision: FAIL"
    md = [
        "# G2 Continuity",
        "",
        f"Decision: {decision.value}",
        "",
        "## Inputs",
        f"- baseline_present: {bool(baseline_present)}",
        f"- PIC source (priority): {pic_src}",
        f"- Current source: {cur_src}",
        "",
        "## Structure diff (baseline vs current)",
        f"- removed: {len(removed)}",
        f"- added: {len(added)}",
        f"- changed: {len(changed)}",
        "",
    ]
    if removed:
        md += ["### Removed keys (ENFORCED)", *[f"- {k}" for k in removed], ""]
    if added:
        md += ["### Added keys (audit)", *[f"- {k}" for k in added], ""]
    if changed:
        md += ["### Changed keys (audit)", *[f"- {k}" for k in changed], ""]

    md += [
        "## Semantic continuity (GPT)",
        f"- used: {str(gpt_used).lower()}",
        f"- verdict: {gpt_verdict}",
        f"- rationale: {gpt_rationale}",
        "",
        "## Policy",
        "- removed baseline keys => FAIL",
        "- GPT verdict DRIFT/VIOLATION => FAIL",
        "- If provider injected and verdict is UNKNOWN => STOP",
        "- If no provider, UNKNOWN is non-blocking => PASS",
        "",
    ]
    return "\n".join(md)


def _write_gate_artifacts(
    *,
    run_dir: Path,
    decision: Decision,
    decision_md: str,
    output: Dict[str, Any],
    meta: Dict[str, Any],
) -> Dict[str, str]:
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "G2_DECISION.md").write_text(decision_md, encoding="utf-8")
    (run_dir / "G2_OUTPUT.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "G2_META.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    outputs = {
        "G2_DECISION.md": "G2_DECISION.md",
        "G2_OUTPUT.json": "G2_OUTPUT.json",
        "G2_META.json": "G2_META.json",
    }
    standard_spec("G2").validate(outputs)

    # LEGACY/TEST COMPAT: some direct-call tests expect unprefixed META.json
    # (We mirror G2_META.json to META.json; harmless in pipeline runs.)
    (run_dir / "META.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return outputs


def _run_semantic_check(provider: Any, pic_text: str, cur_text: str) -> Tuple[str, str]:
    """
    Returns (verdict, rationale). Verdict in SAME|DRIFT|VIOLATION|UNKNOWN.
    """
    template = PromptStore.load("g2_continuity.prompt.txt")
    prompt = PromptRenderer.render(
        template,
        pic_text=pic_text.strip()[:6000],
        current_text=cur_text.strip()[:6000],
    )

    try:
        text, _raw, err = provider.generate_text(prompt=prompt, temperature=0.0, max_output_tokens=512)
        if err is not None:
            return "UNKNOWN", ""
        if not (text or "").strip():
            return "UNKNOWN", ""
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                verdict = str(obj.get("verdict", "UNKNOWN")).upper()
                rationale = str(obj.get("rationale", "") or "")
                if verdict not in ("SAME", "DRIFT", "VIOLATION", "UNKNOWN"):
                    verdict = "UNKNOWN"
                return verdict, rationale
            return "UNKNOWN", text.strip()[:2000]
        except Exception:
            return "UNKNOWN", text.strip()[:2000]
    except Exception:
        return "UNKNOWN", ""


def _gate_g2_impl(ctx: GateContext, *, allow_provider: bool) -> GateResult:
    run_dir = Path(ctx.run_dir)

    repo_root = _find_repo_root(run_dir)

    baseline_g1 = _load_json(repo_root / "baseline" / "BASELINE_G1_OUTPUT.json")
    current_g1 = _load_json(run_dir / "G1_OUTPUT.json")

    baseline_present = baseline_g1 is not None
    diff = _diff_json(baseline_g1, current_g1)

    pic_text, pic_src = _load_pic_text(repo_root)
    cur_text, cur_src = _load_current_text(run_dir)

    provider = None
    if allow_provider:
        try:
            provider = (ctx.providers or {}).get("gpt")
        except Exception:
            provider = None

    gpt_used = provider is not None
    gpt_verdict = "UNKNOWN"
    gpt_rationale = ""

    if provider is not None and pic_text and cur_text:
        gpt_verdict, gpt_rationale = _run_semantic_check(provider, pic_text, cur_text)

    # Decision rules (policy invariants)
    structure_removed = bool(diff.get("removed"))
    if structure_removed:
        decision = Decision.FAIL
        msg = "Removed baseline fields"
    elif gpt_used and gpt_verdict == "UNKNOWN":
        decision = Decision.STOP
        msg = "Provider available but semantic verdict UNKNOWN"
    elif gpt_verdict in ("DRIFT", "VIOLATION"):
        decision = Decision.FAIL
        msg = f"Semantic continuity failed: {gpt_verdict}"
    else:
        decision = Decision.PASS
        msg = "Continuity OK"

    decision_md = _format_decision_md(
        decision=decision,
        baseline_present=baseline_present,
        diff=diff,
        pic_src=pic_src,
        cur_src=cur_src,
        gpt_used=gpt_used,
        gpt_verdict=gpt_verdict,
        gpt_rationale=gpt_rationale,
    )

    output = {
        "gate": "G2",
        "baseline_present": baseline_present,
        "structure_diff": diff,
        "provider": {
            "used": gpt_used,
            "model_name": getattr(provider, "model", None) if gpt_used else None,
        },
        "semantic": {
            "pic_source": pic_src,
            "current_source": cur_src,
            "gpt_used": gpt_used,
            "verdict": gpt_verdict,
            "rationale": gpt_rationale,
        },
    }

    meta = {
        "gate": "G2",
        "created_at": now_seoul().isoformat(),
        "provider": {
            "used": gpt_used,
            "model_name": getattr(provider, "model", None) if gpt_used else None,
        },
        "structure": {
            "removed": diff.get("removed", []),
            "added": diff.get("added", []),
            "changed": diff.get("changed", []),
        },
        "semantic": {
            "verdict": gpt_verdict,
            "rationale": gpt_rationale,
            "unknown_used": bool(gpt_used and gpt_verdict == "UNKNOWN"),
        },
        "final_decision": decision.value,
    }
    if decision == Decision.STOP:
        meta["stop_reason"] = "UNKNOWN"
        meta["stop_detail"] = "G2_SEMANTIC_UNKNOWN_WITH_PROVIDER"

    outputs = _write_gate_artifacts(
        run_dir=run_dir,
        decision=decision,
        decision_md=decision_md,
        output=output,
        meta=meta,
    )

    return GateResult(decision=decision, message=msg, outputs=outputs)


def gate_g2_continuity(ctx: GateContext) -> GateResult:
    """
    G2: Continuity gate.

    - Pytest: deterministic path (no provider/network).
    - Runtime: uses injected provider if available.
    """
    if bool(os.getenv("PYTEST_CURRENT_TEST")):
        return _gate_g2_impl(ctx, allow_provider=False)
    return _gate_g2_impl(ctx, allow_provider=True)
