# scripts/update_baseline.py
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


KST = timezone(timedelta(hours=9))


def _now_seoul_iso() -> str:
    return datetime.now(KST).isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


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


def _normalize_json_for_compare(x: Any) -> Any:
    # Stable normalization to make diffs deterministic.
    # - dict: sort keys recursively
    # - list: keep order (we do NOT sort lists; list ordering may be meaningful)
    if isinstance(x, dict):
        return {k: _normalize_json_for_compare(x[k]) for k in sorted(x.keys())}
    if isinstance(x, list):
        return [_normalize_json_for_compare(v) for v in x]
    return x


@dataclass
class JsonDiff:
    added: List[str]
    removed: List[str]
    changed: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {"added": self.added, "removed": self.removed, "changed": self.changed}


def _diff_json_paths(old: Any, new: Any, prefix: str = "") -> JsonDiff:
    """
    Structure diff (paths only).
    - added: present in new, missing in old
    - removed: present in old, missing in new
    - changed: both present but value differs (deep compare)
    """
    added: List[str] = []
    removed: List[str] = []
    changed: List[str] = []

    if isinstance(old, dict) and isinstance(new, dict):
        old_keys = set(old.keys())
        new_keys = set(new.keys())

        for k in sorted(new_keys - old_keys):
            path = f"{prefix}.{k}" if prefix else k
            added.append(path)

        for k in sorted(old_keys - new_keys):
            path = f"{prefix}.{k}" if prefix else k
            removed.append(path)

        for k in sorted(old_keys & new_keys):
            path = f"{prefix}.{k}" if prefix else k
            d = _diff_json_paths(old[k], new[k], path)
            added.extend(d.added)
            removed.extend(d.removed)
            changed.extend(d.changed)
        return JsonDiff(added=added, removed=removed, changed=changed)

    if isinstance(old, list) and isinstance(new, list):
        # Compare list length and per-index changes (structure-level conservative)
        if len(old) != len(new):
            changed.append(f"{prefix} (list length {len(old)} -> {len(new)})")
            # still attempt per-index compare for overlapping region
        n = min(len(old), len(new))
        for i in range(n):
            path = f"{prefix}[{i}]"
            d = _diff_json_paths(old[i], new[i], path)
            added.extend(d.added)
            removed.extend(d.removed)
            changed.extend(d.changed)
        # extra tail elements count as added/removed at index paths
        if len(new) > len(old):
            for i in range(len(old), len(new)):
                added.append(f"{prefix}[{i}]")
        elif len(old) > len(new):
            for i in range(len(new), len(old)):
                removed.append(f"{prefix}[{i}]")
        return JsonDiff(added=added, removed=removed, changed=changed)

    # primitive or type mismatch
    if old != new:
        changed.append(prefix if prefix else "<root>")
    return JsonDiff(added=added, removed=removed, changed=changed)


