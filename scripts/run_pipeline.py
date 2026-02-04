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
from src.pipeline.state import RunMeta, GateId
from src.pipeline.runner import PipelineRunner
from src.gates.g1_design import gate_g1_design
from src.gates.g2_continuity import gate_g2_continuity
from src.gates.mock_gate_v2 import make_contract_pass_gate
from src.utils.time import now_seoul


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="7-Gate Pipeline Runner (Step 5: G1+G2 real, others mock)")
    p.add_argument("--request", required=True, help="Path to a markdown file containing user request")
    p.add_argument("--run-id", default=None, help="Optional run id YYYY-MM-DD_HHMM")
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

    # Create run folder + write 00_USER_REQUEST.md
    try:
        artifacts = Artifacts.create_new(repo_root=REPO_ROOT, run_id=args.run_id)
    except FileExistsError:
        print(f"[red]ERROR[/red] run-id already exists: runs/{args.run_id}")
        return 3

    artifacts.write_text("00_USER_REQUEST.md", read_request_text(request_path))

    # Initialize META
    meta = RunMeta(
        run_id=artifacts.run_id,
        created_at=now_seoul().isoformat(),
        baseline_version_id=None,
        providers={"gpt": "stub", "gemini": "stub", "perplexity": "stub", "codex": "stub"},
    )
    artifacts.write_meta(meta)

    # Runner + gates
    runner = PipelineRunner(meta=meta, run_dir=str(artifacts.run_dir))

    # Step 5: G1 + G2 real; others contract mocks
    runner.register(GateId.G1, gate_g1_design)
    runner.register(GateId.G2, gate_g2_continuity)
    runner.register(GateId.G3, make_contract_pass_gate("G3", "Facts OK (mock)"))
    runner.register(GateId.G4, make_contract_pass_gate("G4", "Self-check OK (mock)"))
    runner.register(GateId.G5, make_contract_pass_gate("G5", "Implementation OK (mock)"))
    runner.register(GateId.G6, make_contract_pass_gate("G6", "Counterfactual OK (mock)"))
    runner.register(GateId.G7, make_contract_pass_gate("G7", "Final review OK (mock)"))

    runner.run()
    artifacts.write_meta(meta)

    print(f"[green]Pipeline finished[/green] status={meta.status.value}")
    print("Artifacts written:")
    for f in sorted(Path(artifacts.run_dir).iterdir()):
        print(" -", f.name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
