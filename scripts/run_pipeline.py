from __future__ import annotations

import argparse
import sys
from pathlib import Path

# bootstrap import path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
from rich import print

from src.pipeline.artifacts import Artifacts
from src.pipeline.state import RunMeta, GateId
from src.pipeline.runner import PipelineRunner
from src.gates.mock_gate import make_pass_gate, make_info_gate
from src.utils.time import now_seoul


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="7-Gate Pipeline Runner (Step 2)")
    p.add_argument("--request", required=True)
    p.add_argument("--run-id")
    p.add_argument("--dry-run", action="store_true")
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

    # register mock gates
    runner.register(GateId.G1, make_pass_gate("G1 PASS"))
    runner.register(GateId.G2, make_pass_gate("G2 PASS"))
    runner.register(GateId.G3, make_pass_gate("G3 PASS"))
    runner.register(GateId.G4, make_pass_gate("G4 PASS"))
    runner.register(GateId.G5, make_pass_gate("G5 PASS"))
    runner.register(GateId.G6, make_info_gate("G6 INFO"))
    runner.register(GateId.G7, make_pass_gate("G7 PASS"))

    runner.run()
    artifacts.write_meta(meta)

    print(f"[green]Pipeline finished[/green] status={meta.status.value}")
    print("Transitions:")
    for t in meta.transitions:
        print(f" - {t.from_gate} -> {t.to_gate} ({t.decision})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
