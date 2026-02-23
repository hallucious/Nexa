# src/gates/g2_continuity.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.models.decision_models import Decision, GateResult
from src.pipeline.runner import GateContext
from src.utils.time import now_seoul
from src.pipeline.stop_reason import StopReason

# NOTE:
# - Gate2 uses an injected GPT provider (ctx.providers['gpt']) when available.
# - Gate2 must still run deterministically without network; if no provider is injected -> verdict UNKNOWN (non-blocking).
try:
    from src.providers.gpt_provider import GPTProvider  # only for type checking / optional availability
except Exception:  # pragma: no cover
    GPTProvider = None  # type: ignore


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
    gpt_used: bool,
    gpt_verdict: str,
    gpt_rationale: str,
    notes: str,
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
    md.append(f"- GPT used: {gpt_used}\n")
    md.append(f"- GPT verdict: {gpt_verdict}\n")

    md.append("\n## Structure diff (audit)\n")
    md.append(f"- Added: {added}\n")
    md.append(f"- Removed: {removed}\n")
    md.append(f"- Changed: {changed}\n")

    md.append("\n## Semantic continuity (GPT)\n")
    md.append(f"- Verdict: {gpt_verdict}\n")
    if gpt_rationale:
        md.append("\n### Rationale\n")
        md.append(gpt_rationale.strip() + "\n")

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



def _meta_path(run_dir: Path) -> Path:
    return run_dir / "META.json"


def _read_meta(run_dir: Path) -> dict:
    p = _meta_path(run_dir)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        # do not fail Gate2 due to meta corruption
        return {}


def _write_meta(run_dir: Path, data: dict) -> None:
    p = _meta_path(run_dir)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _merge_dict(dst: dict, patch: dict) -> dict:
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            dst[k] = _merge_dict(dst[k], v)
        else:
            dst[k] = v
    return dst


