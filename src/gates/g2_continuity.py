# src/gates/g2_continuity.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.models.decision_models import Decision, GateResult
from src.pipeline.runner import GateContext
from src.utils.time import now_seoul

# NOTE:
# - Gemini provider is optional. Gate2 must still run (deterministically) without network.
# - If Gemini is unavailable -> verdict UNKNOWN (non-blocking), but structure rules still apply.
try:
    from src.providers.gemini_provider import GeminiProvider
except Exception:  # pragma: no cover
    GeminiProvider = None  # type: ignore


# SAFE_MODE linkage (optional): Gate2 can explain continuity decisions when SAFE_MODE rewrites/chunks prompts.
try:
    from src.providers.safe_mode import get_last_safe_mode_result, get_safe_mode_link_mode
except Exception:  # pragma: no cover
    get_last_safe_mode_result = None  # type: ignore
    get_safe_mode_link_mode = None  # type: ignore


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _find_repo_root(run_dir: Path) -> Path:
    """
    run_dir is expected like: <repo>/runs/<RUN_ID>
    """
    # runs/<id> -> repo root
    return run_dir.parent.parent


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_baseline_g1(repo_root: Path) -> Optional[Dict[str, Any]]:
    return _load_json(repo_root / "baseline" / "BASELINE_G1_OUTPUT.json")


def _load_current_g1(run_dir: Path) -> Optional[Dict[str, Any]]:
    return _load_json(run_dir / "G1_OUTPUT.json")


