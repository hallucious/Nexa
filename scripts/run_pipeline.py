from __future__ import annotations

import argparse
import sys
from pathlib import Path

# --- BOOTSTRAP ---
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
# -----------------

from src.pipeline.artifacts import Artifacts
from src.pipeline.state import RunMeta, GateId
from src.pipeline.runner import PipelineRunner
from src.gates.g1_design import gate_g1_design
from src.gates.g2_continuity import gate_g2_continuity
from src.gates.g3_fact_audit import gate_g3_fact_audit
from src.gates.g4_self_check import gate_g4_self_check
from src.gates.g5_implement_test import gate_g5_implement_and_test
from src.gates.g6_counterfactual import gate_g6_counterfactual_review
from src.gates.mock_gate_v2 import make_contract_pass_gate
from src.utils.time import now_seoul


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="7-Gate Pipeline Runner (Step 9: G1~G6 real, stdlib-only)"
    )
    p.add_argument("--request", required=True, help="Path to a markdown file containing user request")
    p.add_argument("--run-id", default=None, help="Optional run id YYYY-MM-DD_HHMM")
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

    try:
        artifacts = Artifacts.create_new(repo_root=REPO_ROOT, run_id=args.run_id)
    except FileExistsError:
        print(f"ERROR: run-id already exists: runs/{args.run_id}")
        return 3

    artifacts.write_text("00_USER_REQUEST.md", read_request_text(request_path))

    meta = RunMeta(
        run_id=artifacts.run_id,
        created_at=now_seoul().isoformat(),
        baseline_version_id=None,
        providers={"gpt": "stub", "gemini": "stub", "perplexity": "stub", "codex": "stub"},
    )
    artifacts.write_meta(meta)

    runner = PipelineRunner(meta=meta, run_dir=str(artifacts.run_dir))

    # Real gates: G1~G6
    runner.register(GateId.G1, gate_g1_design)
    runner.register(GateId.G2, gate_g2_continuity)
    runner.register(GateId.G3, gate_g3_fact_audit)
    runner.register(GateId.G4, gate_g4_self_check)
    runner.register(GateId.G5, gate_g5_implement_and_test)
    runner.register(GateId.G6, gate_g6_counterfactual_review)

    # Gate7 remains contract mock for now
    runner.register(GateId.G7, make_contract_pass_gate("G7", "Final review OK (mock)"))

    runner.run()
    artifacts.write_meta(meta)

    print(f"Pipeline finished status={meta.status.value}")
    print("Artifacts written:")
    for f in sorted(Path(artifacts.run_dir).iterdir()):
        print(" -", f.name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