def _update_meta(run_dir: Path, patch: dict) -> None:
    data = _read_meta(run_dir)
    _merge_dict(data, patch)
    _write_meta(run_dir, data)


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def gate_g2_continuity(ctx: GateContext) -> GateResult:
    """
    Gate2 = Continuity check (Structure + Semantic).

    - Structure: JSON diff baseline vs current (for audit / debugging)
      *Decision rule (STRUCTURE): removed baseline keys => FAIL*  (backward incompatible schema regression)
    - Semantic: GPT compares PIC vs current text and outputs SAME/DRIFT/VIOLATION/UNKNOWN
      *Decision rule (SEMANTIC): DRIFT or VIOLATION => FAIL*

    Final decision:
      - If structure_removed => FAIL
      - Else if GPT verdict in {DRIFT, VIOLATION} => FAIL
      - Else PASS

    If GPT is unavailable => verdict UNKNOWN (non-blocking), but artifacts record that it was not validated.
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

    # Semantic continuity via GPT (PIC vs current)
    pic_text, pic_src = _load_pic_text(repo_root, run_dir)
    cur_text, cur_src = _load_current_text(run_dir)

        # Provider is injected by the runner / caller. Do not create providers inside the gate.
    provider = None
    try:
        provider = (ctx.providers or {}).get("gpt")
    except Exception:
        provider = None

    gpt_used = provider is not None
    gpt_verdict = "UNKNOWN"
    gpt_rationale = ""
    gpt_raw = {}
    gpt_text = ""

    if provider is not None and pic_text and cur_text:
        try:
            prompt = (
                "You are Gate2 (Continuity). Compare the previous \"PIC\" text and the current text. "
                "Return ONLY valid JSON: {\"verdict\": \"SAME|DRIFT|VIOLATION|UNKNOWN\", \"rationale\": \"...\"}.\n\n"
                "PIC:\n"
                f"{pic_text.strip()[:6000]}\n\n"
                "CURRENT:\n"
                f"{cur_text.strip()[:6000]}"
            )
            gpt_text, gpt_raw, err = provider.generate_text(prompt=prompt, temperature=0.0, max_output_tokens=512)
            if err is None and gpt_text.strip():
                try:
                    obj = json.loads(gpt_text)
                    if isinstance(obj, dict):
                        gpt_verdict = str(obj.get("verdict", "UNKNOWN")).upper()
                        gpt_rationale = str(obj.get("rationale", "") or "")
                except Exception:
                    gpt_verdict = "UNKNOWN"
                    gpt_rationale = gpt_text.strip()[:2000]
        except Exception:
            gpt_verdict = "UNKNOWN"
            gpt_rationale = ""

    # Decision rule (fixed)
    structure_removed = bool(diff.get("removed"))
    if structure_removed:
        decision = Decision.FAIL
    elif gpt_used and gpt_verdict == "UNKNOWN":
        decision = Decision.STOP
    elif gpt_verdict in ("DRIFT", "VIOLATION"):
        decision = Decision.FAIL
    else:
        decision = Decision.PASS

    notes = (
        f"- PIC source (priority): {pic_src}\n"
        f"- Current source: {cur_src}\n"
        f"- Structure diff is audit + ENFORCEMENT for 'removed' only.\n"
        f"- Semantic verdict is ENFORCEMENT for DRIFT/VIOLATION.\n"
        f"- If GPT verdict is UNKNOWN, semantic continuity is NOT validated (recorded), but pipeline is not blocked."
    )

    decision_md = _format_decision_md(
        decision=decision,
        baseline_present=baseline_present,
        previous_present=previous_present,
        diff=diff,
        gpt_used=gpt_used,
        gpt_verdict=gpt_verdict,
        gpt_rationale=gpt_rationale,
        notes=notes,
    )

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
            "unknown_used": gpt_used and gpt_verdict == "UNKNOWN",
        },
        "final_decision": decision.value,
    }

    out = {
        "baseline_present": baseline_present,
        "structure_diff": diff,
        "semantic": {
            "pic_source": pic_src,
            "current_source": cur_src,
            "gpt_used": gpt_used,
            "verdict": gpt_verdict,
            "rationale": gpt_rationale,
        },
    }

    # Write artifacts
    (run_dir / "G2_DECISION.md").write_text(decision_md, encoding="utf-8")
    _write_json(run_dir / "G2_META.json", meta)


    # C) Quantitative recording for long-term analysis (best-effort; never blocks):
    # - Write a compact Gate2 metrics snapshot into META.json
    # - Append a JSONL record into runs/_stats/g2_metrics.jsonl
    try:
        record = {
            "ts": now_seoul().isoformat(),
            "run_id": getattr(ctx.meta, "run_id", None),
            "gate": "G2",
            "mode": meta.get("mode", "structure_diff + gpt_semantic_pic"),
            "decision": getattr(decision, "value", str(decision)),
            "baseline_present": baseline_present,
            "pic_source": pic_src,
            "current_source": cur_src,
            "structure_diff_counts": {
                "added": len(diff.get("added", [])),
                "removed": len(diff.get("removed", [])),
                "changed": len(diff.get("changed", [])),
            },
            "gpt": {
                "used": gpt_used,
                "verdict": gpt_verdict,
            },
        }
        _update_meta(run_dir, {"gate2_continuity": record})
        if decision == Decision.STOP:
            _update_meta(
                run_dir,
                {
                    "stop_reason": StopReason.UNKNOWN.value,
                    "stop_detail": "G2_SEMANTIC_UNKNOWN_WITH_PROVIDER",
                },
            )
        stats_path = repo_root / "runs" / "_stats" / "g2_metrics.jsonl"
        _append_jsonl(stats_path, record)
    except Exception:
        # Do not fail the pipeline because statistics could not be written.
        pass

    _write_json(run_dir / "G2_OUTPUT.json", out)

    gate_meta = {}
    if decision == Decision.STOP:
        gate_meta = {
            "stop_reason": StopReason.UNKNOWN.value,
            "stop_detail": "G2_SEMANTIC_UNKNOWN_WITH_PROVIDER",
        }

    return GateResult(
        decision=decision,
        message=str(decision),
        outputs={
            "G2_DECISION.md": "G2_DECISION.md",
            "G2_OUTPUT.json": "G2_OUTPUT.json",
            "G2_META.json": "G2_META.json",
        },
        meta=gate_meta or None,
    )