def _diff_json(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Shallow, key-level diff for audit purposes.

    - added: keys present in b but not in a
    - removed: keys present in a but not in b
    - changed: keys present in both but with different JSON-serialized value
    """
    a_keys = set(a.keys())
    b_keys = set(b.keys())

    added = sorted(list(b_keys - a_keys))
    removed = sorted(list(a_keys - b_keys))

    changed: List[str] = []
    for k in sorted(list(a_keys & b_keys)):
        try:
            if json.dumps(a.get(k), sort_keys=True, ensure_ascii=False) != json.dumps(
                b.get(k), sort_keys=True, ensure_ascii=False
            ):
                changed.append(k)
        except Exception:
            changed.append(k)

    return {"added": added, "removed": removed, "changed": changed}


def _format_decision_md(
    *,
    decision: Decision,
    baseline_present: bool,
    previous_present: bool,
    diff: Dict[str, List[str]],
    gemini_used: bool,
    gemini_verdict: str,
    gemini_rationale: str,
    notes: str,
    safe_mode_link: str,
    safe_mode_last: Optional[Dict[str, Any]],
) -> str:
    removed = diff.get("removed", [])
    added = diff.get("added", [])
    changed = diff.get("changed", [])

    md = []
    md.append("# G2 CONTINUITY DECISION\n")
    md.append(f"Decision: {decision.value}\n")
    md.append("## Summary\n")
    md.append(f"- Baseline present: {baseline_present}\n")
    md.append(f"- Previous run present: {previous_present}\n")
    md.append(f"- JSON diff: added={len(added)}, removed={len(removed)}, changed={len(changed)}\n")
    md.append(f"- Gemini used: {gemini_used}\n")
    md.append(f"- Gemini verdict: {gemini_verdict}\n")

    md.append(f"- SAFE_MODE link mode: {safe_mode_link}\n")
    if safe_mode_last:
        md.append(f"- SAFE_MODE used: {safe_mode_last.get('used')}\n")
        md.append(f"- SAFE_MODE category: {safe_mode_last.get('category')}\n")
        md.append(f"- SAFE_MODE stage: {safe_mode_last.get('stage')}\n")
        smm = safe_mode_last.get('meta') or {}
        if smm:
            md.append(f"- SAFE_MODE meaning_preserved: {smm.get('meaning_preserved')} (anchors_covered={smm.get('anchors_covered')}/{smm.get('anchors_required')})\n")

    md.append("\n## Structure diff (audit)\n")
    md.append(f"- Added: {added}\n")
    md.append(f"- Removed: {removed}\n")
    md.append(f"- Changed: {changed}\n")

    md.append("\n## Semantic continuity (Gemini)\n")
    md.append(f"- Verdict: {gemini_verdict}\n")
    if gemini_rationale:
        md.append("\n### Rationale\n")
        md.append(gemini_rationale.strip() + "\n")

    md.append("\n## Notes\n")
    md.append(notes.strip() + "\n")
    return "\n".join(md)


def _load_pic_text(repo_root: Path, run_dir: Path) -> Tuple[str, str]:
    """
    Long-project default PIC priority:

    1) baseline/PIC.md                      (highest priority)
    2) baseline/BASELINE_PACKET.md          (legacy PIC container)
    3) baseline/BASELINE_G1_OUTPUT.json     (JSON string fallback)
    4) current request text (00_USER_REQUEST.md)

    Returns (text, source_label). If nothing exists, returns ("", "MISSING").
    """
    # 1) New canonical PIC location
    pic1 = repo_root / "baseline" / "PIC.md"
    if pic1.exists():
        return pic1.read_text(encoding="utf-8"), "baseline/PIC.md"

    # 2) Legacy PIC container (kept for backward compatibility)
    pic2 = repo_root / "baseline" / "BASELINE_PACKET.md"
    if pic2.exists():
        return pic2.read_text(encoding="utf-8"), "baseline/BASELINE_PACKET.md"

    # 3) As a last resort, reuse baseline G1 output as "PIC-like" context
    g1 = repo_root / "baseline" / "BASELINE_G1_OUTPUT.json"
    if g1.exists():
        return g1.read_text(encoding="utf-8"), "baseline/BASELINE_G1_OUTPUT.json"

    # 4) Fallback to current request
    req = run_dir / "00_USER_REQUEST.md"
    if req.exists():
        return req.read_text(encoding="utf-8"), "00_USER_REQUEST.md"

    return "", "MISSING"


def _load_current_text(run_dir: Path) -> Tuple[str, str]:
    """
    What we compare against PIC for "meaning continuity".
    Priority:
      1) G1_DECISION.md (human-readable design log)
      2) G1_OUTPUT.json (structured)
      3) 00_USER_REQUEST.md (fallback)
    """
    p1 = run_dir / "G1_DECISION.md"
    if p1.exists():
        return p1.read_text(encoding="utf-8"), "G1_DECISION.md"
    p2 = run_dir / "G1_OUTPUT.json"
    if p2.exists():
        return p2.read_text(encoding="utf-8"), "G1_OUTPUT.json"
    p3 = run_dir / "00_USER_REQUEST.md"
    if p3.exists():
        return p3.read_text(encoding="utf-8"), "00_USER_REQUEST.md"
    return "", "MISSING"


def gate_g2_continuity(ctx: GateContext) -> GateResult:
    """
    Gate2 = Continuity check (Structure + Semantic).

    - Structure: JSON diff baseline vs current (for audit / debugging)
      *Decision rule (STRUCTURE): removed baseline keys => FAIL*  (backward incompatible schema regression)
    - Semantic: Gemini compares PIC vs current text and outputs SAME/DRIFT/VIOLATION/UNKNOWN
      *Decision rule (SEMANTIC): DRIFT or VIOLATION => FAIL*

    Final decision:
      - If structure_removed => FAIL
      - Else if Gemini verdict in {DRIFT, VIOLATION} => FAIL
      - Else PASS

    If Gemini is unavailable => verdict UNKNOWN (non-blocking), but artifacts record that it was not validated.
    """
    run_dir = Path(ctx.run_dir)
    repo_root = _find_repo_root(run_dir)

    baseline_g1 = _load_baseline_g1(repo_root)
    current_g1 = _load_current_g1(run_dir)

    baseline_present = baseline_g1 is not None
    previous_present = False  # reserved (not implemented here)

    if baseline_present and current_g1 is not None:
        diff = _diff_json(baseline_g1, current_g1)
    else:
        diff = {"added": [], "removed": [], "changed": []}

    # Semantic continuity via Gemini (PIC vs current)
    pic_text, pic_src = _load_pic_text(repo_root, run_dir)
    cur_text, cur_src = _load_current_text(run_dir)

    provider = None
    if GeminiProvider is not None:
        try:
            provider = GeminiProvider.from_env()
        except Exception:
            provider = None

    gemini_used = provider is not None
    gemini_verdict = "UNKNOWN"
    gemini_rationale = ""

    if provider is not None and pic_text and cur_text:
        try:
            res = provider.judge_continuity(pic_text=pic_text, current_text=cur_text)
            gemini_verdict = getattr(res, "verdict", "UNKNOWN")
            gemini_rationale = getattr(res, "rationale", "") or ""
        except Exception:
            gemini_verdict = "UNKNOWN"
            gemini_rationale = ""


    # SAFE_MODE linkage snapshot (best-effort, in-process only)
    safe_mode_link = "OFF"
    safe_mode_last: Optional[Dict[str, Any]] = None
    if get_safe_mode_link_mode is not None:
        try:
            safe_mode_link = str(get_safe_mode_link_mode())
        except Exception:
            safe_mode_link = "OFF"
    if get_last_safe_mode_result is not None:
        try:
            r = get_last_safe_mode_result()
            if r is not None:
                safe_mode_last = {
                    "used": getattr(r, "used", None),
                    "category": getattr(r, "category", None),
                    "stage": getattr(r, "stage", None),
                    "meta": getattr(r, "meta", None),
                }
        except Exception:
            safe_mode_last = None

    # Decision rule (fixed)
    structure_removed = bool(diff.get("removed"))
    if structure_removed:
        decision = Decision.FAIL
    elif gemini_verdict in ("DRIFT", "VIOLATION"):
        decision = Decision.FAIL
    else:
        decision = Decision.PASS

    notes = (
        f"- PIC source (priority): {pic_src}\n"
        f"- Current source: {cur_src}\n"
        f"- Structure diff is audit + ENFORCEMENT for 'removed' only.\n"
        f"- Semantic verdict is ENFORCEMENT for DRIFT/VIOLATION.\n"
        f"- If Gemini verdict is UNKNOWN, semantic continuity is NOT validated (recorded), but pipeline is not blocked.\n- SAFE_MODE link is informational unless you explicitly change decision rules."
    )

    decision_md = _format_decision_md(
        decision=decision,
        baseline_present=baseline_present,
        previous_present=previous_present,
        diff=diff,
        gemini_used=gemini_used,
        gemini_verdict=gemini_verdict,
        gemini_rationale=gemini_rationale,
        notes=notes,
        safe_mode_link=safe_mode_link,
        safe_mode_last=safe_mode_last,
    )

    meta = {
        "gate": "G2",
        "created_at": now_seoul().isoformat(),
        "mode": "structure_diff + gemini_semantic_pic",
        "baseline_present": baseline_present,
        "gemini_used": gemini_used,
        "gemini_verdict": gemini_verdict,
        "pic_source": pic_src,
        "current_source": cur_src,
        "safe_mode_link_mode": safe_mode_link,
        "safe_mode_last": safe_mode_last,
        "decision_rule": {
            "structure_removed": "FAIL",
            "semantic_drift_violation": "FAIL",
            "otherwise": "PASS",
        },
    }

    out = {
        "safe_mode_link_mode": safe_mode_link,
        "safe_mode_last": safe_mode_last,
        "baseline_present": baseline_present,
        "structure_diff": diff,
        "semantic": {
            "pic_source": pic_src,
            "current_source": cur_src,
            "gemini_used": gemini_used,
            "verdict": gemini_verdict,
            "rationale": gemini_rationale,
        },
    }

    
    # Quantitative metrics for long-term tracking (written into META.json via RunMeta.attrs)
    try:
        
        # C) Gate2 판단을 META에 정량 기록 (장기 통계)
        # - 카운트/스코어 + 샘플(상위 N)만 기록해서 META 폭발을 막는다.
        added_fields = diff.get("added", []) or []
        removed_fields = diff.get("removed", []) or []
        changed_fields = diff.get("changed", []) or []

        removed_n = len(removed_fields)
        added_n = len(added_fields)
        changed_n = len(changed_fields)

        denom = max(1, len(set(added_fields) | set(removed_fields) | set(changed_fields)))
        continuity_score = max(0.0, 1.0 - ((removed_n * 2 + changed_n) / float(denom)))

        g2_metrics = {
            "mode": mode,
            "status": result.status.value,
            "baseline_present": baseline_present,
            "continuity_score": round(continuity_score, 4),
            "diff": {"added": added_n, "removed": removed_n, "changed": changed_n},
            "samples": {
                "added": list(added_fields)[:20],
                "removed": list(removed_fields)[:20],
                "changed": list(changed_fields)[:20],
            },
            "strict_notes": strict_notes,
            "safe_mode_used": bool(safe_mode_used),
            "safe_mode_last_stage": (safe_mode_last or {}).get("stage") if isinstance(safe_mode_last, dict) else None,
            "safe_mode_last_category": (safe_mode_last or {}).get("category") if isinstance(safe_mode_last, dict) else None,
            "decision": str(decision),
        }
        attrs = getattr(getattr(ctx, "meta", None), "attrs", None)
        if isinstance(attrs, dict):
            attrs.setdefault("gate_metrics", {})["G2"] = g2_metrics
    except Exception:
        pass

# Write artifacts
    (run_dir / "G2_DECISION.md").write_text(decision_md, encoding="utf-8")
    _write_json(run_dir / "G2_META.json", meta)
    _write_json(run_dir / "G2_OUTPUT.json", out)

    return GateResult(
        decision=decision,
        message=str(decision),
        outputs={
            "G2_DECISION.md": "G2_DECISION.md",
            "G2_OUTPUT.json": "G2_OUTPUT.json",
            "G2_META.json": "G2_META.json",
        },
    )
