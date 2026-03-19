from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from src.contracts.nex_bundle_loader import load_nex_bundle
from src.contracts.nex_engine_adapter import build_engine_from_nex
from src.contracts.nex_loader import load_nex_file
from src.contracts.nex_plugin_integration import validate_plugins_from_nex
from src.engine.engine import Engine
from src.engine.types import NodeStatus


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

    # legacy args
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


def _node_attempts(node_meta: Optional[Dict[str, Any]], status: NodeStatus) -> int:
    if node_meta and isinstance(node_meta.get("retry"), dict):
        retry_meta = node_meta["retry"]
        if isinstance(retry_meta.get("attempt_count"), int):
            return retry_meta["attempt_count"]
    if status in (NodeStatus.SUCCESS, NodeStatus.FAILURE):
        return 1
    return 0


def build_trace_summary(circuit_id: str, trace) -> Dict[str, Any]:
    nodes: Dict[str, Dict[str, Any]] = {}
    any_failure = False

    for node_id, node_trace in trace.nodes.items():
        status = node_trace.node_status
        nodes[node_id] = {
            "status": status.value.upper(),
            "attempts": _node_attempts(getattr(node_trace, "meta", None), status),
        }
        if status == NodeStatus.FAILURE:
            any_failure = True

    return {
        "circuit_id": circuit_id,
        "status": "FAILURE" if any_failure else "SUCCESS",
        "nodes": nodes,
    }


def run_nex(
    circuit_path: str,
    out_path: Optional[str] = None,
    bundle_path: Optional[str] = None,
) -> int:
    if bundle_path:
        raw_data = json.loads(Path(circuit_path).read_text(encoding="utf-8"))
        validate_plugins_from_nex(raw_data, bundle_path)

    circuit = load_nex_file(circuit_path)
    engine = build_engine_from_nex(circuit)
    trace = engine.execute(revision_id="cli")
    payload = build_trace_summary(circuit.circuit.circuit_id, trace)

    if out_path:
        out_file = Path(out_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))

    return 0


def run_nex_bundle(bundle_path: str, out_path: Optional[str] = None) -> int:
    bundle = load_nex_bundle(bundle_path)
    try:
        raw_data = json.loads(bundle.circuit_path.read_text(encoding="utf-8"))
        validate_plugins_from_nex(raw_data, str(bundle.temp_dir))

        circuit = load_nex_file(str(bundle.circuit_path))
        engine = build_engine_from_nex(circuit)
        trace = engine.execute(revision_id="cli")
        payload = build_trace_summary(circuit.circuit.circuit_id, trace)

        if out_path:
            out_file = Path(out_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        else:
            print(json.dumps(payload, indent=2, ensure_ascii=False))

        return 0
    finally:
        bundle.cleanup()


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
            return run_nex_bundle(args.circuit, getattr(args, "out", None))
        return run_nex(args.circuit, getattr(args, "out", None), getattr(args, "bundle", None))

    node_ids = _parse_node_ids(args.node_ids)
    return run_engine(args.input, args.dry_run, args.entry_node_id, node_ids)


if __name__ == "__main__":
    sys.exit(main())
