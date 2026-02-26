from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

from src.pipeline.artifacts import Artifacts
from src.pipeline.drift_detector import run_drift_detector
from src.pipeline.runner import PipelineRunner
from src.pipeline.state import GateId, RunMeta
from src.utils.time import now_seoul

def _maybe_load_dotenv(repo_root: Optional[Path] = None) -> None:
    """Best-effort load of a .env file.

    - Does NOT require python-dotenv.
    - Sets environment variables only if they are not already set.
    - Ignores blank lines and comments starting with '#'.
    """
    root = repo_root or Path.cwd()
    env_path = root / ".env"
    if not env_path.exists():
        return

    try:
        raw = env_path.read_text(encoding="utf-8")
    except Exception:
        return

    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        key, val = s.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if not key:
            continue
        if os.environ.get(key) is None:
            os.environ[key] = val


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-16")


def _load_dotenv_if_available(*, cwd: Optional[Path] = None) -> None:
    """Best-effort load of .env from repo/project root.

    Behavior:
    - If `.env` doesn't exist, do nothing.
    - If `python-dotenv` is installed, use it.
    - Otherwise, fall back to a minimal parser (KEY=VALUE per line).
    - Never raises.
    """

    base = cwd or Path.cwd()
    env_path = base / ".env"
    if not env_path.exists():
        return

    # 1) Preferred: python-dotenv
    try:
        from dotenv import load_dotenv  # type: ignore

        try:
            load_dotenv(dotenv_path=env_path, override=False)
            return
        except Exception:
            # Fall through to minimal parser.
            pass
    except Exception:
        pass

    # 2) Minimal parser fallback
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, val = line.split('=', 1)
            key = key.strip()
            val = val.strip()
            if not key:
                continue
            # Do not override existing env vars
            if os.environ.get(key) is None:
                os.environ[key] = val
    except Exception:
        return



def build_default_runner(*, run_dir: str, meta: RunMeta, context: Optional[dict] = None) -> PipelineRunner:
    """Create a runner with the default G1~G7 gates registered."""
    # Lazy imports to keep CLI import fast and stable for test collection.
    from src.gates.g1_design import gate_g1_design
    from src.gates.g2_continuity import gate_g2_continuity
    from src.gates.g3_fact_audit import gate_g3_fact_audit
    from src.gates.g4_self_check import gate_g4_self_check
    from src.gates.g5_implement_test import gate_g5_implement_and_test
    from src.gates.g6_counterfactual import gate_g6_counterfactual_review
    from src.gates.g7_final_review import gate_g7_final_review

    runner = PipelineRunner(meta=meta, run_dir=run_dir, context=context or {})

    runner.register(GateId.G1, gate_g1_design)
    runner.register(GateId.G2, gate_g2_continuity)
    runner.register(GateId.G3, gate_g3_fact_audit)
    runner.register(GateId.G4, gate_g4_self_check)
    runner.register(GateId.G5, gate_g5_implement_and_test)
    runner.register(GateId.G6, gate_g6_counterfactual_review)
    runner.register(GateId.G7, gate_g7_final_review)

    return runner


def _cmd_run(*, request_file: Optional[Path], request_text: Optional[str], run_id: Optional[str], baseline: Optional[str]) -> int:
    if (request_file is None) == (request_text is None):
        print("ERROR: specify exactly one of --request-file or --request")
        return 2

    request_body: str
    if request_file is not None:
        request_file = request_file.resolve()
        if not request_file.exists():
            print(f"ERROR: request file not found: {request_file}")
            return 2
        request_body = _read_text(request_file)
    else:
        request_body = request_text or ""

    user_run_id = (run_id or "").strip() or None
    allocated_run_id: Optional[str] = user_run_id

    attempts = 0
    while True:
        if not allocated_run_id:
            allocated_run_id = now_seoul().strftime("%Y-%m-%d_%H%M%S_%f")
        try:
            artifacts = Artifacts.create_new(repo_root=Path.cwd(), run_id=allocated_run_id)
            break
        except FileExistsError:
            attempts += 1
            if user_run_id:
                print(f"ERROR: run-id already exists: runs/{user_run_id}")
                return 3
            if attempts >= 5:
                print("ERROR: failed to allocate a unique run-id after 5 attempts")
                return 3
            allocated_run_id = None

    (artifacts.run_dir / "00_USER_REQUEST.md").write_text(request_body, encoding="utf-8")


    baseline_id = (baseline or "").strip() or None
    if baseline_id is not None:
        baseline_dir = Path.cwd() / "runs" / baseline_id
        if not baseline_dir.exists():
            print(f"WARNING: baseline run not found: runs/{baseline_id} (continuing; diff may be skipped)")

    meta = RunMeta(run_id=artifacts.run_id, created_at=now_seoul().isoformat(), baseline_version_id=baseline_id)
    runner = build_default_runner(run_dir=str(artifacts.run_dir), meta=meta)

    runner.run()

    # Step39 Phase2: baseline drift detector (post-run)
    if baseline_id is not None:
        baseline_dir = Path.cwd() / "runs" / baseline_id
        if baseline_dir.exists():
            try:
                run_drift_detector(
                    baseline_run_dir=baseline_dir,
                    current_run_dir=artifacts.run_dir,
                    baseline_id=baseline_id,
                    current_id=artifacts.run_id,
                )
            except Exception as e:
                print(f"WARNING: drift detector failed: {e}")
        else:
            print(f"WARNING: baseline dir missing for drift detector: runs/{baseline_id} (skipping)")

    print(f"Pipeline finished status={meta.status.value}")
    print("Artifacts written:")
    for p in sorted(artifacts.run_dir.iterdir(), key=lambda x: x.name):
        print(f" - {p.name}")

    return 0


def _cmd_list_gates() -> int:
    """Print the default gate registry snapshot (introspection)."""
    meta = RunMeta(run_id="LIST_GATES", created_at=now_seoul().isoformat())
    runner = build_default_runner(run_dir=str(Path.cwd()), meta=meta)

    snap = runner.registered_gates()
    for gid in sorted(snap.keys()):
        print(f"{gid}: {snap[gid]}")

    return 0


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m src.pipeline.cli")

    sub = p.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run the pipeline")
    g = p_run.add_mutually_exclusive_group(required=True)
    g.add_argument("--request-file", default=None, help="Path to markdown file containing user request")
    g.add_argument("--request", default=None, help="Inline request text (use PowerShell `n for newlines)")
    p_run.add_argument("--run-id", default=None, help="Optional run id")
    p_run.add_argument("--baseline", default=None, help="Optional baseline run id (for drift/policy diff comparisons)")

    sub.add_parser("list-gates", help="List default registered gates")

    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    # Ensure .env is loaded before any provider checks happen.
    _maybe_load_dotenv(repo_root=Path.cwd())

    args = parse_args(argv)

    if args.cmd == "run":
        req_file = Path(args.request_file) if args.request_file else None
        return _cmd_run(request_file=req_file, request_text=args.request, run_id=args.run_id, baseline=args.baseline)

    if args.cmd == "list-gates":
        return _cmd_list_gates()

    print(f"ERROR: unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
