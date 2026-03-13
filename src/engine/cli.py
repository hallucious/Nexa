"""
Engine CLI - Hyper-AI

Phase B:
- Provide a stable Engine-native CLI surface.
- Keep backward-stable contract: running with no args returns 0 and prints a placeholder.
- Allow opt-in real Engine execution when required engine wiring args are provided.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional, Sequence

from src.engine.engine import Engine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hai-engine",
        description="Hyper-AI Engine CLI (Engine-native execution)",
    )
    parser.add_argument(
        "--input",
        type=str,
        required=False,
        help="Input file or payload path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without side effects",
    )

    # Opt-in real engine run wiring (Phase B step2)
    parser.add_argument(
        "--entry-node-id",
        type=str,
        required=False,
        help="Engine entry_node_id (required for real run)",
    )
    parser.add_argument(
        "--node-ids",
        type=str,
        required=False,
        help="Comma-separated list of engine node_ids (required for real run)",
    )
    return parser


def _parse_node_ids(node_ids_csv: Optional[str]) -> Optional[List[str]]:
    if not node_ids_csv:
        return None
    items = [s.strip() for s in node_ids_csv.split(",")]
    items = [s for s in items if s]
    return items or None


def run_engine(
    input_path: Optional[str],
    dry_run: bool,
    entry_node_id: Optional[str],
    node_ids: Optional[List[str]],
) -> int:
    if dry_run:
        print("[Engine CLI] Dry run successful.")
        return 0

    # Keep contract stability: if not enough info to construct Engine, do nothing.
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
    node_ids = _parse_node_ids(args.node_ids)
    return run_engine(args.input, args.dry_run, args.entry_node_id, node_ids)


if __name__ == "__main__":
    sys.exit(main())
