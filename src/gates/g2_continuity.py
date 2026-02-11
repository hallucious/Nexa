from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models.decision_models import Decision, GateResult
from src.pipeline.runner import GateContext
from src.utils.time import now_seoul


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _find_repo_root(run_dir: Path) -> Path:
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


def gate_g2_continuity(ctx: GateContext) -> GateResult:
    """
    Pre-semantic rollback version:
    - No sentence-transformers dependency
    - No semantic scoring
    - Continuity decision is structural-only (deterministic)
    """
    run_dir = Path(ctx.run_dir)
    repo_root = _find_repo_root(run_dir)

    baseline_g1 = _load_baseline_g1(repo_root)
    current_g1 = _load_current_g1(run_dir)
    baseline_present = baseline_g1 is not None

    if baseline_present and current_g1 is not None:
        diff = _diff_json(baseline_g1, current_g1)
    else:
        diff = {"added": [], "removed": [], "changed": []}

    # Keep semantic block for backward/forward compatibility with tests & reports,
    # but semantic scoring is intentionally disabled in this version.
    semantic_available = False
    semantic_score = None
    semantic_verdict = "UNAVAILABLE"
    pic_source = "baseline/PIC.md"

    # Decision rule (structural-only)
    if diff.get("removed"):
        decision = Decision.FAIL
    else:
        decision = Decision.PASS

    decision_md = (
        "# G2 CONTINUITY DECISION\n\n"
        f"Decision: {decision.value}\n\n"
        "## Semantic similarity (local)\n"
        f"- Available: {semantic_available}\n"
        f"- Score: {semantic_score}\n"
        f"- Verdict: {semantic_verdict}\n"
        f"- PIC source: {pic_source}\n\n"
        "## Structure diff\n"
        f"- Added: {diff.get('added')}\n"
        f"- Removed: {diff.get('removed')}\n"
        f"- Changed: {diff.get('changed')}\n"
    )

    meta = {
        "gate": "G2",
        "created_at": now_seoul().isoformat(),
        "baseline_present": baseline_present,
        "semantic_available": semantic_available,
        "semantic_score": semantic_score,
        "semantic_verdict": semantic_verdict,
        "pic_source": pic_source,
    }

    out = {
        "baseline_present": baseline_present,
        "structure_diff": diff,
        "semantic": {
            "available": semantic_available,
            "score": semantic_score,
            "verdict": semantic_verdict,
            "pic_source": pic_source,
        },
    }

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
