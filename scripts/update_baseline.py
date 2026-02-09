# scripts/update_baseline.py
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur] + list(cur.parents):
        if (p / "src").exists() and (p / "tests").exists():
            return p
    raise RuntimeError("Cannot find repo root (expected to find src/ and tests/ directories).")


def _pick_latest_run(runs_dir: Path) -> Optional[Path]:
    if not runs_dir.exists():
        return None
    run_dirs = [p for p in runs_dir.iterdir() if p.is_dir()]
    if not run_dirs:
        return None
    run_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return run_dirs[0]


def _resolve_run_dir(repo_root: Path, run_id: Optional[str]) -> Path:
    runs_dir = repo_root / "runs"
    if run_id:
        run_dir = runs_dir / run_id
        if not run_dir.exists():
            raise FileNotFoundError(f"Run dir not found: {run_dir}")
        return run_dir

    latest = _pick_latest_run(runs_dir)
    if latest is None:
        raise FileNotFoundError(f"No run directories found under: {runs_dir}")
    return latest


def _ensure_baseline_dir(repo_root: Path) -> Path:
    baseline_dir = repo_root / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    return baseline_dir


def _copy_text(src: Path, dst: Path) -> None:
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _is_run_pass(run_dir: Path) -> Tuple[bool, str]:
    """
    Safety gate (fixed):
    - META.json must exist and status == PASS
    - G7_DECISION.md must exist and Decision: PASS
    """
    meta_path = run_dir / "META.json"
    if not meta_path.exists():
        return False, "META.json missing in run_dir (cannot verify PASS)."

    meta = _read_json(meta_path)
    status = str(meta.get("status", "")).upper()
    if status != "PASS":
        return False, f"META.json status is not PASS (status={status})."

    g7_md = run_dir / "G7_DECISION.md"
    if not g7_md.exists():
        return False, "G7_DECISION.md missing in run_dir (cannot verify Gate7 PASS)."

    decision_line = ""
    for line in g7_md.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip().lower().startswith("decision:"):
            decision_line = line.split(":", 1)[1].strip().upper()
            break
    if decision_line != "PASS":
        return False, f"G7_DECISION.md Decision is not PASS (Decision={decision_line or 'UNKNOWN'})."

    return True, "Verified PASS."


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Promote a PASS run's stable artifacts to baseline/ (stdlib-only).")
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run directory name under runs/. If omitted, uses latest by modified time.",
    )
    parser.add_argument(
        "--promote-pic",
        action="store_true",
        help="Also promote runs/<run>/PIC.md to baseline/PIC.md if it exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without writing files.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass PASS verification (NOT recommended).",
    )
    args = parser.parse_args(argv)

    repo_root = _find_repo_root(Path.cwd())
    run_dir = _resolve_run_dir(repo_root, args.run_id)
    baseline_dir = _ensure_baseline_dir(repo_root)

    ok, reason = _is_run_pass(run_dir)
    if not args.force and not ok:
        raise RuntimeError(f"Refusing to update baseline: run is not verified PASS. Reason: {reason}")

    planned = []

    # 1) Promote Gate1 structured output as baseline structure contract
    g1_src = run_dir / "G1_OUTPUT.json"
    g1_dst = baseline_dir / "BASELINE_G1_OUTPUT.json"
    if not g1_src.exists():
        raise FileNotFoundError(f"Missing required artifact in run: {g1_src}")
    planned.append((g1_src, g1_dst, "json"))

    # 2) Optionally promote PIC.md (semantic anchor)
    if args.promote_pic:
        pic_src = run_dir / "PIC.md"
        pic_dst = baseline_dir / "PIC.md"
        if pic_src.exists():
            planned.append((pic_src, pic_dst, "text"))
        else:
            planned.append((pic_src, pic_dst, "missing_optional"))

    # 3) Write a promotion log for traceability
    promote_log = baseline_dir / "BASELINE_PROMOTION_LOG.json"
    log_obj = {
        "promoted_from_run": run_dir.name,
        "repo_root": str(repo_root),
        "pass_verification": {"ok": ok, "reason": reason, "forced": bool(args.force)},
        "artifacts": [{"src": str(s), "dst": str(d), "kind": k} for (s, d, k) in planned if k != "missing_optional"],
    }

    if args.dry_run:
        print("[DRY RUN] Repo root:", repo_root)
        print("[DRY RUN] Run dir  :", run_dir)
        print("[DRY RUN] PASS check:", ok, "-", reason, "(forced)" if args.force else "")
        for s, d, k in planned:
            print(f"[DRY RUN] {k}: {s} -> {d}")
        print("[DRY RUN] Would write:", promote_log)
        return 0

    for s, d, k in planned:
        if k == "json":
            _write_json(d, _read_json(s))
        elif k == "text":
            d.write_text(s.read_text(encoding="utf-8"), encoding="utf-8")
        elif k == "missing_optional":
            pass
        else:
            raise RuntimeError(f"Unknown kind: {k}")

    _write_json(promote_log, log_obj)

    print("Baseline updated.")
    print("- BASELINE_G1_OUTPUT.json updated from:", g1_src)
    if args.promote_pic:
        print("- PIC.md promoted:", "YES" if (baseline_dir / "PIC.md").exists() else "NO (not found in run)")
    print("- Promotion log written:", promote_log)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print("ERROR:", e, file=sys.stderr)
        raise
