from __future__ import annotations

import argparse
import sys
from pathlib import Path

# --- BOOTSTRAP: ensure repo root is on sys.path so "import src.*" works ---
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
# ------------------------------------------------------------------------

from dotenv import load_dotenv
from rich import print

from src.pipeline.artifacts import Artifacts
from src.pipeline.state import RunMeta
from src.utils.time import now_seoul


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="7-Gate Pipeline Runner (Step-1 skeleton)")
    p.add_argument("--request", required=True, help="Path to a markdown file containing user request")
    p.add_argument("--run-id", default=None, help="Optional run id YYYY-MM-DD_HHMM")
    p.add_argument("--dry-run", action="store_true", help="Only create run folder + META + 00_USER_REQUEST")
    return p.parse_args()


def read_request_text(path: Path) -> str:
    """
    Robust text reader for Windows/PowerShell artifacts.
    Tries UTF-8 first, then UTF-16 (common for PS redirection).
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-16")


def main() -> int:
    load_dotenv()

    args = parse_args()
    request_path = Path(args.request).resolve()

    if not request_path.exists():
        print(f"[red]ERROR[/red] request file not found: {request_path}")
        return 2

    try:
        artifacts = Artifacts.create_new(repo_root=REPO_ROOT, run_id=args.run_id)
    except FileExistsError:
        print(f"[red]ERROR[/red] run-id already exists: runs/{args.run_id}")
        return 3

    # --- robust read ---
    req_text = read_request_text(request_path)
    artifacts.write_text("00_USER_REQUEST.md", req_text)

    meta = RunMeta(
        run_id=artifacts.run_id,
        created_at=now_seoul().isoformat(),
        baseline_version_id=None,
        providers={
            "gpt": "stub",
            "gemini": "stub",
            "perplexity": "stub",
            "codex": "stub",
        },
    )
    artifacts.write_meta(meta)

    print(f"[green]OK[/green] created run: {artifacts.run_dir}")
    print(" - 00_USER_REQUEST.md")
    print(" - META.json")

    if args.dry_run:
        print("[yellow]DRY-RUN[/yellow] stopping after initialization (Step 1).")
        return 0

    print("[yellow]NOTE[/yellow] Step 2 runner/state-machine not implemented yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
