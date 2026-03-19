from __future__ import annotations

import argparse
import sys
from typing import List, Optional, Sequence

from src.engine.engine import Engine
from src.contracts.nex_loader import load_nex_file
from src.contracts.nex_engine_adapter import build_engine_from_nex


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hai-engine",
        description="Hyper-AI Engine CLI (Engine-native execution)",
    )

    subparsers = parser.add_subparsers(dest="command")

    # run .nex
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("file", type=str)

    # legacy args
    parser.add_argument("--input", type=str, required=False)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--entry-node-id", type=str, required=False)
    parser.add_argument("--node-ids", type=str, required=False)

    return parser


def _parse_node_ids(node_ids_csv: Optional[str]) -> Optional[List[str]]:
    if not node_ids_csv:
        return None
    return [s.strip() for s in node_ids_csv.split(",") if s.strip()]


def run_nex(file_path: str) -> int:
    circuit = load_nex_file(file_path)
    engine = build_engine_from_nex(circuit)

    trace = engine.execute(revision_id="cli")

    for node_id, node in trace.nodes.items():
        print(f"{node_id}: {node.node_status}")

    return 0


def run_engine(
    input_path: Optional[str],
    dry_run: bool,
    entry_node_id: Optional[str],
    node_ids: Optional[List[str]],
) -> int:
    if dry_run:
        print("[Engine CLI] Dry run successful.")
        return 0

    if not entry_node_id or not node_ids:
        print("[Engine CLI] Execution placeholder.")
        return 0

    engine = Engine(entry_node_id=entry_node_id, node_ids=node_ids)

    result = engine.run(payload={"input": input_path})

    if getattr(result, "success", True):
        print("[Engine CLI] Execution completed.")
        return 0

    print("[Engine CLI] Execution failed.")
    return 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "run":
        return run_nex(args.file)

    node_ids = _parse_node_ids(args.node_ids)
    return run_engine(args.input, args.dry_run, args.entry_node_id, node_ids)


if __name__ == "__main__":
    sys.exit(main())
