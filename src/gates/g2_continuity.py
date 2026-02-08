from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.models.decision_models import GateResult, Decision
from src.pipeline.runner import GateContext
from src.utils.time import now_seoul

from src.providers.gemini_provider import GeminiProvider


def _find_repo_root(run_dir: Path) -> Path:
    """
    Gate2 needs repo root to find:
      - baseline/
      - runs/
    """
    p = run_dir.resolve()
    for parent in [p] + list(p.parents):
        if (parent / "runs").exists() and (parent / "baseline").exists():
            return parent
    return run_dir.parent


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _flatten(obj: Any, prefix: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.update(_flatten(v, key))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            key = f"{prefix}[{i}]"
            out.update(_flatten(v, key))
    else:
        out[prefix] = obj
    return out


def _diff_json(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    fa = _flatten(a)
    fb = _flatten(b)

    a_keys = set(fa.keys())
    b_keys = set(fb.keys())

    added = sorted(list(b_keys - a_keys))
    removed = sorted(list(a_keys - b_keys))

    changed = []
    for k in sorted(list(a_keys & b_keys)):
        if fa[k] != fb[k]:
            changed.append({"path": k, "from": fa[k], "to": fb[k]})

    return {"added": added, "removed": removed, "changed": changed}


def _load_baseline_g1(repo_root: Path) -> Optional[Dict[str, Any]]:
    """
    Baseline is expected at:
      baseline/BASELINE_G1_OUTPUT.json
    """
    p = repo_root / "baseline" / "BASELINE_G1_OUTPUT.json"
    if not p.exists():
        return None
    return _read_json(p)


def _load_current_g1(run_dir: Path) -> Optional[Dict[str, Any]]:
    p = run_dir / "G1_OUTPUT.json"
    if not p.exists():
        return None
    return _read_json(p)


def _load_pic_text(repo_root: Path, run_dir: Path) -> Tuple[str, str]:
    """
    Long-project default: baseline/BASELINE_PACKET.md (PIC) if exists.
    Fallback: baseline/BASELINE_G1_OUTPUT.json (as JSON string)
    Fallback2: current request text.

    Returns: (pic_text, source_label)
    """
    pic_md = repo_root / "baseline" / "BASELINE_PACKET.md"
    if pic_md.exists():
        return _read_text(pic_md), "baseline/BASELINE_PACKET.md"

    base_g1 = repo_root / "baseline" / "BASELINE_G1_OUTPUT.json"
    if base_g1.exists():
        return _read_text(base_g1), "baseline/BASELINE_G1_OUTPUT.json"

    req = run_dir / "00_USER_REQUEST.md"
    if req.exists():
        return _read_text(req), "runs/.../00_USER_REQUEST.md"

    return "", "MISSING"


def _load_current_text(run_dir: Path) -> Tuple[str, str]:
    """
    Prefer current design output of G1 (JSON) as text; fallback to request.
    """
    g1 = run_dir / "G1_OUTPUT.json"
    if g1.exists():
        return _read_text(g1), "G1_OUTPUT.json"
    req = run_dir / "00_USER_REQUEST.md"
    if req.exists():
        return _read_text(req), "00_USER_REQUEST.md"
    return "", "MISSING"


def _format_decision_md(
    *,
    decision: Decision,
    baseline_present: bool,
    previous_present: bool,
    diff: Dict[str, Any],
    gemini_used: bool,
    gemini_verdict: str,
    gemini_rationale: str,
    fail_reasons: Optional[list],
    notes: str,
) -> str:
    lines = []
    lines.append("# G2 CONTINUITY DECISION")
    lines.append("")
    lines.append(f"Decision: {decision.value}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Baseline present: {baseline_present}")
    lines.append(f"- Previous run present: {previous_present}")
    lines.append(f"- Gemini used: {gemini_used}")
    lines.append(f"- Gemini verdict: {gemini_verdict}")
    lines.append("")
    lines.append("## Fail reasons")
    if decision == Decision.FAIL:
        if fail_reasons:
            for r in fail_reasons:
                lines.append(f"- {r}")
        else:
            lines.append("- (unspecified)")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Structure diff (baseline G1_OUTPUT vs current G1_OUTPUT)")
    lines.append(f"- added: {len(diff.get('added', []))}")
    lines.append(f"- removed: {len(diff.get('removed', []))}")
    lines.append(f"- changed: {len(diff.get('changed', []))}")
    lines.append("")
    lines.append("## Gemini rationale")
    lines.append(gemini_rationale if gemini_rationale else "- (none)")
    lines.append("")
    lines.append("## Notes")
    lines.append(notes if notes else "- (none)")
    lines.append("")
    return "\n".join(lines)


def gate_g2_continuity(ctx: GateContext) -> GateResult:
    """
    Gate2 = Continuity check (Structure + Semantic).

    STRUCTURE (deterministic, offline):
      - JSON diff baseline vs current (audit + safety)
      - If baseline has fields that CURRENT removed => FAIL (hard safety)

    SEMANTIC (Gemini, PIC-based):
      - Gemini compares PIC vs current text and outputs SAME/DRIFT/VIOLATION
      - If Gemini says DRIFT/VIOLATION => FAIL

    Decision rule (priority):
      1) If structure removed fields exist => FAIL
      2) Else if Gemini verdict DRIFT/VIOLATION => FAIL
      3) Else => PASS
         (Gemini UNKNOWN simply means semantic check unavailable; structure still applied)
    """
    run_dir = Path(ctx.run_dir)
    repo_root = _find_repo_root(run_dir)

    baseline_g1 = _load_baseline_g1(repo_root)
    current_g1 = _load_current_g1(run_dir)

    baseline_present = baseline_g1 is not None
    previous_present = False  # reserved (not implemented here; baseline is primary)

    if baseline_present and current_g1 is not None:
        diff = _diff_json(baseline_g1, current_g1)
    else:
        diff = {"added": [], "removed": [], "changed": []}

    # Semantic continuity via Gemini (PIC vs current)
    pic_text, pic_src = _load_pic_text(repo_root, run_dir)
    cur_text, cur_src = _load_current_text(run_dir)

    provider = GeminiProvider.from_env()
    gemini_used = provider is not None

    gemini_verdict = "UNKNOWN"
    gemini_rationale = ""
    if provider is not None and pic_text and cur_text:
        res = provider.judge_continuity(pic_text=pic_text, current_text=cur_text)
        gemini_verdict = res.verdict
        gemini_rationale = res.rationale

    # Decision (STRUCTURE removed > SEMANTIC drift/violation)
    fail_reasons = []
    removed = diff.get("removed", []) or []
    if removed:
        decision = Decision.FAIL
        fail_reasons.append(f"STRUCTURE: baseline fields removed ({len(removed)}).")
    elif gemini_verdict in ("DRIFT", "VIOLATION"):
        decision = Decision.FAIL
        fail_reasons.append(f"SEMANTIC: Gemini verdict={gemini_verdict}.")
    else:
        decision = Decision.PASS

    notes = (
        f"- PIC source: {pic_src}\n"
        f"- Current source: {cur_src}\n"
        f"- Structure diff is enforced ONLY for removed-fields safety; added/changed are audit-only.\n"
        f"- If Gemini verdict is UNKNOWN, semantic continuity is NOT validated (recorded), but structure safety still applies."
    )

    decision_md = _format_decision_md(
        decision=decision,
        baseline_present=baseline_present,
        previous_present=previous_present,
        diff=diff,
        gemini_used=gemini_used,
        gemini_verdict=gemini_verdict,
        gemini_rationale=gemini_rationale,
        fail_reasons=fail_reasons,
        notes=notes,
    )

    meta = {
        "gate": "G2",
        "created_at": now_seoul().isoformat(),
        "mode": "structure_removed_safety + gemini_semantic_pic",
        "baseline_present": baseline_present,
        "gemini_used": gemini_used,
        "gemini_verdict": gemini_verdict,
        "structure_removed_count": len(removed),
    }

    out = {
        "baseline_present": baseline_present,
        "structure_diff": diff,
        "semantic": {
            "pic_source": pic_src,
            "current_source": cur_src,
            "gemini_used": gemini_used,
            "verdict": gemini_verdict,
            "rationale": gemini_rationale,
        },
        "decision_drivers": {
            "structure_removed_enforced": bool(removed),
            "semantic_enforced": gemini_verdict in ("DRIFT", "VIOLATION"),
        },
    }

    # Write artifacts
    (run_dir / "G2_DECISION.md").write_text(decision_md, encoding="utf-8")
    _write_json(run_dir / "G2_META.json", meta)
    _write_json(run_dir / "G2_OUTPUT.json", out)

    msg = (
        f"G2 continuity: decision={decision.value}, "
        f"removed={len(removed)}, semantic={gemini_verdict}, gemini_used={gemini_used}"
    )

    return GateResult(
        decision=decision,
        message=msg,
        outputs={
            "G2_DECISION.md": "G2_DECISION.md",
            "G2_OUTPUT.json": "G2_OUTPUT.json",
            "G2_META.json": "G2_META.json",
        },
    )
