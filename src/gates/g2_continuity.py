from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple, List, Optional

from src.models.decision_models import GateResult, Decision
from src.pipeline.runner import GateContext
from src.pipeline.contracts import standard_spec
from src.utils.time import now_seoul


def _find_repo_root(run_dir: Path) -> Path:
    """
    Locate repo root.

    Gate2 needs 'runs' + 'baseline' to function.
    In real repo we also have 'src', but tests may not.
    So we treat a folder as repo root if it contains:
      - runs/ AND baseline/
    (src/ is optional)

    Fallback: parent of run_dir.
    """
    p = run_dir.resolve()
    for parent in [p] + list(p.parents):
        if (parent / "runs").exists() and (parent / "baseline").exists():
            return parent
    return run_dir.parent


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _flatten(obj: Any, prefix: str = "") -> Dict[str, Any]:
    """
    Flatten JSON-like dict/list into path -> value mapping for diff.
    """
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
    """
    Returns {added, removed, changed} based on flattened paths.
    """
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


def _load_baseline(repo_root: Path) -> Optional[Dict[str, Any]]:
    """
    Baseline source of truth (eventually updated only on Gate7 PASS).
    For now: baseline/BASELINE_G1_OUTPUT.json
    """
    p = repo_root / "baseline" / "BASELINE_G1_OUTPUT.json"
    if not p.exists():
        return None
    return _read_json(p)


def _load_previous_run_g1_output(repo_root: Path, current_run_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Loads previous run's G1_OUTPUT.json (most recent by folder name lexicographically).
    Assumes run ids are sortable as YYYY-MM-DD_HHMM.
    """
    runs_dir = repo_root / "runs"
    if not runs_dir.exists():
        return None

    run_ids = sorted([d.name for d in runs_dir.iterdir() if d.is_dir()])
    run_ids = [rid for rid in run_ids if rid != current_run_id]
    if not run_ids:
        return None

    prev_id = run_ids[-1]
    p = runs_dir / prev_id / "G1_OUTPUT.json"
    if not p.exists():
        return None
    return prev_id, _read_json(p)


def _fail_conditions(diff: Dict[str, Any]) -> List[str]:
    """
    Minimal, deterministic FAIL rules:
    - If any keys were removed (backward incompatibility risk)
    - If critical sections removed: interfaces/constraints/acceptance_criteria
    """
    reasons: List[str] = []
    removed = diff.get("removed", [])
    if removed:
        reasons.append("Removed fields detected (backward compatibility risk).")
        removed_paths = set(removed)
        for critical in ["interfaces", "constraints", "acceptance_criteria"]:
            if any(
                p == critical
                or p.startswith(f"{critical}.")
                or p.startswith(f"{critical}[")
                for p in removed_paths
            ):
                reasons.append(f"Critical section removed: {critical}")
    return reasons


def gate_g2_continuity(ctx: GateContext) -> GateResult:
    run_dir = Path(ctx.run_dir).resolve()
    repo_root = _find_repo_root(run_dir)

    # Input: current G1_OUTPUT.json must exist
    g1_path = run_dir / "G1_OUTPUT.json"
    if not g1_path.exists():
        raise FileNotFoundError("G1_OUTPUT.json not found (Gate2 requires Gate1 output)")

    current = _read_json(g1_path)

    baseline = _load_baseline(repo_root)
    prev = _load_previous_run_g1_output(repo_root, ctx.meta.run_id)

    output: Dict[str, Any] = {
        "gate": "G2",
        "mode": "continuity_check",
        "baseline_present": baseline is not None,
        "previous_run_present": prev is not None,
        "baseline_diff": None,
        "previous_run_diff": None,
        "notes": [],
    }

    # Compare vs baseline if present
    if baseline is not None:
        bd = _diff_json(baseline, current)
        output["baseline_diff"] = bd
    else:
        output["notes"].append("No baseline found: baseline/BASELINE_G1_OUTPUT.json")

    # Compare vs previous run if present
    if prev is not None:
        prev_id, prev_json = prev
        pd = _diff_json(prev_json, current)
        output["previous_run_id"] = prev_id
        output["previous_run_diff"] = pd
    else:
        output["notes"].append("No previous run G1_OUTPUT.json found.")

    # Decision logic
    fail_reasons: List[str] = []
    if output["baseline_diff"] is not None:
        fail_reasons.extend(_fail_conditions(output["baseline_diff"]))

    decision = Decision.FAIL if fail_reasons else Decision.PASS

    # Write standard artifacts
    decision_md = (
        "# G2 CONTINUITY DECISION\n\n"
        f"Decision: {decision.value}\n\n"
        "## Summary\n"
        f"- Baseline: {'PRESENT' if baseline is not None else 'MISSING'}\n"
        f"- Previous run: {'PRESENT' if prev is not None else 'MISSING'}\n\n"
        "## Fail reasons\n"
        + (("\n".join([f"- {r}" for r in fail_reasons]) + "\n") if fail_reasons else "- None\n")
        + "\n## Notes\n"
        + (("\n".join([f"- {n}" for n in output["notes"]]) + "\n") if output["notes"] else "- None\n")
    )
    (run_dir / "G2_DECISION.md").write_text(decision_md, encoding="utf-8")

    _write_json(run_dir / "G2_OUTPUT.json", output)

    meta = {
        "gate": "G2",
        "decision": decision.value,
        "at": now_seoul().isoformat(),
        "attempt": ctx.meta.attempts.get("G2", 1),
        "repo_root": str(repo_root),
        "inputs": {"G1_OUTPUT.json": "G1_OUTPUT.json"},
    }
    _write_json(run_dir / "G2_META.json", meta)

    outputs = {
        "G2_DECISION.md": "G2_DECISION.md",
        "G2_OUTPUT.json": "G2_OUTPUT.json",
        "G2_META.json": "G2_META.json",
    }
    standard_spec("G2").validate(outputs)

    return GateResult(
        decision=decision,
        message="Continuity check completed",
        outputs=outputs,
        meta={"fail_reasons": fail_reasons},
    )
