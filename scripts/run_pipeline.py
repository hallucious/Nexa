from __future__ import annotations

import argparse
import sys
from pathlib import Path

# --- BOOTSTRAP ---
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
# -----------------

import os

def load_dotenv(path: Path) -> None:
    """Load a .env file into os.environ (best-effort, stdlib-only).

    - Ignores blank lines and comments (#)
    - Supports KEY=VALUE, with optional surrounding quotes on VALUE
    - Does NOT override already-set environment variables
    """
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            key, val = s.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except Exception:
        # Never fail pipeline boot due to dotenv issues.
        return

# Load .env from repo root early (keys for OpenAI/Perplexity/Gemini)
load_dotenv(REPO_ROOT / ".env")

from src.pipeline.artifacts import Artifacts
from src.pipeline.state import RunMeta, GateId
from src.pipeline.runner import PipelineRunner
from src.gates.g1_design import gate_g1_design
from src.gates.g2_continuity import gate_g2_continuity
from src.gates.g3_fact_audit import gate_g3_fact_audit
from src.gates.g4_self_check import gate_g4_self_check
from src.gates.g5_implement_test import gate_g5_implement_and_test
from src.gates.g6_counterfactual import gate_g6_counterfactual_review
from src.gates.g7_final_review import gate_g7_final_review
from src.utils.time import now_seoul


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="7-Gate Pipeline Runner (Step 10: G1~G7 real, stdlib-only)"
    )
    p.add_argument("--request", required=True, help="Path to a markdown file containing user request")
    p.add_argument("--run-id", default=None, help="Optional run id. If omitted, an id is auto-generated.")
    return p.parse_args()


def read_request_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-16")


def main() -> int:
    args = parse_args()

    request_path = Path(args.request).resolve()
    if not request_path.exists():
        print(f"ERROR: request file not found: {request_path}")
        return 2

    # Ensure run_id is never None; auto-generate a unique id when not provided.
    user_run_id = (args.run_id or "").strip() or None
    run_id = user_run_id

    # If user didn't provide a run_id, generate one. If collision occurs (extremely rare),
    # regenerate a few times.
    attempts = 0
    while True:
        if not run_id:
            run_id = now_seoul().strftime("%Y-%m-%d_%H%M%S_%f")
        try:
            artifacts = Artifacts.create_new(repo_root=REPO_ROOT, run_id=run_id)
            break
        except FileExistsError:
            attempts += 1
            if user_run_id:
                print(f"ERROR: run-id already exists: runs/{user_run_id}")
                return 3
            if attempts >= 5:
                print("ERROR: failed to allocate a unique run-id after 5 attempts")
                return 3
            # regenerate and retry
            run_id = None

    artifacts.write_text("00_USER_REQUEST.md", read_request_text(request_path))

    meta = RunMeta(
        run_id=artifacts.run_id,
        created_at=now_seoul().isoformat(),
        baseline_version_id=None,
        providers={"gpt": "stub", "gemini": "stub", "perplexity": "stub", "codex": "stub"},
    )
    artifacts.write_meta(meta)

    runner = PipelineRunner(meta=meta, run_dir=str(artifacts.run_dir))

    # Real gates: G1~G7
    runner.register(GateId.G1, gate_g1_design)
    runner.register(GateId.G2, gate_g2_continuity)
    runner.register(GateId.G3, gate_g3_fact_audit)
    runner.register(GateId.G4, gate_g4_self_check)
    runner.register(GateId.G5, gate_g5_implement_and_test)
    runner.register(GateId.G6, gate_g6_counterfactual_review)
    runner.register(GateId.G7, gate_g7_final_review)

    runner.run()
    artifacts.write_meta(meta)

    print(f"Pipeline finished status={meta.status.value}")
    print("Artifacts written:")
    for f in sorted(Path(artifacts.run_dir).iterdir()):
        print(" -", f.name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())