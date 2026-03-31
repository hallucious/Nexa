"""Compatibility wrapper for the legacy engine CLI surface.

The canonical public CLI entrypoint is ``src.cli.nexa_cli:main`` as exposed
through ``pyproject.toml`` and ``nexa.py``. This module remains only as a
bounded compatibility surface for engine-specific tests and old callers that
still import ``src.engine.cli`` directly.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional, Sequence

from src.cli.savefile_runtime import (
    run_legacy_nex,
    run_legacy_nex_bundle,
    run_savefile_nex,
)
from src.engine.cli_policy_integration import render_regression_policy_output
from src.engine.engine import Engine
from src.engine.types import NodeStatus

CANONICAL_PUBLIC_CLI = "src.cli.nexa_cli:main"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hai-engine",
        description="Hyper-AI Engine CLI (Engine-native execution)",
    )

    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Execute a .nex circuit file")
    run_parser.add_argument("circuit", type=str, help="Path to .nex circuit file")
    run_parser.add_argument(
        "--out",
        type=str,
        required=False,
        help="Write execution summary JSON to file",
    )
    run_parser.add_argument(
        "--bundle",
        type=str,
        required=False,
        help="Path to bundle root that contains plugins/",
    )
    run_parser.add_argument(
        "--baseline",
        type=str,
        required=False,
        help="Path to baseline execution summary JSON for regression gating",
    )
    run_parser.add_argument(
        "--policy-config",
        type=str,
        required=False,
        help="Path to policy config JSON",
    )

    parser.add_argument("--input", type=str, required=False)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--entry-node-id", type=str, required=False)
    parser.add_argument("--node-ids", type=str, required=False)

    return parser


def _parse_node_ids(node_ids_csv: Optional[str]) -> Optional[List[str]]:
    if not node_ids_csv:
        return None
    items = [s.strip() for s in node_ids_csv.split(",")]
    items = [s for s in items if s]
    return items or None


# Compatibility export retained for older tests/importers.
def _render_policy_output(policy_result):
    return render_regression_policy_output(policy_result)


def run_nex(
    circuit_path: str,
    out_path: Optional[str] = None,
    bundle_path: Optional[str] = None,
    baseline_path: Optional[str] = None,
    policy_config_path: Optional[str] = None,
) -> int:
    return run_legacy_nex(
        circuit_path,
        out_path,
        bundle_path,
        baseline_path,
        policy_config_path,
    )



def run_nex_bundle(
    bundle_path: str,
    out_path: Optional[str] = None,
    baseline_path: Optional[str] = None,
    policy_config_path: Optional[str] = None,
) -> int:
    return run_legacy_nex_bundle(
        bundle_path,
        out_path,
        baseline_path,
        policy_config_path,
    )



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
    trace = engine.execute(revision_id="cli")
    has_failure = any(node.node_status == NodeStatus.FAILURE for node in trace.nodes.values())

    if not has_failure:
        print("[Engine CLI] Execution completed.")
        return 0

    print("[Engine CLI] Execution failed.")
    return 1



def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "run":
        if str(args.circuit).endswith(".nexb"):
            return run_nex_bundle(
                args.circuit,
                getattr(args, "out", None),
                getattr(args, "baseline", None),
                getattr(args, "policy_config", None),
            )
        return run_nex(
            args.circuit,
            getattr(args, "out", None),
            getattr(args, "bundle", None),
            getattr(args, "baseline", None),
            getattr(args, "policy_config", None),
        )

    node_ids = _parse_node_ids(args.node_ids)
    return run_engine(args.input, args.dry_run, args.entry_node_id, node_ids)


if __name__ == "__main__":
    sys.exit(main())
