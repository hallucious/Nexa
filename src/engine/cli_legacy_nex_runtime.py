from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from src.cli.savefile_runtime import is_savefile_contract
from src.contracts.nex_bundle_loader import load_nex_bundle
from src.contracts.nex_engine_adapter import build_engine_from_nex
from src.contracts.nex_loader import load_nex_file
from src.contracts.nex_plugin_integration import validate_plugins_from_nex
from src.engine.types import NodeStatus

ApplyBaselinePolicy = Callable[[Dict[str, Any], Optional[str], Optional[str]], tuple[Dict[str, Any], int]]
WritePayload = Callable[[Dict[str, Any], Optional[str]], None]
RunSavefile = Callable[[str, Optional[str], Optional[str], Optional[str]], int]


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


def run_legacy_nex(
    circuit_path: str,
    *,
    out_path: Optional[str] = None,
    bundle_path: Optional[str] = None,
    baseline_path: Optional[str] = None,
    policy_config_path: Optional[str] = None,
    apply_baseline_policy: ApplyBaselinePolicy,
    write_or_print_payload: WritePayload,
) -> int:
    if bundle_path:
        raw_data = json.loads(Path(circuit_path).read_text(encoding="utf-8"))
        validate_plugins_from_nex(raw_data, bundle_path)

    circuit = load_nex_file(circuit_path)
    engine = build_engine_from_nex(circuit)
    trace = engine.execute(revision_id="cli")
    payload = build_trace_summary(circuit.circuit.circuit_id, trace)
    payload, exit_code = apply_baseline_policy(payload, baseline_path, policy_config_path)
    write_or_print_payload(payload, out_path)
    return exit_code


def run_legacy_nex_bundle(
    bundle_path: str,
    *,
    out_path: Optional[str] = None,
    baseline_path: Optional[str] = None,
    policy_config_path: Optional[str] = None,
    run_savefile_nex: RunSavefile,
    apply_baseline_policy: ApplyBaselinePolicy,
    write_or_print_payload: WritePayload,
) -> int:
    bundle = load_nex_bundle(bundle_path, require_plugins=False)
    try:
        if is_savefile_contract(str(bundle.circuit_path)):
            return run_savefile_nex(
                str(bundle.circuit_path),
                out_path,
                baseline_path,
                policy_config_path,
            )

        if not bundle.plugins_dir.exists():
            raise RuntimeError("plugins/ missing in bundle")

        raw_data = json.loads(bundle.circuit_path.read_text(encoding="utf-8"))
        validate_plugins_from_nex(raw_data, str(bundle.temp_dir))

        circuit = load_nex_file(str(bundle.circuit_path))
        engine = build_engine_from_nex(circuit)
        trace = engine.execute(revision_id="cli")
        payload = build_trace_summary(circuit.circuit.circuit_id, trace)
        payload, exit_code = apply_baseline_policy(payload, baseline_path, policy_config_path)
        write_or_print_payload(payload, out_path)
        return exit_code
    finally:
        bundle.cleanup()
