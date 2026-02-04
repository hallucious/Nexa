from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
from rich import print

from src.pipeline.artifacts import Artifacts
from src.pipeline.state import RunMeta, GateId
from src.pipeline.runner import PipelineRunner
from src.gates.mock_gate_v2 import make_contract_pass_gate
from src.utils.time import now_seoul


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="7-Gate Pipeline Runner (Step 3)")
    p.add_argument("--request", required=True)
    p.add_argument("--run-id")
    return p.parse_args()


def read_request_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-16")


def main() -> int:
    load_dotenv()
    args = parse_args()

    request_path = Path(args.request).resolve()
    if not request_path.exists():
        raise FileNotFoundError(request_path)

    artifacts = Artifacts.create_new(repo_root=REPO_ROOT, run_id=args.run_id)
    artifacts.write_text("00_USER_REQUEST.md", read_request_text(request_path))

    meta = RunMeta(
        run_id=artifacts.run_id,
        created_at=now_seoul().isoformat(),
        providers={"gpt": "mock", "gemini": "mock", "perplexity": "mock", "codex": "mock"},
    )
    artifacts.write_meta(meta)

    runner = PipelineRunner(meta=meta, run_dir=str(artifacts.run_dir))

    runner.register(GateId.G1, make_contract_pass_gate("G1", "Design OK"))
    runner.register(GateId.G2, make_contract_pass_gate("G2", "Consistency OK"))
    runner.register(GateId.G3, make_contract_pass_gate("G3", "Facts OK"))
    runner.register(GateId.G4, make_contract_pass_gate("G4", "Self-check OK"))
    runner.register(GateId.G5, make_contract_pass_gate("G5", "Implementation OK"))
    runner.register(GateId.G6, make_contract_pass_gate("G6", "Counterfactual OK"))
    runner.register(GateId.G7, make_contract_pass_gate("G7", "Final review OK"))

    runner.run()
    artifacts.write_meta(meta)

    print(f"[green]Pipeline finished[/green] status={meta.status.value}")
    print("Artifacts written:")
    for f in sorted(Path(artifacts.run_dir).iterdir()):
        print(" -", f.name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