def _render_history_md(entries: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("# BASELINE HISTORY\n")
    lines.append("This file is generated by scripts/update_baseline.py (stdlib-only).\n")
    lines.append("## Entries (newest first)\n")

    for e in entries:
        at = e.get("at", "UNKNOWN")
        run_id = e.get("promoted_from_run", "UNKNOWN")
        changed = e.get("diff_summary", {})
        a = changed.get("added", 0)
        r = changed.get("removed", 0)
        c = changed.get("changed", 0)
        promote_pic = e.get("promote_pic", False)

        lines.append(f"### {at} — {run_id}\n")
        lines.append(f"- promote_pic: {promote_pic}\n")
        lines.append(f"- diff_summary: added={a}, removed={r}, changed={c}\n")
        note = e.get("note")
        if note:
            lines.append(f"- note: {note}\n")
        lines.append("")  # blank line

    return "\n".join(lines).rstrip() + "\n"


def _load_history_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    entries: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                entries.append(obj)
        except Exception:
            # ignore corrupted line (do not crash baseline ops)
            continue
    return entries


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Promote a run's stable artifacts to baseline/ (stdlib-only).")
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
        "--note",
        default="",
        help="Optional note recorded into baseline history (e.g., reason/intent).",
    )

    args = parser.parse_args(argv)

    repo_root = _find_repo_root(Path.cwd())
    run_dir = _resolve_run_dir(repo_root, args.run_id)
    baseline_dir = _ensure_baseline_dir(repo_root)

    # Required source
    g1_src = run_dir / "G1_OUTPUT.json"
    if not g1_src.exists():
        raise FileNotFoundError(f"Missing required artifact in run: {g1_src}")

    # Destinations
    g1_dst = baseline_dir / "BASELINE_G1_OUTPUT.json"
    pic_src = run_dir / "PIC.md"
    pic_dst = baseline_dir / "PIC.md"

    # Pre-read old baseline for diff
    old_baseline: Optional[Dict[str, Any]] = None
    if g1_dst.exists():
        try:
            old_baseline = _normalize_json_for_compare(_read_json(g1_dst))
        except Exception:
            old_baseline = None

    new_baseline = _normalize_json_for_compare(_read_json(g1_src))
    diff = _diff_json_paths(old_baseline if old_baseline is not None else {}, new_baseline, prefix="")

    diff_obj = {
        "from": str(g1_dst) if g1_dst.exists() else None,
        "to": str(g1_src),
        "at": _now_seoul_iso(),
        "diff": diff.to_dict(),
        "diff_summary": {
            "added": len(diff.added),
            "removed": len(diff.removed),
            "changed": len(diff.changed),
        },
    }

    planned: List[Tuple[Path, Path, str]] = []
    planned.append((g1_src, g1_dst, "json"))
    if args.promote_pic:
        planned.append((pic_src, pic_dst, "text_optional"))

    promote_log = baseline_dir / "BASELINE_PROMOTION_LOG.json"
    last_diff = baseline_dir / "BASELINE_LAST_DIFF.json"
    history_jsonl = baseline_dir / "BASELINE_HISTORY.jsonl"
    history_md = baseline_dir / "BASELINE_HISTORY.md"

    if args.dry_run:
        print("[DRY RUN] Repo root:", repo_root)
        print("[DRY RUN] Run dir  :", run_dir)
        for s, d, k in planned:
            print(f"[DRY RUN] {k}: {s} -> {d}")
        print("[DRY RUN] Would write:", promote_log)
        print("[DRY RUN] Would write:", last_diff)
        print("[DRY RUN] Would append:", history_jsonl)
        print("[DRY RUN] Would render:", history_md)
        print("[DRY RUN] Diff summary:", diff_obj["diff_summary"])
        return 0

    # Execute promotions
    for s, d, k in planned:
        if k == "json":
            _write_json(d, _read_json(s))
        elif k == "text_optional":
            if s.exists():
                _copy_text(s, d)
        else:
            raise RuntimeError(f"Unknown kind: {k}")

    # Write promotion log (traceability)
    log_obj = {
        "at": _now_seoul_iso(),
        "promoted_from_run": run_dir.name,
        "repo_root": str(repo_root),
        "artifacts": [
            {"src": str(s), "dst": str(d), "kind": k}
            for (s, d, k) in planned
            if not (k == "text_optional" and not s.exists())
        ],
    }
    _write_json(promote_log, log_obj)

    # Write last diff
    _write_json(last_diff, diff_obj)

    # Append history entry
    history_entry = {
        "at": _now_seoul_iso(),
        "promoted_from_run": run_dir.name,
        "promote_pic": bool(args.promote_pic),
        "diff_summary": diff_obj["diff_summary"],
        "diff_paths": diff_obj["diff"],  # keep full paths for audits
        "note": (args.note or "").strip() or None,
    }
    _append_jsonl(history_jsonl, history_entry)

    # Regenerate history markdown (newest first)
    entries = _load_history_jsonl(history_jsonl)
    entries.sort(key=lambda x: x.get("at", ""), reverse=True)
    history_md.write_text(_render_history_md(entries), encoding="utf-8")

    print("Baseline updated.")
    print("- BASELINE_G1_OUTPUT.json updated from:", g1_src)
    if args.promote_pic:
        print("- PIC.md promoted:", "YES" if (baseline_dir / "PIC.md").exists() else "NO (not found in run)")
    print("- BASELINE_LAST_DIFF.json written:", last_diff)
    print("- BASELINE_HISTORY.jsonl appended:", history_jsonl)
    print("- BASELINE_HISTORY.md rendered:", history_md)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print("ERROR:", e, file=sys.stderr)
        raise
